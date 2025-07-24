#!/usr/bin/env python3
"""
Standalone test of Humansa v2 test data without any external dependencies.
"""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import test data directly
from humansa.v2.test_data import (
    DOCTORS, CLINICS, HEALTH_PACKAGES, REGIONS, INSURANCE_PROVIDERS,
    generate_appointment_slots, search_doctors, get_doctors_by_specialty,
    get_doctors_by_region, get_clinic_info
)


def test_doctors_data():
    """Test the doctors database."""
    print("\n👨‍⚕️ Testing Doctors Database")
    print("=" * 50)
    
    print(f"\nTotal doctors in database: {len(DOCTORS)}")
    
    # Show specialties
    specialties = set(d['specialty'] for d in DOCTORS)
    print(f"\nSpecialties available: {', '.join(sorted(specialties))}")
    
    # Show doctors by specialty
    print("\nDoctors by specialty:")
    for specialty in sorted(specialties):
        doctors = get_doctors_by_specialty(specialty)
        print(f"  - {specialty}: {len(doctors)} doctors")
        for doctor in doctors[:2]:
            print(f"    • {doctor['name']} ({doctor['years_experience']} years exp, Rating: {doctor['rating']}/5)")
    
    # Show language distribution
    all_languages = set()
    for doctor in DOCTORS:
        all_languages.update(doctor['languages'])
    print(f"\nLanguages supported: {', '.join(sorted(all_languages))}")


def test_clinics_data():
    """Test the clinics database."""
    print("\n\n🏥 Testing Clinics Database")
    print("=" * 50)
    
    print(f"\nTotal clinics: {len(CLINICS)}")
    
    # Show clinics by region
    print("\nClinics by region:")
    for region_id, region_info in REGIONS.items():
        region_clinics = [c for c in CLINICS if c['region'] == region_id]
        print(f"  - {region_info['name']}: {len(region_clinics)} clinics")
        for clinic in region_clinics:
            print(f"    • {clinic['name']} ({clinic['type']})")
            print(f"      Address: {clinic['address']}")


def test_appointment_generation():
    """Test appointment slot generation."""
    print("\n\n📅 Testing Appointment Generation")
    print("=" * 50)
    
    # Generate slots for first 3 doctors
    for doctor in DOCTORS[:3]:
        doctor_id = doctor['doctor_id']
        slots = generate_appointment_slots(doctor_id, days_ahead=7)
        
        available_slots = [s for s in slots if s['available']]
        print(f"\n{doctor['name']} ({doctor['specialty']}):")
        print(f"  - Total slots generated: {len(slots)}")
        print(f"  - Available slots: {len(available_slots)}")
        print(f"  - Working days: {', '.join(doctor['available_days'])}")
        
        # Show first few available slots
        print("  - Sample available times:")
        for slot in available_slots[:5]:
            print(f"    • {slot['date']} at {slot['time']} ({slot['type']}) - ${slot['consultation_fee']}")


def test_health_packages():
    """Test health screening packages."""
    print("\n\n📋 Testing Health Packages")
    print("=" * 50)
    
    print(f"\nTotal packages: {len(HEALTH_PACKAGES)}")
    
    for package in HEALTH_PACKAGES:
        print(f"\n{package['name']}:")
        print(f"  - Price: ${package['price']}")
        print(f"  - Duration: {package['duration']}")
        print(f"  - Number of tests: {len(package['tests'])}")
        print(f"  - Key tests: {', '.join(package['tests'][:3])}...")
        print(f"  - Suitable for: {', '.join(package['suitable_for'])}")


def test_search_functionality():
    """Test search functions."""
    print("\n\n🔍 Testing Search Functions")
    print("=" * 50)
    
    # Test 1: Search doctors by multiple criteria
    print("\n1. Female doctors who speak Mandarin:")
    results = search_doctors(gender="Female", language="Mandarin")
    for doctor in results[:3]:
        print(f"  - {doctor['name']} ({doctor['specialty']})")
    
    # Test 2: Search doctors in specific region
    print("\n2. Doctors in Central region:")
    results = get_doctors_by_region("central")
    for doctor in results[:3]:
        clinic = get_clinic_info(doctor['clinic_id'])
        print(f"  - {doctor['name']} at {clinic['name'] if clinic else 'Unknown'}")
    
    # Test 3: Cardiologists
    print("\n3. All Cardiologists:")
    results = get_doctors_by_specialty("Cardiology")
    for doctor in results:
        print(f"  - {doctor['name']} - {doctor['sub_specialty']}")
        print(f"    Qualifications: {', '.join(doctor['qualifications'])}")


def test_insurance_providers():
    """Test insurance data."""
    print("\n\n🏦 Testing Insurance Providers")
    print("=" * 50)
    
    print(f"\nTotal insurance providers: {len(INSURANCE_PROVIDERS)}")
    print("\nPanel providers:")
    for provider in INSURANCE_PROVIDERS:
        if provider['panel']:
            print(f"  ✓ {provider['name']} - {provider['coverage_type']}")
    
    print("\nNon-panel providers:")
    for provider in INSURANCE_PROVIDERS:
        if not provider['panel']:
            print(f"  ✗ {provider['name']} - {provider['coverage_type']}")


def test_data_completeness():
    """Test data completeness and relationships."""
    print("\n\n✅ Testing Data Completeness")
    print("=" * 50)
    
    # Check all doctors have valid clinics
    print("\nValidating doctor-clinic relationships:")
    clinic_ids = {c['clinic_id'] for c in CLINICS}
    doctors_with_invalid_clinics = []
    
    for doctor in DOCTORS:
        if doctor['clinic_id'] not in clinic_ids:
            doctors_with_invalid_clinics.append(doctor)
    
    if doctors_with_invalid_clinics:
        print(f"  ❌ {len(doctors_with_invalid_clinics)} doctors have invalid clinic IDs")
    else:
        print("  ✅ All doctors have valid clinic assignments")
    
    # Check regional coverage
    print("\nRegional coverage:")
    for region_id, region_info in REGIONS.items():
        doctors_in_region = get_doctors_by_region(region_id)
        clinics_in_region = [c for c in CLINICS if c['region'] == region_id]
        print(f"  - {region_info['name']}: {len(doctors_in_region)} doctors, {len(clinics_in_region)} clinics")
    
    # Check specialty coverage at clinics
    print("\nSpecialty coverage by clinic:")
    for clinic in CLINICS[:3]:  # Show first 3 clinics
        doctors_at_clinic = [d for d in DOCTORS if d['clinic_id'] == clinic['clinic_id']]
        specialties = set(d['specialty'] for d in doctors_at_clinic)
        print(f"  - {clinic['name']}: {', '.join(specialties) if specialties else 'No doctors assigned'}")


def main():
    """Run all tests."""
    print("🚀 Humansa v2 Test Data Validation")
    print("=" * 70)
    print(f"Timestamp: {datetime.now()}")
    
    try:
        test_doctors_data()
        test_clinics_data()
        test_appointment_generation()
        test_health_packages()
        test_search_functionality()
        test_insurance_providers()
        test_data_completeness()
        
        print("\n\n✅ All test data validation completed successfully!")
        print("\n📊 Summary:")
        print(f"  - Doctors: {len(DOCTORS)}")
        print(f"  - Clinics: {len(CLINICS)}")
        print(f"  - Regions: {len(REGIONS)}")
        print(f"  - Health Packages: {len(HEALTH_PACKAGES)}")
        print(f"  - Insurance Providers: {len(INSURANCE_PROVIDERS)}")
        
    except Exception as e:
        print(f"\n\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()