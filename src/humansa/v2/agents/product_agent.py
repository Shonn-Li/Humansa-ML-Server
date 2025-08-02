"""
Product Recommendation Agent for Humansa V2
Based on Noah Medical Supplement SubAgent System
Uses two-stage loading: compact catalog + detailed info on demand
"""

import logging
import json
import asyncio
from typing import Dict, Any, AsyncGenerator, List, Set, Optional
from datetime import datetime
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool
from llama_index.core.agent import ReActAgent

logger = logging.getLogger(__name__)

# Import generated data
try:
    import sys
    sys.path.append('data')
    from product_knowledge_generated import PRODUCT_CATALOG_COMPACT, PRODUCT_DETAILS
except ImportError:
    # Fallback - will need to load from file
    PRODUCT_CATALOG_COMPACT = ""
    PRODUCT_DETAILS = {}


class ProductAgent:
    """
    Product Agent using staged loading pattern from Noah Medical system
    Stage 1: Compact catalog for search (~5K tokens)
    Stage 2: Full details loaded on demand
    """
    
    def __init__(self, llm: LLM, use_multi_expert: bool = False):
        self.llm = llm
        self.use_multi_expert = use_multi_expert
        self.selected_products: Set[str] = set()
        
        # Load catalog if not already loaded
        if not PRODUCT_CATALOG_COMPACT:
            self._load_catalog_from_file()
        
        # Parse catalog
        self._parse_catalog()
        
        # Initialize agent
        self._initialize_agent()
        
        logger.info(f"✅ Initialized ProductAgent with {len(self.all_products)} products (staged loading)")
    
    def _load_catalog_from_file(self):
        """Load catalog from generated files"""
        try:
            with open('data/product_catalog_compact.txt', 'r', encoding='utf-8') as f:
                global PRODUCT_CATALOG_COMPACT
                PRODUCT_CATALOG_COMPACT = f.read()
                
            with open('data/product_details_full.json', 'r', encoding='utf-8') as f:
                global PRODUCT_DETAILS
                PRODUCT_DETAILS = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load product data: {e}")
    
    def _parse_catalog(self):
        """Parse compact catalog"""
        self.catalog = {}
        self.all_products = []
        
        current_category = ""
        lines = PRODUCT_CATALOG_COMPACT.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('【'):
                continue
                
            if line.startswith('[') and line.endswith(']'):
                current_category = line[1:-1]
                self.catalog[current_category] = []
            elif '|' in line and current_category:
                parts = line.split('|')
                if len(parts) >= 4:
                    product = {
                        'id': parts[0],
                        'name': parts[1],
                        'tags': parts[2].split(','),
                        'brief': parts[3],
                        'category': current_category
                    }
                    self.catalog[current_category].append(product)
                    self.all_products.append(product)
    
    def _initialize_agent(self):
        """Initialize ReAct agent with tools"""
        tools = [
            FunctionTool.from_defaults(
                fn=self._search_products,
                name="search_products",
                description="搜索产品：根据症状/需求/标签查找相关产品（返回简要信息）"
            ),
            FunctionTool.from_defaults(
                fn=self._get_product_details,
                name="get_product_details",
                description="获取产品详情：用法用量、成分、禁忌、营销描述等完整信息"
            ),
            FunctionTool.from_defaults(
                fn=self._match_products,
                name="match_products",
                description="智能匹配：基于用户需求匹配最相关的产品并返回详情"
            ),
            FunctionTool.from_defaults(
                fn=self._check_product_safety,
                name="check_safety",
                description="安全检查：验证产品是否适合特定人群，检查禁忌症"
            )
        ]
        
        # Use product matching expert prompt from Noah system
        system_prompt = f"""你是诺亚医疗的产品匹配专家Dr. Matcher，负责从产品库中匹配用户需求。

{PRODUCT_CATALOG_COMPACT}

**专业职责**:
1. **需求匹配分析**：首先分析用户的核心健康需求和症状
2. **产品相关性判断**：仅推荐与用户需求直接相关的产品
   - 检查产品功效与用户症状的匹配度
   - 检查产品适用人群与用户情况的符合度
   - 严格排除不相关产品（如：失眠患者不推荐备孕产品，儿童不推荐成人产品）
3. **信息整理**：整理匹配产品的完整信息

**相关性判断标准**:
- 产品功效必须直接针对用户的症状或健康目标
- 产品适用人群必须与用户年龄、性别、健康状况相符
- 只推荐与用户需求高度相关的产品，宁可缺少也不要不相关

**工作流程**:
1. 使用search_products搜索相关产品
2. 选择最相关的2-3个产品
3. 使用get_product_details获取完整信息
4. 提供包含用法用量和注意事项的专业推荐

**重要**:
- 搜索阶段只有产品ID、名称、标签和简介
- 必须调用get_product_details才能获得用法、成分、禁忌
- 产品链接格式：https://shop137071643.m.youzan.com/v2/goods/{{product_id}}"""
        
        # Use new ReActAgent API (llama-index 0.13.0)
        self.agent = ReActAgent(
            name="ProductAgent",
            description="Product recommendation specialist for health supplements and medical devices",
            tools=tools,
            llm=self.llm,
            system_prompt=system_prompt,
            verbose=True
        )
    
    async def _search_products(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Stage 1: Search in compact catalog"""
        query_lower = query.lower()
        results = []
        
        for product in self.all_products:
            score = 0
            
            # Name matching
            if query_lower in product['name'].lower():
                score += 10
            
            # Tag matching
            for tag in product['tags']:
                if query_lower in tag.lower():
                    score += 8
                if tag.lower() in query_lower:
                    score += 5
            
            # Brief matching
            if query_lower in product['brief'].lower():
                score += 6
            
            # Category matching
            if query_lower in product['category'].lower():
                score += 3
            
            if score > 0:
                results.append({
                    'id': product['id'],
                    'name': product['name'],
                    'category': product['category'],
                    'tags': product['tags'],
                    'brief': product['brief'],
                    'score': score
                })
        
        # Sort by relevance
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    async def _get_product_details(self, product_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Stage 2: Get full details for selected products"""
        details = {}
        
        for pid in product_ids:
            self.selected_products.add(pid)
            
            if pid in PRODUCT_DETAILS:
                full_details = PRODUCT_DETAILS[pid]
                details[pid] = {
                    'id': pid,
                    'name': full_details['name'],
                    'url': f"https://shop137071643.m.youzan.com/v2/goods/{pid}",
                    'effectiveness': full_details['full_desc'],
                    'usage': full_details['usage'],
                    'ingredients': full_details['ingredients'],
                    'restrictions': full_details['restrictions'],
                    'marketing': full_details['marketing']
                }
            else:
                details[pid] = {
                    'id': pid,
                    'error': '产品详情暂未录入系统'
                }
        
        return details
    
    async def _match_products(self, user_needs: str) -> Dict[str, Any]:
        """Intelligent product matching with auto detail loading"""
        # Search for products
        search_results = await self._search_products(user_needs, limit=5)
        
        if not search_results:
            return {
                'matches': [],
                'message': '未找到相关产品'
            }
        
        # Auto-load details for top 3
        top_ids = [p['id'] for p in search_results[:3]]
        details = await self._get_product_details(top_ids)
        
        # Build matches following Noah system format
        matches = []
        for pid, detail in details.items():
            if 'error' not in detail:
                # Find category from search results
                category = next((p['category'] for p in search_results if p['id'] == pid), '')
                
                matches.append({
                    'category': category,
                    'name': detail['name'],
                    'effectiveness': detail['effectiveness'],
                    'ingredients': detail['ingredients'],
                    'usage': detail['usage'],
                    'link': detail['url'],
                    'restrictions': detail['restrictions'],
                    'rationale': f"基于您的需求'{user_needs}'，此产品功效匹配"
                })
        
        return {
            'matches': matches,
            'similar_products': [p['name'] for p in search_results[3:]]
        }
    
    async def _check_product_safety(self, product_id: str, user_info: str) -> Dict[str, Any]:
        """Check product safety for specific user"""
        # Get product details
        details = await self._get_product_details([product_id])
        
        if product_id not in details:
            return {'error': '产品不存在'}
        
        product = details[product_id]
        
        # Check contraindications
        contraindications = []
        warnings = []
        
        restrictions = product.get('restrictions', '').lower()
        user_info_lower = user_info.lower()
        
        # Common checks
        if '婴幼儿' in restrictions and ('婴儿' in user_info_lower or '幼儿' in user_info_lower):
            contraindications.append('本产品不适用于婴幼儿')
        
        if '孕妇' in restrictions and '孕' in user_info_lower:
            contraindications.append('孕妇慎用或禁用')
        
        if '过敏' in user_info_lower:
            warnings.append('请仔细查看成分表，避免过敏原')
        
        # Build safety assessment
        return {
            'product_safety': {
                'contraindications': contraindications,
                'dosage_warnings': f"请严格按照用法用量服用：{product.get('usage', '')}",
                'interaction_risks': warnings
            },
            'overall_assessment': '可以使用' if not contraindications else '不建议使用'
        }
    
    # Optional multi-expert consultation
    async def _multi_expert_analysis(self, query: str) -> Optional[Dict[str, Any]]:
        """Run multi-expert analysis if enabled"""
        if not self.use_multi_expert:
            return None
        
        try:
            # Simplified multi-expert for product context
            tasks = []
            
            # Demand analysis
            demand_prompt = f"""分析用户需求：{query}
输出JSON格式：
{{"demands": [{{"category": "核心需求", "details": "...", "knowledge_match": "..."}}]}}"""
            
            # Risk assessment 
            risk_prompt = f"""评估产品使用风险：{query}
输出JSON格式：
{{"primary_risk": {{"level": "低/中/高", "description": "..."}}}}"""
            
            tasks.append(self.llm.acomplete(demand_prompt))
            tasks.append(self.llm.acomplete(risk_prompt))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            return {
                'demand_analysis': str(results[0].text) if not isinstance(results[0], Exception) else "",
                'risk_assessment': str(results[1].text) if not isinstance(results[1], Exception) else ""
            }
            
        except Exception as e:
            logger.error(f"Multi-expert analysis failed: {e}")
            return None
    
    async def process_query(
        self, 
        query: str, 
        context: Dict[str, Any], 
        stream: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process product queries with staged loading"""
        
        try:
            # Optional multi-expert analysis
            expert_insights = await self._multi_expert_analysis(query) if self.use_multi_expert else None
            
            # Enhance query with insights
            enhanced_query = query
            if expert_insights:
                enhanced_query = f"{query}\n\n专家分析：{json.dumps(expert_insights, ensure_ascii=False)[:500]}"
            
            if stream:
                # Use run method for new API
                response_handler = self.agent.run(enhanced_query)
                
                # Handle the WorkflowHandler response
                result = await response_handler
                
                # Extract response text
                if hasattr(result, 'response'):
                    response_text = str(result.response)
                elif hasattr(result, 'output'):
                    response_text = str(result.output)
                else:
                    response_text = str(result)
                
                # Yield complete response
                yield {
                    "type": "content",
                    "chunk": response_text
                }
                
                # Add footer
                yield {
                    "type": "content",
                    "chunk": f"\n\n💡 已为您筛选{len(self.selected_products)}个相关产品"
                }
            else:
                # Non-streaming - use run method
                response_handler = self.agent.run(enhanced_query)
                result = await response_handler
                
                # Extract response text
                if hasattr(result, 'response'):
                    response_text = str(result.response)
                elif hasattr(result, 'output'):
                    response_text = str(result.output)
                else:
                    response_text = str(result)
                
                yield {
                    "type": "content",
                    "chunk": response_text
                }
                
        except Exception as e:
            logger.error(f"Error in ProductAgent: {e}")
            yield {
                "type": "error",
                "chunk": "产品推荐服务暂时不可用，请稍后再试。"
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get agent statistics"""
        return {
            'total_products': len(self.all_products),
            'categories': list(self.catalog.keys()),
            'selected_products': len(self.selected_products),
            'token_usage': {
                'catalog': len(PRODUCT_CATALOG_COMPACT) // 4,
                'per_product_detail': 200,
                'current_total': len(PRODUCT_CATALOG_COMPACT) // 4 + (len(self.selected_products) * 200)
            },
            'multi_expert_enabled': self.use_multi_expert
        }


# Convenience function
def create_product_agent(llm: LLM, use_multi_expert: bool = False) -> ProductAgent:
    """Create product agent instance"""
    return ProductAgent(llm, use_multi_expert)