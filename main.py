from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from supabase import create_client
import pandas as pd
import urllib.parse

import requests
CACHE_TTL = 300
import time
cache = {}


app = FastAPI()

def get_flag(country):

    codes = {
 "Holandia": "nl",        "Polska": "pl",
        "Japonia": "jp",
        "Korea Południowa": "kr",
        "Meksyk": "mx",
        "Szwajcaria": "ch",
        "Szwecja": "se",
        "Turcja": "tr",
        "Arabia Saudyjska": "sa",
        "Kanada": "ca",
        "RPA": "za",
        "Czechy": "cz",
        "Bośnia i Hercegowina": "ba",
        "Paragwaj": "py",
        "Katar": "qa",
        "Maroko": "ma",
        "Haiti": "ht",
        "Australia": "au",
        "Curacao": "cw",
        "Ekwador": "ec",
        "Wybrzeże Kości Słoniowej": "ci",
        "Tunezja": "tn",
        "Republika Zielonego Przylądka": "cv",
        "Belgia": "be",
        "Egipt": "eg",
        "Urugwaj": "uy",
        "Iran": "ir",
        "Nowa Zelandia": "nz",
        "Senegal": "sn",
        "Irak": "iq",
        "Norwegia": "no",
        "Algieria": "dz",
        "Austria": "at",
        "Jordania": "jo",
        "Portugalia": "pt",
        "DR Konga": "cd",
        "Chorwacja": "hr",
        "Ghana": "gh",
        "Panama": "pa",
        "Uzbekistan": "uz",
        "Kolumbia": "co"
    }

    code = codes.get(country)

    if code:
        return f"https://flagcdn.com/w20/{code}.png"
    else:
        return ""

# ===== MAPA NAZW DO API =====
name_map = {
    "Polska": "Poland",
    "Niemcy": "Germany",
    "Francja": "France",
    "Włochy": "Italy",
    "Hiszpania": "Spain",
    "Anglia": "England"
}

# ===== LIVE API =====
def get_live_match(mecz):

    # ✅ sprawdź cache
    if mecz in cache:
        data, timestamp = cache[mecz]

        if time.time() - timestamp < CACHE_TTL:
            return data  # użyj cache

    teams = mecz.split("-")

    if len(teams) != 2:
        return None

    t1 = teams[0].strip()
    t2 = teams[1].strip()

    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"

    querystring = {
        "search": f"{t1} vs {t2}"
    }

    headers = {
        "X-RapidAPI-Key": "TU_WSTAW_KLUCZ",
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=5)
        data = response.json()

        fixtures = data.get("response")

        if not fixtures:
            return None

        match = fixtures[0]

        g1 = match["goals"]["home"]
        g2 = match["goals"]["away"]

        if g1 is not None and g2 is not None:

            wynik = (g1, g2)

            # ✅ ZAPIS DO CACHE
            cache[mecz] = (wynik, time.time())

            return wynik

    except:
        return None

    return None


# ===== AUTO UPDATE =====
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

    html = '<meta http-equiv="refresh" content="30">' + STYLE + "<h2>🏆 Ranking</h2><table>"
    html += "<tr><th>#</th><th>Gracz</th><th>Pkt</th><th>🎯</th></tr>"

    for i, r in enumerate(ranking,1):

        safe = urllib.parse.quote(r["name"])
        pos = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else str(i)

        html += "<tr>"
        html += f"<td>{pos}</td>"
        html += f"<td>/gracz/{safe}{r['name']}</a></td>"
        html += f"<td>{r['pkt']}</td>"
        html += f"<td>{r['dokladne']}</td>"
        html += "</tr>"

    html += "</table>"
    html += "<br>/admin⚙️ Panel admin</a>"

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

    html = STYLE + f"<h2>{name}</h2><table>"
    html += "<tr><th>Mecz</th><th>Typ</th><th>Wynik</th><th>Pkt</th></tr>"

    suma = 0

    for _, r in df.iterrows():

        mecz = str(r.get("Mecz","")).strip()
        typ = str(r.get("Typ","")).strip()

        if not mecz:
            continue

        wynik = wyniki.get(mecz)

        teams = mecz.split("-")

        if len(teams) == 2:
            t1 = teams[0].strip()
            t2 = teams[1].strip()
            mecz_html = f"<img class='flag' src='{get_flag(t1)}'>{t1} vs <img class='flag' src='{get_flag(t2)}'>{t2}"
        else:
            mecz_html = mecz

        if wynik is not None:
            pkt = licz_punkty(typ, wynik)
            suma += pkt
            wynik_txt = f"{wynik[0]}:{wynik[1]}"
        else:
            pkt = "-"
            wynik_txt = "-"

        html += "<tr>"
        html += f"<td>{mecz_html}</td>"
        html += f"<td>{typ}</td>"
        html += f"<td>{wynik_txt}</td>"
        html += f"<td>{pkt}</td>"
        html += "</tr>"

    html += "</table>"
    html += f"<h3>Suma: {suma}</h3>"
    html += "<br>/⬅ Powrót</a>"

    return html
.gold { color: gold; font-weight:bold; }
.silver { color: silver; }
.bronze { color:#cd7f32; }

</style>
"""
