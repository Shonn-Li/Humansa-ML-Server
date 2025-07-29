-- Create product-related tables for Humansa
CREATE TABLE IF NOT EXISTS humansa_product_category (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parent_category_id INTEGER REFERENCES humansa_product_category(category_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS humansa_products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category_id INTEGER REFERENCES humansa_product_category(category_id),
    description TEXT,
    price DECIMAL(10,2),
    price_range_min DECIMAL(10,2),
    price_range_max DECIMAL(10,2),
    manufacturer VARCHAR(100),
    specifications TEXT,
    usage_instructions TEXT,
    warnings TEXT,
    stock_quantity INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS humansa_product_packages (
    package_id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    total_price DECIMAL(10,2),
    discount_percentage DECIMAL(5,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS humansa_package_items (
    package_item_id SERIAL PRIMARY KEY,
    package_id INTEGER REFERENCES humansa_product_packages(package_id),
    product_id INTEGER REFERENCES humansa_products(product_id),
    quantity INTEGER DEFAULT 1,
    UNIQUE(package_id, product_id)
);

-- Insert product categories
INSERT INTO humansa_product_category (name, description) VALUES
('保健品', '各类保健营养品'),
('维生素', '维生素及矿物质补充剂'),
('医疗器械', '家用医疗设备和器械'),
('护肤美容', '医美和护肤产品'),
('中药材', '传统中药材及制品'),
('母婴用品', '孕妇及婴幼儿专用产品'),
('助眠产品', '改善睡眠质量的产品')
ON CONFLICT (name) DO NOTHING;

-- Insert products
INSERT INTO humansa_products (name, category_id, description, price, manufacturer, specifications, usage_instructions) VALUES
-- 维生素类
('维生素D3软胶囊', (SELECT category_id FROM humansa_product_category WHERE name = '维生素'), 
 '补充维生素D，促进钙吸收', 89.00, 'Swisse', '每粒含维生素D3 1000IU，60粒/瓶', 
 '每日1粒，随餐服用'),
 
('复合维生素片', (SELECT category_id FROM humansa_product_category WHERE name = '维生素'), 
 '全面补充多种维生素和矿物质', 168.00, '善存', '含21种维生素和矿物质，100片/瓶', 
 '每日1片，早餐后服用'),

-- 保健品类
('深海鱼油软胶囊', (SELECT category_id FROM humansa_product_category WHERE name = '保健品'), 
 '富含Omega-3，维护心血管健康', 198.00, 'Blackmores', '每粒含EPA180mg+DHA120mg，100粒/瓶', 
 '每日2粒，餐后服用'),
 
('益生菌粉', (SELECT category_id FROM humansa_product_category WHERE name = '保健品'), 
 '调节肠道菌群，改善消化', 238.00, 'Life-Space', '每袋含300亿活性益生菌，30袋/盒', 
 '每日1袋，温水冲服'),

-- 医疗器械类
('电子血压计', (SELECT category_id FROM humansa_product_category WHERE name = '医疗器械'), 
 '全自动臂式血压计，大屏显示', 298.00, '欧姆龙', '测量范围：0-299mmHg，记忆功能90组', 
 '按说明书操作，定期校准'),
 
('血糖仪套装', (SELECT category_id FROM humansa_product_category WHERE name = '医疗器械'), 
 '快速测血糖，含50片试纸', 168.00, '罗氏', '5秒出结果，需血量0.6μL', 
 '清洁手指，按操作步骤测量'),

-- 护肤美容类
('医美修复面膜', (SELECT category_id FROM humansa_product_category WHERE name = '护肤美容'), 
 '术后修复，舒缓敏感', 268.00, '敷尔佳', '透明质酸+积雪草精华，5片/盒', 
 '洁面后敷15-20分钟'),
 
('玻尿酸精华液', (SELECT category_id FROM humansa_product_category WHERE name = '护肤美容'), 
 '深层补水，改善细纹', 398.00, '修丽可', '含高低分子透明质酸，30ml/瓶', 
 '早晚洁面后使用'),

-- 助眠产品类
('褪黑素片', (SELECT category_id FROM humansa_product_category WHERE name = '助眠产品'), 
 '改善睡眠，调节生物钟', 128.00, 'GNC', '每片含褪黑素3mg，60片/瓶', 
 '睡前30分钟服用1片'),
 
('薰衣草精油', (SELECT category_id FROM humansa_product_category WHERE name = '助眠产品'), 
 '舒缓助眠，放松身心', 168.00, 'NOW Foods', '100%纯薰衣草精油，30ml/瓶', 
 '睡前滴2-3滴于枕头或香薰灯'),

-- 母婴用品类
('孕妇DHA胶囊', (SELECT category_id FROM humansa_product_category WHERE name = '母婴用品'), 
 '促进胎儿大脑发育', 298.00, 'Nordic Naturals', '每粒含DHA 200mg，60粒/瓶', 
 '每日1-2粒，随餐服用'),
 
('叶酸片', (SELECT category_id FROM humansa_product_category WHERE name = '母婴用品'), 
 '预防胎儿神经管缺陷', 68.00, '斯利安', '每片含叶酸0.4mg，93片/瓶', 
 '每日1片，孕前3个月开始服用'),

-- 中药材类
('西洋参片', (SELECT category_id FROM humansa_product_category WHERE name = '中药材'), 
 '益气养阴，清热生津', 388.00, '同仁堂', '特级西洋参切片，50g/盒', 
 '每次3-5片，开水冲泡或含服'),
 
('冬虫夏草胶囊', (SELECT category_id FROM humansa_product_category WHERE name = '中药材'), 
 '补肺益肾，止血化痰', 1288.00, '青海春天', '每粒含冬虫夏草粉0.25g，60粒/瓶', 
 '每日2次，每次2粒')
ON CONFLICT DO NOTHING;

-- Create product packages
INSERT INTO humansa_product_packages (name, description, category, total_price, discount_percentage) VALUES
('基础保健套餐', '日常保健必备组合', '保健套餐', 450.00, 10),
('孕妇营养套餐', '孕期全程营养支持', '母婴套餐', 580.00, 15),
('三高管理套餐', '血压血糖监测组合', '慢病管理', 420.00, 12),
('睡眠改善套餐', '全方位改善睡眠质量', '健康调理', 380.00, 8),
('美容护肤套餐', '医美术后修复套装', '美容套餐', 880.00, 20)
ON CONFLICT DO NOTHING;

-- Add items to packages (example for basic health package)
INSERT INTO humansa_package_items (package_id, product_id, quantity) 
SELECT 
    (SELECT package_id FROM humansa_product_packages WHERE name = '基础保健套餐'),
    product_id,
    1
FROM humansa_products 
WHERE name IN ('复合维生素片', '深海鱼油软胶囊', '益生菌粉')
ON CONFLICT DO NOTHING;

-- Verify data
SELECT 'Product Categories' as entity, COUNT(*) as count FROM humansa_product_category
UNION ALL
SELECT 'Products' as entity, COUNT(*) as count FROM humansa_products
UNION ALL
SELECT 'Product Packages' as entity, COUNT(*) as count FROM humansa_product_packages;