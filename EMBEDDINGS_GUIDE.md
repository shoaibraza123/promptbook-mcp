# 🔬 Embedding Providers Guide

## Overview

The prompt library now supports multiple embedding providers for flexible RAG configuration:

- **sentence-transformers** (default): Fast, local, CPU-friendly
- **LMStudio**: GPU-accelerated, higher quality, larger models

## Quick Start

### Using Default (sentence-transformers)

No configuration needed - works out of the box:

```bash
python prompt_rag.py --search "testing automation"
```

### Using LMStudio

1. **Start LMStudio** with an embedding model loaded (e.g., nomic-embed-text)

2. **Configure environment:**
```bash
export EMBEDDING_PROVIDER=lmstudio
export LMSTUDIO_URL=http://localhost:1234
export LMSTUDIO_MODEL=nomic-embed-text
```

3. **Use normally:**
```bash
python prompt_rag.py --search "testing automation"
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_PROVIDER` | `sentence-transformer` | Provider type |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Model for sentence-transformers |
| `LMSTUDIO_URL` | `http://localhost:1234` | LMStudio API endpoint |
| `LMSTUDIO_MODEL` | `nomic-embed-text` | Model name in LMStudio |
| `LMSTUDIO_DIMENSION` | `768` | Expected embedding dimension |

### Docker Usage

#### With sentence-transformers (default)

```yaml
services:
  mcp-server:
    environment:
      - EMBEDDING_PROVIDER=sentence-transformer
```

#### With LMStudio

```yaml
services:
  mcp-server:
    environment:
      - EMBEDDING_PROVIDER=lmstudio
      - LMSTUDIO_URL=http://host.docker.internal:1234
      - LMSTUDIO_MODEL=nomic-embed-text
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

## Comparison

### sentence-transformers (all-MiniLM-L6-v2)

**Pros:**
- ✅ Fast (~1000 tokens/s)
- ✅ No external dependencies
- ✅ Works offline
- ✅ Low memory (~500MB)
- ✅ CPU-friendly

**Cons:**
- ⚠️ Lower dimension (384)
- ⚠️ Good but not best quality

**Best for:** Development, quick searches, CPU-only machines

### LMStudio (nomic-embed-text)

**Pros:**
- ✅ Higher quality embeddings
- ✅ Larger dimension (768)
- ✅ GPU acceleration
- ✅ Multiple model options
- ✅ Better for complex queries

**Cons:**
- ⚠️ Requires LMStudio running
- ⚠️ Slower (~2-3x via HTTP)
- ⚠️ More memory (~1.2GB)
- ⚠️ Needs GPU for best performance

**Best for:** Production, important searches, GPU-enabled systems

## Best Practices

1. **Use sentence-transformers for Development** - Fast iteration
2. **Use LMStudio for Production** - Better quality
3. **Keep Collections Separate** - Don't mix providers
4. **Monitor Performance** - Benchmark before switching
5. **Document Your Choice** - Add to project README

---

**Updated:** 2025-12-03  
**Version:** 1.0.0  
**Supported Providers:** sentence-transformers, LMStudio
