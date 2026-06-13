
@app.get("/", response_class=HTMLResponse)
def home():
    html = "<h2>Ranking</h2>"
html += "<div onclick=\"location.href='/test'ml
    return html

@app.get("/test")
def test():
    return "klik działa ✅"
