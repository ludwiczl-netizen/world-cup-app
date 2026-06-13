from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd
import urllib.parse


app = FastAPI()




# ===== HOME (RANKING) =====
@app.get("/", response_class=HTMLResponse)
def home():

    df = pd.read_excel("tabela zbiorcza z rankingiem.xlsx")
    df.columns = df.columns.str.strip()

    html = "<h2>🏆 Ranking</h2>"
    html += "<table border='1'>"
    html += "<tr><th>#</th><th>Gracz</th><th>Punkty</th></tr>"

    for i, row in df.iterrows():

        name = str(row["Gracz"])
        safe = urllib.parse.quote(name)

        html += "<tr>"
        html += "<td>" + str(i+1) + "</td>"
        html += "<td><a href='/gracz/" + safe + "'>" + name + "</a></td>"
        html += "<td>" + str(row["Punkty"]) + "</td>"
        html += "</tr>"

    html += "</table>"

    return html


# ===== STRONA GRACZA =====

@app.get("/gracz/{name}", response_class=HTMLResponse)
def player(name: str):

    name = urllib.parse.unquote(name)

    xls = pd.ExcelFile("tabela zbiorcza z rankingiem.xlsx")

    # jeśli brak arkusza gracza
    if name not in xls.sheet_names:
        return "Brak danych dla gracza"

    df = pd.read_excel(xls, name)
    df.columns = df.columns.str.strip()

    html = "<h2>" + name + "</h2>"
    html += "<table border='1'>"
    html += "<tr><th>Mecz</th><th>Typ</th></tr>"

    for _, row in df.iterrows():

        mecz = str(row.get("Mecz", ""))
        typ = str(row.get("Typ", ""))

        if mecz != "nan":

            html += "<tr>"
            html += "<td>" + mecz + "</td>"
            html += "<td>" + typ + "</td>"
            html += "</tr>"

    html += "</table>"
    html += "<br><a href='/'>⬅ Powrót</a>"

    return html
