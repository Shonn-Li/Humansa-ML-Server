"""
OpenAI O3 Demo Endpoint - Quick Demo Wrapper

This endpoint provides a quick demo of OpenAI O3 streaming wrapped with our
comprehensive streaming format and system prompts.

Usage:
POST /api/humansa/o3-demo
{
    "messages": [{"role": "user", "content": "帮我预约深圳的心脏科医生"}],
    "stream": true,
    "user_id": "demo_user"
}
"""

import os
import logging
import time
import asyncio
import json
import uuid
from typing import Dict, Any
from datetime import datetime
from typing import Dict, Any
from datetime import datetime

from .humansa_chat_endpoint import HumansaChatEndpoint

logger = logging.getLogger(__name__)


class O3DemoEndpoint:
    """
    OpenAI O3 Demo Endpoint

    Provides a quick demo interface for testing O3 model with our streaming format.
    """

    def __init__(self):
        """Initialize the O3 demo endpoint."""
        self.humansa_endpoint = HumansaChatEndpoint()
        logger.info("🤖 O3DemoEndpoint initialized")

    async def handle_demo_request(self, request_data: Dict[str, Any]):
        """
        Handle O3 demo requests - Direct forwarding to OpenAI O3 API.

        This method makes direct HTTP requests to OpenAI's O3 endpoint,
        similar to test_doctor_tools.py pattern.

        Args:
            request_data: Request data with messages, stream, user_id

        Returns:
            Streaming response or JSON response
        """
        start_time = time.time()

        try:
            logger.info("🚀 Handling O3 demo request - Direct API forwarding")

            # Validate environment
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                error_msg = "OPENAI_API_KEY not configured in environment"
                logger.error(f"❌ {error_msg}")
                return {
                    "error": error_msg,
                    "status": "error",
                    "demo_mode": "o3"
                }

            # Extract and validate messages
            messages = request_data.get('messages', [])
            if not messages:
                messages = [
                    {
                        "role": "user",
                        "content": "你好，我想了解一下如何预约医生。"
                    }
                ]

            # Validate message format
            for msg in messages:
                if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                    return {
                        "error": "Invalid message format. Each message must have 'role' and 'content'",
                        "status": "error",
                        "demo_mode": "o3"
                    }

            logger.info(f"📝 Processing {len(messages)} messages")
            logger.info(
                f"🎯 Last message: {messages[-1].get('content', '')[:100]}...")

            # Build O3 API request with Humansa system prompt
            from ..prompts.humansa_system_prompt import GENERAL_AGENTIC_POLICY
            current_date = datetime.now().strftime('%Y-%m-%d')
            system_prompt = GENERAL_AGENTIC_POLICY.format(
                current_date=current_date)

            # Convert messages to O3 format and prepend system message
            o3_messages = [
                {
                    "type": "message",
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": system_prompt
                        }
                    ]
                }
            ]

            # Add conversation messages
            for msg in messages:
                content = msg.get('content', '')
                role = msg.get('role', 'user')

                if isinstance(content, list):
                    # Handle structured content
                    content_text = ""
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'text':
                            content_text += item.get('text', '')
                        elif isinstance(item, str):
                            content_text += item
                    content = content_text

                # Use correct content type based on role
                # O3 API expects: input_text for user messages, output_text for assistant messages
                content_type = "input_text" if role == "user" else "output_text"

                o3_messages.append({
                    "type": "message",
                    "role": role,
                    "content": [
                        {
                            "type": content_type,
                            "text": str(content)
                        }
                    ]
                })

            # Prepare O3 API request
            stream = request_data.get('stream', True)
            enable_reasoning = request_data.get('enable_reasoning', False)

            o3_payload = {
                "model": "gpt-4.1",
                "stream": stream,
                "input": o3_messages,
                "tools": [
                    {"type": "web_search"}
                ],
                "max_output_tokens": 10000,
                "store": True,
                "background": False,
            }

            # Add reasoning config if enabled
            if enable_reasoning:
                o3_payload["reasoning"] = {
                    "summary": "detailed",
                    "effort": "low"
                }

            # Make request to OpenAI O3 API
            import aiohttp
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            url = "https://api.openai.com/v1/responses"

            logger.info(f"🌐 Making O3 API request to {url}")
            logger.info(f"🔧 Tools enabled: {o3_payload['tools']}")

            # Log reasoning config if present
            if 'reasoning' in o3_payload:
                logger.info(
                    f"🧠 Reasoning: summary={o3_payload['reasoning']['summary']}, effort={o3_payload['reasoning']['effort']}")
            else:
                logger.info("🧠 Reasoning: disabled (non-reasoning model)")

            logger.info(f"🌊 Streaming: {stream}")

            if stream:
                # Return streaming response
                return self._stream_o3_response(url, headers, o3_payload, start_time)
            else:
                # Return non-streaming response
                return await self._get_o3_response(url, headers, o3_payload, start_time)

        except Exception as e:
            logger.error(f"❌ O3 demo request failed: {e}")
            import traceback
            traceback.print_exc()

            processing_time = time.time() - start_time
            return {
                "error": str(e),
                "status": "error",
                "timestamp": time.time(),
                "processing_time": processing_time,
                "demo_mode": "o3"
            }

    async def _stream_o3_response(self, url: str, headers: Dict, payload: Dict, start_time: float):
        """
        Stream O3 response and convert to our comprehensive format.
        Following the comprehensive_response_streaming_handler_fixed.py pattern exactly.
        """
        import aiohttp

        # Initialize streaming state - following comprehensive streaming handler pattern
        response_id = f"resp_{uuid.uuid4().hex[:8]}"
        output_index = -1
        sequence_number = 0

        def create_event(event_type: str, **kwargs) -> Dict[str, Any]:
            nonlocal sequence_number
            event_data = {
                "type": event_type,
                "sequence_number": sequence_number,
            }
            event_data.update(kwargs)
            sequence_number += 1
            return event_data

        def generate_output_id(prefix: str = "item") -> str:
            nonlocal output_index
            output_index += 1
            return f"{prefix}_{uuid.uuid4().hex[:8]}"

        try:
            # Phase 1: Lifecycle - response.created
            event_created = create_event('response.created', response={'id': response_id, 'object': 'response', 'created_at': int(
                time.time()), 'status': 'in_progress', 'model': 'gpt-4.1-nano', 'output': []})
            yield f"data: {json.dumps(event_created)}\n\n"

            # Phase 2: response.in_progress
            event_progress = create_event('response.in_progress', response={
                                          'id': response_id, 'status': 'in_progress'})
            yield f"data: {json.dumps(event_progress)}\n\n"

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:

                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            f"❌ O3 API error: {response.status} - {error_text}")
                        yield f"data: {json.dumps(create_event('response.failed', response={'id': response_id, 'status': 'failed', 'error': error_text}))}\n\n"
                        yield "data: [DONE]\n\n"
                        return

                    logger.info(
                        f"📡 O3 streaming started - Status: {response.status}")

                    current_reasoning_item = None
                    current_message_item = None
                    event_count = 0
                    # Track which items we've seen 'added' events for
                    seen_added_items = set()

                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()

                        if not line_str:
                            continue

                        if line_str.startswith("data: "):
                            data_str = line_str[6:]  # Remove "data: "

                            if data_str == "[DONE]":
                                # Phase 6: Lifecycle - response.completed
                                yield f"data: {json.dumps(create_event('response.completed', response={'id': response_id, 'status': 'completed', 'object': 'response', 'output': []}))}\n\n"
                                yield "data: [DONE]\n\n"
                                break

                            try:
                                o3_event = json.loads(data_str)
                                event_type = o3_event.get('type', 'unknown')
                                event_count += 1

                                logger.debug(
                                    f"📡 O3 Event #{event_count}: {event_type} -> Converting to backend format")

                                # Convert O3 events to our comprehensive format - Follow the comprehensive streaming pattern
                                if event_type == "response.output_item.added":
                                    item = o3_event.get('item', {})
                                    item_type = item.get('type', 'unknown')

                                    # Track that we've seen an 'added' event for this item type
                                    seen_added_items.add(item_type)

                                    if item_type == 'reasoning':
                                        # Stream reasoning following comprehensive format
                                        reasoning_id = generate_output_id("rs")
                                        current_reasoning_item = {
                                            'id': reasoning_id,
                                            'type': 'reasoning',
                                            'output_index': output_index
                                        }

                                        # Emit response.output_item.added
                                        yield f"data: {json.dumps(create_event('response.output_item.added', output_index=output_index, item={'id': reasoning_id, 'type': 'reasoning', 'content': []}))}\n\n"
                                        logger.debug(
                                            f"🔵 Emitted output_item.added for reasoning: {reasoning_id}")

                                    elif item_type == 'message':
                                        # Stream message following comprehensive format
                                        message_id = generate_output_id("msg")
                                        current_message_item = {
                                            'id': message_id,
                                            'type': 'message',
                                            'role': 'assistant',
                                            'output_index': output_index
                                        }

                                        # Emit response.output_item.added
                                        yield f"data: {json.dumps(create_event('response.output_item.added', output_index=output_index, item={'id': message_id, 'type': 'message', 'role': 'assistant', 'status': 'in_progress'}))}\n\n"

                                        # Emit response.content_part.added
                                        yield f"data: {json.dumps(create_event('response.content_part.added', item_id=message_id, output_index=output_index, content_index=0, part={'type': 'output_text', 'annotations': [], 'logprobs': [], 'text': ''}))}\n\n"

                                        logger.debug(
                                            f"🔵 Emitted output_item.added for message: {message_id}")

                                # elif event_type == "response.output_text.delta":
                                #     # Handle real-time text streaming - This is the key missing piece!
                                #     delta_text = o3_event.get('delta', '')
                                #     item_id = o3_event.get('item_id', '')
                                #     output_index = o3_event.get('output_index', 0)
                                #     content_index = o3_event.get('content_index', 0)

                                #     if delta_text and item_id:
                                #         # Forward the delta event directly to maintain real-time streaming
                                #         yield f"data: {json.dumps(create_event('response.output_text.delta', item_id=item_id, output_index=output_index, content_index=content_index, delta=delta_text))}\n\n"
                                #         logger.debug(f"🌊 Streaming text delta: '{delta_text[:50]}...' for item {item_id}")

                                # elif event_type == "response.reasoning_summary_text.delta":
                                #     # Handle real-time reasoning summary streaming
                                #     # Convert OpenAI's reasoning_summary_text.delta to our reasoning_text.delta
                                #     delta_text = o3_event.get('delta', '')
                                #     item_id = o3_event.get('item_id', '')
                                #     output_index = o3_event.get('output_index', 0)
                                #     summary_index = o3_event.get('summary_index', 0)

                                #     if delta_text and item_id:
                                #         # Convert to our backend's expected format: reasoning_text.delta
                                #         yield f"data: {json.dumps(create_event('response.reasoning_text.delta', item_id=item_id, output_index=output_index, content_index=summary_index, delta=delta_text))}\n\n"
                                #         logger.debug(f"🧠 Streaming reasoning delta: '{delta_text[:50]}...' for item {item_id}")

                                # elif event_type == "response.reasoning_summary_part.added":
                                #     # Handle reasoning summary part added
                                #     # Convert OpenAI's reasoning_summary_part.added to our reasoning_part.added
                                #     item_id = o3_event.get('item_id', '')
                                #     output_index = o3_event.get('output_index', 0)
                                #     summary_index = o3_event.get('summary_index', 0)
                                #     part = o3_event.get('part', {})

                                #     if item_id and part:
                                #         # Convert to our backend's expected format: reasoning_part.added
                                #         yield f"data: {json.dumps(create_event('response.reasoning_part.added', item_id=item_id, output_index=output_index, content_index=summary_index, part={'type': 'reasoning_text', 'text': part.get('text', '')}))}\n\n"
                                #         logger.debug(f"🧠 Reasoning part added for item {item_id}")

                                # elif event_type == "response.reasoning_summary_part.done":
                                #     # Handle reasoning summary part done
                                #     # Convert OpenAI's reasoning_summary_part.done to our reasoning_part.done
                                #     item_id = o3_event.get('item_id', '')
                                #     output_index = o3_event.get('output_index', 0)
                                #     summary_index = o3_event.get('summary_index', 0)
                                #     part = o3_event.get('part', {})

                                #     if item_id and part:
                                #         # Convert to our backend's expected format: reasoning_part.done
                                #         yield f"data: {json.dumps(create_event('response.reasoning_part.done', item_id=item_id, output_index=output_index, content_index=summary_index, part={'type': 'reasoning_text', 'text': part.get('text', '')}))}\n\n"
                                #         logger.debug(f"🧠 Reasoning part done for item {item_id}")

                                # elif event_type == "response.reasoning_summary_text.done":
                                #     # Handle reasoning summary text done
                                #     # Convert OpenAI's reasoning_summary_text.done to our reasoning_text.done
                                #     item_id = o3_event.get('item_id', '')
                                #     output_index = o3_event.get('output_index', 0)
                                #     summary_index = o3_event.get('summary_index', 0)
                                #     text = o3_event.get('text', '')

                                #     if item_id and text:
                                #         # Convert to our backend's expected format: reasoning_text.done
                                #         yield f"data: {json.dumps(create_event('response.reasoning_text.done', item_id=item_id, output_index=output_index, content_index=summary_index, text=text))}\n\n"
                                #         logger.debug(f"🧠 Reasoning text done for item {item_id}")

                                # elif event_type == "response.output_text.done":
                                #     # Handle output text done
                                #     item_id = o3_event.get('item_id', '')
                                #     output_index = o3_event.get('output_index', 0)
                                #     content_index = o3_event.get('content_index', 0)
                                #     text = o3_event.get('text', '')

                                #     if item_id and text:
                                #         # Forward output_text.done directly (no conversion needed)
                                #         yield f"data: {json.dumps(create_event('response.output_text.done', item_id=item_id, output_index=output_index, content_index=content_index, text=text))}\n\n"
                                #         logger.debug(f"💬 Output text done for item {item_id}")

                                # elif event_type == "response.content_part.added":
                                #     # Handle content part added
                                #     item_id = o3_event.get('item_id', '')
                                #     output_index = o3_event.get('output_index', 0)
                                #     content_index = o3_event.get('content_index', 0)
                                #     part = o3_event.get('part', {})

                                #     if item_id and part:
                                #         # Forward content_part.added directly (no conversion needed)
                                #         yield f"data: {json.dumps(create_event('response.content_part.added', item_id=item_id, output_index=output_index, content_index=content_index, part=part))}\n\n"
                                #         logger.debug(f"📄 Content part added for item {item_id}")

                                # elif event_type == "response.content_part.done":
                                #     # Handle content part done
                                #     item_id = o3_event.get('item_id', '')
                                #     output_index = o3_event.get('output_index', 0)
                                #     content_index = o3_event.get('content_index', 0)
                                #     part = o3_event.get('part', {})

                                #     if item_id and part:
                                #         # Forward content_part.done directly (no conversion needed)
                                #         yield f"data: {json.dumps(create_event('response.content_part.done', item_id=item_id, output_index=output_index, content_index=content_index, part=part))}\n\n"
                                #         logger.debug(f"📄 Content part done for item {item_id}")

                                elif event_type == "response.output_item.done":
                                    # Process completed items with comprehensive format
                                    item = o3_event.get('item', {})
                                    item_type = item.get('type', 'unknown')

                                    logger.debug(
                                        f"🔍 Processing output_item.done for {item_type}, seen_added_items: {seen_added_items}")

                                    # 🔧 FIX: If we haven't seen an 'added' event for this item type, emit it now
                                    if item_type not in seen_added_items:
                                        logger.debug(
                                            f"🔧 Item type {item_type} not in seen_added_items, emitting missing added event")

                                        if item_type == 'message':
                                            # Emit missing output_item.added for message
                                            message_id = generate_output_id(
                                                "msg")
                                            current_message_item = {
                                                'id': message_id,
                                                'type': 'message',
                                                'role': 'assistant',
                                                'output_index': output_index
                                            }
                                            yield f"data: {json.dumps(create_event('response.output_item.added', output_index=output_index, item={'id': message_id, 'type': 'message', 'role': 'assistant', 'status': 'in_progress'}))}\n\n"

                                            # Emit response.content_part.added
                                            yield f"data: {json.dumps(create_event('response.content_part.added', item_id=message_id, output_index=output_index, content_index=0, part={'type': 'output_text', 'annotations': [], 'logprobs': [], 'text': ''}))}\n\n"

                                            logger.debug(
                                                f"🔵 Emitted missing output_item.added for message: {message_id}")
                                            seen_added_items.add(item_type)

                                        elif item_type == 'reasoning':
                                            # Emit missing output_item.added for reasoning
                                            reasoning_id = generate_output_id(
                                                "rs")
                                            current_reasoning_item = {
                                                'id': reasoning_id,
                                                'type': 'reasoning',
                                                'output_index': output_index
                                            }
                                            yield f"data: {json.dumps(create_event('response.output_item.added', output_index=output_index, item={'id': reasoning_id, 'type': 'reasoning', 'content': []}))}\n\n"
                                            logger.debug(
                                                f"🔵 Emitted missing output_item.added for reasoning: {reasoning_id}")
                                            seen_added_items.add(item_type)

                                    if item_type == 'reasoning':
                                        # Extract reasoning content from O3 format
                                        summary = item.get('summary', [])
                                        reasoning_text = ""

                                        if isinstance(summary, list) and summary:
                                            for summary_part in summary:
                                                if isinstance(summary_part, dict) and summary_part.get('type') == 'summary_text':
                                                    reasoning_text += summary_part.get(
                                                        'text', '')

                                        reasoning_id = current_reasoning_item['id'] if current_reasoning_item else generate_output_id(
                                            "rs")
                                        current_output_index = current_reasoning_item[
                                            'output_index'] if current_reasoning_item else output_index

                                        # Stream reasoning following comprehensive format
                                        # Add reasoning text part
                                        yield f"data: {json.dumps(create_event('response.reasoning_part.added', item_id=reasoning_id, output_index=current_output_index, content_index=0, part={'type': 'reasoning_text', 'text': ''}))}\n\n"

                                        # Stream reasoning text delta
                                        yield f"data: {json.dumps(create_event('response.reasoning_text.delta', item_id=reasoning_id, output_index=current_output_index, content_index=0, delta=reasoning_text))}\n\n"

                                        # Complete reasoning text
                                        yield f"data: {json.dumps(create_event('response.reasoning_text.done', item_id=reasoning_id, output_index=current_output_index, content_index=0, text=reasoning_text))}\n\n"

                                        # Complete reasoning part
                                        yield f"data: {json.dumps(create_event('response.reasoning_part.done', item_id=reasoning_id, output_index=current_output_index, content_index=0, part={'type': 'reasoning_text', 'text': reasoning_text}))}\n\n"

                                        # Complete reasoning output item
                                        final_reasoning_item = {
                                            "id": reasoning_id,
                                            "type": "reasoning",
                                            "content": [
                                                {
                                                    "type": "reasoning_text",
                                                    "text": reasoning_text
                                                }
                                            ]
                                        }

                                        yield f"data: {json.dumps(create_event('response.output_item.done', output_index=current_output_index, item=final_reasoning_item))}\n\n"
                                        logger.info(
                                            f"✅ Emitted comprehensive reasoning events for: {reasoning_id}")

                                    elif item_type == 'message':
                                        # Extract message content from O3 format
                                        content = item.get('content', [])
                                        message_text = ""

                                        if isinstance(content, list) and content:
                                            for content_part in content:
                                                if isinstance(content_part, dict) and content_part.get('type') == 'output_text':
                                                    message_text += content_part.get(
                                                        'text', '')

                                        message_id = current_message_item['id'] if current_message_item else generate_output_id(
                                            "msg")
                                        current_output_index = current_message_item[
                                            'output_index'] if current_message_item else output_index

                                        # Stream message following comprehensive format
                                        # Stream output text delta
                                        yield f"data: {json.dumps(create_event('response.output_text.delta', item_id=message_id, output_index=current_output_index, content_index=0, delta=message_text))}\n\n"

                                        # Complete output text
                                        yield f"data: {json.dumps(create_event('response.output_text.done', item_id=message_id, output_index=current_output_index, content_index=0, text=message_text))}\n\n"

                                        # Complete content part
                                        yield f"data: {json.dumps(create_event('response.content_part.done', item_id=message_id, output_index=current_output_index, content_index=0, part={'type': 'output_text', 'annotations': [], 'logprobs': [], 'text': message_text}))}\n\n"

                                        # Complete message output item
                                        final_message_item = {
                                            "id": message_id,
                                            "type": "message",
                                            "role": "assistant",
                                            "status": "completed",
                                            "content": [
                                                {
                                                    "type": "output_text",
                                                    "text": message_text,
                                                    "annotations": []
                                                }
                                            ]
                                        }

                                        yield f"data: {json.dumps(create_event('response.output_item.done', output_index=current_output_index, item=final_message_item))}\n\n"
                                        logger.info(
                                            f"✅ Emitted comprehensive message events for: {message_id}")

                                # Skip all other intermediate events (deltas, etc.) - we only care about completions

                            except json.JSONDecodeError:
                                # Skip invalid JSON
                                continue

                    current_time = time.time() - start_time
                    logger.info(
                        f"✅ O3 streaming converted to comprehensive format - {event_count} events processed in {current_time:.2f}s")

                    # Phase 6: Lifecycle - response.completed (if not already sent)
                    yield f"data: {json.dumps(create_event('response.completed', response={'id': response_id, 'status': 'completed', 'object': 'response', 'output': []}))}\n\n"
                    yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"❌ O3 streaming failed: {e}")
            yield f"data: {json.dumps(create_event('response.failed', response={'id': response_id, 'status': 'failed', 'error': str(e)}))}\n\n"
            yield "data: [DONE]\n\n"

    async def _get_o3_response(self, url: str, headers: Dict, payload: Dict, start_time: float) -> Dict:
        """Handle non-streaming O3 request."""
        import aiohttp

        try:
            # Remove stream parameter for non-streaming
            non_stream_payload = {**payload, "stream": False}

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=non_stream_payload) as response:

                    processing_time = time.time() - start_time

                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            f"❌ O3 API error: {response.status} - {error_text}")
                        return {
                            "error": error_text,
                            "status": response.status,
                            "demo_mode": "o3",
                            "processing_time": processing_time
                        }

                    # Get O3 response
                    o3_response = await response.json()

                    logger.info(
                        f"✅ O3 non-streaming completed in {processing_time:.2f}s")

                    # Wrap O3 response with our metadata
                    return {
                        "demo_mode": "o3",
                        "processing_time": processing_time,
                        "timestamp": time.time(),
                        "o3_response": o3_response,
                        "status": "success"
                    }

        except Exception as e:
            logger.error(f"❌ O3 non-streaming request failed: {e}")
            processing_time = time.time() - start_time
            return {
                "error": str(e),
                "status": "error",
                "demo_mode": "o3",
                "processing_time": processing_time,
                "timestamp": time.time()
            }


