from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd
import requests

app = FastAPI()

FILE = "tabela zbiorcza z rankingiem.xlsx"


def get_flag(team):
    mapping = {
        "polska": "pl",
        "niemcy": "de",
        "meksyk": "mx",
        "rpa": "za",
        "korea południowa": "kr",
        "czechy": "cz"
    }

    if not isinstance(team, str):
        return ""

    for k in mapping:
        if k in team.lower():
            return f'<img src="https://flagcdn.com/24x18/{mapping[k]}.png" class="flag">'
    return ""


def get_results():
    df = pd.read_excel(FILE, sheet_name="Wyniki")
    results = {}

    for _, r in df.iterrows():
        if isinstance(r.get("Mecz"), str) and pd.notna(r.get("Gol 1")):
            results[r["Mecz"].strip()] = (int(r["Gol 1"]), int(r["Gol 2"]))

    return results


def get_live():
    try:
        r = requests.get("https://sportscore.com/api/widget/matches/?sport=football", timeout=5)
        data = r.json()
        return [m for m in data.get("matches", []) if isinstance(m, dict)]
    except:
        return []


def get_live_match(name, matches):
    if not isinstance(name, str):
        return None

    name = name.lower()

    for m in matches:
        if not isinstance(m, dict):
            continue

        home = m.get("home")
        away = m.get("away")

        if not isinstance(home, dict) or not isinstance(away, dict):
            continue

        h = home.get("name")
        a = away.get("name")

        if isinstance(h, str) and isinstance(a, str):
            if h.lower() in name and a.lower() in name:
                hs = home.get("score")
                as_ = away.get("score")

                if isinstance(hs, int) and isinstance(as_, int):
                    return {
                        "score": (hs, as_),
                        "minute": m.get("minute") or ""
                    }

    return None


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


def get_ranking():
    xls = pd.ExcelFile(FILE)
    results = get_results()
    live = get_live()

    out = []

    for sheet in xls.sheet_names:
        if sheet in ["Wyniki", "Ranking", "Typy_Zbiorcze", "Instrukcja"]:
            continue

        df = pd.read_excel(xls, sheet)
        total = 0
        hits = 0

        for _, r in df.iterrows():
            match = r.get("Mecz")
            typ = r.get("Typ")

            if not isinstance(match, str):
                continue

            actual = results.get(match.strip())
            live_data = get_live_match(match, live)

            if live_data:
                actual = live_data["score"]

            if actual:
                pts, _, _ = get_points(typ, actual)
                total += pts
                if pts == 3:
                    hits += 1

        out.append({"name": sheet, "pts": total, "hits": hits})

    out.sort(key=lambda x: (x["pts"], x["hits"]), reverse=True)
    return out


@app.get("/", response_class=HTMLResponse)
def home():
    data = get_ranking()

    rows = ""
    for i, r in enumerate(data, 1):
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
    <body style="font-family:Arial">

    <h2>🏆 Ranking</h2>

    <table border="1" cellpadding="8">
    <tr><th>#</th><th>Gracz</th><th>Pkt</th><th>Trafione</th></tr>
    {rows}
    </table>

    </body>
    </html>
    """


@app.get("/gracz/{name}", response_class=HTMLResponse)
def player(name: str):

    xls = pd.ExcelFile(FILE)
    df = pd.read_excel(xls, name)

    results = get_results()
    live = get_live()

    rows = ""
    total = 0

    hits = partial = miss = 0

    for _, r in df.iterrows():
        match = r.get("Mecz")
        typ = r.get("Typ")

        if not isinstance(match, str):
            continue

        actual = results.get(match.strip())
        live_data = get_live_match(match, live)

        minute = ""

        if live_data:
            actual = live_data["score"]
            minute = live_data["minute"]

        if not actual:
            continue

        pts, sym, col = get_points(typ, actual)
        total += pts

        if pts == 3:
            hits += 1
        elif pts == 1:
            partial += 1
        else:
            miss += 1

        t1, t2 = [x.strip() for x in match.split("-")]

        rows += f"""
        <div style="border:1px solid #ccc;margin:10px;padding:10px">
            <div>{get_flag(t1)} {t1}</div>
            <div>{get_flag(t2)} {t2}</div>
            <div><b>{actual[0]}:{actual[1]}</b></div>
            <div>TYP: {typ}</div>
            <div style="color:{col}">{sym} {pts} pkt</div>
            <div style="color:red">{minute}</div>
        </div>
        """

    total_matches = hits + partial + miss
    acc = int((hits / total_matches) * 100) if total_matches else 0

    return f"""
    <html>
    <body style="font-family:Arial">

    <h2><a href="/">⬅ Powrót</a></h2>

    <h3>{name} • {total} pkt</h3>

    <div>
        🎯 {hits} | ⚖️ {partial} | ❌ {miss} | 📊 {acc}%
    </div>

    {rows}

    </body>
    </html>
