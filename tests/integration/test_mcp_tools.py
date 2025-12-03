#!/usr/bin/env python3
"""
Test MCP server tools directly (simulating MCP calls)
"""

import sys
import os
from pathlib import Path
import asyncio

# Setup paths
SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))
os.environ['PROMPTS_DIR'] = str(SCRIPT_DIR / 'prompts')

# Import server components
from mcp_server import (
    initialize_systems,
    search_prompts,
    get_library_stats,
    list_prompts_by_category,
    prompts_dir
)

async def test_search():
    """Test search_prompts tool"""
    print("=" * 60)
    print("🧪 Testing: search_prompts")
    print("=" * 60)

    result = await search_prompts("testing automation", None, 3)
    print(result[0].text)
    print()

async def test_stats():
    """Test get_library_stats tool"""
    print("=" * 60)
    print("🧪 Testing: get_library_stats")
    print("=" * 60)

    result = await get_library_stats()
    print(result[0].text)
    print()

async def test_list_category():
    """Test list_prompts_by_category tool"""
    print("=" * 60)
    print("🧪 Testing: list_prompts_by_category")
    print("=" * 60)

    result = await list_prompts_by_category("testing")
    print(result[0].text)
    print()

async def main():
    print("🚀 MCP Server Tool Tests")
    print(f"📂 Prompts directory: {prompts_dir}")
    print()

    # Initialize systems
    print("Initializing systems...")
    initialize_systems()
    print("✅ Systems initialized")
    print()

    # Run tests
    await test_stats()
    await test_list_category()
    await test_search()

    print("✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
