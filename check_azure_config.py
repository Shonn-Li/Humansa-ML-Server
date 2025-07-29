#!/usr/bin/env python3
"""Check Azure OpenAI configuration"""

import os

print("Checking Azure OpenAI Configuration:")
print("=" * 50)

# Check environment variables
azure_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_INFERENCE_CREDENTIAL")
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://youwoai-dev-resource.openai.azure.com/")
openai_key = os.getenv("OPENAI_API_KEY")

print(f"AZURE_OPENAI_API_KEY: {'Set' if os.getenv('AZURE_OPENAI_API_KEY') else 'Not set'}")
print(f"AZURE_INFERENCE_CREDENTIAL: {'Set' if os.getenv('AZURE_INFERENCE_CREDENTIAL') else 'Not set'}")
print(f"AZURE_OPENAI_ENDPOINT: {azure_endpoint}")
print(f"OPENAI_API_KEY: {'Set' if openai_key else 'Not set'}")

print("\nMem0 Configuration:")
if azure_key and azure_endpoint:
    print("✅ Would use Azure OpenAI for Mem0")
    print(f"   Endpoint: {azure_endpoint}")
    print(f"   Model: gpt-4.1")
elif openai_key:
    print("⚠️ Would fall back to OpenAI for Mem0")
    print(f"   Model: gpt-3.5-turbo")
else:
    print("❌ No API keys available for Mem0")

# Try to import and check Mem0
try:
    from mem0 import Memory
    print("\n✅ Mem0 package is installed")
    
    # Check version
    import mem0
    if hasattr(mem0, '__version__'):
        print(f"   Version: {mem0.__version__}")
except ImportError:
    print("\n❌ Mem0 package not installed")