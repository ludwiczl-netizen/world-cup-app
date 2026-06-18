
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from supabase import create_client
import pandas as pd
import urllib.parse
import requests
import time
import os
import asyncio


# ===== API CONFIG =====
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
FOOTBALL_API_URL = "https://api.football-data.org/v4/competitions/WC/matches"

HEADERS = {
    "X-Auth-Token": FOOTBALL_API_KEY
}

# cache API
LAST_API_UPDATE = 0
API_CACHE = {}

def norm(name):
    return name.strip().lower()

def normalize_match_name(mecz):
    parts = [p.strip().lower() for p in mecz.replace("-", " - ").split(" - ")]
    return tuple(sorted(parts))
TEAM_MAP = {
    "Algeria": "Algieria",
    "Argentina": "Argentyna",
    "Australia": "Australia",
    "Austria": "Austria",
    "Belgium": "Belgia",
    "Bosnia-Herzegovina": "Bośnia i Hercegowina",
    "Brazil": "Brazylia",
    "Canada": "Kanada",
    "Cape Verde Islands": "Republika Zielonego Przylądka",
    "Colombia": "Kolumbia",
    "Congo DR": "DR Konga",
    "Croatia": "Chorwacja",
    "Curaçao": "Curacao",
    "Czechia": "Czechy",
    "Ecuador": "Ekwador",
    "Egypt": "Egipt",
    "England": "Anglia",
    "France": "Francja",
    "Germany": "Niemcy",
    "Ghana": "Ghana",
    "Haiti": "Haiti",
    "Iran": "Iran",
    "Iraq": "Irak",
    "Ivory Coast": "Wybrzeże Kości Słoniowej",
    "Japan": "Japonia",
    "Jordan": "Jordania",
    "Mexico": "Meksyk",
    "Morocco": "Maroko",
    "Netherlands": "Holandia",
    "New Zealand": "Nowa Zelandia",
    "Norway": "Norwegia",
    "Panama": "Panama",
    "Paraguay": "Paragwaj",
    "Portugal": "Portugalia",
    "Qatar": "Katar",
    "Saudi Arabia": "Arabia Saudyjska",
    "Scotland": "Szkocja",
    "Senegal": "Senegal",
    "South Africa": "RPA",
    "South Korea": "Korea Południowa",
    "Spain": "Hiszpania",
    "Sweden": "Szwecja",
    "Switzerland": "Szwajcaria",
    "Tunisia": "Tunezja",
    "Turkey": "Turcja",
    "United States": "USA",
    "Uruguay": "Urugwaj",
    "Uzbekistan": "Uzbekistan"
}
# ===== APP =====
app = FastAPI()

