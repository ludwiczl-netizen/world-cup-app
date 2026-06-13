from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from supabase import create_client
import urllib.parse

app = FastAPI()


# ===== SUPABASE =====
SUPABASE_URL = "https://viqamqyqfobiwdbgfeoy.supabase.co"
SUPABASE_KEY = "sb_publishable_Q975X156iJX3Ktd1X_xXOw_ILadf35a"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ===== FLAGI =====
def get_flag(team):
    mapping = {
        "polska": "pl","niemcy": "de","meksyk": "mx","kanada": "ca",
        "usa": "us","paragwaj": "py","katar": "qa","szwajcaria": "ch",
        "brazylia": "br","maroko": "ma","australia": "au","turcja": "tr",
        "korea": "kr","czechy": "cz","holandia": "nl","japonia": "jp",
        "szwecja": "se","hiszpania": "es","belgia": "be","egipt": "eg",
        "urugwaj": "uy","iran": "ir","francja": "fr","argentyna": "ar",
        "portugalia": "pt","anglia": "gb","chorwacja": "hr",
        "ghana": "gh","panama": "pa","kolumbia": "co"
    }

    t = team.lower()
    for k in mapping:
        if k in t:
            return f'<img src="https://flagcdn.com/24x18/{mapping[k]}.png" style="margin-right:6px">'
    return ""


# ===== WYNIKI =====
def get_results():
    response = supabase.table("wyniki").select("*").execute()

    results = {}

    for r in response.data:
        if r["gol1"] is not None and r["gol2"] is not None:
            results[r["mecz"].strip()] = (r["gol1"], r["gol2"])

    return results


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
    results = get_results()

    # 👉 tu nadal korzystasz z arkuszy typów (Excel lub inny system)
    import pandas as pd

    FILE = "tabela zbiorcza z rankingiem.xlsx"
    xls = pd.ExcelFile(FILE)

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
        safe = urllib.parse.quote(r["name"])

        medal = ["🥇", "🥈", "🥉"]
        place = medal[i-1] if i <= 3 else i

        rows += f"""
        <tr onclick="location.href='/gracz/{safe}'" style="    <td>{r['name']}</td>
            <td><b>{r['pts']}</b></td>
            <td>🎯 {r['hits']}</td>
        </tr>
        """

    return f"""
    <html>
    <body style="font-family:Arial;background:#f2f2f2">

    <div style="max-width:500px;margin:auto">

    <h2>🏆 Ranking</h2>

    <table border="1" style="width:100%;background:white">
    <tr><th>#</th><th>Gracz</th><th>Pkt</th><th>🎯</th></tr>
    {rows}
    </table>

    <br><a href="/admin">⚙️ Panel admin</a>

    </div>
    </body>
    </html>
    """


# ===== PLAYER =====
@app.get("/gracz/{name}", response_class=HTMLResponse)
def player(name: str):

    import pandas as pd

    FILE = "tabela zbiorcza z rankingiem.xlsx"
    name = urllib.parse.unquote(name)

    xls = pd.ExcelFile(FILE)

    if name not in xls.sheet_names:
        return "<h2>❌ Nie znaleziono gracza</h2>"

    df = pd.read_excel(xls, name)
    results = get_results()

    html = ""
    total = 0

    for _, r in df.iterrows():

        match = r.get("Mecz")
        typ = r.get("Typ")

        if not isinstance(match, str):
            continue

        actual = results.get(match.strip())
        t1, t2 = [x.strip() for x in match.split("-")]

        if not actual:
            continue

        pts, sym, col = get_points(typ, actual)
        total += pts

        html += f"""
        <div style="padding:10px;margin:8px;background:white;border-radius:10px">
            <div>{get_flag(t1)} {t1}</div>
            <div>{get_flag(t2)} {t2}</div>
            <b>{actual[0]}:{actual[1]}</b><br>
            {sym} {pts}
        </div>
        """

    return f"<h2>{name} • {total} pkt</h2>{html}"


# ===== ADMIN =====
@app.get("/admin", response_class=HTMLResponse)
def admin():

    data = supabase.table("wyniki").select("*").execute()

    rows = ""

    for i, r in enumerate(data.data):

        g1 = "" if r["gol1"] is None else r["gol1"]
        g2 = "" if r["gol2"] is None else r["gol2"]

        rows += f"""
        <tr>
            <td>{r['mecz']}</td>
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

    <br><button>ZAPISZ</button>
    </form>

    </body>
    </html>
    """


@app.post("/admin")
async def admin_save(request: Request):

    form = await request.form()
    data = supabase.table("wyniki").select("*").execute()

    for i, row in enumerate(data.data):

        g1 = form.get(f"g1_{i}")
        g2 = form.get(f"g2_{i}")

        if g1 and g1.isdigit():
            supabase.table("wyniki").update({"gol1": int(g1)}).eq("id", row["id"]).execute()

        if g2 and g2.isdigit():
            supabase.table("wyniki").update({"gol2": int(g2)}).eq("id", row["id"]).execute()

    return RedirectResponse("/", status_code=303)
