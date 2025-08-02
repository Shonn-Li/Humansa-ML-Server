# HUMANSA V2 - Product Management & Conversation Tracking Design

## Executive Summary

This document addresses:
1. Product management strategy for 108 products
2. Integration analysis of external supplement subagent
3. Conversation tracking system design for HUMANSA V2

## 1. Product Management Strategy (108 Products)

### Analysis: Direct Injection vs RAG

For only **108 products**, the optimal approach is **direct prompt injection**:

#### Why Direct Injection Wins:

1. **Token Economics**:
   - 108 products × ~200 tokens/product = ~21,600 tokens
   - GPT-4.1 has 128K context window
   - Only uses ~17% of available context
   - Leaves plenty of room for conversation history

2. **Performance Benefits**:
   - Zero additional latency (no retrieval step)
   - 100% recall guaranteed
   - No embedding/indexing overhead
   - Simpler system architecture

3. **Implementation Simplicity**:
   ```python
   class ProductAgent:
       def __init__(self, llm, db_config):
           self.llm = llm
           # Load all 108 products once at startup
           self.products_knowledge = self._load_product_knowledge()
           
       async def _load_product_knowledge(self):
           """Load all products into a formatted knowledge string"""
           conn = await asyncpg.connect(**self.db_config)
           products = await conn.fetch("""
               SELECT product_id, name, category, description, 
                      price, ingredients, usage, benefits, warnings
               FROM humansa_products 
               WHERE is_active = true
               ORDER BY category, name
           """)
           
           # Format as structured knowledge
           knowledge = "诺亚医疗产品目录（共{}个产品）：\n\n".format(len(products))
           
           for p in products:
               knowledge += f"""
   产品ID: {p['product_id']}
   名称: {p['name']}
   类别: {p['category']}
   描述: {p['description']}
   成分: {p['ingredients']}
   功效: {p['benefits']}
   用法: {p['usage']}
   价格: ¥{p['price']}
   注意事项: {p['warnings']}
   ---
   """
           return knowledge
           
       def get_system_prompt(self):
           return f"""你是诺亚医疗的产品推荐专家。
   
   {self.products_knowledge}
   
   基于以上完整的产品目录，为用户推荐最合适的产品。
   """
   ```

### Recommendation: Hybrid Caching Strategy

```python
class OptimizedProductAgent:
    """Production-ready product agent with smart caching"""
    
    def __init__(self, llm, db_config):
        self.llm = llm
        self.db_config = db_config
        self.products_cache = {}
        self.formatted_knowledge = ""
        self.last_refresh = None
        self.refresh_interval = 3600  # 1 hour
        
    async def ensure_fresh_cache(self):
        """Refresh cache if needed"""
        now = time.time()
        if not self.last_refresh or (now - self.last_refresh) > self.refresh_interval:
            await self._refresh_product_cache()
            
    async def _refresh_product_cache(self):
        """Refresh the product cache from database"""
        conn = await asyncpg.connect(**self.db_config)
        try:
            # Load all products with full details
            products = await conn.fetch("""
                SELECT p.*, 
                       COUNT(DISTINCT o.order_id) as purchase_count,
                       AVG(r.rating) as avg_rating
                FROM humansa_products p
                LEFT JOIN order_items o ON p.product_id = o.product_id
                LEFT JOIN product_reviews r ON p.product_id = r.product_id
                WHERE p.is_active = true
                GROUP BY p.product_id
                ORDER BY purchase_count DESC, p.category, p.name
            """)
            
            # Build cache and formatted knowledge
            self.products_cache = {p['product_id']: dict(p) for p in products}
            self.formatted_knowledge = self._format_product_knowledge(products)
            self.last_refresh = time.time()
            
            logger.info(f"✅ Refreshed cache with {len(products)} products")
            
        finally:
            await conn.close()
    
    def _format_product_knowledge(self, products):
        """Format products into structured prompt knowledge"""
        # Group by category for better organization
        categories = {}
        for p in products:
            cat = p['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(p)
        
        knowledge = f"诺亚医疗产品目录（更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}）\n\n"
        
        for category, items in categories.items():
            knowledge += f"【{category}】（{len(items)}个产品）\n"
            for p in items:
                popularity = "⭐" * min(5, int((p['purchase_count'] or 0) / 100))
                knowledge += f"""
产品：{p['name']} {popularity}
- ID: {p['product_id']}
- 功效：{p['benefits']}
- 成分：{p['ingredients']}
- 价格：¥{p['price']}
- 评分：{p['avg_rating'] or 'N/A'}/5
- 适用：{p['target_audience']}
"""
            knowledge += "\n"
        
        return knowledge
```

