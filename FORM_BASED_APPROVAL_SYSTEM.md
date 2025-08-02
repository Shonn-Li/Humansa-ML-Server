# Form-Based Approval System Design

## Overview
A genius approach where agents populate forms that are handled by the UI for confirmation, editing, and submission.

## Architecture

### 1. Form Schema Definition

```python
# Form templates stored in database
CREATE TABLE appointment_form_templates (
    id SERIAL PRIMARY KEY,
    form_type VARCHAR(50), -- 'appointment', 'medication', 'checkup'
    schema JSONB, -- Form field definitions
    validation_rules JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

# Filled forms (temporary storage)
CREATE TABLE appointment_forms (
    form_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id INTEGER REFERENCES appointment_form_templates(id),
    user_id VARCHAR(255),
    conversation_id VARCHAR(255),
    form_data JSONB, -- Actual filled data
    status VARCHAR(50) DEFAULT 'draft', -- draft, confirmed, submitted, expired
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP + INTERVAL '30 minutes',
    submitted_at TIMESTAMP,
    confirmation_code VARCHAR(20)
);

# Form field definitions
{
    "appointment": {
        "fields": [
            {
                "name": "doctor_id",
                "type": "select",
                "label": "医生",
                "required": true,
                "datasource": "doctors"
            },
            {
                "name": "date",
                "type": "date",
                "label": "日期",
                "required": true,
                "min": "today",
                "max": "+30days"
            },
            {
                "name": "time_slot",
                "type": "select",
                "label": "时间段",
                "required": true,
                "datasource": "available_slots"
            },
            {
                "name": "symptoms",
                "type": "textarea",
                "label": "症状描述",
                "required": true,
                "max_length": 500
            },
            {
                "name": "is_urgent",
                "type": "boolean",
                "label": "紧急",
                "default": false
            },
            {
                "name": "estimated_fee",
                "type": "number",
                "label": "预计费用",
                "readonly": true,
                "calculated": true
            }
        ]
    }
}
```

### 2. Agent Implementation

```python
class AppointmentFormTool:
    """
    Tool that creates and fills appointment forms
    Returns form_id for UI handling
    """
    
    @tool
    async def create_appointment_form(
        self,
        patient_query: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Parse user intent and create a pre-filled form
        Returns form_id for UI display
        """
        
        # Extract information from query
        extracted_info = await self.extract_appointment_info(patient_query)
        
        # Create form instance
        form_data = {
            "doctor_name": extracted_info.get("doctor"),
            "symptoms": extracted_info.get("symptoms"),
            "preferred_date": extracted_info.get("date"),
            "preferred_time": extracted_info.get("time"),
            "is_urgent": self.detect_urgency(patient_query)
        }
        
        # Validate and enhance data
        if form_data["doctor_name"]:
            doctor = await self.find_doctor(form_data["doctor_name"])
            if doctor:
                form_data["doctor_id"] = doctor.id
                form_data["doctor_info"] = {
                    "name": doctor.name,
                    "speciality": doctor.speciality,
                    "clinic": doctor.clinic_name
                }
        
        # Find available slots if date specified
        if form_data["preferred_date"]:
            slots = await self.get_available_slots(
                doctor_id=form_data.get("doctor_id"),
                date=form_data["preferred_date"]
            )
            form_data["available_slots"] = slots
        
        # Calculate estimated fee
        form_data["estimated_fee"] = await self.calculate_fee(form_data)
        
        # Save form to database
        form_id = await self.save_form(
            user_id=context.get("user_id"),
            conversation_id=context.get("conversation_id"),
            form_type="appointment",
            form_data=form_data
        )
        
        # Return structured response
        return json.dumps({
            "type": "form_created",
            "form_id": str(form_id),
            "form_type": "appointment",
            "preview": self.generate_preview(form_data),
            "missing_fields": self.get_missing_required_fields(form_data),
            "message": self.generate_form_message(form_data)
        })
    
    @tool
    async def update_appointment_form(
        self,
        form_id: str,
        updates: str,  # Natural language updates
        context: Dict[str, Any]
    ) -> str:
        """
        Update existing form based on user input
        """
        
        # Load existing form
        form = await self.load_form(form_id)
        if not form:
            return "表单已过期或不存在"
        
        # Parse updates from natural language
        parsed_updates = await self.parse_updates(updates, form.form_data)
        
        # Apply updates
        updated_data = {**form.form_data, **parsed_updates}
        
        # Re-validate
        if "doctor_id" in parsed_updates or "date" in parsed_updates:
            # Refresh available slots
            slots = await self.get_available_slots(
                doctor_id=updated_data.get("doctor_id"),
                date=updated_data.get("preferred_date")
            )
            updated_data["available_slots"] = slots
        
        # Save updated form
        await self.update_form(form_id, updated_data)
        
        return json.dumps({
            "type": "form_updated",
            "form_id": form_id,
            "updated_fields": list(parsed_updates.keys()),
            "preview": self.generate_preview(updated_data),
            "message": "表单已更新"
        })
    
    @tool  
    async def submit_appointment_form(
        self,
        form_id: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Submit confirmed form for actual booking
        Called by frontend after user confirmation
        """
        
        # Load and validate form
        form = await self.load_form(form_id)
        if not form:
            return json.dumps({
                "type": "error",
                "message": "表单已过期或不存在"
            })
        
        if form.status != "confirmed":
            return json.dumps({
                "type": "error", 
                "message": "表单未确认"
            })
        
        # Submit actual appointment
        try:
            result = await self.book_appointment_internal(form.form_data)
            
            # Update form status
            await self.update_form_status(form_id, "submitted", {
                "confirmation_code": result.confirmation_code,
                "submitted_at": datetime.now()
            })
            
            return json.dumps({
                "type": "appointment_booked",
                "confirmation_code": result.confirmation_code,
                "details": result.to_dict(),
                "message": f"预约成功！确认码：{result.confirmation_code}"
            })
            
        except Exception as e:
            return json.dumps({
                "type": "error",
                "message": f"预约失败：{str(e)}"
            })
```

