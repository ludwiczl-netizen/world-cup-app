
@app.get("/", response_class=HTMLResponse)
def home():

    html = "<h2>Ranking</h2>"
    html += "/testKlik mnie</div>"
    return html