## 2. External Supplement SubAgent Analysis

### Code Review of `subagent_system.py`

The external agent is a **multi-expert parallel consultation system** with interesting architecture:

#### Strengths:
1. **Multi-Provider Support**: Supports OpenAI, DeepSeek, Claude, Grok, Gemini
2. **Parallel Processing**: 4 experts run concurrently
3. **Structured Output**: Each expert returns JSON
4. **Error Handling**: Graceful fallbacks

#### Weaknesses for Integration:
1. **No Database Connection**: Pure prompt-based, no real product data
2. **Different Architecture**: Not LlamaIndex-based
3. **Stateless**: No conversation memory
4. **External API Dependency**: Requires separate API keys

### Integration Analysis

**❌ NOT RECOMMENDED for direct integration** because:

1. **Architecture Mismatch**:
   - Uses ThreadPoolExecutor vs our async architecture
   - No LlamaIndex tool framework
   - Different response format

2. **Data Source Issues**:
   - Relies on prompt injection of product data
   - No connection to our PostgreSQL database
   - Can't access real inventory/pricing

3. **Conversation Tracking**:
   - Completely stateless
   - No user_id or session_id handling
   - No Mem0 integration

### Better Approach: Extract Useful Concepts

Instead of integrating the code, extract useful patterns:

```python
class EnhancedProductAgent(BaseHumansaAgent):
    """Enhanced product agent inspired by multi-expert pattern"""
    
    def __init__(self, llm, db_config):
        # Create internal expert prompts
        self.expert_prompts = {
            'demand_analysis': self._get_demand_expert_prompt(),
            'nutrition_science': self._get_nutrition_expert_prompt(),
            'risk_assessment': self._get_risk_expert_prompt()
        }
        
        # Create tools that use expert analysis
        tools = [
            FunctionTool.from_defaults(
                fn=self._analyze_with_experts,
                name="expert_analysis",
                description="Analyze user needs with multiple expert perspectives"
            ),
            FunctionTool.from_defaults(
                fn=self._search_products_db,
                name="search_products",
                description="Search products from database"
            ),
            FunctionTool.from_defaults(
                fn=self._generate_recommendation,
                name="generate_recommendation",
                description="Generate final product recommendations"
            )
        ]
        
        super().__init__(
            agent_id="enhanced_product_agent",
            llm=llm,
            tools=tools
        )
    
    async def _analyze_with_experts(self, query: str) -> Dict[str, Any]:
        """Run parallel expert analysis using our LLM"""
        # Use asyncio.gather for parallel processing
        tasks = []
        for expert_type, prompt in self.expert_prompts.items():
            tasks.append(self._get_expert_opinion(prompt, query))
        
        results = await asyncio.gather(*tasks)
        
        return {
            'demand_analysis': results[0],
            'nutrition_science': results[1],
            'risk_assessment': results[2]
        }
```

## 3. Conversation Tracking System Design

### Current State Analysis

From the test environment SQL, we can see YouWoAI V1 has:
- `conversation_v1` table with proper structure
- User-conversation relationships
- Message history in JSONB format

### HUMANSA V2 Conversation Design

Since HUMANSA V2 is **completely separate** from V1, we need our own conversation system:

#### Database Schema

