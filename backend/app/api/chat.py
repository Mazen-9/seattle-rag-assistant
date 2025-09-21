from fastapi import APIRouter, Body
from pydantic import BaseModel
from typing import Dict, Any, List
import os

from dotenv import load_dotenv; load_dotenv()
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores.pgvector import PGVector as PGVectorStore

# --- DB config from .env ---
PG_CONN_STR = (
    f"postgresql+psycopg://{os.getenv('PGUSER','postgres')}:{os.getenv('PGPASSWORD','postgres')}@"
    f"{os.getenv('PGHOST','localhost')}:{os.getenv('PGPORT','5432')}/{os.getenv('PGDATABASE','seattle_rag')}"
)
COLLECTION = os.getenv("PGVECTOR_COLLECTION", "seattle_docs")

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    top_k: int = 6

@router.post("/chat")
def chat(req: ChatRequest = Body(...)) -> Dict[str, Any]:
    emb = OpenAIEmbeddings(model="text-embedding-3-small")
    vstore = PGVectorStore(
        connection_string=PG_CONN_STR,
        collection_name=COLLECTION,
        embedding_function=emb,
    )

    docs = vstore.similarity_search(req.query, k=req.top_k)

    if not docs:
        return {"answer": "I couldn't find anything relevant in the documents.", "citations": []}

    context_blocks: List[str] = []
    cites: List[Dict[str, Any]] = []
    for i, d in enumerate(docs, 1):
        src = d.metadata.get("source")
        page = d.metadata.get("page")
        context_blocks.append(f"[{i}] (source: {src}, page {page})\n{d.page_content}")
        cites.append({"index": i, "source": src, "page": page})

    system = (
        "You are a helpful assistant for Seattle HR/benefits documents. "
        "Answer ONLY using the provided context. "
        "If the answer is not in the context, say you don't know. "
        "Always include bracketed citations like [1], [2]."
    )
    user = f"Question: {req.query}\n\nContext:\n" + "\n\n".join(context_blocks) + "\n\nAnswer briefly with citations."

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    resp = llm.invoke([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ])

    return {"answer": resp.content, "citations": cites}
