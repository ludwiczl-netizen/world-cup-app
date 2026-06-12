from fastapi import FastAPIfrom fastapi import FastAPI()

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
            code = mapping[k]
            return f'<img src="https://flagcdn.com/24x18/{code}.png" class="flag">'
    return ""


# ===== EXCEL =====
def get_results():
    df = pd.read_excel(FILE, sheet_name="Wyniki")
    results = {}

    for _, r in df.iterrows():
        if isinstance(r.get("Mecz"), str) and pd.notna(r.get("Gol 1")):
            results[r["Mecz"].strip()] = (int(r["Gol 1"]), int(r["Gol 2"]))

    return results


# ===== LIVE =====
def get_live():
    try:
        r = requests.get("https://sportscore.com/api/widget/matches/?sport=football", timeout=5)
        data = r.json()
        return [m for m in data.get("matches", []) if isinstance(m, dict)]
    except:
        return []


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


# ===== RANKING (z tie-break ✅)
def get_ranking():
    xls = pd.ExcelFile(FILE)
    results = get_results()
    live = get_live()

    out = []

    for sheet in xls.sheet_names:
        if sheet in ["Wyniki", "Ranking", "Typy_Zbiorcze", "Instrukcja"]:
            continue

        df = pd.read_excel(xls, sheet)
        total = 0
        hits = 0

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

                if pts == 3:
                    hits += 1

        out.append({
            "name": sheet,
            "pts": total,
            "hits": hits
        })

    # ✅ sortowanie: pkt -> trafienia
    out.sort(key=lambda x: (x["pts"], x["hits"]), reverse=True)

    return out


# ===== HOME =====
@app.get("/", response_class=HTMLResponse)
def home():
    data = get_ranking()

    rows = ""

    for i, r in enumerate(data, 1):
        rows += f"""
        <tr>
            <td>{i}</td>
            <td>gracz/{r['name']}">{r['name']}</a></td>
            <td><b>{r['pts']}</b></td>
            <td style="color:green">🎯 {r['hits']}</td>
        </tr>
        """

    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width">
    <style>

    body {{background:#f4f4f4;font-family:Arial;margin:0}}

    .container {{max-width:500px;margin:auto;padding:10px}}

    table {{
        width:100%;
        background:white;
        border-radius:12px;
    }}

    td {{padding:12px}}

    a {{
        text-decoration:none;
        color:black;
        font-weight:bold;
    }}

    </style>
    </head>

    <body>

    <div class="container">

    <h3>🏆 Ranking</h3>

    <table>
        <tr>
            <th>#</th>
            <th>Gracz</th>
            <th>Pkt</th>
            <th>Trafione</th>
        </tr>
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

    rows = ""
    total = 0

    hits = 0
    partial = 0
    miss = 0

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

        pts, sym, col = get_points(typ, actual)
        total += pts

        # ✅ statystyki
        if pts == 3:
            hits += 1
        elif pts == 1:
            partial += 1
        else:
            miss += 1

        t1, t2 = [x.strip() for x in match.split("-")]

        rows += f"""
        <div class="card">

            <div>
                <div>{get_flag(t1)} {t1}</div>
                <div>{get_flag(t2)} {t2}</div>
            </div>

            <div class="right">
                <div class="score">{actual[0]}:{actual[1]}</div>
                <div class="pred">TYP {typ}</div>
                <div class="live">{'🔴 '+str(minute) if is_live else ''}</div>
                <div class="pts {col}">{sym} {pts} pkt</div>
            </div>

        </div>
        """

    total_matches = hits + partial + miss
    accuracy = int((hits / total_matches) * 100) if total_matches else 0

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
        padding:14px;
        border-radius:12px;
        margin-bottom:10px;
        text-align:center;
        font-size:20px;
    }}

    .stats {{
        background:white;
        border-radius:12px;
        padding:12px;
        margin-bottom:10px;
    }}

    .card {{
        background:white;
        padding:14px;
        border-radius:12px;
        margin-bottom:10px;
        display:flex;
        justify-content:space-between;
    }}

    .score {{
        font-size:26px;
        font-weight:bold;
    }}

    .pred {{
        font-size:18px;
        font-weight:bold;
    }}

    .green {{color:green}}
    .orange {{color:orange}}
    .red {{color:red}}

    .flag {{
        width:24px;
        margin-right:6px;
    }}

    a {{
        color:white;
        text-decoration:none;
    }}

    </style>
    </head>

    <body>

    <div class="container">

        <div class="header">
            /⬅ Powrót</a>
        </div>

        <div class="header">
            {name} • {total} pkt
        </div>

        <div class="stats">
            🎯 Trafione: <b>{hits}</b><br>
            ⚖️ 1 pkt: <b>{partial}</b><br>
            ❌ Błędne: <b>{miss}</b><br>
            📊 Skuteczność: <b>{accuracy}%</b>
        </div>

        {rows}

    </div>

    </body>
    </html>

from fastapi.responses import HTMLResponse
import pandas as pd
import requests
