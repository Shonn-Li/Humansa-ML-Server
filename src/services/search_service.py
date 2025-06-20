import logging
from typing import List, Dict, Any
from src.utility.postgres import keyword_search, advanced_keyword_search
from src.models.response import SearchResult

logger = logging.getLogger(__name__)


class SearchService:
    """Service for search operations"""
    
    def keyword_search(self, query: str, user_id: int, limit: int = 20) -> List[SearchResult]:
        """Perform keyword search using tsvector"""
        results = keyword_search(query, user_id, limit)
        
        search_results = []
        for note_id, chunk_text, source, rank in results:
            preview = chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
            search_results.append(SearchResult(
                note_id=note_id,
                chunk_text=chunk_text,
                source=source,
                relevance_score=float(rank),
                preview=preview
            ))
        
        return search_results
    
    def advanced_search(self, query: str, user_id: int, source_filter: str = None, limit: int = 20) -> Dict[str, Any]:
        """Perform advanced search with source filtering"""
        results = advanced_keyword_search(query, user_id, source_filter, limit)
        
        # Group results by note
        note_groups = {}
        for note_id, chunk_text, source, rank, note_title in results:
            if note_id not in note_groups:
                note_groups[note_id] = {
                    "note_id": note_id,
                    "note_title": note_title,
                    "chunks": [],
                    "max_relevance": 0.0
                }
            
            preview = chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
            chunk_info = {
                "chunk_text": chunk_text,
                "source": source,
                "relevance_score": float(rank),
                "preview": preview
            }
            
            note_groups[note_id]["chunks"].append(chunk_info)
            note_groups[note_id]["max_relevance"] = max(note_groups[note_id]["max_relevance"], float(rank))
        
        # Sort notes by maximum relevance
        sorted_notes = sorted(note_groups.values(), key=lambda x: x["max_relevance"], reverse=True)
        
        return {
            "total_notes": len(sorted_notes),
            "total_chunks": len(results),
            "results": sorted_notes
        }
    
    def validate_search_request(self, data: dict) -> tuple[bool, str, dict]:
        """Validate search request and extract parameters"""
        query = data.get("query", "").strip()
        user_id = data.get("user_id")
        limit = data.get("limit", 20)
        
        if not query:
            return False, "Query is required", {}
        
        if not user_id:
            return False, "user_id is required", {}
        
        # Validate limit
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            limit = 20
        
        params = {
            "query": query,
            "user_id": user_id,
            "limit": limit,
            "source_filter": data.get("source_filter")
        }
        
        return True, "", params


# Global search service instance
search_service = SearchService()
