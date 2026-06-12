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
        if isinstance(row.get("Mecz"), str) and pd.notna(row.get("Gol 1")) and pd.notna(row.get("Gol 2")):
            results[row["Mecz"]] = (int(row["Gol 1"]), int(row["Gol 2"]))

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

        ranking.append({
            "gracz": str(sheet),
            "punkty": int(total)
        })

    ranking.sort(key=lambda x: x["punkty"], reverse=True)
    return ranking


@app.get("/")
def home(request: Request):
    raw_ranking = get_ranking()

    ranking = [
        {
            "gracz": str(r["gracz"]),
            "punkty": int(r["punkty"])
        }
        for r in raw_ranking
        if isinstance(r, dict) and "gracz" in r and "punkty" in r
    ]

    return templates.TemplateResponse("index.html", {
        "request": request,
        "ranking": ranking
    })
