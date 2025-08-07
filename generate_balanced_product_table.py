#!/usr/bin/env python3
"""
Generate balanced product table from CSV
Includes essential information while optimizing tokens
"""

import csv
import json

# Read CSV and create balanced structure
csv_path = 'data/noah_supplements.csv'
categories = {}
all_products = []

with open(csv_path, 'r', encoding='utf-8') as f:
    next(f)  # Skip header
    
    current_category = ""
    csv_reader = csv.reader(f)
    
    for row in csv_reader:
        if len(row) >= 8:
            # Check for category
            if row[0].strip():
                current_category = row[0].strip()
                if current_category not in categories:
                    categories[current_category] = []
            
            # Check for product
            if row[1].strip() and current_category:
                # Extract fields
                name = row[1].strip()
                desc_full = row[3].strip()
                usage_full = row[4].strip()
                ingredients_full = row[5].strip()
                restrictions_full = row[6].strip()
                tags_str = row[7].strip() if len(row) > 7 else ""
                
                # Extract key efficacy points
                efficacy = ""
                if '功效' in desc_full:
                    efficacy_parts = desc_full.split('功效')[1].split('。')[0]
                    efficacy = efficacy_parts.strip('：').strip()[:100]
                elif '本品' in desc_full:
                    efficacy = desc_full.split('本品')[1].split('。')[0][:100]
                else:
                    # Get first meaningful sentence
                    sentences = desc_full.split('。')
                    efficacy = sentences[0][:100] if sentences else desc_full[:100]
                
                # Extract dosage
                usage = ""
                if '用量' in usage_full:
                    usage_parts = usage_full.split('用量')[1].split('。')[0]
                    usage = usage_parts.strip('：').strip()[:80]
                elif '每日' in usage_full:
                    usage = usage_full.split('。')[0][:80]
                else:
                    usage = usage_full.split('。')[0][:80] if usage_full else ""
                
                # Extract key ingredients
                ingredients = ""
                if '含' in ingredients_full:
                    # Extract content info
                    ingredients = ingredients_full[:80]
                elif 'mg' in ingredients_full or 'g' in ingredients_full:
                    ingredients = ingredients_full[:80]
                
                # Extract restrictions
                restrictions = ""
                if '禁忌' in restrictions_full:
                    restrictions = restrictions_full.split('禁忌')[1].strip('：').strip()[:60]
                elif '不适用' in restrictions_full:
                    restrictions = restrictions_full[:60]
                elif '注意' in restrictions_full:
                    restrictions = restrictions_full.split('注意')[1].strip('：').strip()[:60]
                
                # Parse tags (limit to 5-6 most important)
                tags = [tag.strip().strip('"') for tag in tags_str.split('、') if tag.strip()]
                key_tags = tags[:6] if tags else []
                
                product = {
                    'name': name,
                    'tags': key_tags,
                    'efficacy': efficacy,
                    'usage': usage,
                    'ingredients': ingredients,
                    'restrictions': restrictions
                }
                
                categories[current_category].append(product)
                all_products.append(product)

# Generate balanced format
output = """【诺亚医疗产品库】共184个产品

"""

# Process each category
for cat_name, products in categories.items():
    if not products:
        continue
        
    output += f"═══【{cat_name}】{len(products)}个═══\n\n"
    
    for i, p in enumerate(products, 1):
        output += f"{i}.{p['name']}\n"
        
        if p['tags']:
            output += f"标签：{','.join(p['tags'][:5])}\n"
        
        if p['efficacy']:
            output += f"功效：{p['efficacy']}\n"
        
        if p['usage']:
            output += f"用法：{p['usage']}\n"
        
        if p['ingredients']:
            output += f"成分：{p['ingredients']}\n"
        
        if p['restrictions']:
            output += f"注意：{p['restrictions']}\n"
        
        output += "\n"
    
    output += "\n"

# Add footer
output += "购买方式：诺亚新舟医疗小程序-医选好物\n"

# Save balanced format
with open('data/noah_products_balanced_full.txt', 'w', encoding='utf-8') as f:
    f.write(output)

# Calculate stats
print(f"Generated balanced format with {len(all_products)} products")
print(f"Categories: {len(categories)}")
print(f"Output size: {len(output):,} characters")
print(f"Estimated tokens: ~{len(output)//3:,}")
print(f"Saved to: data/noah_products_balanced_full.txt")

# Show sample
print("\nSample output:")
print("=" * 60)
print(output[:1000] + "...")