```sql
-- HUMANSA V2 Conversation Management Tables

-- 1. Conversation Sessions
CREATE TABLE humansa_conversations (
    conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_message_at TIMESTAMP DEFAULT NOW(),
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'active', -- active, archived, expired
    session_type VARCHAR(50) DEFAULT 'chat', -- chat, consultation, appointment_flow
    
    -- Context summary (for quick loading)
    context_summary JSONB DEFAULT '{}',
    key_topics TEXT[],
    
    -- Metrics
    message_count INTEGER DEFAULT 0,
    token_count INTEGER DEFAULT 0,
    
    -- Expiration (for GDPR/privacy)
    expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '90 days'),
    
    INDEX idx_user_conversations (user_id, updated_at DESC),
    INDEX idx_active_sessions (status, last_message_at DESC)
);

-- 2. Conversation Messages
CREATE TABLE humansa_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES humansa_conversations(conversation_id) ON DELETE CASCADE,
    
    -- Message content
    role VARCHAR(50) NOT NULL, -- user, assistant, system, tool
    content TEXT NOT NULL,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Tool calls and results
    tool_calls JSONB, -- Array of tool calls made
    tool_results JSONB, -- Results from tools
    
    -- Agent routing
    agent_used VARCHAR(100), -- Which sub-agent handled this
    reasoning JSONB, -- Agent's reasoning chain
    
    -- Metrics
    token_count INTEGER,
    processing_time_ms INTEGER,
    
    INDEX idx_conversation_messages (conversation_id, created_at)
);

-- 3. Conversation Context (for efficient loading)
CREATE TABLE humansa_conversation_context (
    conversation_id UUID PRIMARY KEY REFERENCES humansa_conversations(conversation_id) ON DELETE CASCADE,
    
    -- User profile snapshot
    user_profile JSONB DEFAULT '{}',
    
    -- Medical context
    symptoms TEXT[],
    medications TEXT[],
    allergies TEXT[],
    conditions TEXT[],
    
    -- Preferences
    preferences JSONB DEFAULT '{}',
    
    -- Recent actions
    recent_products TEXT[],
    recent_appointments TEXT[],
    
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 4. Session continuity (for handling disconnections)
CREATE TABLE humansa_session_continuity (
    continuity_token UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES humansa_conversations(conversation_id),
    user_id VARCHAR(255) NOT NULL,
    
    -- For resuming
    last_message_id UUID,
    last_agent_state JSONB,
    
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '1 hour'),
    
    INDEX idx_user_tokens (user_id, created_at DESC)
);
```

#### Conversation Object Structure

```python
@dataclass
class HumansaConversation:
    """Conversation object for HUMANSA V2"""
    conversation_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    status: str = 'active'
    session_type: str = 'chat'
    
    # Messages
    messages: List[HumansaMessage] = field(default_factory=list)
    
    # Context
    context_summary: Dict[str, Any] = field(default_factory=dict)
    key_topics: List[str] = field(default_factory=list)
    
    # Metrics
    message_count: int = 0
    token_count: int = 0
    
    # Medical context
    medical_context: MedicalContext = field(default_factory=MedicalContext)

@dataclass
class HumansaMessage:
    """Message object"""
    message_id: str
    role: str  # user, assistant, system, tool
    content: str
    created_at: datetime
    
    # Optional fields
    tool_calls: Optional[List[Dict]] = None
    tool_results: Optional[List[Dict]] = None
    agent_used: Optional[str] = None
    reasoning: Optional[Dict] = None
    token_count: Optional[int] = None

@dataclass
class MedicalContext:
    """Medical context for a conversation"""
    symptoms: List[str] = field(default_factory=list)
    medications: List[str] = field(default_factory=list)
    allergies: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    recent_products: List[str] = field(default_factory=list)
    recent_appointments: List[str] = field(default_factory=list)
```

#### Conversation Manager Implementation

