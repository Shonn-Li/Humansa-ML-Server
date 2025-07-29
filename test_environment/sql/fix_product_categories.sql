-- Fix product category inconsistency
-- Update products to use the correct category IDs that match the category names

-- Update vitamin products to use CAT1 (营养保健)
UPDATE humansa_products 
SET category_id = 'CAT1'
WHERE category_id = 'CAT_VITAMIN';

-- Update health products to use CAT1 (营养保健)
UPDATE humansa_products 
SET category_id = 'CAT1'
WHERE category_id = 'CAT_HEALTH';

-- Update medical device products to use CAT2 (医疗器械)
UPDATE humansa_products 
SET category_id = 'CAT2'
WHERE category_id = 'CAT_DEVICE';

-- Update beauty products to use CAT3 (护肤美容)
UPDATE humansa_products 
SET category_id = 'CAT3'
WHERE category_id = 'CAT_BEAUTY';

-- Update TCM products to use CAT4 (中医养生)
UPDATE humansa_products 
SET category_id = 'CAT4'
WHERE category_id = 'CAT_TCM';

-- Update baby products to use CAT5 (母婴健康)
UPDATE humansa_products 
SET category_id = 'CAT5'
WHERE category_id = 'CAT_BABY';

-- Update sleep products to use CAT1 (营养保健) since there's no sleep category
UPDATE humansa_products 
SET category_id = 'CAT1'
WHERE category_id = 'CAT_SLEEP';

-- Clean up duplicate categories
DELETE FROM humansa_product_category 
WHERE category_id IN ('CAT_VITAMIN', 'CAT_HEALTH', 'CAT_DEVICE', 'CAT_BEAUTY', 'CAT_SLEEP', 'CAT_BABY', 'CAT_TCM');