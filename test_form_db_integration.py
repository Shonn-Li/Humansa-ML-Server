#!/usr/bin/env python3
"""
Test form system with actual database integration
"""

import asyncio
import asyncpg
import json
from datetime import datetime, timedelta

async def test_database_form_creation():
    """Test creating forms in the database"""
    
    # Connect to test database
    conn = await asyncpg.connect(
        host='localhost',
        port=5454,
        user='postgres',
        password='12931',
        database='test4'
    )
    
    try:
        # Test 1: Check if tables exist
        print("=== Testing Database Tables ===")
        
        # Check appointment_forms table
        result = await conn.fetchval("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'appointment_forms'
        """)
        print(f"✅ appointment_forms table exists: {result > 0}")
        
        # Check form_templates table
        result = await conn.fetchval("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'appointment_form_templates'
        """)
        print(f"✅ appointment_form_templates table exists: {result > 0}")
        
        # Test 2: Query existing templates
        print("\n=== Form Templates ===")
        templates = await conn.fetch("""
            SELECT form_type, name, description 
            FROM appointment_form_templates
        """)
        for template in templates:
            print(f"Template: {template['name']} ({template['form_type']})")
            print(f"  Description: {template['description']}")
        
        # Test 3: Query existing forms
        print("\n=== Existing Forms ===")
        forms = await conn.fetch("""
            SELECT form_id, user_id, form_type, status, 
                   form_data->>'doctor_name' as doctor_name,
                   form_data->>'date' as appointment_date,
                   form_data->>'symptoms' as symptoms
            FROM appointment_forms
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        if forms:
            for form in forms:
                print(f"\nForm ID: {form['form_id']}")
                print(f"  User: {form['user_id']}")
                print(f"  Status: {form['status']}")
                print(f"  Doctor: {form['doctor_name']}")
                print(f"  Date: {form['appointment_date']}")
                print(f"  Symptoms: {form['symptoms'][:50]}...")
        else:
            print("No forms found")
        
        # Test 4: Create a new form
        print("\n=== Creating New Form ===")
        
        new_form_data = {
            "doctor_id": 2,
            "doctor_name": "李明医生",
            "speciality": "内科",
            "clinic_name": "北京协和医院",
            "date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
            "time_slot": "14:00-14:30",
            "symptoms": "最近有些咳嗽，喉咙痛，可能是感冒了",
            "is_urgent": False,
            "patient_name": "测试患者2",
            "patient_phone": "13900139000",
            "estimated_fee": 150
        }
        
        form_id = await conn.fetchval("""
            INSERT INTO appointment_forms (
                user_id, conversation_id, form_type, form_data, status
            ) VALUES ($1, $2, $3, $4, $5)
            RETURNING form_id
        """, 
            "test_user_integration",
            "conv_integration_001",
            "appointment",
            json.dumps(new_form_data),
            "draft"
        )
        
        print(f"✅ Created form with ID: {form_id}")
        
        # Test 5: Update form status
        print("\n=== Updating Form Status ===")
        
        await conn.execute("""
            UPDATE appointment_forms 
            SET status = 'pending_confirmation',
                updated_at = CURRENT_TIMESTAMP
            WHERE form_id = $1
        """, form_id)
        
        print(f"✅ Updated form status to pending_confirmation")
        
        # Test 6: Check expired forms
        print("\n=== Checking Expired Forms ===")
        
        expired_count = await conn.fetchval("""
            SELECT COUNT(*) FROM appointment_forms
            WHERE status IN ('draft', 'pending_confirmation')
            AND expires_at < CURRENT_TIMESTAMP
        """)
        
        print(f"Found {expired_count} expired forms")
        
        # Run cleanup function
        await conn.execute("SELECT cleanup_expired_forms()")
        print("✅ Ran cleanup function")
        
        # Test 7: Form statistics
        print("\n=== Form Statistics ===")
        
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_forms,
                COUNT(CASE WHEN status = 'draft' THEN 1 END) as draft_forms,
                COUNT(CASE WHEN status = 'pending_confirmation' THEN 1 END) as pending_forms,
                COUNT(CASE WHEN status = 'confirmed' THEN 1 END) as confirmed_forms,
                COUNT(CASE WHEN status = 'submitted' THEN 1 END) as submitted_forms,
                COUNT(CASE WHEN status = 'expired' THEN 1 END) as expired_forms,
                COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_forms
            FROM appointment_forms
        """)
        
        print(f"Total forms: {stats['total_forms']}")
        print(f"  Draft: {stats['draft_forms']}")
        print(f"  Pending: {stats['pending_forms']}")
        print(f"  Confirmed: {stats['confirmed_forms']}")
        print(f"  Submitted: {stats['submitted_forms']}")
        print(f"  Expired: {stats['expired_forms']}")
        print(f"  Cancelled: {stats['cancelled_forms']}")
        
    finally:
        await conn.close()
        print("\n✅ Database connection closed")

if __name__ == "__main__":
    print("Form System Database Integration Test")
    print("=" * 50)
    asyncio.run(test_database_form_creation())