"""
Providers package for prompt library.

Contains embedding providers and other extensible components.
"""

from .embeddings import (
    EmbeddingProvider,
    SentenceTransformerProvider,
    LMStudioProvider,
    create_embedding_provider,
    get_default_provider,
    list_available_providers,
)

__all__ = [
    'EmbeddingProvider',
    'SentenceTransformerProvider',
    'LMStudioProvider',
    'create_embedding_provider',
    'get_default_provider',
    'list_available_providers',
]
