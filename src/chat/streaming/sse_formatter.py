"""SSE (Server-Sent Events) formatter for streaming responses."""
import json
from typing import Dict, Any


class SSEFormatter:
    """Formats data for Server-Sent Events streaming."""
    
    def format_sse(self, data: Dict[str, Any], event: str = None) -> str:
        """Format data as SSE."""
        lines = []
        
        if event:
            lines.append(f"event: {event}")
            
        if isinstance(data, dict):
            lines.append(f"data: {json.dumps(data)}")
        else:
            lines.append(f"data: {data}")
            
        lines.append("")  # Empty line to end the SSE message
        
        return "\n".join(lines) + "\n"