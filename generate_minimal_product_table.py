#!/usr/bin/env python3
"""
Generate minimal structured product table from CSV
"""

import csv
import json
from collections import defaultdict

# Read CSV and create minimal structure
csv_path = 'data/noah_supplements.csv'
products = []
categories = defaultdict(list)

with open(csv_path, 'r', encoding='utf-8') as f:
    next(f)  # Skip header
    
    current_category = ""
    csv_reader = csv.reader(f)
    
    for row in csv_reader:
        if len(row) >= 8:
            # Check for category
            if row[0].strip():
                current_category = row[0].strip()
            
            # Check for product
            if row[1].strip() and current_category:
                # Extract core fields only
                name = row[1].strip()
                
                # Simplify description - extract key benefits
                desc = row[3].strip()
                # Extract main benefits (first sentence or key points)
                if '功效' in desc:
                    desc_parts = desc.split('功效')[1].split('。')[0].strip('：').strip()
                    desc = desc_parts[:80]  # Limit length
                elif '本品' in desc:
                    desc_parts = desc.split('本品')[1].split('。')[0].strip()
                    desc = desc_parts[:80]
                else:
                    desc = desc.split('。')[0][:80]
                
                # Extract key tags (max 3-4)
                tags_str = row[7].strip() if len(row) > 7 else ""
                tags = [tag.strip().strip('"') for tag in tags_str.split('、') if tag.strip()]
                key_tags = tags[:4] if tags else []
                
                # Create minimal product entry
                product = {
                    'n': name,  # name
                    'd': desc,  # description (shortened)
                    't': key_tags  # tags (limited)
                }
                
                categories[current_category].append(product)

# Generate minimal structured format
output = "# 诺亚医疗产品目录（184个产品）\n\n"

# Create ultra-compact format
for cat, prods in categories.items():
    if cat and prods:  # Skip empty categories
        output += f"## {cat}({len(prods)})\n"
        
        for i, p in enumerate(prods):
            # Ultra-compact format: Name|Tags|Desc
            tags_str = ','.join(p['t'][:3]) if p['t'] else ''
            desc_str = p['d'][:60] + '...' if len(p['d']) > 60 else p['d']
            output += f"{i+1}.{p['n']}|{tags_str}|{desc_str}\n"
        
        output += "\n"

# Save to file
with open('data/noah_products_minimal.txt', 'w', encoding='utf-8') as f:
    f.write(output)

# Also create JSON version for programmatic use
json_data = {
    'total': sum(len(prods) for prods in categories.values()),
    'categories': dict(categories)
}

with open('data/noah_products_minimal.json', 'w', encoding='utf-8') as f:
    json.dump(json_data, f, ensure_ascii=False, indent=2)

print(f"Generated minimal product table with {json_data['total']} products")
print(f"Text file size: {len(output)} characters")
print(f"Saved to: data/noah_products_minimal.txt and data/noah_products_minimal.json")