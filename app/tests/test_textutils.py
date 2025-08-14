import pytest

from app.textutils import (
    is_monosyllabic,
    preprocess_hyphens,
    group_words_with_pages,
    build_tokens_with_rules,
)


def test_is_monosyllabic_basic():
    assert is_monosyllabic("no") is True
    assert is_monosyllabic("olá") is False
    assert is_monosyllabic("a,") is True


def test_preprocess_hyphens_merge_line_break():
    words = ["desenvolvi-", "mento", "é", "legal"]
    pages = [1, 1, 1, 1]
    out_w, out_p = preprocess_hyphens(words, pages)
    assert out_w == ["desenvolvimento", "é", "legal"]
    assert out_p == [1, 1, 1]


def test_preprocess_hyphens_middle_dash():
    words = ["e", "-", "mail"]
    pages = [1, 1, 1]
    out_w, out_p = preprocess_hyphens(words, pages)
    assert out_w == ["e-mail"]
    assert out_p == [1]


def test_group_words_with_pages_monosyllables():
    words = ["eu", "gosto", "de", "café", "."]
    pages = [1, 1, 1, 1, 1]
    t, tp = group_words_with_pages(words, pages)
    assert t[0].startswith("eu ")
    assert tp[0] == 1


def test_build_tokens_with_rules_counts_and_weights():
    words = ["A", "vida", "é", "boa,", "certo?"]
    pages = [2, 2, 2, 2, 2]
    tokens, token_pages, token_weights = build_tokens_with_rules(words, pages)
    assert len(tokens) == len(token_pages) == len(token_weights)
    # Deve manter sequência com pesos coerentes (>0)
    assert all(w > 0 for w in token_weights)
    # Páginas propagadas
    assert set(token_pages) == {2}


