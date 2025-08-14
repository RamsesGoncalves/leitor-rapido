import io
import os
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app, UPLOADS_DIR
from app.storage import db


@pytest.fixture(autouse=True)
def cleanup_tmp(tmp_path, monkeypatch):
    # Isola uploads em diretório temporário
    monkeypatch.setattr("app.main.UPLOADS_DIR", tmp_path, raising=False)
    tmp_path.mkdir(parents=True, exist_ok=True)
    yield
    # limpa banco em memória
    db.clear()


def create_fake_pdf_bytes():
    # PDF mínimo válido
    return (
        b"%PDF-1.1\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n"
        b"trailer\n<<>>\n%%EOF\n"
    )


def test_upload_and_status_completed(monkeypatch):
    # Monkeypatch pdfplumber para retornar conteúdo conhecido
    class FakePage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class FakePDF:
        def __init__(self, pages):
            self.pages = pages

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_open(file_path):
        return FakePDF([FakePage("ola mundo"), FakePage("mais palavras aqui")])

    monkeypatch.setattr("app.processing.pdfplumber.open", lambda fp: fake_open(fp))

    client = TestClient(app)
    files = {"file": ("teste.pdf", create_fake_pdf_bytes(), "application/pdf")}
    res = client.post("/documents", files=files)
    assert res.status_code == 202
    data = res.json()
    doc_id = data["document_id"]

    # Força processamento síncrono chamando diretamente o handler interno
    # via endpoints de tokens que disparam reprocessamento se necessário
    res2 = client.get(f"/documents/{doc_id}/tokens")
    assert res2.status_code == 200
    tokens = res2.json()["tokens"]
    assert len(tokens) > 0

    # Atualiza progresso
    res3 = client.post(f"/documents/{doc_id}/progress", params={"page": 2})
    assert res3.status_code == 200
    # Lista documentos
    res4 = client.get("/documents")
    assert res4.status_code == 200
    docs = res4.json()
    assert any(d["id"] == doc_id and d["last_read_page"] == 2 for d in docs)

    # Exclusão
    res5 = client.delete(f"/documents/{doc_id}")
    assert res5.status_code == 200


