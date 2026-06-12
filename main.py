from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import pandas as pd
import urllib.parse

app = FastAPI()
FILE = "tabela zbiorcza z rankingiem.xlsx"


# ===== NORMALIZACJA =====
def normalize(text):
    if not isinstance(text, str):
        return ""
    return text.lower()


# ===== FLAGI =====
def get_flag(team):
    mapping = {
        "polska": "pl", "niemcy": "de", "meksyk": "mx",
        "kanada": "ca", "usa": "us", "paragwaj": "py",
        "katar": "qa", "szwajcaria": "ch",
        "brazylia": "br", "maroko": "ma",
        "australia": "au", "turcja": "tr",
        "korea": "kr", "czechy": "cz",
        "holandia": "nl", "japonia": "jp",
        "szwecja": "se", "tunezja": "tn",
        "hiszpania": "es", "belgia": "be",
        "egipt": "eg", "arabia": "sa",
        "urugwaj": "uy", "iran": "ir",
        "nowa zelandia": "nz", "francja": "fr",
        "senegal": "sn", "norwegia": "no",
        "argentyna": "ar", "algieria": "dz",
        "austria": "at", "jordania": "jo",
        "portugalia": "pt", "anglia": "gb",
        "chorwacja": "hr", "ghana": "gh",
        "panama": "pa", "kolumbia": "co",
        "kongo": "cd"
    }

    t = normalize(team)

    for k in mapping:
        if k in t:
            return f'<img src="https://flagcdn.com/24x18/{mapping[k]}.png" style="margin-right:6px">'
    return ""


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
        if (p1 - p2) * (a1 - a2) > 0 or (p1 == p2 and a1 == a2):
            return 1, "➖", "orange"
        return 0, "❌", "red"
    except:
        return 0, "❌", "red"


# ===== RANKING =====
def get_ranking():
    xls = pd.ExcelFile(FILE)
    results = get_results()
    data = []

    for sheet in xls.sheet_names:

        if sheet in ["Wyniki", "Ranking", "Typy_Zbiorcze", "Instrukcja"]:
            continue

        df = pd.read_excel(xls, sheet)

        total = hits = 0

        for _, r in df.iterrows():
            match = r.get("Mecz")
            typ = r.get("Typ")

            if not isinstance(match, str):
                continue

            actual = results.get(match.strip())

            if actual:
                pts, _, _ = get_points(typ, actual)
                total += pts
                if pts == 3:
                    hits += 1

        data.append({"name": sheet.strip(), "pts": total, "hits": hits})

    return sorted(data, key=lambda x: (x["pts"], x["hits"]), reverse=True)


# ===== HOME =====
@app.get("/", response_class=HTMLResponse)
def home():

    rows = ""
    for i, r in enumerate(get_ranking(), 1):
        safe = urllib.parse.quote(r['name'])

        rows += f"""
        <tr>
            <td>{i}</td>
            <td><a href="/gracz/{safe}">{r['name']}</a></td>
            <td>{r['pts']}</td>
            <td>🎯 {r['hits']}</td>
        </tr>
        """

    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width">
    <style>
    body {{background:#f2f2f2;font-family:Arial;margin:0}}
    .box {{max-width:500px;margin:auto;padding:10px}}
    table {{width:100%;background:white;border-radius:10px}}
    td, th {{padding:12px}}
    a {{text-decoration:none;color:black;font-weight:bold}}
    </style>
    </head>

    <body>
    <div class="box">
    <h3>🏆 Ranking</h3>

    <table>
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
    xls = pd.ExcelFile(FILE)

    if name not in xls.sheet_names:
        return "<h2>❌ Nie znaleziono gracza</h2>"

    df = pd.read_excel(xls, name)
    results = get_results()

    html = ""
    total = hits = mid = miss = 0

    for _, r in df.iterrows():

        match = r.get("Mecz")
        typ = r.get("Typ")

        if not isinstance(match, str):
            continue

        actual = results.get(match.strip())

        t1, t2 = [x.strip() for x in match.split("-")]

        if not actual:
            html += f"""
            <div style="background:#eee;padding:10px;margin:5px;border-radius:8px">
                <div>{get_flag(t1)} {t1}</div>
                <div>{get_flag(t2)} {t2}</div>
                <div>-:-</div>
                <div>TYP {typ}</div>
            </div>
            """
            continue

        pts, sym, col = get_points(typ, actual)

        total += pts
        if pts == 3:
            hits += 1
        elif pts == 1:
            mid += 1
        else:
            miss += 1

        html += f"""
        <div style="background:white;padding:10px;margin:5px;border-radius:8px">
            <div>{get_flag(t1)} {t1}</div>
            <div>{get_flag(t2)} {t2}</div>

            <div><b>{actual[0]}:{actual[1]}</b></div>
            <div>TYP {typ}</div>

            <div style="color:{col}">{sym} {pts}</div>
        </div>
        """

    total_matches = hits + mid + miss
    acc = int(hits / total_matches * 100) if total_matches else 0

    return f"""
    <html>
    <body style="background:#eee;font-family:Arial">

    <div style="max-width:500px;margin:auto;padding:10px">

    <a href="/">⬅ Powrót</a>

    <h3>{name} • {total} pkt</h3>

    <div style="background:white;padding:10px;border-radius:8px">
        🎯 {hits} | ⚖️ {mid} | ❌ {miss} | 📊 {acc}%
    </div>

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
            <td><input name="g1_{i}" value="{g1}" style="width:50px"></td>
            <td><input name="g2_{i}" value="{g2}" style="width:50px"></td>
        </tr>
        """

    return f"""
    <html>
    <body style="font-family:Arial">

    <h2>⚙️ Panel wyników</h2>

    <a href="/">⬅ Powrót</a><br><br>

    <form method="post">
    <table border="1" cellpadding="8">
    <tr><th>Mecz</th><th>Gol 1</th><th>Gol 2</th></tr>
    {rows}
    </table>

    <br>
    <button type="submit">💾 ZAPISZ</button>
    </form>

    </body>
    </html>
    """


@app.post("/admin")
async def admin_save(request: Request):

    try:
        form = await request.form()

        xls = pd.ExcelFile(FILE)
        sheets = {}

        for sheet in xls.sheet_names:
            sheets[sheet] = pd.read_excel(xls, sheet)

        df = sheets["Wyniki"]

        for i in df.index:
            g1 = form.get(f"g1_{i}")
            g2 = form.get(f"g2_{i}")

            if g1 and g1.isdigit():
                df.at[i, "Gol 1"] = int(g1)

            if g2 and g2.isdigit():
                df.at[i, "Gol 2"] = int(g2)

        sheets["Wyniki"] = df

        with pd.ExcelWriter(FILE, engine="openpyxl") as writer:
            for name, data in sheets.items():
                data.to_excel(writer, sheet_name=name, index=False)

        return RedirectResponse("/", status_code=303)

    except Exception as e:
        return HTMLResponse(f"<h2>Błąd zapisu</h2><pre>{e}</pre>")