# ===== CONFIG =====
SUPABASE_URL = "https://viqamqyqfobiwdbgfeoy.supabase.co"
SUPABASE_KEY = "sb_publishable_Q975X156iJX3Ktd1X_xXOw_ILadf35a"
FILE = "tabela zbiorcza z rankingiem.xlsx"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
xls_cached = pd.ExcelFile(FILE)
# ===== STYLE =====
STYLE = """
<style>


/* ===== TABELA (RANKING + ADMIN) ===== */

* {
    box-sizing: border-box;
}


table {
    width:100%;
    max-width:800px;   /* 🔥 kontrola szerokości */
    margin:auto;       /* 🔥 centrowanie */
    border-collapse:collapse;
    table-layout:fixed;
}


th {
    background:#222;
    padding:12px;
    color:#aaa;
}

td {
    padding:10px;
    border-bottom:1px solid #2a2a2a;
}
/* ✅ SZEROKOŚCI KOLUMN (ranking) */

th:nth-child(1), td:nth-child(1) { width:36px; }
th:nth-child(3), td:nth-child(3) { width:45px; }
th:nth-child(4), td:nth-child(4) { width:45px; }


th:nth-child(2), td:nth-child(2) {
    width:auto;
}


/* hover */
tr:hover {
    background:#252525;
}

/* linki */
a {
    color:#4da6ff;
    text-decoration:none;
}

/* ===== TOP 3 ===== */
table.ranking tr:nth-child(2) td { color:#ffd700; font-weight:bold; }
table.ranking tr:nth-child(3) td { color:#c0c0c0; }
table.ranking tr:nth-child(4) td { color:#cd7f32; }

/* ===== PUNKTY ===== */
.p3 { color:#4caf50; font-weight:bold; }
.p1 { color:#ffd54f; }
.p0 { color:#ef5350; }

.up {
    color:#4caf50;
    margin-left:5px;
    animation: popUp 0.4s ease;
}

.down {
    color:#ef5350;
    margin-left:5px;
    animation: popDown 0.4s ease;
}


.same {
    color:#aaa;
    margin-left:5px;
}


@keyframes popUp {
    0% { opacity:0; transform:scale(0.6); }
    100% { opacity:1; transform:scale(1); }
}


@keyframes popDown {
    0% { opacity:0; transform:scale(0.6); }
    100% { opacity:1; transform:scale(1); }
}

.row-up {
    animation: flashUp 0.6s ease;
}

@keyframes flashUp {
    0% { background: rgba(76,175,80,0.4); }
    100% { background: rgba(76,175,80,0.08); }
}



/* ===== MECZ ===== */
.match {
    color:#e0e0e0 !important;
}

/* ===== FLAGI ===== */
img.flag {
    height:16px;
}

/* ===== MOBILE TABELA ===== */
@media (max-width:600px){

    table {
        width:100%;
    }

    th, td {
        font-size:15px;
        padding:6px;
        white-space:nowrap;
    }

    /* 🔥 ZWĘŻENIE KOLUMNY GRACZ */
    th:nth-child(2), td:nth-child(2) {
        white-space:nowrap;
        max-width:140px;
        overflow:visible;
    }
}

/* ===== KARTY (player view) ===== */
.cards {
    display:grid;
    grid-template-columns:1fr;
    gap:12px;
}

.card {
    background:#1a1a1a;
    padding:12px;
    border-radius:10px;
}

.card .match {
    margin-bottom:6px;
}

.row {
    display:flex;
    gap:10px;
    flex-wrap:wrap;
}

/* ===== DESKTOP GRID ===== */
@media (min-width:1400px){
    .cards {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (min-width:1200px){
    .cards {
        grid-template-columns: repeat(3, 1fr);
    }
}
/* ===== ADMIN TABLE ===== */
 table.admin {
     max-width:600px;
     margin:auto;
}


table.admin td:nth-child(1) {
    width:auto;           /* 🔥 mecz ma całą szerokość */
    text-align:left;
}

table.admin td:nth-child(2),
table.admin td:nth-child(3) {
    width:60px;           /* 🔥 miejsce na inputy */
    text-align:center;
}

/* ===== INPUTY (ADMIN) ===== */
input.score {
    width:26px !important;
    height:24px !important;
    text-align:center;
    padding:2px !important;
    font-size:13px;
    background:#111;
    color:#fff;
    border:1px solid #444;
    border-radius:6px;
}

/* ===== BUTTON ===== */
button {
    margin-top:10px;
    padding:10px;
    border:none;
    border-radius:8px;
    background:#4da6ff;
    color:white;
    width:100%;
}
/* ===== PODSTAWA ===== */
body {
    font-family: Arial, "Segoe UI Emoji", "Noto Color Emoji", sans-serif;
    background:#0f0f0f;
    color:#e0e0e0;
    margin:0;
    padding:10px;
    
    max-width:1400px;   /* 🔥 DODAJ */
    margin:auto;       /* 🔥 DODAJ */
}

h2 {
    text-align:center;

</style>
"""


