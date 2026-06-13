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

    html = "<h2>" + name + "</h2>"
    html += "<br>Tutaj będą szczegóły gracza"
    html += "<br>/⬅ Powrót</a>"

    return html
