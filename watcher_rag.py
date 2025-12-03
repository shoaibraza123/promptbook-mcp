#!/usr/bin/env python3
"""Enhanced watcher with automatic RAG indexing."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from config import CONFIG, Config
from prompt_organizer import CopilotSessionParser, PromptOrganizer
from prompt_rag import PromptRAG

logging.basicConfig(
    level=getattr(logging, CONFIG.log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CopilotSessionHandler(FileSystemEventHandler):
    """Handles new Copilot session files with RAG indexing"""

    def __init__(
        self,
        config: Config,
        sessions_dir: Path | None = None,
        output_dir: Path | None = None,
        enable_rag: bool | None = None,
    ):
        self.config = config
        self.sessions_dir = (sessions_dir or config.sessions_dir).resolve()
        self.output_dir = (output_dir or config.base_dir).resolve()
        self.organizer = PromptOrganizer(self.output_dir, config=config)
        self.processed_files: set[Path] = set()
        self.enable_rag = config.rag_enabled if enable_rag is None else enable_rag
        self.rag: PromptRAG | None = None
        if self.enable_rag:
            try:
                self.rag = PromptRAG(self.organizer.prompts_dir, config=config)
                logger.info("🧠 RAG system initialized")
            except Exception as exc:  # pragma: no cover - optional dependency
                logger.warning("⚠️  RAG initialization failed: %s", exc)
                self.enable_rag = False
        self._process_existing_files()

    def _process_existing_files(self) -> None:
        """Process any existing session files on startup"""
        logger.info(f"Scanning for existing files in {self.sessions_dir}")

        session_files = list(self.sessions_dir.glob('copilot-session-*.md'))
        if session_files:
            logger.info(f"Found {len(session_files)} existing session files")
            self._process_files(session_files)

            # Index prompts if RAG enabled
            if self.enable_rag and self.rag:
                self._reindex_rag()
        else:
            logger.info("No existing session files found")

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events"""
        if event.is_directory:
            return

        file_path = Path(str(event.src_path))

        # Only process Copilot session files
        if file_path.name.startswith('copilot-session-') and file_path.suffix == '.md':
            logger.info(f"🆕 New session detected: {file_path.name}")

            # Wait a bit to ensure file is completely written
            time.sleep(1)

            if self._process_files([file_path]):
                # Update RAG index with new prompts
                if self.enable_rag and self.rag:
                    self._reindex_rag()

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events"""
        if event.is_directory:
            return

        file_path = Path(str(event.src_path))

        # Only process if it's a session file and not already processed
        if all(
            (
                file_path.name.startswith('copilot-session-'),
                file_path.suffix == '.md',
                file_path not in self.processed_files,
            )
        ):

            logger.info(f"📝 Session file modified: {file_path.name}")

            # Wait for file to be completely written
            time.sleep(2)

            if self._process_files([file_path]):
                # Update RAG index
                if self.enable_rag and self.rag:
                    self._reindex_rag()

    def _process_files(self, files: list[Path]) -> bool:
        """Process session files, returns True if new files were processed"""
        new_files_processed = False

        for file_path in files:
            if file_path in self.processed_files:
                logger.debug(f"Skipping already processed file: {file_path.name}")
                continue

            try:
                logger.info(f"🔄 Processing: {file_path.name}")

                # Parse the session
                parser = CopilotSessionParser(file_path)
                data: dict[str, Any] = parser.parse()

                # Load existing index
                index = self.organizer._load_index()

                # Check if session already exists in index
                session_id = data['metadata'].get('session_id')
                existing_sessions = [s for s in index.get('sessions', []) if s['session_id'] == session_id]

                if existing_sessions:
                    logger.info(f"⚠️  Session {session_id[:8]} already in index, skipping")
                    self.processed_files.add(file_path)
                    continue

                # Save prompts
                self.organizer._save_prompts(data, auto_categorize=True)

                # Update index
                self.organizer._update_index(index, data)
                self.organizer._save_index(index)

                # Generate README if it doesn't exist
                readme_path = self.organizer.prompts_dir / 'README.md'
                if not readme_path.exists():
                    self.organizer.generate_readme()

                logger.info(f"✅ Processed: {data['summary']}")
                self.processed_files.add(file_path)
                new_files_processed = True

            except Exception as e:
                logger.error(f"❌ Error processing {file_path.name}: {e}", exc_info=True)

        return new_files_processed

    def _reindex_rag(self) -> None:
        """Reindex RAG system with all prompts"""
        if not self.rag:
            return
        try:
            logger.info("🧠 Updating RAG index...")
            self.rag.index_prompts(force_reindex=True)
            stats = self.rag.get_stats()
            logger.info(f"✅ RAG indexed: {stats['unique_prompts']} prompts, {stats['total_chunks']} chunks")
        except Exception as e:
            logger.error(f"❌ Error updating RAG index: {e}", exc_info=True)


def main(config: Config | None = None) -> None:
    """Start the watcher with optional automatic RAG reindexing."""
    cfg = config or CONFIG
    sessions_dir = cfg.sessions_dir
    output_dir = cfg.base_dir
    enable_rag = cfg.rag_enabled
    sessions_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("=" * 60)
    logger.info("🚀 Copilot Session Auto-Organizer with RAG")
    logger.info("=" * 60)
    logger.info("📂 Watching directory: %s", sessions_dir)
    logger.info("📦 Output directory: %s", output_dir / 'prompts')
    logger.info("🧠 RAG enabled: %s", enable_rag)
    logger.info("=" * 60)
    event_handler = CopilotSessionHandler(cfg, sessions_dir, output_dir, enable_rag=enable_rag)
    observer = Observer()
    observer.schedule(event_handler, str(sessions_dir), recursive=False)
    observer.start()
    logger.info("👀 Watching for new session files...")
    logger.info("Press Ctrl+C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopping watcher...")
        observer.stop()
    observer.join()
    logger.info("✅ Watcher stopped")


if __name__ == '__main__':
    main()
