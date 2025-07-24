"""
Test data for Humansa v2 system - Realistic mock data for Singapore healthcare.
"""

from datetime import datetime, timedelta
import random
from typing import Dict, List, Any

# Singapore regions
REGIONS = {
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
    },
    "north": {
        "name": "North Region",
        "districts": ["Ang Mo Kio", "Bishan", "Yishun", "Sembawang", "Sengkang"]
    },
    "northeast": {
        "name": "Northeast Region",
        "districts": ["Punggol", "Hougang", "Serangoon", "Seletar", "Buangkok"]
    }
}

# Comprehensive doctor database
DOCTORS = [
    # General Practitioners
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
        "doctor_id": "dr_002",
        "name": "Dr. Michael Wong Kah Meng",
        "specialty": "General Practice",
        "sub_specialty": "Sports Medicine",
        "qualifications": ["MBBS (Singapore)", "MMed (Family Medicine)", "Dip Sports Med"],
        "years_experience": 8,
        "languages": ["English", "Cantonese", "Malay"],
        "gender": "Male",
        "clinic_id": "clinic_002",
        "region": "east",
        "consultation_fee": {"min": 45, "max": 70},
        "rating": 4.6,
        "available_days": ["Monday", "Tuesday", "Thursday", "Friday", "Saturday"],
        "consultation_types": ["in-person"],
        "special_interests": ["Sports injuries", "Rehabilitation", "Musculoskeletal conditions"]
    },
    
    # Specialists - Cardiology
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
    },
    {
        "doctor_id": "dr_004",
        "name": "Dr. Jennifer Tan Hui Min",
        "specialty": "Cardiology",
        "sub_specialty": "Cardiac Electrophysiology",
        "qualifications": ["MBBS (Melbourne)", "FRACP", "PhD (Cardiac Sciences)"],
        "years_experience": 15,
        "languages": ["English", "Mandarin", "Teochew"],
        "gender": "Female",
        "clinic_id": "clinic_003",
        "region": "central",
        "consultation_fee": {"min": 200, "max": 350},
        "rating": 4.8,
        "available_days": ["Tuesday", "Thursday", "Saturday"],
        "consultation_types": ["in-person"],
        "special_interests": ["Arrhythmias", "Pacemaker implantation", "Atrial fibrillation"]
    },
    
    # Dermatology
    {
        "doctor_id": "dr_005",
        "name": "Dr. Amanda Lim Xin Yi",
        "specialty": "Dermatology",
        "sub_specialty": "Cosmetic Dermatology",
        "qualifications": ["MBBS (London)", "MRCP (UK)", "MMed (Int Med)", "FAMS (Dermatology)"],
        "years_experience": 10,
        "languages": ["English", "Mandarin"],
        "gender": "Female",
        "clinic_id": "clinic_004",
        "region": "west",
        "consultation_fee": {"min": 150, "max": 250},
        "rating": 4.7,
        "available_days": ["Monday", "Wednesday", "Thursday", "Friday"],
        "consultation_types": ["in-person", "telemedicine"],
        "special_interests": ["Acne treatment", "Skin cancer screening", "Aesthetic procedures"]
    },
    
    # Pediatrics
    {
        "doctor_id": "dr_006",
        "name": "Dr. David Lee Wei Jie",
        "specialty": "Pediatrics",
        "sub_specialty": "Pediatric Allergy & Immunology",
        "qualifications": ["MBBS (NUS)", "MRCPCH (UK)", "FAMS (Paediatrics)"],
        "years_experience": 14,
        "languages": ["English", "Mandarin", "Hokkien"],
        "gender": "Male",
        "clinic_id": "clinic_005",
        "region": "north",
        "consultation_fee": {"min": 100, "max": 180},
        "rating": 4.9,
        "available_days": ["Monday", "Tuesday", "Wednesday", "Friday", "Saturday"],
        "consultation_types": ["in-person"],
        "special_interests": ["Childhood allergies", "Asthma", "Immunodeficiency disorders"]
    },
    
    # Orthopedics
    {
        "doctor_id": "dr_007",
        "name": "Dr. Marcus Chong Boon Keng",
        "specialty": "Orthopedic Surgery",
        "sub_specialty": "Sports Orthopedics",
        "qualifications": ["MBBS (Australia)", "FRCS (Edinburgh)", "FAOrthA"],
        "years_experience": 18,
        "languages": ["English", "Mandarin", "Cantonese"],
        "gender": "Male",
        "clinic_id": "clinic_006",
        "region": "northeast",
        "consultation_fee": {"min": 200, "max": 400},
        "rating": 4.8,
        "available_days": ["Tuesday", "Thursday", "Friday"],
        "consultation_types": ["in-person"],
        "special_interests": ["ACL reconstruction", "Shoulder arthroscopy", "Joint replacement"]
    },
    
    # Gastroenterology
    {
        "doctor_id": "dr_008",
        "name": "Dr. Priya Nair",
        "specialty": "Gastroenterology",
        "sub_specialty": "Hepatology",
        "qualifications": ["MBBS (India)", "MD (Internal Medicine)", "DM (Gastro)", "FRCP"],
        "years_experience": 16,
        "languages": ["English", "Hindi", "Malayalam"],
        "gender": "Female",
        "clinic_id": "clinic_007",
        "region": "east",
        "consultation_fee": {"min": 180, "max": 280},
        "rating": 4.7,
        "available_days": ["Monday", "Wednesday", "Thursday", "Saturday"],
        "consultation_types": ["in-person", "telemedicine"],
        "special_interests": ["Liver diseases", "IBD", "Endoscopy procedures"]
    },
    
    # Psychiatry
    {
        "doctor_id": "dr_009",
        "name": "Dr. Jonathan Ng Jun Wei",
        "specialty": "Psychiatry",
        "sub_specialty": "Adult Psychiatry",
        "qualifications": ["MBBS (UK)", "MRCPsych", "MMed (Psychiatry)"],
        "years_experience": 12,
        "languages": ["English", "Mandarin"],
        "gender": "Male",
        "clinic_id": "clinic_008",
        "region": "central",
        "consultation_fee": {"min": 200, "max": 350},
        "rating": 4.8,
        "available_days": ["Monday", "Tuesday", "Thursday", "Friday"],
        "consultation_types": ["in-person", "telemedicine"],
        "special_interests": ["Depression", "Anxiety disorders", "Bipolar disorder"]
    },
    
    # Obstetrics & Gynecology
    {
        "doctor_id": "dr_010",
        "name": "Dr. Grace Ong Mei Ling",
        "specialty": "Obstetrics & Gynecology",
        "sub_specialty": "Maternal-Fetal Medicine",
        "qualifications": ["MBBS (Singapore)", "MRCOG (UK)", "FAMS (O&G)"],
        "years_experience": 15,
        "languages": ["English", "Mandarin", "Teochew"],
        "gender": "Female",
        "clinic_id": "clinic_009",
        "region": "west",
        "consultation_fee": {"min": 150, "max": 300},
        "rating": 4.9,
        "available_days": ["Monday", "Tuesday", "Wednesday", "Friday"],
        "consultation_types": ["in-person"],
        "special_interests": ["High-risk pregnancy", "Prenatal diagnosis", "Women's health"]
    }
]

