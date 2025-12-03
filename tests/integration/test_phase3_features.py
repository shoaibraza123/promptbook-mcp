#!/usr/bin/env python3
"""
Test Phase 3 Features:
- organize_session with session_type parameter
- Validation of session types
- Error messages for unsupported types
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server import organize_session
import asyncio


async def test_organize_session_validation():
    """Test session type validation"""

    print("=" * 60)
    print("TEST 1: Session type validation")
    print("=" * 60)

    # Test with unsupported session type
    print("\n1️⃣ Testing with unsupported session type 'claude-code'...")
    result = await organize_session(
        session_path="/fake/path.md",
        session_type="claude-code"
    )

    print(f"\nResult: {result[0].text}")
    assert "Unsupported session type" in result[0].text, "Should reject unsupported type"
    assert "copilot-cli" in result[0].text, "Should mention supported types"
    print("✅ Correctly rejects unsupported session type")

    # Test with default (copilot-cli)
    print("\n\n2️⃣ Testing with default session type (copilot-cli)...")
    result = await organize_session(
        session_path="/fake/path.md"
        # session_type defaults to "copilot-cli"
    )

    print(f"\nResult: {result[0].text}")
    # Should get "file not found" error, not "unsupported type"
    assert "File not found" in result[0].text, "Should accept default type"
    assert "Unsupported session type" not in result[0].text
    print("✅ Default session type works correctly")

    # Test with explicit copilot-cli
    print("\n\n3️⃣ Testing with explicit session_type='copilot-cli'...")
    result = await organize_session(
        session_path="/fake/path.md",
        session_type="copilot-cli"
    )

    print(f"\nResult: {result[0].text}")
    assert "File not found" in result[0].text
    assert "Unsupported session type" not in result[0].text
    print("✅ Explicit copilot-cli type works correctly")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)


async def test_error_messages():
    """Test helpful error messages"""

    print("\n\n" + "=" * 60)
    print("TEST 2: Error message quality")
    print("=" * 60)

    print("\n1️⃣ Testing error message for unsupported type...")
    result = await organize_session(
        session_path="/fake/path.md",
        session_type="some-random-agent"
    )

    error_text = result[0].text
    print(f"\nError message:\n{error_text}")

    # Check that error message is helpful
    checks = [
        ("Unsupported session type" in error_text, "Mentions unsupported type"),
        ("copilot-cli" in error_text, "Lists supported types"),
        ("create_prompt" in error_text, "Suggests alternative"),
    ]

    for check, description in checks:
        status = "✅" if check else "❌"
        print(f"{status} {description}")
        assert check, f"Failed: {description}"

    print("\n✅ Error messages are helpful and informative")


async def main():
    """Run all tests"""
    print("\n🧪 Testing Phase 3 Features\n")

    try:
        await test_organize_session_validation()
        await test_error_messages()

        print("\n\n🎉 ALL PHASE 3 TESTS PASSED!")
        print("\nImplemented features:")
        print("  ✅ session_type parameter with validation")
        print("  ✅ Default to 'copilot-cli'")
        print("  ✅ Helpful error messages")
        print("  ✅ Clear separation from create_prompt")

        print("\n📋 Documented but not implemented:")
        print("  📄 SubFase 3.3: Additional session parsers (Claude Code, Cursor)")
        print("  📄 SubFase 3.4: Auto-detection of session types")
        print("\n  See: docs/PHASE_3_ROADMAP.md for implementation plans")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
