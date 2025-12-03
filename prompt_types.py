"""Shared typing helpers for prompt metadata structures."""

from __future__ import annotations

from typing import TypedDict, Optional, TypeAlias


class PromptMetadata(TypedDict, total=False):
    """Metadata describing a single prompt chunk."""

    file_path: str
    file_name: str
    category: str
    type: str
    keywords: str
    session_id: str
    rol: str
    contexto: str
    objetivo: str
    full_text: str
    chunk_index: str
    total_chunks: str


class SearchResultDict(TypedDict, total=False):
    """Search result payload returned by RAG queries."""

    text: str
    metadata: PromptMetadata
    distance: Optional[float]


SearchResult: TypeAlias = SearchResultDict
