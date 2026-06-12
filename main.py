from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd
import requests
from difflib import SequenceMatcher

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
            return f'<img src="https://flagcdn.com/24x18/{mapping[k]}.png" class="flag"/>'

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


# ===== DOPASOWANIE DRUŻYN =====
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

        cond1 = match_team(team1, h) and match_team(team2, a)
        cond2 = match_team(team1, a) and match_team(team2, h)

        if cond1 or cond2:
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
        rows += f"""
        <tr>
            <td>{i}</td>
            <td><a href="/gracz/{r['name']}">{r['name']}</a></td>
            <td>{r['pts']}</td>
            <td>🎯 {r['hits']}</td>
        </tr>
        """

    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width">
    <style>
    body {{background:#f2f2f2;font-family:Arial}}
    .box {{max-width:500px;margin:auto;padding:10px}}
    table {{width:100%;background:white;border-radius:10px}}
    td,th {{padding:10px}}
    a {{text-decoration:none;color:black;font-weight:bold}}
    </style>
    </head>
    <body>
    <div class="box">
    <h3>🏆 Ranking</h3>
    <table>
    <tr><th>#</th><th>Gracz</th><th>Pkt</th><th>🎯</th></tr>
    {rows}
    </table>
    </div>
    </body>
    </html>
    """
