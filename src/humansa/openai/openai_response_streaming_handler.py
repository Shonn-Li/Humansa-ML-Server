"""
OpenAI Response Streaming Handler for Humansa Agentic Agent

Uses OpenAI Responses API with LlamaIndex to provide streaming functionality
as an alternative to the comprehensive manual streaming handler.
Leverages OpenAI's built-in streaming capabilities for proper event handling.
"""

import json
import logging
import time
import uuid
import os
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

from llama_index.llms.openai import OpenAIResponses
from llama_index.core.llms import ChatMessage
from llama_index.core.tools import FunctionTool
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class OpenAIResponseStreamingHandler:
    """
    OpenAI-based streaming handler using LlamaIndex OpenAI Responses API.

    Provides streaming functionality using OpenAI's native streaming capabilities
    with proper tool calling and reasoning support. Uses standard OpenAI API only.

    Requires:
    - OPENAI_API_KEY: OpenAI API key
    """

    def __init__(self, model: str = "gpt-4o-mini", system_prompt: str = None, use_azure: bool = False):
        self.model = model
        self.system_prompt = system_prompt or "You are a helpful AI assistant."
        self.response_id = f"resp_{uuid.uuid4().hex[:8]}"
        self.sequence_number = 0
        self.use_azure = use_azure

        # Initialize OpenAI LLM - only supports standard OpenAI for Responses API
        self.llm = self._create_openai_llm()
        logger.info(f"🔥 Using standard OpenAI with model: {self.model}")

    def _create_openai_llm(self) -> OpenAIResponses:
        """Create standard OpenAI Responses LLM instance"""
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        return OpenAIResponses(
            model=self.model,
            api_key=api_key,
            temperature=0.7,
            max_output_tokens=4096,
            # Enable built-in tool calling if needed
            built_in_tools=[{"type": "web_search_preview"}
                            ] if "web_search" in self.system_prompt.lower() else []
        )

    def create_event(self, event_type: str, **kwargs) -> Dict[str, Any]:
        """Create a structured SSE event matching the canonical format."""
        event_data = {
            "type": event_type,
            "sequence_number": self.sequence_number,
        }
        event_data.update(kwargs)
        self.sequence_number += 1
        return event_data

    async def stream_openai_response(self,
                                     user_message: str,
                                     tools: List[FunctionTool] = None,
                                     conversation_history: List[ChatMessage] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream response using OpenAI Responses API.

        Args:
            user_message: User's input message
            tools: List of LlamaIndex FunctionTool objects for tool calling
            conversation_history: Previous conversation messages

        Yields:
            Streaming events following the canonical format
        """
        try:
            # Phase 1: Lifecycle - response.created
            yield self.create_event("response.created",
                                    response={
                                        "id": self.response_id,
                                        "object": "response",
                                        "created_at": int(time.time()),
                                        "status": "in_progress",
                                        "model": self.model,
                                        "output": [],
                                    })

            # Phase 2: response.in_progress
            yield self.create_event("response.in_progress",
                                    response={
                                        "id": self.response_id,
                                        "status": "in_progress",
                                    })

            # Prepare messages
            messages = []

            # Add system prompt
            if self.system_prompt:
                messages.append(ChatMessage(
                    role="system", content=self.system_prompt))

            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)

            # Add current user message
            messages.append(ChatMessage(role="user", content=user_message))

            logger.info(
                f"🔄 Starting OpenAI streaming with {len(messages)} messages")

            # Check if we need tool calling
            if tools:
                logger.info(
                    f"🛠️ Using {len(tools)} tools for function calling")
                async for event in self._stream_with_tools(messages, tools):
                    yield event
            else:
                logger.info("💬 Streaming simple chat response")
                async for event in self._stream_simple_chat(messages):
                    yield event

            # Phase 6: Lifecycle - response.completed
            yield self.create_event("response.completed",
                                    response={
                                        "id": self.response_id,
                                        "status": "completed",
                                        "object": "response",
                                        "output": [],
                                    })

            logger.info(f"✅ OpenAI streaming completed successfully")

        except Exception as e:
            logger.error(f"❌ OpenAI streaming failed: {e}")
            import traceback
            traceback.print_exc()

            # Phase 6 (error): Lifecycle - response.failed
            yield self.create_event("response.failed",
                                    response={
                                        "id": self.response_id,
                                        "status": "failed",
                                        "error": str(e)
                                    })

    async def _stream_simple_chat(self, messages: List[ChatMessage]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream simple chat response without tools."""
        message_id = f"msg_{uuid.uuid4().hex[:8]}"

        # Add assistant message output item
        yield self.create_event("response.output_item.added",
                                output_index=0,
                                item={
                                    "id": message_id,
                                    "type": "message",
                                    "role": "assistant",
                                    "status": "in_progress",
                                })

        # Add content part
        yield self.create_event("response.content_part.added",
                                item_id=message_id,
                                output_index=0,
                                content_index=0,
                                part={
                                    "type": "output_text",
                                    "annotations": [],
                                    "logprobs": [],
                                    "text": "",
                                })

        # Stream the response
        full_response = ""
        response_stream = self.llm.stream_chat(messages)

        for chunk in response_stream:
            if chunk.delta:
                full_response += chunk.delta

                # Stream delta
                yield self.create_event("response.output_text.delta",
                                        item_id=message_id,
                                        output_index=0,
                                        content_index=0,
                                        delta=chunk.delta)

        # Complete output text with final text
        yield self.create_event("response.output_text.done",
                                item_id=message_id,
                                output_index=0,
                                content_index=0,
                                text=full_response)

        # Complete content part
        yield self.create_event("response.content_part.done",
                                item_id=message_id,
                                output_index=0,
                                content_index=0,
                                part={
                                    "type": "output_text",
                                    "annotations": [],
                                    "logprobs": [],
                                    "text": full_response,
                                })

        # Complete message output item
        yield self.create_event("response.output_item.done",
                                output_index=0,
                                item={
                                    "id": message_id,
                                    "type": "message",
                                    "role": "assistant",
                                    "status": "completed",
                                    "content": [
                                        {
                                            "type": "output_text",
                                            "text": full_response,
                                            "annotations": [],
                                        }
                                    ],
                                })

    async def _stream_with_tools(self, messages: List[ChatMessage], tools: List[FunctionTool]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream response with tool calling capability."""
        chat_history = messages.copy()
        output_index = -1

        # Create tools by name mapping
        tools_by_name = {t.metadata.name: t for t in tools}

        # Get initial response with potential tool calls
        resp = self.llm.chat_with_tools(tools, chat_history=chat_history)

        # Check for tool calls
        tool_calls = self.llm.get_tool_calls_from_response(
            resp, error_on_no_tool_call=False)

        while tool_calls:
            output_index += 1

            # Add the LLM's response to chat history
            chat_history.append(resp.message)

            # Process each tool call
            for tool_call in tool_calls:
                tool_name = tool_call.tool_name
                tool_kwargs = tool_call.tool_kwargs

                logger.info(f"🔧 Calling {tool_name} with {tool_kwargs}")

                # Stream function call item
                call_id = f"fc_{uuid.uuid4().hex[:8]}"

                yield self.create_event("response.output_item.added",
                                        output_index=output_index,
                                        item={
                                            "id": call_id,
                                            "type": "function_tool_call",
                                            "status": "in_progress",
                                            "name": tool_name,
                                            "arguments": json.dumps(tool_kwargs)
                                        })

                # Execute tool
                try:
                    tool = tools_by_name[tool_name]
                    tool_output = tool(**tool_kwargs)

                    # Complete function call
                    yield self.create_event("response.output_item.done",
                                            output_index=output_index,
                                            item={
                                                "id": call_id,
                                                "type": "function_tool_call",
                                                "status": "completed",
                                                "name": tool_name,
                                                "arguments": json.dumps(tool_kwargs),
                                                "output": None
                                            })

                    # Stream function result
                    output_index += 1
                    result_id = f"fr_{uuid.uuid4().hex[:8]}"
                    result_text = str(tool_output)

                    yield self.create_event("response.output_item.added",
                                            output_index=output_index,
                                            item={
                                                "id": result_id,
                                                "type": "function_tool_result",
                                                "status": "in_progress",
                                                "role": "tool"
                                            })

                    yield self.create_event("response.function_tool_result.delta",
                                            item_id=result_id,
                                            delta=result_text)

                    yield self.create_event("response.function_tool_result.done",
                                            item_id=result_id)

                    yield self.create_event("response.output_item.done",
                                            output_index=output_index,
                                            item={
                                                "id": result_id,
                                                "type": "function_tool_result",
                                                "status": "completed",
                                                "role": "tool",
                                                "content": [
                                                    {
                                                        "type": "output_text",
                                                        "text": result_text
                                                    }
                                                ]
                                            })

                    # Add tool result to chat history
                    chat_history.append(
                        ChatMessage(
                            role="tool",
                            content=result_text,
                            additional_kwargs={"call_id": tool_call.tool_id},
                        )
                    )

                except Exception as e:
                    logger.error(f"❌ Tool {tool_name} failed: {e}")
                    error_msg = f"Error executing {tool_name}: {str(e)}"
                    chat_history.append(
                        ChatMessage(
                            role="tool",
                            content=error_msg,
                            additional_kwargs={"call_id": tool_call.tool_id},
                        )
                    )

            # Get next response from LLM
            resp = self.llm.chat_with_tools(tools, chat_history=chat_history)
            tool_calls = self.llm.get_tool_calls_from_response(
                resp, error_on_no_tool_call=False)

        # Stream final assistant response
        if resp.message.content:
            output_index += 1
            message_id = f"msg_{uuid.uuid4().hex[:8]}"

            yield self.create_event("response.output_item.added",
                                    output_index=output_index,
                                    item={
                                        "id": message_id,
                                        "type": "message",
                                        "role": "assistant",
                                        "status": "in_progress",
                                    })

            yield self.create_event("response.content_part.added",
                                    item_id=message_id,
                                    output_index=output_index,
                                    content_index=0,
                                    part={
                                        "type": "output_text",
                                        "annotations": [],
                                        "logprobs": [],
                                        "text": "",
                                    })

            yield self.create_event("response.output_text.delta",
                                    item_id=message_id,
                                    output_index=output_index,
                                    content_index=0,
                                    delta=resp.message.content)

            yield self.create_event("response.output_text.done",
                                    item_id=message_id,
                                    output_index=output_index,
                                    content_index=0,
                                    text=resp.message.content)

            yield self.create_event("response.content_part.done",
                                    item_id=message_id,
                                    output_index=output_index,
                                    content_index=0,
                                    part={
                                        "type": "output_text",
                                        "annotations": [],
                                        "logprobs": [],
                                        "text": resp.message.content,
                                    })

            yield self.create_event("response.output_item.done",
                                    output_index=output_index,
                                    item={
                                        "id": message_id,
                                        "type": "message",
                                        "role": "assistant",
                                        "status": "completed",
                                        "content": [
                                            {
                                                "type": "output_text",
                                                "text": resp.message.content,
                                                "annotations": [],
                                            }
                                        ],
                                    })


async def stream_openai_response(user_message: str,
                                 system_prompt: str = None,
                                 tools: List[FunctionTool] = None,
                                 conversation_history: List[ChatMessage] = None,
                                 model: str = "gpt-4o-mini",
                                 use_azure: bool = True) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Convenience function to stream OpenAI response using Azure or standard OpenAI.

    Args:
        user_message: User's input message
        system_prompt: System prompt to include as additional instructions
        tools: List of LlamaIndex FunctionTool objects for tool calling
        conversation_history: Previous conversation messages
        model: OpenAI model to use
        use_azure: Whether to use Azure OpenAI (default: True)

    Yields:
        Streaming events following the canonical format
    """
    handler = OpenAIResponseStreamingHandler(
        model=model, system_prompt=system_prompt, use_azure=use_azure)
    async for event in handler.stream_openai_response(user_message, tools, conversation_history):
        yield event
