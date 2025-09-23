from fastapi import APIRouter, Body
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os

from dotenv import load_dotenv; load_dotenv()
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores.pgvector import PGVector as PGVectorStore

PG_CONN_STR = (
    f"postgresql+psycopg://{os.getenv('PGUSER','postgres')}:{os.getenv('PGPASSWORD','postgres')}@"
    f"{os.getenv('PGHOST','localhost')}:{os.getenv('PGPORT','5432')}/{os.getenv('PGDATABASE','seattle_rag')}"
)
COLLECTION = os.getenv("PGVECTOR_COLLECTION", "seattle_docs")

router = APIRouter()

class FrontMsg(BaseModel):
  role: str
  content: str

class ChatRequest(BaseModel):
  query: str
  top_k: int = 6
  history: Optional[List[FrontMsg]] = None  

def condense_question(llm: ChatOpenAI, history: List[FrontMsg], query: str) -> str:
  """
  Turn a follow-up into a standalone question using the last few messages.
  """
  short_hist = history[-8:] if history else []
  msgs = [{"role": "system", "content":
           "Rewrite the user's latest question as a standalone query, using prior turns for context. "
           "Return only the rewritten question."}]
  
  for m in short_hist:
    if m.role in {"user", "assistant"} and m.content:
      msgs.append({"role": m.role, "content": m.content})
  
  msgs.append({"role": "user", "content": query})
  
  out = llm.invoke(msgs)
  
  return out.content.strip() or query

@router.post("/chat")
def chat(req: ChatRequest = Body(...)) -> Dict[str, Any]:
  emb = OpenAIEmbeddings(model="text-embedding-3-small")

  vstore = PGVectorStore(
      connection_string=PG_CONN_STR,
      collection_name=COLLECTION,
      embedding_function=emb,
  )

  llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

  standalone = condense_question(llm, req.history or [], req.query)

  try:
    docs = vstore.max_marginal_relevance_search(standalone, k=req.top_k, fetch_k=max(12, req.top_k))
  except Exception:
    docs = vstore.similarity_search(standalone, k=req.top_k)

  seen = set()
  clean = []
  for d in docs:
    key = (d.metadata.get("source"), d.metadata.get("page"))
    if key in seen: continue
    seen.add(key)
    if (d.page_content or "").strip():
      clean.append(d)
  docs = clean

  if not docs:
    return {"answer": "I don't know based on the documents I have.", "citations": []}

  blocks, cites = [], []
  for i, d in enumerate(docs, 1):
    src = d.metadata.get("source")
    page = d.metadata.get("page")
    blocks.append(f"[{i}] (source: {src}, page {page})\n{d.page_content}")
    cites.append({"index": i, "source": src, "page": page})

  brief_hist = []
  for m in (req.history or [])[-6:]:
    if m.role in {"user", "assistant"} and m.content:
      brief_hist.append(f"{m.role}: {m.content}")
  convo = "\n".join(brief_hist)

  system = (
    "You are a Seattle HR/benefits assistant. "
    "Answer ONLY using the provided context. If not present, say you don't know. "
    "Be concise. Include citation markers like [1][2] that map to the chunks."
  )

  prompt = (
    f"Conversation so far (may be empty):\n{convo}\n\n"
    f"Standalone question:\n{standalone}\n\n"
    "Context:\n" + "\n\n".join(blocks) + "\n\n"
    "Answer using ONLY the context above. End with citations like [1][2]."
  )

  resp = llm.invoke([
    {"role": "system", "content": system},
    {"role": "user", "content": prompt},
  ])

  return {"answer": resp.content, "citations": cites, "standalone": standalone}
