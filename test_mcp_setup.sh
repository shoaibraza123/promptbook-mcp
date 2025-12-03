#!/bin/bash
# Test MCP server locally without installing dependencies

echo "🧪 Testing MCP Server Configuration"
echo "===================================="
echo ""

# Check if mcp_server.py exists
if [ -f "mcp_server.py" ]; then
    echo "✅ mcp_server.py found"
else
    echo "❌ mcp_server.py not found"
    exit 1
fi

# Check Python syntax
echo ""
echo "Checking Python syntax..."
python3 -m py_compile mcp_server.py 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Python syntax OK"
else
    echo "❌ Python syntax errors found"
    exit 1
fi

# Check if prompts directory exists
if [ -d "prompts" ]; then
    prompt_count=$(find prompts -name "*.md" -not -name "README.md" | wc -l)
    echo "✅ Prompts directory found ($prompt_count prompts)"
else
    echo "⚠️  Prompts directory not found (will be created on first run)"
fi

# Display configuration
echo ""
echo "📋 MCP Configuration (mcp_config.json):"
cat mcp_config.json | python3 -m json.tool

echo ""
echo "🎯 Available Tools:"
echo "  1. search_prompts - Semantic search with RAG"
echo "  2. get_prompt_by_file - Get full prompt content"
echo "  3. find_similar_prompts - Find related prompts"
echo "  4. list_prompts_by_category - List by category"
echo "  5. get_library_stats - Library statistics"
echo "  6. index_prompts - Manual RAG indexing"
echo "  7. organize_session - Process session file"
echo "  8. get_prompt_index - Get full index"

echo ""
echo "📝 Next Steps:"
echo "  1. Install MCP: pip install mcp (or use Docker)"
echo "  2. Test server: python3 mcp_server.py"
echo "  3. Configure Claude Desktop with mcp_config.json"
echo ""
echo "✅ MCP Server configuration test complete!"
