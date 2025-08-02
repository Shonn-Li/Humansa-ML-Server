-- Appointment Forms System Tables
-- For form-based approval workflow

-- Drop existing tables if needed
DROP TABLE IF EXISTS appointment_forms CASCADE;
DROP TABLE IF EXISTS appointment_form_templates CASCADE;
DROP TYPE IF EXISTS form_status CASCADE;

-- Form status enum
CREATE TYPE form_status AS ENUM (
    'draft',              -- Initial state, being filled
    'pending_confirmation', -- Ready for user confirmation
    'confirmed',          -- User confirmed, ready to submit
    'submitted',          -- Actually submitted to booking system
    'expired',            -- Timed out
    'cancelled'           -- User cancelled
);

-- Form templates for different types
CREATE TABLE appointment_form_templates (
    id SERIAL PRIMARY KEY,
    form_type VARCHAR(50) NOT NULL, -- 'appointment', 'checkup', 'consultation'
    name VARCHAR(100) NOT NULL,
    description TEXT,
    schema JSONB NOT NULL, -- Field definitions
    validation_rules JSONB,
    ui_config JSONB, -- UI hints for frontend
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(form_type)
);

-- Actual filled forms
CREATE TABLE appointment_forms (
    form_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id INTEGER REFERENCES appointment_form_templates(id),
    user_id VARCHAR(255) NOT NULL,
    conversation_id VARCHAR(255),
    form_type VARCHAR(50) NOT NULL,
    form_data JSONB NOT NULL, -- Actual filled data
    status form_status DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP + INTERVAL '30 minutes',
    confirmed_at TIMESTAMP,
    submitted_at TIMESTAMP,
    confirmation_code VARCHAR(20),
    submission_result JSONB, -- Result from booking system
    metadata JSONB -- Additional context
);

-- Indexes for performance
CREATE INDEX idx_appointment_forms_user_id ON appointment_forms(user_id);
CREATE INDEX idx_appointment_forms_status ON appointment_forms(status);
CREATE INDEX idx_appointment_forms_expires_at ON appointment_forms(expires_at);
CREATE INDEX idx_appointment_forms_conversation_id ON appointment_forms(conversation_id);

-- Insert default appointment form template
INSERT INTO appointment_form_templates (form_type, name, description, schema, validation_rules, ui_config) VALUES (
    'appointment',
    '医疗预约表单',
    '标准医疗预约信息收集表单',
    '{
        "fields": [
            {
                "name": "doctor_id",
                "type": "select",
                "label": "选择医生",
                "required": true,
                "datasource": "doctors"
            },
            {
                "name": "doctor_name",
                "type": "text",
                "label": "医生姓名",
                "readonly": true
            },
            {
                "name": "speciality",
                "type": "text",
                "label": "科室",
                "readonly": true
            },
            {
                "name": "clinic_name",
                "type": "text",
                "label": "诊所",
                "readonly": true
            },
            {
                "name": "date",
                "type": "date",
                "label": "预约日期",
                "required": true,
                "min": "today",
                "max": "+30days"
            },
            {
                "name": "time_slot",
                "type": "select",
                "label": "时间段",
                "required": true,
                "datasource": "time_slots"
            },
            {
                "name": "symptoms",
                "type": "textarea",
                "label": "症状描述",
                "required": true,
                "maxLength": 500,
                "placeholder": "请描述您的症状或就诊原因"
            },
            {
                "name": "is_urgent",
                "type": "boolean",
                "label": "是否紧急",
                "default": false
            },
            {
                "name": "patient_name",
                "type": "text",
                "label": "患者姓名",
                "required": true
            },
            {
                "name": "patient_phone",
                "type": "tel",
                "label": "联系电话",
                "required": true,
                "pattern": "^1[3-9]\\d{9}$"
            },
            {
                "name": "estimated_fee",
                "type": "number",
                "label": "预计费用（元）",
                "readonly": true,
                "calculated": true
            }
        ]
    }'::jsonb,
    '{
        "doctor_id": {
            "required": true,
            "message": "请选择医生"
        },
        "date": {
            "required": true,
            "min": "today",
            "max": "+30days",
            "message": "请选择未来30天内的日期"
        },
        "time_slot": {
            "required": true,
            "message": "请选择时间段"
        },
        "symptoms": {
            "required": true,
            "minLength": 10,
            "maxLength": 500,
            "message": "请描述症状（10-500字）"
        },
        "patient_phone": {
            "required": true,
            "pattern": "^1[3-9]\\d{9}$",
            "message": "请输入有效的手机号码"
        }
    }'::jsonb,
    '{
        "layout": "vertical",
        "submitButton": {
            "text": "确认预约",
            "style": "primary"
        },
        "cancelButton": {
            "text": "取消",
            "style": "default"
        },
        "sections": [
            {
                "title": "医生信息",
                "fields": ["doctor_id", "doctor_name", "speciality", "clinic_name"]
            },
            {
                "title": "预约时间",
                "fields": ["date", "time_slot"]
            },
            {
                "title": "就诊信息",
                "fields": ["symptoms", "is_urgent"]
            },
            {
                "title": "患者信息",
                "fields": ["patient_name", "patient_phone"]
            },
            {
                "title": "费用信息",
                "fields": ["estimated_fee"]
            }
        ]
    }'::jsonb
);

-- Function to clean up expired forms
CREATE OR REPLACE FUNCTION cleanup_expired_forms() RETURNS void AS $$
BEGIN
    UPDATE appointment_forms 
    SET status = 'expired' 
    WHERE status IN ('draft', 'pending_confirmation') 
    AND expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Sample form data for testing
INSERT INTO appointment_forms (
    user_id, 
    conversation_id, 
    form_type, 
    form_data, 
    status
) VALUES (
    'test_user_001',
    'conv_test_001',
    'appointment',
    '{
        "doctor_id": 1,
        "doctor_name": "张医生",
        "speciality": "心内科",
        "clinic_name": "北京诊所",
        "date": "2025-08-03",
        "time_slot": "09:00-09:30",
        "symptoms": "最近心跳有些不规律，偶尔会心慌",
        "is_urgent": false,
        "patient_name": "测试患者",
        "patient_phone": "13800138000",
        "estimated_fee": 300
    }'::jsonb,
    'pending_confirmation'
);