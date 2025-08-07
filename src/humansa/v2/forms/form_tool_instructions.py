"""
Form Tool Instructions - Best Practices Implementation
Based on industry research for optimal AI form collection
"""

# Required fields schema that the AI agent should know upfront
APPOINTMENT_FORM_SCHEMA = {
    "required_fields": {
        "doctor_name": {
            "description": "医生姓名",
            "example": "李明医生",
            "validation": "Must be a valid doctor name in our system"
        },
        "appointment_date": {
            "description": "预约日期", 
            "example": "明天、下周一、3月15日",
            "validation": "Must be a future date within 30 days"
        },
        "appointment_time": {
            "description": "预约时间",
            "example": "上午9点、下午3点、14:00",
            "validation": "Must be during clinic hours"
        },
        "symptoms": {
            "description": "症状描述",
            "example": "头痛、发烧、咳嗽",
            "validation": "At least 2 characters describing the medical concern"
        }
    },
    "optional_fields": {
        "patient_name": {
            "description": "患者姓名",
            "example": "张三",
            "when_to_ask": "Ask only if booking for someone else"
        },
        "urgency": {
            "description": "是否紧急",
            "example": "紧急、尽快",
            "auto_detect": True
        },
        "department": {
            "description": "科室",
            "example": "内科、外科、儿科",
            "auto_infer": "Can be inferred from symptoms or doctor"
        }
    }
}

# Instructions for the AI agent on how to use form tools
FORM_COLLECTION_INSTRUCTIONS = """
## Form Collection Best Practices

When helping users book appointments, follow these guidelines:

### 1. Progressive Data Collection
- Don't ask for all information at once
- Start by understanding the user's main concern
- Build upon previous answers naturally

### 2. Required Information
You need to collect these 4 essential pieces of information:
- **Doctor**: Who they want to see (or what type of doctor)
- **Date**: When they want the appointment
- **Time**: What time of day
- **Symptoms**: What medical issue they're experiencing

### 3. Conversation Flow
GOOD Example:
```
User: 我想看医生
AI: 您有什么不舒服的症状吗？
User: 最近头痛
AI: 头痛的情况我了解了。您想看哪个科室的医生呢？内科医生可以帮您诊断。
User: 好的，内科
AI: 我为您推荐李明医生（内科主任）。您什么时候方便就诊？
User: 明天可以吗
AI: 明天可以。您上午还是下午方便？
User: 上午
AI: 好的，我为您整理一下预约信息...
```

BAD Example:
```
User: 我想看医生
AI: 请提供：1.医生姓名 2.日期 3.时间 4.症状
```

### 4. Validation and Confirmation
- Only call create_appointment_form when you have enough information
- If critical fields are missing, ask conversationally
- Always show a preview before final confirmation

### 5. Error Recovery
If user provides unclear information:
- Ask clarifying questions naturally
- Provide examples or options
- Never say "invalid input" - guide them instead

### 6. Tool Usage Rules
- Call create_appointment_form when you have at least 2-3 key fields
- The tool will tell you what's missing - relay this conversationally
- Use update_appointment_form for modifications
- Always use handle_form_confirmation for user responses to previews
"""

# Schema for Pattern 2 orchestrator to understand
PATTERN2_FORM_TOOL_CONFIG = {
    "create_appointment_form": {
        "description": "Create appointment booking form from user request",
        "when_to_use": [
            "User expresses intent to book appointment",
            "Have collected at least doctor OR symptoms",
            "User asks to see a doctor"
        ],
        "expected_behavior": "Will return form_id and preview or list of missing fields",
        "follow_up_actions": [
            "If missing fields returned, ask for them conversationally",
            "If preview returned, ask for confirmation",
            "Store form_id in conversation context"
        ]
    },
    "update_appointment_form": {
        "description": "Update existing form with new information",
        "when_to_use": [
            "User provides additional information after form creation",
            "User wants to change something in the form",
            "Collecting missing required fields"
        ],
        "expected_behavior": "Updates form and returns new preview",
        "follow_up_actions": [
            "Show updated preview",
            "Ask for confirmation if form is complete"
        ]
    },
    "submit_appointment_form": {
        "description": "Submit confirmed form for actual booking",
        "when_to_use": [
            "User explicitly confirms the appointment",
            "All required fields are present",
            "User says '确认', '好的', '可以'"
        ],
        "expected_behavior": "Books appointment and returns confirmation code",
        "follow_up_actions": [
            "Show booking confirmation with code",
            "Provide next steps instructions"
        ]
    }
}

# Prompt enhancement for Pattern 2 orchestrator
ENHANCED_ORCHESTRATOR_PROMPT = """
When handling appointment booking requests:

1. **Understand Intent First**: Don't immediately create a form. Understand what the user needs.

2. **Collect Information Naturally**: 
   - If user says "我想看医生", ask about symptoms first
   - If user mentions symptoms, suggest appropriate department/doctor
   - If user knows the doctor, ask about preferred time

3. **Use Tools Intelligently**:
   - create_appointment_form: When you have initial information (even partial)
   - The tool will tell you what's missing - DON'T pre-validate
   - Let the tool handle validation and tell you what's needed

4. **Handle Tool Responses**:
   - If tool returns missing_fields, ask for them conversationally
   - If tool returns preview, present it clearly and ask for confirmation
   - If tool returns error, help user correct it without technical jargon

5. **Maintain Context**: Remember form_id throughout the conversation

Example Tool Usage:
```
User: 我想预约李医生
You: 好的，我来帮您预约李医生。请问您有什么症状需要就诊吗？
User: 头痛
You: [Call create_appointment_form with doctor="李医生", symptoms="头痛"]
Tool: Returns form_id and missing fields: date, time
You: 了解了，您头痛的情况需要及时就诊。李医生什么时候方便？比如明天或后天？
```

Remember: The form tools handle all validation. Your job is to:
- Collect information conversationally
- Call tools at appropriate times  
- Present results in a friendly way
- Guide users through the process
"""