# ===== FLAGI (działają na Windows) =====
def get_flag(country):
        
    codes = {
        "Polska":"pl","Niemcy":"de","Francja":"fr","Hiszpania":"es",
        "USA":"us","Argentyna":"ar","Brazylia":"br","Holandia":"nl",
        "Japonia":"jp","Korea Południowa":"kr","Meksyk":"mx",
        "Szwajcaria":"ch","Szwecja":"se","Turcja":"tr",
        "Arabia Saudyjska":"sa","Kanada":"ca","RPA":"za",
        "Czechy":"cz","Bośnia i Hercegowina":"ba","Paragwaj":"py",
        "Katar":"qa","Maroko":"ma","Haiti":"ht","Australia":"au",
        "Curacao":"cw","Ekwador":"ec",
        "Wybrzeże Kości Słoniowej":"ci","Tunezja":"tn",
        "Republika Zielonego Przylądka":"cv","Belgia":"be",
        "Egipt":"eg","Urugwaj":"uy","Iran":"ir",
        "Nowa Zelandia":"nz","Senegal":"sn","Irak":"iq",
        "Norwegia":"no","Algieria":"dz","Austria":"at",
        "Jordania":"jo","Portugalia":"pt","DR Konga":"cd",
        "Chorwacja":"hr","Ghana":"gh","Panama":"pa",
        "Uzbekistan":"uz","Kolumbia":"co","Anglia": "gb-eng","Szkocja": "gb-sct"
    }
    code = codes.get(country)
    if code:
        return f"<img class='flag' src='https://flagcdn.com/w20/{code}.png'>"
    return ""

# ===== WYNIKI =====
def get_wyniki():
    db = supabase.table("wyniki").select("*").order("id").execute()
    api = get_api_cached()

    out = {}

    for r in db.data:
        mecz = r["mecz"].strip()
        key = normalize_match_name(mecz)

        # ✅ ręczne dane mają priorytet
        if r["gol1"] is not None and r["gol2"] is not None:
            out[mecz] = (r["gol1"], r["gol2"])

        # ✅ fallback API
        elif key in api:
            out[mecz] = api[key]

        else:
            out[mecz] = None

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

# ===== API FETCH =====

def get_all_teams():
    url = "https://api.football-data.org/v4/competitions/WC/teams"
    response = requests.get(url, headers=HEADERS)
    data = response.json()

    teams = []

    for t in data.get("teams", []):
        teams.append(t["name"])

    return sorted(teams)


def fetch_matches_from_api():
    try:
        response = requests.get(FOOTBALL_API_URL, headers=HEADERS, timeout=10)
        data = response.json()

        matches = {}

        for m in data.get("matches", []):
            if m["status"] not in ["FINISHED", "IN_PLAY"]:
                continue

            home_en = m["homeTeam"]["name"]
            away_en = m["awayTeam"]["name"]

            home = TEAM_MAP.get(home_en, TEAM_MAP.get(home_en.strip(), home_en))
            away = TEAM_MAP.get(away_en, TEAM_MAP.get(away_en.strip(), away_en))

            key = normalize_match_name(f"{home} - {away}")

            score = m["score"]["fullTime"]
            
            score1 = score.get("home")
            score2 = score.get("away")
            
            if score1 is None or score2 is None:
                score = m["score"].get("halfTime") or {}
                score1 = score.get("home")
                score2 = score.get("away")



            if score1 is None or score2 is None:
                continue

            matches[key] = (score1, score2)
        print("=== API MATCHES ===")
        for k, v in matches.items():
            print(k, v)
        print("API:", home_en, "-", away_en)
        print("MAPPED:", home, "-", away)

        
        return matches


    except Exception as e:
        print("API error:", e)
        return {}

def get_api_cached():
    global LAST_API_UPDATE, API_CACHE

    if time.time() - LAST_API_UPDATE > 300:
        API_CACHE = fetch_matches_from_api()
        LAST_API_UPDATE = time.time()

    return API_CACHE
def is_empty(v):
    return v is None or str(v).strip() == ""

