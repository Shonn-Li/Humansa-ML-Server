"""
Citation Position Tracker for OpenAI Response API Format

This module tracks citation positions in text and generates proper annotation events
with accurate start_index and end_index positions.
"""
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class CitationAnnotation:
    """Represents a citation annotation with position information"""
    type: str = "url_citation"
    start_index: int = 0
    end_index: int = 0
    text: str = ""  # The citation marker text e.g. "[1]"
    url: str = ""
    title: str = ""
    note_id: Optional[int] = None
    conversation_id: Optional[int] = None
    source_type: str = "web"  # "web", "note", or "conversation"
    
    def to_dict(self) -> Dict:
        """Convert to OpenAI Response API format"""
        result = {
            "type": self.type,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "text": self.text,
            "url": self.url,
            "title": self.title
        }
        # Include additional fields if present
        if self.note_id is not None:
            result["note_id"] = self.note_id
        if self.conversation_id is not None:
            result["conversation_id"] = self.conversation_id
        if self.source_type:
            result["source_type"] = self.source_type
        return result


class CitationPositionTracker:
    """Tracks citation positions in text for OpenAI Response API compliance"""
    
    def __init__(self):
        # Pattern to match citation markers like [1], [2], etc.
        self.citation_pattern = re.compile(r'\[(\d+)\]')
        
    def extract_citations_with_positions(self, text: str, sources: List[Dict]) -> Tuple[str, List[CitationAnnotation]]:
        """
        Extract citation positions from text and match with sources.
        
        Args:
            text: The text containing citation markers [1], [2], etc.
            sources: List of source dictionaries with url, title, etc.
            
        Returns:
            Tuple of (text, annotations) where annotations have accurate positions
        """
        annotations = []
        
        # Find all citation markers in the text
        for match in self.citation_pattern.finditer(text):
            citation_num = int(match.group(1))
            start_pos = match.start()
            end_pos = match.end()
            citation_text = match.group(0)  # e.g. "[1]"
            
            # Get corresponding source (1-indexed)
            source_idx = citation_num - 1
            if 0 <= source_idx < len(sources):
                source = sources[source_idx]
                
                # Create annotation with full source metadata
                # Generate URL for notes if not present
                url = source.get('url', '')
                if not url and source.get('note_id'):
                    url = f"note://{source.get('note_id')}"
                elif not url and source.get('conversation_id'):
                    url = f"conversation://{source.get('conversation_id')}"
                
                annotation = CitationAnnotation(
                    start_index=start_pos,
                    end_index=end_pos,
                    text=citation_text,
                    url=url,
                    title=source.get('title', f'Source {citation_num}'),
                    note_id=source.get('note_id'),
                    conversation_id=source.get('conversation_id'),
                    source_type=source.get('type', 'web' if source.get('url', '').startswith('http') else 'note')
                )
                annotations.append(annotation)
                
                logger.info(f"📍 Found citation {citation_text} at position {start_pos}-{end_pos}")
            else:
                logger.warning(f"Citation {citation_text} has no matching source")
        
        return text, annotations
    
    def track_streaming_positions(self, text_chunks: List[str]) -> List[Tuple[int, int, str]]:
        """
        Track citation positions across streaming chunks.
        
        Args:
            text_chunks: List of text chunks received during streaming
            
        Returns:
            List of (chunk_index, position_in_chunk, citation_text) tuples
        """
        positions = []
        cumulative_length = 0
        
        for chunk_idx, chunk in enumerate(text_chunks):
            # Find citations in this chunk
            for match in self.citation_pattern.finditer(chunk):
                position_in_chunk = match.start()
                absolute_position = cumulative_length + position_in_chunk
                citation_text = match.group(0)
                
                positions.append((chunk_idx, position_in_chunk, citation_text, absolute_position))
                
            cumulative_length += len(chunk)
            
        return positions
    
    def inject_citations_into_text(self, text: str, sources: List[Dict]) -> Tuple[str, List[CitationAnnotation]]:
        """
        Inject citations into text if not already present.
        
        This is useful when the LLM doesn't add citation markers but we want to
        add them based on source relevance.
        
        Args:
            text: The original text without citations
            sources: List of sources to cite
            
        Returns:
            Tuple of (text_with_citations, annotations)
        """
        if not sources:
            return text, []
            
        # Check if text already has citations
        if self.citation_pattern.search(text):
            # Text already has citations, just extract positions
            return self.extract_citations_with_positions(text, sources)
        
        # No citations found, we need to inject them
        # This is a simplified approach - in production you'd want
        # more sophisticated relevance matching
        
        # Add a citation section at the end
        citations_text = "\n\nSources:\n"
        annotations = []
        
        # Position where we'll add citations
        citation_start = len(text) + len("\n\nSources:\n")
        
        for i, source in enumerate(sources):
            citation_num = i + 1
            citation_marker = f"[{citation_num}]"
            source_text = f"{citation_marker} {source.get('title', 'Untitled')}\n"
            
            # Create annotation for this citation with full metadata
            # Generate URL for notes if not present
            url = source.get('url', '')
            if not url and source.get('note_id'):
                url = f"note://{source.get('note_id')}"
            elif not url and source.get('conversation_id'):
                url = f"conversation://{source.get('conversation_id')}"
            
            annotation = CitationAnnotation(
                start_index=citation_start,
                end_index=citation_start + len(citation_marker),
                text=citation_marker,
                url=url,
                title=source.get('title', f'Source {citation_num}'),
                note_id=source.get('note_id'),
                conversation_id=source.get('conversation_id'),
                source_type=source.get('type', 'web' if source.get('url', '').startswith('http') else 'note')
            )
            annotations.append(annotation)
            
            citations_text += source_text
            citation_start += len(source_text)
        
        return text + citations_text, annotations


# Singleton instance
citation_position_tracker = CitationPositionTracker()