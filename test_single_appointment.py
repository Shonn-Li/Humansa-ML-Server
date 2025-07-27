#!/usr/bin/env python3
"""Test single appointment booking case (Test #12)"""

import requests
import json
from datetime import datetime, timedelta

def test_appointment_booking():
    """Test case 12: 帮我预约明天上午的骨科"""
    
    base_url = "http://localhost:5001"
    user_id = "test_user_12"
    query = "帮我预约明天上午的骨科"
    
    print(f"\n📋 Test #12: Appointment Booking")
    print(f"   User: {user_id}")
    print(f"   Query: {query}")
    print("=" * 60)
    
    # Test V2 API
    endpoint = f"{base_url}/v2/humansa/chat"
    payload = {
        "user_id": user_id,
        "messages": [{"role": "user", "content": query}],
        "stream": False
    }
    
    try:
        print("\n🔄 Sending request to V2 API...")
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract content
            if 'choices' in data and len(data['choices']) > 0:
                content = data['choices'][0]['message']['content']
                print(f"\n✅ Response received:")
                print("-" * 60)
                print(content)
                print("-" * 60)
                
                # Check for expected keywords
                expected_keywords = ['骨科', '医生', '预约', '明天', '上午']
                found_keywords = [kw for kw in expected_keywords if kw in content]
                missing_keywords = [kw for kw in expected_keywords if kw not in content]
                
                print(f"\n📊 Analysis:")
                print(f"   Found keywords: {', '.join(found_keywords)}")
                if missing_keywords:
                    print(f"   Missing keywords: {', '.join(missing_keywords)}")
                
                # Check for error indicators
                if "Reached max iterations" in content:
                    print("\n❌ ERROR: Agent reached max iterations (stuck in loop)")
                    print("   This usually indicates a database query issue")
                elif "错误" in content or "error" in content.lower():
                    print("\n❌ ERROR: Response contains error message")
                elif len(found_keywords) >= 3:
                    print("\n✅ Test appears successful - found key appointment elements")
                else:
                    print("\n⚠️  Test may have failed - missing key elements")
                    
            else:
                print("❌ No content in response")
                print(f"Full response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
        else:
            print(f"❌ API returned error status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 30 seconds")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def check_database_schema():
    """Quick check of database schema"""
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    print("\n🔍 Checking database schema...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5454,
            user='postgres',
            password='12931',
            database='test4'
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if shift_date column exists
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'humansa_schedule' 
            AND column_name IN ('shift_date', 'schedule_date')
        """)
        columns = cursor.fetchall()
        
        if columns:
            print("✅ Schedule table columns found:")
            for col in columns:
                print(f"   - {col['column_name']} ({col['data_type']})")
        else:
            print("❌ No date columns found in humansa_schedule table")
            
        # Check for orthopedic doctors
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM humansa_doctor 
            WHERE specialty = '骨科' OR name LIKE '%骨科%'
        """)
        result = cursor.fetchone()
        print(f"\n📊 Orthopedic doctors in database: {result['count']}")
        
        # Check for tomorrow's schedules
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM humansa_schedule 
            WHERE shift_date = CURRENT_DATE + INTERVAL '1 day'
            AND start_time < '12:00:00'
        """)
        result = cursor.fetchone()
        print(f"📅 Tomorrow morning schedules: {result['count']}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")

if __name__ == "__main__":
    print("🚀 Testing Humansa V2 Appointment Booking (Test #12)")
    
    # First check database
    check_database_schema()
    
    # Then run the test
    test_appointment_booking()
    
    print("\n✅ Test complete")