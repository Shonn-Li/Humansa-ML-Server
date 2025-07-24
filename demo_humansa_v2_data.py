#!/usr/bin/env python3
"""
Demo of Humansa v2 test data - showing the comprehensive mock data available.
"""

from datetime import datetime, timedelta
import random
import json


def show_sample_data():
    """Show sample of the comprehensive test data."""
    
    print("🚀 Humansa v2 Test Data Demo")
    print("=" * 70)
    print(f"Timestamp: {datetime.now()}")
    
    # Sample doctor data
    print("\n\n👨‍⚕️ SAMPLE DOCTORS DATA")
    print("=" * 50)
    
    sample_doctors = [
        {
            "doctor_id": "dr_001",
            "name": "Dr. Sarah Chen Wei Lin",
            "specialty": "General Practice",
            "sub_specialty": "Family Medicine",
            "qualifications": ["MBBS (NUS)", "MCFP(S)", "GDPM"],
            "years_experience": 12,
            "languages": ["English", "Mandarin", "Hokkien"],
            "gender": "Female",
            "clinic_id": "clinic_001",
            "region": "central",
            "consultation_fee": {"min": 50, "max": 80},
            "rating": 4.8,
            "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "consultation_types": ["in-person", "telemedicine"],
            "special_interests": ["Chronic disease management", "Preventive care", "Women's health"]
        },
        {
            "doctor_id": "dr_003",
            "name": "Dr. Rajesh Kumar",
            "specialty": "Cardiology",
            "sub_specialty": "Interventional Cardiology",
            "qualifications": ["MBBS (India)", "MRCP (UK)", "FRCP (Edinburgh)", "FSCAI"],
            "years_experience": 20,
            "languages": ["English", "Hindi", "Tamil"],
            "gender": "Male",
            "clinic_id": "clinic_003",
            "region": "central",
            "consultation_fee": {"min": 180, "max": 300},
            "rating": 4.9,
            "available_days": ["Monday", "Wednesday", "Friday"],
            "consultation_types": ["in-person", "telemedicine"],
            "special_interests": ["Coronary interventions", "Heart failure", "Preventive cardiology"]
        }
    ]
    
    for doctor in sample_doctors:
        print(f"\n{doctor['name']} - {doctor['specialty']}")
        print(f"  Sub-specialty: {doctor['sub_specialty']}")
        print(f"  Experience: {doctor['years_experience']} years")
        print(f"  Languages: {', '.join(doctor['languages'])}")
        print(f"  Consultation: ${doctor['consultation_fee']['min']}-${doctor['consultation_fee']['max']}")
        print(f"  Rating: {doctor['rating']}/5")
        print(f"  Available: {', '.join(doctor['available_days'][:3])}...")
    
    # Sample clinic data
    print("\n\n🏥 SAMPLE CLINICS DATA")
    print("=" * 50)
    
    sample_clinic = {
        "clinic_id": "clinic_001",
        "name": "Humansa Medical Centre - Orchard",
        "type": "Multi-specialty Clinic",
        "region": "central",
        "address": "290 Orchard Road, #10-01 Paragon Medical Centre, Singapore 238859",
        "phone": "+65 6234 5678",
        "email": "orchard@humansa.sg",
        "operating_hours": {
            "weekdays": "8:00 AM - 9:00 PM",
            "saturday": "8:00 AM - 5:00 PM",
            "sunday": "9:00 AM - 1:00 PM"
        },
        "facilities": ["Pharmacy", "Laboratory", "X-Ray", "Ultrasound", "ECG", "Vaccination"],
        "parking": True,
        "wheelchair_accessible": True,
        "nearest_mrt": "Orchard MRT (100m)"
    }
    
    print(f"\n{sample_clinic['name']}")
    print(f"  Type: {sample_clinic['type']}")
    print(f"  Address: {sample_clinic['address']}")
    print(f"  Phone: {sample_clinic['phone']}")
    print(f"  Operating Hours:")
    for day, hours in sample_clinic['operating_hours'].items():
        print(f"    - {day.capitalize()}: {hours}")
    print(f"  Facilities: {', '.join(sample_clinic['facilities'])}")
    
    # Sample appointment slots
    print("\n\n📅 SAMPLE APPOINTMENT SLOTS")
    print("=" * 50)
    
    print(f"\nGenerating appointment slots for Dr. Sarah Chen:")
    for i in range(5):
        date = datetime.now() + timedelta(days=i+1)
        if date.weekday() < 5:  # Weekdays only
            available = random.random() > 0.3
            print(f"  {date.strftime('%Y-%m-%d')} ({date.strftime('%A')})")
            times = ["09:00", "09:30", "10:00", "14:00", "15:00", "16:00"]
            available_times = [t for t in times if random.random() > 0.3]
            for time in available_times[:3]:
                print(f"    - {time}: {'Available' if available else 'Booked'} (${random.randint(50, 80)})")
    
    # Singapore regions
    print("\n\n🗺️ SINGAPORE REGIONS")
    print("=" * 50)
    
    regions = {
        "central": {
            "name": "Central Region",
            "districts": ["Orchard", "Marina Bay", "Tanjong Pagar", "Chinatown", "Clarke Quay"]
        },
        "east": {
            "name": "East Region", 
            "districts": ["Tampines", "Pasir Ris", "Bedok", "Changi", "Simei"]
        },
        "west": {
            "name": "West Region",
            "districts": ["Jurong", "Clementi", "Bukit Batok", "Choa Chu Kang", "Woodlands"]
        }
    }
    
    for region_id, info in regions.items():
        print(f"\n{info['name']}:")
        print(f"  Districts: {', '.join(info['districts'])}")
    
    # Health screening packages
    print("\n\n📋 HEALTH SCREENING PACKAGES")
    print("=" * 50)
    
    package = {
        "package_id": "pkg_comprehensive",
        "name": "Comprehensive Health Screening",
        "price": 480,
        "duration": "4 hours",
        "tests": [
            "Complete Blood Count (CBC)",
            "Lipid Profile",
            "Liver Function Test",
            "Kidney Function Test",
            "Thyroid Function Test",
            "Cancer Markers (AFP, CEA, CA19-9)",
            "Chest X-Ray",
            "Resting ECG",
            "Ultrasound Abdomen",
            "Doctor Consultation & Report"
        ]
    }
    
    print(f"\n{package['name']}")
    print(f"  Price: ${package['price']}")
    print(f"  Duration: {package['duration']}")
    print(f"  Tests included ({len(package['tests'])}):")
    for test in package['tests'][:5]:
        print(f"    • {test}")
    print("    • ... and more")
    
    print("\n\n✅ This demo shows the comprehensive test data available in Humansa v2:")
    print("  - 10 doctors across various specialties")
    print("  - 5 clinics in different regions")
    print("  - Dynamic appointment slot generation")
    print("  - 3 health screening packages")
    print("  - 6 insurance providers")
    print("  - Complete Singapore regional coverage")


if __name__ == "__main__":
    show_sample_data()