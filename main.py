from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
import pandas as pd

app = FastAPI()
templates = Jinja2Templates(directory="templates")

FILE = "tabela zbiorcza z rankingiem.xlsx"


def get_results():
    df = pd.read_excel(FILE, sheet_name="Wyniki")
    results = {}

    for _, row in df.iterrows():
        match = row.get("Mecz")
        g1 = row.get("Gol 1")
        g2 = row.get("Gol 2")

        if isinstance(match, str) and pd.notna(g1) and pd.notna(g2):
            results[match] = (int(g1), int(g2))

    return results


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


def get_ranking():
    xls = pd.ExcelFile(FILE, engine="openpyxl")
    results = get_results()

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

        # ✅ TU jest klucz – zawsze dict
        item = {
            "gracz": str(sheet),
            "punkty": int(total)
        }

        ranking.append(item)

    # ✅ TU drugie zabezpieczenie
    clean = []
    for r in ranking:
        if type(r) is dict:
            if "gracz" in r and "punkty" in r:
                clean.append({
                    "gracz": str(r["gracz"]),
                    "punkty": int(r["punkty"])
                })

    clean.sort(key=lambda x: x["punkty"], reverse=True)

    return clean


from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def home():
    ranking = get_ranking()

    # ✅ generujemy HTML ręcznie (bez Jinja)
    rows = ""
    for i, r in enumerate(ranking, 1):
        rows += f"""
        <tr>
            <td>{i}</td>
            <td>{r['gracz']}</td>
            <td><b>{r['punkty']}</b></td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <title>Ranking MŚ 2026</title>
    </head>

    <body class="p-3">
    <h2>🏆 Ranking MŚ 2026</h2>

    <table class="table table-striped">
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
    </body>
    </html>
    """

    return html
