"""
Think Block Parser for extracting reasoning content from <think> tokens
Used for Azure AI Inference's DeepSeek models which embed reasoning in regular content
"""

import re
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ThinkBlockParser:
    """
    Parser for extracting <think> blocks from streaming content.
    Handles partial tags across chunks and maintains state.
    """
    
    def __init__(self):
        self.in_think_block = False
        self.partial_buffer = ""  # For handling partial tags across chunks
        
    def process_chunk(self, chunk_content: str) -> Tuple[str, Optional[str], bool]:
        """
        Process a chunk of content and extract think blocks.
        Streams reasoning content as it arrives instead of waiting for closing tag.
        
        Args:
            chunk_content: The content chunk to process
            
        Returns:
            Tuple of:
            - regular_content: Content outside think blocks
            - reasoning_content: Reasoning content from this chunk (streamed immediately)
            - has_reasoning: Whether this chunk contains reasoning content
        """
        # Combine with any partial buffer from previous chunk
        content = self.partial_buffer + chunk_content
        self.partial_buffer = ""
        
        regular_content = ""
        reasoning_content = ""
        has_reasoning = False
        
        # Process character by character to handle partial tags
        i = 0
        while i < len(content):
            if not self.in_think_block:
                # Look for <think> opening tag
                if content[i:].startswith("<think>"):
                    self.in_think_block = True
                    i += 7  # Skip "<think>"
                    has_reasoning = True
                    logger.debug("🧠 ThinkBlockParser: Found <think> opening tag")
                elif i >= len(content) - 6 and "<think>".startswith(content[i:]):
                    # Partial opening tag at end of chunk
                    self.partial_buffer = content[i:]
                    break
                else:
                    regular_content += content[i]
                    i += 1
            else:
                # Inside think block, look for </think> closing tag
                if content[i:].startswith("</think>"):
                    self.in_think_block = False
                    i += 8  # Skip "</think>"
                    logger.debug(f"🧠 ThinkBlockParser: Found </think> closing tag")
                elif i >= len(content) - 7 and "</think>".startswith(content[i:]):
                    # Partial closing tag at end of chunk
                    self.partial_buffer = content[i:]
                    break
                else:
                    # Stream reasoning content immediately as it arrives
                    reasoning_content += content[i]
                    has_reasoning = True
                    i += 1
        
        # Return reasoning content immediately if we have any
        return regular_content, reasoning_content if reasoning_content else None, has_reasoning
    
    def get_partial_reasoning(self) -> Optional[str]:
        """Get any partial reasoning content being buffered
        
        Note: With streaming approach, we don't buffer reasoning content.
        This method is kept for compatibility but always returns None.
        """
        return None
    
    def reset(self):
        """Reset parser state"""
        self.in_think_block = False
        self.partial_buffer = ""
    
    @staticmethod
    def has_think_blocks(content: str) -> bool:
        """Quick check if content contains think blocks"""
        return "<think>" in content
    
    @staticmethod
    def extract_all_think_blocks(content: str) -> Tuple[str, list[str]]:
        """
        Extract all think blocks from complete content (non-streaming).
        
        Returns:
            Tuple of (content_without_think_blocks, list_of_think_contents)
        """
        think_pattern = re.compile(r'<think>(.*?)</think>', re.DOTALL)
        
        think_blocks = []
        def replacer(match):
            think_blocks.append(match.group(1))
            return ""
        
        clean_content = think_pattern.sub(replacer, content)
        
        return clean_content.strip(), think_blocks