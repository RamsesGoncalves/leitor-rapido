from __future__ import annotations

import re
from typing import List, Tuple
import string


_VOWELS = "aeiouáéíóúâêôãõàüy"
_EDGE_PUNCT_RE = re.compile(r"^[\W_]+|[\W_]+$", re.UNICODE)
_VOWEL_GROUPS_RE = re.compile("[" + _VOWELS + "]+", re.IGNORECASE)


def _strip_punctuation_edges(text: str) -> str:
    return _EDGE_PUNCT_RE.sub("", text)


def is_monosyllabic(raw_word: str) -> bool:
    word = _strip_punctuation_edges(raw_word.lower())
    if not word:
        return False
    if len(word) <= 2:
        return True
    matches = _VOWEL_GROUPS_RE.findall(word)
    syllables = len(matches)
    return syllables <= 1


def group_monosyllables_with_next(words: List[str]) -> List[str]:
    tokens: List[str] = []
    i = 0
    n = len(words)
    while i < n:
        current = words[i]
        next_word = words[i + 1] if i + 1 < n else None
        prev_word = words[i - 1] if i - 1 >= 0 else None
        # Não agrupar monossílabo se o atual termina em ponto final, ou se o anterior termina em ponto final
        if (
            is_monosyllabic(current)
            and next_word is not None
            and not _has_trailing_dot(current)
            and not (prev_word is not None and _has_trailing_dot(prev_word))
        ):
            tokens.append(f"{current} {next_word}")
            i += 2
        else:
            tokens.append(current)
            i += 1
    return tokens


def group_words_with_pages(words: List[str], pages: List[int]) -> tuple[List[str], List[int]]:
    """Agrupa monossílabos com a próxima palavra e propaga a página do primeiro termo do grupo.

    Retorna (tokens, token_pages).
    """
    assert len(words) == len(pages)
    tokens: List[str] = []
    token_pages: List[int] = []
    i = 0
    n = len(words)
    while i < n:
        current = words[i]
        current_page = pages[i]
        next_word = words[i + 1] if i + 1 < n else None
        prev_word = words[i - 1] if i - 1 >= 0 else None
        if (
            is_monosyllabic(current)
            and next_word is not None
            and not _has_trailing_dot(current)
            and not (prev_word is not None and _has_trailing_dot(prev_word))
        ):
            tokens.append(f"{current} {next_word}")
            token_pages.append(current_page)
            i += 2
        else:
            tokens.append(current)
            token_pages.append(current_page)
            i += 1
    return tokens, token_pages


def _is_alpha_word(token: str) -> bool:
    return token and all(ch.isalpha() or ch in "áéíóúâêôãõàüÁÉÍÓÚÂÊÔÃÕÀÜ" for ch in token)


def preprocess_hyphens(words: List[str], pages: List[int]) -> tuple[List[str], List[int]]:
    """Corrige casos comuns de hifenização na extração:
    1) Quebra de linha: "desenvolvi-" + "mento" -> "desenvolvimento" (remove '-')
    2) Separação em três tokens: "e" "-" "mail" -> "e-mail"
    Mantém a página do primeiro termo do grupo.
    """
    assert len(words) == len(pages)

    result_words: List[str] = []
    result_pages: List[int] = []
    i = 0
    n = len(words)
    while i < n:
        current = words[i]
        current_page = pages[i]
        next_word = words[i + 1] if i + 1 < n else None

        # Caso 2: token '-' isolado entre palavras
        if (
            current != "-"
            and next_word == "-"
            and (i + 2) < n
            and _is_alpha_word(words[i + 2])
        ):
            merged = f"{current}-{words[i + 2]}"
            result_words.append(merged)
            result_pages.append(current_page)
            i += 3
            continue

        # Caso 1: quebra de linha com hífen no final
        if (
            isinstance(current, str)
            and current.endswith("-")
            and next_word is not None
            and _is_alpha_word(next_word)
        ):
            merged = current[:-1] + next_word
            result_words.append(merged)
            result_pages.append(current_page)
            i += 2
            continue

        # Padrão: mantém token
        result_words.append(current)
        result_pages.append(current_page)
        i += 1

    return result_words, result_pages