def update_results_from_api(force=False):
    if force:
        api = fetch_matches_from_api()   # 🔥 bez cache
    else:
        api = get_api_cached()

    db = supabase.table("wyniki").select("*").execute()

    for row in db.data:
        mecz = row["mecz"].strip()
        print("ROW:", mecz, row["gol1"], row["gol2"])  # 👈 TU
        key = normalize_match_name(mecz)

        if is_empty(row["gol1"]) and is_empty(row["gol2"]):

            if key in api:
                g1, g2 = api[key]

                print(f"AUTO UPDATE: {mecz} -> {g1}:{g2}")

                supabase.table("wyniki").update({
                    "gol1": g1,
                    "gol2": g2
                }).eq("id", row["id"]).execute()

# ===== HOME =====


@app.get("/", response_class=HTMLResponse)
def home():


    #update_missing_results()

    xls = xls_cached
    wyniki = get_wyniki()

    html = '<meta name="viewport" content="width=device-width, initial-scale=1">' + STYLE
    from datetime import datetime

    html += f"<p style='text-align:center;color:#888;'>last update: {datetime.now().strftime('%H:%M:%S')}</p>"

    old_data = supabase.table("ranking_history_old").select("*").execute()


    old_positions = {}

    if old_data.data:
        old_positions = {
            norm(r["name"]): r["position"]
            for r in old_data.data
        }



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

            if not mecz or mecz == "nan":
                continue

            wynik = wyniki.get(mecz)

            if wynik is not None:
                pkt = licz_punkty(typ, wynik)
                suma += pkt
                if pkt == 3:
                    dokladne += 1

        ranking.append({
            "name": sheet,
            "pkt": suma,
            "dokladne": dokladne
        })

    ranking.sort(key=lambda x: (x["pkt"], x["dokladne"]), reverse=True)

    html = '<meta name="viewport" content="width=device-width, initial-scale=1">' + STYLE
    html += "<h2>🏆 Ranking</h2>"
    html += "<div class='table-wrap'>"
    html += "<table id='ranking-table' class='ranking'>"
    html += "<tr><th>#</th><th>Gracz</th><th>Pkt</th><th>🎯</th></tr>"

    for i, r in enumerate(ranking,1):

        old_pos = old_positions.get(r["name"].strip().lower())

        change = ""

        if old_pos is not None:
            diff = old_pos - i

            if diff > 0:
                change = f" <span class='up'>🔼{diff}</span>"
            elif diff < 0:
                change = f" <span class='down'>🔽{abs(diff)}</span>"
            else:
                change = " <span class='same'>➖</span>"



                
        safe = urllib.parse.quote(r["name"])

        pos = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else str(i)

        html += "<tr>"
        html += f"<td>{pos}</td>"
        html += f"<td><a href='/gracz/{safe}'>{r['name']}</a>{change}</td>"

        cls = "p3" if i == 1 else "p1" if i <= 3 else ""

        html += f"<td class='{cls}'>{r['pkt']}</td>"
        html += f"<td>{r['dokladne']}</td>"
        html += "</tr>"

    html += "</table></div>"
    html += "<br><a href='/admin'>⚙️ Panel admin</a>"
    html += """
<script>

async function refreshRanking() {

    try {
        const res = await fetch('/ranking-data');
        const data = await res.json();

        let table = document.getElementById("ranking-table");

        let html = "<tr><th>#</th><th>Gracz</th><th>Pkt</th><th>🎯</th></tr>";

        data.forEach(r => {

            let change = "";

            if (r.diff > 0) {
                change = " <span class='up'>🔼" + r.diff + "</span>";
            } else if (r.diff < 0) {
                change = " <span class='down'>🔽" + Math.abs(r.diff) + "</span>";
            } else {
                change = " <span class='same'>➖</span>";
            }

            let pos = r.position == 1 ? "🥇" :
                      r.position == 2 ? "🥈" :
                      r.position == 3 ? "🥉" :
                      r.position;

            html += `
                <tr>
                    <td>${pos}</td>
                    <td><a href='/gracz/${encodeURIComponent(r.name)}'>${r.name}</a>${change}</td>
                    <td>${r.pkt}</td>
                    <td>${r.dokladne}</td>
                </tr>
            `;
        });

        table.innerHTML = html;

    } catch(e) {
        console.log("refresh error", e);
    }
}

// 🔁 co 15 sekund
setInterval(refreshRanking, 15000);

</script>
"""

    
    return html
    
