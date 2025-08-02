#!/usr/bin/env python3
"""
Generate staged product data from CSV
Stage 1: Compact catalog
Stage 2: Full details dictionary
"""

import csv
import json
import re

def extract_product_id(url):
    """Extract product ID from URL"""
    match = re.search(r'/goods/([a-z0-9]+)', url)
    return match.group(1) if match else ""

# Read CSV
csv_path = 'data/noah_supplements.csv'
categories = {}
product_details = {}

with open(csv_path, 'r', encoding='utf-8') as f:
    next(f)  # Skip header
    
    current_category = ""
    csv_reader = csv.reader(f)
    
    for row in csv_reader:
        if len(row) >= 8:
            # Get category
            if row[0].strip():
                current_category = row[0].strip()
                if current_category not in categories:
                    categories[current_category] = []
            
            # Process product
            if row[1].strip() and row[2].strip() and current_category:
                name = row[1].strip()
                url = row[2].strip()
                product_id = extract_product_id(url)
                
                if not product_id:
                    continue
                
                # Parse tags (limit to 4-5 key ones)
                tags_str = row[7].strip() if len(row) > 7 else ""
                all_tags = [tag.strip().strip('"') for tag in tags_str.split('、') if tag.strip()]
                
                # Prioritize important tags
                priority_keywords = ['DHA', '维生素', '钙', '免疫', '睡眠', '备孕', '儿童', '益智', '护眼', '长高']
                key_tags = []
                
                # First add priority tags
                for tag in all_tags:
                    if any(kw in tag for kw in priority_keywords) and len(key_tags) < 4:
                        key_tags.append(tag)
                
                # Then add others
                for tag in all_tags:
                    if tag not in key_tags and len(key_tags) < 4:
                        key_tags.append(tag)
                
                # Extract brief description (first key benefit)
                desc = row[3].strip()
                if '功效' in desc:
                    brief = desc.split('功效')[1].split('。')[0].strip('：').strip()[:30]
                elif '本品' in desc:
                    brief = desc.split('本品')[1].split('，')[0].strip()[:30]
                else:
                    brief = desc.split('。')[0][:30]
                
                # Add to catalog
                catalog_entry = f"{product_id}|{name}|{','.join(key_tags)}|{brief}"
                categories[current_category].append(catalog_entry)
                
                # Add to details
                product_details[product_id] = {
                    'name': name,
                    'full_desc': row[3].strip(),
                    'usage': row[4].strip(),
                    'ingredients': row[5].strip(),
                    'restrictions': row[6].strip(),
                    'marketing': tags_str
                }

# Generate Stage 1: Compact Catalog
catalog_output = "【诺亚医疗产品目录】184个产品\n\n"

for cat_name, products in categories.items():
    if products and cat_name not in ['信息详情页搜索对应内容，截图贴到对应的表格位置，由ai读取）"']:
        catalog_output += f"[{cat_name}]\n"
        for product in products:
            catalog_output += f"{product}\n"
        catalog_output += "\n"

# Save outputs
with open('data/product_catalog_compact.txt', 'w', encoding='utf-8') as f:
    f.write(catalog_output)

with open('data/product_details_full.json', 'w', encoding='utf-8') as f:
    json.dump(product_details, f, ensure_ascii=False, indent=2)

# Generate Python file
python_output = f'''"""
Auto-generated staged product knowledge
Generated from: {csv_path}
"""

# Stage 1: Compact catalog for search
PRODUCT_CATALOG_COMPACT = """
{catalog_output}"""

# Stage 2: Full product details
PRODUCT_DETAILS = {json.dumps(product_details, ensure_ascii=False, indent=4)}
'''

with open('data/product_knowledge_generated.py', 'w', encoding='utf-8') as f:
    f.write(python_output)

# Statistics
total_products = sum(len(prods) for prods in categories.values())
catalog_size = len(catalog_output)
details_size = len(json.dumps(product_details))

print(f"Generated staged product data:")
print(f"  Total products: {total_products}")
print(f"  Categories: {len(categories)}")
print(f"  Stage 1 catalog: {catalog_size:,} chars (~{catalog_size//4:,} tokens)")
print(f"  Stage 2 details: {details_size:,} chars (~{details_size//4:,} tokens)")
print(f"  Average per product in catalog: {catalog_size//total_products if total_products > 0 else 0} chars")
print(f"\nFiles created:")
print(f"  - data/product_catalog_compact.txt")
print(f"  - data/product_details_full.json")
print(f"  - data/product_knowledge_generated.py")

# Show sample
print("\nSample catalog entries:")
for cat, prods in list(categories.items())[:2]:
    if prods:
        print(f"\n[{cat}]")
        for p in prods[:3]:
            print(f"  {p}")