from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd
import requests
from difflib import SequenceMatcher

app = FastAPI()
FILE = "tabela zbiorcza z rankingiem.xlsx"


# ===== NORMALIZACJA (fuzzy) =====
def normalize(text):
    if not isinstance(text, str):
        return ""
    return (
        text.lower()
        .replace("ł", "l")
        .replace("ś", "s")
        .replace("ą", "a")
        .replace("ę", "e")
        .replace("ż", "z")
        .replace("ź", "z")
        .replace("ó", "o")
        .replace("ń", "n")
    )


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


# ===== FLAGI =====
def get_flag(team):
    mapping = {
        "polska": "pl",
        "niemcy": "de",
        "meksyk": "mx",
        "rpa": "za",
        "korea poludniowa": "kr",
        "czechy": "cz"
    }

    team_norm = normalize(team)

    for k in mapping:
        if k in team_norm:
            return f'<img src="https://flagcdn.com/24x18/{mapping[k]}.png" class="flag">'
    return ""


# ===== WYNIKI =====
def get_results():
    df = pd.read_excel(FILE, sheet_name="Wyniki")
    results = {}

    for _, r in df.iterrows():
        match = r.get("Mecz")
        g1 = r.get("Gol 1")
        g2 = r.get("Gol 2")

        if isinstance(match, str) and pd.notna(g1) and pd.notna(g2):
            results[match.strip()] = (int(g1), int(g2))

    return results


# ===== LIVE =====
def get_live():
    try:
        res = requests.get(
            "https://sportscore.com/api/widget/matches/?sport=football",
            timeout=5
        )
        data = res.json()
        return [m for m in data.get("matches", []) if isinstance(m, dict)]
    except:
        return []


# ===== AUTO DOPASOWANIE ✅ =====
def get_live_match(match_name, matches):

    if not isinstance(match_name, str):
        return None, ""

    match_norm = normalize(match_name)

    for m in matches:
        if not isinstance(m, dict):
            continue

        home = m.get("home")
        away = m.get("away")

        if not isinstance(home, dict) or not isinstance(away, dict):
            continue

        h = normalize(home.get("name"))
        a = normalize(away.get("name"))

        if not h or not a:
            continue

        # 🔥 fuzzy matching
        if similar(h, match_norm) > 0.4 and similar(a, match_norm) > 0.4:
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

    html = ""
    total, hits, partial, miss = 0, 0, 0, 0

    for _, r in df.iterrows():

        match = r.get("Mecz")
        typ = r.get("Typ")

        if not isinstance(match, str):
            continue

        actual = results.get(match.strip())
        live_score, minute = get_live_match(match, live)

        is_live = False

        if live_score:
            actual = live_score
            is_live = True

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

        live_class = "live-match" if is_live else ""

        html += f"""
        <div class="card {live_class}">

            <div>
                <div>{get_flag(t1)} {t1}</div>
                <div>{get_flag(t2)} {t2}</div>
            </div>

            <div class="right">
                <div class="score">{actual[0]}:{actual[1]}</div>
                <div class="pred">TYP {typ}</div>
                <div class="live">{minute if is_live else ""}</div>
                <div style="color:{col}">{sym} {pts} pkt</div>
            </div>

        </div>
        """

    total_matches = hits + partial + miss
    acc = int(hits / total_matches * 100) if total_matches else 0

    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width">

    <style>

    body {{background:#eee;font-family:Arial;margin:0}}

    .box {{max-width:500px;margin:auto;padding:10px}}

    .header {{
        background:black;
        color:white;
        padding:10px;
        border-radius:10px;
        margin-bottom:10px;
        text-align:center;
    }}

    .card {{
        background:white;
        padding:12px;
        border-radius:10px;
        margin-bottom:10px;
        display:flex;
        justify-content:space-between;
    }}

    .live-match {{
        background:#ffeaea;
        border:1px solid red;
    }}

    .score {{font-size:22px;font-weight:bold}}
    .pred {{font-size:16px;font-weight:bold}}
    .live {{color:red;font-weight:bold}}

    .flag {{margin-right:6px}}

    a {{color:white;text-decoration:none}}

    </style>

    </head>

    <body>

    <div class="box">

        <div class="header">
            <a href="/">⬅ Powrót</a>
        </div>

        <div class="header">
            {name} • {total} pkt
        </div>

        <div class="card">
            🎯 {hits} | ⚖️ {partial} | ❌ {miss} | 📊 {acc}%
        </div>

        {html}

    </div>

    </body>
    </html>
    """
