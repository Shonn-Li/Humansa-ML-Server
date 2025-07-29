-- Insert comprehensive product test data
-- Ensure product tables exist and have data

-- First ensure categories exist
INSERT INTO humansa_product_category (category_id, name, description) VALUES
('CAT_VITAMIN', '维生素类', '各类维生素及营养补充剂'),
('CAT_HEALTH', '保健品类', '保健养生产品'),
('CAT_DEVICE', '医疗器械', '家用医疗设备和器械'),
('CAT_BEAUTY', '护肤美容', '医美和护肤产品'),
('CAT_SLEEP', '助眠产品', '改善睡眠质量的产品'),
('CAT_BABY', '母婴用品', '孕妇及婴幼儿专用产品'),
('CAT_TCM', '中药材类', '传统中药材及制品')
ON CONFLICT (category_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description;

-- Insert products with proper data
INSERT INTO humansa_products (
    product_id, name, category_id, price, original_price, 
    discount_tag, description, benefits, usage_instructions, 
    suitable_for, stock_status, is_featured
) VALUES
-- Vitamin products
('PROD001', '维生素D3软胶囊', 'CAT_VITAMIN', 89.00, 120.00, '7.5折', 
 '补充维生素D，促进钙吸收，每粒含维生素D3 1000IU', 
 '促进钙吸收，增强骨骼健康，提高免疫力', 
 '每日1粒，随餐服用', 
 '缺乏维生素D者，少晒太阳者，中老年人', 
 'in_stock', true),

('PROD002', '复合维生素片', 'CAT_VITAMIN', 168.00, 198.00, '8.5折',
 '全面补充21种维生素和矿物质，满足每日营养需求',
 '补充日常饮食不足，增强体质，提高抵抗力',
 '每日1片，早餐后服用',
 '饮食不均衡者，工作压力大者，亚健康人群',
 'in_stock', true),

-- Health supplements
('PROD003', '深海鱼油软胶囊', 'CAT_HEALTH', 198.00, 258.00, '特惠',
 '富含Omega-3（EPA+DHA），维护心血管健康',
 '降低血脂，保护心血管，改善记忆力，抗炎',
 '每日2粒，餐后服用',
 '三高人群，心血管疾病风险者，中老年人',
 'in_stock', true),

('PROD004', '益生菌粉', 'CAT_HEALTH', 238.00, 298.00, '8折',
 '每袋含300亿活性益生菌，调节肠道菌群',
 '改善消化，缓解便秘，增强肠道免疫力',
 '每日1袋，温水冲服，避免热水',
 '肠道功能紊乱者，便秘人群，免疫力低下者',
 'in_stock', false),

-- Medical devices
('PROD005', '电子血压计', 'CAT_DEVICE', 298.00, 398.00, '限时优惠',
 '全自动臂式血压计，大屏显示，语音播报',
 '准确测量血压，记录历史数据，及时监测健康',
 '按说明书操作，定期校准',
 '高血压患者，中老年人，需要监测血压者',
 'in_stock', true),

('PROD006', '血糖仪套装', 'CAT_DEVICE', 168.00, 228.00, '新品特价',
 '快速测血糖，5秒出结果，含50片试纸',
 '快速准确测量血糖，帮助控制血糖水平',
 '清洁手指，按操作步骤测量',
 '糖尿病患者，血糖异常者，需要监测血糖者',
 'in_stock', false),

-- Beauty products
('PROD007', '医美修复面膜', 'CAT_BEAUTY', 268.00, 328.00, 'VIP价',
 '透明质酸+积雪草精华，术后修复专用',
 '深层补水，舒缓敏感，加速修复，淡化红肿',
 '洁面后敷15-20分钟，每周2-3次',
 '医美术后，敏感肌，需要密集修复者',
 'in_stock', true),

('PROD008', '玻尿酸精华液', 'CAT_BEAUTY', 398.00, 498.00, '8折',
 '含高低分子透明质酸，深层补水抗衰',
 '深层补水，改善细纹，提升肌肤弹性',
 '早晚洁面后使用，轻拍至吸收',
 '缺水肌肤，初抗老人群，25岁以上女性',
 'low_stock', false),

-- Sleep aids
('PROD009', '褪黑素片', 'CAT_SLEEP', 128.00, 168.00, '促销',
 '每片含褪黑素3mg，改善睡眠质量',
 '改善睡眠，调节生物钟，缓解时差反应',
 '睡前30分钟服用1片，不宜长期服用',
 '失眠人群，倒时差人群，睡眠质量差者',
 'in_stock', true),

('PROD010', '薰衣草精油', 'CAT_SLEEP', 168.00, 218.00, '新客优惠',
 '100%纯薰衣草精油，舒缓助眠',
 '舒缓情绪，放松身心，改善睡眠，驱蚊虫',
 '睡前滴2-3滴于枕头或香薰灯',
 '睡眠不佳者，压力大者，需要放松者',
 'in_stock', false),

-- Mother & baby products
('PROD011', '孕妇DHA胶囊', 'CAT_BABY', 298.00, 398.00, '孕妈专享',
 '每粒含DHA 200mg，促进胎儿大脑发育',
 '促进胎儿大脑和视力发育，补充孕期营养',
 '每日1-2粒，随餐服用',
 '孕妇，哺乳期妇女',
 'in_stock', true),

('PROD012', '叶酸片', 'CAT_BABY', 68.00, 88.00, '必备',
 '每片含叶酸0.4mg，预防胎儿神经管缺陷',
 '预防胎儿神经管缺陷，补充孕期叶酸',
 '每日1片，孕前3个月开始服用',
 '备孕女性，孕早期妇女',
 'in_stock', true),

-- Traditional Chinese medicine
('PROD013', '西洋参片', 'CAT_TCM', 388.00, 488.00, '精选',
 '特级西洋参切片，益气养阴',
 '益气养阴，清热生津，提高免疫力',
 '每次3-5片，开水冲泡或含服',
 '气阴两虚者，免疫力低下者，经常熬夜者',
 'low_stock', true),

('PROD014', '冬虫夏草胶囊', 'CAT_TCM', 1288.00, 1588.00, '高端',
 '每粒含冬虫夏草粉0.25g，补肺益肾',
 '补肺益肾，止血化痰，增强免疫力',
 '每日2次，每次2粒，饭后服用',
 '肺肾两虚者，慢性咳嗽者，体质虚弱者',
 'low_stock', false)
ON CONFLICT (product_id) DO UPDATE SET
    name = EXCLUDED.name,
    category_id = EXCLUDED.category_id,
    price = EXCLUDED.price,
    original_price = EXCLUDED.original_price,
    discount_tag = EXCLUDED.discount_tag,
    description = EXCLUDED.description,
    benefits = EXCLUDED.benefits,
    usage_instructions = EXCLUDED.usage_instructions,
    suitable_for = EXCLUDED.suitable_for,
    stock_status = EXCLUDED.stock_status,
    is_featured = EXCLUDED.is_featured;

-- Insert product packages
INSERT INTO humansa_product_packages (
    package_id, name, description, tags, 
    total_value, savings_amount, included_items, target_audience
) VALUES
('PKG001', '基础保健套餐', '日常保健必备组合，包含复合维生素、鱼油、益生菌', 
 '日常保健,基础营养,热销', 604.00, 60.00, 
 ARRAY['复合维生素片 x1', '深海鱼油软胶囊 x1', '益生菌粉 x1'],
 '亚健康人群，办公室白领'),

('PKG002', '孕妇营养套餐', '孕期全程营养支持，科学搭配', 
 '孕妇专用,营养补充,医生推荐', 434.00, 50.00,
 ARRAY['孕妇DHA胶囊 x1', '叶酸片 x2', '复合维生素片 x1'],
 '孕妇，备孕女性'),

('PKG003', '三高管理套餐', '血压血糖监测组合，慢病管理必备', 
 '慢病管理,监测设备,实用', 466.00, 46.00,
 ARRAY['电子血压计 x1', '血糖仪套装 x1'],
 '三高患者，中老年人'),

('PKG004', '睡眠改善套餐', '全方位改善睡眠质量', 
 '助眠,放松,改善睡眠', 296.00, 30.00,
 ARRAY['褪黑素片 x1', '薰衣草精油 x1'],
 '失眠人群，睡眠质量差者'),

('PKG005', '美容护肤套餐', '医美术后修复套装', 
 '医美,修复,护肤', 666.00, 80.00,
 ARRAY['医美修复面膜 x2盒', '玻尿酸精华液 x1'],
 '医美术后，爱美女性')
ON CONFLICT (package_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    tags = EXCLUDED.tags,
    total_value = EXCLUDED.total_value,
    savings_amount = EXCLUDED.savings_amount,
    included_items = EXCLUDED.included_items,
    target_audience = EXCLUDED.target_audience;

-- Verify the data
SELECT 'Product Categories' as entity, COUNT(*) as count FROM humansa_product_category
UNION ALL
SELECT 'Products' as entity, COUNT(*) as count FROM humansa_products
UNION ALL
SELECT 'Product Packages' as entity, COUNT(*) as count FROM humansa_product_packages
UNION ALL
SELECT 'Featured Products' as entity, COUNT(*) as count FROM humansa_products WHERE is_featured = true
UNION ALL
SELECT 'In Stock Products' as entity, COUNT(*) as count FROM humansa_products WHERE stock_status = 'in_stock';