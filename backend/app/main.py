from fastapi import FastAPI
from backend.app.api.chat import router as chat_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Seattle RAG")

@app.get("/healthz")
def healthz():
    return {"ok": True}


app.include_router(chat_router, prefix="/api", tags=["chat"])
