import pandas as pd
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()



@app.get("/", response_class=HTMLResponse)
def home():

    df = pd.read_excel("tabela zbiorcza z rankingiem.xlsx")

    html = "<h2>🏆 Ranking</h2>"
    html += "<table border='1'>"
    html += "<tr><th>#</th><th>Gracz</th><th>Pkt</th></tr>"

    for i, row in df.iterrows():
        html += "<tr>"
        html += "<td>" + str(i+1) + "</td>"
        html += "<td>" + str(row["Gracz"]) + "</td>"
        html += "<td>" + str(row["Pkt"]) + "</td>"
        html += "</tr>"

    html += "</table>"

    return html

@app.get("/test")
def test():
    return "klik działa ✅"
