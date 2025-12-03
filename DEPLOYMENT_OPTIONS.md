# 🐳 MCP Server Deployment Options

## Option 1: Docker Container (Recommended)

### 1.1 Standard Docker Run

**Pros:**
- Isolated environment
- No local Python dependencies
- Consistent across machines
- Easy updates (rebuild image)

**Cons:**
- Slower startup (~2-3s)
- Larger memory footprint
- Requires Docker running

**Config:**
```json
{
  "Prompt-Library": {
    "type": "local",
    "command": "docker",
    "tools": ["*"],
    "args": [
      "run",
      "-i",
      "--rm",
      "-v", "/Users/isaac/Development_Projects/ia_tools/mcp_tools/prompts:/app/prompts:ro",
      "-e", "PROMPTS_DIR=/app/prompts",
      "-e", "PYTHONUNBUFFERED=1",
      "mcp_tools-prompt-organizer:latest",
      "python", "mcp_server.py"
    ]
  }
}
```

**Build command:**
```bash
cd /Users/isaac/Development_Projects/ia_tools/mcp_tools
docker build -t mcp_tools-prompt-organizer:latest .
```

---

### 1.2 Docker with Named Container (Persistent)

**Pros:**
- Faster restarts (container stays alive)
- Shared state between calls
- Better for debugging

**Cons:**
- Must manage container lifecycle
- Memory stays allocated

**Config:**
```json
{
  "Prompt-Library": {
    "type": "local",
    "command": "docker",
    "tools": ["*"],
    "args": [
      "exec",
      "-i",
      "prompt-library-mcp",
      "python", "mcp_server.py"
    ]
  }
}
```

**Setup:**
```bash
# Start persistent container
docker run -d --name prompt-library-mcp \
  -v /Users/isaac/Development_Projects/ia_tools/mcp_tools/prompts:/app/prompts:ro \
  -e PROMPTS_DIR=/app/prompts \
  mcp_tools-prompt-organizer:latest \
  tail -f /dev/null

# Restart after code changes
docker restart prompt-library-mcp
```

---

## Option 2: uvx (Python Package Manager)

### 2.1 uvx with pyproject.toml

**Pros:**
- Fast startup (<1s)
- Automatic dependency management
- Clean, modern Python packaging
- No Docker required

**Cons:**
- Requires uv installed
- Less isolated than Docker

**Setup:**

Create `pyproject.toml`:
```toml
[project]
name = "prompt-library-mcp"
version = "0.1.0"
description = "MCP Server for Prompt Library with RAG"
requires-python = ">=3.11"
dependencies = [
    "mcp>=0.1.0",
    "chromadb>=0.4.0",
    "sentence-transformers>=2.2.0",
    "watchdog>=3.0.0",
]

[project.scripts]
prompt-library-mcp = "mcp_server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Config:**
```json
{
  "Prompt-Library": {
    "type": "local",
    "command": "uvx",
    "tools": ["*"],
    "args": [
      "--from", "/Users/isaac/Development_Projects/ia_tools/mcp_tools",
      "prompt-library-mcp"
    ],
    "env": {
      "PROMPTS_DIR": "/Users/isaac/Development_Projects/ia_tools/mcp_tools/prompts"
    }
  }
}
```

**Install uv:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

### 2.2 uvx with GitHub/PyPI

**Pros:**
- Can install from Git repo
- Version management
- Shareable across team

**Config:**
```json
{
  "Prompt-Library": {
    "type": "local",
    "command": "uvx",
    "tools": ["*"],
    "args": [
      "--from", "git+https://github.com/user/prompt-library-mcp",
      "prompt-library-mcp"
    ],
    "env": {
      "PROMPTS_DIR": "/Users/isaac/Development_Projects/ia_tools/mcp_tools/prompts"
    }
  }
}
```

---

## Option 3: Docker Compose Service

**Pros:**
- Managed lifecycle
- Easy multi-service orchestration
- Health checks
- Auto-restart

**Cons:**
- More complex setup
- Overkill for single service

**docker-compose.mcp.yml:**
```yaml
version: '3.8'

services:
  mcp-server:
    build: .
    container_name: prompt-library-mcp-stdio
    stdin_open: true
    tty: false
    command: python mcp_server.py
    volumes:
      - ./prompts:/app/prompts:ro
    environment:
      - PROMPTS_DIR=/app/prompts
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
```

**Config:**
```json
{
  "Prompt-Library": {
    "type": "local",
    "command": "docker",
    "tools": ["*"],
    "args": [
      "compose",
      "-f", "/Users/isaac/Development_Projects/ia_tools/mcp_tools/docker-compose.mcp.yml",
      "run",
      "--rm",
      "mcp-server"
    ]
  }
}
```

---

## Option 4: Hybrid - Docker Build + Direct Exec

**Pros:**
- Best of both worlds
- Fast execution
- Isolated dependencies

**Setup script (mcp-server-wrapper.sh):**
```bash
#!/bin/bash
cd /Users/isaac/Development_Projects/ia_tools/mcp_tools
source .venv/bin/activate
export PROMPTS_DIR="$PWD/prompts"
exec python mcp_server.py "$@"
```

**Config:**
```json
{
  "Prompt-Library": {
    "type": "local",
    "command": "/Users/isaac/Development_Projects/ia_tools/mcp_tools/mcp-server-wrapper.sh",
    "tools": ["*"]
  }
}
```

---

## 📊 Comparison Matrix

| Option | Startup | Memory | Isolation | Maintenance | Recommended For |
|--------|---------|--------|-----------|-------------|-----------------|
| Docker run --rm | 2-3s | High | Excellent | Easy | Production |
| Docker exec | <1s | Medium | Excellent | Manual | Development |
| uvx | <1s | Low | Good | Auto | Local dev |
| Docker Compose | 2-3s | High | Excellent | Easy | Multi-service |
| Wrapper script | <1s | Low | Medium | Manual | Current setup |

---

## 🎯 Recommended Approach

### For Production/Team Use: **Option 1.1 (Docker run --rm)**

```json
{
  "Prompt-Library": {
    "type": "local",
    "command": "docker",
    "tools": ["*"],
    "args": [
      "run",
      "-i",
      "--rm",
      "-v", "/Users/isaac/Development_Projects/ia_tools/mcp_tools/prompts:/app/prompts:ro",
      "mcp-tools-prompt-library:latest",
      "python", "mcp_server.py"
    ],
    "env": {
      "PROMPTS_DIR": "/app/prompts"
    }
  }
}
```

### For Development: **Option 2.1 (uvx)**

Creates `pyproject.toml` and uses uvx for fast iteration.

---

## 🚀 Migration Steps

### To Docker:
```bash
# 1. Build image
docker build -t mcp-tools-prompt-library:latest .

# 2. Test locally
docker run --rm -i \
  -v "$PWD/prompts:/app/prompts:ro" \
  mcp-tools-prompt-library:latest \
  python mcp_server.py

# 3. Update config
# Use config from Option 1.1

# 4. Restart Copilot CLI
```

### To uvx:
```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Create pyproject.toml
# Use template from Option 2.1

# 3. Test
uvx --from . prompt-library-mcp

# 4. Update config
# Use config from Option 2.1

# 5. Restart Copilot CLI
```

