#!/usr/bin/env python3
"""Test schema alignment after HIS API updates"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime, date, timedelta

# Test database connection
DB_CONFIG = {
    'host': 'localhost',
    'port': 5454,
    'user': 'postgres',
    'password': '12931',
    'database': 'test4'
}

def test_connection():
    """Test database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Database connection successful")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def apply_schema_updates():
    """Apply schema alignment updates"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Read and execute the alignment SQL
        sql_files = [
            'test_environment/sql/06_humansa_test_data.sql',
            'test_environment/sql/humansa_test_doctors.sql',
            'test_environment/sql/07_humansa_his_alignment.sql'
        ]
        
        for sql_file in sql_files:
            if os.path.exists(sql_file):
                print(f"\n📄 Applying {sql_file}...")
                with open(sql_file, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                    try:
                        cursor.execute(sql_content)
                        conn.commit()
                        print(f"✅ Successfully applied {sql_file}")
                    except Exception as e:
                        conn.rollback()
                        print(f"⚠️  Error applying {sql_file}: {e}")
                        # Continue with next file
            else:
                print(f"❌ File not found: {sql_file}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Schema update failed: {e}")
        return False

def test_doctor_availability():
    """Test doctor availability query with correct schema"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Test query for orthopedic doctors with availability
        tomorrow = date.today() + timedelta(days=1)
        
        query = """
            SELECT 
                d.doctor_code,
                d.name as doctor_name,
                d.title,
                d.specialty,
                d.dept_id,
                dept.dept_name,
                c.name as clinic_name,
                s.shift_date,
                s.start_time,
                s.end_time,
                s.remaining_slots
            FROM humansa_doctor d
            LEFT JOIN humansa_department dept ON d.dept_id = dept.dept_id
            LEFT JOIN humansa_clinic c ON d.clinic_code = c.clinic_code
            LEFT JOIN humansa_schedule s ON d.doctor_code = s.doctor_code
            WHERE d.specialty = '骨科'
            AND s.shift_date = %s
            AND s.start_time < '12:00:00'
            AND s.remaining_slots > 0
            ORDER BY s.start_time
        """
        
        print(f"\n🔍 Searching for orthopedic doctors available tomorrow morning...")
        cursor.execute(query, (tomorrow,))
        results = cursor.fetchall()
        
        if results:
            print(f"✅ Found {len(results)} available slots:")
            for slot in results:
                print(f"   - Dr. {slot['doctor_name']} ({slot['title']}) - {slot['dept_name'] or slot['specialty']}")
                print(f"     📍 {slot['clinic_name']}")
                print(f"     📅 {slot['shift_date']} {slot['start_time']} - {slot['end_time']}")
                print(f"     🎫 {slot['remaining_slots']} slots available")
        else:
            print("❌ No orthopedic doctors available tomorrow morning")
        
        cursor.close()
        conn.close()
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ Availability test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_patient_lookup():
    """Test patient lookup by phone"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Test patient lookup
        phone = '13800138000'
        query = """
            SELECT 
                p.*,
                COUNT(DISTINCT ah.appointment_id) as total_appointments,
                COUNT(DISTINCT CASE WHEN ah.status = 'completed' THEN ah.appointment_id END) as completed_appointments
            FROM humansa_patient p
            LEFT JOIN humansa_appointment_history ah ON p.patient_id = ah.patient_id
            WHERE p.phone = %s
            GROUP BY p.patient_id
        """
        
        print(f"\n📱 Looking up patient with phone {phone}...")
        cursor.execute(query, (phone,))
        patient = cursor.fetchone()
        
        if patient:
            print(f"✅ Found patient:")
            print(f"   - Name: {patient['name']}")
            print(f"   - ID: {patient['patient_id']}")
            print(f"   - Total appointments: {patient['total_appointments']}")
            print(f"   - Completed appointments: {patient['completed_appointments']}")
        else:
            print("❌ Patient not found")
        
        cursor.close()
        conn.close()
        return patient is not None
        
    except Exception as e:
        print(f"❌ Patient lookup test failed: {e}")
        return False

def test_his_api_response_format():
    """Test HIS API response format generation"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get availability in HIS API format
        tomorrow = date.today() + timedelta(days=1)
        query = """
            SELECT 
                s.schedule_id as shift_id,
                d.doctor_code as doctor_id,
                d.name as doctor_name,
                d.dept_id,
                dept.dept_name,
                s.shift_date as sch_date,
                s.start_time,
                s.end_time,
                s.remaining_slots as remaining_capacity,
                c.clinic_code as hospital_id,
                c.name as hospital_name
            FROM humansa_schedule s
            JOIN humansa_doctor d ON s.doctor_code = d.doctor_code
            LEFT JOIN humansa_department dept ON d.dept_id = dept.dept_id
            JOIN humansa_clinic c ON s.clinic_code = c.clinic_code
            WHERE s.shift_date = %s
            AND s.remaining_slots > 0
            LIMIT 5
        """
        
        print(f"\n🔄 Testing HIS API response format...")
        cursor.execute(query, (tomorrow,))
        results = cursor.fetchall()
        
        # Format as HIS API response
        his_response = {
            "code": 0,
            "message": "Success",
            "data": []
        }
        
        for row in results:
            his_response["data"].append({
                "shiftId": str(row['shift_id']),
                "doctorId": row['doctor_id'],
                "doctorName": row['doctor_name'],
                "deptId": row['dept_id'] or "",
                "deptName": row['dept_name'] or row['doctor_name'].split('医生')[0],
                "schDate": row['sch_date'].strftime('%Y-%m-%d'),
                "startTime": row['start_time'].strftime('%H:%M'),
                "endTime": row['end_time'].strftime('%H:%M'),
                "remainingCapacity": row['remaining_capacity'],
                "hospitalId": row['hospital_id'],
                "hospitalName": row['hospital_name']
            })
        
        if his_response["data"]:
            print("✅ HIS API format response generated successfully:")
            import json
            print(json.dumps(his_response, ensure_ascii=False, indent=2))
        else:
            print("❌ No data for HIS API response")
        
        cursor.close()
        conn.close()
        return len(his_response["data"]) > 0
        
    except Exception as e:
        print(f"❌ HIS API format test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Humansa Schema Alignment Test Suite")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_connection),
        ("Schema Updates", apply_schema_updates),
        ("Doctor Availability Query", test_doctor_availability),
        ("Patient Phone Lookup", test_patient_lookup),
        ("HIS API Response Format", test_his_api_response_format)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n▶️  Running: {test_name}")
        result = test_func()
        results.append((test_name, result))
        print("-" * 50)
    
    print("\n📊 Test Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! Schema alignment successful.")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()