"""
Shared pytest fixtures for MCP Prompt Library tests
"""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_prompts_dir():
    """Create temporary prompts directory for testing"""
    temp_dir = Path(tempfile.mkdtemp())

    # Create category directories
    for category in ['refactoring', 'testing', 'debugging', 'general']:
        (temp_dir / category).mkdir()

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_prompt_content():
    """Sample prompt content for testing"""
    return """
# Prompt: Test Prompt

## Metadata
- **Type**: testing
- **Keywords**: test, example

## ROL
You are a testing expert

## OBJETIVO
Create comprehensive tests

## Original Prompt
Create unit tests for the application
"""


@pytest.fixture
def mock_rag_system(monkeypatch):
    """Mock RAG system for testing without embeddings"""
    class MockRAG:
        def __init__(self, *args, **kwargs):
            pass

        def search(self, query, **kwargs):
            return [
                {
                    'text': 'Sample result',
                    'metadata': {'file_name': 'test.md', 'category': 'testing'},
                    'distance': 0.1
                }
            ]

        def index_prompts(self, **kwargs):
            pass

        def get_stats(self):
            return {
                'total_chunks': 10,
                'unique_prompts': 5,
                'avg_chunks_per_prompt': 2.0
            }

    return MockRAG


@pytest.fixture
def sample_session_file(tmp_path):
    """Create a sample Copilot session file"""
    session_content = """
# Copilot Session Export

Session ID: `test-session-123`
Started: 3/12/2025, 10:00:00

---

### 👤 User

Create unit tests for the calculator module

---

### 🤖 Assistant

I'll help you create comprehensive unit tests...
"""

    session_file = tmp_path / "copilot-session-test.md"
    session_file.write_text(session_content)

    return session_file
