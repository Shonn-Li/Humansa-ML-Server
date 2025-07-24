from typing import Dict, Any, List, Optional
import json
from datetime import datetime, timedelta
from ..test_data import (
    DOCTORS, CLINICS, HEALTH_PACKAGES, REGIONS,
    generate_appointment_slots, search_doctors as search_doctors_data,
    get_clinic_info as get_clinic_data
)


async def search_doctors(
    specialty: Optional[str] = None,
    name: Optional[str] = None,
    location: Optional[str] = None,
    language: Optional[str] = None,
    gender: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search for doctors based on criteria."""
    # Use the comprehensive test data
    results = search_doctors_data(
        specialty=specialty,
        region=location,
        gender=gender,
        language=language
    )
    
    # Additional filtering by name if provided
    if name:
        results = [d for d in results if name.lower() in d["name"].lower()]
    
    # Format the results with additional info
    formatted_results = []
    for doctor in results:
        clinic = get_clinic_data(doctor["clinic_id"])
        formatted_results.append({
            "doctor_id": doctor["doctor_id"],
            "name": doctor["name"],
            "specialty": doctor["specialty"],
            "sub_specialty": doctor.get("sub_specialty", ""),
            "qualifications": doctor["qualifications"],
            "languages": doctor["languages"],
            "gender": doctor["gender"],
            "clinic_name": clinic["name"] if clinic else "Unknown",
            "location": clinic["region"] if clinic else doctor["region"],
            "address": clinic["address"] if clinic else "Address not available",
            "rating": doctor["rating"],
            "years_experience": doctor["years_experience"],
            "consultation_fee": doctor["consultation_fee"],
            "consultation_types": doctor["consultation_types"],
            "availability_status": "Available"
        })
        
    return formatted_results


async def check_doctor_availability(
    doctor_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Dict[str, Any]:
    """Check doctor availability for specific dates."""
    if not date_from:
        date_from = datetime.now().strftime("%Y-%m-%d")
    if not date_to:
        date_to = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    
    # Get doctor info
    doctor = next((d for d in DOCTORS if d["doctor_id"] == doctor_id), None)
    if not doctor:
        return {"error": "Doctor not found"}
    
    # Generate appointment slots
    all_slots = generate_appointment_slots(doctor_id, days_ahead=14)
    
    # Filter slots by date range
    start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
    end_date = datetime.strptime(date_to, "%Y-%m-%d").date()
    
    filtered_slots = [
        slot for slot in all_slots
        if start_date <= datetime.strptime(slot["date"], "%Y-%m-%d").date() <= end_date
    ]
    
    # Group by date
    availability_by_date = {}
    for slot in filtered_slots:
        if slot["available"]:
            date = slot["date"]
            if date not in availability_by_date:
                availability_by_date[date] = {
                    "date": date,
                    "times": [],
                    "types": set()
                }
            availability_by_date[date]["times"].append(slot["time"])
            availability_by_date[date]["types"].add(slot["type"])
    
    # Convert to list format
    available_slots = []
    for date, info in sorted(availability_by_date.items()):
        available_slots.append({
            "date": info["date"],
            "times": sorted(info["times"]),
            "type": "both" if len(info["types"]) > 1 else list(info["types"])[0]
        })
    
    # Find next available slot
    next_available = None
    for slot in sorted(filtered_slots, key=lambda x: (x["date"], x["time"])):
        if slot["available"]:
            next_available = {
                "date": slot["date"],
                "time": slot["time"],
                "type": slot["type"],
                "consultation_fee": slot["consultation_fee"]
            }
            break
    
    return {
        "doctor_id": doctor_id,
        "doctor_name": doctor["name"],
        "specialty": doctor["specialty"],
        "date_range": {
            "from": date_from,
            "to": date_to
        },
        "available_slots": available_slots[:7],  # Limit to 7 days for readability
        "next_available": next_available,
        "total_available_slots": sum(len(slot["times"]) for slot in available_slots)
    }


async def get_service_pricing(
    service_type: str,
    doctor_id: Optional[str] = None,
    insurance_provider: Optional[str] = None
) -> Dict[str, Any]:
    """Get pricing information for medical services."""
    # Base pricing structure
    base_prices = {
        "consultation": {"min": 80, "max": 150},
        "specialist_consultation": {"min": 120, "max": 250},
        "health_screening": {"min": 200, "max": 500},
        "vaccination": {"min": 50, "max": 150},
        "telemedicine": {"min": 60, "max": 100}
    }
    
    service_key = service_type.lower().replace(" ", "_")
    price_range = base_prices.get(service_key, {"min": 100, "max": 200})
    
    pricing_info = {
        "service": service_type,
        "price_range": {
            "currency": "SGD",
            "min": price_range["min"],
            "max": price_range["max"]
        },
        "notes": []
    }
    
    if insurance_provider:
        pricing_info["insurance_coverage"] = {
            "provider": insurance_provider,
            "estimated_coverage": "60-80%",
            "copay": f"${int(price_range['min'] * 0.2)}-${int(price_range['max'] * 0.4)}"
        }
        pricing_info["notes"].append("Coverage depends on your specific plan")
    
    pricing_info["notes"].extend([
        "Prices are estimates and may vary",
        "Additional tests or procedures may incur extra charges",
        "Please verify with billing department"
    ])
    
    return pricing_info


async def get_clinic_info(
    clinic_name: Optional[str] = None,
    location: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get information about clinics and facilities."""
    results = CLINICS.copy()
    
    # Filter by name
    if clinic_name:
        results = [c for c in results if clinic_name.lower() in c["name"].lower()]
    
    # Filter by location/region
    if location:
        # Check both region and address
        results = [
            c for c in results 
            if location.lower() in c.get("region", "").lower() or
               location.lower() in c.get("address", "").lower() or
               any(location.lower() in district.lower() 
                   for district in REGIONS.get(c.get("region", ""), {}).get("districts", []))
        ]
    
    # Add additional computed information
    formatted_results = []
    for clinic in results:
        # Count doctors at this clinic
        doctors_at_clinic = [d for d in DOCTORS if d["clinic_id"] == clinic["clinic_id"]]
        specialties = list(set(d["specialty"] for d in doctors_at_clinic))
        
        formatted_results.append({
            **clinic,
            "total_doctors": len(doctors_at_clinic),
            "specialties_available": specialties,
            "region_name": REGIONS.get(clinic["region"], {}).get("name", clinic["region"]),
            "accepts_walk_ins": clinic["type"] == "Family Medicine Clinic",
            "telemedicine_available": "Telemedicine" in clinic.get("facilities", [])
        })
        
    return formatted_results


async def search_health_packages(
    package_type: Optional[str] = None,
    age_group: Optional[str] = None,
    gender: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search for health screening packages."""
    results = HEALTH_PACKAGES.copy()
    
    # Filter by package type
    if package_type:
        results = [p for p in results if package_type.lower() in p["name"].lower()]
    
    # Add promotional pricing and availability
    formatted_results = []
    for package in results:
        formatted_package = {
            **package,
            "promotional_price": int(package["price"] * 0.9),  # 10% discount
            "slots_available": {
                "this_week": 12,
                "next_week": 18
            },
            "earliest_available": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
            "includes_consultation": "Doctor Consultation" in package.get("tests", []),
            "report_turnaround": "3-5 working days"
        }
        formatted_results.append(formatted_package)
    
    return formatted_results