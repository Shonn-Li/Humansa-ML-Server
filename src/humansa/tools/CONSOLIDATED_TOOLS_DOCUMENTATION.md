# HUMANSA Consolidated Tools Documentation

## Overview

The HUMANSA V2 system uses 7 consolidated tools (simplified from the original ~15 tools) to provide all medical assistance functionality. This consolidation reduces token usage and improves performance while maintaining full feature coverage.

## The 7 Core Tools

### 1. unified_search
**Purpose**: Universal search for doctors, clinics, and services

**Arguments**:
- `query` (str, required): Search query - can be doctor name, clinic name, service, specialty
- `search_type` (str, optional): Filter by type - 'doctor', 'clinic', 'service', or None for all
- `city` (str, optional): City filter - e.g., '深圳', '北京'
- `specialty` (str, optional): Specialty filter - e.g., '内科', '妇科'
- `date_range` (str, optional): Date range - e.g., '明天', '本周', '下周'
- `limit` (int, default=5): Number of results to return

**Example Usage**:
```python
# Search for cardiologists in Beijing
result = await unified_search(
    query="心脏科",
    search_type="doctor",
    city="北京"
)

# Search for available clinics this week
result = await unified_search(
    query="诊所",
    search_type="clinic",
    date_range="本周"
)
```

### 2. appointment_manager
**Purpose**: Complete appointment lifecycle management

**Arguments**:
- `action` (str, required): Operation type
  - 'check': Check appointment information
  - 'book': Create new appointment
  - 'reschedule': Change appointment time
  - 'cancel': Cancel appointment
  - 'history': View appointment history
- `doctor_name` (str, optional): Doctor's name
- `patient_name` (str, optional): Patient's name
- `phone` (str, optional): Contact phone
- `date` (str, optional): Appointment date
- `time` (str, optional): Appointment time
- `appointment_id` (str, optional): Appointment ID for changes
- `new_date` (str, optional): New date for rescheduling
- `new_time` (str, optional): New time for rescheduling
- `reason` (str, optional): Reason for cancellation/rescheduling

**Example Usage**:
```python
# Book an appointment
result = await appointment_manager(
    action="book",
    doctor_name="张医生",
    patient_name="李明",
    phone="13800138000",
    date="2024-01-15",
    time="14:00"
)

# Cancel an appointment
result = await appointment_manager(
    action="cancel",
    appointment_id="APT123456",
    reason="时间冲突"
)
```

### 3. medical_advisor
**Purpose**: Health consultation and medical triage

**Arguments**:
- `symptoms` (List[str], required): List of symptoms - e.g., ['头痛', '发烧', '咳嗽']
- `duration` (str, optional): Symptom duration - e.g., '3天', '一周'
- `severity` (str, optional): Severity level - '轻微', '中等', '严重'
- `patient_age` (int, optional): Patient's age
- `medical_history` (List[str], optional): Previous medical conditions
- `current_medications` (List[str], optional): Current medications
- `allergies` (List[str], optional): Known allergies

**Example Usage**:
```python
# Get medical advice for symptoms
result = await medical_advisor(
    symptoms=["头痛", "发烧"],
    duration="2天",
    severity="中等",
    patient_age=35,
    medical_history=["高血压"],
    current_medications=["阿司匹林"]
)
```

### 4. product_recommender
**Purpose**: Health product and medical device recommendations

**Arguments**:
- `category` (str, optional): Product category
  - 'supplements': 保健品
  - 'devices': 医疗器械
  - 'skincare': 护肤品
- `condition` (str, optional): Health condition - e.g., '失眠', '关节痛'
- `budget` (str, optional): Budget range - e.g., '100-500'
- `preferences` (List[str], optional): Preferences - e.g., ['天然', '进口', '无糖']

**Example Usage**:
```python
# Recommend products for insomnia
result = await product_recommender(
    category="supplements",
    condition="失眠",
    budget="100-300",
    preferences=["天然", "无副作用"]
)
```

### 5. information_lookup
**Purpose**: General information queries about services, pricing, hours

**Arguments**:
- `info_type` (str, required): Information type
  - 'pricing': 价格信息
  - 'hours': 营业时间
  - 'contact': 联系方式
  - 'insurance': 保险信息
  - 'location': 地址位置