```python
class HumansaConversationManager:
    """Manages conversations for HUMANSA V2"""
    
    def __init__(self, db_pool, mem0_manager=None):
        self.db_pool = db_pool
        self.mem0_manager = mem0_manager
        
    async def create_conversation(self, user_id: str, session_type: str = 'chat') -> HumansaConversation:
        """Create a new conversation"""
        conversation_id = str(uuid.uuid4())
        
        await self.db_pool.execute("""
            INSERT INTO humansa_conversations 
            (conversation_id, user_id, session_type)
            VALUES ($1, $2, $3)
        """, conversation_id, user_id, session_type)
        
        # Load user context from Mem0
        if self.mem0_manager:
            user_context = await self.mem0_manager.get_user_context(user_id)
            await self._initialize_context(conversation_id, user_context)
        
        return HumansaConversation(
            conversation_id=conversation_id,
            user_id=user_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            session_type=session_type
        )
    
    async def get_or_create_conversation(
        self, 
        user_id: str, 
        conversation_id: Optional[str] = None
    ) -> HumansaConversation:
        """Get existing conversation or create new one"""
        
        if conversation_id:
            # Try to load existing
            conversation = await self.load_conversation(conversation_id)
            if conversation and conversation.user_id == user_id:
                return conversation
        
        # Check for recent active conversation
        recent = await self.db_pool.fetchrow("""
            SELECT conversation_id 
            FROM humansa_conversations
            WHERE user_id = $1 
                AND status = 'active'
                AND last_message_at > NOW() - INTERVAL '30 minutes'
            ORDER BY last_message_at DESC
            LIMIT 1
        """, user_id)
        
        if recent:
            return await self.load_conversation(recent['conversation_id'])
        
        # Create new conversation
        return await self.create_conversation(user_id)
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        **metadata
    ) -> HumansaMessage:
        """Add a message to conversation"""
        message_id = str(uuid.uuid4())
        
        # Calculate tokens (approximate)
        token_count = len(content.split()) * 1.3
        
        await self.db_pool.execute("""
            INSERT INTO humansa_messages
            (message_id, conversation_id, role, content, 
             tool_calls, tool_results, agent_used, reasoning, token_count)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, 
            message_id, conversation_id, role, content,
            json.dumps(metadata.get('tool_calls')),
            json.dumps(metadata.get('tool_results')),
            metadata.get('agent_used'),
            json.dumps(metadata.get('reasoning')),
            int(token_count)
        )
        
        # Update conversation metadata
        await self.db_pool.execute("""
            UPDATE humansa_conversations
            SET last_message_at = NOW(),
                updated_at = NOW(),
                message_count = message_count + 1,
                token_count = token_count + $1
            WHERE conversation_id = $2
        """, int(token_count), conversation_id)
        
        # Update Mem0 if assistant response
        if role == 'assistant' and self.mem0_manager:
            await self._update_mem0(conversation_id, content)
        
        return HumansaMessage(
            message_id=message_id,
            role=role,
            content=content,
            created_at=datetime.now(),
            token_count=int(token_count),
            **metadata
        )
    
    async def load_conversation(
        self, 
        conversation_id: str,
        include_messages: bool = True,
        message_limit: int = 50
    ) -> Optional[HumansaConversation]:
        """Load a conversation with messages"""
        
        # Load conversation metadata
        conv_row = await self.db_pool.fetchrow("""
            SELECT * FROM humansa_conversations
            WHERE conversation_id = $1
        """, conversation_id)
        
        if not conv_row:
            return None
        
        conversation = HumansaConversation(
            conversation_id=conv_row['conversation_id'],
            user_id=conv_row['user_id'],
            created_at=conv_row['created_at'],
            updated_at=conv_row['updated_at'],
            status=conv_row['status'],
            session_type=conv_row['session_type'],
            context_summary=conv_row['context_summary'] or {},
            key_topics=conv_row['key_topics'] or [],
            message_count=conv_row['message_count'],
            token_count=conv_row['token_count']
        )
        
        # Load messages if requested
        if include_messages:
            messages = await self.db_pool.fetch("""
                SELECT * FROM humansa_messages
                WHERE conversation_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, conversation_id, message_limit)
            
            conversation.messages = [
                HumansaMessage(
                    message_id=msg['message_id'],
                    role=msg['role'],
                    content=msg['content'],
                    created_at=msg['created_at'],
                    tool_calls=msg['tool_calls'],
                    tool_results=msg['tool_results'],
                    agent_used=msg['agent_used'],
                    reasoning=msg['reasoning'],
                    token_count=msg['token_count']
                )
                for msg in reversed(messages)  # Reverse to get chronological order
            ]
        
        # Load medical context
        context_row = await self.db_pool.fetchrow("""
            SELECT * FROM humansa_conversation_context
            WHERE conversation_id = $1
        """, conversation_id)
        
        if context_row:
            conversation.medical_context = MedicalContext(
                symptoms=context_row['symptoms'] or [],
                medications=context_row['medications'] or [],
                allergies=context_row['allergies'] or [],
                conditions=context_row['conditions'] or [],
                recent_products=context_row['recent_products'] or [],
                recent_appointments=context_row['recent_appointments'] or []
            )
        
        return conversation
    
    async def get_conversation_summary(self, conversation_id: str) -> str:
        """Get a summary of the conversation for context"""
        messages = await self.db_pool.fetch("""
            SELECT role, content, created_at
            FROM humansa_messages
            WHERE conversation_id = $1
            ORDER BY created_at
            LIMIT 20
        """, conversation_id)
        
        if not messages:
            return "新对话"
        
        # Simple summary logic
        topics = set()
        for msg in messages:
            if msg['role'] == 'user':
                # Extract key topics (simple version)
                content_lower = msg['content'].lower()
                if '预约' in content_lower or '挂号' in content_lower:
                    topics.add('预约挂号')
                if '产品' in content_lower or '保健品' in content_lower:
                    topics.add('产品咨询')
                if '症状' in content_lower or '疼' in content_lower:
                    topics.add('症状分析')
        
        summary = f"对话包含{len(messages)}条消息"
        if topics:
            summary += f"，涉及：{', '.join(topics)}"
        
        return summary
```