# Comprehensive clinic database
CLINICS = [
    {
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
    },
    {
        "clinic_id": "clinic_002",
        "name": "Humansa Family Clinic - Tampines",
        "type": "Family Medicine Clinic",
        "region": "east",
        "address": "825 Tampines Street 81, #01-50, Singapore 520825",
        "phone": "+65 6785 4321",
        "email": "tampines@humansa.sg",
        "operating_hours": {
            "weekdays": "8:30 AM - 8:00 PM",
            "saturday": "8:30 AM - 2:00 PM",
            "sunday": "Closed"
        },
        "facilities": ["Pharmacy", "Basic Laboratory", "Vaccination"],
        "parking": True,
        "wheelchair_accessible": True,
        "nearest_mrt": "Tampines MRT (500m)"
    },
    {
        "clinic_id": "clinic_003",
        "name": "Humansa Heart & Vascular Centre",
        "type": "Specialist Centre",
        "region": "central",
        "address": "3 Mount Elizabeth, #14-08 Mount Elizabeth Medical Centre, Singapore 228510",
        "phone": "+65 6235 8888",
        "email": "heart@humansa.sg",
        "operating_hours": {
            "weekdays": "9:00 AM - 6:00 PM",
            "saturday": "9:00 AM - 1:00 PM",
            "sunday": "Closed"
        },
        "facilities": ["Cardiac Lab", "Echo Suite", "Stress Test Room", "CT Angiography"],
        "parking": True,
        "wheelchair_accessible": True,
        "nearest_mrt": "Orchard MRT (400m)"
    },
    {
        "clinic_id": "clinic_004",
        "name": "Humansa Skin & Laser Clinic",
        "type": "Specialist Clinic",
        "region": "west",
        "address": "1 Jurong West Central 2, #07-01 Jurong Point, Singapore 648886",
        "phone": "+65 6795 5555",
        "email": "skin@humansa.sg",
        "operating_hours": {
            "weekdays": "10:00 AM - 8:00 PM",
            "saturday": "10:00 AM - 5:00 PM",
            "sunday": "Closed"
        },
        "facilities": ["Laser Suite", "Treatment Rooms", "Skin Analysis Lab"],
        "parking": True,
        "wheelchair_accessible": True,
        "nearest_mrt": "Boon Lay MRT (300m)"
    },
    {
        "clinic_id": "clinic_005",
        "name": "Humansa Children's Clinic - AMK",
        "type": "Pediatric Clinic",
        "region": "north",
        "address": "53 Ang Mo Kio Ave 3, #02-45 AMK Hub, Singapore 569933",
        "phone": "+65 6555 1234",
        "email": "kids@humansa.sg",
        "operating_hours": {
            "weekdays": "9:00 AM - 9:00 PM",
            "saturday": "9:00 AM - 5:00 PM",
            "sunday": "9:00 AM - 1:00 PM"
        },
        "facilities": ["Play Area", "Vaccination Room", "Nebulizer Station", "Breastfeeding Room"],
        "parking": True,
        "wheelchair_accessible": True,
        "nearest_mrt": "Ang Mo Kio MRT (Direct)"
    }
]

