from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()



@app.get("/", response_class=HTMLResponse)
def home():

    html = "<h2>🏆 Ranking</h2>"
    html += "<table border='1'>"
    html += "<tr><th>#</th><th>Gracz</th><th>Pkt</th></tr>"

    html += "<tr><td>1</td><td>Jan</td><td>10</td></tr>"
    html += "<tr><td>2</td><td>Adam</td><td>8</td></tr>"

    html += "</table>"
    html += "<br><a href='/test'>Test</a>"

    return html



@app.get("/test")
def test():
    return "klik działa ✅"
