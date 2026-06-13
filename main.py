
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from supabase import create_client
import pandas as pd
import urllib.parse

import requests
import time

# ===== CACHE =====
CACHE_TTL = 300
cache = {}

# ===== APP =====
app = FastAPI()

# ===== CONFIG =====
SUPABASE_URL = "https://viqamqyqfobiwdbgfeoy.supabase.co"
SUPABASE_KEY = "TU_WSTAW_SWÓJ_KLUCZ"
FILE = "tabela zbiorcza z rankingiem.xlsx"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===== CACHE =====
CACHE_TTL = 300
cache = {}

# ===== STYLE =====
STYLE = """
<style>
body {
    font-family: Arial;
    background:#111;
    color:#eee;
    margin:0;
    padding:10px;
}

h2 {
    text-align:center;
    margin:20px 0;
}

table {
    width:100%;
    border-collapse:collapse;
    background:#1e1e1e;
}

th {
    background:#222;
    padding:10px;
}

td {
    padding:8px;
    border-bottom:1px solid #333;
}

tr:hover {
    background:#2a2a2a;
}

a {
    color:#4da6ff;
    text-decoration:none;
}

img.flag {
    height:18px;
    vertical-align:middle;
    margin-right:5px;
}
</style>
"""

# ===== FLAGI =====
def get_flag(country):

    codes = {
        "Polska":"pl","Niemcy":"de","Francja":"fr","Hiszpania":"es",
        "USA":"us","Argentyna":"ar","Brazylia":"br","Holandia":"nl",
        "Japonia":"jp","Korea Południowa":"kr","Meksyk":"mx",
        "Szwajcaria":"ch","Szwecja":"se","Turcja":"tr",
        "Arabia Saudyjska":"sa","Kanada":"ca","RPA":"za",
        "Czechy":"cz","Bośnia i Hercegowina":"ba","Paragwaj":"py",
        "Katar":"qa","Maroko":"ma","Haiti":"ht","Australia":"au",
        "Curacao":"cw","Ekwador":"ec","Wybrzeże Kości Słoniowej":"ci",
        "Tunezja":"tn","Republika Zielonego Przylądka":"cv",
        "Belgia":"be","Egipt":"eg","Urugwaj":"uy","Iran":"ir",
        "Nowa Zelandia":"nz","Senegal":"sn","Irak":"iq",
        "Norwegia":"no","Algieria":"dz","Austria":"at",
        "Jordania":"jo","Portugalia":"pt","DR Konga":"cd",
        "Chorwacja":"hr","Ghana":"gh","Panama":"pa",
        "Uzbekistan":"uz","Kolumbia":"co"
    }

    code = codes.get(country)
    if code:
        return f"https://flagcdn.com/w20/{code}.png"
    return ""

# ===== LIVE API =====
def get_live_match(mecz):

    if mecz in cache:
        data, t = cache[mecz]
        if time.time() - t < CACHE_TTL:
            return data

    teams = mecz.split("-")
    if len(teams) != 2:
        return None

    t1 = teams[0].strip()
    t2 = teams[1].strip()

    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    querystring = {"search": f"{t1} vs {t2}"}

    headers = {
        "X-RapidAPI-Key": "TU_WSTAW_KLUCZ",
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }

    try:
        r = requests.get(url, headers=headers, params=querystring, timeout=5)
        data = r.json()

        fixtures = data.get("response")
        if not fixtures:
            return None

        match = fixtures[0]

        g1 = match["goals"]["home"]
        g2 = match["goals"]["away"]

        if g1 is not None and g2 is not None:
            wynik = (g1, g2)
            cache[mecz] = (wynik, time.time())
            return wynik

    except:
        return None

    return None

# ===== UPDATE =====
def update_missing_results():

    data = supabase.table("wyniki").select("*").order("id").execute()

    for row in data.data:
        if row["gol1"] is None and row["gol2"] is None:
            wynik = get_live_match(row["mecz"])
            if wynik:
                supabase.table("wyniki").update({
                    "gol1": wynik[0],
                    "gol2": wynik[1]
                }).eq("id", row["id"]).execute()

# ===== WYNIKI =====
def get_wyniki():

    data = supabase.table("wyniki").select("*").order("id").execute()

    out = {}
    for r in data.data:
        if r["gol1"] is not None and r["gol2"] is not None:
            out[r["mecz"].strip()] = (r["gol1"], r["gol2"])
        else:
            out[r["mecz"].strip()] = None

    return out

# ===== PUNKTY =====
def licz_punkty(typ, wynik):
    try:
        t1, t2 = map(int, str(typ).replace("-", ":").split(":"))
        w1, w2 = wynik

        if t1 == w1 and t2 == w2:
            return 3
        if (t1 - t2)*(w1 - w2) > 0:
            return 1
        if t1 == t2 and w1 == w2:
            return 1

        return 0
    except:
        return 0

# ===== HOME =====
@app.get("/", response_class=HTMLResponse)
def home():

    update_missing_results()

    xls = pd.ExcelFile(FILE)
    wyniki = get_wyniki()

    ranking = []

    for sheet in xls.sheet_names:

        if sheet.strip().lower() in ["wyniki","ranking","instrukcja","typy_zbiorcze"]:
            continue

        df = pd.read_excel(xls, sheet)
        df.columns = df.columns.str.strip()

        suma = 0
        dokladne = 0

        for _, r in df.iterrows():

            mecz = str(r.get("Mecz","")).strip()
            typ = str(r.get("Typ","")).strip()

            if not mecz:
                continue

            wynik = wyniki.get(mecz)

            if wynik is not None:
                pkt = licz_punkty(typ, wynik)
                suma += pkt
                if pkt == 3:
                    dokladne += 1

        ranking.append({"name":sheet,"pkt":suma,"dokladne":dokladne})

    ranking.sort(key=lambda x: x["pkt"], reverse=True)

    html = '<meta http-equiv="refresh" content="30">' + STYLE
    html += "<h2>🏆 Ranking</h2><table>"
    html += "<tr><th>#</th><th>Gracz</th><th>Pkt</th><th>🎯</th></tr>"

    for i, r in enumerate(ranking,1):

        safe = urllib.parse.quote(r["name"])
        pos = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else str(i)

        html += "<tr>"
        html += f"<td>{pos}</td>"
        html += f"<td><a href='/gracz/{safe}'>{r['name']}</a></td>"
        html += f"<td>{r['pkt']}</td>"
        html += f"<td>{r['dokladne']}</td>"
        html += "</tr>"

    html += "</table>"
    html += "<br><a href='/admin'>⚙️ Panel admin</a>"

    return html
from fastapi.responses import HTMLResponse, RedirectResponse
