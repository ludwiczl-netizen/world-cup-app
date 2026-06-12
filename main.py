from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
import pandas as pd

app = FastAPI()
templates = Jinja2Templates(directory="templates")

EXCEL_FILE = "tabela zbiorcza z rankingiem.xlsx"


def calculate_points(predicted, actual):
    if not isinstance(predicted, str):
        return 0

    predicted = predicted.replace("-", ":")
    p1, p2 = map(int, predicted.split(":"))
    a1, a2 = actual

    # dokładny wynik
    if p1 == a1 and p2 == a2:
        return 3

    # zwycięzca / remis
    if (p1 - p2) * (a1 - a2) > 0:
        return 1

    if p1 == p2 and a1 == a2:
        return 1

    return 0


def generate_ranking():
    xls = pd.ExcelFile(EXCEL_FILE, engine="openpyxl")

    wyniki = pd.read_excel(xls, "Wyniki")

    results = {
        row["Mecz"]: (row["Gol 1"], row["Gol 2"])
        for _, row in wyniki.dropna().iterrows()
        if pd.notna(row["Gol 1"]) and pd.notna(row["Gol 2"])
    }

    ranking = []

    ignored = ["Wyniki", "Ranking", "Typy_Zbiorcze", "Instrukcja"]

    for sheet in xls.sheet_names:
        if sheet in ignored:
            continue

        df = pd.read_excel(xls, sheet)

        total = 0

        for _, row in df.iterrows():
            match = row.get("Mecz")
            pred = row.get("Typ")

            if match in results:
                total += calculate_points(pred, results[match])

        ranking.append({
            "gracz": sheet,
            "punkty": total
        })

    ranking.sort(key=lambda x: x["punkty"], reverse=True)

    return ranking


@app.get("/")
def home(request: Request):
    ranking = generate_ranking()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "ranking": ranking
    })