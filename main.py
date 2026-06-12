from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
import pandas as pd

app = FastAPI()
templates = Jinja2Templates(directory="templates")

FILE = "tabela zbiorcza z rankingiem.xlsx"


# 🔽 POBIERANIE WYNIKÓW Z EXCELA
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


# 🔽 LICZENIE PUNKTÓW
def calc_points(pred, actual):
    if not isinstance(pred, str):
        return 0

    try:
        pred = pred.replace("-", ":")
        p1, p2 = map(int, pred.split(":"))
        a1, a2 = actual

        # dokładny wynik
        if p1 == a1 and p2 == a2:
            return 3

        # zwycięzca
        if (p1 - p2) * (a1 - a2) > 0:
            return 1

        # remis
        if p1 == p2 and a1 == a2:
            return 1

    except:
        return 0

    return 0


# 🔽 RANKING
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

        ranking.append({
            "gracz": str(sheet),
            "punkty": int(total)
        })

    # zabezpieczenie (na wypadek błędów danych)
    ranking = [r for r in ranking if isinstance(r, dict)]

    ranking.sort(key=lambda x: x["punkty"], reverse=True)
    return ranking


@app.get("/")
def home(request: Request):
    ranking = get_ranking()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "ranking": ranking
    })
``