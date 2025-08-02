#!/usr/bin/env python3
"""
Simple test to verify CSV product loading
"""

import csv
import json
from datetime import datetime

# Read and analyze the CSV
csv_path = 'data/noah_supplements.csv'

print("=" * 60)
print("Noah Supplements CSV Analysis")
print("=" * 60)
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

try:
    with open(csv_path, 'r', encoding='utf-8') as f:
        # Skip header
        next(f)
        
        products = []
        categories = {}
        all_tags = set()
        current_category = ""
        
        csv_reader = csv.reader(f)
        for row in csv_reader:
            if len(row) >= 8:
                # Check if this is a category row
                if row[0].strip():
                    current_category = row[0].strip()
                
                # Check if this has a product name
                if row[1].strip():
                    product_name = row[1].strip()
                    tags_str = row[7].strip() if len(row) > 7 else ""
                    tags = [tag.strip().strip('"') for tag in tags_str.split('、') if tag.strip()]
                    
                    product = {
                        'category': current_category,
                        'name': product_name,
                        'link': row[2].strip(),
                        'description': row[3].strip()[:100] + "...",  # Truncate
                        'tags': tags
                    }
                    
                    products.append(product)
                    
                    # Track categories
                    if current_category not in categories:
                        categories[current_category] = []
                    categories[current_category].append(product)
                    
                    # Track all tags
                    all_tags.update(tags)
    
    print(f"\n✅ Successfully loaded CSV")
    print(f"📊 Total products: {len(products)}")
    print(f"📁 Categories: {len(categories)}")
    print(f"🏷️  Unique tags: {len(all_tags)}")
    
    print("\n📁 Categories and Product Counts:")
    for cat, prods in categories.items():
        print(f"  - {cat}: {len(prods)} products")
    
    print("\n🏷️  Top Tags (sample):")
    tag_list = sorted(list(all_tags))[:20]
    for i in range(0, len(tag_list), 4):
        print(f"  {', '.join(tag_list[i:i+4])}")
    
    print("\n📦 Sample Products:")
    for i, product in enumerate(products[:5]):
        print(f"\n{i+1}. {product['name']}")
        print(f"   Category: {product['category']}")
        print(f"   Tags: {', '.join(product['tags'][:5])}")
        print(f"   Description: {product['description']}")
    
    # Test search functionality
    print("\n🔍 Search Test:")
    search_terms = ["儿童", "睡眠", "维生素", "备孕"]
    
    for term in search_terms:
        matching = []
        for product in products:
            # Check in name, description, or tags
            if (term in product['name'] or 
                term in product['description'] or
                any(term in tag for tag in product['tags'])):
                matching.append(product)
        
        print(f"\n  '{term}' - Found {len(matching)} products:")
        for p in matching[:2]:
            print(f"    - {p['name']}")
    
    print("\n✅ CSV analysis complete!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()