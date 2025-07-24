"""
Hybrid Search Module - Combines keyword and vector search for better results

This module implements a hybrid search approach that:
1. Performs keyword/full-text search for exact matches
2. Performs vector/semantic search for conceptual matches
3. Combines and re-ranks results using reciprocal rank fusion
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class HybridSearchResult:
    """Result from hybrid search with combined scoring"""
    type_id: int
    type: str  # 'note' or 'conversation'
    chunk_text: str
    section_id: str
    keyword_score: float = 0.0
    vector_score: float = 0.0
    hybrid_score: float = 0.0
    title: Optional[str] = None
    snippet: Optional[str] = None
    match_positions: Optional[List[Tuple[int, int]]] = None  # For highlighting


class HybridSearchEngine:
    """Implements hybrid search combining keyword and vector search"""
    
    def __init__(self, postgres_manager):
        self.postgres = postgres_manager
        
    def keyword_search_notes(self, query: str, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Perform keyword search on notes using PostgreSQL full-text search
        """
        with self.postgres.get_connection() as conn:
            with conn.cursor() as cursor:
                # Prepare search query - handle special characters
                search_terms = re.sub(r'[^\w\s]', ' ', query).strip()
                if not search_terms:
                    return []
                
                # Convert to tsquery format
                tsquery = ' & '.join(search_terms.split())
                
                cursor.execute("""
                    WITH note_search AS (
                        SELECT 
                            n.id,
                            n."noteTitle" as title,
                            n.promptcontent as content,
                            n."ownerId",
                            ts_rank_cd(
                                to_tsvector('english', COALESCE(n."noteTitle", '') || ' ' || COALESCE(n.promptcontent->>'currentPromptContent', '')),
                                to_tsquery('english', %s)
                            ) as rank,
                            ts_headline(
                                'english',
                                COALESCE(n.promptcontent->>'currentPromptContent', ''),
                                to_tsquery('english', %s),
                                'StartSel=<mark>, StopSel=</mark>, MaxWords=50, MinWords=20'
                            ) as snippet
                        FROM note_v1 n
                        WHERE n."ownerId" = %s
                          AND n."deletedAt" IS NULL
                          AND to_tsvector('english', COALESCE(n."noteTitle", '') || ' ' || COALESCE(n.promptcontent->>'currentPromptContent', '')) @@ to_tsquery('english', %s)
                        ORDER BY rank DESC
                        LIMIT %s
                    )
                    SELECT * FROM note_search WHERE rank > 0
                """, (tsquery, tsquery, user_id, tsquery, limit))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'type_id': row[0],
                        'type': 'note',
                        'title': row[1],
                        'content': row[2],
                        'rank': float(row[4]),
                        'snippet': row[5]
                    })
                
                logger.info(f"Keyword search found {len(results)} notes for query: {query}")
                return results
                
    def keyword_search_conversations(self, query: str, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Perform keyword search on conversations using PostgreSQL full-text search
        """
        with self.postgres.get_connection() as conn:
            with conn.cursor() as cursor:
                # Prepare search query
                search_terms = re.sub(r'[^\w\s]', ' ', query).strip()
                if not search_terms:
                    return []
                
                tsquery = ' & '.join(search_terms.split())
                
                cursor.execute("""
                    WITH conversation_search AS (
                        SELECT 
                            c.id,
                            c.title,
                            c.messages,
                            c."ownerId",
                            ts_rank_cd(
                                to_tsvector('english', COALESCE(c.title, '') || ' ' || COALESCE(c.messages::text, '')),
                                to_tsquery('english', %s)
                            ) as rank,
                            ts_headline(
                                'english',
                                COALESCE(c.messages::text, ''),
                                to_tsquery('english', %s),
                                'StartSel=<mark>, StopSel=</mark>, MaxWords=50, MinWords=20'
                            ) as snippet
                        FROM conversation_v1 c
                        WHERE c."ownerId" = %s
                          AND c."deletedAt" IS NULL
                          AND to_tsvector('english', COALESCE(c.title, '') || ' ' || COALESCE(c.messages::text, '')) @@ to_tsquery('english', %s)
                        ORDER BY rank DESC
                        LIMIT %s
                    )
                    SELECT * FROM conversation_search WHERE rank > 0
                """, (tsquery, tsquery, user_id, tsquery, limit))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'type_id': row[0],
                        'type': 'conversation',
                        'title': row[1],
                        'messages': row[2],
                        'rank': float(row[4]),
                        'snippet': row[5]
                    })
                
                logger.info(f"Keyword search found {len(results)} conversations for query: {query}")
                return results
    
    def combine_results_rrf(self, keyword_results: List[Dict[str, Any]], 
                           vector_results: List[Any], 
                           k: int = 60) -> List[HybridSearchResult]:
        """
        Combine keyword and vector search results using Reciprocal Rank Fusion
        
        RRF Score = 1 / (k + rank)
        where k is a constant (typically 60)
        """
        # Create maps for easy lookup
        keyword_map = {(r['type'], r['type_id']): r for r in keyword_results}
        vector_map = {}
        
        for vr in vector_results:
            key = (vr.type, vr.type_id)
            if key not in vector_map:
                vector_map[key] = []
            vector_map[key].append(vr)
        
        # Calculate RRF scores
        rrf_scores = defaultdict(lambda: {'keyword_rrf': 0, 'vector_rrf': 0})
        
        # Process keyword results
        for rank, result in enumerate(keyword_results):
            key = (result['type'], result['type_id'])
            rrf_scores[key]['keyword_rrf'] = 1 / (k + rank + 1)
            rrf_scores[key]['keyword_data'] = result
        
        # Process vector results
        for rank, result in enumerate(vector_results):
            key = (result.type, result.type_id)
            rrf_scores[key]['vector_rrf'] = 1 / (k + rank + 1)
            if 'vector_data' not in rrf_scores[key]:
                rrf_scores[key]['vector_data'] = []
            rrf_scores[key]['vector_data'].append(result)
        
        # Combine scores and create hybrid results
        hybrid_results = []
        
        for key, scores in rrf_scores.items():
            type_name, type_id = key
            
            # Calculate combined score (can be weighted)
            keyword_weight = 0.4  # Adjust these weights as needed
            vector_weight = 0.6
            
            hybrid_score = (keyword_weight * scores['keyword_rrf'] + 
                          vector_weight * scores['vector_rrf'])
            
            # Get the best data source
            if 'keyword_data' in scores:
                data = scores['keyword_data']
                title = data.get('title')
                snippet = data.get('snippet')
                
                # Get chunk text from vector results if available
                chunk_text = data.get('content', '')
                if 'vector_data' in scores and scores['vector_data']:
                    chunk_text = scores['vector_data'][0].chunk_text
                    section_id = scores['vector_data'][0].section_id
                else:
                    section_id = f"{type_name}_{type_id}_full"
                    
            elif 'vector_data' in scores:
                # Only vector results available
                vdata = scores['vector_data'][0]
                chunk_text = vdata.chunk_text
                section_id = vdata.section_id
                title = getattr(vdata, 'note_title', None) if type_name == 'note' else None
                snippet = chunk_text[:200] + '...' if len(chunk_text) > 200 else chunk_text
            else:
                continue
            
            hybrid_results.append(HybridSearchResult(
                type_id=type_id,
                type=type_name,
                chunk_text=chunk_text,
                section_id=section_id,
                keyword_score=scores['keyword_rrf'],
                vector_score=scores['vector_rrf'],
                hybrid_score=hybrid_score,
                title=title,
                snippet=snippet
            ))
        
        # Sort by hybrid score
        hybrid_results.sort(key=lambda x: x.hybrid_score, reverse=True)
        
        logger.info(f"Hybrid search combined {len(keyword_results)} keyword and {len(vector_results)} vector results into {len(hybrid_results)} hybrid results")
        
        return hybrid_results
    
    async def hybrid_search(self, query: str, user_id: int, 
                          query_embedding: Optional[List[float]] = None,
                          search_type: str = "mixed",
                          note_ids: Optional[List[int]] = None,
                          conversation_ids: Optional[List[int]] = None,
                          top_k: int = 20) -> List[HybridSearchResult]:
        """
        Perform hybrid search combining keyword and vector search
        
        Args:
            query: Search query text
            user_id: User ID
            query_embedding: Pre-computed query embedding (optional)
            search_type: "notes", "conversations", or "mixed"
            note_ids: Specific note IDs to search within
            conversation_ids: Specific conversation IDs to search within
            top_k: Number of results to return
        """
        # Perform keyword search
        keyword_results = []
        
        if search_type in ["notes", "mixed"]:
            keyword_notes = self.keyword_search_notes(query, user_id, limit=top_k * 2)
            
            # Filter by specific IDs if provided
            if note_ids:
                keyword_notes = [r for r in keyword_notes if r['type_id'] in note_ids]
            
            keyword_results.extend(keyword_notes)
        
        if search_type in ["conversations", "mixed"]:
            keyword_convs = self.keyword_search_conversations(query, user_id, limit=top_k * 2)
            
            # Filter by specific IDs if provided
            if conversation_ids:
                keyword_convs = [r for r in keyword_convs if r['type_id'] in conversation_ids]
                
            keyword_results.extend(keyword_convs)
        
        # Perform vector search if embedding provided
        vector_results = []
        if query_embedding:
            # Use existing vector search methods
            from ..rag.rag_processor import UnifiedRAGSearcher, ResolvedIDs
            
            searcher = UnifiedRAGSearcher(self.postgres)
            
            # Build resolved IDs
            resolved_ids = ResolvedIDs(
                notes=note_ids or [],
                conversations=conversation_ids or []
            )
            
            # If no specific IDs, get all user's content
            if not note_ids and not conversation_ids:
                id_resolver = self.postgres
                resolved_ids = id_resolver.resolve_all_ids(
                    user_id=user_id,
                    note_ids=None,
                    folder_ids=None,
                    conversation_ids=None
                )
            
            vector_results = searcher.search_relevant_chunks(
                query=query,
                resolved_ids=resolved_ids,
                top_k=top_k * 2,
                search_type=search_type
            )
        
        # Combine results using RRF
        hybrid_results = self.combine_results_rrf(keyword_results, vector_results)
        
        # Return top_k results
        return hybrid_results[:top_k]