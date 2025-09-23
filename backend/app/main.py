from fastapi import FastAPI
from backend.app.api.chat import router as chat_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Seattle RAG")

origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"ok": True}


app.include_router(chat_router, prefix="/api", tags=["chat"])
