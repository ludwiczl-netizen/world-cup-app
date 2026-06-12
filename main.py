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

    for key in mapping:
        if key in team.lower():
            code = mapping[key]
            return f'<img src="https://flagcdn.com/24x18/{code}.png" class="flag">'
    return ""


# ✅ EXCEL
def get_results():
    df = pd.read_excel(FILE, sheet_name="Wyniki")
    results = {}

    for _, row in df.iterrows():
        if isinstance(row.get("Mecz"), str) and pd.notna(row.get("Gol 1")):
            results[row["Mecz"].strip()] = (int(row["Gol 1"]), int(row["Gol 2"]))

    return results


# ✅ LIVE API (SAFE)
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


# ✅ MATCHING
def get_live_match(name, matches):
    if not isinstance(name, str):
        return None

    name = name.lower()

    for m in matches:
        if not isinstance(m, dict):
            continue

        home = m.get("home", {}).get("name", "")
        away = m.get("away", {}).get("name", "")

        if home.lower() in name and away.lower() in name:
            hs = m.get("home", {}).get("score")
            as_ = m.get("away", {}).get("score")

            if isinstance(hs, int) and isinstance(as_, int):
                return {
                    "score": (hs, as_),
                    "minute": m.get("minute", ""),
                    "live": True
                }

    return None


# ✅ PUNKTY
def points(pred, real):
    try:
        p1, p2 = map(int, str(pred).replace("-", ":").split(":"))
        r1, r2 = real

        if p1 == r1 and p2 == r2:
            return 3
        if (p1 - p2) * (r1 - r2) > 0:
            return 1
        if p1 == p2 and r1 == r2:
            return 1
    except:
        return 0

    return 0


# ✅ RANKING
def ranking():
    xls = pd.ExcelFile(FILE)
    results = get_results()
    live = get_live()

    res = []

    for sheet in xls.sheet_names:
        if sheet in ["Wyniki", "Ranking"]:
            continue

        df = pd.read_excel(xls, sheet)
        total = 0

        for _, r in df.iterrows():
            match = r.get("Mecz")
            typ = r.get("Typ")

            if not isinstance(match, str):
                continue

            actual = results.get(match.strip())
            live_data = get_live_match(match, live)

            if live_data:
                actual = live_data["score"]

            if actual:
                total += points(typ, actual)

        res.append({"name": sheet, "pts": total})

    res.sort(key=lambda x: x["pts"], reverse=True)
    return res


# ✅ HOME (NAPRAWIONE LINKI 🔥)
@app.get("/", response_class=HTMLResponse)
def home():
    data = ranking()

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

    .box {{
        max-width:500px;
        margin:auto;
        padding:10px;
    }}

    table {{
        width:100%;
        background:white;
        border-radius:10px;
        overflow:hidden;
    }}

    td {{
        padding:12px;
        font-size:16px;
    }}

    a {{
        text-decoration:none;
        color:black;
        font-weight:bold;
    }}

    .pts {{
        font-size:18px;
        font-weight:bold;
    }}
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


# ✅ PLAYER (FLASHCORE PRO 📱🔥)
@app.get("/gracz/{name}", response_class=HTMLResponse)
def player(name: str):
    xls = pd.ExcelFile(FILE)
    df = pd.read_excel(xls, name)

    results = get_results()
    live = get_live()

    html = ""
    total = 0

    for _, r in df.iterrows():
        match = r.get("Mecz")
        typ = r.get("Typ")

        if not isinstance(match, str):
            continue

        actual = results.get(match.strip())
        live_data = get_live_match(match, live)

        is_live = False
        minute = ""

        if live_data:
            actual = live_data["score"]
            is_live = True
            minute = live_data["minute"]

        if not actual:
            continue

        pts = points(typ, actual)
        total += pts

        t1, t2 = [x.strip() for x in match.split("-")]

        html += f"""
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
        padding:15px;
        border-radius:10px;
        margin-bottom:10px;
    }}

    .big {{
        font-size:22px;
        text-align:center;
        font-weight:bold;
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

    .teams div {{margin-bottom:6px;font-size:16px}}

    .score {{
        text-align:right;
        font-size:22px;
        font-weight:bold;
    }}

    .live {{color:red;font-size:13px}}

    .pts {{color:#007bff;font-size:15px;font-weight:bold}}

    .flag {{
        width:24px;
        margin-right:6px;
    }}

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

        {html}

    </div>

    </body>

    </html>
