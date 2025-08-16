from typing import Any, Dict, List, Optional
from pathlib import Path
import sqlite3
from datetime import datetime
import json


# Banco de dados em memória para conteúdo processado (tokens/words)
# Exemplo: {"doc-123": {"status": "completed", "words": ["olá", "mundo"]}}
db: Dict[str, Dict[str, Any]] = {}


# Persistência leve em SQLite para metadados dos documentos
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SQLITE_PATH = DATA_DIR / "leitor.db"
TOKENS_DIR = DATA_DIR / "tokens"
TOKENS_DIR.mkdir(parents=True, exist_ok=True)


def _get_conn() -> sqlite3.Connection:
    return sqlite3.connect(SQLITE_PATH, check_same_thread=False)


def init_db() -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                mime_type TEXT,
                uploaded_at TEXT NOT NULL,
                status TEXT NOT NULL,
                page_count INTEGER DEFAULT 0,
                last_read_page INTEGER DEFAULT 1,
                last_token_index INTEGER DEFAULT 0
            )
            """
        )
        # Migração leve: garantir coluna mime_type
        try:
            cur = conn.execute("PRAGMA table_info(documents)")
            cols = [r[1] for r in cur.fetchall()]
            if "mime_type" not in cols:
                conn.execute("ALTER TABLE documents ADD COLUMN mime_type TEXT")
            if "last_token_index" not in cols:
                conn.execute("ALTER TABLE documents ADD COLUMN last_token_index INTEGER DEFAULT 0")
        except Exception:
            pass
        conn.commit()


def insert_document_record(document_id: str, filename: str, file_path: str, mime_type: str | None, status: str = "processing") -> None:
    uploaded_at = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO documents (id, filename, file_path, mime_type, uploaded_at, status, page_count, last_read_page) VALUES (?, ?, ?, ?, ?, COALESCE((SELECT status FROM documents WHERE id = ?), ?), COALESCE((SELECT page_count FROM documents WHERE id = ?), 0), COALESCE((SELECT last_read_page FROM documents WHERE id = ?), 1))",
            (document_id, filename, file_path, mime_type, uploaded_at, document_id, status, document_id, document_id),
        )
        conn.commit()


def update_document_after_processing(document_id: str, page_count: int, status: str = "completed") -> None:
    with _get_conn() as conn:
        conn.execute(
            "UPDATE documents SET status = ?, page_count = ?, last_read_page = COALESCE(last_read_page, 1) WHERE id = ?",
            (status, page_count, document_id),
        )
        conn.commit()


def list_documents() -> List[Dict[str, Any]]:
    with _get_conn() as conn:
        cur = conn.execute(
            "SELECT id, filename, status, page_count, last_read_page, uploaded_at, mime_type, last_token_index FROM documents ORDER BY uploaded_at DESC"
        )
        rows = cur.fetchall()
    documents = [
        {
            "id": r[0],
            "filename": r[1],
            "status": r[2],
            "page_count": int(r[3] or 0),
            "last_read_page": int(r[4] or 1),
            "uploaded_at": r[5],
            "mime_type": r[6],
            "last_token_index": int(r[7] or 0),
        }
        for r in rows
    ]
    return documents


def get_document_meta(document_id: str) -> Optional[Dict[str, Any]]:
    with _get_conn() as conn:
        cur = conn.execute(
            "SELECT id, filename, status, page_count, last_read_page, uploaded_at, file_path, mime_type, last_token_index FROM documents WHERE id = ?",
            (document_id,),
        )
        r = cur.fetchone()
    if not r:
        return None
    return {
        "id": r[0],
        "filename": r[1],
        "status": r[2],
        "page_count": int(r[3] or 0),
        "last_read_page": int(r[4] or 1),
        "uploaded_at": r[5],
        "file_path": r[6],
        "mime_type": r[7],
        "last_token_index": int(r[8] or 0),
    }
def update_progress(document_id: str, last_read_page: int | None = None, last_token_index: int | None = None) -> None:
    with _get_conn() as conn:
        if last_read_page is not None and last_token_index is not None:
            conn.execute("UPDATE documents SET last_read_page = ?, last_token_index = ? WHERE id = ?", (last_read_page, last_token_index, document_id))
        elif last_read_page is not None:
            conn.execute("UPDATE documents SET last_read_page = ? WHERE id = ?", (last_read_page, document_id))
        elif last_token_index is not None:
            conn.execute("UPDATE documents SET last_token_index = ? WHERE id = ?", (last_token_index, document_id))
        else:
            return
        conn.commit()


def update_last_read_page(document_id: str, last_read_page: int) -> None:
    with _get_conn() as conn:
        conn.execute(
            "UPDATE documents SET last_read_page = ? WHERE id = ?",
            (last_read_page, document_id),
        )
        conn.commit()


def delete_document_record(document_id: str) -> None:
    with _get_conn() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        conn.commit()


def save_tokens_cache(document_id: str, *, tokens: List[str], token_pages: List[int], token_weights: List[int], page_count: int) -> None:
    payload = {
        "tokens": tokens,
        "pages": token_pages,
        "weights": token_weights,
        "page_count": page_count,
    }
    target = TOKENS_DIR / f"{document_id}.json"
    with open(target, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def load_tokens_cache(document_id: str) -> Optional[Dict[str, Any]]:
    target = TOKENS_DIR / f"{document_id}.json"
    if not target.exists():
        return None
    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        # validações mínimas
        if not isinstance(data.get("tokens"), list):
            return None
        return data
    except Exception:
        return None


