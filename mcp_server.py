#!/usr/bin/env python3
"""MCP Server exposing prompt search, organization, and RAG capabilities."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable, List, Optional, cast

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from config import CONFIG, Config
from exceptions import InvalidPathError, PromptLibraryError, RAGInitializationError
from prompt_organizer import CopilotSessionParser, PromptOrganizer
from prompt_rag import PromptRAG

CONFIG.ensure_directories()
LOG_LEVEL = getattr(logging, CONFIG.log_level.upper(), logging.INFO)
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(CONFIG.log_file),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("prompt-mcp-server")

app = Server("prompt-library-server")
PROMPTS_DIR = CONFIG.prompts_dir
CATEGORY_CHOICES = [
    "refactoring",
    "testing",
    "debugging",
    "implementation",
    "code-review",
    "documentation",
    "general",
]
rag_system: Optional[PromptRAG] = None
organizer: Optional[PromptOrganizer] = None

ToolListHandler = Callable[[], Awaitable[list[Tool]]]
ToolCallHandler = Callable[[str, Any], Awaitable[list[TextContent]]]

if TYPE_CHECKING:
    def register_list_tools(func: ToolListHandler) -> ToolListHandler:
        ...

    def register_call_tool(func: ToolCallHandler) -> ToolCallHandler:
        ...
else:
    register_list_tools = app.list_tools()
    register_call_tool = app.call_tool()


def _require_organizer() -> PromptOrganizer:
    """Return the initialized organizer or raise a configuration error."""
    if organizer is None:
        raise PromptLibraryError("Prompt organizer is not initialized")
    return organizer


def _validate_safe_path(base_dir: Path, user_path: str) -> Path:
    """Ensure user-controlled paths stay within the prompts directory.

    Args:
        base_dir: Allowed base directory for prompt files.
        user_path: Relative path provided by the user.

    Returns:
        Path: Absolute path that is guaranteed to be inside ``base_dir``.

    Raises:
        InvalidPathError: If the path is absolute, escapes the base dir, or is malformed.
    """
    base_resolved = base_dir.resolve()
    if ".." in user_path:
        raise InvalidPathError("Invalid path: path contains '..' (parent directory access)")
    if user_path.startswith("/"):
        raise InvalidPathError("Invalid path: absolute paths not allowed")
    try:
        full_path = (base_dir / user_path).resolve()
    except (RuntimeError, OSError) as exc:
        raise InvalidPathError(f"Invalid path: {exc}") from exc
    try:
        full_path.relative_to(base_resolved)
    except ValueError as exc:
        raise InvalidPathError(
            f"Invalid path: '{user_path}' resolves outside base directory"
        ) from exc
    return full_path


def initialize_systems(config: Config = CONFIG) -> None:
    """Initialize dependencies required by the MCP server.

    Args:
        config: Shared configuration for filesystem paths and providers.
    """
    global rag_system, organizer
    prompts_dir = config.prompts_dir
    logger.info("📂 Using prompts directory: %s", prompts_dir)
    if not prompts_dir.exists():
        logger.warning("⚠️  Prompts directory does not exist, creating: %s", prompts_dir)
        prompts_dir.mkdir(parents=True, exist_ok=True)
    categories = [d.name for d in prompts_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    logger.info("📂 Found categories: %s", categories)
    prompt_files = [f for f in prompts_dir.rglob('*.md') if f.name != 'README.md']
    logger.info("📚 Found %s prompt files", len(prompt_files))
    organizer = PromptOrganizer(prompts_dir.parent, config=config)
    try:
        rag_system = PromptRAG(prompts_dir, config=config)
        logger.info("✅ RAG system initialized")
    except (RAGInitializationError, PromptLibraryError) as exc:
        logger.warning("⚠️  RAG initialization failed: %s", exc)
        rag_system = None
    except Exception as exc:  # pragma: no cover - defensive safeguard
        logger.exception("Unexpected error initializing RAG: %s", exc)
        rag_system = None


@register_list_tools
async def list_tools() -> list[Tool]:
    """List the MCP tools exposed by the Prompt Library server.

    Returns:
        list[Tool]: Tool definitions discoverable by MCP clients.
    """
    return [
        Tool(
            name="search_prompts",
            description="Semantic search for prompts using RAG. Finds prompts by meaning, not just keywords.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Search query (e.g., 'refactor backend code', 'testing automation')"
                        )
                    },
                    "category": {
                        "type": "string",
                        "description": (
                            "Filter by category (optional): refactoring, testing, debugging, "
                            "implementation, documentation, general"
                        ),
                        "enum": CATEGORY_CHOICES
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_prompt_by_file",
            description="Get the full content of a specific prompt file",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Relative path to prompt file (e.g., 'refactoring/2-12-2025_prompt1.md')"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="find_similar_prompts",
            description="Find prompts similar to a given prompt file",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the reference prompt file"
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Number of similar prompts to return (default: 3)",
                        "default": 3,
                        "minimum": 1,
                        "maximum": 10
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="list_prompts_by_category",
            description="List all prompts in a specific category",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category name",
                        "enum": CATEGORY_CHOICES
                    }
                },
                "required": ["category"]
            }
        ),
        Tool(
            name="get_library_stats",
            description=(
                "Get statistics about the prompt library (total prompts, categories, RAG status)"
            ),
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="index_prompts",
            description="Manually trigger RAG indexing of all prompts",
            inputSchema={
                "type": "object",
                "properties": {
                    "force": {
                        "type": "boolean",
                        "description": "Force reindex even if already indexed (default: false)",
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="organize_session",
            description=(
                "Process and organize a session file exported from an AI coding agent "
                "(Copilot CLI, Claude Code, etc.). Extracts prompts, categorizes them, "
                "and indexes for search. Use 'create_prompt' for individual prompts instead."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_path": {
                        "type": "string",
                        "description": "Path to the session markdown file"
                    },
                    "session_type": {
                        "type": "string",
                        "description": "Type of AI agent session (default: copilot-cli)",
                        "enum": ["copilot-cli"],
                        "default": "copilot-cli"
                    }
                },
                "required": ["session_path"]
            }
        ),
        Tool(
            name="get_prompt_index",
            description="Get the full prompt library index with all sessions and metadata",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="create_prompt",
            description=(
                "Create a new prompt directly in the library without needing a Copilot session file. "
                "Auto-categorizes and indexes the prompt for immediate searchability."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The prompt content (markdown supported)"
                    },
                    "category": {
                        "type": "string",
                        "description": "Category (auto-detected if not provided)",
                        "enum": CATEGORY_CHOICES
                    },
                    "title": {
                        "type": "string",
                        "description": "Title for the prompt (auto-generated if not provided)"
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of keywords for better searchability"
                    },
                    "source": {
                        "type": "string",
                        "description": "Origin of the prompt (manual, agent, import, etc.)",
                        "default": "manual"
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="update_prompt",
            description=(
                "Update an existing prompt. Can modify content, category, title, or keywords. "
                "Re-indexes automatically in RAG."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Relative path to the prompt file (e.g., 'testing/prompt1.md')"
                    },
                    "content": {
                        "type": "string",
                        "description": "New content (optional, keeps existing if not provided)"
                    },
                    "category": {
                        "type": "string",
                        "description": "New category (optional, moves file if changed)",
                        "enum": CATEGORY_CHOICES
                    },
                    "title": {
                        "type": "string",
                        "description": "New title (optional)"
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "New keywords (optional)"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="delete_prompt",
            description=(
                "Delete a prompt from the library. Removes file and RAG chunks. Requires "
                "confirmation for safety."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Relative path to the prompt file (e.g., 'testing/prompt1.md')"
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Must be true to actually delete (safety check)",
                        "default": False
                    }
                },
                "required": ["file_path"]
            }
        )
    ]


@register_call_tool
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Route an MCP tool invocation to the matching handler.

    Args:
        name: Tool name provided by the MCP runtime.
        arguments: JSON-serializable payload supplied by the client.

    Returns:
        list[TextContent]: Serialized response content for the MCP client.
    """

    if name == "search_prompts":
        return await search_prompts(
            arguments.get("query"),
            arguments.get("category"),
            arguments.get("n_results", 5)
        )

    elif name == "get_prompt_by_file":
        return await get_prompt_by_file(arguments.get("file_path"))

    elif name == "find_similar_prompts":
        return await find_similar_prompts(
            arguments.get("file_path"),
            arguments.get("n_results", 3)
        )

    elif name == "list_prompts_by_category":
        return await list_prompts_by_category(arguments.get("category"))

    elif name == "get_library_stats":
        return await get_library_stats()

    elif name == "index_prompts":
        return await index_prompts(arguments.get("force", False))

    elif name == "organize_session":
        return await organize_session(
            arguments.get("session_path"),
            arguments.get("session_type", "copilot-cli")
        )

    elif name == "get_prompt_index":
        return await get_prompt_index()

    elif name == "create_prompt":
        return await create_prompt(
            content=arguments.get("content"),
            category=arguments.get("category"),
            title=arguments.get("title"),
            keywords=arguments.get("keywords"),
            source=arguments.get("source", "manual")
        )

    elif name == "update_prompt":
        return await update_prompt(
            file_path=arguments.get("file_path"),
            content=arguments.get("content"),
            category=arguments.get("category"),
            title=arguments.get("title"),
            keywords=arguments.get("keywords")
        )

    elif name == "delete_prompt":
        return await delete_prompt(
            file_path=arguments.get("file_path"),
            confirm=arguments.get("confirm", False)
        )

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def search_prompts(query: str, category: Optional[str], n_results: int) -> list[TextContent]:
    """Perform a semantic search using the RAG subsystem.

    Args:
        query: Natural-language query string.
        category: Optional category filter applied at query time.
        n_results: Number of matches to return.

    Returns:
        list[TextContent]: Formatted search summary for the MCP client.
    """
    if not rag_system:
        return [TextContent(
            type="text",
            text="❌ RAG system not available. Please run 'index_prompts' first."
        )]

    try:
        results = rag_system.search(query, n_results=n_results, category=category)

        if not results:
            return [TextContent(
                type="text",
                text=f"No prompts found for query: '{query}'"
            )]

        # Format results
        output = f"🔍 Found {len(results)} prompts for: '{query}'\n"
        if category:
            output += f"📂 Category filter: {category}\n"
        output += "=" * 60 + "\n\n"

        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            output += f"📄 Result {i}: {metadata['file_name']}\n"
            output += f"   Category: {metadata['category']}\n"
            output += f"   Type: {metadata.get('type', 'N/A')}\n"

            if result['distance']:
                similarity = (1 - result['distance']) * 100
                output += f"   Similarity: {similarity:.1f}%\n"

            # Show keywords if available
            if 'keywords' in metadata:
                output += f"   Keywords: {metadata['keywords']}\n"

            # Show excerpt
            text_preview = result['text'][:250].replace('\n', ' ')
            output += f"\n   Preview: {text_preview}...\n"
            output += "-" * 60 + "\n\n"

        return [TextContent(type="text", text=output)]

    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return [TextContent(type="text", text=f"❌ Search failed: {str(e)}")]