# Create global instance for easy import
o3_demo_endpoint = O3DemoEndpoint()


async def handle_o3_demo_request(request_data: Dict[str, Any]):
    """
    Global function to handle O3 demo requests.

    This can be imported and used directly in Flask/FastAPI route handlers.
    """
    return await o3_demo_endpoint.handle_demo_request(request_data)


def create_demo_test_payload() -> Dict[str, Any]:
    """
    Create a test payload for O3 demo.

    Returns:
        Dict with sample request data for testing
    """
    return {
        "messages": [
            {
                "role": "user",
                "content": "帮我预约深圳的心脏科医生，我希望下周看诊。"
            }
        ],
        "stream": True,
        "user_id": "demo_user_12345",
        "enable_rag": False,
        "enable_web_search": True
    }


if __name__ == "__main__":
    """
    Quick test script for O3 demo endpoint.
    """
    import asyncio

    async def test_o3_demo():
        """Test the O3 demo endpoint."""
        print("🧪 Testing O3 Demo Endpoint")

        # Create test request
        test_request = create_demo_test_payload()
        print(f"📝 Test request: {test_request}")

        # Run the demo
        try:
            result = await handle_o3_demo_request(test_request)

            if hasattr(result, '__aiter__'):
                # Streaming response
                print("🌊 Streaming response:")
                event_count = 0
                async for event in result:
                    event_count += 1
                    print(f"Event #{event_count}: {str(event)[:100]}...")

                    # Stop after 20 events for testing
                    if event_count >= 20:
                        print("🛑 Stopping after 20 events for test")
                        break

                print(f"✅ Streaming test completed - {event_count} events")
            else:
                # Non-streaming response
                print(f"📄 Non-streaming response: {result}")

        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()

    # Run test
    asyncio.run(test_o3_demo())