_TRAIL_PUNCT = set([",", ".", ":", ";", "?", "!", "…"])


def _has_trailing_punct(token: str) -> bool:
    t = token.strip()
    return bool(t) and t[-1] in _TRAIL_PUNCT


def _has_trailing_dot(token: str) -> bool:
    t = token.strip()
    return bool(t) and t.endswith(".")

def _count_words_in_token(token: str) -> int:
    return len([w for w in token.strip().split() if w])


def build_tokens_with_rules(words: List[str], pages: List[int]) -> Tuple[List[str], List[int], List[int]]:
    """Constrói tokens aplicando as regras:
    1) Monossílabos agrupam com a próxima palavra (regra anterior)
    2) Se um token for monossílabo e terminar com pontuação, agrupa toda a
       sequência desde a última pontuação até este token como UM ÚNICO TOKEN
       com peso 1 (conta como uma palavra).

    Retorna (tokens, token_pages, token_weights)
    """
    assert len(words) == len(pages)

    tokens: List[str] = []
    token_pages: List[int] = []
    token_weights: List[int] = []

    seg_tokens: List[str] = []
    seg_first_page: int | None = None

    i = 0
    n = len(words)
    while i < n:
        current = words[i]
        current_page = pages[i]
        stripped = _strip_punctuation_edges(current)

        # Regra 2 AJUSTADA: monossílabo (alfabético) com pontuação no final encerra o segmento,
        # porém NÃO agrega todo o trecho em um único token. Em vez disso, emitimos os tokens
        # do segmento individualmente e o token atual com peso 1. Assim evitamos frases enormes
        # virarem um único token visual.
        # Observação: não disparamos esta regra para tokens numéricos como "1950,".
        if is_monosyllabic(stripped) and _has_trailing_punct(current) and _is_alpha_word(stripped):
            if seg_first_page is None:
                tokens.append(current)
                token_pages.append(current_page)
                token_weights.append(1)
            else:
                for t in seg_tokens:
                    tokens.append(t)
                    token_pages.append(seg_first_page)
                    token_weights.append(_count_words_in_token(t))
                seg_tokens = []
                # atual é emitido com peso 1 e página própria
                tokens.append(current)
                token_pages.append(current_page)
                token_weights.append(1)
                seg_first_page = None
            i += 1
            continue

        # Regra 1: monossílabo agrupa com próxima palavra (se existir)
        # NÃO agrupar se o token atual termina com ponto final, ou se o token anterior termina com ponto final
        if (
            is_monosyllabic(stripped)
            and (i + 1) < n
            and not _has_trailing_dot(current)
            and not (i - 1 >= 0 and _has_trailing_dot(words[i - 1]))
        ):
            combined = f"{current} {words[i + 1]}"
            if seg_first_page is None:
                seg_first_page = current_page
            seg_tokens.append(combined)
            i += 2
            # Se terminou com pontuação, finalizar segmento (modo normal)
            if _has_trailing_punct(combined):
                for t in seg_tokens:
                    tokens.append(t)
                    token_pages.append(seg_first_page)
                    token_weights.append(_count_words_in_token(t))
                    seg_first_page = seg_first_page  # unchanged
                seg_tokens = []
                seg_first_page = None
            continue

        # Token normal
        if seg_first_page is None:
            seg_first_page = current_page
        seg_tokens.append(current)
        i += 1
        if _has_trailing_punct(current):
            # Finaliza segmento com tokens individuais
            for t in seg_tokens:
                tokens.append(t)
                token_pages.append(seg_first_page)
                token_weights.append(_count_words_in_token(t))
            seg_tokens = []
            seg_first_page = None

    # Flush final
    if seg_tokens:
        for t in seg_tokens:
            tokens.append(t)
            token_pages.append(seg_first_page if seg_first_page is not None else pages[-1])
            token_weights.append(_count_words_in_token(t))

    return tokens, token_pages, token_weights


