#!/usr/bin/env python3
"""Direct database connection test for Humansa test environment."""

import os
import asyncio
import asyncpg
import json
from datetime import datetime

async def test_database():
    """Test direct database connection and query data."""
    
    # Connection parameters
    host = os.getenv('DB_HOST', 'localhost')
    port = int(os.getenv('DB_PORT', '5456'))
    database = os.getenv('DB_NAME', 'youwoai')
    user = os.getenv('DB_USER', 'youwo')
    password = os.getenv('DB_PASSWORD', 'youwo123')
    
    print("🏥 Humansa Database Direct Test")
    print("=" * 50)
    print(f"Connection: {host}:{port}/{database}")
    print()
    
    try:
        # Create connection
        conn = await asyncpg.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        print("✅ Connected to database successfully!")
        print()
        
        # Test 1: Check doctors
        print("👨‍⚕️ DOCTORS IN DATABASE:")
        print("-" * 40)
        doctors = await conn.fetch("""
            SELECT doctor_id, name, specialty, languages, consultation_fee_range 
            FROM humansa_doctors 
            ORDER BY name
        """)
        for doc in doctors[:5]:  # Show first 5
            print(f"• {doc['name']} - {doc['specialty']}")
            print(f"  Languages: {', '.join(doc['languages'])}")
            print(f"  Fee: ${doc['consultation_fee_range'][0]}-${doc['consultation_fee_range'][1]}")
            print()
        print(f"Total doctors: {len(doctors)}")
        print()
        
        # Test 2: Check clinics
        print("🏥 CLINICS IN DATABASE:")
        print("-" * 40)
        clinics = await conn.fetch("""
            SELECT clinic_id, name, type, address, region 
            FROM humansa_clinics 
            ORDER BY name
        """)
        for clinic in clinics:
            print(f"• {clinic['name']} ({clinic['type']})")
            print(f"  Region: {clinic['region']}")
            print(f"  Address: {clinic['address']}")
            print()
        print(f"Total clinics: {len(clinics)}")
        print()
        
        # Test 3: Check appointment slots
        print("📅 SAMPLE APPOINTMENT SLOTS:")
        print("-" * 40)
        slots = await conn.fetch("""
            SELECT s.*, d.name as doctor_name 
            FROM humansa_appointment_slots s
            JOIN humansa_doctors d ON s.doctor_id = d.doctor_id
            WHERE s.status = 'available' 
            AND s.appointment_datetime > NOW()
            ORDER BY s.appointment_datetime
            LIMIT 10
        """)
        for slot in slots[:5]:
            dt = slot['appointment_datetime']
            print(f"• {slot['doctor_name']} - {dt.strftime('%Y-%m-%d %H:%M')}")
            print(f"  Type: {slot['appointment_type']}, Price: ${slot['price']}")
        print(f"\nTotal available future slots: {len(slots)}+")
        print()
        
        # Test 4: Check health packages
        print("📋 HEALTH PACKAGES:")
        print("-" * 40)
        packages = await conn.fetch("""
            SELECT package_id, name, price, duration_hours 
            FROM humansa_health_packages 
            ORDER BY price
        """)
        for pkg in packages:
            print(f"• {pkg['name']} - ${pkg['price']} ({pkg['duration_hours']}h)")
        print()
        
        # Test 5: Check table counts
        print("📊 DATABASE STATISTICS:")
        print("-" * 40)
        tables = [
            'humansa_doctors',
            'humansa_clinics', 
            'humansa_appointment_slots',
            'humansa_health_packages',
            'humansa_insurance_providers',
            'humansa_regions'
        ]
        
        for table in tables:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            print(f"• {table}: {count} records")
        
        await conn.close()
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(test_database())