from fastapi.responses import JSONResponse


@app.get("/ranking-data")
def ranking_data():

    xls = xls_cached
    wyniki = get_wyniki()

    old_data = supabase.table("ranking_history_old").select("*").execute()

    old_positions = {}
    if old_data.data:
        old_positions = {
            norm(r["name"]): r["position"]
            for r in old_data.data
        }

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

            if not mecz or mecz == "nan":
                continue

            wynik = wyniki.get(mecz)

            if wynik is not None:
                pkt = licz_punkty(typ, wynik)
                suma += pkt
                if pkt == 3:
                    dokladne += 1

        ranking.append({
            "name": sheet,
            "pkt": suma,
            "dokladne": dokladne
        })

    ranking.sort(key=lambda x: (x["pkt"], x["dokladne"]), reverse=True)

    out = []

    for i, r in enumerate(ranking, 1):

        old_pos = old_positions.get(norm(r["name"]))
        diff = 0

        if old_pos is not None:
            diff = old_pos - i

        out.append({
            "position": i,
            "name": r["name"],
            "pkt": r["pkt"],
            "dokladne": r["dokladne"],
            "diff": diff
        })

    return JSONResponse(out)


# ===== GRACZ =====
@app.get("/gracz/{name}", response_class=HTMLResponse)
def player(name: str):

    name = urllib.parse.unquote(name)

    xls = xls_cached
    if name not in xls.sheet_names:
        return "Brak danych"

    df = pd.read_excel(xls, name)
    df.columns = df.columns.str.strip()

    wyniki = get_wyniki()

    html = '<meta name="viewport" content="width=device-width, initial-scale=1">' + STYLE
    html += f"<h2>{name}</h2>"
    html += "<div class='cards'>"

    suma = 0

    for _, r in df.iterrows():

        mecz = str(r.get("Mecz","")).strip()
        typ = str(r.get("Typ","")).strip()

        if not mecz or mecz == "nan":
            continue

        wynik = wyniki.get(mecz)

        parts = mecz.split("-")

        if len(parts) == 2:
            t1 = parts[0].strip()
            t2 = parts[1].strip()
            mecz_html = f"{get_flag(t1)}{t1} vs {get_flag(t2)}{t2}"
        else:
            mecz_html = mecz

        if wynik is not None:
            pkt = licz_punkty(typ, wynik)
            suma += pkt
            wynik_txt = f"{wynik[0]}:{wynik[1]}"
        else:
            pkt = "-"
            wynik_txt = "-"

        cls = "p3" if pkt==3 else "p1" if pkt==1 else "p0" if pkt==0 else ""

        html += "<div class='card'>"
        
        html += f"<div class='match'><span class='match'>{mecz_html}</span></div>"

        html += "<div class='row'>"
        html += f"<span>Typ: {typ}</span>"
        html += f"<span class='{cls}'>Wynik: {wynik_txt}</span>"
        html += f"<span class='{cls}'>Pkt: {pkt}</span>"
        html += "</div>"

        html += "</div>"

    html += "</div>"
    html += f"<h3>Suma: {suma}</h3>"
    html += "<br><a href='/'>⬅ Powrót</a>"

    return html

# ===== ADMIN =====

from fastapi import Request

