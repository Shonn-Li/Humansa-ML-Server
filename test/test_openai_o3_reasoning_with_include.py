#!/usr/bin/env python3
"""
OpenAI o3 Reasoning Streaming Test with Detailed Summary
This script tests the OpenAI o3 model with reasoning summary enabled using the correct 'reasoning' parameter.
"""

import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv(
    '/Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server/.env')


def test_openai_o3_reasoning_with_include():
    """Test OpenAI o3 with detailed reasoning summary using reasoning parameter"""

    # Get API key from environment
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        return

    print(f"🔑 Using API Key: {api_key[:20]}..." if api_key else "No API Key")

    # Prepare the request for o3 with reasoning include
    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "o3",
        "stream": True,
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "What is Elon Musk's America Party and why did he create it? Please think step by step about this complex political question."
                    }
                ]
            }
        ],
        "tools": [
            {"type": "web_search"}
        ],
        "reasoning": {
            "effort": "low",
            "summary": "detailed"
        },
        "max_output_tokens": 3000,
        "store": True,
        "background": False
    }

    # Create output file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"/Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/openai_o3_reasoning_with_include_{timestamp}.txt"

    print(f"🚀 Starting OpenAI o3 reasoning test with detailed summary...")
    print(f"📝 Output will be saved to: {output_file}")
    print(f"🌐 URL: {url}")
    print(f"📊 Model: {payload['model']}")
    print(f"🔧 Tools: {payload['tools']}")
    print(f"🧠 Reasoning: {payload['reasoning']}")
    print(f"💭 Question: {payload['input'][0]['content'][0]['text']}")
    print("=" * 80)

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header information
            f.write(
                f"OpenAI o3 Reasoning Streaming Test with Detailed Summary - {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n")
            f.write(f"URL: {url}\n")
            f.write(f"Model: {payload['model']}\n")
            f.write(f"Question: {payload['input'][0]['content'][0]['text']}\n")
            f.write(f"Tools: {json.dumps(payload['tools'], indent=2)}\n")
            f.write(
                f"Reasoning: {json.dumps(payload['reasoning'], indent=2)}\n")
            f.write(f"Max Output Tokens: {payload['max_output_tokens']}\n")
            f.write(f"Background: {payload['background']}\n")
            f.write(f"Store: {payload['store']}\n")
            f.write("=" * 80 + "\n\n")

            # Make the streaming request
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                stream=True
            )

            print(f"📡 Response Status: {response.status_code}")
            f.write(f"Response Status: {response.status_code}\n")
            f.write(f"Response Headers: {dict(response.headers)}\n")
            f.write("\n" + "=" * 50 + " STREAMING EVENTS " + "=" * 50 + "\n\n")

            if response.status_code != 200:
                error_text = response.text
                print(f"❌ Error: {response.status_code} - {error_text}")
                f.write(f"ERROR: {response.status_code}\n{error_text}\n")
                return

            event_count = 0
            start_time = time.time()
            reasoning_events = 0
            reasoning_with_content = 0
            tool_call_events = 0
            content_events = 0

            # Process streaming response
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    current_time = time.time() - start_time
                    event_count += 1

                    # Print to console
                    print(
                        f"[{current_time:.2f}s] Event #{event_count}: {line[:100]}...")

                    # Write to file
                    f.write(f"[{current_time:.2f}s] Event #{event_count}:\n")
                    f.write(f"{line}\n")
                    f.write("-" * 40 + "\n")

                    # Try to parse as JSON for better formatting and event categorization
                    if line.startswith('data: '):
                        try:
                            json_data = line[6:]  # Remove 'data: ' prefix
                            if json_data.strip() and json_data.strip() != '[DONE]':
                                parsed = json.loads(json_data)
                                f.write(
                                    f"Parsed JSON:\n{json.dumps(parsed, indent=2)}\n")

                                # Categorize events and look for reasoning content
                                if 'type' in parsed:
                                    event_type = parsed['type']
                                    if 'reasoning' in event_type.lower():
                                        reasoning_events += 1
                                        f.write(
                                            f"🧠 REASONING EVENT DETECTED\n")

                                        # Check if reasoning has actual content
                                        if 'item' in parsed and 'summary' in parsed['item']:
                                            summary = parsed['item']['summary']
                                            if summary and len(summary) > 0:
                                                reasoning_with_content += 1
                                                f.write(
                                                    f"🎯 REASONING WITH CONTENT FOUND: {len(summary)} items\n")

                                        # Check for encrypted content
                                        if 'item' in parsed and 'encrypted_content' in parsed['item']:
                                            f.write(
                                                f"🔐 ENCRYPTED REASONING CONTENT FOUND\n")

                                    elif 'tool' in event_type.lower() or 'web_search' in event_type.lower():
                                        tool_call_events += 1
                                        f.write(
                                            f"🔧 TOOL CALL EVENT DETECTED\n")
                                    elif 'content' in event_type.lower() or 'delta' in event_type.lower() or 'output_text' in event_type.lower():
                                        content_events += 1
                                        f.write(f"💬 CONTENT EVENT DETECTED\n")

                        except json.JSONDecodeError:
                            f.write(f"Non-JSON data: {json_data}\n")

                    f.write("\n")
                    f.flush()  # Ensure immediate write

            total_time = time.time() - start_time
            print(f"\n✅ Streaming completed!")
            print(f"📊 Total events received: {event_count}")
            print(f"🧠 Reasoning events: {reasoning_events}")
            print(f"🎯 Reasoning with content: {reasoning_with_content}")
            print(f"🔧 Tool call events: {tool_call_events}")
            print(f"💬 Content events: {content_events}")
            print(f"⏱️  Total time: {total_time:.2f} seconds")

            f.write("\n" + "=" * 50 + " SUMMARY " + "=" * 50 + "\n")
            f.write(f"Total events received: {event_count}\n")
            f.write(f"Reasoning events: {reasoning_events}\n")
            f.write(f"Reasoning with content: {reasoning_with_content}\n")
            f.write(f"Tool call events: {tool_call_events}\n")
            f.write(f"Content events: {content_events}\n")
            f.write(f"Total time: {total_time:.2f} seconds\n")
            f.write(
                f"Average time per event: {total_time/event_count:.3f} seconds\n" if event_count > 0 else "")

    except requests.exceptions.RequestException as e:
        error_msg = f"❌ Request error: {str(e)}"
        print(error_msg)
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(f"\nERROR: {error_msg}\n")

    except Exception as e:
        error_msg = f"❌ Unexpected error: {str(e)}"
        print(error_msg)
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(f"\nUNEXPECTED ERROR: {error_msg}\n")

    print(f"\n📄 Full output saved to: {output_file}")


if __name__ == "__main__":
    test_openai_o3_reasoning_with_include()
