from fastapi import FastAPIfrom fastapiecz")
        g1 = r.get("Gol 1")
        g2 = r.get("Gol 2")

        if isinstance(match, str) and pd.notna(g1) and pd.notna(g2):
            results[match.strip()] = (int(g1), int(g2))

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

        # ignorujemy systemowe arkusze
        if sheet in ["Wyniki", "Ranking", "Typy_Zbiorcze", "Instrukcja"]:
            continue

        df = pd.read_excel(xls, sheet)

        total = 0

        for _, r in df.iterrows():
            match = r.get("Mecz")
            typ = r.get("Typ")

            if not isinstance(match, str):
                continue

            actual = results.get(match.strip())

            if actual:
                total += get_points(typ, actual)

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
        return "<h2>⚠️ Ranking pusty — sprawdź Excel</h2>"

    rows = ""

    for i, r in enumerate(ranking, 1):
        safe_name = urllib.parse.quote(r["name"])

        rows += f"""
        <tr onclick="location.href='/gracz/{safe_name}'" style="cursor:pointer}</td>
            <td>{r['pts']}</td>
        </tr>
        """

    return f"""
    <html>
    <body style="font-family:Arial">

    <h2>🏆 Ranking</h2>

    <table border="1" style="width:100%">
    <tr><th>#</th><th>Gracz</th><th>Pkt</th></tr>
    {rows}
    </table>

    </body>
    </html>
    """


# ===== PLAYER =====
@app.get("/gracz/{name}", response_class=HTMLResponse)
def player(name: str):

    name = urllib.parse.unquote(name)

    xls = pd.ExcelFile(FILE)

    if name not in xls.sheet_names:
        return f"<h2>❌ Nie znaleziono gracza: {name}</h2>"

    df = pd.read_excel(xls, name)
    results = get_results()

    html = ""

    for _, r in df.iterrows():
        match = r.get("Mecz")
        typ = r.get("Typ")

        if not isinstance(match, str):
            continue

        actual = results.get(match.strip())

        if actual:
            html += f"<div>{match} → {actual[0]}:{actual[1]} (typ {typ})</div>"
        else:
            html += f"<div>{match} → -:- (typ {typ})</div>"

    return f"""
    <html>
    <body>

    <h2>{name}</h2>

    {html}

    </body>
    </html>
    """
from fastapi.responses import HTMLResponse
import pandas as pd
import urllib.parse

app = FastAPI()

FILE = "tabela zbiorcza z rankingiem.xlsx"


# ===== WYNIKI =====
def get_results():
    df = pd.read_excel(FILE, sheet_name="Wyniki")
    results = {}

    for _, r in df.iterrows():
