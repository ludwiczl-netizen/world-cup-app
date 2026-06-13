from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
def home():
    html = "<h2>Ranking</h2>"
    html += "<a href='/test'>Klik mnie</a>"
    return html


@app.get("/test")
def test():
    return "klik działa ✅"
