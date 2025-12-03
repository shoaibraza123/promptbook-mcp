# 🤖 Promptbook MCP

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-enabled-brightgreen.svg)](https://www.docker.com/)
[![MCP](https://img.shields.io/badge/MCP-compatible-purple.svg)](https://modelcontextprotocol.io)

> Your personal cookbook for AI prompts with RAG-powered semantic search

## ✨ What is this?

**Promptbook MCP** is a plug-and-play server that helps developers who use AI coding assistants (like GitHub Copilot, Claude, etc.) to:

- 📚 **Store** prompts from your AI sessions automatically
- 🔍 **Search** prompts by *meaning*, not just keywords (RAG-powered)
- 🤖 **Access** your prompt library from any MCP-compatible tool
- 📊 **Organize** prompts by category (refactoring, testing, debugging, etc.)

**Perfect for:** Developers who reuse AI prompts and want a searchable knowledge base.

---

## 🚀 Quick Start

**Get running in 30 seconds:**

### Option 1: Automated Setup (Recommended)

```bash
git clone https://github.com/isaacpalomero/promptbook-mcp.git
cd promptbook-mcp
./setup.sh
```

That's it! 🎉

### Option 2: Docker

```bash
git clone https://github.com/isaacpalomero/promptbook-mcp.git
cd promptbook-mcp
docker-compose up -d
```

Done! Your server is running.

---

## 💡 Use Cases

**Problem:** You asked ChatGPT/Copilot the perfect prompt for refactoring last week. Now you can't find it.

**Solution:** Promptbook MCP auto-saves and indexes all your prompts.

```bash
# Later, search by meaning
search_prompts("refactor typescript to use dependency injection")
→ Returns your exact prompt from last week
```

### Real Examples

1. **Refactoring patterns** - Store your best "clean code" prompts
2. **Testing strategies** - Find that perfect test structure prompt
3. **Debugging workflows** - Access proven debugging prompts
4. **Code review** - Reuse comprehensive review prompts

---

## 📦 Installation

### Prerequisites

- Python 3.9+ OR Docker
- 2GB RAM minimum
- macOS, Linux, or Windows

### Detailed Setup

#### Automated Setup (Recommended)

```bash
# Clone repository
git clone https://github.com/isaacpalomero/promptbook-mcp.git
cd promptbook-mcp

# Run setup script
chmod +x setup.sh
./setup.sh

# Activate virtual environment
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Start server
python mcp_server.py
```

#### Docker Method

```bash
# Clone repository
git clone https://github.com/isaacpalomero/promptbook-mcp.git
cd promptbook-mcp

# Copy environment file
cp .env.example .env

# Start services
docker-compose up -d

# Verify
docker-compose logs
```

#### Manual Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p prompts sessions

# Index existing prompts (if any)
python prompt_rag.py --index

# Start server
python mcp_server.py
```

---

## 🎯 Features

### 1. Semantic Search (RAG)

Find prompts by **meaning**, not exact words:

```python
search_prompts("how to add unit tests")
→ Finds prompts about "testing", "jest", "pytest", etc.
```

### 2. Auto-Organization

Drop AI session files → Auto-categorized and indexed:

```bash
sessions/
└── copilot-session-abc123.md  → Auto-processed into:
    ├── prompts/refactoring/prompt1.md
    ├── prompts/testing/prompt2.md
    └── Updated RAG index
```

### 3. Multi-Provider Embeddings

Choose your embedding backend:
- **Sentence-Transformers** (default, local, CPU)
- **LMStudio** (GPU-accelerated, better quality)

```bash
# Use local embeddings (default)
EMBEDDING_PROVIDER=sentence-transformer

# Or use LMStudio
EMBEDDING_PROVIDER=lmstudio
LMSTUDIO_URL=http://localhost:1234
```

### 4. MCP Tools (13 Available)

Access via any MCP client:

| Tool | Description |
|------|-------------|
| `search_prompts` | Semantic search by meaning |
| `create_prompt` | Add new prompt directly |
| `update_prompt` | Modify existing prompt |
| `delete_prompt` | Remove prompt safely |
| `get_prompt_by_file` | Get full content |
| `list_prompts_by_category` | Browse by category |
| `find_similar_prompts` | Find related prompts |
| `get_library_stats` | View statistics |
| `index_prompts` | Rebuild search index |
| `organize_session` | Process AI session file |
| `get_prompt_index` | View full metadata index |

**Available categories:**
- `refactoring`
- `testing`
- `debugging`
- `implementation`
- `documentation`
- `code-review`
- `general`

---

## 🔌 MCP Client Setup

### Claude Desktop

1. Open Claude config file:
   ```bash
   # macOS
   ~/Library/Application Support/Claude/claude_desktop_config.json
   
   # Windows
   %APPDATA%\Claude\claude_desktop_config.json
   ```

2. Add Promptbook MCP server:
   ```json
   {
     "mcpServers": {
       "promptbook": {
         "command": "python",
         "args": ["/path/to/promptbook-mcp/mcp_server.py"]
       }
     }
   }
   ```

3. Restart Claude Desktop

### Other MCP Clients

Any MCP-compatible client can connect using the same pattern. See [MCP Protocol docs](https://modelcontextprotocol.io) for details.

---

## 📖 Documentation

- **[Setup Guide](./SETUP_GUIDE.md)** - Detailed installation steps
- **[Deployment Options](./DEPLOYMENT_OPTIONS.md)** - Docker, local, and production setups
- **[Embeddings Guide](./EMBEDDINGS_GUIDE.md)** - Configure RAG providers
- **[Contributing](./CONTRIBUTING.md)** - How to contribute
- **[Changelog](./CHANGELOG.md)** - Version history

---

# 👨‍💻 For Developers

## ⚙️ Configuration

All runtime settings are centralized in [`config.py`](./config.py) and exposed through an immutable `Config` dataclass. The server loads environment variables once at startup.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROMPTS_DIR` | Root folder for categorized prompts | `./prompts` |
| `SESSIONS_DIR` | Directory watched for exported sessions | `./sessions` |
| `VECTOR_DB_DIR` | Persistent ChromaDB path | `<PROMPTS_DIR>/.vectordb` |
| `EMBEDDING_PROVIDER` | `sentence-transformer` or `lmstudio` | `sentence-transformer` |
| `EMBEDDING_MODEL` | Sentence Transformers model name | `all-MiniLM-L6-v2` |
| `LMSTUDIO_URL` / `LMSTUDIO_MODEL` | LMStudio endpoint + model | `http://localhost:1234` / `nomic-embed-text` |
| `LMSTUDIO_DIMENSION` | Expected LMStudio embedding size | `768` |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Prompt chunking parameters | `500` / `100` |
| `ENABLE_RAG` | Toggle RAG initialization | `true` |
| `AUTO_REINDEX_INTERVAL` | Seconds between auto-index checks | `30` |
| `LOG_LEVEL` | Python logging level | `INFO` |

**Configuration file:**

```bash
# Copy example
cp .env.example .env

# Edit settings
vim .env
```

Access config anywhere in code:
```python
from config import CONFIG

print(CONFIG.prompts_dir)  # Validated Path object
print(CONFIG.embedding_provider)  # Type-safe enum
```

---

## 🧪 Testing & Quality

We enforce strict quality gates:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Style check
flake8 --max-line-length=100

# Type check
mypy --strict mcp_server.py prompt_rag.py prompt_organizer.py
```

### Quality Standards

- **Test Coverage**: Minimum 80%
- **Type Safety**: `mypy --strict` must pass
- **Code Style**: Flake8 compliant
- **CI Pipeline**: All checks run on Python 3.9-3.12

A GitHub Actions workflow (`.github/workflows/ci.yml`) runs these checks automatically.

---

## 🐳 Docker Advanced

### Multi-Stage Build

The `Dockerfile` uses a multi-stage build for optimized image size:

```dockerfile
# Stage 1: Builder (installs dependencies)
FROM python:3.11-slim as builder

# Stage 2: Runtime (slim final image)
FROM python:3.11-slim
COPY --from=builder /app/.venv /app/.venv
```

**Result:** Final image < 800 MB

### Health Checks

Docker includes automatic health monitoring:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -m prompt_rag --health || exit 1
```

### Volume Mounts

Persist data outside containers:

```yaml
volumes:
  - ./prompts:/app/prompts        # Prompt storage
  - ./sessions:/app/sessions      # Session import
  - ./prompts/.vectordb:/app/prompts/.vectordb  # RAG database
```

### Building & Running

```bash
# Build image
docker build -t promptbook-mcp:latest .

# Run container
docker run --rm -i \
  -v "$(pwd)/prompts:/app/prompts" \
  -v "$(pwd)/sessions:/app/sessions" \
  -e EMBEDDING_PROVIDER=sentence-transformer \
  promptbook-mcp:latest
```

---

## 🏗️ Architecture

### Components

```
┌─────────────────────────────────────┐
│         MCP Client (Claude)         │
└──────────────┬──────────────────────┘
               │ MCP Protocol
┌──────────────▼──────────────────────┐
│         mcp_server.py               │
│  - 13 MCP tools                     │
│  - Request routing                  │
│  - Error handling                   │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼──────┐  ┌─────▼────────┐
│prompt_rag.py│  │prompt_org.py │
│- RAG search │  │- Session     │
│- Embeddings │  │  parsing     │
│- ChromaDB   │  │- Auto-org    │
└─────────────┘  └──────────────┘
       │                │
       └───────┬────────┘
               │
┌──────────────▼──────────────────────┐
│       prompts/                      │
│       ├── refactoring/              │
│       ├── testing/                  │
│       ├── debugging/                │
│       └── .vectordb/                │
└─────────────────────────────────────┘
```

### Data Flow

1. **User** asks Claude to search prompts
2. **Claude** sends MCP request to `mcp_server.py`
3. **Server** calls `prompt_rag.py` for semantic search
4. **RAG** queries ChromaDB vector database
5. **Results** returned to Claude with metadata
6. **User** sees relevant prompts instantly

---

## 🤝 Contributing

We love contributions! 🎉

### Quick Start

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and add tests
4. Run tests: `pytest`
5. Ensure quality: `flake8 && mypy --strict`
6. Commit: `git commit -m 'feat: add amazing feature'`
7. Push: `git push origin feature/amazing-feature`
8. Open Pull Request

See [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed guidelines.

### Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test changes
- `chore:` Build/tooling changes

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](./LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [MCP Protocol](https://github.com/modelcontextprotocol)
- Powered by [ChromaDB](https://www.trychroma.com/) and [Sentence-Transformers](https://www.sbert.net/)
- Inspired by the need for better prompt management in AI-assisted development

---

## 📞 Support

- 🐛 [Report bugs](../../issues)
- 💡 [Request features](../../issues)
- 💬 [Discussions](../../discussions)
- 📖 [Documentation](./docs/)

---

**Made with ❤️ for the AI development community**
