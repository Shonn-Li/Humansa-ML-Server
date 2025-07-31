"""
Product Recommendation Agent for Humansa V2
Specialized in health products, supplements, and medical equipment recommendations
"""

import logging
from typing import Dict, Any, AsyncGenerator, Optional
from llama_index.core.llms import LLM

logger = logging.getLogger(__name__)


class ProductAgent:
    """Agent specialized in product recommendations and health shopping guidance."""
    
    def __init__(self, llm: LLM):
        self.llm = llm
        self.system_prompt = """
你是诺亚新舟健康商城的产品推荐专家。你的职责是：

1. 根据用户的健康需求推荐合适的产品
2. 介绍产品的功效、适用人群和使用方法
3. 提供价格信息和优惠活动
4. 引导用户到健康商城购买

产品类别：
- 营养保健：维生素、矿物质、益生菌、鱼油等
- 医疗器械：血压计、血糖仪、制氧机、体温计等
- 护肤美容：医美面膜、抗衰产品、美白精华等
- 中医养生：西洋参、灵芝、燕窝、枸杞等
- 母婴健康：孕妇营养品、婴儿用品、产后恢复等

推荐原则：
1. 根据用户症状或需求推荐相关产品
2. 优先推荐有优惠活动的产品
3. 提供产品搭配建议（如套餐）
4. 强调产品的品质和安全性
5. 适时引导到健康商城：#小程序://诺亚新舟医疗/t5ZpOWu0UyRtEFl

注意事项：
- 不能替代医生诊断，保健品不能治病
- 提醒用户遵医嘱使用
- 特殊人群（孕妇、儿童）需特别提醒
"""
        
    async def process_query(self, query: str, context: Dict[str, Any], stream: bool = True) -> AsyncGenerator[Dict[str, Any], None]:
        """Process product-related queries."""
        
        # Check for product-related keywords
        product_keywords = ['产品', '保健品', '维生素', '血压计', '血糖仪', '护肤', '美容', 
                           '中医', '养生', '母婴', '孕妇', '营养品', '购买', '推荐', '商城',
                           '价格', '优惠', '折扣', '套餐']
        
        is_product_query = any(keyword in query.lower() for keyword in product_keywords)
        
        if not is_product_query:
            # Check if asking about specific health issues that might need products
            health_keywords = ['失眠', '疲劳', '免疫力', '皮肤', '血压', '血糖', '记忆力', '关节',
                             '美白', '抗衰', '补钙', '补铁', '增强体质']
            is_health_query = any(keyword in query.lower() for keyword in health_keywords)
            
            if not is_health_query:
                yield {
                    "type": "content",
                    "chunk": "这个问题不在我的专业范围内。我是产品推荐专家，可以帮您推荐健康产品、保健品、医疗器械等。"
                }
                return
        
        # Build context for product recommendation
        prompt = f"""{self.system_prompt}

用户查询：{query}

请根据用户需求推荐合适的产品，包括：
1. 产品名称和类别
2. 主要功效和适用人群
3. 价格信息（如有优惠请标注）
4. 使用建议
5. 购买链接

如果用户有特定健康问题，请推荐相关的产品组合。
"""
        
        try:
            if stream:
                # Stream response
                response = await self.llm.astream_complete(prompt)
                async for chunk in response:
                    if chunk.delta:
                        yield {
                            "type": "content", 
                            "chunk": chunk.delta
                        }
            else:
                # Non-streaming response
                response = await self.llm.acomplete(prompt)
                yield {
                    "type": "content",
                    "chunk": response.text
                }
                
        except Exception as e:
            logger.error(f"Error in ProductAgent: {e}")
            yield {
                "type": "error",
                "chunk": "抱歉，产品推荐服务暂时出现问题。请稍后再试或直接访问我们的健康商城。"
            }
    
    def get_product_categories(self) -> Dict[str, Any]:
        """Get available product categories."""
        return {
            "categories": [
                {
                    "id": "CAT1",
                    "name": "营养保健",
                    "description": "维生素、矿物质、保健品",
                    "popular_products": ["维生素D3", "深海鱼油", "益生菌"]
                },
                {
                    "id": "CAT2", 
                    "name": "医疗器械",
                    "description": "家用医疗设备和监测器材",
                    "popular_products": ["血压计", "血糖仪", "制氧机"]
                },
                {
                    "id": "CAT3",
                    "name": "护肤美容",
                    "description": "医美级护肤品",
                    "popular_products": ["医美面膜", "美白精华", "抗衰面霜"]
                },
                {
                    "id": "CAT4",
                    "name": "中医养生",
                    "description": "中药材、养生茶饮",
                    "popular_products": ["西洋参", "灵芝孢子粉", "燕窝"]
                },
                {
                    "id": "CAT5",
                    "name": "母婴健康",
                    "description": "孕妇及婴幼儿专用产品",
                    "popular_products": ["孕妇DHA", "婴儿益生菌", "产后修复"]
                }
            ]
        }