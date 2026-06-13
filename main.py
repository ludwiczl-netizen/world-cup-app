from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from supabase import create_client
import pandas as pd
import urllib.parse

app = FastAPI()

# ===== SUPABASE =====
SUPABASE_URL = "https://viqamqyqfobiwdbgfeoy.supabase.co"
SUPABASE_KEY = "sb_publishable_Q975X156iJX3Ktd1X_xXOw_ILadf35a"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

FILE = "tabela zbiorcza z rankingiem.xlsx"


# ===== CSS (WSPÓLNY) =====
STYLE = """
<style>
body { font-family: Arial; background:#f5f5f5; padding:20px; }
table { border-collapse: collapse; width:100%; background:white; }
th { background:#333; color:white; padding:8px; }
td { padding:8px; text-align:center; }
tr:nth-child(even) { background:#f2f2f2; }
tr:hover { background:#ddd; cursor:pointer; }
a { text-decoration:none; color:#007bff; }
h2, h3 { margin-bottom: 10px; }
</style>
"""


# ===== WYNIKI =====
def get_wyniki():
    data = supabase.table("wyniki").select("*").execute()
    wyniki = {}

    for r in data.data:
        if r["gol1"] is not None and r["gol2"] is not None:
            wyniki[r["mecz"].strip()] = (r["gol1"], r["gol2"])

    return wyniki


# ===== PUNKTY =====
def licz_punkty(typ, wynik):
    try:
        t1, t2 = map(int, str(typ).replace("-", ":").split(":"))
        w1, w2 = wynik

        if t1 == w1 and t2 == w2:
            return 3
        if (t1 - t2) * (w1 - w2) > 0:
            return 1
        if t1 == t2 and w1 == w2:
            return 1
        return 0
    except:
        return 0


# ===== RANKING (LIVE) =====
@app.get("/", response_class=HTMLResponse)
def home():

    xls = pd.ExcelFile(FILE)
    wyniki = get_wyniki()

    ranking = []

    for sheet in xls.sheet_names:

        if sheet in ["Wyniki", "Ranking", "Instrukcja", "Typy_Zbiorcze"]:
            continue

        df = pd.read_excel(xls, sheet)
        df.columns = df.columns.str.strip()

        suma = 0

        for _, r in df.iterrows():

            mecz = str(r.get("Mecz", "")).strip()
            typ = str(r.get("Typ", "")).strip()

            if mecz == "" or mecz == "nan":
                continue

            wynik = wyniki.get(mecz)

            if wynik:
                suma += licz_punkty(typ, wynik)

        ranking.append({
            "name": sheet,
            "pkt": suma
        })

    ranking.sort(key=lambda x: x["pkt"], reverse=True)

    html = STYLE
    html += "<h2>🏆 Ranking</h2>"
    html += "<table>"
    html += "<tr><th>#</th><th>Gracz</th><th>Punkty</th></tr>"

    for i, r in enumerate(ranking, 1):

        safe = urllib.parse.quote(r["name"])

        if i == 1:
            pos = "🥇"
        elif i == 2:
            pos = "🥈"
        elif i == 3:
            pos = "🥉"
        else:
            pos = str(i)

        html += "<tr>"
        html += "<td>" + pos + "</td>"
        html += "<td><a href='/gracz/" + safe + "'>" + r["name"] + "</a></td>"
        html += "<td>" + str(r["pkt"]) + "</td>"
        html += "</tr>"

    html += "</table>"
    html += "<br><a href='/admin'>⚙️ Panel admin</a>"

    return html


# ===== GRACZ =====
@app.get("/gracz/{name}", response_class=HTMLResponse)
def player(name: str):

    name = urllib.parse.unquote(name)
    xls = pd.ExcelFile(FILE)

    if name not in xls.sheet_names:
        return "Brak danych"

    df = pd.read_excel(xls, name)
    df.columns = df.columns.str.strip()

    wyniki = get_wyniki()

    html = STYLE
    html += "<h2>" + name + "</h2>"
    html += "<table>"
    html += "<tr><th>Mecz</th><th>Typ</th><th>Wynik</th><th>Pkt</th></tr>"

    suma = 0

    for _, r in df.iterrows():

        mecz = str(r.get("Mecz", "")).strip()
        typ = str(r.get("Typ", "")).strip()

        if mecz == "" or mecz == "nan":
            continue

        wynik = wyniki.get(mecz)

        if wynik:
            pkt = licz_punkty(typ, wynik)
            suma += pkt
            wynik_txt = str(wynik[0]) + ":" + str(wynik[1])
        else:
            pkt = "-"
            wynik_txt = "-"

        # kolor punktów
        if pkt == 3:
            color = "green"
        elif pkt == 1:
            color = "orange"
        elif pkt == 0:
            color = "red"
        else:
            color = "black"

        html += "<tr>"
        html += "<td>" + mecz + "</td>"
        html += "<td>" + typ + "</td>"
        html += "<td>" + wynik_txt + "</td>"
        html += "<td style='color:" + color + "'>" + str(pkt) + "</td>"
        html += "</tr>"

    html += "</table>"
    html += "<h3>🔥 Suma: " + str(suma) + "</h3>"
    html += "<br><a href='/'>⬅ Powrót</a>"

    return html


# ===== ADMIN =====
@app.get("/admin", response_class=HTMLResponse)
def admin():

    data = supabase.table("wyniki").select("*").execute()

    html = STYLE
    html += "<h2>Panel wyników</h2>"
    html += "<form method='post'>"
    html += "<table>"

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
    html += "<br><a href='/'>⬅ Powrót</a>"

    return html


# ===== ZAPIS =====
@app.post("/admin")
async def admin_save(request: Request):

    form = await request.form()
    data = supabase.table("wyniki").select("*").execute()

    for i, row in enumerate(data.data):

        g1 = form.get("g1_" + str(i))
        g2 = form.get("g2_" + str(i))

        # jeśli pole puste → ustaw NULL
        if g1 == "":
            val1 = None
        elif g1 and g1.isdigit():
            val1 = int(g1)
        else:
            val1 = row["gol1"]

        if g2 == "":
            val2 = None
        elif g2 and g2.isdigit():
            val2 = int(g2)
        else:
            val2 = row["gol2"]

        supabase.table("wyniki").update({
            "gol1": val1,
            "gol2": val2
        }).eq("id", row["id"]).execute()

    return RedirectResponse("/admin", status_code=303)
