"""
Agentic RAG Processor - Intelligent Multi-Step Retrieval

Based on the LlamaIndex article about agentic retrieval, this processor:
1. Understands user intent and decomposes queries
2. Performs multi-step retrieval with different strategies
3. Handles temporal queries (recent, last week, etc.)
4. Iteratively refines search based on results
5. Combines multiple search strategies (keyword, semantic, temporal)
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

from ..provider.llm_provider import LLMProviderSelector
from ..rag.rag_processor import RAGProcessor, RAGContext
from ..search.hybrid_search import HybridSearchEngine
from ..postgres.db_manager import PostgresManager, ChunkResult
from ..embedding.embedding_provider_selector import EmbeddingProviderSelector

logger = logging.getLogger(__name__)


@dataclass
class QueryUnderstanding:
    """Result of query analysis"""
    intent: str  # summarize, search, question, etc.
    temporal_filter: Optional[Dict[str, Any]]  # date range if applicable
    key_concepts: List[str]  # main concepts to search for
    search_strategies: List[str]  # keyword, semantic, temporal, etc.
    original_query: str


@dataclass 
class RetrievalStep:
    """A single retrieval step in the multi-step process"""
    strategy: str
    query: str
    filters: Optional[Dict[str, Any]]
    results: List[ChunkResult]
    evaluation: Optional[str]  # LLM evaluation of results


class AgenticRAGProcessor:
    """
    Intelligent RAG processor that uses LLM to understand queries
    and perform multi-step retrieval
    """
    
    def __init__(
        self,
        rag_processor: RAGProcessor,
        postgres: PostgresManager,
        hybrid_search: HybridSearchEngine
    ):
        self.rag_processor = rag_processor
        self.postgres = postgres
        self.hybrid_search = hybrid_search
        self.embedder = EmbeddingProviderSelector().get_embedding_client()
        self.llm_selector = LLMProviderSelector()
        # Import embedding manager for auto-embedding
        from ..embedding.embedding_manager import embedding_manager
        self.embedding_manager = embedding_manager
        
    async def process_query(
        self,
        query: str,
        user_id: int,
        note_ids: Optional[List[int]] = None,
        conversation_ids: Optional[List[int]] = None,
        max_steps: int = 3
    ) -> Dict[str, Any]:
        """
        Process query using agentic approach with multi-step retrieval
        """
        logger.info(f"🤖 Starting agentic RAG processing for: {query}")
        
        # Step 1: Understand the query
        understanding = await self._understand_query(query)
        
        # Step 1.5: Handle missing embeddings for temporal/recency searches
        if understanding.intent == "summarize" or understanding.temporal_filter:
            # For temporal queries, we need to check and embed recent notes
            await self._handle_missing_embeddings_for_temporal(
                user_id, understanding.temporal_filter or {"days_ago": 7}
            )
        logger.info(f"📊 Query understanding: {understanding}")
        
        # Step 2: Perform multi-step retrieval
        retrieval_steps = []
        all_results = []
        seen_chunks = set()  # Track unique chunks
        
        for step in range(max_steps):
            # Determine retrieval strategy for this step
            strategy = await self._determine_next_strategy(
                understanding, retrieval_steps, all_results
            )
            
            if not strategy:
                logger.info("✅ No more retrieval steps needed")
                break
                
            # Execute retrieval step
            step_result = await self._execute_retrieval_step(
                strategy=strategy,
                understanding=understanding,
                user_id=user_id,
                note_ids=note_ids,
                conversation_ids=conversation_ids,
                previous_results=all_results
            )
            
            # Filter out duplicates
            unique_results = []
            for chunk in step_result.results:
                chunk_id = f"{chunk.type}_{chunk.type_id}_{chunk.section_id}"
                if chunk_id not in seen_chunks:
                    seen_chunks.add(chunk_id)
                    unique_results.append(chunk)
                    all_results.append(chunk)
            
            step_result.results = unique_results
            retrieval_steps.append(step_result)
            
            # Evaluate if we have enough relevant results
            if await self._has_sufficient_results(understanding, all_results):
                logger.info("✅ Sufficient results found")
                break
        
        # Step 3: Format and return results
        return self._format_agentic_results(
            understanding=understanding,
            retrieval_steps=retrieval_steps,
            all_results=all_results
        )
    
    async def _understand_query(self, query: str) -> QueryUnderstanding:
        """Use LLM to understand query intent and extract key information"""
        
        prompt = f"""Analyze this query and extract key information:
