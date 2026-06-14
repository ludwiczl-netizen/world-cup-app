
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from supabase import create_client
import pandas as pd
import urllib.parse


# ===== APP =====
app = FastAPI()

# ===== CONFIG =====
SUPABASE_URL = "https://viqamqyqfobiwdbgfeoy.supabase.co"
SUPABASE_KEY = "sb_publishable_Q975X156iJX3Ktd1X_xXOw_ILadf35a"
FILE = "tabela zbiorcza z rankingiem.xlsx"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===== STYLE =====
STYLE = """
<style>
body {
    font-family: Arial;
    background:#0f0f0f;
    color:#e0e0e0;
    margin:0;
    padding:10px;
}

h2 {
    text-align:center;
    margin:15px 0;
}

table {
    width:100%;
    border-collapse:collapse;
    background:#1a1a1a;
    border-radius:10px;
    overflow:hidden;
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

tr:hover {
    background:#252525;
}

a {
    color:#4da6ff;
    text-decoration:none;
}

/* TOP 3 */
tr:nth-child(2) td { color:#ffd700; font-weight:bold; }
tr:nth-child(3) td { color:#c0c0c0; }
tr:nth-child(4) td { color:#cd7f32; }

/* PUNKTY */
td.p3 { color:#4caf50; font-weight:bold; }
td.p1 { color:#ffb74d; }
td.p0 { color:#ef5350; }

.match {
    color: #e0e0e0 !important;
}

img.flag {
    height:16px;
}

/* MOBILE */
@media (max-width:600px){
    table {
        font-size:12px;
        display:block;
        overflow-x:auto;
    }
}
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
        "Uzbekistan":"uz","Kolumbia":"co"
    }
    code = codes.get(country)
    if code:
        return f"<img class='flag' src='https://flagcdn.com/w20/{code}.png'>"
    return ""

# ===== AUTO WYNIKI (tylko puste!) =====
def get_live_match(mecz):
    demo = {
        "Polska-Niemcy": (2,1),
        "Francja-Włochy": (1,0)
    }
    return demo.get(mecz)

def update_missing_results():
    data = supabase.table("wyniki").select("*").order("id").execute()
    for r in data.data:
        if r["gol1"] is None and r["gol2"] is None:
            wynik = get_live_match(r["mecz"])
            if wynik:
                supabase.table("wyniki").update({
                    "gol1": wynik[0],
                    "gol2": wynik[1]
                }).eq("id", r["id"]).execute()

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

    ranking.sort(key=lambda x: x["pkt"], reverse=True)

    html = '<meta name="viewport" content="width=device-width, initial-scale=1">' + STYLE
    html += "<h2>🏆 Ranking</h2>"
    html += "<table>"
    html += "<tr><th>#</th><th>Gracz</th><th>Pkt</th><th>🎯</th></tr>"

    for i, r in enumerate(ranking,1):

        safe = urllib.parse.quote(r["name"])

        pos = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else str(i)

        html += "<tr>"
        html += f"<td>{pos}</td>"
        html += f"<td><a href='/gracz/{safe}'>{r['name']}</a></td>"

        cls = "p3" if i == 1 else "p1" if i <= 3 else ""

        html += f"<td class='{cls}'>{r['pkt']}</td>"
        html += f"<td>{r['dokladne']}</td>"
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

    html = '<meta name="viewport" content="width=device-width, initial-scale=1">' + STYLE
    html += f"<h2>{name}</h2>"
    html += "<table>"
    html += "<tr><th>Mecz</th><th>Typ</th><th>Wynik</th><th>Pkt</th></tr>"

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

        html += "<tr>"
        html += f"<td><span class='match'>{mecz_html}</span></td>"
        html += f"<td>{typ}</td>"
        html += f"<td><span class='{cls}'>{wynik_txt}</span></td>"
        html += f"<td><span class='{cls}'>{pkt}</span></td>"
        html += "</tr>"

    html += "</table>"
    html += f"<h3>Suma: {suma}</h3>"
    html += "<br><a href='/'>⬅ Powrót</a>"

    return html

# ===== ADMIN =====
@app.get("/admin", response_class=HTMLResponse)
def admin():

    data = supabase.table("wyniki").select("*").order("id").execute()

    html = '<meta name="viewport" content="width=device-width, initial-scale=1">' + STYLE
    html += "<h2>Panel wyników</h2>"
    html += "<form method='post'>"
    html += "<table>"

    for i, r in enumerate(data.data):

        g1 = "" if r["gol1"] is None else str(r["gol1"])
        g2 = "" if r["gol2"] is None else str(r["gol2"])

        html += "<tr>"
        html += f"<td>{r['mecz']}</td>"
        html += f"<td><input name='g1_{i}' value='{g1}'></td>"
        html += f"<td><input name='g2_{i}' value='{g2}'></td>"
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

    return RedirectResponse("/admin", status_code=303)
