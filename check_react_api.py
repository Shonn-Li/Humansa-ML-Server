#!/usr/bin/env python3
"""Check ReActAgent API in new llama-index version"""

from llama_index.core.agent import ReActAgent

print("ReActAgent available methods:")
for attr in dir(ReActAgent):
    if not attr.startswith('_'):
        print(f"  - {attr}")

# Check if there's a constructor
print("\nChecking constructors...")
print(f"  - __init__ signature: {ReActAgent.__init__.__doc__}")

# Try to find the right way to create an agent
if hasattr(ReActAgent, 'from_tools'):
    print("  - from_tools is available")
else:
    print("  - from_tools is NOT available")
    
# Check for other factory methods
for attr in dir(ReActAgent):
    if attr.startswith('from_'):
        print(f"  - Found factory method: {attr}")