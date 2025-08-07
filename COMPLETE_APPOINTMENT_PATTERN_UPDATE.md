# Complete Appointment Pattern Update

## Summary of Changes Needed

Based on your correct observation, here's what needs to change:

### 1. **Current (Wrong) Pattern**
```
Orchestrator → Form Tools (tries to extract/validate)
Orchestrator → Does validation itself
```

### 2. **Correct Pattern**
```
Orchestrator → Appointment Agent → Agent Validates → Returns Status
                                 ↓
                    If missing info: Tell orchestrator what's needed
                    If complete: Create form and return preview
```

## Required Code Changes

### 1. Update Appointment Agent Tool in Pattern 2

```python
# In orchestrator_pattern2_fixed.py
def call_appointment_agent(request: str) -> str:
    """
    Appointment booking with validation
    Agent will tell us if it needs more information
    """
    logger.info(f"🏥 AppointmentAgent called with: {request}")
    
    if self._current_state:
        self._current_state.agents_called.append("AppointmentAgent")
    
    if agent := self.agents.get("AppointmentAgent"):
        try:
            # Build context from current state
            context = {}
            
            # Extract any appointment-related info from state
            if hasattr(self._current_state, 'patient_profile'):
                context['patient_name'] = self._current_state.patient_profile.get('name')
            
            # Check if we already collected some info in conversation
            # This is where accumulated context goes
            if hasattr(self._current_state, 'appointment_context'):
                context.update(self._current_state.appointment_context)
            
            async def run_agent():
                # Use enhanced appointment agent
                from src.humansa.v2.forms.appointment_agent_enhanced import AppointmentAgentEnhanced
                enhanced_agent = AppointmentAgentEnhanced()
                
                result = await enhanced_agent.process_appointment_request(
                    query=request,
                    context=context,
                    user_id=self._current_state.user_id
                )
                
                # Handle different response types
                if result['status'] == 'need_more_info':
                    # Store what's missing in state
                    if not hasattr(self._current_state, 'appointment_context'):
                        self._current_state.appointment_context = {}
                    
                    # Update context with what we have
                    if 'current_info' in result:
                        self._current_state.appointment_context.update(result['current_info'])
                    
                    # Build natural response
                    response = result['message']
                    
                    # Add specific prompts based on what's missing
                    if 'available_doctors' in result:
                        response += "\n\n可选医生：\n"
                        for doc in result['available_doctors']:
                            response += f"- {doc['name']}（{doc['department']}，{doc['title']}）\n"
                    
                    if 'available_times' in result:
                        response += "\n可选时间：" + "、".join(result['available_times'])
                    
                    return response
                
                elif result['status'] == 'form_created':
                    # Store form_id in state
                    self._current_state.active_form_id = result['form_id']
                    
                    # Return preview for user confirmation
                    response = f"{result['message']}\n\n{result['preview']}\n\n{result.get('instructions', '')}"
                    return response
                
                elif result['status'] == 'booking_confirmed':
                    # Clear appointment context
                    self._current_state.appointment_context = {}
                    self._current_state.active_form_id = None
                    
                    return result['message']
                
                elif result['status'] == 'cancelled':
                    # Clear context
                    self._current_state.appointment_context = {}
                    self._current_state.active_form_id = None
                    
                    return result['message']
                
                else:
                    return result.get('message', '处理预约请求时出现错误')
            
            # Run with proper async handling
            try:
                result = asyncio.run(run_agent())
            except RuntimeError as e:
                if "already running" in str(e):
                    loop = asyncio.get_event_loop()
                    result = loop.run_until_complete(run_agent())
                else:
                    raise
            
            return result
            
        except Exception as e:
            logger.error(f"AppointmentAgent error: {e}")
            return f"预约服务出现错误: {str(e)}"
    
    return "预约服务暂时不可用"
```

### 2. Update Orchestrator Prompt

```python
# Add to orchestrator prompt
"""
【预约工具使用说明】
8. book_appointment - 智能预约管理
   - 工具会自动验证是否有足够信息
   - 如果信息不足，会告诉你缺少什么
   - 不需要你预先验证，直接调用即可
   
   使用示例：
   用户："我想看医生"
   你：调用 book_appointment("我想看医生")
   工具返回："需要更多信息：医生、日期、时间、症状"
   你："请问您想看哪位医生？有什么症状？"
   
   用户："头痛，看李明医生"  
   你：调用 book_appointment("头痛，看李明医生")
   工具返回："还需要：日期、时间"
   你："李明医生什么时候方便？"
   
   注意：
   - 不要自己判断信息是否完整
   - 让工具告诉你缺什么
   - 根据工具反馈自然地询问用户
"""
```

### 3. Remove Form Tools from Orchestrator

Since appointment agent handles its own form creation:

```python
# Remove these from orchestrator:
# - create_appointment_form
# - update_appointment_form  
# - submit_appointment_form
# - handle_form_confirmation

# The appointment agent handles all of this internally
```

## Example Conversation Flow

### Before (Complex):
```
User: 我想看医生
Orchestrator: [Thinks: Need to collect info first]
Orchestrator: 请问您有什么症状？想看哪位医生？什么时候方便？
User: ...
[Multiple back and forth]
Orchestrator: [Finally calls form tool]
```

### After (Simple):
```
User: 我想看医生
Orchestrator: [Calls appointment agent]
Agent: {status: need_more_info, missing: [doctor, date, time, symptoms]}
Orchestrator: 请问您想看哪位医生？有什么症状需要就诊？
User: 头痛，看李明医生
Orchestrator: [Calls appointment agent with accumulated context]
Agent: {status: need_more_info, missing: [date, time]}
Orchestrator: 李明医生什么时候方便？明天还是后天？
User: 明天上午
Orchestrator: [Calls appointment agent]
Agent: {status: form_created, preview: "..."}
Orchestrator: [Shows preview] 请确认预约信息
```

## Key Benefits

1. **Simpler Orchestrator Logic**
   - Just calls agent and responds based on status
   - No complex validation logic

2. **Encapsulated Business Logic**
   - All appointment logic in appointment agent
   - Easy to test and maintain

3. **Natural Conversation Flow**
   - Orchestrator focuses on conversation
   - Agent focuses on business rules

4. **Progressive Information Collection**
   - Agent validates and returns what's missing
   - Orchestrator asks naturally

## Testing the Pattern

```python
# Test 1: Missing all info
result = await agent.process_appointment_request("我想看医生", {}, "user1")
assert result['status'] == 'need_more_info'
assert len(result['missing_info']) == 4

# Test 2: Partial info
result = await agent.process_appointment_request(
    "看李明医生", 
    {"symptoms": "头痛"}, 
    "user1"
)
assert result['status'] == 'need_more_info'
assert 'date' in result['missing_info']
assert 'time' in result['missing_info']

# Test 3: Complete info
result = await agent.process_appointment_request(
    "明天上午", 
    {
        "doctor": "李明医生",
        "symptoms": "头痛",
        "date": "明天",
        "time": "上午"
    }, 
    "user1"
)
assert result['status'] == 'form_created'
```

## Conclusion

This pattern correctly implements:
- **Appointment agent owns validation**
- **Returns clear status to orchestrator**
- **Orchestrator just manages conversation**
- **Clean separation of concerns**

The key insight: Let each component do what it's best at. The appointment agent knows appointments, the orchestrator knows conversation.