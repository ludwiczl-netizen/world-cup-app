from fastapi import FastAPI, Request
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
    return (
        text.lower()
        .replace("ł", "l").replace("ś", "s")
        .replace("ą", "a").replace("ę", "e")
        .replace("ż", "z").replace("ź", "z")
        .replace("ó", "o").replace("ń", "n")
        .replace("&", " ")
    )


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def words(text):
    return normalize(text).replace("-", " ").split()


# ===== FLAGI =====
def get_flag(team):
    mapping = {
        "polska": "pl", "niemcy": "de", "meksyk": "mx",
        "kanada": "ca", "usa": "us", "paragwaj": "py",
        "katar": "qa", "szwajcaria": "ch",
        "brazylia": "br", "maroko": "ma",
        "australia": "au", "turcja": "tr",
        "bosnia": "ba", "hercegowina": "ba",
        "curacao": "cw", "korea": "kr",
        "czechy": "cz", "holandia": "nl",
        "japonia": "jp", "szwecja": "se",
        "tunezja": "tn", "hiszpania": "es",
        "belgia": "be", "egipt": "eg",
        "arabia": "sa", "urugwaj": "uy",
        "iran": "ir", "nowa zelandia": "nz",
        "francja": "fr", "senegal": "sn",
        "irak": "iq", "norwegia": "no",
        "argentyna": "ar", "algieria": "dz",
        "austria": "at", "jordania": "jo",
        "portugalia": "pt", "anglia": "gb",
        "chorwacja": "hr", "ghana": "gh",
        "panama": "pa", "kolumbia": "co",
        "kongo": "cd"
    }

    t = normalize(team)

    for k in mapping:
        if k in t:
            return f'<img src="https://flagcdn.com/24x18/{mapping[k]}.png" style="margin-right:6px">'
    return ""


# ===== WYNIKI =====
def get_results():
    df = pd.read_excel(FILE, sheet_name="Wyniki")
    results = {}

    for _, r in df.iterrows():
        match = r.get("Mecz")
        g1 = r.get("Gol 1")
        g2 = r.get("Gol 2")

        if isinstance(match, str) and pd.notna(g1) and pd.notna(g2):
            results[match.strip()] = (int(g1), int(g2))

    return results


# ===== LIVE =====
def get_live():
    try:
        r = requests.get("https://sportscore.com/api/widget/matches/?sport=football", timeout=5)
        data = r.json()
        return [m for m in data.get("matches", []) if isinstance(m, dict)]
    except:
        return []


def match_team(excel_team, api_team):
    for w1 in words(excel_team):
        for w2 in words(api_team):
            if similar(w1, w2) > 0.7:
                return True
    return False


def get_live_match(match_name, matches):
    if not isinstance(match_name, str):
        return None, ""

    try:
        team1, team2 = [x.strip() for x in match_name.split("-")]
    except:
        return None, ""

    for m in matches:
        if not isinstance(m, dict):
            continue

        home = m.get("home")
        away = m.get("away")

        if not isinstance(home, dict) or not isinstance(away, dict):
            continue

        h = home.get("name")
        a = away.get("name")

        if not isinstance(h, str) or not isinstance(a, str):
            continue

        if match_team(team1, h) and match_team(team2, a) or \
           match_team(team1, a) and match_team(team2, h):

            hs = home.get("score")
            as_ = away.get("score")

            if isinstance(hs, int) and isinstance(as_, int):
                return (hs, as_), m.get("minute", "")

    return None, ""


# ===== PUNKTY =====
def get_points(pred, actual):
    try:
        p1, p2 = map(int, str(pred).replace("-", ":").split(":"))
        a1, a2 = actual

        if p1 == a1 and p2 == a2:
            return 3, "✅", "green"
        if (p1 - p2) * (a1 - a2) > 0 or (p1 == p2 and a1 == a2):
            return 1, "➖", "orange"
        return 0, "❌", "red"
    except:
        return 0, "❌", "red"


# ===== RANKING =====
def get_ranking():
    xls = pd.ExcelFile(FILE)
    results = get_results()
    live = get_live()

    data = []

    for sheet in xls.sheet_names:
        if sheet in ["Wyniki", "Ranking", "Typy_Zbiorcze", "Instrukcja"]:
            continue

        df = pd.read_excel(xls, sheet)
        total = hits = 0

        for _, r in df.iterrows():
            match = r.get("Mecz")
            typ = r.get("Typ")

            if not isinstance(match, str):
                continue

            actual = results.get(match.strip())
            live_score, _ = get_live_match(match, live)

            if live_score:
                actual = live_score

            if actual:
                pts, _, _ = get_points(typ, actual)
                total += pts
                if pts == 3:
                    hits += 1

        data.append({"name": sheet.strip(), "pts": total, "hits": hits})

    return sorted(data, key=lambda x: (x["pts"], x["hits"]), reverse=True)


# ===== HOME =====
@app.get("/", response_class=HTMLResponse)
def home():

    rows = ""
    for i, r in enumerate(get_ranking(), 1):
        safe = urllib.parse.quote(r['name'])
        rows += f"""
        <tr>
            <td>{i}</td>
            <td><a href="/gracz/{safe}">{r['name']}</a></td>
            <td>{r['pts']}</td>
            <td>🎯 {r['hits']}</td>
        </tr>
        """

    return f"""
    <html>
    <body>
    <h2>🏆 Ranking</h2>
    <table border="1">
    <tr><th>#</th><th>Gracz</th><th>Pkt</th><th>🎯</th></tr>
    {rows}
    </table>

    <br>
    <a href="/admin">⚙️ Panel admin</a>

    </body>
    </html>
    """


# ===== PLAYER =====
@app.get("/gracz/{name}", response_class=HTMLResponse)
def player(name: str):

    name = urllib.parse.unquote(name)

    df = pd.read_excel(pd.ExcelFile(FILE), name)
    results = get_results()
    live = get_live()

    html = ""
    total = hits = partial = miss = 0

    for _, r in df.iterrows():

        match = r.get("Mecz")
        typ = r.get("Typ")

        if not isinstance(match, str):
            continue

        actual = results.get(match.strip())
        live_score, minute = get_live_match(match, live)

        if live_score:
            actual = live_score

        if not actual:
            continue

        pts, sym, col = get_points(typ, actual)
        total += pts

        html += f"<div>{match} → {actual[0]}:{actual[1]} ({sym} {pts})</div>"

    return f"<h3>{name} — {total} pkt</h3>{html}"


# ===== ADMIN =====
@app.get("/admin", response_class=HTMLResponse)
def admin():

    df = pd.read_excel(FILE, sheet_name="Wyniki")

    rows = ""

    for i, r in df.iterrows():

        match = r.get("Mecz")
        g1 = "" if pd.isna(r.get("Gol 1")) else int(r.get("Gol 1"))
        g2 = "" if pd.isna(r.get("Gol 2")) else int(r.get("Gol 2"))

        rows += f"""
        <tr>
            <td>{match}</td>
            <td><input name="g1_{i}" value="{g1}"></td>
            <td><input name="g2_{i}" value="{g2}"></td>
        </tr>
        """

    return f"""
    <html>
    <body>

    <h2>Panel wyników</h2>

    <form method="post">
    <table border="1">
    {rows}
    </table>

    <br>
    <button type="submit">Zapisz</button>
    </form>

    </body>
    </html>
    """


@app.post("/admin")
async def admin_save(request: Request):

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
