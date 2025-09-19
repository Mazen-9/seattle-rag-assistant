from fastapi import FastAPI
from backend.app.api.chat import router as chat_router

app = FastAPI(title="Seattle RAG")

@app.get("/healthz")
def healthz():
    return {"ok": True}

# If chat router file doesn't exist yet, comment the line below temporarily
app.include_router(chat_router, prefix="/api", tags=["chat"])
