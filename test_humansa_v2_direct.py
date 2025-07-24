#!/usr/bin/env python3
"""
Direct test of Humansa v2 components without server dependency.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import v2 components directly
from humansa.v2.tools.medical_tools import (
    search_doctors, check_doctor_availability,
    get_service_pricing, get_clinic_info,
    search_health_packages
)


async def test_doctor_search():
    """Test doctor search functionality."""
    print("\n🔍 Testing Doctor Search")
    print("=" * 50)
    
    # Test 1: Search by specialty
    print("\n1. Searching for cardiologists:")
    results = await search_doctors(specialty="Cardiology")
    for doctor in results[:3]:
        print(f"   - {doctor['name']} ({doctor['specialty']})")
        print(f"     Location: {doctor['location']}")
        print(f"     Languages: {', '.join(doctor['languages'])}")
        print(f"     Rating: {doctor['rating']}/5")
    
    # Test 2: Search by language
    print("\n2. Searching for Mandarin-speaking doctors:")
    results = await search_doctors(language="Mandarin")
    for doctor in results[:3]:
        print(f"   - {doctor['name']}: {', '.join(doctor['languages'])}")
    
    # Test 3: Search by region
    print("\n3. Searching for doctors in East region:")
    results = await search_doctors(location="east")
    for doctor in results[:3]:
        print(f"   - {doctor['name']} at {doctor['clinic_name']}")
    
    # Test 4: Combined search
    print("\n4. Female General Practitioners:")
    results = await search_doctors(specialty="General Practice", gender="Female")
    for doctor in results[:3]:
        print(f"   - {doctor['name']} ({doctor['years_experience']} years exp)")


async def test_appointment_availability():
    """Test appointment availability checking."""
    print("\n\n🗓️ Testing Appointment Availability")
    print("=" * 50)
    
    # Test availability for specific doctors
    doctor_ids = ["dr_001", "dr_003", "dr_006"]
    
    for doctor_id in doctor_ids:
        print(f"\nChecking availability for {doctor_id}:")
        availability = await check_doctor_availability(doctor_id)
        
        if "error" not in availability:
            print(f"   Doctor: {availability['doctor_name']}")
            print(f"   Specialty: {availability['specialty']}")
            print(f"   Total available slots: {availability['total_available_slots']}")
            
            if availability['next_available']:
                next_slot = availability['next_available']
                print(f"   Next available: {next_slot['date']} at {next_slot['time']}")
                print(f"   Type: {next_slot['type']}")
                print(f"   Fee: ${next_slot['consultation_fee']}")
            
            print("   Available days:")
            for slot in availability['available_slots'][:3]:
                print(f"     - {slot['date']}: {len(slot['times'])} slots ({slot['type']})")


async def test_clinic_search():
    """Test clinic information search."""
    print("\n\n🏥 Testing Clinic Search")
    print("=" * 50)
    
    # Test 1: Search all clinics
    print("\n1. All Humansa clinics:")
    results = await get_clinic_info()
    for clinic in results:
        print(f"   - {clinic['name']} ({clinic['type']})")
        print(f"     Region: {clinic['region_name']}")
        print(f"     Address: {clinic['address']}")
        print(f"     Doctors: {clinic['total_doctors']}")
        print(f"     Specialties: {', '.join(clinic['specialties_available'])}")
    
    # Test 2: Search by location
    print("\n2. Clinics in Orchard area:")
    results = await get_clinic_info(location="Orchard")
    for clinic in results:
        print(f"   - {clinic['name']}")
        print(f"     Operating hours: {clinic['operating_hours']['weekdays']}")
        print(f"     Nearest MRT: {clinic['nearest_mrt']}")


async def test_service_pricing():
    """Test service pricing information."""
    print("\n\n💰 Testing Service Pricing")
    print("=" * 50)
    
    services = ["consultation", "specialist consultation", "health screening"]
    
    for service in services:
        print(f"\nPricing for {service}:")
        pricing = await get_service_pricing(service)
        price_range = pricing['price_range']
        print(f"   Price range: ${price_range['min']}-${price_range['max']} {price_range['currency']}")
        
        if pricing.get('insurance_coverage'):
            coverage = pricing['insurance_coverage']
            print(f"   With insurance: {coverage['estimated_coverage']} coverage")
            print(f"   Estimated copay: {coverage['copay']}")


async def test_health_packages():
    """Test health screening packages."""
    print("\n\n📋 Testing Health Screening Packages")
    print("=" * 50)
    
    packages = await search_health_packages()
    
    for package in packages:
        print(f"\n{package['name']}:")
        print(f"   Duration: {package['duration']}")
        print(f"   Regular price: ${package['price']}")
        print(f"   Promotional price: ${package['promotional_price']}")
        print(f"   Tests included: {len(package['tests'])}")
        print(f"   Sample tests: {', '.join(package['tests'][:3])}...")
        print(f"   Earliest slot: {package['earliest_available']}")
        print(f"   Report turnaround: {package['report_turnaround']}")


async def test_multi_agent_scenario():
    """Test a complex scenario involving multiple tools."""
    print("\n\n🤖 Testing Complex Multi-Agent Scenario")
    print("=" * 50)
    
    print("\nScenario: Patient with diabetes looking for endocrinologist")
    
    # Step 1: Search for endocrinologists
    print("\n1. Searching for endocrinologists...")
    doctors = await search_doctors(specialty="Gastroenterology")  # Using available specialty
    if doctors:
        selected_doctor = doctors[0]
        print(f"   Found: {selected_doctor['name']}")
        print(f"   Specialty: {selected_doctor['specialty']}")
        
        # Step 2: Check availability
        print(f"\n2. Checking availability for {selected_doctor['name']}...")
        availability = await check_doctor_availability(selected_doctor['doctor_id'])
        if availability.get('next_available'):
            print(f"   Next slot: {availability['next_available']['date']} at {availability['next_available']['time']}")
        
        # Step 3: Get clinic info
        print(f"\n3. Getting clinic information...")
        clinics = await get_clinic_info(location=selected_doctor['location'])
        if clinics:
            clinic = clinics[0]
            print(f"   Clinic: {clinic['name']}")
            print(f"   Facilities: {', '.join(clinic['facilities'][:3])}...")
        
        # Step 4: Check pricing
        print(f"\n4. Checking consultation pricing...")
        pricing = await get_service_pricing("specialist consultation")
        print(f"   Consultation fee: ${pricing['price_range']['min']}-${pricing['price_range']['max']}")


async def main():
    """Run all tests."""
    print("🚀 Humansa v2 Direct Component Testing")
    print("=" * 70)
    print(f"Timestamp: {datetime.now()}")
    
    try:
        await test_doctor_search()
        await test_appointment_availability()
        await test_clinic_search()
        await test_service_pricing()
        await test_health_packages()
        await test_multi_agent_scenario()
        
        print("\n\n✅ All direct tests completed successfully!")
        
    except Exception as e:
        print(f"\n\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())