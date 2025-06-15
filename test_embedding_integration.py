#!/usr/bin/env python3
"""
Test embedding functionality in enhanced chat bot
"""

import requests
import json


def test_note_embedding_functionality():
    """Test that note embedding functionality works in enhanced chat bot"""

    base_url = "http://localhost:5001"

    print("📝 Testing Note Embedding Functionality")
    print("=" * 60)

    # Test 1: Test with your specific note IDs and question
    print("\n1. Testing embedding with specific note IDs...")

    try:
        chat_data = {
            "messages": [
                {"role": "user", "content": "Hows future AI trend? Please provide your sources"}
            ],
            "model": "gpt-4.1-nano",
            "note_ids": [2769, 2771, 2857, 2856, 2272],
            "max_tokens": 300
        }

        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json=chat_data,
            timeout=45
        )

        if response.status_code == 200:
            result = response.json()
            message = result['choices'][0]['message']['content']
            used_notes = result.get('used_notes', [])

            print("   ✅ Note embedding retrieval successful!")
            print(f"   Question: Hows future AI trend? Please provide your sources")
            print(f"   Input note IDs: [2769, 2771, 2857, 2856, 2272]")
            print(f"   Used notes (most relevant): {used_notes}")
            print(f"   Response: {message}")
            print(f"   Provider: {result.get('provider', 'unknown')}")
            print(f"   Model: {result.get('model', 'unknown')}")

        else:
            print(f"   ❌ Note embedding failed: {response.status_code}")
            print(f"   Error: {response.text}")

    except Exception as e:
        print(f"   ❌ Note embedding test failed: {e}")

    # Test 2: Test with simplified chat endpoint
    print(f"\n2. Testing with simplified /v1/chat endpoint...")

    try:
        chat_data = {
            "question": "Hows future AI trend? Please provide your sources",
            "note_ids": [2769, 2771, 2857, 2856, 2272],
            "model": "gpt-4.1-nano",
            "max_tokens": 300
        }

        response = requests.post(
            f"{base_url}/v1/chat",
            headers={"Content-Type": "application/json"},
            json=chat_data,
            timeout=45
        )

        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', '')
            used_notes = result.get('used_notes', [])

            print("   ✅ Simplified chat endpoint working!")
            print(f"   Used notes: {used_notes}")
            print(f"   Answer: {answer}")

        else:
            print(f"   ❌ Simplified chat failed: {response.status_code}")
            print(f"   Error: {response.text}")

    except Exception as e:
        print(f"   ❌ Simplified chat test failed: {e}")

    # Test 3: Test without note IDs (should work)
    print(f"\n3. Testing without note IDs (baseline)...")

    try:
        chat_data = {
            "messages": [
                {"role": "user", "content": "Hello, how are you?"}
            ],
            "model": "gpt-4.1-nano",
            "max_tokens": 50
        }

        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json=chat_data,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            message = result['choices'][0]['message']['content']
            print(f"   ✅ Baseline chat working!")
            print(f"   Response: {message}")
        else:
            print(f"   ❌ Baseline chat failed: {response.status_code}")

    except Exception as e:
        print(f"   ❌ Baseline chat error: {e}")

    print(f"\n" + "=" * 60)
    print("🎯 Embedding Integration Summary:")
    print("   - Enhanced chat bot should use note_utils.py functions")
    print("   - Embeddings should be created automatically for new notes")
    print("   - Cosine similarity should find most relevant notes")
    print("   - RAG should work with note context + LLM response")


def test_note_text_endpoint():
    """Test the note text endpoint to see what notes are available"""

    print(f"\n📋 Testing Your Specific Notes")
    print("=" * 60)

    base_url = "http://localhost:5001"

    # Test your specific note IDs
    note_ids = [2769, 2771, 2857, 2856, 2272]

    for note_id in note_ids:
        try:
            response = requests.get(f"{base_url}/note_text/{note_id}")
            if response.status_code == 200:
                result = response.json()
                note_text = result.get('note_text', '')
                if note_text and note_text != "Note not found":
                    print(f"   ✅ Note {note_id}: {note_text[:150]}...")
                else:
                    print(f"   ❌ Note {note_id}: No content found")
            else:
                print(
                    f"   ❌ Note {note_id}: Not found ({response.status_code})")
        except Exception as e:
            print(f"   ❌ Note {note_id}: Error - {e}")


if __name__ == "__main__":
    print("🚀 Testing Enhanced Chat Bot Embedding Integration")

    # First check what notes are available
    test_note_text_endpoint()

    # Then test the embedding functionality
    test_note_embedding_functionality()

    print(f"\n🏁 Testing Complete!")
