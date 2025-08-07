# Humansa V2 Comprehensive Test Cases

## Overview
This document outlines 30 comprehensive test cases for Humansa V2 that validate:
- Identity and greetings
- Doctor search and availability
- Appointment booking workflow
- Clinic services and pricing
- Emergency handling
- Memory persistence and recall
- Multi-language support
- Complex multi-part queries

## Test Categories

### 1. Identity & Basic Interactions (Tests 1-5)

**Test 1: Chinese Identity Query**
- Query: `你是谁？`
- Expected: Should identify as "诺亚新舟健康医疗助理（小诺）"
- Validates: Basic identity recognition

**Test 2: English Identity Query**
- Query: `Who are you?`
- Expected: Should respond with "Humansa Health Medical Assistant"
- Validates: Multi-language support

**Test 3: Chinese Greeting**
- Query: `你好`
- Expected: Greeting with identity introduction
- Validates: Greeting handling

**Test 4: Company Introduction**
- Query: `介绍一下诺亚新舟`
- Expected: Full company description with "以爱行舟，亲近相守" slogan
- Validates: Company knowledge

**Test 5: Service Capabilities**
- Query: `你能做什么？`
- Expected: List all services (健康咨询、实时预约、检查项目、诊所导航、体检报告)
- Validates: Service awareness

### 2. Doctor Search & Information (Tests 6-10)

**Test 6: Find Cardiologist**
- Query: `我想找一个心脏科医生`
- Expected: List available cardiologists
- Validates: Specialty search

**Test 7: Find Doctors by City**
- Query: `深圳有哪些医生？`
- Expected: List doctors in Shenzhen
- Validates: Location-based search

**Test 8: Specific Doctor Info**
- Query: `张医生的信息`
- Expected: Dr. Zhang's details (specialty, experience, clinic)
- Validates: Individual doctor lookup

**Test 9: Doctor Availability**
- Query: `李医生下周有空吗？`
- Expected: Dr. Li's schedule for next week
- Validates: Schedule checking

**Test 10: Multi-criteria Search**
- Query: `北京的骨科医生，要有20年以上经验`
- Expected: Filtered list of orthopedic doctors in Beijing with 20+ years experience
- Validates: Complex search criteria

### 3. Appointment Booking Flow (Tests 11-15)

**Test 11: Complete Booking Request**
- Query: `预约王医生，我叫李明，电话13800138000，想看下周二下午`
- Expected: Confirmation with all details
- Validates: Full booking workflow

**Test 12: Incomplete Booking - Missing Info**
- Query: `帮我预约张医生`
- Expected: Request for missing patient name, phone, and preferred time
- Validates: Information gathering

**Test 13: Follow-up to Test 12**
- Query: `我叫王芳，电话15900159000`
- Expected: Still ask for preferred time, then complete booking
- Validates: Multi-turn conversation

**Test 14: Appointment Modification**
- Query: `改一下我明天的预约，改到后天同一时间`
- Expected: Modification confirmation
- Validates: Appointment management

**Test 15: Appointment Cancellation**
- Query: `取消我下周三的预约`
- Expected: Cancellation confirmation and policy
- Validates: Cancellation handling

### 4. Clinic Services & Pricing (Tests 16-20)

**Test 16: Clinic Locations**
- Query: `广州有哪些诊所？`
- Expected: List of Guangzhou clinics with addresses
- Validates: Clinic directory

**Test 17: Service Availability**
- Query: `深圳诊所提供什么服务？`
- Expected: List of services at Shenzhen clinics
- Validates: Service catalog

**Test 18: Service Pricing**
- Query: `肝功能检查多少钱？`
- Expected: Price range for liver function test
- Validates: Pricing information

**Test 19: Price Comparison**
- Query: `哪里的体检套餐最便宜？`
- Expected: Clinic comparison with prices
- Validates: Comparative queries

**Test 20: Service Details**
- Query: `核磁共振检查需要准备什么？`
- Expected: MRI preparation instructions
- Validates: Service guidance

### 5. Medical Consultation & Emergency (Tests 21-25)

**Test 21: Symptom Analysis**
- Query: `最近总是失眠，还头痛`
- Expected: Sleep disorder analysis and doctor recommendation
- Validates: Symptom handling

**Test 22: Emergency Case**
- Query: `我现在胸痛很厉害，呼吸困难`
- Expected: Immediate 120 recommendation
- Validates: Emergency detection

**Test 23: Medication Query**
- Query: `阿司匹林和华法林能一起吃吗？`
- Expected: Drug interaction warning
- Validates: Medication safety

**Test 24: Health Product Recommendation**
- Query: `我想买保健品`
- Expected: Direct to health mall mini-program
- Validates: Product recommendations

**Test 25: Department Recommendation**
- Query: `头晕应该看什么科？`
- Expected: Recommend neurology or ENT
- Validates: Triage capability

### 6. Memory Persistence Tests (Tests 26-30)