Query: "{query}"

Please provide a JSON response with:
1. intent: The main intent (summarize, search, question, explain, etc.)
2. temporal_filter: Any time-based filters mentioned (recent, today, last week, etc.)
   - If "recent" is mentioned, assume last 7 days
   - Format as: {{"days_ago": number}} or {{"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}}
3. key_concepts: List of main concepts/keywords to search for
   - IMPORTANT: For summarize intent, DO NOT include words like "summarize", "summary", etc.
   - Only include the actual topics/subjects to search for
   - If no specific topics mentioned (e.g., "summarize my recent notes"), return empty array []
4. search_strategies: Ordered list of strategies to try (temporal, keyword, semantic, expand_query, recency)
   - Use "recency" for fetching most recent notes without semantic search

Example responses:
{{
  "intent": "summarize",
  "temporal_filter": {{"days_ago": 7}},
  "key_concepts": [],  // Empty because no specific topic mentioned
  "search_strategies": ["recency", "temporal"]
}}

{{
  "intent": "summarize", 
  "temporal_filter": {{"days_ago": 7}},
  "key_concepts": ["project updates", "deadlines"],  // Specific topics to find
  "search_strategies": ["temporal", "keyword", "semantic"]
}}
"""
        
        try:
            # Use a fast model for query understanding
            provider_info = self.llm_selector.get_provider(model="gpt-4-mini")
            llm = provider_info["llm"]
            from llama_index.core.llms import ChatMessage
            messages = [ChatMessage(role="user", content=prompt)]
            response = await llm.achat(messages, temperature=0.1)
            
            # Parse JSON response from llama_index format
            content = response.message.content
            # Extract JSON from markdown if wrapped
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            result = json.loads(content.strip())
            
            return QueryUnderstanding(
                intent=result.get("intent", "search"),
                temporal_filter=result.get("temporal_filter"),
                key_concepts=result.get("key_concepts", [query]),
                search_strategies=result.get("search_strategies", ["keyword", "semantic"]),
                original_query=query
            )
            
        except Exception as e:
            logger.error(f"Failed to understand query: {e}")
            # Fallback to simple understanding
            return QueryUnderstanding(
                intent="search",
                temporal_filter={"days_ago": 7} if "recent" in query.lower() else None,
                key_concepts=[query],
                search_strategies=["keyword", "semantic"],
                original_query=query
            )
    
    async def _determine_next_strategy(
        self,
        understanding: QueryUnderstanding,
        previous_steps: List[RetrievalStep],
        current_results: List[ChunkResult]
    ) -> Optional[Dict[str, Any]]:
        """Determine the next retrieval strategy based on current state"""
        
        # Get unused strategies
        used_strategies = {step.strategy for step in previous_steps}
        remaining_strategies = [
            s for s in understanding.search_strategies 
            if s not in used_strategies
        ]
        
        if not remaining_strategies:
            return None
            
        # If we have no results yet, try the next strategy
        if not current_results:
            return {
                "type": remaining_strategies[0],
                "query": understanding.original_query
            }
        
        # Use LLM to evaluate current results and determine next step
        results_summary = "\n".join([
            f"- {r.chunk_text[:100]}..." for r in current_results[:5]
        ])
        
        prompt = f"""Based on the user query and current search results, should we continue searching?

User Query: "{understanding.original_query}"
Intent: {understanding.intent}
Current Results Found: {len(current_results)}

Sample of current results:
{results_summary}

Remaining search strategies available: {remaining_strategies}

If the current results seem insufficient or not relevant enough, suggest the next strategy.
Otherwise, return null.

Respond with JSON:
{{"continue": true/false, "strategy": "strategy_name" or null, "reason": "explanation"}}
"""
        
        try:
            provider_info = self.llm_selector.get_provider(model="gpt-4-mini")
            llm = provider_info["llm"]
            from llama_index.core.llms import ChatMessage
            messages = [ChatMessage(role="user", content=prompt)]
            response = await llm.achat(messages, temperature=0.1)
            
            content = response.message.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            result = json.loads(content.strip())
            
            if result.get("continue") and result.get("strategy"):
                return {
                    "type": result["strategy"],
                    "query": understanding.original_query,
                    "reason": result.get("reason", "")
                }
                
        except Exception as e:
            logger.error(f"Failed to determine next strategy: {e}")
            
        return None
    
    async def _execute_retrieval_step(
        self,
        strategy: Dict[str, Any],
        understanding: QueryUnderstanding,
        user_id: int,
        note_ids: Optional[List[int]],
        conversation_ids: Optional[List[int]],
        previous_results: List[ChunkResult]
    ) -> RetrievalStep:
        """Execute a single retrieval step with the given strategy"""
        
        strategy_type = strategy["type"]
        results = []
        
        logger.info(f"🔍 Executing retrieval strategy: {strategy_type}")
        
        if strategy_type == "recency":
            results = await self._recency_search(
                understanding, user_id, note_ids, conversation_ids
            )
        elif strategy_type == "temporal":
            results = await self._temporal_search(
                understanding, user_id, note_ids, conversation_ids
            )
        elif strategy_type == "keyword":
            results = await self._keyword_search(
                understanding, user_id, note_ids, conversation_ids
            )
        elif strategy_type == "semantic":
            results = await self._semantic_search(
                understanding, user_id, note_ids, conversation_ids
            )
        elif strategy_type == "expand_query":
            results = await self._expanded_query_search(
                understanding, user_id, note_ids, conversation_ids, previous_results
            )
        
        return RetrievalStep(
            strategy=strategy_type,
            query=strategy.get("query", understanding.original_query),
            filters=understanding.temporal_filter,
            results=results,
            evaluation=None
        )
    
    async def _recency_search(
        self,
        understanding: QueryUnderstanding,
        user_id: int,
        note_ids: Optional[List[int]],
        conversation_ids: Optional[List[int]]
    ) -> List[ChunkResult]:
        """Fetch most recent notes without semantic search - for summary intents"""
        
        # Get temporal filter or default to last 7 days
        temporal_filter = understanding.temporal_filter or {"days_ago": 7}
        
        # Get notes within the time range
        temporal_note_ids = await self._get_temporal_notes(
            user_id, temporal_filter, note_ids
        )
        
        if not temporal_note_ids:
            logger.info("No notes found in temporal range")
            return []
        
        logger.info(f"Found {len(temporal_note_ids)} notes in recency search")
        
        # For recency search, we want to get ALL chunks from these notes
        # without filtering by semantic similarity
        with self.postgres.get_connection() as conn:
            with conn.cursor() as cursor:
                # First check if these notes have embeddings
                cursor.execute("""
                    SELECT COUNT(DISTINCT e.type_id) 
                    FROM embedding_v1 e 
                    WHERE e.type_id = ANY(%s) AND e.type = 'note'
                """, (temporal_note_ids,))
                embedded_count = cursor.fetchone()[0]
                logger.info(f"Found {embedded_count} notes with embeddings out of {len(temporal_note_ids)} temporal notes")
                
                # Get all chunks from the temporal notes
                cursor.execute("""
                    SELECT 
                        e.type_id,
                        e.type,
                        e.chunk_text,
                        1.0 as similarity,  -- Max similarity since it's recency-based
                        e.section_id,
                        n."noteTitle" as title,
                        n."createDate"
                    FROM embedding_v1 e
                    INNER JOIN note_v1 n ON e.type_id = n.id AND e.type = 'note'
                    WHERE e.type_id = ANY(%s)
                    AND e.type = 'note'
                    ORDER BY n."createDate" DESC, e.section_id ASC
                    LIMIT %s
                """, (temporal_note_ids, 50))  # Get up to 50 chunks
                
                results = []
                for row in cursor.fetchall():
                    chunk = ChunkResult(
                        type_id=row[0],
                        type=row[1],
                        chunk_text=row[2],
                        similarity=row[3],
                        section_id=row[4],
                        metadata={"title": row[5], "created": str(row[6])} if row[5] else None
                    )
                    results.append(chunk)
                
                logger.info(f"Recency search returned {len(results)} chunks")
                
                # If no embeddings found, try to get note content directly as fallback
                if len(results) == 0 and len(temporal_note_ids) > 0:
                    logger.warning(f"No embeddings found for temporal notes, falling back to direct note content")
                    cursor.execute("""
                        SELECT 
                            n.id,
                            'note' as type,
                            n."noteTextContent",
                            1.0 as similarity,
                            0 as section_id,
                            n."noteTitle",
                            n."createDate"
                        FROM note_v1 n
                        WHERE n.id = ANY(%s)
                        AND n."noteTextContent" IS NOT NULL
                        AND n."noteTextContent" != ''
                        ORDER BY n."createDate" DESC
                        LIMIT 20
                    """, (temporal_note_ids[:20],))  # Limit to 20 most recent notes
                    
                    for row in cursor.fetchall():
                        if row[2]:  # If note has content
                            chunk = ChunkResult(
                                type_id=row[0],
                                type=row[1],
                                chunk_text=row[2][:1000],  # Limit text length
                                similarity=row[3],
                                section_id=row[4],
                                metadata={"title": row[5], "created": str(row[6])} if row[5] else None
                            )
                            results.append(chunk)
                    
                    logger.info(f"Fallback: Got {len(results)} notes with direct content")
                
                return results
    
    async def _handle_missing_embeddings_for_temporal(
        self,
        user_id: int,
        temporal_filter: Dict[str, Any]
    ) -> None:
        """Check and embed missing notes for temporal queries"""
        try:
            # Get notes within temporal range
            temporal_note_ids = await self._get_temporal_notes(user_id, temporal_filter, None)
            
            if not temporal_note_ids:
                return
            
            logger.info(f"Checking embeddings for {len(temporal_note_ids)} temporal notes")
            
            # Check which notes are missing embeddings
            missing_note_ids = await self.rag_processor._check_missing_embeddings_async('note', temporal_note_ids)
            
            if missing_note_ids:
                logger.warning(f"⚠️ Found {len(missing_note_ids)} temporal notes without embeddings")
                logger.info("⏳ Creating embeddings for temporal notes...")
                
                # Create embeddings synchronously for temporal queries
                await self.rag_processor._create_embeddings_sync_async('note', missing_note_ids)
                
                logger.info(f"✅ Created embeddings for {len(missing_note_ids)} temporal notes")
            else:
                logger.info(f"✅ All {len(temporal_note_ids)} temporal notes have embeddings")
                
        except Exception as e:
            logger.error(f"Error handling missing embeddings: {e}")
            # Don't fail the whole query if embedding check fails
    
    async def _temporal_search(
        self,
        understanding: QueryUnderstanding,
        user_id: int,
        note_ids: Optional[List[int]],
        conversation_ids: Optional[List[int]]
    ) -> List[ChunkResult]:
        """Search with temporal filters"""
        
        if not understanding.temporal_filter:
            return []
            
        # Get notes within the time range
        temporal_note_ids = await self._get_temporal_notes(
            user_id, understanding.temporal_filter, note_ids
        )
        
        if not temporal_note_ids:
            logger.info("No notes found in temporal range")
            return []
        
        # Search within these temporal notes
        try:
            embedding = self.embedder.get_text_embedding(understanding.original_query)
        except:
            embedding = None
            
        results = await self.hybrid_search.hybrid_search(
            query=understanding.original_query,
            user_id=user_id,
            query_embedding=embedding,
            search_type="notes",
            note_ids=temporal_note_ids,
            conversation_ids=None,  # Disabled to prevent context pollution
            top_k=10
        )
        
        return results
    
    async def _get_temporal_notes(
        self,
        user_id: int,
        temporal_filter: Dict[str, Any],
        existing_note_ids: Optional[List[int]] = None
    ) -> List[int]:
        """Get note IDs that match temporal filter"""
        
        with self.postgres.get_connection() as conn:
            with conn.cursor() as cursor:
                # Build date filter
                if "days_ago" in temporal_filter:
                    days = temporal_filter["days_ago"]
                    start_date = datetime.now() - timedelta(days=days)
                    date_filter = f'"createDate" >= %s'
                    params = [start_date, user_id]
                else:
                    # Assume start_date and end_date
                    date_filter = '"createDate" BETWEEN %s AND %s'
                    params = [
                        temporal_filter.get("start_date"),
                        temporal_filter.get("end_date"),
                        user_id
                    ]
                
                # Build query
                query = f"""
                    SELECT id 
                    FROM note_v1 
                    WHERE {date_filter}
                    AND "ownerId" = %s
                    AND "deletedAt" IS NULL
                """
                
                # Add existing note filter if provided
                if existing_note_ids:
                    query += " AND id = ANY(%s)"
                    params.append(existing_note_ids)
                
                query += " ORDER BY \"createDate\" DESC"
                
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                note_ids = [row[0] for row in results]
                logger.info(f"Found {len(note_ids)} notes in temporal range")
                return note_ids
    
    async def _keyword_search(
        self,
        understanding: QueryUnderstanding,
        user_id: int,
        note_ids: Optional[List[int]],
        conversation_ids: Optional[List[int]]
    ) -> List[ChunkResult]:
        """Perform keyword-based search"""
        
        # Use key concepts for keyword search
        query = " ".join(understanding.key_concepts)
        
        results = await self.hybrid_search.hybrid_search(
            query=query,
            user_id=user_id,
            query_embedding=None,  # Pure keyword search
            search_type="notes",
            note_ids=note_ids,
            conversation_ids=None,  # Disabled to prevent context pollution
            top_k=10
        )
        
        return results
    
    async def _semantic_search(
        self,
        understanding: QueryUnderstanding,
        user_id: int,
        note_ids: Optional[List[int]],
        conversation_ids: Optional[List[int]]
    ) -> List[ChunkResult]:
        """Perform semantic/embedding-based search"""
        
        try:
            embedding = self.embedder.get_text_embedding(understanding.original_query)
        except:
            return []
            
        results = await self.hybrid_search.hybrid_search(
            query=understanding.original_query,
            user_id=user_id,
            query_embedding=embedding,
            search_type="notes",
            note_ids=note_ids,
            conversation_ids=None,  # Disabled to prevent context pollution
            top_k=10
        )
        
        return results
    
    async def _expanded_query_search(
        self,
        understanding: QueryUnderstanding,
        user_id: int,
        note_ids: Optional[List[int]],
        conversation_ids: Optional[List[int]],
        previous_results: List[ChunkResult]
    ) -> List[ChunkResult]:
        """Expand query based on previous results and search again"""
        
        # Use LLM to suggest related terms based on what we've found
        if previous_results:
            sample_results = "\n".join([
                f"- {r.chunk_text[:100]}..." for r in previous_results[:3]
            ])
            
            prompt = f"""Based on the user query and sample results found, suggest related search terms.

User Query: "{understanding.original_query}"

Sample results found:
{sample_results}

Suggest 3-5 related search terms that might find more relevant content.
Return as JSON: {{"terms": ["term1", "term2", ...]}}
"""
            
            try:
                provider_info = self.llm_selector.get_provider(model="gpt-4-mini")
                llm = provider_info["llm"]
                from llama_index.core.llms import ChatMessage
                messages = [ChatMessage(role="user", content=prompt)]
                response = await llm.achat(messages, temperature=0.3)
                
                content = response.message.content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                    
                result = json.loads(content.strip())
                expanded_terms = result.get("terms", [])
                
                # Search with expanded terms
                expanded_query = " ".join(expanded_terms)
                embedding = self.embedder.get_text_embedding(expanded_query)
                
                results = await self.hybrid_search.hybrid_search(
                    query=expanded_query,
                    user_id=user_id,
                    query_embedding=embedding,
                    search_type="notes",
                    note_ids=note_ids,
                    conversation_ids=None,  # Disabled to prevent context pollution
                    top_k=10
                )
                
                return results
                
            except Exception as e:
                logger.error(f"Failed to expand query: {e}")
                
        return []
    
    async def _has_sufficient_results(
        self,
        understanding: QueryUnderstanding,
        results: List[ChunkResult]
    ) -> bool:
        """Determine if we have enough relevant results"""
        
        # Simple heuristics
        if understanding.intent == "summarize":
            # For summarization, we want at least 5 chunks
            return len(results) >= 5
        elif understanding.intent == "search":
            # For search, even 1 good result might be enough
            return len(results) >= 1
        else:
            # Default: aim for at least 3 results
            return len(results) >= 3
    
    def _format_agentic_results(
        self,
        understanding: QueryUnderstanding,
        retrieval_steps: List[RetrievalStep],
        all_results: List[ChunkResult]
    ) -> Dict[str, Any]:
        """Format the agentic retrieval results"""
        
        # Group results by source
        sources = []
        seen_sources = set()
        
        # Collect all unique note and conversation IDs
        note_ids = set()
        conversation_ids = set()
        for chunk in all_results:
            if chunk.type == "note":
                note_ids.add(chunk.type_id)
            elif chunk.type == "conversation":
                conversation_ids.add(chunk.type_id)
        
        # Batch fetch titles
        note_titles = {}
        if note_ids:
            note_titles = self.postgres.get_note_titles_batch(list(note_ids))
        
        for chunk in all_results:
            source_key = f"{chunk.type}_{chunk.type_id}"
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                
                # Get title from batch results or metadata
                title = None
                if chunk.type == "note" and chunk.type_id in note_titles:
                    title = note_titles[chunk.type_id]
                elif chunk.metadata and isinstance(chunk.metadata, dict):
                    title = chunk.metadata.get("title")
                
                source = {
                    "type": chunk.type,
                    "type_id": chunk.type_id,
                    "title": title,
                    "chunks": []
                }
                
                # Add all chunks from this source
                for c in all_results:
                    if c.type == chunk.type and c.type_id == chunk.type_id:
                        source["chunks"].append({
                            "content": c.chunk_text,
                            "section_id": c.section_id,
                            "score": getattr(c, "similarity", 0.0)
                        })
                
                sources.append(source)
        
        # Build context for LLM
        context_parts = []
        for chunk in all_results[:15]:  # Limit to top 15 chunks
            context_parts.append(chunk.chunk_text)
        
        return {
            "status": "completed",
            "understanding": {
                "intent": understanding.intent,
                "temporal_filter": understanding.temporal_filter,
                "key_concepts": understanding.key_concepts
            },
            "retrieval_steps": [
                {
                    "strategy": step.strategy,
                    "query": step.query,
                    "results_count": len(step.results)
                }
                for step in retrieval_steps
            ],
            "context": "\n\n---\n\n".join(context_parts),
            "sources": sources,
            "total_results": len(all_results),
            "search_summary": f"Found {len(all_results)} relevant chunks from {len(sources)} sources using {len(retrieval_steps)} retrieval strategies"
        }