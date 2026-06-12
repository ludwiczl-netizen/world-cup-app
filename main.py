from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd
import requests
from difflib import SequenceMatcher
import urllib.parse

app = FastAPI()
FILE = "tabela zbiorcza z rankingiem.xlsx"


# ===== NORMALIZACJA =====
def norm(t):
    if not isinstance(t, str):
        return ""
    return t.lower().replace("ó","o").replace("ł","l").replace("ś","s").replace("ą","a").replace("ę","e").replace("ż","z").replace("ź","z").replace("ń","n")


# ===== FLAGI (AUTO 🌍) =====
ISO = {
    "polska":"pl","niemcy":"de","meksyk":"mx","kanada":"ca","usa":"us","paragwaj":"py",
    "katar":"qa","szwajcaria":"ch","brazylia":"br","maroko":"ma","australia":"au",
    "turcja":"tr","bosnia":"ba","hercegowina":"ba","curacao":"cw","korea":"kr",
    "czechy":"cz","holandia":"nl","japonia":"jp","szwecja":"se","tunezja":"tn",
    "hiszpania":"es","belgia":"be","egipt":"eg","arabia":"sa","urugwaj":"uy",
    "iran":"ir","nowa zelandia":"nz","francja":"fr","senegal":"sn","norwegia":"no",
    "argentyna":"ar","algieria":"dz","austria":"at","jordania":"jo","portugalia":"pt",
    "anglia":"gb","chorwacja":"hr","ghana":"gh","panama":"pa","kolumbia":"co",
    "kongo":"cd"
}

def get_flag(team):
    t = norm(team)
    for k in ISO:
        if k in t:
            return f'<img src="https://flagcdn.com/24x18/{ISO[k]}.png">'
    return ""


# ===== WYNIKI =====
def get_results():
    df = pd.read_excel(FILE, sheet_name="Wyniki")
    out = {}
    for _, r in df.iterrows():
        m = r.get("Mecz")
        g1 = r.get("Gol 1")
        g2 = r.get("Gol 2")
        if isinstance(m,str) and pd.notna(g1) and pd.notna(g2):
            out[m.strip()] = (int(g1), int(g2))
    return out


# ===== LIVE =====
def get_live():
    try:
        r = requests.get("https://sportscore.com/api/widget/matches/?sport=football", timeout=5)
        data = r.json()
        return data.get("matches", [])
    except:
        return []


def sim(a,b):
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def get_live_match(match, matches):
    try:
        t1,t2 = [x.strip() for x in match.split("-")]
    except:
        return None,""

    for m in matches:
        if not isinstance(m,dict):
            continue

        h = m.get("home")
        a = m.get("away")

        if not isinstance(h,dict) or not isinstance(a,dict):
            continue

        hn = h.get("name")
        an = a.get("name")

        if not isinstance(hn,str) or not isinstance(an,str):
            continue

        if sim(t1,hn)>0.6 and sim(t2,an)>0.6 or sim(t1,an)>0.6 and sim(t2,hn)>0.6:
            hs = h.get("score")
            as_ = a.get("score")
            if isinstance(hs,int) and isinstance(as_,int):
                return (hs,as_), m.get("minute","")

    return None,""


# ===== PUNKTY =====
def get_points(p,a):
    try:
        p1,p2 = map(int,str(p).replace("-",":").split(":"))
        a1,a2 = a

        if p1==a1 and p2==a2: return 3,"✅","green"
        if (p1-p2)*(a1-a2)>0 or (p1==p2==a1==a2): return 1,"➖","orange"
        return 0,"❌","red"
    except:
        return 0,"❌","red"


# ===== RANKING =====
def get_ranking():
    xls = pd.ExcelFile(FILE)
    res = get_results()
    live = get_live()

    out=[]

    for s in xls.sheet_names:
        if s in ["Wyniki","Ranking","Typy_Zbiorcze","Instrukcja"]:
            continue

        df = pd.read_excel(xls,s)
        name = s.strip()

        pts=hits=0

        for _,r in df.iterrows():
            m=r.get("Mecz")
            t=r.get("Typ")

            if not isinstance(m,str):
                continue

            a = res.get(m.strip())
            ls,_ = get_live_match(m,live)

            if ls: a=ls

            if a:
                p,_,_=get_points(t,a)
                pts+=p
                if p==3: hits+=1

        out.append({"name":name,"pts":pts,"hits":hits})

    return sorted(out,key=lambda x:(x["pts"],x["hits"]),reverse=True)


# ===== HOME =====
@app.get("/", response_class=HTMLResponse)
def home():
    rows=""
    for i,r in enumerate(get_ranking(),1):
        url=urllib.parse.quote(r["name"])
        rows+=f"""
        <tr>
            <td>{i}</td>
            <td><a href="/gracz/{url}">{r['name']}</a></td>
            <td>{r['pts']}</td>
            <td>🎯 {r['hits']}</td>
        </tr>
        """

    return f"""
    <html><head>
    <meta name="viewport" content="width=device-width">
    <style>
    body {{font-family:Arial;background:#eee;margin:0}}
    .box {{max-width:500px;margin:auto;padding:10px}}
    table {{width:100%;background:white;border-radius:10px}}
    td,th {{padding:10px}}
    </style>
    </head><body>

    <div class="box">
    <h3>🏆 Ranking</h3>
    <table>
    <tr><th>#</th><th>Gracz</th><th>Pkt</th><th>🎯</th></tr>
    {rows}
    </table>
    </div>

    </body></html>
    """


# ===== PLAYER =====
@app.get("/gracz/{name}", response_class=HTMLResponse)
def player(name:str):

    name = urllib.parse.unquote(name)

    df = pd.read_excel(pd.ExcelFile(FILE), name)
    res = get_results()
    live = get_live()

    html=""
    pts=hits=mid=miss=0

    for _,r in df.iterrows():
        m=r.get("Mecz")
        t=r.get("Typ")

        if not isinstance(m,str):
            continue

        actual = res.get(m.strip())
        ls,minute = get_live_match(m,live)

        is_live=False
        if ls:
            actual=ls
            is_live=True

        t1,t2=[x.strip() for x in m.split("-")]

        if not actual:
            html+=f"""
            <div style="background:#ddd;padding:10px;margin:5px;border-radius:8px">
            {get_flag(t1)} {t1}<br>{get_flag(t2)} {t2}<br>-:-<br>TYP {t}
            </div>
            """
            continue

        p,sym,col = get_points(t,actual)

        pts+=p
        if p==3: hits+=1
        elif p==1: mid+=1
        else: miss+=1

        style="background:#ffeaea;border:2px solid red" if is_live else "background:white"

        html+=f"""
        <div style="{style};padding:10px;margin:5px;border-radius:8px">
        {get_flag(t1)} {t1}<br>
        {get_flag(t2)} {t2}<br>
        <b>{actual[0]}:{actual[1]}</b><br>
        TYP {t}<br>
        <span style="color:red">{minute if is_live else ""}</span><br>
        <span style="color:{col}">{sym} {p}</span>
        </div>
        """

    total = hits+mid+miss
    acc = int(hits/total*100) if total else 0

    return f"""
    <html><head>
    <meta name="viewport" content="width=device-width">
    </head><body>

    <div style="max-width:500px;margin:auto">

    <h3>{name} • {pts} pkt</h3>
    <div>🎯 {hits} | ➖ {mid} | ❌ {miss} | 📊 {acc}%</div>

    {html}

    </div>

    </body></html>
    """
