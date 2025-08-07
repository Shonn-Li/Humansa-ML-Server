"""
Mem0 Manager for Humansa
Handles automatic initialization and memory operations
"""

import os
import logging
from typing import Optional, Dict, Any, List
from mem0 import Memory

logger = logging.getLogger(__name__)


class Mem0Manager:
    """
    Manages Mem0 initialization and operations for Humansa.
    Auto-creates schema on first run in production.
    """
    
    _instance: Optional['Mem0Manager'] = None
    
    def __init__(self):
        self.memory: Optional[Memory] = None
        self.initialized = False
        self.config = self._build_config()
        
    @classmethod
    def get_instance(cls) -> 'Mem0Manager':
        """Get singleton instance of Mem0Manager"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _build_config(self) -> Dict[str, Any]:
        """Build Mem0 configuration from environment variables"""
        # Determine environment
        environment = os.getenv("ENVIRONMENT", "prod")
        mem0_schema = os.getenv("MEM0_SCHEMA", f"mem0_humansa_{environment}")
        
        # Azure OpenAI configuration
        azure_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_INFERENCE_CREDENTIAL")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://youwoai-dev-resource.openai.azure.com/")
        azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT4", "gpt-4.1")
        azure_embedding = os.getenv("AZURE_OPENAI_DEPLOYMENT_EMBEDDING", "text-embedding-ada-002")
        
        # Use OpenAI if Azure not configured
        openai_key = os.getenv("OPENAI_API_KEY")
        
        config = {
            "vector_store": {
                "provider": "pgvector",
                "config": {
                    "host": os.getenv("DB_HOST", "localhost"),
                    "port": int(os.getenv("DB_PORT", "5432")),
                    "user": os.getenv("DB_USER", "postgres"),
                    "password": os.getenv("DB_PASSWORD", "postgres"),
                    "dbname": os.getenv("DB_NAME", "youwoai"),
                    "collection_name": f"{mem0_schema}_memories"
                }
            }
        }
        
        # Configure LLM provider
        # For now, skip Azure and use OpenAI directly if available
        # Azure configuration seems to have compatibility issues with Mem0
        if openai_key:
            logger.info("Configuring Mem0 with OpenAI - model: gpt-4o-mini")
            config["llm"] = {
                "provider": "openai",
                "config": {
                    "api_key": openai_key,
                    "model": "gpt-4o-mini"  # Use a model this project has access to
                }
            }
            config["embedder"] = {
                "provider": "openai",
                "config": {
                    "api_key": openai_key,
                    "model": "text-embedding-3-small"
                }
            }
        else:
            logger.warning("No LLM API keys configured. Mem0 will not be initialized.")
            return {}
            
        return config
    
    async def initialize(self) -> bool:
        """
        Initialize Mem0 with auto-schema creation.
        Returns True if successful, False otherwise.
        """
        if self.initialized:
            return True
            
        if not self.config:
            logger.warning("Mem0 not configured. Skipping initialization.")
            return False
            
        try:
            logger.info("Initializing Mem0 memory layer...")
            
            # First, ensure schema exists
            await self._ensure_schema_exists()
            
            # Initialize Mem0
            self.memory = Memory.from_config(self.config)
            
            # Test connection
            test_user = "mem0_init_test"
            self.memory.get_all(user_id=test_user)  # This will create tables if needed
            
            self.initialized = True
            logger.info("✅ Mem0 initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Mem0: {e}")
            return False
    
    async def _ensure_schema_exists(self):
        """Ensure the database schema exists for Mem0"""
        try:
            import asyncpg
            
            # Get schema name from config
            collection_name = self.config["vector_store"]["config"]["collection_name"]
            schema_name = collection_name.split("_memories")[0]
            
            # Connect to database
            conn = await asyncpg.connect(
                host=self.config["vector_store"]["config"]["host"],
                port=self.config["vector_store"]["config"]["port"],
                user=self.config["vector_store"]["config"]["user"],
                password=self.config["vector_store"]["config"]["password"],
                database=self.config["vector_store"]["config"]["dbname"]
            )
            
            try:
                # Create schema if not exists
                await conn.execute(f"""
                    CREATE SCHEMA IF NOT EXISTS {schema_name}
                """)
                
                # Grant permissions
                user = self.config["vector_store"]["config"]["user"]
                await conn.execute(f"""
                    GRANT ALL PRIVILEGES ON SCHEMA {schema_name} TO {user}
                """)
                
                # Ensure pgvector extension
                await conn.execute("""
                    CREATE EXTENSION IF NOT EXISTS vector
                """)
                
                logger.info(f"✅ Schema '{schema_name}' ready for Mem0")
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.warning(f"Could not ensure schema exists: {e}")
            # Not critical - Mem0 might create it anyway
    
    def get_memory_user_id(self, user_id: str, context: str = "humansa") -> str:
        """Generate consistent memory user ID"""
        environment = os.getenv("ENVIRONMENT", "prod")
        return f"{context}_{environment}_{user_id}"
    
    async def add_conversation(
        self,
        user_id: str,
        query: str = None,
        response: str = None,
        messages: List[Dict[str, str]] = None,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add conversation to memory"""
        if not self.initialized:
            logger.warning("Mem0 not initialized. Cannot add conversation.")
            return False
            
        try:
            memory_user_id = self.get_memory_user_id(user_id)
            
            # Add default metadata
            if metadata is None:
                metadata = {}
            metadata.update({
                "source": "humansa",
                "conversation_id": conversation_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Format the conversation for Mem0
            if query and response:
                # Single Q&A format
                memory_text = f"User: {query}\nAssistant: {response}"
            elif messages:
                # Full conversation format
                memory_text = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in messages])
            else:
                logger.warning("No conversation content provided")
                return False
            
            # Mem0 operations are synchronous, so we run in thread
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.memory.add(
                    memory_text,
                    user_id=memory_user_id,
                    metadata=metadata
                )
            )
            
            logger.info(f"✅ Added conversation to memory for user {user_id}: {result}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add conversation to memory: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search user memories"""
        if not self.initialized:
            return []
            
        try:
            memory_user_id = self.get_memory_user_id(user_id)
            
            import asyncio
            loop = asyncio.get_event_loop()
            memories = await loop.run_in_executor(
                None,
                lambda: self.memory.search(
                    query,
                    user_id=memory_user_id,
                    limit=limit
                )
            )
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user context from memories"""
        if not self.initialized:
            return {"user_id": user_id, "memories": []}
            
        try:
            memory_user_id = self.get_memory_user_id(user_id)
            logger.info(f"🔍 Getting context for memory_user_id: {memory_user_id}")
            
            import asyncio
            loop = asyncio.get_event_loop()
            all_memories = await loop.run_in_executor(
                None,
                lambda: self.memory.get_all(user_id=memory_user_id)
            )
            
            logger.info(f"📚 Retrieved memories: {all_memories}")
            
            # Extract memories from results format
            if isinstance(all_memories, dict) and 'results' in all_memories:
                all_memories = all_memories['results']
            elif not isinstance(all_memories, list):
                all_memories = []
            
            return {
                "user_id": user_id,
                "memory_count": len(all_memories),
                "recent_memories": all_memories[:5] if all_memories else []
            }
            
        except Exception as e:
            logger.error(f"Failed to get user context: {e}")
            import traceback
            traceback.print_exc()
            return {
                "user_id": user_id, 
                "memory_count": 0,
                "recent_memories": []
            }


# Import datetime if not already imported
from datetime import datetime