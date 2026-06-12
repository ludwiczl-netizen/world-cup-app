from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import pandas as pd
import requests
from difflib import SequenceMatcher
import urllib.parse

app = FastAPI()
FILE = "tabela zbiorcza z rankingiem.xlsx"


# ===== NORMALIZACJA =====
def normalize(text):
    if not isinstance(text, str):
        return ""
    return text.lower()


# ===== FLAGI =====
def get_flag(team):
    mapping = {
        "polska": "pl","niemcy": "de","meksyk": "mx","kanada": "ca","usa": "us",
        "paragwaj": "py","katar": "qa","szwajcaria": "ch","brazylia": "br",
        "maroko": "ma","australia": "au","turcja": "tr","japonia": "jp",
        "holandia": "nl","szwecja": "se","hiszpania": "es","belgia": "be",
        "egipt": "eg","arabia": "sa","urugwaj": "uy","iran": "ir",
        "nowa zelandia": "nz","francja": "fr","senegal": "sn",
        "norwegia": "no","argentyna": "ar","algieria": "dz","austria": "at",
        "portugalia": "pt","anglia": "gb","chorwacja": "hr","ghana": "gh",
        "panama": "pa","kolumbia": "co","czechy": "cz","rpa": "za"
    }
    t = normalize(team)
    for k in mapping:
        if k in t:
            return f'<img src="https://flagcdn.com/24x18/{mapping[k]}.png">'
    return ""


# ===== WYNIKI =====
def get_results():
    df = pd.read_excel(FILE, sheet_name="Wyniki")
    out = {}

    for _, r in df.iterrows():
        m = r.get("Mecz")
        g1 = r.get("Gol 1")
        g2 = r.get("Gol 2")

        if isinstance(m, str) and pd.notna(g1) and pd.notna(g2):
            out[m.strip()] = (int(g1), int(g2))

    return out


# ===== LIVE (PROSTY + STABILNY) =====
def get_live():
    try:
        r = requests.get("https://sportscore.com/api/widget/matches/?sport=football", timeout=5)
        return r.json().get("matches", [])
    except:
        return []


def get_live_match(match, matches):

    if not isinstance(match, str):
        return None, ""

    match = normalize(match)

    for m in matches:
        if not isinstance(m, dict):
            continue

        home = m.get("home")
        away = m.get("away")

        if not isinstance(home, dict) or not isinstance(away, dict):
            continue

        h = normalize(home.get("name"))
        a = normalize(away.get("name"))

        if h in match and a in match:
            hs = home.get("score")
            as_ = away.get("score")

            if isinstance(hs, int) and isinstance(as_, int):
                return (hs, as_), str(m.get("minute", "")) + "'"

    return None, ""


# ===== PUNKTY =====
def get_points(pred, actual):
    try:
        p1, p2 = map(int, str(pred).replace("-", ":").split(":"))
        a1, a2 = actual

        if p1 == a1 and p2 == a2:
            return 3, "✅", "green"
        if (p1 - p2) * (a1 - a2) > 0 or (p1 == p2 == a1 == a2):
            return 1, "➖", "orange"
        return 0, "❌", "red"
    except:
        return 0, "❌", "red"


# ===== RANKING =====
def get_ranking():
    xls = pd.ExcelFile(FILE)
    results = get_results()
    live = get_live()

    out = []

    for sheet in xls.sheet_names:
        if sheet == "Wyniki":
            continue

        df = pd.read_excel(xls, sheet)
        total = hits = 0

        for _, r in df.iterrows():
            m = r.get("Mecz")
            t = r.get("Typ")

            if not isinstance(m, str):
                continue

            actual = results.get(m.strip())
            live_score, _ = get_live_match(m, live)

            if live_score:
                actual = live_score

            if actual:
                p, _, _ = get_points(t, actual)
                total += p
                if p == 3:
                    hits += 1

        out.append({"name": sheet.strip(), "pts": total, "hits": hits})

    return sorted(out, key=lambda x: (x["pts"], x["hits"]), reverse=True)