**Test 26: Store Personal Information**
- User: `memory_test_user_1`
- Query 1: `我叫张三，住在北京，今年45岁`
- Query 2: `我对花生和海鲜过敏`
- Query 3: `我有高血压，每天吃降压药`
- Expected: Acknowledgment and storage
- Validates: Information storage

**Test 27: Recall Personal Information**
- User: `memory_test_user_1` (same as Test 26)
- Query: `你知道我的基本信息吗？`
- Expected: Recall name (张三), location (北京), age (45)
- Validates: Basic info recall

**Test 28: Recall Medical History**
- User: `memory_test_user_1` (same as Test 26)
- Query: `我有什么过敏史和慢性病？`
- Expected: Recall allergies (花生、海鲜) and conditions (高血压)
- Validates: Medical history recall

**Test 29: Cross-Session Continuity**
- User: `memory_test_user_2`
- Session 1 Query: `我想找骨科医生，我膝盖老是疼`
- Session 2 Query: `上次我说的膝盖问题，有推荐的医生吗？`
- Expected: Reference previous knee pain discussion
- Validates: Context continuity

**Test 30: Complex Memory Integration**
- User: `memory_test_user_3`
- Query 1: `我住在深圳，想找离家近的诊所`
- Query 2: `我女儿5岁，经常感冒`
- Query 3: `推荐一个适合看儿童感冒的医生，最好在我附近`
- Expected: Recommend pediatrician in Shenzhen, considering stored location and child info
- Validates: Complex memory integration

### 7. Product Recommendation Tests (Tests 31-40)

**Test 31: General Product Inquiry**
- Query: `你们有什么保健品推荐吗？`
- Expected: List of product categories with examples
- Validates: Product agent activation

**Test 32: Vitamin Recommendation**
- Query: `我想买维生素D，有什么推荐？`
- Expected: Specific vitamin D products with prices (¥168 维生素D3软胶囊)
- Validates: Specific product search

**Test 33: Medical Equipment Query**
- Query: `家里老人需要血压计，推荐一款`
- Expected: Blood pressure monitor recommendation (¥399 智能血压计)
- Validates: Medical equipment category

**Test 34: Price Range Filter**
- Query: `有500元以下的保健品吗？`
- Expected: Products under ¥500 with prices
- Validates: Price filtering

**Test 35: Health Condition Based**
- Query: `我失眠严重，有什么产品可以帮助睡眠？`
- Expected: Sleep-related products (褪黑素、助眠枕等)
- Validates: Condition-based recommendation

**Test 36: Beauty Product Query**
- Query: `有医美面膜吗？`
- Expected: Medical beauty masks (¥368 医美修复面膜)
- Validates: Beauty category

**Test 37: Package Recommendation**
- Query: `有什么健康套餐推荐？`
- Expected: Health packages (免疫力提升套餐 ¥1288)
- Validates: Package products

**Test 38: Mother-Baby Products**
- Query: `孕妇需要补充什么营养品？`
- Expected: Pregnancy products (孕妇DHA ¥398)
- Validates: Mother-baby category

**Test 39: Traditional Chinese Medicine**
- Query: `有西洋参吗？`
- Expected: TCM products (西洋参含片 ¥298)
- Validates: TCM category

**Test 40: Purchase Guidance**
- Query: `怎么购买这些产品？`
- Expected: Mini-program link and purchase instructions
- Validates: Purchase flow guidance

## Expected Success Criteria

### Pass/Fail Criteria
- **Identity Tests (1-5)**: Must include key identity markers
- **Doctor Search (6-10)**: Must return relevant doctor information
- **Appointment Booking (11-15)**: Must handle complete and incomplete flows
- **Clinic Services (16-20)**: Must provide accurate service/pricing info
- **Medical Consultation (21-25)**: Must detect emergencies correctly
- **Memory Tests (26-30)**: Must recall stored information accurately
- **Product Tests (31-40)**: Must recommend relevant products with prices

### Performance Metrics
- Response time: < 10 seconds per query
- Memory recall accuracy: 100% for explicitly stored facts
- Emergency detection: 100% accuracy for critical symptoms
- Tool usage: Appropriate tools called for each query type

### Streaming Requirements
- All responses should show thought process when streaming enabled
- Format should include: 💭 思考, 🔧 行动, 📊 观察结果, ✅ 最终回答

## Test Execution Notes

1. **Memory Tests Setup**: Tests 26-30 require sequential execution with the same user ID to build memory context
2. **Multi-turn Tests**: Tests 12-13 should be executed in sequence
3. **Emergency Tests**: Test 22 must trigger immediate 120 recommendation
4. **Language Tests**: Tests should maintain language consistency (Chinese query = Chinese response)

## Validation Checklist

- [ ] All 30 tests pass with expected responses
- [ ] Memory persistence works across sessions
- [ ] Emergency detection is 100% accurate
- [ ] Streaming shows complete thought process
- [ ] No external web searches triggered
- [ ] Response times are acceptable
- [ ] Multi-language support works correctly
- [ ] Appointment flow handles all scenarios
- [ ] Tool usage is appropriate and logged