async def get_prompt_by_file(file_path: str) -> list[TextContent]:
    """Return the entire contents of a specific prompt file.

    Args:
        file_path: Relative path within the prompts directory.

    Returns:
        list[TextContent]: Prompt content wrapped for MCP transport.
    """
    try:
        full_path = _validate_safe_path(PROMPTS_DIR, file_path)

        if not full_path.exists():
            return [TextContent(
                type="text",
                text=f"""❌ File not found: {file_path}

💡 Tips:
- Use search_prompts to find prompts
- Check available categories with list_prompts_by_category
- Verify path format: category/filename.md
"""
            )]

        content = full_path.read_text(encoding='utf-8')

        return [TextContent(
            type="text",
            text=f"📄 **{full_path.name}**\n\n{content}"
        )]

    except ValueError as e:
        logger.warning(f"Path validation failed: {e}")
        return [TextContent(type="text", text=f"❌ Invalid path: {str(e)}")]
    except Exception as e:
        logger.error(f"Get prompt error: {e}", exc_info=True)
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def find_similar_prompts(file_path: str, n_results: int) -> list[TextContent]:
    """Find prompts that are semantically similar to a reference file.

    Args:
        file_path: Relative path to the reference prompt.
        n_results: Number of similar prompts to return.

    Returns:
        list[TextContent]: Similarity summary ready for MCP clients.
    """
    if not rag_system:
        return [TextContent(type="text", text="❌ RAG system not available")]

    try:
        full_path = _validate_safe_path(PROMPTS_DIR, file_path)

        if not full_path.exists():
            return [TextContent(type="text", text=f"❌ File not found: {file_path}")]

        results = rag_system.find_similar_prompts(full_path, n_results=n_results)

        if not results:
            return [TextContent(type="text", text="No similar prompts found")]

        output = f"🔍 Similar prompts to: {full_path.name}\n"
        output += "=" * 60 + "\n\n"

        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            similarity = (1 - result['distance']) * 100 if result['distance'] else 0

            output += f"📄 {i}. {metadata['file_name']}\n"
            output += f"   Category: {metadata['category']}\n"
            output += f"   Similarity: {similarity:.1f}%\n"
            output += f"   Preview: {result['text'][:150]}...\n\n"

        return [TextContent(type="text", text=output)]

    except Exception as e:
        logger.error(f"Find similar error: {e}", exc_info=True)
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def list_prompts_by_category(category: str) -> list[TextContent]:
    """List all prompts in a given category folder.

    Args:
        category: Category folder name such as ``testing`` or ``refactoring``.

    Returns:
        list[TextContent]: Markdown-formatted listing.
    """
    try:
        category_dir = PROMPTS_DIR / category

        if not category_dir.exists():
            return [TextContent(
                type="text",
                text=f"❌ Category not found: {category}"
            )]

        prompts = list(category_dir.glob("*.md"))
        prompts = [p for p in prompts if p.name != "README.md"]

        output = f"📂 Category: {category}\n"
        output += f"Total prompts: {len(prompts)}\n"
        output += "=" * 60 + "\n\n"

        for prompt in sorted(prompts):
            output += f"📄 {prompt.name}\n"

        return [TextContent(type="text", text=output)]

    except Exception as e:
        logger.error(f"List category error: {e}", exc_info=True)
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def get_library_stats() -> list[TextContent]:
    """Return aggregate statistics about the prompt library and RAG index.

    Returns:
        list[TextContent]: Human-readable statistics summary.
    """
    try:
        # Count prompts by category
        categories = {}
        total_prompts = 0

        for category in CATEGORY_CHOICES:
            category_dir = PROMPTS_DIR / category
            if category_dir.exists():
                prompts = list(category_dir.glob("*.md"))
                prompts = [p for p in prompts if p.name != "README.md"]
                count = len(prompts)
                if count > 0:
                    categories[category] = count
                    total_prompts += count

        # Get RAG stats if available
        rag_stats = None
        if rag_system:
            try:
                rag_stats = rag_system.get_stats()
            except Exception:
                pass

        # Format output
        output = "📊 Prompt Library Statistics\n"
        output += "=" * 60 + "\n\n"
        output += f"Total prompts: {total_prompts}\n\n"

        output += "By category:\n"
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            output += f"  • {category}: {count}\n"

        if rag_stats:
            output += "\n🧠 RAG System:\n"
            output += "  • Status: Active\n"
            output += f"  • Total chunks: {rag_stats['total_chunks']}\n"
            output += f"  • Indexed prompts: {rag_stats['unique_prompts']}\n"
            output += f"  • Avg chunks/prompt: {rag_stats['avg_chunks_per_prompt']}\n"
        else:
            output += "\n🧠 RAG System: Not initialized\n"

        return [TextContent(type="text", text=output)]

    except Exception as e:
        logger.error(f"Stats error: {e}", exc_info=True)
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def index_prompts(force: bool) -> list[TextContent]:
    """Trigger a reindex of the prompt collection.

    Args:
        force: Whether to rebuild the collection from scratch.

    Returns:
        list[TextContent]: Status information for the MCP client.
    """
    if not rag_system:
        return [TextContent(type="text", text="❌ RAG system not available")]

    try:
        output = "🧠 Indexing prompts...\n\n"

        # Capture indexing output
        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()

        rag_system.index_prompts(force_reindex=force)

        sys.stdout = old_stdout
        indexing_output = buffer.getvalue()

        output += indexing_output

        stats = rag_system.get_stats()
        output += "\n✅ Indexing complete!\n"
        output += f"Total prompts: {stats['unique_prompts']}\n"
        output += f"Total chunks: {stats['total_chunks']}\n"

        return [TextContent(type="text", text=output)]

    except Exception as e:
        logger.error(f"Indexing error: {e}", exc_info=True)
        return [TextContent(type="text", text=f"❌ Indexing failed: {str(e)}")]


