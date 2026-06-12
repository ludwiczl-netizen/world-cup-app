from fastapi import FastAPI, Requestfrom fastapi import

app = FastAPI()

FILE = "tabela zbiorcza z rankingiem.xlsx"


# ===== WYNIKI =====
def get_results():
    df = pd.read_excel(FILE, sheet_name="Wyniki")
    results = {}

    for _, r in df.iterrows():
        m = r.get("Mecz")
        g1 = r.get("Gol 1")
        g2 = r.get("Gol 2")

        if isinstance(m, str) and pd.notna(g1) and pd.notna(g2):
            results[m.strip()] = (int(g1), int(g2))

    return results


# ===== PUNKTY =====
def get_points(pred, actual):
    try:
        p1, p2 = map(int, str(pred).replace("-", ":").split(":"))
        a1, a2 = actual

        if p1 == a1 and p2 == a2:
            return 3

        if (p1 - p2) * (a1 - a2) > 0 or (p1 == p2 == a1 == a2):
            return 1

        return 0

    except:
        return 0


# ===== RANKING =====
def get_ranking():
    xls = pd.ExcelFile(FILE)
    results = get_results()

    ranking = []

    for sheet in xls.sheet_names:

        # ✅ ignorujemy systemowe arkusze
        if sheet in ["Wyniki", "Ranking", "Typy_Zbiorcze", "Instrukcja"]:
            continue

        df = pd.read_excel(xls, sheet)

        total = 0

        for _, r in df.iterrows():
            m = r.get("Mecz")
            t = r.get("Typ")

            if not isinstance(m, str):
                continue

            actual = results.get(m.strip())

            if actual:
                total += get_points(t, actual)

        ranking.append({
            "name": sheet.strip(),
            "pts": total
        })

    return sorted(ranking, key=lambda x: x["pts"], reverse=True)


# ===== HOME =====
@app.get("/", response_class=HTMLResponse)
def home():

    ranking = get_ranking()

    if not ranking:
        return """
        <h2>⚠️ Ranking pusty</h2>
        <p>Sprawdź czy masz arkusze graczy (np. Marta, Kasia)</p>
        """

    rows = ""

    for i, r in enumerate(ranking, 1):
        safe_name = urllib.parse.quote(r["name"])

        rows += f"""
        <tr onclick="location.href='/gracz/{safe_name}'" style="<td>{r['name']}</td>
            <td>{r['pts']}</td>
        </tr>
        """

    return f"""
    <html>
    <body style="font-family:Arial;background:#eee">

    <div style="max-width:500px;margin:auto">

    <h2>🏆 Ranking</h2>

    <table border="1" style="width:100%;background:white">
    <tr><th>#</th><th>Gracz</th><th>Pkt</th></tr>
    {rows}
    </table>

    </div>

    </body>
    </html>
    """


# ===== PLAYER =====
@app.get("/gracz/{name}", response_class=HTMLResponse)
def player(name: str):

    name = urllib.parse.unquote(name)

    xls = pd.ExcelFile(FILE)

    # ✅ zabezpieczenie
    if name not in xls.sheet_names:
        return f"<h2>❌ Nie ma gracza: {name}</h2>"

    df = pd.read_excel(xls, name)
    results = get_results()

    html = ""

    for _, r in df.iterrows():

        m = r.get("Mecz")
        t = r.get("Typ")

        if not isinstance(m, str):
            continue

        actual = results.get(m.strip())

        if actual:
            html += f"""
            <div style="padding:10px;margin:5px;background:white">
                {m} → {actual[0]}:{actual[1]} (typ {t})
            </div>
            """
        else:
            html += f"""
            <div style="padding:10px;margin:5px;background:#eee">
                {m} → -:- (typ {t})
            </div>
            """

    return f"""
    <html>
    <body style="font-family:Arial;background:#eee">

    <div style="max-width:500px;margin:auto">

    <h3>{name}</h3>

    {html}

    </div>

    </body>
    </html>
    """

from fastapi.responses import HTMLResponse, RedirectResponse
import pandas as pd
