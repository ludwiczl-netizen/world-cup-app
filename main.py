from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd
import requests

app = FastAPI()

FILE = "tabela zbiorcza z rankingiem.xlsx"


# ✅ FLAGI (obrazki – działają wszędzie)
def get_flag_img(team):
    mapping = {
        "polska": "pl",
        "niemcy": "de",
        "brazylia": "br",
        "usa": "us",
        "francja": "fr",
        "hiszpania": "es",
        "argentyna": "ar",
        "anglia": "gb",
        "włochy": "it",
        "meksyk": "mx",
        "rpa": "za",
        "korea południowa": "kr",
        "czechy": "cz"
    }

    if not isinstance(team, str):
        return ""

    name = team.lower()

    for k in mapping:
        if k in name:
            return f'<img src="https://flagcdn.com/24x18/{mapping[k]}.png" style="margin-right:6px;">'

    return ""


# ✅ EXCEL
def get_results():
    df = pd.read_excel(FILE, sheet_name="Wyniki")
    results = {}

    for _, row in df.iterrows():
        match = row.get("Mecz")
        g1 = row.get("Gol 1")
        g2 = row.get("Gol 2")

        if isinstance(match, str) and pd.notna(g1) and pd.notna(g2):
            results[match.strip()] = (int(g1), int(g2))

    return results


# ✅ LIVE API (SAFE)
def get_live_scores():
    try:
        url = "https://sportscore.com/api/widget/matches/?sport=football"
        res = requests.get(url, timeout=5)

        if res.status_code != 200:
            return []

        data = res.json()

        matches = data.get("matches", [])

        # 🔥 tylko dicty
        return [m for m in matches if isinstance(m, dict)]

    except:
        return []


# ✅ SAFE LIVE MATCH
def find_live_score(match_name, live_matches):
    if not isinstance(match_name, str):
        return None

    match_name = match_name.lower()

    for m in live_matches:

        if not isinstance(m, dict):
            continue

        home_data = m.get("home")
        away_data = m.get("away")

        if not isinstance(home_data, dict) or not isinstance(away_data, dict):
            continue

        home = home_data.get("name")
        away = away_data.get("name")

        if not isinstance(home, str) or not isinstance(away, str):
            continue

        if home.lower() in match_name and away.lower() in match_name:

            hs = home_data.get("score")
            as_ = away_data.get("score")
            minute = m.get("minute") or "LIVE"

            if isinstance(hs, int) and isinstance(as_, int):
                return {
                    "score": (hs, as_),
                    "minute": minute,
                    "live": True
                }

    return None


# ✅ PUNKTY
def calc_points(pred, actual):
    if not isinstance(pred, str) or not actual:
        return 0

    try:
        p1, p2 = map(int, pred.replace("-", ":").split(":"))
        a1, a2 = actual

        if p1 == a1 and p2 == a2:
            return 3
        if (p1 - p2) * (a1 - a2) > 0:
            return 1
        if p1 == p2 and a1 == a2:
            return 1

    except:
        return 0

    return 0


# ✅ RANKING
def get_ranking():
    xls = pd.ExcelFile(FILE, engine="openpyxl")
    results = get_results()
    live_matches = get_live_scores()

    ranking = []

    for sheet in xls.sheet_names:
        if sheet in ["Wyniki", "Ranking"]:
            continue

        df = pd.read_excel(xls, sheet)

        total = 0

        for _, row in df.iterrows():
            match = row.get("Mecz")
            pred = row.get("Typ")

            if not isinstance(match, str):
                continue

            actual = results.get(match.strip())

            live = find_live_score(match, live_matches)
            if live:
                actual = live["score"]

            if actual:
                total += calc_points(pred, actual)

        ranking.append({
            "gracz": sheet,
            "pkt": total
        })

    ranking.sort(key=lambda x: x["pkt"], reverse=True)
    return ranking


# ✅ HOME (link działa!)
@app.get("/", response_class=HTMLResponse)
def home():
    ranking = get_ranking()

    rows = ""

    for i, r in enumerate(ranking, 1):
        rows += f"""
        <tr>
            <td>{i}</td>
            <td><a href="/gracz/{r['gracz']}">{r['gracz']}</a></td>
            <td><b>{r['pkt']}</b></td>
        </tr>
        """

    return f"""
    <html>
    <head>
    <style>
    body {{ font-family: Arial; background:#f4f4f4 }}
    table {{ background:white; border-radius:10px }}
    </style>
    </head>

    <body>

    <h2>🏆 Ranking</h2>

    <table cellpadding="10">
    <tr><th>#</th><th>Gracz</th><th>Punkty</th></tr>
    {rows}
    </table>

    </body>
    </html>
    """


# ✅ FLASHSCORE VIEW
@app.get("/gracz/{name}", response_class=HTMLResponse)
def player(name: str):
    xls = pd.ExcelFile(FILE, engine="openpyxl")
    df = pd.read_excel(xls, name)

    results = get_results()
    live_matches = get_live_scores()

    matches_html = ""
    total = 0

    for _, row in df.iterrows():
        match = row.get("Mecz")
        pred = row.get("Typ")

        if not isinstance(match, str):
            continue

        actual = results.get(match.strip())
        live = find_live_score(match, live_matches)

        is_live = False
        minute = ""

        if live:
            actual = live["score"]
            is_live = True
            minute = live["minute"]

        if not actual:
            continue

        pts = calc_points(pred, actual)
        total += pts

        t1, t2 = [x.strip() for x in match.split("-")]

        matches_html += f"""
        <div class="match">

            <div class="teams">
                <div>{get_flag_img(t1)}{t1}</div>
                <div>{get_flag_img(t2)}{t2}</div>
            </div>

            <div class="score">
                {actual[0]}:{actual[1]}
                <div class="live">{'🔴 '+str(minute) if is_live else ''}</div>
                <div class="points">{pts} pkt</div>
            </div>

        </div>
        """

    return f"""
    <html>
    <head>

    <style>
    body {{ background:#eee; font-family:Arial }}

    .container {{ max-width:500px; margin:auto }}

    .header {{
        background:black;
        color:white;
        padding:15px;
        margin-bottom:10px;
    }}

    .match {{
        background:white;
        margin-bottom:10px;
        padding:10px;
        border-radius:10px;
        display:flex;
        justify-content:space-between;
    }}

    .teams div {{
        margin-bottom:5px;
    }}

    .score {{
        text-align:right;
        font-weight:bold;
    }}

    .live {{
        color:red;
        font-size:12px;
    }}

    .points {{
        font-size:11px;
        color:gray;
    }}

    a {{ color:white; text-decoration:none }}

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

    {matches_html}

    </div>

    </body>
    </html>
    """
