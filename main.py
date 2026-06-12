from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd
import requests

app = FastAPI()

FILE = "tabela zbiorcza z rankingiem.xlsx"


# ✅ EXCEL (pewne dane)
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


# ✅ LIVE API (bezpieczne)
def get_live_scores():
    try:
        url = "https://sportscore.com/api/widget/matches/?sport=football"
        res = requests.get(url, timeout=5)
        data = res.json()

        matches = data.get("matches", [])

        # 🔥 filtr: tylko dict
        return [m for m in matches if isinstance(m, dict)]

    except:
        return []


# ✅ SMART DOPASOWANIE
def find_live_score(match_name, live_matches):
    match_name = match_name.lower()

    for m in live_matches:

        home = m.get("home", {}).get("name", "")
        away = m.get("away", {}).get("name", "")

        if not home or not away:
            continue

        home = home.lower()
        away = away.lower()

        if home in match_name and away in match_name:
            hs = m.get("home", {}).get("score")
            as_ = m.get("away", {}).get("score")

            if hs is not None and as_ is not None:
                return (int(hs), int(as_))

    return None


# ✅ LICZENIE PUNKTÓW
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

            # ✅ Excel wynik
            actual = results_excel.get(match_clean)

            # ✅ LIVE nadpisuje
            live_score = find_live_score(match_clean, live_matches)
            if live_score:
                actual = live_score

            if actual:
                total += calc_points(pred, actual)

        ranking.append({
            "gracz": str(sheet),
            "punkty": int(total)
        })

    ranking.sort(key=lambda x: x["punkty"], reverse=True)
    return ranking


# ✅ STRONA GŁÓWNA
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
    <meta http-equiv="refresh" content="60">
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
    a {{
        text-decoration:none;
        color:black;
    }}
    </style>
    </head>

    <body class="p-3">

    <div class="card">
    <h3>🏆 Ranking LIVE</h3>

    <table class="table">
    <thead>
    <tr>
        <th>#</th>
        <th>Gracz</th>
        <th>Punkty</th>
    </tr>
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


# ✅ SZCZEGÓŁY GRACZA
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
        live_score = find_live_score(match_clean, live_matches)

        if live_score:
            actual = live_score

        if not actual:
            continue

        pts = calc_points(pred, actual)
        total += pts

        emoji = "✅" if pts == 3 else "➖" if pts == 1 else "❌"

        rows += f"""
        <tr>
            <td>{match}</td>
            <td>{pred}</td>
            <td>{actual[0]}:{actual[1]}</td>
            <td><b>{pts}</b> {emoji}</td>
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

    <h2>👤 {name}</h2>
    <h4>🏆 Punkty: {total}</h4>

    <table class="table table-striped">

    <thead>
    <tr>
        <th>Mecz</th>
        <th>Typ</th>
        <th>Wynik</th>
        <th>Punkty</th>
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
