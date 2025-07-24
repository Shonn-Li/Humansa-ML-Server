-- Test Conversations for YouWoAI Test Environment
-- Generated at: 2025-07-19
-- Includes conversations for test notes to demonstrate system capabilities

-- Create test conversations for our notes
INSERT INTO conversation_v1 (
  id, "ownerId", title, type, typeid, 
  messages, "threadId", "createDate", "updateDate"
)
VALUES
  -- Conversation for PARL paper (Note 10001)
  (10001, 10001, 'Understanding Predictability in RL Agents', 'note'::conversation_type_enum, 10001,
   '[
     {"role": "user", "content": "What is the main contribution of this PARL paper?"},
     {"role": "assistant", "content": "The main contribution of the PARL (Predictability-Aware Reinforcement Learning) paper is introducing a novel framework that makes RL agents more predictable by minimizing the entropy rate of their trajectories. This addresses a critical challenge in deploying RL agents in real-world scenarios where predictability is essential for safety and coordination with humans or other agents."},
     {"role": "user", "content": "How does PARL balance predictability with performance?"},
     {"role": "assistant", "content": "PARL balances predictability and performance through a weighted linear combination of two objectives: the traditional expected reward and the negative entropy rate of the agent''s trajectory. The framework introduces a trade-off parameter that allows practitioners to adjust how much weight to give to predictability versus task performance. The paper shows that agents can maintain near-optimal task performance while achieving substantially lower entropy rates (more predictable behaviors)."},
     {"role": "user", "content": "What are the practical applications mentioned?"},
     {"role": "assistant", "content": "The paper validates PARL on several practical applications including:\n\n1. **Robotics tasks** - Where predictable motion is crucial for human-robot interaction\n2. **MuJoCo control tasks** - Standard benchmarks for continuous control\n3. **Autonomous driving scenarios** - Where predictability is essential for safety\n\nThe results show that PARL agents naturally avoid high-uncertainty regions (like slippery surfaces or stochastic obstacles), making them more suitable for real-world deployment in safety-critical applications."}
   ]'::jsonb,
   NULL, NOW(), NOW()),

  -- Conversation for G1 Graph Learning paper (Note 10002)
  (10002, 10001, 'Graph Reasoning with LLMs: The G1 Approach', 'note'::conversation_type_enum, 10002,
   '[
     {"role": "user", "content": "Why do LLMs struggle with graph-structured data?"},
     {"role": "assistant", "content": "LLMs struggle with graph-structured data for several reasons:\n\n1. **Training data bias** - LLMs are primarily trained on sequential text, not graph representations\n2. **Structural complexity** - Graphs require understanding of non-sequential relationships, cycles, and complex connectivity patterns\n3. **Data scarcity** - There''s limited high-quality graph data compared to text data\n4. **Representation challenges** - Converting graphs to text format loses structural information\n\nThe G1 approach addresses these by using reinforcement learning on synthetic graph tasks to develop latent graph reasoning capabilities."},
     {"role": "user", "content": "What is the Erdős dataset?"},
     {"role": "assistant", "content": "The Erdős dataset is the largest and most diverse graph-theoretic dataset created for this research, featuring:\n\n- **50 different tasks** ranging from simple properties to NP-hard problems\n- **100,000 training instances** and 5,000 test instances\n- **Real-world graph structures** as the foundation\n- **Rule-based reward assignment** eliminating need for human annotation\n\nThis enables scalable RL training for graph reasoning without the typical data limitations."},
     {"role": "user", "content": "How much improvement does G1 achieve?"},
     {"role": "assistant", "content": "G1 achieves substantial improvements:\n\n- **G1-7B**: 66.16% average accuracy on Erdős benchmark\n- **Baseline comparison**: Outperforms Qwen2.5-72B-Instruct which only achieves 47.16%\n- **Model efficiency**: G1-7B is 10x smaller than Qwen2.5-72B but performs significantly better\n- **Zero-shot transfer**: Excels on unseen tasks and real-world applications like citation networks (Cora, PubMed)\n- **Bonus**: RL training on graphs actually enhances general reasoning on unrelated benchmarks like GSM8K and MATH"}
   ]'::jsonb,
   NULL, NOW(), NOW()),

  -- Conversation for Resource Allocation paper (Note 10003)
  (10003, 10001, 'Game Theory Meets RL: Colonel Blotto on Graphs', 'note'::conversation_type_enum, 10003,
   '[
     {"role": "user", "content": "What is the Colonel Blotto Game and how does this paper extend it?"},
     {"role": "assistant", "content": "The Colonel Blotto Game is a classic game theory problem where two players compete to allocate limited resources across multiple battlefields. The player who allocates more resources to a battlefield wins it.\n\nThis paper extends it in several ways:\n1. **Multi-step dynamics** - Players can reallocate resources over multiple rounds\n2. **Graph constraints** - Resources can only move along graph edges\n3. **RL solution approach** - Uses DQN and PPO instead of traditional game theory methods\n\nThis creates the Multi-step Colonel Blotto Game (MCBG) which better models real-world scenarios like cybersecurity or market competition."},
     {"role": "user", "content": "How do they handle the dynamic action spaces?"},
     {"role": "assistant", "content": "The paper introduces an innovative **action-displacement adjacency matrix** approach:\n\n1. At each step, valid actions depend on current resource distribution and graph structure\n2. The matrix systematically generates all valid moves that respect graph constraints\n3. This ensures agents only consider legal actions at each decision point\n4. The approach is mathematically proven correct with formal proofs\n\nThis is a key methodological contribution that enables RL to work effectively with the complex, state-dependent action spaces inherent in graph-based games."}
   ]'::jsonb,
   NULL, NOW(), NOW()),

  -- Conversation for Startup Ideas YouTube video (Note 10004)
  (10004, 10001, 'AI-Enabled Startup Opportunities in 2024', 'note'::conversation_type_enum, 10004,
   '[
     {"role": "user", "content": "What startup ideas are now possible with AI that weren''t before?"},
     {"role": "assistant", "content": "According to the discussion, AI has enabled several previously impractical startup categories:\n\n1. **AI-Native Recruiting Platforms** - Companies like Meror and Apriora can now provide instant, sophisticated candidate assessment that previously required years of manual data labeling\n\n2. **Personalized AI Tutoring** - Startups like Revision Dojo and Speak rival human tutors, unlocking new business models with higher willingness to pay\n\n3. **Full-Stack Service Companies** - AI agents can automate traditionally manual work, making previously low-margin businesses scalable and profitable\n\n4. **Infrastructure/Tooling** - The surge in AI applications has validated companies like Replicate and Ollama that persisted through ''AI winters''"},
     {"role": "user", "content": "Why is now the best time to build according to the speakers?"},
     {"role": "assistant", "content": "The speakers argue this is an unprecedented opportunity because:\n\n1. **Shifting Idea Maze** - Traditional lean startup validation is less relevant; founders should experiment at the AI frontier\n2. **Dropping Intelligence Costs** - AI capabilities are becoming exponentially cheaper\n3. **Platform Neutrality** - There''s still significant room for startups despite big tech dominance\n4. **Rapid Iteration** - Those exploring AI''s capabilities will naturally ''bump into'' transformative ideas\n\nThey recommend following curiosity and experimenting rather than exhaustive customer validation before building."}
   ]'::jsonb,
   NULL, NOW(), NOW()),

  -- Conversation for Zepto startup story (Note 10005)
  (10005, 10001, 'Zepto''s 10-Minute Delivery Revolution', 'note'::conversation_type_enum, 10005,
   '[
     {"role": "user", "content": "How did Zepto become India''s fastest growing startup?"},
     {"role": "assistant", "content": "Based on the video content, Zepto''s rapid growth stems from several key factors:\n\n1. **10-minute delivery promise** - Revolutionized grocery delivery expectations in India\n2. **Dark store model** - Small warehouses in neighborhoods enable ultra-fast delivery\n3. **Perfect timing** - Launched during COVID when demand for quick delivery peaked\n4. **Young founders'' advantage** - Their fresh perspective challenged industry assumptions\n5. **Operational excellence** - Focused intensely on logistics optimization\n\nThey went from startup to unicorn status faster than almost any Indian company by solving a real pain point with exceptional execution."},
     {"role": "user", "content": "What can other startups learn from Zepto?"},
     {"role": "assistant", "content": "Key lessons from Zepto''s success:\n\n1. **Challenge assumptions** - Everyone said 10-minute delivery was impossible\n2. **Start with a focused market** - They began in select Mumbai neighborhoods\n3. **Obsess over operations** - Their tech is good, but operations excellence is their moat\n4. **Move fast during opportunities** - They scaled aggressively during COVID demand surge\n5. **Young founders can win** - Don''t let age be a barrier if you have deep market insights"}
   ]'::jsonb,
   NULL, NOW(), NOW()),

  -- Conversation for YouWoAI welcome document (Note 10008)
  (10006, 10001, 'Getting Started with YouWoAI', 'note'::conversation_type_enum, 10008,
   '[
     {"role": "user", "content": "什么是由我AI？它有什么特别之处？"},
     {"role": "assistant", "content": "由我AI是一个智能笔记和对话系统，具有以下特色功能：\n\n1. **多模态支持** - 可以处理文档、音频、视频等多种内容类型\n2. **智能对话** - 基于您的笔记内容进行深度对话和问答\n3. **知识管理** - 通过文件夹组织您的知识，支持向量搜索\n4. **跨平台** - 支持网页版和移动应用\n5. **AI增强** - 使用先进的语言模型提供智能摘要和洞察\n\n它不仅是笔记工具，更是您的个人AI知识助手。"},
     {"role": "user", "content": "我该如何开始使用？"},
     {"role": "assistant", "content": "开始使用由我AI非常简单：\n\n1. **创建账户** - 注册并登录系统\n2. **创建文件夹** - 按主题组织您的内容\n3. **添加笔记** - 上传文档、录制音频或输入文本\n4. **开始对话** - 点击任何笔记，即可与AI深度交流\n5. **探索功能** - 尝试搜索、导出、分享等高级功能\n\n系统会自动为您的内容生成智能摘要和嵌入向量，让知识检索更加智能高效。"}
   ]'::jsonb,
   NULL, NOW(), NOW()),

  -- Conversation for Product Demo (Note 10009)
  (10007, 10001, 'YouWoAI产品演示要点', 'note'::conversation_type_enum, 10009,
   '[
     {"role": "user", "content": "这个产品演示的主要内容是什么？"},
     {"role": "assistant", "content": "根据音频记录，这个产品演示涵盖了YouWoAI的核心功能展示，包括：\n\n1. **实时语音转文字** - 展示了系统如何准确转录中文语音\n2. **智能对话功能** - 基于转录内容进行智能问答\n3. **多语言支持** - 系统可以处理中英文混合内容\n4. **笔记管理** - 如何组织和检索您的音频笔记\n5. **AI增强功能** - 自动生成摘要和关键信息提取"},
     {"role": "user", "content": "产品的目标用户是谁？"},
     {"role": "assistant", "content": "基于演示内容，YouWoAI的目标用户包括：\n\n1. **知识工作者** - 需要管理大量信息和笔记的专业人士\n2. **学生和研究人员** - 用于学习笔记和研究资料管理\n3. **内容创作者** - 录制想法并转化为结构化内容\n4. **商务人士** - 会议记录和要点总结\n5. **终身学习者** - 构建个人知识库的任何人\n\n产品设计注重易用性，适合各种技术水平的用户。"}
   ]'::jsonb,
   NULL, NOW(), NOW()),

  -- Additional conversation for Replit growth story
  (10008, 10001, 'Replit''s Journey to $100M ARR', 'note'::conversation_type_enum, 10006,
   '[
     {"role": "user", "content": "What were the key factors in Replit''s growth from $10M to $100M ARR?"},
     {"role": "assistant", "content": "Replit''s 10x growth was driven by several strategic moves:\n\n1. **AI Integration** - They were early to integrate AI coding assistants, making coding more accessible\n2. **Community Focus** - Built a vibrant community of creators sharing projects\n3. **Education Market** - Became the go-to platform for coding education\n4. **Viral Features** - Features like instant deployment made projects shareable\n5. **Developer Experience** - Obsessive focus on reducing friction in the coding process\n\nTheir growth accelerated when they shifted from just being an online IDE to becoming a complete development and deployment platform."},
     {"role": "user", "content": "What can B2B SaaS companies learn from Replit?"},
     {"role": "assistant", "content": "Key B2B SaaS lessons from Replit:\n\n1. **Start with consumers/students** - Built grassroots adoption before enterprise\n2. **Make the complex simple** - Their one-click deployment changed the game\n3. **Community as a moat** - User-generated content and templates drive growth\n4. **Freemium done right** - Generous free tier created millions of advocates\n5. **Platform thinking** - Evolved from tool to ecosystem\n6. **AI as accelerant** - Used AI to solve real user problems, not as a gimmick"}
   ]'::jsonb,
   NULL, NOW(), NOW()),

  -- Conversation for Andrew Ng AI talk
  (10009, 10001, 'Building Faster with AI: Andrew Ng''s Insights', 'note'::conversation_type_enum, 10007,
   '[
     {"role": "user", "content": "What are Andrew Ng''s main points about building with AI?"},
     {"role": "assistant", "content": "Andrew Ng emphasizes several key principles for building with AI:\n\n1. **Iterative Development** - Start small, test quickly, and iterate based on results\n2. **Data-Centric AI** - Focus on improving data quality over model complexity\n3. **Domain Expertise Matters** - Combine AI capabilities with deep domain knowledge\n4. **Build vs Buy** - Understand when to use existing models vs training custom ones\n5. **Responsible AI** - Consider ethical implications from the start\n\nHe advocates for a practical, engineering-focused approach rather than chasing the latest research trends."},
     {"role": "user", "content": "How does he suggest teams get started with AI?"},
     {"role": "assistant", "content": "Andrew Ng''s recommended approach for teams:\n\n1. **Start with pilot projects** - Choose bounded problems with clear success metrics\n2. **Use pre-trained models** - Don''t reinvent the wheel, leverage existing solutions\n3. **Focus on deployment** - Getting a model into production teaches more than perfecting it\n4. **Build AI literacy** - Ensure the whole team understands AI basics\n5. **Measure impact** - Track business metrics, not just model accuracy\n6. **Create feedback loops** - Use production data to continuously improve\n\nHe emphasizes that the goal is creating value, not building the most sophisticated system."}
   ]'::jsonb,
   NULL, NOW(), NOW());

