import os
from typing import List, Tuple
from pathlib import Path

import pdfplumber

from .storage import db, update_document_after_processing, save_tokens_cache
from .textutils import group_words_with_pages, preprocess_hyphens


def _extract_words_with_pages_pdf(file_path: str) -> Tuple[List[str], List[int], int]:
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


def _extract_words_with_pages_txt(file_path: str) -> Tuple[List[str], List[int], int]:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    normalized = text.replace("\r\n", " ").replace("\n", " ")
    words = [w for w in normalized.split(" ") if w]
    words_per_page = 300
    pages = [max(1, (i // words_per_page) + 1) for i in range(len(words))]
    page_count = max(pages) if pages else 0
    return words, pages, page_count


def _extract_words_with_pages_md(file_path: str) -> Tuple[List[str], List[int], int]:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        md = f.read()
    try:
        from markdown import markdown  # type: ignore
        from bs4 import BeautifulSoup  # type: ignore
        html = markdown(md)
        text = BeautifulSoup(html, "html.parser").get_text(separator=" ")
    except Exception:
        text = md.replace("#", " ").replace("*", " ").replace("_", " ")
    normalized = text.replace("\r\n", " ").replace("\n", " ")
    words = [w for w in normalized.split(" ") if w]
    words_per_page = 300
    pages = [max(1, (i // words_per_page) + 1) for i in range(len(words))]
    page_count = max(pages) if pages else 0
    return words, pages, page_count


def _extract_words_with_pages_epub(file_path: str) -> Tuple[List[str], List[int], int]:
    try:
        from ebooklib import epub  # type: ignore
        from bs4 import BeautifulSoup  # type: ignore
    except Exception:
        raise ValueError("EPUB não suportado: instale 'ebooklib' e 'beautifulsoup4'")
    book = epub.read_epub(file_path)
    all_words: List[str] = []
    for item in book.get_items_of_type(9):  # 9 = DOCUMENT
        try:
            html = item.get_content().decode("utf-8", errors="ignore")
        except Exception:
            continue
        text = BeautifulSoup(html, "html.parser").get_text(separator=" ")
        words = [w for w in text.replace("\r\n", " ").replace("\n", " ").split(" ") if w]
        all_words.extend(words)
    words_per_page = 300
    pages = [max(1, (i // words_per_page) + 1) for i in range(len(all_words))]
    page_count = max(pages) if pages else 0
    return all_words, pages, page_count


def process_pdf(document_id: str, file_path: str) -> None:
    """Processa arquivo por extensão: pdf, txt, md, epub.
    Mantém nome para compatibilidade.
    """
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        words, pages, page_count = _extract_words_with_pages_pdf(file_path)
    elif suffix == ".txt":
        words, pages, page_count = _extract_words_with_pages_txt(file_path)
    elif suffix == ".md":
        words, pages, page_count = _extract_words_with_pages_md(file_path)
    elif suffix == ".epub":
        words, pages, page_count = _extract_words_with_pages_epub(file_path)
    else:
        raise ValueError("Formato de arquivo não suportado")
    # Corrige hífens sempre que possível
    try:
        words, pages = preprocess_hyphens(words, pages)
    except Exception:
        pass
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


