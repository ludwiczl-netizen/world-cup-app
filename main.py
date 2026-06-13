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


def get_results():
    data = supabase.table("wyniki").select("*").execute()

    results = {}

    for r in data.data:
        if r["gol1"] is not None and r["gol2"] is not None:
            results[r["mecz"].strip()] = (r["gol1"], r["gol2"])

    return results


def get_points(pred, actual):
    try:
        p1, p2 = map(int, str(pred).replace("-", ":").split(":"))
        a1, a2 = actual

        if p1 == a1 and p2 == a2:
            return 3
        if (p1 - p2) * (a1 - a2) > 0:
            return 1
        return 0
    except:
        return 0


def get_ranking():
    results = get_results()
    xls = pd.ExcelFile(FILE)

    ranking = []

    for sheet in xls.sheet_names:
        if sheet in ["Wyniki", "Ranking", "Typy_Zbiorcze", "Instrukcja"]:
            continue

        df = pd.read_excel(xls, sheet)

        total = 0

        for _, r in df.iterrows():
            match = r.get("Mecz")
            typ = r.get("Typ")

            if not isinstance(match, str):
                continue

            actual = results.get(match.strip())

            if actual:
                total += get_points(typ, actual)

        ranking.append({"name": sheet, "pts": total})

    return sorted(ranking, key=lambda x: x["pts"], reverse=True)


@app.get("/", response_class=HTMLResponse)
def home():

    ranking = get_ranking()

    rows = ""

    for i, r in enumerate(ranking, 1):
        rows += f"<tr><td>{i}</td><td>{r['name']}</td><td>{r['pts']}</td></tr>"

    return f"""
    <h2>Ranking</h2>
    <table border="1">
    {rows}
    </table>
    <br>
    <a href="/admin">Admin</a>
    """


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
    <form method="post">
    <table border="1">
    {rows}
    </table>
    <button>ZAPISZ</button>
    </form>
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
