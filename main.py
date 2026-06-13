from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from supabase import create_client
import pandas as pd
import urllib.parse

app = FastAPI()

SUPABASE_URL = "https://viqamqyqfobiwdbgfeoy.supabase.co"
SUPABASE_KEY = "sb_publishable_Q975X156iJX3Ktd1X_xXOw_ILadf35a"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

FILE = "tabela zbiorcza z rankingiem.xlsx"

# ===== STYLE =====
STYLE = """
<style>
body {
  font-family: "Segoe UI Emoji","Apple Color Emoji","Noto Color Emoji",Arial;
  background:#f5f5f5;
  margin:0;
  padding:10px;
}
h2 { text-align:center; }
table { width:100%; border-collapse:collapse; background:white; }
th { background:#333; color:white; padding:10px; }
td { padding:8px; text-align:center; }
tr:nth-child(even){ background:#f2f2f2; }
tr:hover{ background:#ddd; }
a { text-decoration:none; color:#007bff; display:block; }
@media (max-width:600px){
  table { font-size:12px; }
  td,th { padding:6px; }
}
</style>
"""

# ===== FLAGI =====
flags = {
    "Polska":"🇵🇱","Niemcy":"🇩🇪","Francja":"🇫🇷","Hiszpania":"🇪🇸",
    "Anglia":"🏴","USA":"🇺🇸","Argentyna":"🇦🇷","Brazylia":"🇧🇷",
    "Holandia":"🇳🇱","Japonia":"🇯🇵","Korea Południowa":"🇰🇷",
    "Meksyk":"🇲🇽","Szwajcaria":"🇨🇭","Szwecja":"🇸🇪","Turcja":"🇹🇷",
    "Arabia Saudyjska":"🇸🇦","Kanada":"🇨🇦","RPA":"🇿🇦","Czechy":"🇨🇿",
    "Bośnia i Hercegowina":"🇧🇦","Paragwaj":"🇵🇾","Katar":"🇶🇦",
    "Maroko":"🇲🇦","Haiti":"🇭🇹","Szkocja":"🏴","Australia":"🇦🇺",
    "Curacao":"🇨🇼","Ekwador":"🇪🇨","Wybrzeże Kości Słoniowej":"🇨🇮",
    "Tunezja":"🇹🇳","Republika Zielonego Przylądka":"🇨🇻","Belgia":"🇧🇪",
    "Egipt":"🇪🇬","Urugwaj":"🇺🇾","Iran":"🇮🇷","Nowa Zelandia":"🇳🇿",
    "Senegal":"🇸🇳","Irak":"🇮🇶","Norwegia":"🇳🇴","Algieria":"🇩🇿",
    "Austria":"🇦🇹","Jordania":"🇯🇴","Portugalia":"🇵🇹",
    "DR Konga":"🇨🇩","Chorwacja":"🇭🇷","Ghana":"🇬🇭",
    "Panama":"🇵🇦","Uzbekistan":"🇺🇿","Kolumbia":"🇨🇴"
}

# ===== AUTO WYNIKI =====
def get_live_match(mecz):
    demo = {
        "Polska-Niemcy": (2,1),
        "Francja-Włochy": (1,0)
    }
    return demo.get(mecz)

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
        mecz = r["mecz"].strip()
        if r["gol1"] is not None and r["gol2"] is not None:
            out[mecz] = (r["gol1"], r["gol2"])
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

            if mecz == "" or mecz == "nan":
                continue

            wynik = wyniki.get(mecz)

            if wynik is not None:
                pkt = licz_punkty(typ, wynik)
                suma += pkt
                if pkt == 3:
                    dokladne += 1

        ranking.append({"name":sheet,"pkt":suma,"dokladne":dokladne})

    ranking.sort(key=lambda x: x["pkt"], reverse=True)

    html = STYLE
    html += "<h2>🏆 Ranking</h2><table>"
    html += "<tr><th>#</th><th>Gracz</th><th>Pkt</th><th>🎯</th></tr>"

    for i,r in enumerate(ranking,1):

        safe = urllib.parse.quote(r["name"])
        pos = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else str(i)

        html += "<tr>"
        html += "<td>"+pos+"</td>"
        html += "<td><a href='/gracz/"+safe+"'>"+r["name"]+"</a></td>"
        html += "<td>"+str(r["pkt"])+"</td>"
        html += "<td>"+str(r["dokladne"])+"</td>"
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
    html += "<h2>"+name+"</h2><table>"
    html += "<tr><th>Mecz</th><th>Typ</th><th>Wynik</th><th>Pkt</th></tr>"

    suma = 0

    for _, r in df.iterrows():

        mecz = str(r.get("Mecz","")).strip()
        typ = str(r.get("Typ","")).strip()

        if mecz == "" or mecz == "nan":
            continue

        wynik = wyniki.get(mecz)

        parts = mecz.split("-")
        if len(parts)==2:
            t1=parts[0].strip()
            t2=parts[1].strip()
            mecz_html = flags.get(t1,"🌍")+" "+t1+" vs "+flags.get(t2,"🌍")+" "+t2
        else:
            mecz_html = mecz

        if wynik is not None:
            pkt = licz_punkty(typ, wynik)
            suma += pkt
            wynik_txt = str(wynik[0])+":"+str(wynik[1])
        else:
            pkt = "-"
            wynik_txt = "-"

        color = "green" if pkt==3 else "orange" if pkt==1 else "red" if pkt==0 else "black"

        html += "<tr>"
        html += "<td>"+mecz_html+"</td>"
        html += "<td>"+typ+"</td>"
        html += "<td>"+wynik_txt+"</td>"
        html += "<td style='color:"+color+"'>"+str(pkt)+"</td>"
        html += "</tr>"

    html += "</table>"
    html += "<h3>Suma: "+str(suma)+"</h3>"
    html += "<a href='/'>⬅ Powrót</a>"

    return html

# ===== ADMIN =====
@app.get("/admin", response_class=HTMLResponse)
def admin():

    data = supabase.table("wyniki").select("*").order("id").execute()

    html = STYLE
    html += "<h2>Panel wyników</h2>"
    html += "<form method='post'><table>"

    for i, r in enumerate(data.data):

        g1 = "" if r["gol1"] is None else str(r["gol1"])
        g2 = "" if r["gol2"] is None else str(r["gol2"])

        html += "<tr>"
        html += "<td>"+r["mecz"]+"</td>"
        html += "<td><input name='g1_"+str(i)+"' value='"+g1+"'></td>"
        html += "<td><input name='g2_"+str(i)+"' value='"+g2+"'></td>"
        html += "</tr>"

    html += "</table><button>ZAPISZ</button></form>"
    html += "<br><a href='/'>⬅ Powrót</a>"

    return html

# ===== SAVE =====
@app.post("/admin")
async def save(request: Request):

    form = await request.form()
    data = supabase.table("wyniki").select("*").order("id").execute()

    for i, row in enumerate(data.data):

        g1 = form.get("g1_"+str(i))
        g2 = form.get("g2_"+str(i))

        val1 = None if g1=="" else int(g1) if g1 and g1.isdigit() else row["gol1"]
        val2 = None if g2=="" else int(g2) if g2 and g2.isdigit() else row["gol2"]

        supabase.table("wyniki").update({
            "gol1": val1,
            "gol2": val2
        }).eq("id", row["id"]).execute()

    return RedirectResponse("/admin", status_code=303)
