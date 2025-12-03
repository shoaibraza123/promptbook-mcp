"""Centralized configuration management for the MCP Prompt Library."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


def _resolve_path(value: str | None, default: Path) -> Path:
    """Return an absolute :class:`Path` using ``value`` or a ``default`` fallback."""
    if value:
        candidate = Path(value)
        if candidate.is_absolute():
            return candidate
        base_reference = default if default.is_dir() else default.parent
        return (base_reference / candidate).resolve()
    return default


@dataclass(frozen=True)
class Config:
    """Immutable application settings loaded once from the environment."""

    base_dir: Path
    prompts_dir: Path
    sessions_dir: Path
    vectordb_dir: Path
    logs_dir: Path
    log_file: Path
    log_level: str
    embedding_provider: str
    embedding_model: str
    lmstudio_url: str
    lmstudio_model: str
    lmstudio_dimension: int
    chunk_size: int
    chunk_overlap: int
    rag_enabled: bool
    auto_reindex_interval: int
    watcher_enabled: bool
    server_timeout: int
    healthcheck_path: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Config":
        """Build a configuration instance from environment variables.

        Args:
            env: Optional mapping that overrides ``os.environ`` for testing.

        Returns:
            Config: Fully-populated configuration object ready for dependency injection.
        """
        env_map = dict(env or os.environ)
        base_dir = _resolve_path(env_map.get("BASE_DIR"), Path(__file__).resolve().parent)
        prompts_dir = _resolve_path(env_map.get("PROMPTS_DIR"), base_dir / "prompts")
        sessions_dir = _resolve_path(env_map.get("SESSIONS_DIR"), base_dir / "sessions")
        vectordb_dir = _resolve_path(env_map.get("VECTOR_DB_DIR"), prompts_dir / ".vectordb")
        logs_dir = _resolve_path(env_map.get("LOGS_DIR"), base_dir)
        log_file = _resolve_path(env_map.get("LOG_FILE"), logs_dir / "mcp_server.log")

        return cls(
            base_dir=base_dir,
            prompts_dir=prompts_dir,
            sessions_dir=sessions_dir,
            vectordb_dir=vectordb_dir,
            logs_dir=logs_dir,
            log_file=log_file,
            log_level=env_map.get("LOG_LEVEL", "INFO"),
            embedding_provider=env_map.get("EMBEDDING_PROVIDER", "sentence-transformer"),
            embedding_model=env_map.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            lmstudio_url=env_map.get("LMSTUDIO_URL", "http://localhost:1234"),
            lmstudio_model=env_map.get("LMSTUDIO_MODEL", "nomic-embed-text"),
            lmstudio_dimension=int(env_map.get("LMSTUDIO_DIMENSION", "768")),
            chunk_size=int(env_map.get("CHUNK_SIZE", "500")),
            chunk_overlap=int(env_map.get("CHUNK_OVERLAP", "100")),
            rag_enabled=env_map.get("ENABLE_RAG", "true").lower() == "true",
            auto_reindex_interval=int(env_map.get("AUTO_REINDEX_INTERVAL", "30")),
            watcher_enabled=env_map.get("ENABLE_FILE_WATCHER", "true").lower() == "true",
            server_timeout=int(env_map.get("SERVER_TIMEOUT", "30")),
            healthcheck_path=env_map.get("HEALTHCHECK_PATH", "healthcheck"),
        )

    def ensure_directories(self) -> None:
        """Create the directories required for runtime artifacts.

        Raises:
            OSError: If the process lacks filesystem permissions.
        """
        for directory in (self.prompts_dir, self.sessions_dir, self.vectordb_dir, self.logs_dir):
            directory.mkdir(parents=True, exist_ok=True)


CONFIG = Config.from_env()
