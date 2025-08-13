from pydantic import BaseModel
from typing import List


class DocumentStatus(BaseModel):
    status: str
    word_count: int


class DocumentWords(BaseModel):
    words: List[str]


class DocumentUploadResponse(BaseModel):
    document_id: str
    status: str


class DocumentTokens(BaseModel):
    tokens: List[str]
    pages: List[int]
    page_count: int
    weights: List[int]


