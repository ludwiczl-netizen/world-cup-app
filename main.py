from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd
import requests

app = FastAPI()

FILE = "tabela zbiorcza z rankingiem.xlsx"


# ✅ FLAGI (obrazki)
def get_flag_img(team_name):
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

    name = team_name.lower()

    for key in mapping:
        if key in name:
            code = mapping[key]
            return f'<img src="https://flagcdn.com/24x18/{code}.png" class="flag">'

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
        url = "https://sportscore.com/api/widget/matches/?sport=football"
        res = requests.get(url, timeout=5)
        data = res.json()

        return [m for m in data.get("matches", []) if isinstance(m, dict)]
    except:
        return []


# ✅ LIVE MATCH
def find_live_score(match_name, live_matches):
    match_name = match_name.lower()

    for m in live_matches:
        if not isinstance(m, dict):
            continue

        home = m.get("home", {}).get("name", "")
        away = m.get("away", {}).get("name", "")

        if home.lower() in match_name and away.lower() in match_name:
            hs = m.get("home", {}).get("score")
            as_ = m.get("away", {}).get("score")

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
    ignore = ["Wyniki", "Ranking"]

    for sheet in xls.sheet_names:
        if sheet in ignore:
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

        ranking.append({"gracz": sheet, "pkt": total})

    ranking.sort(key=lambda x: x["pkt"], reverse=True)
    return ranking


# ✅ STRONA GŁÓWNA
@app.get("/", response_class=HTMLResponse)
def home():
    ranking = get_ranking()

    rows = ""
    for i, r in enumerate(ranking, 1):
        rows += f"""
        <tr>
            <td>{i}</td>
            <td>{r['gracz']}</a></td>
            <td>{r['pkt']}</td>
        </tr>
        """

    return f"""
    <html>
    <body style="font-family:Arial">

    <h2>🏆 Ranking</h2>

    <table border="1" cellpadding="10">
    <tr><th>#</th><th>Gracz</th><th>Punkty</th></tr>
    {rows}
    </table>

    </body>
    </html>
    """


# ✅ FLASH SCORE UI
@app.get("/gracz/{name}", response_class=HTMLResponse)
def player_details(name: str):
    xls = pd.ExcelFile(FILE, engine="openpyxl")
    df = pd.read_excel(xls, name)

    results = get_results()
    live_matches = get_live_scores()

    matches_html = ""
    total = 0

    for _, row in df.iterrows():
        match = row["Mecz"]
        pred = row["Typ"]

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

        flag1 = get_flag_img(t1)
        flag2 = get_flag_img(t2)

        score = f"{actual[0]}:{actual[1]}"

        matches_html += f"""
        <div class="match">

            <div class="teams">

                <div class="team">{flag1}{t1}</div>
                <div class="team">{flag2}{t2}</div>

            </div>

            <div class="score">
                {score}
                <div class="live">{"🔴 "+str(minute)+"'" if is_live else ""}</div>
                <div class="pts">{pts} pkt</div>
            </div>

        </div>
        """

    return f"""
    <html>
    <head>
    <style>

    body {{background:#eee;font-family:Arial}}

    .container {{max-width:500px;margin:auto}}

    .header {{background:black;color:white;padding:15px}}

    .match {{
        background:white;
        margin:10px 0;
        padding:10px;
        border-radius:10px;
        display:flex;
        justify-content:space-between
    }}

    .team {{display:flex;align-items:center}}
    .flag {{margin-right:6px}}

    .score {{text-align:right;font-weight:bold}}
    .live {{color:red;font-size:12px}}
    .pts {{font-size:11px;color:gray}}

    </style>
    </head>

    <body>

    <div class="container">

    <div class="header">
        ⬅ Powrót
    </div>

    <div class="header">
        {name} • {total} pkt
    </div>

    {matches_html}

    </div>

    </body>
    </html>
    """