# Health screening packages
HEALTH_PACKAGES = [
    {
        "package_id": "pkg_basic",
        "name": "Basic Health Screening",
        "price": 180,
        "duration": "2 hours",
        "tests": [
            "Complete Blood Count (CBC)",
            "Lipid Profile",
            "Liver Function Test",
            "Kidney Function Test",
            "Fasting Blood Glucose",
            "Urine FEME",
            "Blood Pressure",
            "BMI Calculation"
        ],
        "suitable_for": ["Adults 18-39", "Annual checkup"],
        "preparation": ["Fast for 8-10 hours", "Bring previous medical records"]
    },
    {
        "package_id": "pkg_comprehensive",
        "name": "Comprehensive Health Screening",
        "price": 480,
        "duration": "4 hours",
        "tests": [
            "All Basic Screening tests",
            "Thyroid Function Test",
            "Hepatitis B & C Screening",
            "Cancer Markers (AFP, CEA, CA19-9)",
            "Chest X-Ray",
            "Resting ECG",
            "Ultrasound Abdomen",
            "Bone Mineral Density (DEXA)",
            "Doctor Consultation & Report"
        ],
        "suitable_for": ["Adults 40+", "Pre-employment", "Executive screening"],
        "preparation": ["Fast for 10-12 hours", "Wear comfortable clothing", "Avoid alcohol 24 hours before"]
    },
    {
        "package_id": "pkg_cardiac",
        "name": "Cardiac Risk Assessment",
        "price": 680,
        "duration": "3 hours",
        "tests": [
            "Lipid Profile (Advanced)",
            "HbA1c",
            "High-sensitivity CRP",
            "Homocysteine",
            "Resting & Stress ECG",
            "Echocardiogram",
            "Coronary Calcium Score",
            "Cardiologist Consultation"
        ],
        "suitable_for": ["Family history of heart disease", "Diabetics", "High cholesterol"],
        "preparation": ["Fast for 8 hours", "Bring list of current medications", "Wear sports attire"]
    }
]

