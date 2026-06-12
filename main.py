from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd
import requests

app = FastAPI()
FILE = "tabela zbiorcza z rankingiem.xlsx"


# ===== FLAGI =====
def get_flag(team):
    mapping = {
        "polska": "pl",
        "niemcy": "de",
        "meksyk": "mx",
        "rpa": "za",
        "korea południowa": "kr",
        "czechy": "cz"
    }

    if not isinstance(team, str):
        return ""

    for k in mapping:
        if k in team.lower():
            return f'<img src="https://flagcdn.com/24x18/{mapping[k]}.png" class="flag">'
    return ""


# ===== EXCEL (NAPRAWA NaN ✅) =====
def get_results():
    df = pd.read_excel(FILE, sheet_name="Wyniki")
    results = {}

    for _, r in df.iterrows():
        match = r.get("Mecz")
        g1 = r.get("Gol 1")
        g2 = r.get("Gol 2")

        # ✅ KLUCZOWA NAPRAWA
        if isinstance(match, str) and pd.notna(g1) and pd.notna(g2):
            results[match.strip()] = (int(g1), int(g2))

    return results


# ===== LIVE =====
def get_live():
    try:
        res = requests.get("https://sportscore.com/api/widget/matches/?sport=football", timeout=5)
        data = res.json()
        return [m for m in data.get("matches", []) if isinstance(m, dict)]
    except:
        return []


def get_live_match(name, matches):
    name = str(name).lower()

    for m in matches:
        if not isinstance(m, dict):
            continue

        home = m.get("home", {})
        away = m.get("away", {})

        h = home.get("name")
        a = away.get("name")

        if isinstance(h, str) and isinstance(a, str):
            if h.lower() in name and a.lower() in name:
                hs = home.get("score")
                as_ = away.get("score")

                if isinstance(hs, int) and isinstance(as_, int):
                    return (hs, as_), m.get("minute", "")

    return None, ""


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
    live = get_live()

    ranking = []

    for sheet in xls.sheet_names:
        if sheet in ["Wyniki", "Ranking", "Typy_Zbiorcze", "Instrukcja"]:
            continue

        df = pd.read_excel(xls, sheet)

        total, hits = 0, 0

        for _, r in df.iterrows():
            match = r.get("Mecz")
            typ = r.get("Typ")

            if not isinstance(match, str):
                continue

            actual = results.get(match.strip())
            live_score, _ = get_live_match(match, live)

            if live_score:
                actual = live_score

            if actual:
                pts, _, _ = get_points(typ, actual)
                total += pts

                if pts == 3:
                    hits += 1

        ranking.append({"name": sheet, "pts": total, "hits": hits})

    return sorted(ranking, key=lambda x: (x["pts"], x["hits"]), reverse=True)


# ===== HOME =====
@app.get("/", response_class=HTMLResponse)
def home():
    data = get_ranking()

    rows = ""
    for i, r in enumerate(data, 1):
        rows += f"""
        <tr>
            <td>{i}</td>
            <td><a href="/gracz/{r['name']}">{r['name']}</a></td>
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

    .container {{
        max-width:500px;
        margin:auto;
        padding:10px;
    }}

    table {{
        width:100%;
        background:white;
        border-radius:10px;
    }}

    td, th {{
        padding:12px;
    }}

    a {{
        text-decoration:none;
        font-weight:bold;
        color:black;
    }}

    </style>
    </head>

    <body>

    <div class="container">
    <h3>🏆 Ranking</h3>

    <table>
    <tr><th>#</th><th>Gracz</th><th>Pkt</th><th>Trafienia</th></tr>
    {rows}
    </table>

    </div>

    </body>
    </html>
    """


# ===== PLAYER =====
@app.get("/gracz/{name}", response_class=HTMLResponse)
def player(name: str):

    xls = pd.ExcelFile(FILE)
    df = pd.read_excel(xls, name)

    results = get_results()
    live = get_live()

    matches_html = ""
    total, hits, partial, miss = 0, 0, 0, 0

    for _, r in df.iterrows():
        match = r.get("Mecz")
        typ = r.get("Typ")

        if not isinstance(match, str):
            continue

        actual = results.get(match.strip())
        live_score, minute = get_live_match(match, live)

        if live_score:
            actual = live_score

        if not actual:
            continue

        pts, sym, col = get_points(typ, actual)
        total += pts

        if pts == 3:
            hits += 1
        elif pts == 1:
            partial += 1
        else:
            miss += 1

        t1, t2 = [x.strip() for x in match.split("-")]

        matches_html += f"""
        <div class="match">

            <div>
                <div>{get_flag(t1)} {t1}</div>
                <div>{get_flag(t2)} {t2}</div>
            </div>

            <div class="right">
                <div class="score">{actual[0]}:{actual[1]}</div>
                <div class="pred">TYP {typ}</div>
                <div class="live">{minute}</div>
                <div class="{col}">{sym} {pts} pkt</div>
            </div>

        </div>
        """

    total_matches = hits + partial + miss
    accuracy = int(hits / total_matches * 100) if total_matches else 0

    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width">

    <style>

    body {{background:#eee;font-family:Arial;margin:0}}

    .container {{
        max-width:500px;
        margin:auto;
        padding:10px;
    }}

    .header {{
        background:#111;
        color:white;
        padding:12px;
        border-radius:10px;
        text-align:center;
        margin-bottom:10px;
    }}

    .stats {{
        background:white;
        padding:10px;
        border-radius:10px;
        margin-bottom:10px;
    }}

    .match {{
        background:white;
        padding:12px;
        border-radius:10px;
        margin-bottom:10px;
        display:flex;
        justify-content:space-between;
    }}

    .score {{
        font-size:22px;
        font-weight:bold;
    }}

    .pred {{
        font-size:16px;
        font-weight:bold;
    }}

    .flag {{
        margin-right:6px;
    }}

    .green {{color:green}}
    .orange {{color:orange}}
    .red {{color:red}}

    a {{color:white;text-decoration:none}}

    </style>

    </head>

    <body>

    <div class="container">

    <div class="header">
        <a href="/">⬅ Powrót</a>
    </div>

    <div class="header">
        {name} • {total} pkt
    </div>

    <div class="stats">
        🎯 {hits} | ⚖️ {partial} | ❌ {miss} | 📊 {accuracy}%
    </div>

    {matches_html}

    </div>

    </body>
    </html>
    """
