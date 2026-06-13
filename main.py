from fastapi import FastAPIfrom fastapi import Fast.responses import HTMLResponse
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
            results[r["mecz"]] = (r["gol1"], r["gol2"])

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


@app.get("/")
def home():
    return "✅ działa backend"
