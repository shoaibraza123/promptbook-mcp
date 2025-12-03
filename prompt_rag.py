#!/usr/bin/env python3
"""Vector RAG system for prompt library using ChromaDB."""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Literal

import chromadb
from chromadb.config import Settings

from config import CONFIG, Config
from exceptions import EmbeddingProviderError, RAGInitializationError
from prompt_types import PromptMetadata, SearchResult
from providers.embeddings import EmbeddingProvider, create_embedding_provider

SectionKey = Literal['rol', 'contexto', 'objetivo']

logger = logging.getLogger(__name__)


class PromptRAG:
    """Semantic search helper backed by ChromaDB."""

    def __init__(
        self,
        prompts_dir: Optional[Path] = None,
        db_path: Optional[Path] = None,
        embedding_provider: Optional[str] = None,
        *,
        config: Config | None = None,
    ) -> None:
        """Initialize the RAG subsystem.

        Args:
            prompts_dir: Directory containing prompt markdown files.
            db_path: Destination for the persistent Chroma collection.
            embedding_provider: Optional override for the configured provider.
            config: Shared configuration instance (falls back to global ``CONFIG``).

        Raises:
            RAGInitializationError: If embedding providers or Chroma cannot be initialized.
        """
        self.config = config or CONFIG
        self.prompts_dir = (prompts_dir or self.config.prompts_dir).resolve()
        self.db_path = (db_path or self.config.vectordb_dir).resolve()
        self.index_file = self.prompts_dir / "index.json"
        self.chunk_size = self.config.chunk_size
        self.chunk_overlap = self.config.chunk_overlap
        self.auto_reindex_interval = self.config.auto_reindex_interval
        self.provider = self._build_provider(embedding_provider)
        self.client: Any = self._create_client()
        self.collection: Any = self._create_collection()
        self.last_index_check = 0.0

    def _build_provider(self, provider_override: Optional[str]) -> EmbeddingProvider:
        """Instantiate the embedding provider using configuration defaults."""
        try:
            return create_embedding_provider(provider_override, config=self.config)
        except EmbeddingProviderError as exc:  # pragma: no cover - network/hardware dependent
            raise RAGInitializationError("Failed to initialize embedding provider") from exc

    def _create_client(self) -> Any:
        """Create a persistent ChromaDB client bound to the configured path."""
        try:
            return chromadb.PersistentClient(
                path=str(self.db_path),
                settings=Settings(anonymized_telemetry=False),
            )
        except Exception as exc:  # pragma: no cover - environment specific
            raise RAGInitializationError("Failed to create ChromaDB client") from exc

    def _create_collection(self) -> Any:
        """Create or fetch the Chroma collection for prompts."""
        wrapper = self._build_chroma_wrapper()
        collection_name = self._derive_collection_name()
        logger.info("Using collection: %s", collection_name)
        return self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=wrapper,
            metadata={
                "description": "Copilot prompts library",
                "provider": self.provider.get_name(),
                "dimension": self.provider.get_dimension(),
            },
        )

    def _build_chroma_wrapper(self) -> Any:
        """Build the callable adapter expected by ChromaDB."""
        provider = self.provider

        class ChromaDBEmbeddingWrapper:
            def __init__(self, backing_provider: EmbeddingProvider) -> None:
                self.provider = backing_provider
                self._name = backing_provider.get_name()

            def __call__(self, input: Sequence[str]) -> List[List[float]]:
                return self.provider.embed(list(input))

            def embed_query(self, input: Sequence[str]) -> List[List[float]]:
                return self.provider.embed(list(input))

            def name(self) -> str:
                return self._name

        return ChromaDBEmbeddingWrapper(provider)

    def _derive_collection_name(self) -> str:
        """Return a deterministic collection name for the configured provider."""
        provider_name = self.provider.get_name().replace('/', '_').replace('-', '_')
        dimension = self.provider.get_dimension()
        return f"prompts_{provider_name}_{dimension}d"

    def chunk_prompt(self, prompt_content: str, chunk_size: int | None = None, overlap: int | None = None) -> List[str]:
        """Split prompt text into overlapping chunks for better retrieval.

        Args:
            prompt_content: Full prompt text to split.
            chunk_size: Optional override for the chunk length.
            overlap: Optional override for the overlapping token count.

        Returns:
            List[str]: Prompt chunks respecting the configured overlap.
        """
        chunk_len = chunk_size or self.chunk_size
        overlap_len = overlap or self.chunk_overlap
        words = prompt_content.split()
        chunks: List[str] = []
        step = max(chunk_len - overlap_len, 1)
        for i in range(0, len(words), step):
            chunk = ' '.join(words[i:i + chunk_len])
            if chunk:
                chunks.append(chunk)
        return chunks if chunks else [prompt_content]

    def extract_prompt_content(self, file_path: Path) -> PromptMetadata:
        """Extract metadata and structured text from a prompt file.

        Args:
            file_path: Prompt file to parse.

        Returns:
            PromptMetadata: Structured metadata describing the prompt file.
        """
        content = file_path.read_text(encoding='utf-8')
        valid_categories = [
            'refactoring',
            'testing',
            'debugging',
            'implementation',
            'documentation',
            'code-review',
            'general',
        ]
        inferred_category = file_path.parent.name if file_path.parent.name in valid_categories else 'general'
        metadata: PromptMetadata = {
            'file_path': str(file_path),
            'file_name': file_path.name,
            'category': inferred_category,
        }
        for line in content.split('\n'):
            if '**Type**:' in line:
                metadata['type'] = line.split('**Type**:')[1].strip()
            if '**Keywords**:' in line:
                metadata['keywords'] = line.split('**Keywords**:')[1].strip()
            if '**Session**:' in line:
                metadata['session_id'] = line.split('**Session**:')[1].strip()
        if '## Original Prompt' in content:
            sections = content.split('## Original Prompt')
            if len(sections) > 1:
                prompt_section = sections[1]
                if '```' in prompt_section:
                    metadata['full_text'] = prompt_section.split('```')[1].strip()
                else:
                    metadata['full_text'] = prompt_section.strip()

        def _extract_section_text(marker: str) -> Optional[str]:
            if marker in content:
                remainder = content.split(marker)
                if len(remainder) > 1:
                    return remainder[1].split('##')[0].strip()
            return None

        rol_text = _extract_section_text('## ROL')
        if rol_text:
            metadata['rol'] = rol_text

        contexto_text = _extract_section_text('## CONTEXTO')
        if contexto_text:
            metadata['contexto'] = contexto_text

        objetivo_text = _extract_section_text('## OBJETIVO')
        if objetivo_text:
            metadata['objetivo'] = objetivo_text

        return metadata

    def _discover_prompt_files(self) -> List[Path]:
        """Return the list of prompt files excluding helper documentation."""
        return [f for f in self.prompts_dir.rglob('*.md') if f.name != 'README.md']

    def check_and_reindex_if_needed(self) -> bool:
        """Rebuild the index when the filesystem content drifts.

        Returns:
            bool: ``True`` when a reindex was triggered.
        """
        if time.time() - self.last_index_check < self.auto_reindex_interval:
            return False
        self.last_index_check = time.time()
        prompt_files = self._discover_prompt_files()
        try:
            indexed_count = self.collection.count()
        except Exception as exc:  # pragma: no cover - chroma internals
            logger.warning("Could not check index status: %s", exc)
            return False
        if len(prompt_files) == indexed_count:
            return False
        logger.info(
            "Auto-reindexing RAG collection (files=%s, indexed=%s)",
            len(prompt_files),
            indexed_count,
        )
        self.index_prompts(force_reindex=True)
        return True

    def _reset_collection(self, force_reindex: bool) -> None:
        """Reset the Chroma collection when reindexing is required."""
        if not force_reindex and self.collection.count() == 0:
            return
        try:
            current_collection_name = self.collection.name
            self.client.delete_collection(current_collection_name)
        except Exception as exc:  # pragma: no cover - chroma internals
            raise RAGInitializationError("Failed to reset Chroma collection") from exc
        self.collection = self._create_collection()

    def _build_chunk_metadata(self, prompt_data: PromptMetadata, index: int, total_chunks: int) -> Dict[str, str]:
        """Normalize prompt metadata for ChromaDB."""
        metadata: Dict[str, str] = {
            'file_name': prompt_data['file_name'],
            'category': prompt_data['category'],
            'chunk_index': str(index),
            'total_chunks': str(total_chunks),
        }
        for key in ['type', 'keywords', 'session_id', 'rol', 'contexto', 'objetivo']:
            if value := prompt_data.get(key):
                metadata[key] = str(value)[:500]
        return metadata

    def _prepare_documents(self, prompt_files: Sequence[Path]) -> tuple[List[str], List[Dict[str, str]], List[str]]:
        """Convert prompt files into documents and metadata batches."""
        documents: List[str] = []
        metadatas: List[Dict[str, str]] = []
        ids: List[str] = []
        for file_path in prompt_files:
            try:
                prompt_data = self.extract_prompt_content(file_path)
            except Exception as exc:  # pragma: no cover - file specific
                logger.warning("Error processing %s: %s", file_path.name, exc)
                continue
            full_text = prompt_data.get('full_text', '')
            if not full_text:
                continue
            chunks = self.chunk_prompt(full_text)
            for index, chunk in enumerate(chunks):
                chunk_id = hashlib.md5(f"{file_path.name}_{index}".encode()).hexdigest()
                metadata = self._build_chunk_metadata(prompt_data, index, len(chunks))
                documents.append(chunk)
                metadatas.append(metadata)
                ids.append(chunk_id)
        return documents, metadatas, ids

    def _add_documents_in_batches(
        self,
        documents: Sequence[str],
        metadatas: Sequence[Dict[str, str]],
        ids: Sequence[str],
        batch_size: int = 100,
    ) -> None:
        """Send documents to ChromaDB in controlled batches."""
        for start in range(0, len(documents), batch_size):
            end = start + batch_size
            self.collection.add(
                documents=list(documents[start:end]),
                metadatas=list(metadatas[start:end]),
                ids=list(ids[start:end]),
            )
            logger.info(
                "Indexed batch %s/%s",
                start // batch_size + 1,
                (len(documents) + batch_size - 1) // batch_size,
            )

    def index_prompts(self, force_reindex: bool = False) -> None:
        """Index all prompts in the library.

        Args:
            force_reindex: Set to ``True`` to rebuild the collection from scratch.
        """
        self._reset_collection(force_reindex)
        prompt_files = self._discover_prompt_files()
        logger.info("Scanning %s prompt files", len(prompt_files))
        documents, metadatas, ids = self._prepare_documents(prompt_files)
        if not documents:
            logger.info("No prompt documents found to index.")
            return
        self._add_documents_in_batches(documents, metadatas, ids)
        logger.info("Indexing complete. Total chunks indexed: %s", len(documents))

    def search(self, query: str, n_results: int = 5, category: Optional[str] = None) -> List[SearchResult]:
        """Run a semantic search across indexed prompts.

        Args:
            query: Natural-language query to embed.
            n_results: Maximum number of chunks to return.
            category: Optional category filter applied at query time.

        Returns:
            List[SearchResult]: Ranked results ordered by similarity.
        """
        self.check_and_reindex_if_needed()
        where_filter = {"category": category} if category else None
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
        )
        formatted_results: List[SearchResult] = []
        if results.get('documents') and results['documents'][0]:
            for index, document in enumerate(results['documents'][0]):
                distance = None
                if 'distances' in results and results['distances'][0]:
                    distance = results['distances'][0][index]
                formatted_results.append(
                    {
                        'text': document,
                        'metadata': results['metadatas'][0][index],
                        'distance': distance,
                    }
                )
        return formatted_results

    def find_similar_prompts(self, prompt_file: Path, n_results: int = 3) -> List[SearchResult]:
        """Find prompts similar to a given reference file.

        Args:
            prompt_file: Reference prompt to compare against.
            n_results: Maximum number of neighbors to return.

        Returns:
            List[SearchResult]: Most similar prompts excluding the reference itself.
        """
        prompt_data = self.extract_prompt_content(prompt_file)
        query_text = prompt_data.get('full_text', '')
        if not query_text:
            return []
        results = self.collection.query(query_texts=[query_text], n_results=n_results + 5)
        formatted_results: List[SearchResult] = []
        if results.get('documents') and results['documents'][0]:
            for index, document in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][index]
                if metadata['file_name'] == prompt_file.name:
                    continue
                distance = None
                if 'distances' in results and results['distances'][0]:
                    distance = results['distances'][0][index]
                formatted_results.append({'text': document, 'metadata': metadata, 'distance': distance})
                if len(formatted_results) >= n_results:
                    break
        return formatted_results

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregated statistics for the current RAG index.

        Returns:
            Dict[str, Any]: Summary metrics including chunk counts and categories.
        """
        total_chunks = self.collection.count()
        all_results = self.collection.get()
        unique_files = set()
        categories: Dict[str, int] = {}
        if all_results.get('metadatas'):
            for metadata in all_results['metadatas']:
                unique_files.add(metadata['file_name'])
                category = metadata.get('category', 'unknown')
                categories[category] = categories.get(category, 0) + 1
        avg_chunks = round(total_chunks / len(unique_files), 2) if unique_files else 0
        return {
            'total_chunks': total_chunks,
            'unique_prompts': len(unique_files),
            'categories': categories,
            'avg_chunks_per_prompt': avg_chunks,
        }


def main() -> None:
    """Command-line interface for manual RAG maintenance tasks."""
    import argparse

    parser = argparse.ArgumentParser(description='RAG system for prompt library')
    parser.add_argument('--prompts-dir', default=str(CONFIG.prompts_dir), help='Prompts directory')
    parser.add_argument('--index', action='store_true', help='Index all prompts')
    parser.add_argument('--reindex', action='store_true', help='Force reindex all prompts')
    parser.add_argument('--search', help='Search query')
    parser.add_argument('--similar', help='Find similar prompts to file')
    parser.add_argument('--category', help='Filter by category')
    parser.add_argument('--n-results', type=int, default=5, help='Number of results')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--health', action='store_true', help='Run a lightweight health check')

    args = parser.parse_args()

    prompts_dir = Path(args.prompts_dir)
    rag = PromptRAG(prompts_dir, config=CONFIG)

    if args.health:
        rag.check_and_reindex_if_needed()
        print("✅ RAG health check passed")
        return

    if args.index or args.reindex:
        rag.index_prompts(force_reindex=args.reindex)

    elif args.search:
        print(f"\n🔍 Searching for: '{args.search}'")
        if args.category:
            print(f"📂 Category filter: {args.category}")
        print("=" * 60)

        results = rag.search(args.search, n_results=args.n_results, category=args.category)

        for i, result in enumerate(results, 1):
            print(f"\n📄 Result {i} - {result['metadata']['file_name']}")
            print(f"📂 Category: {result['metadata']['category']}")
            print(f"🏷️  Type: {result['metadata'].get('type', 'N/A')}")
            if result['distance']:
                print(f"📊 Distance: {result['distance']:.4f}")
            print(f"\n{result['text'][:300]}...")
            print("-" * 60)

    elif args.similar:
        similar_file = Path(args.similar)
        if not similar_file.exists():
            print(f"❌ File not found: {similar_file}")
            return

        print(f"\n🔍 Finding prompts similar to: {similar_file.name}")
        print("=" * 60)

        results = rag.find_similar_prompts(similar_file, n_results=args.n_results)

        for i, result in enumerate(results, 1):
            print(f"\n📄 Similar prompt {i}: {result['metadata']['file_name']}")
            print(f"📂 Category: {result['metadata']['category']}")
            if result['distance']:
                print(f"📊 Similarity: {1 - result['distance']:.2%}")
            print(f"\n{result['text'][:200]}...")
            print("-" * 60)

    elif args.stats:
        stats = rag.get_stats()
        print("\n📊 RAG System Statistics")
        print("=" * 60)
        print(f"Total chunks: {stats['total_chunks']}")
        print(f"Unique prompts: {stats['unique_prompts']}")
        print(f"Avg chunks/prompt: {stats['avg_chunks_per_prompt']}")
        print("\nBy category:")
        for category, count in stats['categories'].items():
            print(f"  {category}: {count} chunks")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
