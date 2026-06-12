from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import pandas as pd
import urllib.parse

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
            return 3, "✅", "green"

        if (p1 - p2) * (a1 - a2) > 0 or (p1 == p2 == a1 == a2):
            return 1, "➖", "orange"

        return 0, "❌", "red"

    except:
        return 0, "❌", "red"


# ===== RANKING =====
def get_ranking():
    xls = pd.ExcelFile(FILE)
    results = get_results()
    ranking = []

    for sheet in xls.sheet_names:
        if sheet == "Wyniki":
            continue

        df = pd.read_excel(xls, sheet)

        total = hits = 0

        for _, r in df.iterrows():
            m = r.get("Mecz")
            t = r.get("Typ")

            if not isinstance(m, str):
                continue

            actual = results.get(m.strip())

            if actual:
                p, _, _ = get_points(t, actual)
                total += p

                if p == 3:
                    hits += 1

        ranking.append({
            "name": sheet.strip(),
            "pts": total,
            "hits": hits
        })

    return sorted(ranking, key=lambda x: (x["pts"], x["hits"]), reverse=True)


# ===== HOME =====
@app.get("/", response_class=HTMLResponse)
def home():

    rows = ""

    for i, r in enumerate(get_ranking(), 1):
        safe = urllib.parse.quote(r["name"])

        rows += f"""
        <tr onclick="location.href='/gracz/{safe}'" style="<td>{r['name']}</td>
            <td>{r['pts']}</td>
            <td>🎯 {r['hits']}</td>
        </tr>
        """

    return f"""
    <html>
    <body style="font-family:Arial;background:#eee">

    <div style="max-width:500px;margin:auto">

    <h2>🏆 Ranking</h2>

    <table border="1" style="width:100%;background:white">
    <tr><th>#</th><th>Gracz</th><th>Pkt</th><th>🎯</th></tr>
    {rows}
    </table>

    <br>
    <a href="/admin">⚙️ Panel admin</a>

    </div>

    </body>
    </html>
    """


# ===== PLAYER =====
@app.get("/gracz/{name}", response_class=HTMLResponse)
def player(name: str):

    name = urllib.parse.unquote(name)

    df = pd.read_excel(pd.ExcelFile(FILE), name)
    results = get_results()

    html = ""
    total = hits = mid = miss = 0

    for _, r in df.iterrows():

        m = r.get("Mecz")
        t = r.get("Typ")

        if not isinstance(m, str):
            continue

        actual = results.get(m.strip())

        t1, t2 = [x.strip() for x in m.split("-")]

        if not actual:
            html += f"""
            <div style="background:#eee;padding:10px;margin:5px">
                {t1} vs {t2} -:- TYP {t}
            </div>
            """
            continue

        p, sym, col = get_points(t, actual)

        total += p
        if p == 3:
            hits += 1
        elif p == 1:
            mid += 1
        else:
            miss += 1

        html += f"""
        <div style="background:white;padding:10px;margin:5px">
            {t1} vs {t2}<br>
            <b>{actual[0]}:{actual[1]}</b><br>
            TYP {t}<br>
            <span style="color:{col}">{sym} {p}</span>
        </div>
        """

    total_matches = hits + mid + miss
    acc = int(hits / total_matches * 100) if total_matches else 0

    return f"""
    <html>
    <body>

    <div style="max-width:500px;margin:auto">

    <a href="/">⬅ Powrót</a>

    <h3>{name} • {total} pkt</h3>

    🎯 {hits} | ➖ {mid} | ❌ {miss} | 📊 {acc}%

    {html}

    </div>

    </body>
    </html>
    """


# ===== ADMIN =====
@app.get("/admin", response_class=HTMLResponse)
def admin():

    df = pd.read_excel(FILE, sheet_name="Wyniki")

    rows = ""

    for i, r in df.iterrows():

        m = r.get("Mecz")
        g1 = "" if pd.isna(r.get("Gol 1")) else int(r.get("Gol 1"))
        g2 = "" if pd.isna(r.get("Gol 2")) else int(r.get("Gol 2"))

        rows += f"""
        <tr>
            <td>{m}</td>
            <td><input name="g1_{i}" value="{g1}"></td>
            <td><input name="g2_{i}" value="{g2}"></td>
        </tr>
        """

    return f"""
    <html>
    <body>

    <h2>Panel wyników</h2>

    <form method="post">
    <table border="1">
    {rows}
    </table>

    <br>
    <button type="submit">Zapisz</button>
    </form>

    </body>
    </html>
    """


@app.post("/admin")
async def save(request: Request):

    form = await request.form()

    df = pd.read_excel(FILE, sheet_name="Wyniki")

    for i in df.index:

        g1 = form.get(f"g1_{i}")
        g2 = form.get(f"g2_{i}")

        if g1:
            df.at[i, "Gol 1"] = int(g1)

        if g2:
            df.at[i, "Gol 2"] = int(g2)

    with pd.ExcelWriter(FILE, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        df.to_excel(writer, sheet_name="Wyniki", index=False)

    return RedirectResponse("/", status_code=303)