# Insurance providers
INSURANCE_PROVIDERS = [
    {"name": "AIA", "coverage_type": "Integrated Shield Plan", "panel": True},
    {"name": "Great Eastern", "coverage_type": "Supreme Health", "panel": True},
    {"name": "Prudential", "coverage_type": "PRUShield", "panel": True},
    {"name": "NTUC Income", "coverage_type": "Enhanced IncomeShield", "panel": True},
    {"name": "AXA", "coverage_type": "Shield Plan", "panel": False},
    {"name": "Raffles Health", "coverage_type": "Corporate Plan", "panel": True}
]


def generate_appointment_slots(doctor_id: str, days_ahead: int = 14) -> List[Dict[str, Any]]:
    """Generate available appointment slots for a doctor."""
    doctor = next((d for d in DOCTORS if d["doctor_id"] == doctor_id), None)
    if not doctor:
        return []
    
    slots = []
    current_date = datetime.now().date()
    
    for i in range(days_ahead):
        date = current_date + timedelta(days=i)
        weekday = date.strftime("%A")
        
        # Skip if doctor doesn't work on this day
        if weekday not in doctor["available_days"]:
            continue
            
        # Skip Sundays for most doctors
        if weekday == "Sunday" and doctor["specialty"] != "General Practice":
            continue
        
        # Generate time slots based on specialty
        if doctor["specialty"] == "General Practice":
            time_slots = ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
                         "14:00", "14:30", "15:00", "15:30", "16:00", "16:30"]
        else:
            # Specialists have fewer slots
            time_slots = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
        
        for time in time_slots:
            # Randomly mark some slots as unavailable (30% chance)
            available = random.random() > 0.3
            
            slot = {
                "slot_id": f"slot_{doctor_id}_{date.strftime('%Y%m%d')}_{time.replace(':', '')}",
                "doctor_id": doctor_id,
                "date": date.strftime("%Y-%m-%d"),
                "time": time,
                "duration_minutes": 30 if doctor["specialty"] == "General Practice" else 45,
                "available": available,
                "type": random.choice(doctor["consultation_types"]),
                "consultation_fee": random.randint(
                    doctor["consultation_fee"]["min"],
                    doctor["consultation_fee"]["max"]
                )
            }
            
            slots.append(slot)
    
    return slots


def get_doctors_by_specialty(specialty: str) -> List[Dict[str, Any]]:
    """Get all doctors for a specific specialty."""
    return [d for d in DOCTORS if specialty.lower() in d["specialty"].lower()]


def get_doctors_by_region(region: str) -> List[Dict[str, Any]]:
    """Get all doctors in a specific region."""
    return [d for d in DOCTORS if d["region"] == region.lower()]


def get_clinic_info(clinic_id: str) -> Dict[str, Any]:
    """Get detailed clinic information."""
    return next((c for c in CLINICS if c["clinic_id"] == clinic_id), None)


def search_doctors(
    specialty: str = None,
    region: str = None,
    gender: str = None,
    language: str = None
) -> List[Dict[str, Any]]:
    """Search doctors with multiple criteria."""
    results = DOCTORS.copy()
    
    if specialty:
        results = [d for d in results if specialty.lower() in d["specialty"].lower()]
    if region:
        results = [d for d in results if d["region"] == region.lower()]
    if gender:
        results = [d for d in results if d["gender"].lower() == gender.lower()]
    if language:
        results = [d for d in results if language in d["languages"]]
        
    return results