#### API Integration

```python
# Update api.py to support conversation tracking

@humansa_v2_bp.route('/v2/humansa/chat', methods=['POST'])
async def chat():
    data = await request.get_json()
    user_id = data.get('user_id', 'anonymous')
    conversation_id = data.get('conversation_id')  # Now supported!
    messages = data.get('messages', [])
    stream = data.get('stream', True)
    
    # Get or create conversation
    conversation = await conversation_manager.get_or_create_conversation(
        user_id=user_id,
        conversation_id=conversation_id
    )
    
    # Add user message
    user_message = messages[-1]['content'] if messages else ""
    await conversation_manager.add_message(
        conversation.conversation_id,
        role='user',
        content=user_message
    )
    
    # Load conversation context
    context = await conversation_manager.load_conversation(
        conversation.conversation_id,
        include_messages=True,
        message_limit=10  # Last 10 messages for context
    )
    
    # Process with orchestrator
    async for chunk in orchestrator.process_query(
        query=user_message,
        user_id=user_id,
        session_id=conversation.conversation_id,  # Pass conversation ID
        messages=[  # Convert to API format
            {"role": msg.role, "content": msg.content}
            for msg in context.messages
        ],
        stream=stream
    ):
        # If streaming, include conversation_id in response
        if stream and 'choices' in chunk:
            chunk['conversation_id'] = conversation.conversation_id
        
        yield chunk
    
    # Return conversation_id in response header
    response.headers['X-Conversation-ID'] = conversation.conversation_id
```

## 4. Implementation Recommendations

### Phase 1: Product Agent Enhancement (1 week)
1. Implement direct product knowledge injection
2. Add caching with hourly refresh
3. Connect to real `humansa_products` table
4. Add purchase count and rating data

### Phase 2: Conversation Tracking (2 weeks)
1. Create conversation tables
2. Implement ConversationManager
3. Update API endpoints
4. Test with multiple sessions

### Phase 3: Integration & Testing (1 week)
1. Integrate enhanced ProductAgent
2. Test conversation continuity
3. Performance optimization
4. Documentation

## 5. Summary

1. **Product Management**: Use direct injection for 108 products - no RAG needed
2. **External Agent**: Don't integrate directly - extract useful patterns only
3. **Conversation Tracking**: Implement proper session management with database schema
4. **Separate from V1**: HUMANSA V2 has its own complete conversation system

The proposed design provides:
- ✅ Efficient product recommendations
- ✅ Proper conversation continuity
- ✅ Scalable architecture
- ✅ Clean separation from V1

---

**Created**: 2025-08-01  
**Status**: Design Proposal  
**Next Steps**: Review and approve implementation plan