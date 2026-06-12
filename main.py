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

    for k in mapping:
        if k in team.lower():
            return f'<img src="https://flagcdn.com/24x18/{mapping[k]}.png" class="flag">'
    return ""


# ✅ EXCEL
def get_results():
    df = pd.read_excel(FILE, sheet_name="Wyniki")
    results = {}

    for _, r in df.iterrows():
        if isinstance(r.get("Mecz"), str) and pd.notna(r.get("Gol 1")):
            results[r["Mecz"].strip()] = (int(r["Gol 1"]), int(r["Gol 2"]))

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
        return [m for m in data.get("matches", []) if isinstance(m, dict)]

    except:
        return []


# ✅ LIVE MATCH
def get_live_match(name, matches):
    if not isinstance(name, str):
        return None

    name = name.lower()

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

        if h.lower() in name and a.lower() in name:
            hs = home.get("score")
            as_ = away.get("score")

            if isinstance(hs, int) and isinstance(as_, int):
                return {
                    "score": (hs, as_),
                    "minute": m.get("minute") or "",
                    "live": True
                }

    return None


# ✅ PUNKTY + KOLOR + SYMBOL
def get_points(pred, actual):
    try:
        p1, p2 = map(int, str(pred).replace("-", ":").split(":"))
        a1, a2 = actual

        if p1 == a1 and p2 == a2:
            return 3, "✅", "green"
        if (p1 - p2) * (a1 - a2) > 0:
            return 1, "➖", "orange"
        if p1 == p2 and a1 == a2:
            return 1, "➖", "orange"
        return 0, "❌", "red"

    except:
        return 0, "❌", "red"


# ✅ RANKING
def get_ranking():
    xls = pd.ExcelFile(FILE)
    results = get_results()
    live = get_live()

    out = []

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
                pts, _, _ = get_points(typ, actual)
                total += pts

        out.append({"name": sheet, "pts": total})

    out.sort(key=lambda x: x["pts"], reverse=True)
    return out


# ✅ NAVBAR
def navbar():
    return """
    <div class="nav">
        <a href="/">🏆 Ranking</a>
    </div>
    """


# ✅ STRONA GŁÓWNA
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

    table {{width:100%;background:white;border-radius:10px}}

    td {{padding:12px}}

    .pts {{font-weight:bold;font-size:18px}}

    a {{text-decoration:none;color:black;font-weight:bold}}

    .nav {{
        position:fixed;
        bottom:0;
        width:100%;
        background:#111;
        padding:10px;
        text-align:center;
    }}

    .nav a {{color:white;text-decoration:none}}

    </style>
    </head>

    <body>

    <div class="box">
    <h3>🏆 Ranking</h3>
    <table>{rows}</table>
    </div>

    {navbar()}

    </body>
    </html>
    """


# ✅ SZCZEGÓŁY GRACZA
@app.get("/gracz/{name}", response_class=HTMLResponse)
def player(name: str):

    xls = pd.ExcelFile(FILE)
    df = pd.read_excel(xls, name)

    results = get_results()
    live = get_live()

    rows = ""
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

        pts, symbol, color = get_points(typ, actual)
        total += pts

        t1, t2 = [x.strip() for x in match.split("-")]

        rows += f"""
        <div class="match">

            <div>
                <div>{get_flag(t1)} {t1}</div>
                <div>{get_flag(t2)} {t2}</div>
            </div>

            <div class="score">
                <div class="real">{actual[0]}:{actual[1]}</div>
                <div class="pred">typ: {typ}</div>
                <div class="live">{'🔴 '+str(minute) if is_live else ''}</div>
                <div class="pts {color}">{symbol} {pts} pkt</div>
            </div>

        </div>
        """

    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width">

    <style>
    body {{background:#f2f2f2;font-family:Arial;margin:0}}

    .box {{max-width:500px;margin:auto;padding:10px 10px 60px}}

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

    .real {{font-size:22px;font-weight:bold}}

    .pred {{font-size:12px;color:gray}}

    .live {{color:red;font-size:12px}}

    .green {{color:green}}
    .orange {{color:orange}}
    .red {{color:red}}

    .nav {{
        position:fixed;
        bottom:0;
        width:100%;
        background:#111;
        padding:10px;
        text-align:center;
    }}

    .nav a {{color:white;text-decoration:none}}

    .flag {{margin-right:6px}}

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

    {navbar()}

    </body>
    </html>
    """
