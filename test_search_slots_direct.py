#!/usr/bin/env python
"""Test search_available_slots function directly"""

import asyncio
import sys
import os

# Add the src directory to the Python path so we can import the function
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from humansa.v2.agents.appointment_agent import search_available_slots

async def test_search_slots():
    """Test the search_available_slots function directly"""
    
    print("🔍 Testing search_available_slots function...")
    
    # Test 1: Search for cardiology without parameters
    print("\n📋 Test 1: Search cardiology (心内科)")
    try:
        slots = await search_available_slots(specialty="心内科")
        print(f"✅ Found {len(slots)} slots")
        if slots:
            for i, slot in enumerate(slots[:3], 1):
                print(f"  {i}. {slot['doctor_name']} - {slot['date']} {slot['time']} - {slot['clinic_name']} - ¥{slot['consultation_fee']}")
        else:
            print("❌ No slots returned")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Search with no parameters (should show all available)
    print("\n📋 Test 2: Search all available slots")
    try:
        slots = await search_available_slots()
        print(f"✅ Found {len(slots)} slots")
        if slots:
            for i, slot in enumerate(slots[:3], 1):
                print(f"  {i}. {slot['doctor_name']} ({slot['specialty']}) - {slot['date']} {slot['time']} - {slot['clinic_name']}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Search for tomorrow specifically
    print("\n📋 Test 3: Search for tomorrow (2025-08-02)")
    try:
        slots = await search_available_slots(date_from="2025-08-02", date_to="2025-08-02")
        print(f"✅ Found {len(slots)} slots for tomorrow")
        if slots:
            for i, slot in enumerate(slots[:3], 1):
                print(f"  {i}. {slot['doctor_name']} ({slot['specialty']}) - {slot['time']} - {slot['clinic_name']}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search_slots())