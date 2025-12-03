#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from providers.embeddings import LMStudioProvider

print("🔬 Testing LMStudio connection with text-embedding-gte-base...")

try:
    provider = LMStudioProvider(
        base_url="http://127.0.0.1:1234",
        model_name="text-embedding-gte-base",
        dimension=768
    )

    print(f"✅ Provider initialized: {provider.get_name()}")
    print(f"✅ Dimension: {provider.get_dimension()}")

    # Test embedding
    texts = ["Hello world", "Testing embeddings"]
    embeddings = provider.embed(texts)

    print(f"✅ Generated {len(embeddings)} embeddings")
    print(f"✅ Each embedding has {len(embeddings[0])} dimensions")
    print(f"✅ First 5 values: {embeddings[0][:5]}")

    print("\n🎉 LMStudio provider working correctly!")

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
