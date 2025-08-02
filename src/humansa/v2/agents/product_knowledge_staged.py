"""
Staged Product Knowledge for HUMANSA V2
Stage 1: Compact catalog for search
Stage 2: Full details loaded on demand
"""

import re
from typing import Dict, List, Optional, Tuple

# Stage 1: Compact product catalog for initial search
PRODUCT_CATALOG_COMPACT = """
【诺亚医疗产品目录】184个产品

[儿童营养补剂]
1yegdyu69ofur4j|童年故事复合磷脂酰丝氨酸凝胶糖果|大脑营养,学习期,益智,PS+DHA|健脑益智舒缓情绪
1y8jhcqfx3mwlmo|童年故事DHA88%藻油|高纯度DHA,大脑发育,视力,怀孕|促进大脑视力发育
2y8tg5v81r44lxj|童年故事锌牡蛎橙复合饮液|挑食,免疫力,生长发育|改善挑食增强免疫
3yev5idphv8k2gk|童年故事维生素D3片|维生素D,钙吸收,长高|促进钙吸收助力长高
1yffuz68gwvvx34|金蓓高γ-氨基丁酸胶原蛋白肽|GABA助眠,胶原蛋白,骨骼营养|双效协同骨骼健康深度睡眠
[继续其他产品...]

[科学备孕]
1yapa5hofyjozg0|科学备孕套餐达巢+保绅|备孕,维生素B族,男性活力|女性B族男性活力双补
2yffpqak4k3tzgg|保绅活力1号|男性,活力,前列腺,夜尿|提升男性活力改善前列腺
[继续其他产品...]

[口腔健康]
36kdf9a59zb2m8w|舒敏牙膏|抗敏感,舒缓,牙釉质|缓解敏感修复牙釉质
[继续其他产品...]
"""

# Stage 2: Detailed product information (loaded on demand)
PRODUCT_DETAILS = {
    "1yegdyu69ofur4j": {
        "name": "童年故事复合磷脂酰丝氨酸凝胶糖果",
        "full_desc": "本品是一款专为儿童设计的营养补充品，具有健脑益智，帮助儿童舒缓情绪，原装进口，成分安全，采用凝胶糖果形式，口感佳，儿童更易接受。",
        "usage": "每日1-2粒，直接咀嚼食用",
        "ingredients": "每粒含100mg磷脂酰丝氨酸（PS）和50mg DHA",
        "restrictions": "本品添加新资源食品成分：DHA藻油、磷脂酰丝氨酸（PS）。推荐食用量限制：DHA藻油：≤300毫克/天（以纯DHA计）、磷脂酰丝氨酸：≤600毫克/天。禁忌人群：不适用于婴幼儿",
        "marketing": "聪明宝宝的小零食、含PS+DHA双效成分、磷脂酰丝氨酸配方、Omega-3营养补充"
    },
    "1y8jhcqfx3mwlmo": {
        "name": "童年故事DHA88%藻油宝宝儿童婴幼儿dha成人孕妇60粒",
        "full_desc": "✅ 高纯度DHA：88%藻油DHA，婴幼儿可食用\n✅ 全年龄段适用：宝宝、儿童、孕妇、成人均可补充\n✅ 安全认证：美国进口，无重金属污染风险\n促进大脑、视力发育，提升专注力",
        "usage": "每日1粒，直接口服或牙签刺破融入食物中",
        "ingredients": "配料成分：DHA藻油(含88%DHA)、木薯淀粉、果胶、水、罗汉果甜苷。营养成分表：能量3936千焦(kJ)、蛋白质0克(g)、脂肪99.9克(g)",
        "restrictions": "适用人群：婴幼儿、儿童、孕妇、成人",
        "marketing": "过敏宝宝适用、专注力提升、用脑疲劳缓解"
    },
    # ... 其他产品详情
}

