"""
Embedding providers for prompt library RAG system.

Supports multiple embedding backends:
- sentence-transformers (default, local)
- LMStudio (via HTTP API)
- Extensible for future providers (OpenAI, Ollama, etc.)
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, cast
import logging

from config import CONFIG, Config
from exceptions import EmbeddingProviderError

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: Text samples to embed.

        Returns:
            List[List[float]]: Embedding vectors for each text.
        """

    @abstractmethod
    def get_dimension(self) -> int:
        """Return the dimensionality of the embeddings.

        Returns:
            int: Vector size for each produced embedding.
        """

    @abstractmethod
    def get_name(self) -> str:
        """Return the provider identifier used for logging and telemetry.

        Returns:
            str: Human-readable provider name.
        """


class SentenceTransformerProvider(EmbeddingProvider):
    """Embedding provider backed by ``sentence-transformers`` models."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the provider with a local transformer model.

        Args:
            model_name: Name of the pretrained SentenceTransformer model to load.

        Raises:
            EmbeddingProviderError: If the ``sentence-transformers`` package is missing.
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - defensive branch
            raise EmbeddingProviderError(
                "sentence-transformers is not installed. Install it via 'pip install sentence-transformers'."
            ) from exc

        self.model_name = model_name
        logger.info("Loading sentence-transformers model: %s", model_name)

        self.model = SentenceTransformer(model_name)
        embedding_dimension = cast(int, self.model.get_sentence_embedding_dimension())
        self.dimension: int = embedding_dimension

        logger.info("Model loaded. Dimension: %s", self.dimension)

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings locally using the configured transformer model."""
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return cast(List[List[float]], embeddings.tolist())

    def get_dimension(self) -> int:
        """Return the embedding dimension."""
        return self.dimension

    def get_name(self) -> str:
        """Return a descriptive provider identifier."""
        return f"sentence-transformer/{self.model_name}"


class LMStudioProvider(EmbeddingProvider):
    """Embedding provider that proxies LMStudio's OpenAI-compatible API."""

    def __init__(
        self,
        base_url: str = "http://localhost:1234",
        model_name: str = "nomic-embed-text",
        dimension: int = 768,
        timeout: int = 30,
        batch_size: int = 10
    ):
        """Initialize the provider and validate remote connectivity.

        Args:
            base_url: LMStudio API base URL.
            model_name: Remote embedding model identifier.
            dimension: Expected embedding dimensionality.
            timeout: HTTP timeout in seconds for each request.
            batch_size: Maximum texts per embedding batch.

        Raises:
            EmbeddingProviderError: If the ``requests`` dependency or LMStudio API is unavailable.
        """
        try:
            import requests
        except ImportError as exc:  # pragma: no cover - defensive branch
            raise EmbeddingProviderError(
                "requests is not installed. Install it via 'pip install requests'."
            ) from exc

        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.dimension: int = dimension
        self.timeout = timeout
        self.batch_size = batch_size
        self.session: Any = requests.Session()
        self._requests: Any = requests

        logger.info("Initializing LMStudio provider: %s", base_url)

        try:
            response = self.session.get(
                f"{self.base_url}/v1/models",
                timeout=5
            )
            response.raise_for_status()
            models = response.json()
            logger.info("Connected to LMStudio. Available models: %s", len(models.get('data', [])))
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning(
                "Could not connect to LMStudio at %s: %s. Ensure the service is running.",
                base_url,
                exc,
            )
            raise EmbeddingProviderError(
                f"Cannot connect to LMStudio at {base_url}. Error: {exc}"
            ) from exc

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using LMStudio's HTTP API."""
        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            try:
                response = self.session.post(
                    f"{self.base_url}/v1/embeddings",
                    json={"model": self.model_name, "input": batch},
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                batch_embeddings = sorted(data['data'], key=lambda item: item['index'])
                for item in batch_embeddings:
                    all_embeddings.append(item['embedding'])
            except self._requests.exceptions.RequestException as exc:  # pragma: no cover - network dependent
                logger.error("Error calling LMStudio API: %s", exc)
                raise EmbeddingProviderError(
                    f"Failed to get embeddings from LMStudio: {exc}"
                ) from exc

        return all_embeddings

    def get_dimension(self) -> int:
        """Return the configured embedding dimension."""
        return self.dimension

    def get_name(self) -> str:
        """Return a descriptive provider identifier."""
        return f"lmstudio/{self.model_name}"


def create_embedding_provider(
    provider_type: Optional[str] = None,
    *,
    config: Config = CONFIG,
    **kwargs: Any,
) -> EmbeddingProvider:
    """Instantiate an embedding provider using configuration defaults.

    Args:
        provider_type: Optional override for the configured provider type.
        config: Shared application configuration.
        **kwargs: Provider-specific keyword overrides (e.g., ``model_name``).

    Returns:
        EmbeddingProvider: Ready-to-use embedding provider instance.

    Raises:
        EmbeddingProviderError: If the requested provider cannot be initialized.
    """
    selected_provider = (provider_type or config.embedding_provider).lower().strip()
    logger.info("Creating embedding provider: %s", selected_provider)

    if selected_provider in {"lmstudio", "lm-studio", "lm_studio"}:
        provider_config: Dict[str, Any] = {
            "base_url": config.lmstudio_url,
            "model_name": config.lmstudio_model,
            "dimension": config.lmstudio_dimension,
        }
        provider_config.update(kwargs)
        try:
            return LMStudioProvider(**provider_config)
        except EmbeddingProviderError as exc:
            logger.warning(
                "Failed to initialize LMStudio provider (%s). Falling back to sentence-transformer.",
                exc,
            )
            return SentenceTransformerProvider(model_name=config.embedding_model)

    if selected_provider in {"sentence-transformer", "sentence_transformer", "st", "default"}:
        st_config: Dict[str, Any] = {"model_name": config.embedding_model}
        st_config.update(kwargs)
        return SentenceTransformerProvider(**st_config)

    logger.warning("Unknown provider type: %s. Falling back to sentence-transformer.", selected_provider)
    return SentenceTransformerProvider(model_name=config.embedding_model)


# Convenience functions
def get_default_provider(config: Config = CONFIG) -> EmbeddingProvider:
    """Return the default embedding provider defined by ``Config``."""
    return create_embedding_provider(config=config)


def list_available_providers() -> List[str]:
    """List available embedding provider identifiers."""
    return [
        'sentence-transformer',
        'lmstudio',
    ]
