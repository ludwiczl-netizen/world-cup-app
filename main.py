from fastapi import FastAPI

app = FastAPI()

@app.get return "OK ✅"@app.get("/")

def home():