async def organize_session(session_path: str, session_type: str = "copilot-cli") -> list[TextContent]:
    """Process and organize an AI agent session file.

    Args:
        session_path: Absolute path to the exported session markdown file.
        session_type: Identifier describing the session format.

    Returns:
        list[TextContent]: Outcome of the organization workflow.
    """
    try:
        # Validate session type
        if session_type != "copilot-cli":
            return [TextContent(
                type="text",
                text=f"❌ Unsupported session type: {session_type}\n"
                     f"Currently only 'copilot-cli' is supported.\n"
                     f"For individual prompts, use the 'create_prompt' tool instead."
            )]

        file_path = Path(session_path)

        if not file_path.exists():
            return [TextContent(type="text", text=f"❌ File not found: {session_path}")]

        # Parse session (currently only supports Copilot CLI format)
        parser = CopilotSessionParser(file_path)
        data = parser.parse()

        current_organizer = _require_organizer()

        # Save prompts
        current_organizer._save_prompts(data, auto_categorize=True)

        # Update index
        index = current_organizer._load_index()
        current_organizer._update_index(index, data)
        current_organizer._save_index(index)

        # Reindex RAG if available
        if rag_system:
            rag_system.index_prompts(force_reindex=True)

        output = "✅ Session processed successfully!\n\n"
        output += f"Session Type: {session_type}\n"
        output += f"Session ID: {data['metadata'].get('session_id', 'N/A')}\n"
        output += f"Summary: {data['summary']}\n"
        output += f"Prompts extracted: {len(data['conversations'])}\n"
        output += f"Categories: {', '.join(data['categories'])}\n"

        return [TextContent(type="text", text=output)]

    except Exception as e:
        logger.error(f"Organize session error: {e}", exc_info=True)
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def get_prompt_index() -> list[TextContent]:
    """Load and display the JSON index maintained by the organizer.

    Returns:
        list[TextContent]: Formatted index summary for clients.
    """
    try:
        index_file = PROMPTS_DIR / 'index.json'

        if not index_file.exists():
            return [TextContent(type="text", text="❌ Index file not found")]

        index_data = json.loads(index_file.read_text())

        # Format nicely
        output = "📚 Prompt Library Index\n"
        output += "=" * 60 + "\n\n"

        # Sessions
        sessions = index_data.get('sessions', [])
        output += f"📋 Sessions: {len(sessions)}\n\n"

        for session in sessions[-5:]:  # Show last 5
            output += f"  • {session['session_id'][:8]}... - {session['summary']}\n"

        if len(sessions) > 5:
            output += f"\n  ... and {len(sessions) - 5} more\n"

        # Categories
        output += "\n📂 Categories:\n"
        for category, session_ids in index_data.get('categories', {}).items():
            output += f"  • {category}: {len(session_ids)} sessions\n"

        # Tags
        tags = index_data.get('tags', {})
        if tags:
            output += "\n🏷️  Top Tags:\n"
            sorted_tags = sorted(tags.items(), key=lambda x: len(x[1]), reverse=True)[:10]
            for tag, session_ids in sorted_tags:
                output += f"  • {tag}: {len(session_ids)}\n"

        return [TextContent(type="text", text=output)]

    except Exception as e:
        logger.error(f"Get index error: {e}", exc_info=True)
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


