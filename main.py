from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd
import requests

app = FastAPI()

FILE = "tabela zbiorcza z rankingiem.xlsx"


# ✅ LIVE WYNIKI (TU PODŁĄCZYSZ PRAWDZIWE API)
def get_live_results():
    # 🔥 Na start dane przykładowe (działające)
    return {
        "USA-Brazylia": (2, 1),
        "Polska-Niemcy": (1, 1),
        "Hiszpania-Francja": (0, 2),
    }


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
    results = get_live_results()

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

            if isinstance(match, str) and match in results:
                total += calc_points(pred, results[match])

        ranking.append({
            "gracz": str(sheet),
            "punkty": int(total)
        })

    ranking.sort(key=lambda x: x["punkty"], reverse=True)
    return ranking


# ✅ STRONA GŁÓWNA (FLASHSCORE STYLE)
@app.get("/", response_class=HTMLResponse)
def home():
    ranking = get_ranking()

    rows = ""

    for i, r in enumerate(ranking, 1):
        class_name = "leader" if i == 1 else ""

        rows += f"""
        <tr class="{class_name}">
            <td>{i}</td>
            <td><a href="/gracz/{r['gracz']}" style="text-decoration:none; font-weight:600;">{r['gracz']}</a></td>
            <td><b>{r['punkty']}</b></td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>

    <!-- 🔥 AUTO REFRESH -->
    <meta http-equiv="refresh" content="60">

    <meta name="viewport" content="width=device-width, initial-scale=1">

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

    <title>Ranking MŚ 2026</title>

    <style>
    body {{
        background: #f4f6f9;
    }}

    .card {{
        border-radius: 16px;
        padding: 20px;
        background: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }}

    .leader {{
        background: linear-gradient(90deg, gold, #fff8c5);
        font-weight: bold;
    }}

    .table td {{
        vertical-align: middle;
        font-size: 16px;
    }}

    a {{
        color: black;
    }}

    a:hover {{
        color: #007bff;
    }}
    </style>

    </head>

    <body class="p-3">

    <div class="card">

    <h3 class="mb-3">🏆 Ranking MŚ 2026 (LIVE)</h3>

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
    results = get_live_results()

    df = pd.read_excel(xls, name)

    rows = ""
    total = 0

    for _, row in df.iterrows():
        match = row.get("Mecz")
        pred = row.get("Typ")

        if isinstance(match, str) and match in results:
            actual = results[match]
            pts = calc_points(pred, actual)
            total += pts

            # ✅ oznaczenia
            emoji = "✅" if pts == 3 else "➖" if pts == 1 else "❌"

            # ✅ kolor
            color = "green" if pts == 3 else "orange" if pts == 1 else "red"

            rows += f"""
            <tr>
                <td>{match.replace("-", " vs ")}</td>
                <td>{pred}</td>
                <td>{actual[0]}:{actual[1]}</td>
                <td style="color:{color}"><b>{pts}</b> {emoji}</td>
            </tr>
            """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>

    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <title>{name}</title>

    </head>

    <body class="p-3">

    <a href="/" class="btn btn-secondary mb-3">⬅ Powrót</a>

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
``
