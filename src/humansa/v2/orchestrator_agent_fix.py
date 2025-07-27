"""Fix for orchestrator agent to reduce context length."""

def get_short_orchestrator_prompt():
    """Get a shorter orchestrator prompt to avoid context length issues."""
    return """你是诺亚新舟健康医疗助理（小诺），负责协调各种医疗服务。

今天日期：{current_date}

任务：分析用户查询并使用合适的工具。

重要规则：
1. 必须调用工具，不要直接回答
2. 问候/身份→general_medical_agent
3. 症状/诊断→diagnosis_agent  
4. 药物相关→medication_agent
5. 紧急情况（胸痛/呼吸困难）→emergency_triage_agent
6. 预约/医生→使用find_doctor_info等数据库工具
7. 产品/保健品→recommend_product工具
8. 诊所信息→search_clinics工具

使用工具结果作为最终答案。"""

def create_reduced_tools(tool_manager):
    """Create a reduced set of most important tools to avoid token limit."""
    if not tool_manager:
        return []
    
    all_tools = tool_manager.get_llamaindex_tools()
    
    # Priority tools to keep (most commonly used)
    priority_tool_names = [
        "find_doctor_info",
        "find_doctor_availability", 
        "search_clinics",
        "search_services",
        "recommend_product",
        "search_web",
        "get_pricing"
    ]
    
    # Filter to only keep priority tools
    reduced_tools = []
    for tool in all_tools:
        if tool.metadata.name in priority_tool_names:
            reduced_tools.append(tool)
    
    return reduced_tools