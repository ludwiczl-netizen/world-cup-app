from fastapi import FastAPI, Requestfrom fastapi import FastAPI, supabase import create_client
import pandas as pd
import urllib.parse

app = FastAPI()

SUPABASE_URL = "https://viqamqyqfobiwdbgfeoy.supabase.co"
SUPABASE_KEY = "sb_publishable_Q975X156iJX3Ktd1X_xXOw_ILadf35a"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

FILE = "tabela zbiorcza z rankingiem.xlsx"


def get_results():
    data = supabase.table("wyniki").select("*").execute()
    results = {}

    for r in data.data:
        if r["gol1"] is not None and r["gol2"] is not None:
            results[r["mecz"].strip()] = (r["gol1"], r["gol2"])

    return results


def get_points(pred, actual):
    try:
        p1, p2 = map(int, str(pred).replace("-", ":").split(":"))
        a1, a2 = actual

        if p1 == a1 and p2 == a2:
            return 3
        if (p1 - p2) * (a1 - a2) > 0:
            return 1
        return 0
    except:
        return 0


def get_ranking():
    results = get_results()
    xls = pd.ExcelFile(FILE)

    ranking = []

    for sheet in xls.sheet_names:
        if sheet in ["Wyniki", "Ranking", "Typy_Zbiorcze", "Instrukcja"]:
            continue

        df = pd.read_excel(xls, sheet)
        total = 0

        for _, r in df.iterrows():
            match = r.get("Mecz")
            typ = r.get("Typ")

            if not isinstance(match, str):
                continue

            actual = results.get(match.strip())
            if actual:
                total += get_points(typ, actual)

        ranking.append({"name": sheet, "pts": total})

    ranking.sort(key=lambda x: x["pts"], reverse=True)
    return ranking


@app.get("/", response_class=HTMLResponse)
def home():

    html = "<h2>🏆 Ranking</h2>"
    html += "<table border='1' style='width:100%'>"
    html += "<tr><th>#</th><th>Gracz</th><th>Pkt</th></tr>"

    ranking = get_ranking()

    for i, r in enumerate(ranking, 1):
        safe = urllib.parse.quote(r["name"])

        html += "<gracz/"
        html += "<td>" + str(i) + "</td>"
        html += "<td>" + r["name"] + "</td>"
        html += "<td>" + str(r["pts"]) + "</td>"
        html += "</tr>"

    html += "</table>"
    html += "<br><a href='/admin'>⚙️ admin</a>"

    return html


@app.get("/gracz/{name}")
def player(name: str):

    name = urllib.parse.unquote(name)
    xls = pd.ExcelFile(FILE)

    if name not in xls.sheet_names:
        return "Brak gracza"

    df = pd.read_excel(xls, name)
    results = get_results()

    html = "<h3>" + name + "</h3>"

    for _, r in df.iterrows():
        match = r.get("Mecz")

        if isinstance(match, str):
            actual = results.get(match.strip())
            if actual:
                html += "<div>" + match + " → " + str(actual[0]) + ":" + str(actual[1]) + "</div>"

    html += "<br><a href='/'>⬅ powrót</a>"

    return html


@app.get("/admin")
def admin():

    data = supabase.table("wyniki").select("*").execute()

    html = "<h2>Admin</h2>"
    html += "<form method='post'>"
    html += "<table border='1'>"

    for i, r in enumerate(data.data):
        g1 = "" if r["gol1"] is None else str(r["gol1"])
        g2 = "" if r["gol2"] is None else str(r["gol2"])

        html += "<tr>"
        html += "<td>" + r["mecz"] + "</td>"
        html += "<td><input name='g1_" + str(i) + "' value='" + g1 + "'></td>"
        html += "<td><input name='g2_" + str(i) + "' value='" + g2 + "'></td>"
        html += "</tr>"

    html += "</table>"
    html += "<button>ZAPISZ</button>"
    html += "</form>"
    html += "<br><a href='/'>⬅ powrót</a>"

    return html


@app.post("/admin")
async def admin_save(request: Request):

    form = await request.form()
    data = supabase.table("wyniki").select("*").execute()

    for i, row in enumerate(data.data):
        g1 = form.get("g1_" + str(i))
        g2 = form.get("g2_" + str(i))

        if g1 and g1.isdigit():
            supabase.table("wyniki").update({"gol1": int(g1)}).eq("id", row["id"]).execute()

        if g2 and g2.isdigit():
            supabase.table("wyniki").update({"gol2": int(g2)}).eq("id", row["id"]).execute()

    return RedirectResponse("/", status_code=303)
from fastapi.responses import HTMLResponse, RedirectResponse
