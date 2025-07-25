#!/usr/bin/env python3
"""
Test the enhanced HUMANSA_REACT_PROMPT_V2 to verify it contains the identity instructions.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.humansa.prompts.humansa_system_prompt_v2 import HUMANSA_REACT_PROMPT_V2

print("🔍 Checking Enhanced HUMANSA_REACT_PROMPT_V2")
print("=" * 50)

# Check for key identity elements
identity_checks = [
    ("小诺 mentioned", "小诺" in HUMANSA_REACT_PROMPT_V2),
    ("Company slogan", "以爱行舟，亲近相守" in HUMANSA_REACT_PROMPT_V2),
    ("Doctor count", "500多位" in HUMANSA_REACT_PROMPT_V2),
    ("Clinic count", "30+家" in HUMANSA_REACT_PROMPT_V2),
    ("Greeting instructions", "问候回应" in HUMANSA_REACT_PROMPT_V2),
    ("Identity introduction rule", "介绍自己" in HUMANSA_REACT_PROMPT_V2)
]

all_passed = True
for check_name, result in identity_checks:
    status = "✅" if result else "❌"
    print(f"{status} {check_name}: {result}")
    if not result:
        all_passed = False

print("\n📝 Prompt Preview:")
print("-" * 50)
print(HUMANSA_REACT_PROMPT_V2[:500] + "...")

if all_passed:
    print("\n✅ All identity elements are present in the enhanced prompt!")
else:
    print("\n❌ Some identity elements are missing from the prompt!")

# Show specific greeting instruction
print("\n🎯 Greeting Instruction Section:")
print("-" * 50)
lines = HUMANSA_REACT_PROMPT_V2.split('\n')
in_greeting_section = False
for line in lines:
    if "问候回应" in line:
        in_greeting_section = True
    if in_greeting_section and line.strip() == "":
        break
    if in_greeting_section:
        print(line)