def extract_product_id_from_url(url: str) -> str:
    """Extract product ID from URL"""
    # https://shop137071643.m.youzan.com/v2/goods/1yegdyu69ofur4j
    match = re.search(r'/goods/([a-z0-9]+)', url)
    return match.group(1) if match else ""

def parse_compact_catalog() -> Dict[str, List[Dict]]:
    """Parse compact catalog into categories"""
    categories = {}
    current_category = ""
    
    lines = PRODUCT_CATALOG_COMPACT.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('【'):
            continue
            
        if line.startswith('[') and line.endswith(']'):
            current_category = line[1:-1]
            categories[current_category] = []
        elif '|' in line and current_category:
            parts = line.split('|')
            if len(parts) >= 4:
                product = {
                    'id': parts[0],
                    'name': parts[1],
                    'tags': parts[2].split(','),
                    'brief': parts[3]
                }
                categories[current_category].append(product)
    
    return categories

def get_full_product_url(product_id: str) -> str:
    """Reconstruct full URL from product ID"""
    return f"https://shop137071643.m.youzan.com/v2/goods/{product_id}"

class StagedProductKnowledge:
    """Two-stage product knowledge system"""
    
    def __init__(self):
        self.catalog = parse_compact_catalog()
        self.details = PRODUCT_DETAILS
        self.all_products = []
        
        # Flatten all products for search
        for category, products in self.catalog.items():
            for product in products:
                product['category'] = category
                self.all_products.append(product)
    
    def search_products_stage1(self, query: str, limit: int = 10) -> List[Dict]:
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
            
            # Brief description matching
            if query_lower in product['brief'].lower():
                score += 6
            
            # Category matching
            if query_lower in product['category'].lower():
                score += 3
            
            if score > 0:
                results.append({
                    **product,
                    'score': score
                })
        
        # Sort by relevance
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def get_product_details_stage2(self, product_ids: List[str]) -> Dict[str, Dict]:
        """Stage 2: Get full details for selected products"""
        details = {}
        
        for pid in product_ids:
            if pid in self.details:
                details[pid] = {
                    **self.details[pid],
                    'url': get_full_product_url(pid)
                }
            else:
                # If details not in cache, construct from catalog
                for product in self.all_products:
                    if product['id'] == pid:
                        details[pid] = {
                            'name': product['name'],
                            'brief': product['brief'],
                            'tags': product['tags'],
                            'category': product['category'],
                            'url': get_full_product_url(pid),
                            'note': '详细信息暂未加载'
                        }
                        break
        
        return details
    
    def get_categories_with_filter(self, category: str) -> List[Dict]:
        """Get all products in a category"""
        return self.catalog.get(category, [])
    
    def get_catalog_for_prompt(self) -> str:
        """Get compact catalog for initial prompt injection"""
        return PRODUCT_CATALOG_COMPACT
    
    def get_token_estimate(self) -> Dict[str, int]:
        """Estimate token usage"""
        catalog_size = len(PRODUCT_CATALOG_COMPACT)
        details_size = sum(len(str(d)) for d in self.details.values())
        
        return {
            'stage1_catalog': catalog_size // 4,  # Compact catalog tokens
            'stage2_per_product': details_size // len(self.details) // 4 if self.details else 0,
            'total_products': len(self.all_products)
        }

# Example of how to add more product details
def load_product_details_from_csv(csv_path: str):
    """Load full product details from CSV and populate PRODUCT_DETAILS"""
    import csv
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        next(f)  # Skip header
        csv_reader = csv.reader(f)
        
        for row in csv_reader:
            if len(row) >= 8 and row[2]:  # Has URL
                product_id = extract_product_id_from_url(row[2])
                if product_id:
                    PRODUCT_DETAILS[product_id] = {
                        'name': row[1].strip(),
                        'full_desc': row[3].strip(),
                        'usage': row[4].strip(),
                        'ingredients': row[5].strip(),
                        'restrictions': row[6].strip(),
                        'marketing': row[7].strip() if len(row) > 7 else ""
                    }