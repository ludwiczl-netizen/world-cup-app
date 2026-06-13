from fastapi.responses import HTMLResponse

h2>Ranking start ✅</h2>"@app.get("/", response_class=HTMLResponse)
    html += "<br>"
    return html

def home():
