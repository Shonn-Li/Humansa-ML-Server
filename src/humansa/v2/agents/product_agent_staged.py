"""
Staged Product Agent for HUMANSA V2
Stage 1: Search with compact catalog (5K tokens)
Stage 2: Load full details only for selected products
"""

import logging
import json
from typing import Dict, Any, AsyncGenerator, List, Set
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
    # Fallback to inline data
    from .product_knowledge_staged import PRODUCT_CATALOG_COMPACT, PRODUCT_DETAILS


class ProductAgentStaged:
    """
    Two-stage product agent:
    1. Initial search uses compact catalog (5K tokens)
    2. Details loaded only for selected products
    """
    
    def __init__(self, llm: LLM):
        self.llm = llm
        self.selected_products: Set[str] = set()  # Track which products have been selected
        
        # Parse catalog
        self._parse_catalog()
        
        # Initialize agent
        self._initialize_agent()
        
        logger.info(f"✅ Initialized ProductAgentStaged with {len(self.all_products)} products")
    
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
        """Initialize ReAct agent with staged tools"""
        tools = [
            FunctionTool.from_defaults(
                fn=self._search_products_stage1,
                name="search_products",
                description="搜索产品目录，返回匹配的产品列表（仅基本信息）"
            ),
            FunctionTool.from_defaults(
                fn=self._get_product_details_stage2,
                name="get_product_details",
                description="获取选中产品的完整信息：用法、成分、禁忌、营销描述等"
            ),
            FunctionTool.from_defaults(
                fn=self._filter_by_category,
                name="filter_by_category",
                description="按类别筛选产品，如：儿童营养补剂、科学备孕等"
            ),
            FunctionTool.from_defaults(
                fn=self._recommend_products,
                name="recommend_products",
                description="基于症状推荐产品组合，并自动加载详情"
            )
        ]
        
        # Compact system prompt with catalog
        system_prompt = f"""你是诺亚医疗产品推荐专家。

{PRODUCT_CATALOG_COMPACT}

工作流程：
1. 先用search_products搜索相关产品（基于简要信息）
2. 选出最相关的2-3个产品
3. 用get_product_details获取这些产品的完整信息
4. 基于完整信息给出专业推荐

重要：
- 搜索阶段只有产品ID、名称、标签和简介
- 必须调用get_product_details才能获得用法、成分、禁忌
- 推荐时必须包含用法用量和注意事项
- 产品链接格式：https://shop137071643.m.youzan.com/v2/goods/{{product_id}}"""
        
        self.agent = ReActAgent.from_tools(
            tools=tools,
            llm=self.llm,
            system_prompt=system_prompt,
            verbose=True
        )
    
    async def _search_products_stage1(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
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
    
    async def _get_product_details_stage2(self, product_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Stage 2: Get full details for selected products"""
        details = {}
        
        for pid in product_ids:
            self.selected_products.add(pid)  # Track selection
            
            if pid in PRODUCT_DETAILS:
                # Get full details from database
                full_details = PRODUCT_DETAILS[pid]
                details[pid] = {
                    'id': pid,
                    'name': full_details['name'],
                    'url': f"https://shop137071643.m.youzan.com/v2/goods/{pid}",
                    'description': full_details['full_desc'],
                    'usage': full_details['usage'],
                    'ingredients': full_details['ingredients'],
                    'restrictions': full_details['restrictions'],
                    'marketing': full_details['marketing']
                }
            else:
                # Product not in details database
                details[pid] = {
                    'id': pid,
                    'error': '产品详情暂未录入系统'
                }
        
        return details
    
    async def _filter_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Filter products by category"""
        if category in self.catalog:
            return self.catalog[category]
        
        # Fuzzy match category
        for cat_name, products in self.catalog.items():
            if category.lower() in cat_name.lower():
                return products
        
        return []
    
    async def _recommend_products(self, symptoms: str) -> Dict[str, Any]:
        """Recommend products and auto-load details"""
        # First search for products
        search_results = await self._search_products_stage1(symptoms, limit=5)
        
        if not search_results:
            return {
                'products': [],
                'message': '未找到相关产品'
            }
        
        # Get top 3 product IDs
        top_ids = [p['id'] for p in search_results[:3]]
        
        # Auto-load details for top products
        details = await self._get_product_details_stage2(top_ids)
        
        # Build recommendations
        recommendations = {
            'search_results': search_results[:3],
            'detailed_products': details,
            'usage_summary': []
        }
        
        # Extract usage summary
        for pid, detail in details.items():
            if 'usage' in detail:
                recommendations['usage_summary'].append({
                    'product': detail['name'],
                    'usage': detail['usage']
                })
        
        return recommendations
    
    async def process_query(
        self, 
        query: str, 
        context: Dict[str, Any], 
        stream: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process queries with two-stage approach"""
        
        try:
            if stream:
                # Stream response
                response_stream = self.agent.stream_chat(query)
                
                async for chunk in response_stream.async_response_gen():
                    if chunk:
                        yield {
                            "type": "content",
                            "chunk": str(chunk)
                        }
                
                # Add footer with selected products
                if self.selected_products:
                    yield {
                        "type": "content",
                        "chunk": f"\n\n📦 已查看{len(self.selected_products)}个产品详情"
                    }
            else:
                # Non-streaming
                response = self.agent.chat(query)
                yield {
                    "type": "content",
                    "chunk": response.response
                }
                
        except Exception as e:
            logger.error(f"Error in ProductAgentStaged: {e}")
            yield {
                "type": "error",
                "chunk": "产品推荐服务暂时不可用，请稍后再试。"
            }
    
    def get_token_usage_estimate(self) -> Dict[str, Any]:
        """Get token usage estimate"""
        catalog_tokens = len(PRODUCT_CATALOG_COMPACT) // 4
        avg_detail_tokens = 200  # Estimated per product
        
        return {
            'stage1_catalog_tokens': catalog_tokens,
            'stage2_per_product_tokens': avg_detail_tokens,
            'total_products': len(self.all_products),
            'selected_products': len(self.selected_products),
            'estimated_total': catalog_tokens + (len(self.selected_products) * avg_detail_tokens)
        }


# Factory function
def create_product_agent_staged(llm: LLM) -> ProductAgentStaged:
    """Create staged product agent instance"""
    return ProductAgentStaged(llm)