# ==================== CRUD Helper Functions ====================

def _auto_classify_prompt(content: str) -> str:
    """Auto-detect category from content using keywords"""
    content_lower = content.lower()

    # Keyword mapping for classification
    classifiers = {
        'refactoring': ['refactor', 'clean code', 'solid', 'design pattern', 'restructure', 'mejora'],
        'testing': ['test', 'unittest', 'integration test', 'e2e', 'qa', 'bruno', 'jest', 'pytest'],
        'debugging': ['debug', 'error', 'bug', 'fix', 'troubleshoot', 'issue'],
        'implementation': ['implement', 'create', 'develop', 'build', 'feature', 'añadir', 'crear'],
        'documentation': ['document', 'readme', 'docs', 'comment', 'explain', 'documentar'],
        'code-review': ['review', 'pr', 'pull request', 'feedback', 'revision'],
    }

    scores = {}
    for cat, keywords in classifiers.items():
        score = sum(1 for kw in keywords if kw in content_lower)
        if score > 0:
            scores[cat] = score

    if scores:
        return max(scores.items(), key=lambda x: x[1])[0]

    return 'general'


def _generate_title_from_content(content: str, max_length: int = 60) -> str:
    """Generate title from first meaningful line"""
    lines = [line.strip() for line in content.split('\n') if line.strip()]

    # Skip markdown headers and look for first content line
    for line in lines:
        # Skip headers
        if line.startswith('#'):
            # Could use header text if available
            header_text = line.lstrip('#').strip()
            if header_text and not header_text.lower().startswith('prompt'):
                if len(header_text) > max_length:
                    return header_text[:max_length] + '...'
                return header_text
            continue

        # Use first non-header line
        title = line.replace('**', '').replace('*', '').strip()
        if title:
            if len(title) > max_length:
                return title[:max_length] + '...'
            return title

    return "Untitled Prompt"


