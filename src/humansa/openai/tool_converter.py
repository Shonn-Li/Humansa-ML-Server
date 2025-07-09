"""
Tool conversion utilities for OpenAI integration.

Converts between Humansa tool formats and LlamaIndex FunctionTool format.
"""

import json
import logging
from typing import Dict, Any, List, Callable
from pydantic import BaseModel
from llama_index.core.tools import FunctionTool

logger = logging.getLogger(__name__)


def convert_humansa_tools_to_llamaindex(humansa_tools: List[Dict[str, Any]]) -> List[FunctionTool]:
    """
    Convert Humansa tool definitions to LlamaIndex FunctionTool objects.

    Args:
        humansa_tools: List of tool definitions from Humansa agent

    Returns:
        List of LlamaIndex FunctionTool objects
    """
    llamaindex_tools = []

    for tool in humansa_tools:
        try:
            tool_name = tool.get('name', 'unknown_tool')
            tool_description = tool.get('description', f'Tool: {tool_name}')
            tool_function = tool.get('function')
            tool_parameters = tool.get('parameters', {})

            if not tool_function:
                logger.warning(
                    f"⚠️ Tool {tool_name} has no function, skipping")
                continue

            # Create a wrapper function that handles the tool execution
            def create_tool_wrapper(func, name):
                def wrapper(**kwargs):
                    try:
                        return func(**kwargs)
                    except Exception as e:
                        logger.error(f"❌ Error executing tool {name}: {e}")
                        return f"Error: {str(e)}"
                return wrapper

            wrapped_function = create_tool_wrapper(tool_function, tool_name)

            # Create LlamaIndex FunctionTool
            llamaindex_tool = FunctionTool.from_defaults(
                fn=wrapped_function,
                name=tool_name,
                description=tool_description
            )

            llamaindex_tools.append(llamaindex_tool)
            logger.info(f"✅ Converted tool: {tool_name}")

        except Exception as e:
            logger.error(
                f"❌ Error converting tool {tool.get('name', 'unknown')}: {e}")
            continue

    logger.info(f"🔧 Converted {len(llamaindex_tools)} tools for LlamaIndex")
    return llamaindex_tools


def convert_doctor_tools_to_llamaindex() -> List[FunctionTool]:
    """
    Convert the standard Humansa doctor tools to LlamaIndex format.

    Returns:
        List of LlamaIndex FunctionTool objects for doctor tools
    """
    tools = []

    try:
        from humansa.tools.doctor_tools import get_medical_symptoms, search_medical_conditions, get_treatment_options

        # Medical symptoms tool
        symptoms_tool = FunctionTool.from_defaults(
            fn=get_medical_symptoms,
            name="get_medical_symptoms",
            description="Get comprehensive information about medical symptoms including descriptions, severity, and related conditions"
        )
        tools.append(symptoms_tool)

        # Medical conditions search tool
        conditions_tool = FunctionTool.from_defaults(
            fn=search_medical_conditions,
            name="search_medical_conditions",
            description="Search for medical conditions based on symptoms, keywords, or condition names"
        )
        tools.append(conditions_tool)

        # Treatment options tool
        treatment_tool = FunctionTool.from_defaults(
            fn=get_treatment_options,
            name="get_treatment_options",
            description="Get treatment options and recommendations for specific medical conditions"
        )
        tools.append(treatment_tool)

        logger.info(f"🏥 Created {len(tools)} doctor tools for LlamaIndex")

    except ImportError as e:
        logger.warning(f"⚠️ Doctor tools not available: {e}")
        # Create placeholder tools if the actual tools aren't available
        placeholder_tool = FunctionTool.from_defaults(
            fn=lambda query: f"Doctor tool placeholder for: {query}",
            name="placeholder_medical_tool",
            description="Placeholder medical tool - actual tools not available"
        )
        tools.append(placeholder_tool)

    return tools


def create_simple_search_tool() -> FunctionTool:
    """
    Create a simple web search tool for OpenAI integration.

    Returns:
        LlamaIndex FunctionTool for web search
    """
    def web_search(query: str) -> str:
        """
        Perform a web search for the given query.

        Args:
            query: Search query string

        Returns:
            Search results as formatted string
        """
        try:
            # This would integrate with actual search API
            # For now, return a placeholder response
            return f"Search results for '{query}': [This is a placeholder - integrate with actual search API]"
        except Exception as e:
            return f"Search error: {str(e)}"

    search_tool = FunctionTool.from_defaults(
        fn=web_search,
        name="web_search",
        description="Search the web for information on any topic"
    )

    return search_tool


class ToolExecutionResult(BaseModel):
    """Result of tool execution for structured responses."""
    tool_name: str
    success: bool
    result: Any
    error: str = None


def execute_tool_safely(tool: FunctionTool, **kwargs) -> ToolExecutionResult:
    """
    Execute a tool safely with error handling.

    Args:
        tool: LlamaIndex FunctionTool to execute
        **kwargs: Arguments to pass to the tool

    Returns:
        ToolExecutionResult with success status and result/error
    """
    try:
        result = tool(**kwargs)
        return ToolExecutionResult(
            tool_name=tool.metadata.name,
            success=True,
            result=result
        )
    except Exception as e:
        logger.error(f"❌ Tool {tool.metadata.name} execution failed: {e}")
        return ToolExecutionResult(
            tool_name=tool.metadata.name,
            success=False,
            result=None,
            error=str(e)
        )
