import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi import status

from .models import DocumentStatus, DocumentUploadResponse, DocumentWords, DocumentTokens
from .storage import db, init_db, insert_document_record, list_documents, update_document_after_processing, get_document_meta, update_last_read_page, delete_document_record, load_tokens_cache
from .processing import process_pdf


BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


app = FastAPI(title="Leitor Rápido PDF API", version="0.1.0")

# CORS para permitir o front local (ajuste conforme necessário)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.post("/documents", response_model=DocumentUploadResponse, status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    allowed = {"application/pdf", "text/plain", "text/markdown", "application/epub+zip"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Formato não suportado")

    document_id = str(uuid.uuid4())
    # Determina extensão correta
    from pathlib import Path as _Path
    original_suffix = _Path(file.filename or "").suffix.lower()
    mime_to_ext = {
        "application/pdf": ".pdf",
        "text/plain": ".txt",
        "text/markdown": ".md",
        "application/epub+zip": ".epub",
    }
    ext = original_suffix if original_suffix in {".pdf", ".txt", ".md", ".epub"} else mime_to_ext.get(file.content_type, ".bin")
    dest_path = UPLOADS_DIR / f"{document_id}{ext}"

    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)

    db[document_id] = {"status": "processing", "words": []}
    insert_document_record(document_id, file.filename, str(dest_path), file.content_type, status="processing")

    background_tasks.add_task(process_pdf, document_id, str(dest_path))

    return DocumentUploadResponse(document_id=document_id, status="processing")


@app.get("/documents")
def list_all_documents():
    return list_documents()


@app.get("/documents/{document_id}/status", response_model=DocumentStatus)
def get_document_status(document_id: str):
    if document_id not in db:
        # Pode ter reiniciado o servidor; tenta pegar do meta e indicar status
        meta = get_document_meta(document_id)
        if not meta:
            raise HTTPException(status_code=404, detail="Documento não encontrado")
        status = meta.get("status", "processing")
        # Caso completed mas tokens não estejam em memória, força word_count 0
        return DocumentStatus(status=status, word_count=0)
    entry = db[document_id]
    words = entry.get("words") or []
    status = entry.get("status", "processing")
    word_count = len(words) if status == "completed" else 0
    return DocumentStatus(status=status, word_count=word_count)


@app.get("/documents/{document_id}/words", response_model=DocumentWords)
def get_document_words(document_id: str):
    if document_id not in db:
        cached = load_tokens_cache(document_id)
        if cached is not None:
            db[document_id] = {
                "status": "completed",
                "words": [],
                "tokens": cached.get("tokens", []),
                "token_pages": cached.get("pages", []),
                "token_weights": cached.get("weights", []),
                "page_count": cached.get("page_count", 0),
            }
        else:
            # tenta reprocessar do disco
            meta = get_document_meta(document_id)
            if not meta or not meta.get("file_path") or not os.path.exists(meta["file_path"]):
                raise HTTPException(status_code=404, detail="Documento não encontrado")
            try:
                process_pdf(document_id, meta["file_path"])  # repopula memória
            except Exception:
                raise HTTPException(status_code=422, detail="Falha ao carregar documento")
    entry = db[document_id]
    status = entry.get("status", "processing")
    if status != "completed":
        raise HTTPException(status_code=422, detail="Documento ainda não processado")
    words = entry.get("words") or []
    return DocumentWords(words=words)


@app.get("/documents/{document_id}/tokens", response_model=DocumentTokens)
def get_document_tokens(document_id: str):
    if document_id not in db:
        cached = load_tokens_cache(document_id)
        if cached is not None:
            db[document_id] = {
                "status": "completed",
                "words": [],
                "tokens": cached.get("tokens", []),
                "token_pages": cached.get("pages", []),
                "token_weights": cached.get("weights", []),
                "page_count": cached.get("page_count", 0),
            }
        else:
            # tenta reprocessar do disco
            meta = get_document_meta(document_id)
            if not meta or not meta.get("file_path") or not os.path.exists(meta["file_path"]):
                raise HTTPException(status_code=404, detail="Documento não encontrado")
            try:
                process_pdf(document_id, meta["file_path"])  # repopula memória
            except Exception:
                raise HTTPException(status_code=422, detail="Falha ao carregar documento")
    entry = db[document_id]
    status = entry.get("status", "processing")
    if status != "completed":
        raise HTTPException(status_code=422, detail="Documento ainda não processado")
    tokens = entry.get("tokens") or []
    token_pages = entry.get("token_pages") or [1] * len(tokens)
    token_weights = entry.get("token_weights") or [1] * len(tokens)
    page_count = entry.get("page_count", 0)
    return DocumentTokens(tokens=tokens, pages=token_pages, page_count=page_count, weights=token_weights)


@app.get("/documents/{document_id}/file")
def get_document_file(document_id: str):
    # Procurar em memória e depois em meta
    entry = db.get(document_id)
    file_path = entry.get("file_path") if entry else None
    if not file_path:
        meta = get_document_meta(document_id)
        if meta:
            file_path = meta.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo não disponível")
    return FileResponse(file_path, media_type="application/pdf")


@app.post("/documents/{document_id}/progress")
def set_last_read_page(document_id: str, page: int):
    meta = get_document_meta(document_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    if page < 1 or (meta.get("page_count") and page > meta.get("page_count")):
        raise HTTPException(status_code=400, detail="Página inválida")
    update_last_read_page(document_id, page)
    return JSONResponse({"ok": True, "last_read_page": page})


@app.delete("/documents/{document_id}")
def delete_document(document_id: str):
    meta = get_document_meta(document_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    file_path = meta.get("file_path")
    # remove do armazenamento em memória
    if document_id in db:
        try:
            del db[document_id]
        except Exception:
            pass
    # remove do disco
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass
    # remove do banco
    delete_document_record(document_id)
    return JSONResponse({"ok": True}, status_code=status.HTTP_200_OK)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


