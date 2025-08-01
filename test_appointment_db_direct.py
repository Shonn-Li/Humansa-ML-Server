#!/usr/bin/env python
"""Test appointment database connection directly"""

import asyncio
import asyncpg
from datetime import datetime, timedelta

async def test_appointment_db():
    """Test direct database connection for appointments"""
    
    # Database connection parameters
    db_config = {
        'host': 'localhost',
        'port': 5454,
        'user': 'postgres',
        'password': '12931',
        'database': 'test4'
    }
    
    print("🔍 Testing appointment database connection...")
    
    try:
        conn = await asyncpg.connect(**db_config)
        
        # Test 1: Check available slots for cardiology
        print("\n📋 Test 1: Cardiology slots")
        query = """
        SELECT 
            s.slot_id,
            s.doctor_id,
            d.name as doctor_name,
            d.specialty,
            s.date,
            s.time,
            s.consultation_fee,
            c.name as clinic_name
        FROM humansa_appointment_slots s
        JOIN humansa_doctor d ON s.doctor_id = d.doctor_code
        LEFT JOIN humansa_clinics c ON s.clinic_id = c.clinic_code
        WHERE s.is_available = true 
        AND d.specialty ILIKE '%心内科%'
        AND s.date > CURRENT_DATE
        ORDER BY s.date, s.time
        LIMIT 5
        """
        
        rows = await conn.fetch(query)
        if rows:
            print(f"✅ Found {len(rows)} cardiology slots:")
            for row in rows:
                print(f"  - {row['doctor_name']} ({row['specialty']}) - {row['date']} {row['time']} - {row['clinic_name']} - ¥{row['consultation_fee']}")
        else:
            print("❌ No cardiology slots found")
        
        # Test 2: Check all available specialties
        print("\n📋 Test 2: Available specialties")
        specialty_query = """
        SELECT d.specialty, COUNT(*) as available_slots
        FROM humansa_appointment_slots s
        JOIN humansa_doctor d ON s.doctor_id = d.doctor_code
        WHERE s.is_available = true AND s.date > CURRENT_DATE
        GROUP BY d.specialty
        ORDER BY available_slots DESC
        """
        
        specialty_rows = await conn.fetch(specialty_query)
        if specialty_rows:
            print(f"✅ Available specialties:")
            for row in specialty_rows:
                print(f"  - {row['specialty']}: {row['available_slots']} slots")
        
        # Test 3: Check dates range
        print("\n📋 Test 3: Date range")
        date_query = """
        SELECT MIN(date) as earliest, MAX(date) as latest, COUNT(*) as total
        FROM humansa_appointment_slots 
        WHERE is_available = true AND date > CURRENT_DATE
        """
        
        date_row = await conn.fetchrow(date_query)
        if date_row:
            print(f"✅ Date range: {date_row['earliest']} to {date_row['latest']} ({date_row['total']} total slots)")
        
        await conn.close()
        print("\n✅ Database connection test successful!")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_appointment_db())