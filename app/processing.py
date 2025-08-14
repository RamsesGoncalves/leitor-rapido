import os
from typing import List, Tuple

import pdfplumber

from .storage import db, update_document_after_processing, save_tokens_cache
from .textutils import group_words_with_pages, preprocess_hyphens


def _extract_words_with_pages(file_path: str) -> Tuple[List[str], List[int], int]:
    words: List[str] = []
    pages: List[int] = []
    page_count = 0
    with pdfplumber.open(file_path) as pdf:
        page_count = len(pdf.pages)
        for idx, page in enumerate(pdf.pages):
            page_num = idx + 1  # 1-based
            page_text = page.extract_text() or ""
            normalized = page_text.replace("\r\n", " ").replace("\n", " ")
            page_words = [w for w in normalized.split(" ") if w]
            words.extend(page_words)
            pages.extend([page_num] * len(page_words))
    return words, pages, page_count


def process_pdf(document_id: str, file_path: str) -> None:
    # Extrai palavras por página e atualiza o banco em memória
    words, pages, page_count = _extract_words_with_pages(file_path)
    # Corrige hífens antes do agrupamento de monossílabos
    words, pages = preprocess_hyphens(words, pages)
    tokens, token_pages = group_words_with_pages(words, pages)
    # Aplica regra nova: bloco que termina em monossílabo com pontuação conta como 1
    from .textutils import build_tokens_with_rules
    tokens, token_pages, token_weights = build_tokens_with_rules(tokens, token_pages)
    db[document_id] = {
        "status": "completed",
        "words": words,
        "tokens": tokens,
        "token_pages": token_pages,
        "page_count": page_count,
        "token_weights": token_weights,
        "file_path": file_path,
    }
    # Mantemos o arquivo para visualização posterior via endpoint
    try:
        update_document_after_processing(document_id, page_count, status="completed")
    except Exception:
        # Persistência não deve quebrar o processamento principal
        pass
    try:
        save_tokens_cache(
            document_id,
            tokens=tokens,
            token_pages=token_pages,
            token_weights=token_weights,
            page_count=page_count,
        )
    except Exception:
        pass


