#!/usr/bin/env python3
"""
Citation Engine Debug Test

This script creates mock data to test the citation engine and identify
exactly what's causing the failures.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# Import the citation engine
from chat.citation.citation_engine import CitationEngine, CitationResult, CitationSource


@dataclass
class MockChunkResult:
    """Mock chunk result for testing"""
    type: str
    type_id: int
    chunk_text: str
    section_id: int = 1
    similarity: float = 0.9


@dataclass
class MockRAGContext:
    """Mock RAG context for testing"""
    chunks: List[MockChunkResult]
    used_note_ids: List[int]
    used_conversation_ids: List[int]
    total_chunks: int
    query_used: str


@dataclass
class MockWebSearchResult:
    """Mock web search result for testing"""
    title: str
    snippet: str
    link: str
    source: str
    cached: bool = False


@dataclass
class MockWebSearchContext:
    """Mock web search context for testing"""
    results: List[MockWebSearchResult]
    query_used: str
    total_results: int
    search_performed: bool
    cache_hit: bool


@dataclass
class MockAttachmentContext:
    """Mock attachment context for testing"""
    chunks: List[Dict[str, Any]]
    image_chunks: List[Dict[str, Any]]
    total_chunks: int


class MockLLM:
    """Mock LLM for testing"""
    
    def complete(self, prompt: str):
        """Mock completion method"""
        class MockCompletion:
            def __init__(self, text: str):
                self.text = text
        
        # Return a mock response with citations
        return MockCompletion(
            "Based on the provided sources, here's the information: "
            "[1] shows that artificial intelligence is advancing rapidly. "
            "[2] indicates that machine learning is a key component. "
            "[3] demonstrates practical applications in various fields."
        )


def test_citation_engine_with_rag_context():
    """Test citation engine with RAG context"""
    print("🧠 Testing Citation Engine with RAG Context")
    print("=" * 50)
    
    # Create mock RAG context
    rag_chunks = [
        MockChunkResult(
            type="note",
            type_id=1670,
            chunk_text="Artificial intelligence has made significant advances in recent years, particularly in natural language processing and computer vision.",
            section_id=1,
            similarity=0.95
        ),
        MockChunkResult(
            type="note", 
            type_id=1671,
            chunk_text="Machine learning algorithms, especially deep learning models, are the foundation of modern AI systems.",
            section_id=2,
            similarity=0.88
        )
    ]
    
    rag_context = MockRAGContext(
        chunks=rag_chunks,
        used_note_ids=[1670, 1671],
        used_conversation_ids=[],
        total_chunks=2,
        query_used="What can you tell me about artificial intelligence?"
    )
    
    # Test citation engine
    citation_engine = CitationEngine()
    mock_llm = MockLLM()
    
    try:
        result = citation_engine.generate_citation_response(
            query="What can you tell me about artificial intelligence?",
            rag_context=rag_context,
            attachment_context=None,
            websearch_context=None,
            llm=mock_llm
        )
        
        print(f"✅ RAG Context Test PASSED")
        print(f"   • Response: {result.response[:100]}...")
        print(f"   • Sources: {result.total_sources}")
        print(f"   • Source mapping: {result.source_mapping}")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG Context Test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_citation_engine_with_web_context():
    """Test citation engine with web search context"""
    print("\n🌐 Testing Citation Engine with Web Search Context")
    print("=" * 50)
    
    # Create mock web search context
    web_results = [
        MockWebSearchResult(
            title="AI News | Latest AI News, Analysis & Events",
            snippet="Latest developments in artificial intelligence technology and research.",
            link="https://ai-news.com/latest",
            source="AI News",
            cached=False
        ),
        MockWebSearchResult(
            title="AI Research Advances in 2024",
            snippet="Breakthrough developments in machine learning and neural networks.",
            link="https://research.ai/2024-advances",
            source="AI Research",
            cached=True
        )
    ]
    
    web_context = MockWebSearchContext(
        results=web_results,
        query_used="What are the latest AI developments?",
        total_results=2,
        search_performed=True,
        cache_hit=False
    )
    
    # Test citation engine
    citation_engine = CitationEngine()
    mock_llm = MockLLM()
    
    try:
        result = citation_engine.generate_citation_response(
            query="What are the latest AI developments?",
            rag_context=None,
            attachment_context=None,
            websearch_context=web_context,
            llm=mock_llm
        )
        
        print(f"✅ Web Search Context Test PASSED")
        print(f"   • Response: {result.response[:100]}...")
        print(f"   • Sources: {result.total_sources}")
        print(f"   • Source mapping: {result.source_mapping}")
        
        return True
        
    except Exception as e:
        print(f"❌ Web Search Context Test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_citation_engine_with_attachment_context():
    """Test citation engine with attachment context"""
    print("\n📎 Testing Citation Engine with Attachment Context")
    print("=" * 50)
    
    # Create mock attachment context
    attachment_chunks = [
        {
            'filename': 'ai_research_paper.pdf',
            'content': 'This research paper discusses the latest advances in artificial intelligence and machine learning technologies.',
            'url': 'https://example.com/files/ai_research_paper.pdf',
            'metadata': {'file_type': 'pdf', 'pages': 10}
        },
        {
            'filename': 'ml_presentation.pptx',
            'content': 'Presentation slides covering machine learning algorithms and their applications in various industries.',
            'url': 'https://example.com/files/ml_presentation.pptx',
            'metadata': {'file_type': 'presentation', 'slides': 25}
        }
    ]
    
    attachment_context = MockAttachmentContext(
        chunks=attachment_chunks,
        image_chunks=[],
        total_chunks=2
    )
    
    # Test citation engine
    citation_engine = CitationEngine()
    mock_llm = MockLLM()
    
    try:
        result = citation_engine.generate_citation_response(
            query="What information do you have about AI in my documents?",
            rag_context=None,
            attachment_context=attachment_context,
            websearch_context=None,
            llm=mock_llm
        )
        
        print(f"✅ Attachment Context Test PASSED")
        print(f"   • Response: {result.response[:100]}...")
        print(f"   • Sources: {result.total_sources}")
        print(f"   • Source mapping: {result.source_mapping}")
        
        return True
        
    except Exception as e:
        print(f"❌ Attachment Context Test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_citation_engine_with_mixed_context():
    """Test citation engine with all context types"""
    print("\n🔄 Testing Citation Engine with Mixed Context")
    print("=" * 50)
    
    # Create mock contexts (reuse from above tests)
    rag_chunks = [
        MockChunkResult(
            type="note",
            type_id=1670,
            chunk_text="AI research notes from personal knowledge base.",
            section_id=1,
            similarity=0.95
        )
    ]
    
    rag_context = MockRAGContext(
        chunks=rag_chunks,
        used_note_ids=[1670],
        used_conversation_ids=[],
        total_chunks=1,
        query_used="Mixed query test"
    )
    
    web_results = [
        MockWebSearchResult(
            title="Latest AI News",
            snippet="Current AI developments from the web.",
            link="https://ai-news.com/latest",
            source="AI News",
            cached=False
        )
    ]
    
    web_context = MockWebSearchContext(
        results=web_results,
        query_used="Mixed query test",
        total_results=1,
        search_performed=True,
        cache_hit=False
    )
    
    attachment_chunks = [
        {
            'filename': 'ai_document.pdf',
            'content': 'AI document content from file attachment.',
            'url': 'https://example.com/ai_document.pdf',
            'metadata': {'file_type': 'pdf'}
        }
    ]
    
    attachment_context = MockAttachmentContext(
        chunks=attachment_chunks,
        image_chunks=[],
        total_chunks=1
    )
    
    # Test citation engine
    citation_engine = CitationEngine()
    mock_llm = MockLLM()
    
    try:
        result = citation_engine.generate_citation_response(
            query="Tell me about AI from all available sources",
            rag_context=rag_context,
            attachment_context=attachment_context,
            websearch_context=web_context,
            llm=mock_llm
        )
        
        print(f"✅ Mixed Context Test PASSED")
        print(f"   • Response: {result.response[:100]}...")
        print(f"   • Sources: {result.total_sources}")
        print(f"   • Source mapping: {result.source_mapping}")
        
        return True
        
    except Exception as e:
        print(f"❌ Mixed Context Test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all citation engine tests"""
    print("🔍 Citation Engine Debug Test Suite")
    print("=" * 60)
    
    tests = [
        test_citation_engine_with_rag_context,
        test_citation_engine_with_web_context,
        test_citation_engine_with_attachment_context,
        test_citation_engine_with_mixed_context
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All citation engine tests PASSED!")
        print("   The citation engine should work with proper context objects.")
    else:
        print("❌ Some tests FAILED!")
        print("   The citation engine has issues that need to be fixed.")


if __name__ == "__main__":
    main()