def _format_prompt_file(title: str, content: str, category: str,
                        keywords: List[str], source: str) -> str:
    """Format prompt content with metadata"""
    from datetime import datetime

    date_str = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
    keywords_str = ', '.join(keywords) if keywords else 'none'

    return f"""# Prompt: {title}

## Metadata
- **Type**: {category}
- **Date**: {date_str}
- **Keywords**: {keywords_str}
- **Source**: {source}

## Content

{content}

## Template Variables
<!-- Define variables for reuse -->
- `{{{{PROJECT_NAME}}}}`:
- `{{{{CONTEXT}}}}`:
- `{{{{SPECIFIC_TASK}}}}`:
"""


def _index_single_file(file_path: Path) -> None:
    """Index a single file in RAG system"""
    if not rag_system:
        return

    try:
        content = file_path.read_text(encoding='utf-8')
        chunks = rag_system.chunk_prompt(content)
        metadata = rag_system.extract_prompt_content(file_path)

        # Add to collection
        documents = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            doc_id = f"{file_path.stem}_chunk_{i}"
            documents.append(chunk)
            metadatas.append(metadata)
            ids.append(doc_id)

        if documents:
            rag_system.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"✅ Indexed {len(chunks)} chunks from {file_path.name}")

    except Exception as e:
        logger.error(f"Error indexing {file_path}: {e}")
        raise


