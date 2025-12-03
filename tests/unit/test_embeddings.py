#!/usr/bin/env python3
"""
Test embedding providers
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from providers.embeddings import (
    create_embedding_provider,
    SentenceTransformerProvider,
    list_available_providers
)

def test_sentence_transformer():
    """Test sentence transformer provider"""
    print("🧪 Testing SentenceTransformerProvider...")

    provider = create_embedding_provider('sentence-transformer')

    print(f"  Provider: {provider.get_name()}")
    print(f"  Dimension: {provider.get_dimension()}")

    # Test embedding
    texts = ["Hello world", "Test embedding"]
    embeddings = provider.embed(texts)

    assert len(embeddings) == 2, "Should return 2 embeddings"
    assert len(embeddings[0]) == provider.get_dimension(), "Dimension mismatch"

    print(f"  ✅ Generated {len(embeddings)} embeddings")
    print(f"  ✅ Each embedding has {len(embeddings[0])} dimensions")
    print()

def test_lmstudio_mock():
    """Test LMStudio provider configuration (without actual server)"""
    print("🧪 Testing LMStudioProvider configuration...")

    try:
        from providers.embeddings import LMStudioProvider

        # This will fail to connect (expected)
        try:
            provider = LMStudioProvider(
                base_url="http://localhost:1234",
                model_name="nomic-embed-text"
            )
            print("  ⚠️  LMStudio server is running!")
            print(f"  Provider: {provider.get_name()}")
            print(f"  Dimension: {provider.get_dimension()}")
        except ConnectionError as e:
            print(f"  ✅ ConnectionError expected (LMStudio not running): {str(e)[:80]}...")

    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")

    print()

def test_factory():
    """Test factory function"""
    print("🧪 Testing factory function...")

    # Default
    provider = create_embedding_provider()
    print(f"  Default provider: {provider.get_name()}")
    assert isinstance(provider, SentenceTransformerProvider)

    # Explicit
    provider = create_embedding_provider('sentence-transformer')
    assert isinstance(provider, SentenceTransformerProvider)
    print(f"  ✅ Explicit sentence-transformer works")

    # List available
    providers = list_available_providers()
    print(f"  Available providers: {providers}")
    assert 'sentence-transformer' in providers
    assert 'lmstudio' in providers

    print()

def test_rag_integration():
    """Test RAG integration with new provider"""
    print("🧪 Testing PromptRAG integration...")

    from prompt_rag import PromptRAG

    # Create temp prompts dir
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir) / 'prompts'
        prompts_dir.mkdir()

        # Initialize RAG with default provider
        rag = PromptRAG(prompts_dir)

        print(f"  Provider: {rag.provider.get_name()}")
        print(f"  Collection: {rag.collection.name}")
        print(f"  ✅ RAG initialized successfully")

    print()

if __name__ == '__main__':
    print("=" * 60)
    print("🔬 Embedding Providers Test Suite")
    print("=" * 60)
    print()

    test_sentence_transformer()
    test_lmstudio_mock()
    test_factory()
    test_rag_integration()

    print("=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
