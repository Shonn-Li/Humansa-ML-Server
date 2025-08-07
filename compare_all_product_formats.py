#!/usr/bin/env python3
"""
Compare all product knowledge formats
"""

# Get format sizes
formats = {
    "Original CSV": {
        "file": "data/noah_supplements.csv",
        "example": """
儿童营养补剂,童年故事复合磷脂酰丝氨酸凝胶糖果,https://shop137071643.m.youzan.com/v2/goods/1yegdyu69ofur4j,
"产品名称：童年故事倍启智复合磷脂酰丝氨酸凝胶糖果
功效：产品类型本品是一款专为儿童设计的营养补充品，具有健脑益智，帮助儿童舒缓情绪...",
"建议用量：每日1-2粒
建议用法：直接咀嚼食用",
成分：每粒含100mg磷脂酰丝氨酸（PS）和50mg DHA,
"注意事项：本品添加新资源食品成分：DHA藻油、磷脂酰丝氨酸（PS）..."
"""
    },
    "Minimal Format": {
        "content": """磷脂酰丝氨酸糖果:大脑营养,学习,益智|健脑益智舒缓情绪""",
        "missing": ["用法用量", "具体成分含量", "禁忌", "链接", "详细描述"]
    },
    "Balanced Format": {
        "content": """1.童年故事复合磷脂酰丝氨酸凝胶糖果
标签：大脑营养,学习期,益智,PS+DHA
功效：健脑益智,舒缓情绪,含100mgPS+50mgDHA/粒
用法：每日1-2粒,直接咀嚼
禁忌：不适用于婴幼儿""",
        "preserved": ["产品名", "主要标签", "功效", "用法用量", "成分含量", "禁忌"]
    }
}

print("=" * 80)
print("Product Knowledge Format Comparison")
print("=" * 80)

# Import the actual formats
try:
    import os
    csv_size = os.path.getsize("data/noah_supplements.csv")
    
    # Load minimal format
    minimal_content = open('src/humansa/v2/agents/product_knowledge_minimal.py', 'r', encoding='utf-8').read()
    minimal_start = minimal_content.find('NOAH_PRODUCTS_MINIMAL = """') + 27
    minimal_end = minimal_content.find('"""', minimal_start)
    minimal_data = minimal_content[minimal_start:minimal_end]
    
    # Load balanced format  
    balanced_content = open('src/humansa/v2/agents/product_knowledge_balanced.py', 'r', encoding='utf-8').read()
    balanced_start = balanced_content.find('NOAH_PRODUCTS_BALANCED = """') + 28
    balanced_end = balanced_content.find('"""', balanced_start)
    balanced_data = balanced_content[balanced_start:balanced_end]
    
    print("\n1. Size Comparison:")
    print(f"   Original CSV: {csv_size:,} bytes (~{csv_size//4:,} tokens)")
    print(f"   Minimal Format: {len(minimal_data):,} bytes (~{len(minimal_data)//4:,} tokens)")
    print(f"   Balanced Format: {len(balanced_data):,} bytes (~{len(balanced_data)//3:,} tokens)")
    
    print(f"\n   Minimal Reduction: {100 - (len(minimal_data)/csv_size*100):.1f}%")
    print(f"   Balanced Reduction: {100 - (len(balanced_data)/csv_size*100):.1f}%")
    
except Exception as e:
    print(f"Error loading files: {e}")

print("\n2. Information Comparison:")
print("\n   Original CSV (Full Information):")
print("   ✅ Complete product names")
print("   ✅ Purchase links") 
print("   ✅ Detailed descriptions (100+ chars)")
print("   ✅ Specific dosage instructions")
print("   ✅ Complete ingredient lists with amounts")
print("   ✅ Contraindications and warnings")
print("   ✅ All product tags")

print("\n   Minimal Format (Too Compressed):")
print("   ✅ Abbreviated product names")
print("   ❌ No purchase links")
print("   ⚠️  Very short descriptions (<20 chars)")
print("   ❌ No dosage information")
print("   ❌ No ingredient amounts")
print("   ❌ No contraindications")
print("   ⚠️  Limited tags (3-4 only)")

print("\n   Balanced Format (Recommended):")
print("   ✅ Full product names")
print("   ❌ No purchase links (save tokens)")
print("   ✅ Key efficacy points (50-80 chars)")
print("   ✅ Dosage instructions preserved")
print("   ✅ Key ingredients with amounts")
print("   ✅ Important contraindications")
print("   ✅ Main tags (4-6)")

print("\n3. Example Comparison:")
print("\n   Same Product in Different Formats:")
print("   " + "-" * 60)

print("\n   MINIMAL:")
print("   磷脂酰丝氨酸糖果:大脑营养,学习,益智|健脑益智舒缓情绪")

print("\n   BALANCED:")
print("""   1.童年故事复合磷脂酰丝氨酸凝胶糖果
   标签：大脑营养,学习期,益智,PS+DHA
   功效：健脑益智,舒缓情绪,含100mgPS+50mgDHA/粒
   用法：每日1-2粒,直接咀嚼
   禁忌：不适用于婴幼儿""")

print("\n4. Recommendation:")
print("   " + "=" * 60)
print("   ⭐ Use BALANCED format for production")
print("   - Preserves critical information (dosage, contraindications)")
print("   - Reasonable token usage (~5-10K tokens)")
print("   - Supports safe product recommendations")
print("   - Maintains professional medical standards")

print("\n" + "=" * 80)