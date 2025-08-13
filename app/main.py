import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse

from .models import DocumentStatus, DocumentUploadResponse, DocumentWords, DocumentTokens
from .storage import db
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


@app.post("/documents", response_model=DocumentUploadResponse, status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Somente PDFs são aceitos")

    document_id = str(uuid.uuid4())
    dest_path = UPLOADS_DIR / f"{document_id}.pdf"

    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)

    db[document_id] = {"status": "processing", "words": []}

    background_tasks.add_task(process_pdf, document_id, str(dest_path))

    return DocumentUploadResponse(document_id=document_id, status="processing")


@app.get("/documents/{document_id}/status", response_model=DocumentStatus)
def get_document_status(document_id: str):
    if document_id not in db:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    entry = db[document_id]
    words = entry.get("words") or []
    status = entry.get("status", "processing")
    word_count = len(words) if status == "completed" else 0
    return DocumentStatus(status=status, word_count=word_count)


@app.get("/documents/{document_id}/words", response_model=DocumentWords)
def get_document_words(document_id: str):
    if document_id not in db:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    entry = db[document_id]
    status = entry.get("status", "processing")
    if status != "completed":
        raise HTTPException(status_code=422, detail="Documento ainda não processado")
    words = entry.get("words") or []
    return DocumentWords(words=words)


@app.get("/documents/{document_id}/tokens", response_model=DocumentTokens)
def get_document_tokens(document_id: str):
    if document_id not in db:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
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
    if document_id not in db:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    entry = db[document_id]
    file_path = entry.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo não disponível")
    return FileResponse(file_path, media_type="application/pdf")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


