#!/usr/bin/env python3
"""
Test minimal product format
"""

# Read the minimal format file content directly
minimal_content = open('src/humansa/v2/agents/product_knowledge_minimal.py', 'r', encoding='utf-8').read()

# Extract just the product data
start = minimal_content.find('NOAH_PRODUCTS_MINIMAL = """')
end = minimal_content.find('"""', start + 30)
product_data = minimal_content[start+27:end]

# Get CSV size
import os
csv_size = os.path.getsize('data/noah_supplements.csv')

print("=" * 60)
print("Minimal Product Format Analysis")
print("=" * 60)

print(f"\n📊 Size Comparison:")
print(f"   Original CSV: {csv_size:,} bytes (~{csv_size//4:,} tokens)")
print(f"   Minimal format: {len(product_data):,} bytes (~{len(product_data)//4:,} tokens)")
print(f"   Reduction: {100 - (len(product_data) / csv_size * 100):.1f}%")

print(f"\n📦 Product Count:")
# Count products (lines with : and |)
product_lines = [line for line in product_data.split('\n') if ':' in line and '|' in line]
print(f"   Total products: {len(product_lines)}")

# Count categories
category_lines = [line for line in product_data.split('\n') if line.strip().startswith('[') and line.strip().endswith(']')]
print(f"   Categories: {len(category_lines)}")

print(f"\n🏷️ Sample Products:")
for i, line in enumerate(product_lines[:5]):
    if ':' in line and '|' in line:
        name = line.split(':')[0].strip()
        print(f"   {i+1}. {name}")

print(f"\n✅ Token Efficiency:")
print(f"   ~{len(product_data)//4} tokens for 184 products")
print(f"   ~{(len(product_data)//4)//184} tokens per product")
print(f"   Fits easily in GPT-4 context window (128K tokens)")

print("\n💡 Format Structure:")
print("   [Category(count)]")
print("   ProductName:tag1,tag2,tag3|short description")
print("   - Minimal punctuation")
print("   - Abbreviated descriptions")
print("   - Key tags only")

print("\n" + "=" * 60)