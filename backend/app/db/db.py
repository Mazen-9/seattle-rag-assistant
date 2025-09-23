import uuid
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from datetime import datetime
import os

PG_CONN_STR = (
    f"postgresql+psycopg://{os.getenv('PGUSER','postgres')}:{os.getenv('PGPASSWORD','postgres')}@"
    f"{os.getenv('PGHOST','localhost')}:{os.getenv('PGPORT','5432')}/{os.getenv('PGDATABASE','seattle_rag')}"
)

engine = create_engine(PG_CONN_STR, future=True)

DDL_CONVERSATIONS = """
CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY,
  title TEXT NOT NULL DEFAULT 'New chat',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

DDL_MESSAGES = """
CREATE TABLE IF NOT EXISTS messages (
  id BIGSERIAL PRIMARY KEY,
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user','assistant')),
  content TEXT NOT NULL,
  citations JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

IDX = """
CREATE INDEX IF NOT EXISTS idx_messages_convo_created
ON messages(conversation_id, created_at);
"""

def init_db():
    with engine.begin() as conn:
        conn.execute(text(DDL_CONVERSATIONS))
        conn.execute(text(DDL_MESSAGES))
        conn.execute(text(IDX))

def create_session(title: str = "New chat") -> str:
    sid = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO conversations(id, title) VALUES (:id, :title)"),
                     {"id": sid, "title": title})
    return sid

def list_sessions() -> list[dict]:
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT c.id, c.title,
                   COALESCE(MAX(m.created_at), c.created_at) AS last_activity
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            GROUP BY c.id
            ORDER BY last_activity DESC
        """)).mappings().all()
    return [dict(r) for r in rows]

def rename_session(session_id: str, title: str):
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE conversations SET title=:t, updated_at=now() WHERE id=:id
        """), {"t": title, "id": session_id})

def get_messages(session_id: str, limit: int = 50) -> list[dict]:
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT role, content, citations, created_at
            FROM messages
            WHERE conversation_id=:sid
            ORDER BY created_at ASC
            LIMIT :lim
        """), {"sid": session_id, "lim": limit}).mappings().all()
    return [dict(r) for r in rows]

def add_message(session_id: str, role: str, content: str, citations: Dict[str, Any] | None = None):
    with engine.begin() as conn:
        conn.execute(text("""
           INSERT INTO messages(conversation_id, role, content, citations)
           VALUES (:sid, :role, :content, :citations)
        """), {"sid": session_id, "role": role, "content": content, "citations": citations})