-- Add a system conversation
INSERT INTO conversation_v1 (
  id, "ownerId", title, type, typeid, 
  messages, "threadId", "createDate", "updateDate"
)
VALUES
  (10010, 10001, 'Welcome to YouWoAI Test Environment', 'user'::conversation_type_enum, 10001,
   '[
     {"role": "assistant", "content": "Welcome to the YouWoAI test environment! This is a fully functional test system with:\n\n• 9 notes including research papers, YouTube videos, and documents\n• 190 embeddings for semantic search\n• Sample conversations demonstrating various features\n\nFeel free to explore and test any functionality!"},
     {"role": "user", "content": "Great! What can I test here?"},
     {"role": "assistant", "content": "You can test all core YouWoAI features:\n\n1. **Note Management** - Create, edit, and organize notes\n2. **AI Conversations** - Chat with AI about your note content\n3. **Semantic Search** - Find relevant information across all notes\n4. **Multi-language Support** - Test with English and Chinese content\n5. **Different Content Types** - PDFs, audio, video transcripts\n6. **RAG Capabilities** - See how the system retrieves and uses context\n\nAll data is isolated in this test environment on port 5454, so feel free to experiment!"}
   ]''::jsonb,
   NULL, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Then update user to reference the conversation
UPDATE user_v1 
SET "conversationId" = 10010 
WHERE id = 10001;

-- Create index for conversations if not exists
CREATE INDEX IF NOT EXISTS idx_conversation_owner 
ON conversation_v1("ownerId");

CREATE INDEX IF NOT EXISTS idx_conversation_type_typeid 
ON conversation_v1(type, typeid);

-- Verify conversations loaded
SELECT 
  COUNT(*) as total_conversations,
  COUNT(DISTINCT typeid) as unique_notes_with_conversations
FROM conversation_v1
WHERE type = 'note';