def _update_index_json(file_path: Path, category: str, keywords: List[str]) -> None:
    """Update index.json with new prompt"""
    index_file = PROMPTS_DIR / 'index.json'

    try:
        if index_file.exists():
            index = json.loads(index_file.read_text())
        else:
            index = {'sessions': [], 'categories': {}, 'keywords': {}}

        relative_path = str(file_path.relative_to(PROMPTS_DIR))

        # Add to categories
        if category not in index['categories']:
            index['categories'][category] = []

        if relative_path not in index['categories'][category]:
            index['categories'][category].append(relative_path)

        # Add keywords
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower not in index['keywords']:
                index['keywords'][kw_lower] = []
            if relative_path not in index['keywords'][kw_lower]:
                index['keywords'][kw_lower].append(relative_path)

        index_file.write_text(json.dumps(index, indent=2))
        logger.info("✅ Updated index.json")

    except Exception as e:
        logger.warning(f"Failed to update index.json: {e}")


# ==================== CRUD Tools ====================

async def update_prompt(
    file_path: str,
    content: Optional[str] = None,
    category: Optional[str] = None,
    title: Optional[str] = None,
    keywords: Optional[List[str]] = None
) -> list[TextContent]:
    """
    Update an existing prompt.

    Allows updating content, category, title, or keywords of an existing prompt.
    Re-indexes automatically in RAG after update.

    Args:
        file_path: Relative path to the prompt file (e.g., "testing/prompt1.md")
        content: New content (optional, keeps existing if not provided)
        category: New category (optional, keeps existing if not provided)
        title: New title (optional, keeps existing if not provided)
        keywords: New keywords (optional, keeps existing if not provided)

    Returns:
        Success message with updated details
    """
    try:
        # 1. Validate file exists
        full_path = _validate_safe_path(PROMPTS_DIR, file_path)

        if not full_path.exists():
            return [TextContent(
                type="text",
                text=f"""❌ Prompt not found: {file_path}

Use search_prompts or list_prompts_by_category to find the correct path."""
            )]

        # 2. Read existing content
        existing_content = full_path.read_text(encoding='utf-8')

        # Parse existing metadata
        import re

        existing_metadata: dict[str, Any] = {}
        metadata_match = re.search(r'## Metadata\n(.*?)## Content', existing_content, re.DOTALL)
        if metadata_match:
            metadata_text = metadata_match.group(1)
            for line in metadata_text.split('\n'):
                if '**Type**:' in line:
                    existing_metadata['category'] = line.split(':')[1].strip()
                elif '**Keywords**:' in line:
                    kw_text = line.split(':')[1].strip()
                    existing_metadata['keywords'] = [
                        kw.strip()
                        for kw in kw_text.split(',')
                        if kw.strip() and kw.strip() != 'none'
                    ]
                elif '**Source**:' in line:
                    existing_metadata['source'] = line.split(':')[1].strip()

        title_match = re.search(r'# Prompt: (.+)', existing_content)
        if title_match:
            existing_metadata['title'] = title_match.group(1).strip()

        content_match = re.search(r'## Content\n\n(.*?)\n\n## Template Variables', existing_content, re.DOTALL)
        if content_match:
            existing_metadata['content'] = content_match.group(1).strip()

        # 3. Apply updates (only if provided)
        new_content = content if content is not None else existing_metadata.get('content', '')
        new_category = category if category is not None else existing_metadata.get('category', 'general')
        new_title = title if title is not None else existing_metadata.get('title', 'Untitled')
        new_keywords = (
            keywords
            if keywords is not None
            else cast(List[str], existing_metadata.get('keywords', []))
        )
        source = existing_metadata.get('source', 'manual')

        # Validate category
        valid_categories = CATEGORY_CHOICES
        if new_category not in valid_categories:
            logger.warning(f"Invalid category '{new_category}', using existing")
            new_category = existing_metadata.get('category', 'general')

        # 4. Check if category changed (need to move file)
        old_category = existing_metadata.get('category', 'general')
        category_changed = new_category != old_category

        if category_changed:
            # Move file to new category directory
            new_category_dir = PROMPTS_DIR / new_category
            new_category_dir.mkdir(exist_ok=True)
            new_file_path = new_category_dir / full_path.name

            # Delete old file
            full_path.unlink()
            full_path = new_file_path
            file_path = str(full_path.relative_to(PROMPTS_DIR))

        # 5. Create updated file content
        updated_file_content = _format_prompt_file(
            title=new_title,
            content=new_content,
            category=new_category,
            keywords=new_keywords,
            source=source
        )

        # 6. Write updated content
        full_path.write_text(updated_file_content, encoding='utf-8')
        logger.info(f"✅ Updated prompt file: {full_path}")

        # 7. Re-index in RAG (delete old, add new)
        if rag_system:
            try:
                # Delete old chunks
                old_ids = [id for id in rag_system.collection.get()['ids'] if full_path.stem in id]
                if old_ids:
                    rag_system.collection.delete(ids=old_ids)

                # Index new version
                _index_single_file(full_path)
            except Exception as e:
                logger.warning(f"RAG re-indexing failed: {e}")

        # 8. Update index.json
        _update_index_json(full_path, new_category, new_keywords)

        changes = []
        if content is not None:
            changes.append("content")
        if category is not None and category_changed:
            changes.append(f"category ({old_category} → {new_category})")
        if title is not None:
            changes.append("title")
        if keywords is not None:
            changes.append("keywords")

        changes_str = ", ".join(changes) if changes else "metadata refreshed"

        output = f"""✅ Prompt updated successfully!

📄 **File:** {file_path}
📂 **Category:** {new_category}
🏷️  **Title:** {new_title}
🔖 **Keywords:** {', '.join(new_keywords) if new_keywords else 'none'}

🔄 **Changes:** {changes_str}

The prompt has been re-indexed and is searchable with updated content."""

        return [TextContent(type="text", text=output)]

    except Exception as e:
        logger.error(f"Error updating prompt: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"""❌ Error updating prompt: {str(e)}

Please check the server logs for details."""
        )]


async def delete_prompt(
    file_path: str,
    confirm: bool = False
) -> list[TextContent]:
    """
    Delete a prompt from the library.

    Removes the file and all associated RAG chunks. Requires confirmation.

    Args:
        file_path: Relative path to the prompt file (e.g., "testing/prompt1.md")
        confirm: Must be True to actually delete (safety check)

    Returns:
        Success message or confirmation request
    """
    try:
        # 1. Validate file exists
        full_path = _validate_safe_path(PROMPTS_DIR, file_path)

        if not full_path.exists():
            return [TextContent(
                type="text",
                text=f"""❌ Prompt not found: {file_path}

Use search_prompts or list_prompts_by_category to find the correct path."""
            )]

        # 2. Require confirmation
        if not confirm:
            # Read file to show preview
            content = full_path.read_text(encoding='utf-8')

            # Extract title
            import re
            title_match = re.search(r'# Prompt: (.+)', content)
            title = title_match.group(1) if title_match else "Unknown"

            # Extract category
            category = full_path.parent.name

            return [TextContent(
                type="text",
                text=f"""⚠️  Confirmation required to delete prompt:

📄 **File:** {file_path}
📂 **Category:** {category}
🏷️  **Title:** {title}

This action cannot be undone!

To confirm deletion, call:
delete_prompt({{
  file_path: "{file_path}",
  confirm: true
}})"""
            )]

        # 3. Delete from RAG
        if rag_system:
            try:
                # Delete all chunks related to this file
                chunk_ids = [id for id in rag_system.collection.get()['ids'] if full_path.stem in id]
                if chunk_ids:
                    rag_system.collection.delete(ids=chunk_ids)
                    logger.info(f"Deleted {len(chunk_ids)} chunks from RAG")
            except Exception as e:
                logger.warning(f"RAG cleanup failed: {e}")

        # 4. Remove from index.json
        index_file = PROMPTS_DIR / 'index.json'
        if index_file.exists():
            try:
                index = json.loads(index_file.read_text())
                relative_path = str(full_path.relative_to(PROMPTS_DIR))

                # Remove from categories
                for cat_list in index.get('categories', {}).values():
                    if relative_path in cat_list:
                        cat_list.remove(relative_path)

                # Remove from keywords
                for kw_list in index.get('keywords', {}).values():
                    if relative_path in kw_list:
                        kw_list.remove(relative_path)

                index_file.write_text(json.dumps(index, indent=2))
            except Exception as e:
                logger.warning(f"Failed to update index.json: {e}")

        # 5. Delete the file
        category = full_path.parent.name
        filename = full_path.name
        full_path.unlink()
        logger.info(f"✅ Deleted prompt file: {full_path}")

        output = f"""✅ Prompt deleted successfully!

📄 **Deleted:** {file_path}
📂 **Category:** {category}
🗑️  **File removed:** {filename}

The prompt has been removed from:
- File system ✅
- RAG index ✅
- Metadata index ✅"""

        return [TextContent(type="text", text=output)]

    except Exception as e:
        logger.error(f"Error deleting prompt: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"""❌ Error deleting prompt: {str(e)}

Please check the server logs for details."""
        )]


async def create_prompt(
    content: str,
    category: Optional[str] = None,
    title: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    source: str = "manual"
) -> list[TextContent]:
    """
    Create a new prompt directly in the library.

    This allows creating prompts without needing a Copilot session file.
    Prompts are automatically categorized, indexed, and made searchable.

    Args:
        content: The prompt content (markdown supported)
        category: Category (auto-detected if None). Options: refactoring, testing,
                 debugging, implementation, documentation, code-review, general
        title: Title for the prompt (auto-generated if None)
        keywords: List of keywords for better searchability
        source: Origin of the prompt (manual, agent, import, etc.)

    Returns:
        Success message with file path and details
    """
    try:
        # 1. Auto-detect category if not provided
        if not category:
            category = _auto_classify_prompt(content)
            logger.info(f"Auto-detected category: {category}")

        # Validate category
        valid_categories = [
            'refactoring',
            'testing',
            'debugging',
            'implementation',
            'documentation',
            'general',
            'code-review',
        ]
        if category not in valid_categories:
            logger.warning(f"Invalid category '{category}', using 'general'")
            category = 'general'

        # 2. Auto-generate title if not provided
        if not title:
            title = _generate_title_from_content(content)
            logger.info(f"Auto-generated title: {title}")

        # 3. Generate unique filename
        from datetime import datetime
        import hashlib

        timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        filename = f"{timestamp}_{content_hash}_prompt1.md"

        # 4. Create structured file content
        file_content = _format_prompt_file(
            title=title,
            content=content,
            category=category,
            keywords=keywords or [],
            source=source
        )

        # 5. Save file
        category_dir = PROMPTS_DIR / category
        category_dir.mkdir(exist_ok=True)

        file_path = category_dir / filename
        file_path.write_text(file_content, encoding='utf-8')
        logger.info(f"✅ Created prompt file: {file_path}")

        # 6. Index immediately in RAG
        if rag_system:
            try:
                _index_single_file(file_path)
            except Exception as e:
                logger.warning(f"RAG indexing failed: {e}")

        # 7. Update index.json
        _update_index_json(file_path, category, keywords or [])

        relative_path = file_path.relative_to(PROMPTS_DIR)
        keywords_str = ', '.join(keywords) if keywords else 'none'

        output = f"""✅ Prompt created successfully!

📄 **File:** {relative_path}
📂 **Category:** {category}
🏷️  **Title:** {title}
🔖 **Keywords:** {keywords_str}
📝 **Source:** {source}

The prompt has been indexed and is now searchable.
Use search_prompts to find it!"""

        return [TextContent(type="text", text=output)]

    except Exception as e:
        logger.error(f"Error creating prompt: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"""❌ Error creating prompt: {str(e)}

Please check the server logs for details."""
        )]


async def main() -> None:
    """Main entry point for MCP server"""
    logger.info("🚀 Starting Prompt Library MCP Server...")

    # Initialize systems
    initialize_systems()

    logger.info("✅ Server ready")

    # Run server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