### 3. Frontend Integration

```javascript
// Frontend handling of form-based approval

class AppointmentFormHandler {
    async handleAgentResponse(response) {
        const parsed = JSON.parse(response);
        
        if (parsed.type === "form_created" || parsed.type === "form_updated") {
            // Display form UI
            this.displayAppointmentForm(parsed.form_id);
        }
    }
    
    async displayAppointmentForm(formId) {
        // Fetch full form data
        const formData = await this.fetchForm(formId);
        
        // Render form UI
        const formUI = this.renderForm(formData);
        
        // Add action buttons
        formUI.addButton("确认提交", () => this.confirmForm(formId));
        formUI.addButton("修改信息", () => this.editForm(formId));
        formUI.addButton("取消", () => this.cancelForm(formId));
        
        // Show to user
        this.showModal(formUI);
    }
    
    async confirmForm(formId) {
        // Mark form as confirmed
        await this.updateFormStatus(formId, "confirmed");
        
        // Submit through agent
        const result = await this.callAgent({
            tool: "submit_appointment_form",
            form_id: formId
        });
        
        if (result.type === "appointment_booked") {
            this.showSuccess(result);
        }
    }
    
    async editForm(formId) {
        // Two options:
        // 1. Direct UI editing
        this.enableFormEditing(formId);
        
        // 2. Natural language editing
        const userInput = await this.getUserInput("请说明要修改的内容");
        await this.callAgent({
            tool: "update_appointment_form",
            form_id: formId,
            updates: userInput
        });
    }
}
```

### 4. API Endpoints

```python
# Form management endpoints
GET    /api/forms/{form_id}          # Get form data
PUT    /api/forms/{form_id}          # Update form (UI direct edit)
POST   /api/forms/{form_id}/confirm  # Mark as confirmed
DELETE /api/forms/{form_id}          # Cancel form

# Form templates
GET    /api/forms/templates/{type}   # Get form schema
GET    /api/forms/datasources/{name} # Get dropdown options (doctors, slots, etc)
```

### 5. Conversation Flow

```
User: "我想预约李医生明天上午"
    ↓
Agent: create_appointment_form()
    ↓
Returns: {
    "type": "form_created",
    "form_id": "f1234",
    "preview": "李医生 - 明天上午9:00",
    "missing_fields": []
}
    ↓
Frontend: Shows form UI with all fields filled
    ↓
User: [Clicks 确认] or "改到下午3点"
    ↓
If edit: Agent: update_appointment_form(form_id, "改到下午3点")
If confirm: Frontend: Updates status, then calls submit_appointment_form
    ↓
Result: Appointment booked!
```

## Advantages

1. **Clean Separation of Concerns**
   - Agent only fills forms, doesn't handle UI flow
   - Frontend owns the confirmation UX
   - Backend just validates and submits

2. **Flexible Editing**
   - Users can edit via UI (direct manipulation)
   - Users can edit via chat (natural language)
   - Form persists across conversation turns

3. **Better UX**
   - No back-and-forth "Is this correct?" dialogue
   - Visual form is clearer than text description
   - Users control when to submit

4. **Stateless Agent**
   - Agent doesn't need to track approval state
   - Form ID carries all context
   - Can handle interruptions/context switches

5. **Reusability**
   - Same pattern for prescriptions, test bookings, etc
   - Forms can be saved as drafts
   - Templates ensure consistency

## Implementation Benefits

1. **For Current Pattern 2**:
   - Just add three new tools (create, update, submit)
   - No complex state management
   - Works with existing response flow

2. **For Frontend**:
   - Clear API contract
   - Can build rich form UIs
   - Progressive enhancement possible

3. **For Users**:
   - See everything before committing
   - Edit without re-explaining
   - Familiar form paradigm

## Example Implementation

```python
# In Pattern 2 orchestrator prompt
"""
预约相关工具使用：
1. 用户想预约 → 使用 create_appointment_form
2. 用户想修改表单 → 使用 update_appointment_form (需要form_id)
3. 不要主动要求确认，让前端处理
4. 返回form_id让用户在界面上操作
"""

# Tool response format
def create_appointment_form(...):
    # ... fill form logic ...
    
    return f'''已为您准备预约表单：
医生：{doctor_name}
时间：{date} {time}
症状：{symptoms}

请在弹出的表单中确认信息并提交。
表单编号：{form_id}'''
```

This approach is indeed genius because:
- It leverages UI for what UI does best (forms)
- It leverages agents for what they do best (understanding intent)
- It creates a clean, reusable pattern
- It eliminates the awkward "please confirm" dialogue
- It gives users full control while maintaining conversation context