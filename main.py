from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd
import requests

app = FastAPI()

FILE = "tabela zbiorcza z rankingiem.xlsx"


# ✅ FLAGI (obrazki)
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

    team = team.lower()

    for key in mapping:
        if key in team:
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


# ✅ LIVE API (SAFE)
def get_live():
    try:
        res = requests.get(
            "https://sportscore.com/api/widget/matches/?sport=football",
            timeout=5
        )

        if res.status_code != 200:
            return []

        data = res.json()

        # 🔥 filtr bezpieczeństwa
        return [m for m in data.get("matches", []) if isinstance(m, dict)]

    except:
        return []


# ✅ SAFE MATCH
def get_live_match(match_name, matches):
    if not isinstance(match_name, str):
        return None

    match_name = match_name.lower()

    for m in matches:

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

            if isinstance(hs, int) and isinstance(as_, int):
                return {
                    "score": (hs, as_),
                    "minute": m.get("minute") or "",
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
    xls = pd.ExcelFile(FILE)
    results = get_results()
    live_matches = get_live()

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

            live_data = get_live_match(match, live_matches)
            if live_data:
                actual = live_data["score"]

            if actual:
                total += calc_points(pred, actual)

        ranking.append({
            "name": sheet,
            "pts": total
        })

    ranking.sort(key=lambda x: x["pts"], reverse=True)
    return ranking


# ✅ HOME (✅ POPRAWIONE LINKI)
@app.get("/", response_class=HTMLResponse)
def home():
    data = get_ranking()

    rows = ""

    for i, r in enumerate(data, 1):
        rows += f"""
        <tr>
            <td>{i}</td>
            <td><a href="/gracz/{r['name']}">{r['name']}</a></td>
            <td class="pts">{r['pts']}</td>
        </tr>
        """

    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width">
    <style>
    body {{font-family:Arial;background:#eee;margin:0}}
    .box {{max-width:500px;margin:auto;padding:10px}}
    table {{
        width:100%;
        background:white;
        border-radius:10px;
    }}
    td {{padding:12px}}
    a {{text-decoration:none;color:black;font-weight:bold}}
    .pts {{font-size:18px;font-weight:bold}}
    </style>
    </head>

    <body>
    <div class="box">
    <h3>🏆 Ranking</h3>
    <table>{rows}</table>
    </div>
    </body>
    </html>
    """


# ✅ PLAYER (FLASH SCORE STYLE)
@app.get("/gracz/{name}", response_class=HTMLResponse)
def player(name: str):

    xls = pd.ExcelFile(FILE)
    df = pd.read_excel(xls, name)

    results = get_results()
    live_matches = get_live()

    rows = ""
    total = 0

    for _, row in df.iterrows():

        match = row.get("Mecz")
        pred = row.get("Typ")

        if not isinstance(match, str):
            continue

        actual = results.get(match.strip())
        live_data = get_live_match(match, live_matches)

        is_live = False
        minute = ""

        if live_data:
            actual = live_data["score"]
            is_live = True
            minute = live_data["minute"]

        if not actual:
            continue

        pts = calc_points(pred, actual)
        total += pts

        t1, t2 = [x.strip() for x in match.split("-")]

        rows += f"""
        <div class="match">
            <div class="teams">
                <div>{get_flag(t1)} {t1}</div>
                <div>{get_flag(t2)} {t2}</div>
            </div>

            <div class="score">
                {actual[0]}:{actual[1]}
                <div class="live">{'🔴 '+str(minute) if is_live else ''}</div>
                <div class="pts">{pts} pkt</div>
            </div>
        </div>
        """

    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width">
    <style>

    body {{background:#f2f2f2;font-family:Arial;margin:0}}

    .box {{max-width:500px;margin:auto;padding:10px}}

    .header {{
        background:#111;
        color:white;
        padding:14px;
        border-radius:10px;
        margin-bottom:10px;
    }}

    .big {{
        text-align:center;
        font-size:22px;
        font-weight:bold;
    }}

    .match {{
        background:white;
        padding:14px;
        border-radius:12px;
        margin-bottom:10px;
        display:flex;
        justify-content:space-between;
    }}

    .score {{
        text-align:right;
        font-size:22px;
        font-weight:bold;
    }}

    .live {{color:red;font-size:13px}}

    .pts {{color:#007bff;font-size:15px}}

    .flag {{margin-right:6px}}

    a {{color:white;text-decoration:none}}

    </style>
    </head>

    <body>

    <div class="box">

        <div class="header">
            <a href="/">⬅ Powrót</a>
        </div>

        <div class="header big">
            {name} • {total} pkt
        </div>

        {rows}

    </div>

    </body>
    </html>
    """
