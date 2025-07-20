"""
Code Interpreter Agent for YouWoAI Multi-Agent System

This agent provides Python code execution capabilities similar to OpenAI's Code Interpreter.
It can execute Python code, generate plots, handle data analysis, and return results.
"""

import ast
import io
import json
import logging
import os
import subprocess
import sys
import tempfile
import traceback
import uuid
from typing import Dict, Any, List, Optional, AsyncGenerator
import asyncio
from contextlib import redirect_stdout, redirect_stderr

# Define base agent locally to avoid circular imports
from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator

class BaseAgent(ABC):
    """Enhanced base class for streaming-capable agents"""
    
    def __init__(self):
        super().__init__()
        self.supports_streaming = False
    
    @abstractmethod
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main logic (non-streaming)."""
        pass
    
    async def stream(self, request: Dict[str, Any], context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the agent's logic with streaming support."""
        # Default implementation: yield the full result at once
        result = await self.run(request, context)
        yield result

logger = logging.getLogger(__name__)


class PythonCodeExecutor:
    """Secure Python code executor with sandboxing capabilities"""
    
    def __init__(self):
        self.allowed_modules = {
            # Standard library
            'math', 'statistics', 'random', 'datetime', 'json', 'csv', 'sqlite3',
            'collections', 'itertools', 'functools', 're', 'urllib', 'base64',
            
            # Data science
            'numpy', 'pandas', 'matplotlib', 'seaborn', 'plotly', 'scipy',
            'sklearn', 'statsmodels', 'sympy',
            
            # Visualization
            'matplotlib.pyplot', 'matplotlib.patches', 'matplotlib.colors',
            'seaborn', 'plotly.graph_objects', 'plotly.express',
            
            # File handling
            'io', 'pathlib', 'tempfile', 'zipfile', 'tarfile',
        }
        
        self.restricted_functions = {
            'exec', 'eval', 'compile', 'open', '__import__', 'globals', 'locals',
            'input', 'raw_input', 'reload', 'exit', 'quit', 'help'
        }
        
        self.max_execution_time = 30  # seconds
        self.max_output_length = 10000  # characters
    
    def validate_code(self, code: str) -> tuple[bool, str]:
        """Validate Python code for security and syntax"""
        try:
            # Parse the code to check syntax
            tree = ast.parse(code)
            
            # Check for restricted patterns
            for node in ast.walk(tree):
                # Check for restricted function calls
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in self.restricted_functions:
                            return False, f"Restricted function: {node.func.id}"
                
                # Check for import statements
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name not in self.allowed_modules:
                            return False, f"Module not allowed: {alias.name}"
                
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if module and not any(module.startswith(allowed) for allowed in self.allowed_modules):
                        return False, f"Module not allowed: {module}"
                
                # Check for file operations
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id == 'open':
                        return False, "Direct file operations not allowed"
            
            return True, "Code validation passed"
            
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"
    
    async def execute_code(self, code: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute Python code safely and return results"""
        timeout = timeout or self.max_execution_time
        
        # Validate code first
        is_valid, message = self.validate_code(code)
        if not is_valid:
            return {
                "success": False,
                "error": f"Code validation failed: {message}",
                "output": "",
                "execution_time": 0
            }
        
        # Create isolated execution environment
        execution_globals = {
            '__builtins__': {
                'print': print,
                'len': len,
                'range': range,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'abs': abs,
                'sum': sum,
                'max': max,
                'min': min,
                'sorted': sorted,
                'reversed': reversed,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'round': round,
                'type': type,
                'isinstance': isinstance,
                'hasattr': hasattr,
                'getattr': getattr,
                'setattr': setattr,
                '__import__': __import__,  # Allow import statements
            }
        }
        
        # Import allowed modules
        # Always include standard library modules
        import json
        import math
        import statistics
        import datetime
        import random
        import collections
        import itertools
        import functools
        import re
        
        execution_globals.update({
            'json': json,
            'math': math,
            'statistics': statistics,
            'datetime': datetime,
            'random': random,
            'collections': collections,
            'itertools': itertools,
            'functools': functools,
            're': re,
        })
        
        # Try to import scientific libraries if available
        try:
            import numpy as np
            execution_globals['np'] = np
            execution_globals['numpy'] = np
        except ImportError:
            pass
            
        try:
            import pandas as pd
            execution_globals['pd'] = pd
            execution_globals['pandas'] = pd
        except ImportError:
            pass
            
        try:
            import matplotlib.pyplot as plt
            execution_globals['plt'] = plt
            execution_globals['matplotlib'] = plt.matplotlib
        except ImportError:
            pass
        
        # Capture output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            import time
            start_time = time.time()
            
            # Execute code with output capture
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Handle import statements in the code
                # This allows code like "import math\nprint(math.sqrt(144))"
                exec(compile(code, '<string>', 'exec'), execution_globals, execution_globals)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()
            
            # Combine outputs
            output = stdout_output
            if stderr_output:
                output += f"\nSTDERR:\n{stderr_output}"
            
            # Truncate if too long
            if len(output) > self.max_output_length:
                output = output[:self.max_output_length] + "\n... (output truncated)"
            
            # Check if there was any output
            success = len(stdout_output.strip()) > 0 or (len(stderr_output.strip()) == 0)
            
            return {
                "success": success,
                "output": output if output else "Code executed successfully but produced no output.",
                "error": stderr_output if stderr_output else None,
                "execution_time": execution_time
            }
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time if 'start_time' in locals() else 0
            
            error_output = stderr_capture.getvalue()
            if not error_output:
                error_output = str(e)
            
            return {
                "success": False,
                "output": stdout_capture.getvalue(),
                "error": error_output,
                "execution_time": execution_time,
                "traceback": traceback.format_exc()
            }
    
    def generate_plot_code(self, plot_type: str, data_description: str) -> str:
        """Generate sample plotting code based on request"""
        if plot_type.lower() in ['line', 'lineplot']:
            return f"""
import matplotlib.pyplot as plt
import numpy as np

# Generate sample data for {data_description}
x = np.linspace(0, 10, 100)
y = np.sin(x) + np.random.normal(0, 0.1, 100)

plt.figure(figsize=(10, 6))
plt.plot(x, y, label='{data_description}')
plt.xlabel('X axis')
plt.ylabel('Y axis')
plt.title('Line Plot: {data_description}')
plt.legend()
plt.grid(True)
plt.show()
print(f"Generated line plot for: {data_description}")
"""
        elif plot_type.lower() in ['bar', 'barplot']:
            return f"""
import matplotlib.pyplot as plt
import numpy as np

# Generate sample data for {data_description}
categories = ['A', 'B', 'C', 'D', 'E']
values = np.random.randint(10, 100, len(categories))

plt.figure(figsize=(10, 6))
plt.bar(categories, values)
plt.xlabel('Categories')
plt.ylabel('Values')
plt.title('Bar Plot: {data_description}')
plt.show()
print(f"Generated bar plot for: {data_description}")
"""
        else:
            return f"""
import matplotlib.pyplot as plt
import numpy as np

# Generate sample data for {data_description}
data = np.random.normal(0, 1, 1000)

plt.figure(figsize=(10, 6))
plt.hist(data, bins=30, alpha=0.7)
plt.xlabel('Values')
plt.ylabel('Frequency')
plt.title('Histogram: {data_description}')
plt.show()
print(f"Generated histogram for: {data_description}")
"""


class CodeInterpreterAgent(BaseAgent):
    """Agent for executing Python code and data analysis tasks"""
    
    def __init__(self):
        super().__init__()
        self.supports_streaming = True
        self.executor = PythonCodeExecutor()
        self.code_patterns = {
            'plot': ['plot', 'chart', 'graph', 'visualize', 'visualization'],
            'data_analysis': ['analyze', 'statistics', 'calculate', 'compute'],
            'math': ['solve', 'equation', 'formula', 'mathematical'],
            'file_processing': ['process', 'parse', 'extract', 'transform']
        }
    
    def extract_code_from_message(self, message: str) -> List[str]:
        """Extract Python code blocks from user message"""
        code_blocks = []
        
        # Look for markdown code blocks
        import re
        pattern = r'```python\s*(.*?)\s*```'
        matches = re.findall(pattern, message, re.DOTALL)
        code_blocks.extend(matches)
        
        # Look for inline code
        pattern = r'`([^`]+)`'
        inline_matches = re.findall(pattern, message)
        for match in inline_matches:
            if any(keyword in match.lower() for keyword in ['print', 'import', '=', 'def', 'for', 'if']):
                code_blocks.append(match)
        
        # If no code blocks found, check if the entire message is valid Python code
        if not code_blocks:
            # Check if the message contains Python-like statements
            python_keywords = ['print', 'import', '=', 'def', 'class', 'for', 'while', 'if', 'return', 'lambda']
            python_functions = ['sum', 'len', 'max', 'min', 'range', 'sqrt', 'mean']
            
            # Check if message contains Python code patterns
            if any(keyword in message for keyword in python_keywords + python_functions):
                # Try to compile the message as Python code
                try:
                    compile(message, '<string>', 'exec')
                    code_blocks.append(message)
                except:
                    # If not valid Python, check if it's a single line that could be code
                    lines = message.strip().split('\n')
                    for line in lines:
                        try:
                            compile(line, '<string>', 'exec')
                            code_blocks.append(line)
                        except:
                            pass
        
        return code_blocks
    
    def generate_code_from_intent(self, message: str) -> str:
        """Generate Python code based on user intent"""
        message_lower = message.lower()
        
        # Plotting requests
        if any(word in message_lower for word in self.code_patterns['plot']):
            if 'line' in message_lower:
                return self.executor.generate_plot_code('line', 'data visualization')
            elif 'bar' in message_lower:
                return self.executor.generate_plot_code('bar', 'categorical data')
            else:
                return self.executor.generate_plot_code('histogram', 'data distribution')
        
        # Mathematical calculations
        elif any(word in message_lower for word in self.code_patterns['math']):
            return """
import math
import numpy as np

# Example mathematical computation
def solve_quadratic(a, b, c):
    discriminant = b**2 - 4*a*c
    if discriminant >= 0:
        x1 = (-b + math.sqrt(discriminant)) / (2*a)
        x2 = (-b - math.sqrt(discriminant)) / (2*a)
        return x1, x2
    else:
        return "No real solutions"

# Example: solve x^2 - 5x + 6 = 0
result = solve_quadratic(1, -5, 6)
print(f"Solutions: {result}")
"""
        
        # Data analysis
        elif any(word in message_lower for word in self.code_patterns['data_analysis']):
            return """
import pandas as pd
import numpy as np
import statistics

# Generate sample dataset
data = {
    'values': np.random.normal(50, 15, 100),
    'categories': np.random.choice(['A', 'B', 'C'], 100)
}
df = pd.DataFrame(data)

# Basic statistics
print("Dataset Overview:")
print(df.describe())
print(f"\\nMean: {df['values'].mean():.2f}")
print(f"Median: {df['values'].median():.2f}")
print(f"Standard Deviation: {df['values'].std():.2f}")
print(f"\\nCategory Counts:")
print(df['categories'].value_counts())
"""
        
        else:
            return """
# Simple Python example
print("Hello from Code Interpreter!")
print("I can execute Python code to help with:")
print("- Data analysis and statistics")
print("- Mathematical calculations") 
print("- Creating plots and visualizations")
print("- Processing and transforming data")

# Example calculation
import math
result = math.sqrt(16) + math.factorial(5)
print(f"\\nExample calculation: sqrt(16) + 5! = {result}")
"""
    
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute code interpreter logic (non-streaming)"""
        
        # Get the latest user message
        user_messages = [msg for msg in request["messages"] if msg["role"] == "user"]
        if not user_messages:
            return {"status": "error", "error": "No user messages found"}
        
        user_message = user_messages[-1]["content"]
        
        # Extract or generate code
        code_blocks = self.extract_code_from_message(user_message)
        
        if not code_blocks:
            # Generate code based on intent
            generated_code = self.generate_code_from_intent(user_message)
            code_blocks = [generated_code]
        
        results = []
        
        for i, code in enumerate(code_blocks):
            logger.info(f"Executing code block {i+1}/{len(code_blocks)}")
            
            execution_result = await self.executor.execute_code(code)
            results.append({
                "code": code,
                "result": execution_result,
                "block_index": i
            })
        
        return {
            "status": "success",
            "code_blocks": len(code_blocks),
            "results": results,
            "metadata": {
                "total_execution_time": sum(r["result"].get("execution_time", 0) for r in results),
                "successful_executions": sum(1 for r in results if r["result"].get("success", False))
            }
        }
    
    async def stream(self, request: Dict[str, Any], context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute code interpreter with streaming support"""
        
        # Get the latest user message
        user_messages = [msg for msg in request["messages"] if msg["role"] == "user"]
        if not user_messages:
            yield {"type": "error", "error": "No user messages found"}
            return
        
        user_message = user_messages[-1]["content"]
        
        # Extract or generate code
        code_blocks = self.extract_code_from_message(user_message)
        
        if not code_blocks:
            yield {"type": "code_generated", "message": "No code found in message, generating based on intent..."}
            generated_code = self.generate_code_from_intent(user_message)
            code_blocks = [generated_code]
        
        yield {"type": "code_blocks_identified", "count": len(code_blocks)}
        
        results = []
        
        for i, code in enumerate(code_blocks):
            yield {"type": "code_execution_start", "block_index": i, "code": code[:200] + "..." if len(code) > 200 else code}
            
            # Execute code
            execution_result = await self.executor.execute_code(code)
            
            yield {"type": "code_execution_complete", "block_index": i, "result": execution_result}
            
            results.append({
                "code": code,
                "result": execution_result,
                "block_index": i
            })
        
        # Final summary
        yield {
            "type": "code_interpreter_complete",
            "summary": {
                "total_blocks": len(code_blocks),
                "successful_executions": sum(1 for r in results if r["result"].get("success", False)),
                "total_execution_time": sum(r["result"].get("execution_time", 0) for r in results)
            },
            "results": results
        }


class PythonToolAgent(BaseAgent):
    """Agent that acts as a Python function tool for other agents"""
    
    def __init__(self):
        super().__init__()
        self.supports_streaming = True
        self.interpreter = CodeInterpreterAgent()
    
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute as a function tool call"""
        
        # This agent is designed to be called as a function tool
        function_args = request.get("function_args", {})
        code_to_execute = function_args.get("code", "")
        
        if not code_to_execute:
            return {
                "status": "error",
                "error": "No code provided in function arguments"
            }
        
        # Execute the code
        executor = PythonCodeExecutor()
        result = await executor.execute_code(code_to_execute)
        
        return {
            "status": "success",
            "function_result": result,
            "tool_name": "python_interpreter",
            "metadata": {
                "execution_time": result.get("execution_time", 0),
                "success": result.get("success", False)
            }
        }
    
    async def stream(self, request: Dict[str, Any], context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream function tool execution"""
        
        function_args = request.get("function_args", {})
        code_to_execute = function_args.get("code", "")
        
        if not code_to_execute:
            yield {"type": "error", "error": "No code provided in function arguments"}
            return
        
        yield {"type": "function_tool_start", "tool_name": "python_interpreter"}
        
        # Execute the code
        executor = PythonCodeExecutor()
        result = await executor.execute_code(code_to_execute)
        
        yield {"type": "function_tool_result", "result": result}
        yield {"type": "function_tool_complete", "tool_name": "python_interpreter"}


# Function tools definition for LLM integration
PYTHON_INTERPRETER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "python_interpreter",
            "description": "Execute Python code for data analysis, calculations, visualizations, and computations. Can handle numpy, pandas, matplotlib, and other scientific libraries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to execute. Should be complete and executable."
                    },
                    "description": {
                        "type": "string", 
                        "description": "A brief description of what the code is intended to do."
                    }
                },
                "required": ["code"]
            }
        }
    }
]