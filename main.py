from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd
import requests

app = FastAPI()

FILE = "tabela zbiorcza z rankingiem.xlsx"


# ✅ FLAGI
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
            return f'<img src="https://flagcdn.com/24x18/{mapping[k]}.png" class="flag">'

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


# ✅ LIVE API
def get_live_scores():
    try:
        res = requests.get(
            "https://sportscore.com/api/widget/matches/?sport=football",
            timeout=5
        )

        if res.status_code != 200:
            return []

        data = res.json()
        matches = data.get("matches", [])

        return [m for m in matches if isinstance(m, dict)]

    except:
        return []


# ✅ SAFE LIVE
def find_live_score(match_name, live_matches):
    if not isinstance(match_name, str):
        return None

    match_name = match_name.lower()

    for m in live_matches:

        if not isinstance(m, dict):
            continue

        home = m.get("home")
        away = m.get("away")

        if not isinstance(home, dict) or not isinstance(away, dict):
            continue

        h = home.get("name")
        a = away.get("name")

        if not isinstance(h, str) or not isinstance(a, str):
            continue

        if h.lower() in match_name and a.lower() in match_name:

            hs = home.get("score")
            as_ = away.get("score")

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
    live = get_live_scores()

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

            live_data = find_live_score(match, live)
            if live_data:
                actual = live_data["score"]

            if actual:
                total += calc_points(pred, actual)

        ranking.append({"gracz": sheet, "pkt": total})

    ranking.sort(key=lambda x: x["pkt"], reverse=True)
    return ranking


# ✅ HOME (RESPONSIVE)
@app.get("/", response_class=HTMLResponse)
def home():
    ranking = get_ranking()

    rows = ""

    for i, r in enumerate(ranking, 1):
        rows += f"""
        <tr>
            <td>{i}</td>
            <td>/gracz/{r['gracz']}{r['gracz']}</a></td>
            <td class="pts">{r['pkt']}</td>
        </tr>
        """

    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
    body {{font-family:Arial;background:#eee;margin:0}}

    .container {{max-width:500px;margin:auto;padding:10px}}

    table {{
        width:100%;
        background:white;
        border-radius:10px;
        overflow:hidden;
    }}

    td {{padding:10px}}
    .pts {{font-weight:bold;font-size:18px}}

    a {{text-decoration:none;color:black}}
    </style>
    </head>

    <body>

    <div class="container">

    <h3>🏆 Ranking</h3>

    <table>
    {rows}
    </table>

    </div>

    </body>
    </html>
    """


# ✅ PLAYER (FLASHSCORE MOBILE PRO)
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
                <div class="team">{get_flag_img(t1)}{t1}</div>
                <div class="team">{get_flag_img(t2)}{t2}</div>
            </div>

            <div class="scoreBox">
                <div class="score">{actual[0]}:{actual[1]}</div>
                <div class="live">{'🔴 '+str(minute) if is_live else ''}</div>
                <div class="points">{pts} pkt</div>
            </div>

        </div>
        """

    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>

    body {{
        background:#f2f2f2;
        font-family:Arial;
        margin:0;
    }}

    .container {{
        max-width:600px;
        margin:auto;
        padding:10px;
    }}

    .header {{
        background:#111;
        color:white;
        padding:14px;
        border-radius:10px;
        margin-bottom:10px;
    }}

    .mainScore {{
        font-size:22px;
        font-weight:bold;
        text-align:center;
    }}

    .match {{
        background:white;
        padding:14px;
        border-radius:12px;
        margin-bottom:10px;
        display:flex;
        justify-content:space-between;
        align-items:center;
    }}

    .team {{
        display:flex;
        align-items:center;
        margin-bottom:6px;
        font-size:16px;
    }}

    .flag {{
        width:24px;
        margin-right:8px;
    }}

    .score {{
        font-size:24px;
        font-weight:bold;
    }}

    .points {{
        font-size:15px;
        color:#007bff;
        font-weight:bold;
    }}

    .live {{
        color:red;
        font-size:13px;
        font-weight:bold;
    }}

    a {{color:white;text-decoration:none}}

    </style>
    </head>

    <body>

    <div class="container">

        <div class="header">
            /⬅ Powrót</a>
        </div>

        <div class="header mainScore">
            {name} • {total} pkt
        </div>

        {matches_html}

    </div>

    </body>
    </html>
    """