@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request):

    data = supabase.table("wyniki").select("*").order("id").execute()

    html = '<meta name="viewport" content="width=device-width, initial-scale=1">' + STYLE
    html += "<h2>Panel wyników</h2>"

    # ✅ komunikat po sync
    if request.query_params.get("sync") == "ok":
        html += "<p style='color:lightgreen;text-align:center;'>✅ Wyniki zaktualizowane</p>"

    # ✅ przycisk sync
    html += """
    <div style='text-align:center; margin-bottom:10px;'>
        <form method='post' action='/sync'>
            <button type='submit' style='background:#28a745;color:white;'>🔄 Aktualizuj wyniki</button>
        </form>
    </div>
    """

    
    # ✅ dopiero potem główny form
    html += "<form method='post'>"

    html += "<table class='admin'>"

    for i, r in enumerate(data.data):

        g1 = "" if r["gol1"] is None else str(r["gol1"])
        g2 = "" if r["gol2"] is None else str(r["gol2"])

        html += "<tr>"
        html += f"<td>{r['mecz']}</td>"
        html += f"<td><input class='score' name='g1_{i}' value='{g1}' /></td>"
        html += f"<td><input class='score' name='g2_{i}' value='{g2}' /></td>"
        html += "</tr>"

    html += "</table>"
    html += "<button>ZAPISZ</button>"
    html += "</form>"
    html += "<br><a href='/'>⬅ Powrót</a>"

    return html

# ===== SAVE =====
@app.post("/admin")
async def save(request: Request):

    form = await request.form()
    data = supabase.table("wyniki").select("*").order("id").execute()

    for i, row in enumerate(data.data):

        g1 = form.get(f"g1_{i}")
        g2 = form.get(f"g2_{i}")

        val1 = None if g1=="" else int(g1) if g1 and g1.isdigit() else row["gol1"]
        val2 = None if g2=="" else int(g2) if g2 and g2.isdigit() else row["gol2"]

        supabase.table("wyniki").update({
            "gol1": val1,
            "gol2": val2
        }).eq("id", row["id"]).execute()
        
    xls = xls_cached
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

            if not mecz or mecz == "nan":
                continue

            wynik = wyniki.get(mecz)

            if wynik is not None:
                pkt = licz_punkty(typ, wynik)
                suma += pkt
                if pkt == 3:
                    dokladne += 1

        ranking.append({
            "name": sheet,
            "pkt": suma,
            "dokladne": dokladne
        })

   # ✅ DOPIERO TU (PO PĘTLI)
    ranking.sort(key=lambda x: (x["pkt"], x["dokladne"]), reverse=True)

    # 🔥 pobierz stary ranking (PRZED usunięciem!)
    old_data = supabase.table("ranking_history").select("*").execute()

    # 🔥 przenieś do ranking_history_old
    if old_data.data:
        supabase.table("ranking_history_old").delete().neq("name", "").execute()

        old_rows = []
        for r in old_data.data:
            old_rows.append({
                "name": r["name"],
                "position": r["position"]
            })

        if old_rows:
            supabase.table("ranking_history_old").insert(old_rows).execute()

    # 🔥 teraz usuń aktualny ranking
    supabase.table("ranking_history").delete().neq("name", "").execute()

    # 🔥 zapisz nowy ranking
    rows = []
    for i, r in enumerate(ranking, 1):
        rows.append({
            "name": norm(r["name"]),
            "position": i
        })

    if rows:
        supabase.table("ranking_history").insert(rows).execute()



    
    return RedirectResponse("/admin?sync=ok", status_code=303)

@app.post("/sync")
def sync_api():
    try:
        update_results_from_api(force=True)  # 🔥 TU
        return RedirectResponse("/admin?sync=ok", status_code=303)
    except Exception as e:
        return f"Błąd sync: {e}"


import asyncio

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_task())

async def background_task():
    while True:
        try:
            update_results_from_api()
            print("✅ AUTO UPDATE DONE")
        except Exception as e:
            print("❌ AUTO UPDATE ERROR:", e)

        await asyncio.sleep(300)
