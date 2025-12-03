"""Custom exception hierarchy for the MCP Prompt Library."""

from __future__ import annotations


class PromptLibraryError(Exception):
    """Base class for all domain-specific errors."""


class ConfigurationError(PromptLibraryError):
    """Raised when configuration values are missing or invalid."""


class InvalidPathError(PromptLibraryError):
    """Raised when a user provides a path outside the allowed directories."""


class PromptNotFoundError(PromptLibraryError):
    """Raised when a requested prompt cannot be located."""


class RAGInitializationError(PromptLibraryError):
    """Raised when the RAG subsystem fails to initialize or index data."""


class EmbeddingProviderError(PromptLibraryError):
    """Raised when embedding providers cannot be instantiated or queried."""