- `entity_name` (str, optional): Name of clinic, doctor, or service
- `entity_type` (str, optional): Type - 'doctor', 'clinic', 'service'
- `specific_query` (str, optional): Specific question - e.g., '周末营业吗'

**Example Usage**:
```python
# Get clinic hours
result = await information_lookup(
    info_type="hours",
    entity_name="诺亚新舟广州诊所",
    entity_type="clinic",
    specific_query="周末营业时间"
)

# Get service pricing
result = await information_lookup(
    info_type="pricing",
    entity_name="血常规",
    entity_type="service"
)
```

### 6. emergency_handler
**Purpose**: Handle emergency medical situations

**Arguments**:
- `situation` (str, required): Emergency description
- `severity` (str, required): Severity level - 'urgent', 'critical', 'life_threatening'
- `location` (str, optional): Current location
- `patient_info` (Dict[str, Any], optional): Patient information
- `contact_method` (str, default="phone"): Contact method - 'phone', 'video', 'chat'

**Example Usage**:
```python
# Handle chest pain emergency
result = await emergency_handler(
    situation="胸痛，呼吸困难",
    severity="critical",
    location="广州天河区",
    patient_info={"age": 55, "gender": "男"}
)
```

### 7. conversation_memory
**Purpose**: Store and retrieve conversation context and patient information

**Arguments**:
- `action` (str, required): Operation type
  - 'save': Save information
  - 'retrieve': Get information
  - 'update': Update existing
  - 'summarize': Create summary
- `user_id` (str, required): User identifier
- `memory_type` (str, default="general"): Memory category
  - 'medical_history': 病史
  - 'preferences': 偏好设置
  - 'appointments': 预约记录
  - 'general': 一般信息
- `content` (Dict[str, Any], optional): Content to save
- `time_range` (str, optional): Time range for retrieval

**Example Usage**:
```python
# Save patient allergy information
result = await conversation_memory(
    action="save",
    user_id="user_12345",
    memory_type="medical_history",
    content={
        "query": "我对青霉素过敏",
        "response": "已记录您的过敏信息",
        "allergies": ["青霉素"]
    }
)

# Retrieve patient history
result = await conversation_memory(
    action="retrieve",
    user_id="user_12345",
    memory_type="medical_history"
)
```

## Tool Selection Strategy

The system uses dynamic tool loading based on query analysis:

1. **Medical Queries**: Loads medical_advisor, unified_search, appointment_manager
2. **Product Queries**: Loads product_recommender, information_lookup
3. **Emergency Queries**: Loads emergency_handler, unified_search
4. **General Queries**: Loads conversation_memory, information_lookup

## Error Handling

All tools return a standardized response format:

```python
{
    "success": bool,          # Operation success status
    "data": Dict/List,        # Result data if successful
    "error": str,             # Error message if failed
    "fallback": Any,          # Fallback information if available
    "message": str            # User-friendly message
}
```

## Best Practices

1. **Always check user context first**: Use conversation_memory to retrieve user history
2. **Emergency first**: If symptoms suggest emergency, use emergency_handler immediately
3. **Progressive information gathering**: Start with unified_search, then get details with information_lookup
4. **Confirm before booking**: Always verify patient details before using appointment_manager
5. **Store important information**: Use conversation_memory to save allergies, preferences, medical history

## Migration from Old Tools

| Old Tool | New Tool | Notes |
|----------|----------|-------|
| search_doctor | unified_search | Use search_type="doctor" |
| search_clinic | unified_search | Use search_type="clinic" |
| search_service | unified_search | Use search_type="service" |
| book_appointment | appointment_manager | Use action="book" |
| reschedule_appointment | appointment_manager | Use action="reschedule" |
| cancel_appointment | appointment_manager | Use action="cancel" |
| get_doctor_schedule | unified_search | Include date_range parameter |
| get_clinic_info | information_lookup | Use appropriate info_type |
| health_consultation | medical_advisor | Provide symptom list |
| recommend_product | product_recommender | Specify category |
| web_search | emergency_handler | For emergencies only |
| patient_memory_storage | conversation_memory | Use action="save" |
| patient_memory_retrieval | conversation_memory | Use action="retrieve" |

## Testing

Use the test script `test_HUMANSA_v2_70_cases_multiturn.py` to verify all tools are working correctly. The test environment should be started with:

```bash
./run_HUMANSA_test_environment_v2_enhanced.sh
```

This ensures proper database configuration and enhanced logging for debugging.