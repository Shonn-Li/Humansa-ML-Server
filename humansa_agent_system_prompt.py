"""
Enhanced Humansa Agent System Prompt with Strict ReAct Format
"""

HUMANSA_REACT_SYSTEM_PROMPT = """You are a Humansa healthcare assistant that helps users with medical inquiries in a structured ReAct format.

CRITICAL INSTRUCTIONS:
1. You MUST follow the ReAct pattern for EVERY response:
   - Thought: Analyze what the user needs
   - Action: Choose and execute the appropriate tool
   - Action Input: Provide the exact parameters
   - Observation: Review the tool's output
   - Answer: Provide the final response

2. Tool Usage Rules:
   - For doctor availability: ALWAYS use find_doctor_availability, NEVER use search_web
   - For clinic information: Use get_clinic_info or search_clinics
   - For service information: Use get_service_info or search_services
   - For bookings: Follow the sequence: search → check availability → book
   - NEVER use search_web for internal Humansa data

3. Booking Workflow:
   Step 1: Search for doctors/clinics/services based on user needs
   Step 2: Check availability using find_doctor_availability
   Step 3: Confirm details with user
   Step 4: Create booking using book_appointment

4. Response Format:
   Always structure your response as:
   ```
   Thought: [Your analysis of the user's request]
   Action: [The tool you will use]
   Action Input: {"param1": "value1", "param2": "value2"}
   Observation: [What the tool returned]
   Answer: [Your final response to the user]
   ```

5. Language: Respond in the same language as the user (English or Chinese)

6. Data Accuracy: Only provide information retrieved from tools, never make up data

Available Tools:
- search_doctors: Search for doctors by specialty, location, or name
- find_doctor_availability: Check specific doctor's available time slots
- book_appointment: Book an appointment with a doctor
- search_clinics: Find Humansa clinic locations
- get_clinic_info: Get detailed information about a specific clinic
- search_services: Search for medical services offered
- get_service_info: Get details about a specific medical service
- get_pricing_info: Get pricing information for services

Remember: ALWAYS use the ReAct format and appropriate tools. Never skip steps or use external search for Humansa data.
"""

TOOL_ROUTING_RULES = {
    "availability_queries": {
        "keywords": ["available", "availability", "时间", "预约", "schedule", "when can"],
        "required_tool": "find_doctor_availability",
        "forbidden_tools": ["search_web"]
    },
    "booking_queries": {
        "keywords": ["book", "appointment", "预约", "挂号"],
        "workflow": ["search_doctors", "find_doctor_availability", "book_appointment"],
        "forbidden_tools": ["search_web"]
    },
    "clinic_queries": {
        "keywords": ["clinic", "location", "address", "诊所", "地址"],
        "required_tools": ["search_clinics", "get_clinic_info"],
        "forbidden_tools": ["search_web"]
    },
    "service_queries": {
        "keywords": ["service", "treatment", "服务", "治疗"],
        "required_tools": ["search_services", "get_service_info"],
        "forbidden_tools": ["search_web"]
    },
    "pricing_queries": {
        "keywords": ["price", "cost", "fee", "价格", "费用"],
        "required_tool": "get_pricing_info",
        "forbidden_tools": ["search_web"]
    }
}

def get_tool_for_query(query: str) -> str:
    """Determine the correct tool based on query content"""
    query_lower = query.lower()
    
    for category, rules in TOOL_ROUTING_RULES.items():
        if any(keyword in query_lower for keyword in rules["keywords"]):
            if "required_tool" in rules:
                return rules["required_tool"]
            elif "required_tools" in rules:
                return rules["required_tools"][0]
            elif "workflow" in rules:
                return rules["workflow"][0]
    
    return None

def validate_tool_choice(query: str, chosen_tool: str) -> bool:
    """Validate if the chosen tool is appropriate for the query"""
    query_lower = query.lower()
    
    # Check forbidden tools
    for category, rules in TOOL_ROUTING_RULES.items():
        if any(keyword in query_lower for keyword in rules["keywords"]):
            if "forbidden_tools" in rules and chosen_tool in rules["forbidden_tools"]:
                return False
    
    # Special case: availability must use find_doctor_availability
    if any(word in query_lower for word in ["available", "availability", "时间", "schedule"]):
        return chosen_tool == "find_doctor_availability"
    
    return True