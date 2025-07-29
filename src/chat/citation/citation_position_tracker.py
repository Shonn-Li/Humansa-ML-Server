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
            "type": self.source_type,  # Use source_type as the main type field
            "start_index": self.start_index,
            "end_index": self.end_index,
            "text": self.text,
            "url": self.url,
            "title": self.title
        }
        
        # Include type_id based on source type
        if self.source_type == "note" and self.note_id is not None:
            result["type_id"] = self.note_id
            result["note_id"] = self.note_id
        elif self.source_type == "conversation" and self.conversation_id is not None:
            result["type_id"] = self.conversation_id
            result["conversation_id"] = self.conversation_id
        
        return result


class CitationPositionTracker:
    """Tracks citation positions in text for OpenAI Response API compliance"""
    
    def __init__(self):
        # Pattern to match citation markers like [1], [2], etc.
        self.citation_pattern = re.compile(r'\[(\d+)\]')
        # Pattern to match multi-citation markers like [1, 2], [4, 7-9], etc.
        self.multi_citation_pattern = re.compile(r'\[(\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)\]')
        
    def extract_citations_with_positions(self, text: str, sources: List[Dict]) -> Tuple[str, List[Dict]]:
        """
        Build annotations for ALL sources with their citation positions.
        
        Args:
            text: The text containing citation markers [1], [2], etc.
            sources: List of source dictionaries with url, title, etc.
            
        Returns:
            Tuple of (text, annotations) where annotations include all sources
        """
        annotations = []
        
        # First, find all multi-citation patterns and track which sources they contain
        multi_citation_matches = []
        for match in self.multi_citation_pattern.finditer(text):
            citation_text = match.group(0)  # e.g., "[1, 2]" or "[4, 7-9]"
            citation_nums = match.group(1)  # e.g., "1, 2" or "4, 7-9"
            
            # Parse all numbers from the citation (expanding ranges)
            parsed_numbers = []
            parts = citation_nums.split(',')
            for part in parts:
                part = part.strip()
                if '-' in part:
                    # Handle range like "7-9"
                    start, end = part.split('-')
                    parsed_numbers.extend(range(int(start), int(end) + 1))
                else:
                    parsed_numbers.append(int(part))
            
            multi_citation_matches.append({
                'match': match,
                'text': citation_text,
                'numbers': parsed_numbers,
                'start': match.start(),
                'end': match.end()
            })
        
        # Build annotation for each source
        for idx, source in enumerate(sources):
            source_num = idx + 1
            
            # Find all positions where this source is cited
            citation_positions = []
            
            # Check multi-citations first
            for mc in multi_citation_matches:
                if source_num in mc['numbers']:
                    # Determine the position within the multi-citation
                    nums_before = [n for n in mc['numbers'] if n < source_num]
                    
                    if len(mc['numbers']) == 1:
                        # Single citation, include full brackets
                        citation_positions.append({
                            "start_index": mc['start'],
                            "end_index": mc['end'],
                            "text": mc['text']
                        })
                    else:
                        # Multi-citation, calculate specific portion to replace
                        if source_num == mc['numbers'][0]:
                            # First citation: "[1, " from "[1, 2]"
                            # Find where this number ends in the citation text
                            num_str = str(source_num)
                            inner_text = mc['text'][1:-1]  # Remove outer brackets
                            num_pos = inner_text.find(num_str)
                            if num_pos != -1:
                                # Include from '[' to after the comma and space
                                end_pos = num_pos + len(num_str)
                                # Look for comma and space after the number
                                if end_pos < len(inner_text) and inner_text[end_pos:end_pos+2] == ', ':
                                    end_pos += 2  # Include ", "
                                citation_positions.append({
                                    "start_index": mc['start'],
                                    "end_index": mc['start'] + 1 + end_pos,  # +1 for opening bracket
                                    "text": mc['text'][:1 + end_pos]
                                })
                        elif source_num == mc['numbers'][-1]:
                            # Last citation: "2]" from "[1, 2]"
                            num_str = str(source_num)
                            inner_text = mc['text'][1:-1]  # Remove outer brackets
                            # Find the last occurrence of this number
                            num_pos = inner_text.rfind(num_str)
                            if num_pos != -1:
                                citation_positions.append({
                                    "start_index": mc['start'] + 1 + num_pos,  # +1 for opening bracket
                                    "end_index": mc['end'],
                                    "text": inner_text[num_pos:] + ']'
                                })
                        else:
                            # Middle citation: ", 2, " from "[1, 2, 3]"
                            num_str = str(source_num)
                            inner_text = mc['text'][1:-1]  # Remove outer brackets
                            num_pos = inner_text.find(num_str)
                            if num_pos != -1:
                                # Include leading comma/space and trailing comma/space
                                start_pos = num_pos
                                if start_pos >= 2 and inner_text[start_pos-2:start_pos] == ', ':
                                    start_pos -= 2
                                end_pos = num_pos + len(num_str)
                                if end_pos < len(inner_text) and inner_text[end_pos:end_pos+2] == ', ':
                                    end_pos += 2
                                citation_positions.append({
                                    "start_index": mc['start'] + 1 + start_pos,  # +1 for opening bracket
                                    "end_index": mc['start'] + 1 + end_pos,
                                    "text": inner_text[start_pos:end_pos]
                                })
            
            # Also check for standalone single citations (not part of multi-citations)
            # Only if not already found in multi-citations
            if not citation_positions:
                pattern = re.compile(f'\\[{source_num}\\]')
                for match in pattern.finditer(text):
                    # Make sure this isn't part of a multi-citation we already processed
                    is_part_of_multi = any(
                        mc['start'] <= match.start() < mc['end'] 
                        for mc in multi_citation_matches
                    )
                    if not is_part_of_multi:
                        citation_positions.append({
                            "start_index": match.start(),
                            "end_index": match.end(),
                            "text": f"[{source_num}]"
                        })
            
            # Determine source type
            metadata = source.get('metadata', {})
            actual_type = source.get('type')
            if not actual_type:
                actual_type = metadata.get('type')
            if not actual_type:
                # Fallback to determining type from available fields
                if source.get('note_id') or metadata.get('note_id'):
                    actual_type = 'note'
                elif source.get('conversation_id') or metadata.get('conversation_id'):
                    actual_type = 'conversation'
                elif source.get('url', '').startswith('http'):
                    actual_type = 'web'
                else:
                    actual_type = 'note'  # Default fallback
            
            # Get type_id from source
            type_id = source.get('type_id') or source.get('note_id') or metadata.get('note_id') or source.get('conversation_id') or metadata.get('conversation_id')
            
            # Build annotation object with all source data
            annotation = {
                "type": actual_type,
                "type_id": type_id,
                "source_number": source_num,
                "title": source.get('title', f'Source {source_num}'),
                "url": source.get('url', ''),
                "note_id": source.get('note_id') or metadata.get('note_id'),
                "conversation_id": source.get('conversation_id') or metadata.get('conversation_id'),
                "citation_positions": citation_positions,
                # Include other useful metadata
                "content": source.get('content', ''),
                "snippet": source.get('snippet', '')
            }
            
            # Remove None values
            annotation = {k: v for k, v in annotation.items() if v is not None}
            
            annotations.append(annotation)
            
            if citation_positions:
                logger.info(f"📍 Source {source_num} cited {len(citation_positions)} times")
        
        logger.info(f"📚 Built annotations for {len(sources)} sources")
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
        
        # No citations found, return original text without modifications
        # The citations will be handled by the frontend UI instead of injecting them into text
        return text, []


# Singleton instance
citation_position_tracker = CitationPositionTracker()