# ===== HOME =====
@app.get("/", response_class=HTMLResponse)
def home():

    rows = ""
    for i, r in enumerate(get_ranking(), 1):
        safe = urllib.parse.quote(r["name"])

        rows += f"""
        <tr>
            <td>{i}</td>
            <td>/gracz/{safe}{r['name']}</a></td>
            <td>{r['pts']}</td>
            <td>🎯 {r['hits']}</td>
        </tr>
        """

    return f"""
    <html><head>
    <meta name="viewport" content="width=device-width">
    </head><body>

    <div style="max-width:500px;margin:auto">
    <h2>🏆 Ranking</h2>

    <table border="1" style="width:100%">
    <tr><th>#</th><th>Gracz</th><th>Pkt</th><th>🎯</th></tr>
    {rows}
    </table>

    <br>⚙️ Panel: /admin
    </div>

    </body></html>
    """


# ===== PLAYER =====
@app.get("/gracz/{name}", response_class=HTMLResponse)
def player(name: str):

    name = urllib.parse.unquote(name)

    df = pd.read_excel(pd.ExcelFile(FILE), name)
    results = get_results()
    live = get_live()

    html = ""
    total = hits = mid = miss = 0

    for _, r in df.iterrows():

        m = r.get("Mecz")
        t = r.get("Typ")

        if not isinstance(m, str):
            continue

        actual = results.get(m.strip())
        live_score, minute = get_live_match(m, live)

        is_live = False
        if live_score:
            actual = live_score
            is_live = True

        t1, t2 = [x.strip() for x in m.split("-")]

        if not actual:
            html += f"<div style='background:#ddd;padding:10px;margin:5px'> {t1} vs {t2} -:- TYP {t}</div>"
            continue

        p, sym, col = get_points(t, actual)

        total += p
        if p == 3: hits += 1
        elif p == 1: mid += 1
        else: miss += 1

        style = "background:#ffeaea" if is_live else "background:white"

        html += f"""
        <div style="{style};padding:10px;margin:5px">
        {get_flag(t1)} {t1}<br>
        {get_flag(t2)} {t2}<br>
        {actual[0]}:{actual[1]}<br>
        TYP {t}<br>
        🔴 {minute if is_live else ""}
        <br><span style="color:{col}">{sym} {p}</span>
        </div>
        """

    total_matches = hits + mid + miss
    acc = int(hits / total_matches * 100) if total_matches else 0

    return f"""
    <html><body>
    <div style="max-width:500px;margin:auto">

    <h3>{name} • {total} pkt</h3>
    🎯 {hits} | ➖ {mid} | ❌ {miss} | {acc}%

    {html}

    </div>
    </body></html>
    """


# ===== ADMIN PANEL =====
@app.get("/admin", response_class=HTMLResponse)
def admin():
    df = pd.read_excel(FILE, sheet_name="Wyniki")

    rows = ""

    for i, r in df.iterrows():
        m = r.get("Mecz")
        g1 = r.get("Gol 1")
        g2 = r.get("Gol 2")

        v1 = "" if pd.isna(g1) else int(g1)
        v2 = "" if pd.isna(g2) else int(g2)

        rows += f"""
        <tr>
            <td>{m}</td>
            <td><input name="g1_{i}" value="{v1}"></td>
            <td><input name="g2_{i}" value="{v2}"></td>
        </tr>
        """

    return f"""
    <html><body>
    <h2>ADMIN WYNIKI</h2>

    <form method="post">
    <table border="1">
    {rows}
    </table>

    <br>
    <button type="submit">ZAPISZ</button>
    </form>

    </body></html>
    """


@app.post("/admin")
async def save(request):

    form = await request.form()

    df = pd.read_excel(FILE, sheet_name="Wyniki")

    for i in df.index:

        g1 = form.get(f"g1_{i}")
        g2 = form.get(f"g2_{i}")

        if g1:
            df.at[i, "Gol 1"] = int(g1)
        if g2:
            df.at[i, "Gol 2"] = int(g2)

    with pd.ExcelWriter(FILE, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        df.to_excel(writer, sheet_name="Wyniki", index=False)

    return RedirectResponse("/", status_code=303)
