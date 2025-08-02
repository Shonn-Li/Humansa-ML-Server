#!/usr/bin/env python3
"""Test if agents can be imported after llama-index upgrade"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Testing agent imports...")

try:
    print("\n1. Testing ProductAgent import...")
    from humansa.v2.agents.product_agent import ProductAgent
    print("✅ ProductAgent imported successfully")
except Exception as e:
    print(f"❌ ProductAgent import failed: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n2. Testing other agents...")
    from humansa.v2.agents import (
        AppointmentAgent,
        DiagnosisAgent,
        MedicationAgent,
        GeneralMedicalAgent
    )
    print("✅ All other agents imported successfully")
except Exception as e:
    print(f"❌ Other agents import failed: {e}")
    import traceback
    traceback.print_exc()

print("\n3. Testing llama-index core imports...")
try:
    from llama_index.core.agent import ReActAgent
    from llama_index.core.tools import FunctionTool
    from llama_index.core.llms import LLM
    print("✅ LlamaIndex core imports successful")
except Exception as e:
    print(f"❌ LlamaIndex core imports failed: {e}")
    import traceback
    traceback.print_exc()

print("\nDone!")