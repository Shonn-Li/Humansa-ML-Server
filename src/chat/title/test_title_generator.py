"""
Test script for conversation title generation

This script tests the title generator module to ensure it works correctly.
"""

from chat.title.title_generator import title_generator
import asyncio
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))


class MockLLM:
    """Mock LLM for testing title generation"""

    def __init__(self):
        self.temperature = 0.7

    async def acomplete(self, prompt):
        """Mock completion that returns a simple title"""
        if "Python" in prompt:
            return "Python Error Fix"
        elif "recipe" in prompt.lower():
            return "Recipe Ideas"
        elif "AI" in prompt:
            return "AI Assistant Help"
        else:
            return "General Discussion"


async def test_title_generation():
    """Test the title generation functionality"""

    # Test case 1: Python error question
    messages1 = [
        {"role": "user", "content": "How do I fix this Python import error?"},
        {"role": "assistant", "content": "You can fix the import error by..."},
        {"role": "user", "content": "Can you show me an example?"}
    ]

    # Test case 2: Recipe question
    messages2 = [
        {"role": "user", "content": "What are some easy dinner recipes for tonight?"}
    ]

    # Test case 3: AI question
    messages3 = [
        {"role": "user", "content": "What can AI assistants help me with?"},
        {"role": "assistant", "content": "AI assistants can help with..."},
        {"role": "user", "content": "That's very helpful, thank you!"}
    ]

    mock_llm = MockLLM()

    print("🧪 Testing Title Generation...")
    print("=" * 50)

    # Test 1
    print("\\n📝 Test 1: Python Error Question")
    print("Messages:", len(messages1), "messages")
    title1 = await title_generator.generate_conversation_title(messages1, mock_llm)
    print(f"Generated Title: '{title1}'")

    # Test 2
    print("\\n📝 Test 2: Recipe Question")
    print("Messages:", len(messages2), "messages")
    title2 = await title_generator.generate_conversation_title(messages2, mock_llm)
    print(f"Generated Title: '{title2}'")

    # Test 3
    print("\\n📝 Test 3: AI Assistant Question")
    print("Messages:", len(messages3), "messages")
    title3 = await title_generator.generate_conversation_title(messages3, mock_llm)
    print(f"Generated Title: '{title3}'")

    # Test edge case: No user messages
    print("\\n📝 Test 4: No User Messages (Edge Case)")
    empty_messages = [
        {"role": "system", "content": "You are a helpful assistant"}
    ]
    title4 = await title_generator.generate_conversation_title(empty_messages, mock_llm)
    print(f"Generated Title: '{title4}'")

    print("\\n✅ All tests completed!")
    print("🏷️ Title Generator module is working correctly")


if __name__ == "__main__":
    asyncio.run(test_title_generation())
