from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd
import requests

app = FastAPI()

FILE = "tabela zbiorcza z rankingiem.xlsx"


# ✅ EXCEL (fallback)
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

        if res.status_code != 200:
            return []

        data = res.json()
        matches = data.get("matches", [])

        return [m for m in matches if isinstance(m, dict)]
    except:
        return []


# ✅ SMART MATCH + minuta
def find_live_score(match_name, live_matches):
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

        home_l = home.lower()
        away_l = away.lower()

        if home_l in match_name and away_l in match_name:
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
    if not isinstance(pred, str):
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
    results_excel = get_results()
    live_matches = get_live_scores()

    ranking = []
    ignore = ["Wyniki", "Ranking", "Typy_Zbiorcze", "Instrukcja"]

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

            match_clean = match.strip()

            actual = results_excel.get(match_clean)

            live_data = find_live_score(match_clean, live_matches)
            if live_data:
                actual = live_data["score"]

            if actual:
                total += calc_points(pred, actual)

        ranking.append({
            "gracz": str(sheet),
            "punkty": int(total)
        })

    ranking.sort(key=lambda x: x["punkty"], reverse=True)
    return ranking


# ✅ STRONA GŁÓWNA (NAPRAWIONE LINKI!!!)
@app.get("/", response_class=HTMLResponse)
def home():
    ranking = get_ranking()

    rows = ""

    for i, r in enumerate(ranking, 1):
        leader = "leader" if i == 1 else ""

        rows += f"""
        <tr class="{leader}">
            <td>{i}</td>
            <td><a href="/gracz/{r['gracz']}">{r['gracz']}</a></td>
            <td><b>{r['punkty']}</b></td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta http-equiv="refresh" content="30">
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

    <style>
    body {{ background:#f4f6f9; }}
    .card {{
        background:white;
        padding:20px;
        border-radius:15px;
        box-shadow:0 4px 15px rgba(0,0,0,0.1);
    }}
    .leader {{
        background:gold;
        font-weight:bold;
    }}
    </style>
    </head>

    <body class="p-3">
    <div class="card">

    <h3>🏆 Ranking LIVE</h3>

    <table class="table">
    <thead>
    <tr><th>#</th><th>Gracz</th><th>Punkty</th></tr>
    </thead>

    <tbody>
    {rows}
    </tbody>

    </table>

    </div>
    </body>
    </html>
    """

    return html


# ✅ SZCZEGÓŁY GRACZA (LIVE 🔴 + minuta)
@app.get("/gracz/{name}", response_class=HTMLResponse)
def player_details(name: str):
    xls = pd.ExcelFile(FILE, engine="openpyxl")
    results_excel = get_results()
    live_matches = get_live_scores()

    df = pd.read_excel(xls, name)

    rows = ""
    total = 0

    for _, row in df.iterrows():
        match = row.get("Mecz")
        pred = row.get("Typ")

        if not isinstance(match, str):
            continue

        match_clean = match.strip()

        actual = results_excel.get(match_clean)
        live_data = find_live_score(match_clean, live_matches)

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

        emoji = "✅" if pts == 3 else "➖" if pts == 1 else "❌"
        color = "red" if is_live else "black"

        rows += f"""
        <tr style="color:{color}; font-weight:{'bold' if is_live else 'normal'}">
            <td>{match}</td>
            <td>{pred}</td>
            <td>{actual[0]}:{actual[1]}</td>
            <td>{pts} {emoji}</td>
            <td>{"⏱ " + str(minute) if is_live else ""}</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>

    <body class="p-3">

    <a href="/">⬅ Powrót</a>

    <h2>{name}</h2>
    <h4>Punkty: {total}</h4>

    <table class="table table-striped">
    <thead>
    <tr>
        <th>Mecz</th>
        <th>Typ</th>
        <th>Wynik</th>
        <th>Punkty</th>
        <th>LIVE</th>
    </tr>
    </thead>

    <tbody>
    {rows}
    </tbody>
    </table>

    </body>
    </html>

    """

    return html

    return html
