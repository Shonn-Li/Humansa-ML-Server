#!/usr/bin/env python3
"""
Populate Humansa test database with comprehensive medical data.
"""

import subprocess
import json
from datetime import datetime, timedelta, time
import uuid
import random

# Database connection parameters
DB_PARAMS = {
    "host": "localhost",
    "port": "5456",
    "user": "youwo",
    "password": "youwo123",
    "database": "youwoai"
}

# Singapore regions
REGIONS = ["Central", "East", "West", "North", "Northeast"]

# Medical specialties
SPECIALTIES = [
    "General Practice", "Cardiology", "Pediatrics", "Dermatology", 
    "Orthopedics", "Gynecology", "Psychiatry", "Ophthalmology",
    "ENT", "Internal Medicine", "Neurology", "Endocrinology"
]

# Languages
LANGUAGES = ["English", "Mandarin", "Malay", "Tamil", "Hokkien", "Cantonese"]

def execute_sql(sql, fetch=False):
    """Execute SQL using psql command."""
    cmd = [
        "docker", "exec", "-i", "humansa_test_postgres",
        "psql", "-U", DB_PARAMS["user"], "-d", DB_PARAMS["database"],
        "-t", "-c", sql
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return None
        
        if fetch:
            return result.stdout.strip()
        return True
    except Exception as e:
        print(f"Error executing SQL: {e}")
        return None

def generate_test_data():
    """Generate comprehensive test data."""
    print("🔧 Generating test data...")
    
    # Clear existing data
    print("📝 Clearing existing data...")
    tables = [
        "humansa_appointments",
        "humansa_appointment_slots",
        "humansa_patient_insurance",
        "humansa_patient_profile",
        "humansa_doctor_availability",
        "humansa_doctors",
        "humansa_clinics",
        "humansa_users"
    ]
    
    for table in tables:
        execute_sql(f"DELETE FROM {table};")
    
    # 1. Create test clinics
    print("🏥 Creating clinics...")
    clinics = []
    clinic_names = [
        "Orchard Medical Centre", "Tampines Health Hub", "Jurong Medical Park",
        "Bishan Wellness Centre", "Punggol Family Clinic", "Marina Bay Medical",
        "Changi General Clinic", "Clementi Healthcare", "Woodlands Medical Centre",
        "Serangoon Health Point"
    ]
    
    for i, name in enumerate(clinic_names):
        clinic_id = f"CLINIC{i+1:03d}"
        region = REGIONS[i % len(REGIONS)]
        
        sql = f"""
        INSERT INTO humansa_clinics (
            clinic_id, name, type, region, address, phone, email,
            operating_hours, facilities, parking, wheelchair_accessible, nearest_mrt
        ) VALUES (
            '{clinic_id}', '{name}', 'Multi-Specialty', '{region}',
            '{i+1} Healthcare Road, Singapore {100000+i*1000}',
            '+65 {6000+i:04d} {1000+i:04d}', 'info@{name.lower().replace(" ", "")}.sg',
            '{{"weekdays": "8am-9pm", "saturday": "8am-2pm", "sunday": "closed"}}',
            ARRAY['X-Ray', 'Laboratory', 'Pharmacy'],
            {'TRUE' if i % 2 == 0 else 'FALSE'},
            TRUE,
            '{name.split()[0]} MRT'
        );
        """
        
        if execute_sql(sql):
            clinics.append(clinic_id)
    
    print(f"   ✅ Created {len(clinics)} clinics")
    
    # 2. Create test doctors
    print("👨‍⚕️ Creating doctors...")
    doctors = []
    doctor_names = [
        ("Dr. Sarah Chen", "F"), ("Dr. Michael Tan", "M"), ("Dr. Priya Sharma", "F"),
        ("Dr. James Lee", "M"), ("Dr. Emily Wong", "F"), ("Dr. David Lim", "M"),
        ("Dr. Anita Patel", "F"), ("Dr. Robert Ng", "M"), ("Dr. Lisa Goh", "F"),
        ("Dr. Kevin Ong", "M"), ("Dr. Maya Singh", "F"), ("Dr. Andrew Koh", "M"),
        ("Dr. Jessica Liu", "F"), ("Dr. Daniel Teo", "M"), ("Dr. Sophia Raj", "F"),
        ("Dr. William Chua", "M"), ("Dr. Rachel Tan", "F"), ("Dr. Steven Ho", "M"),
        ("Dr. Catherine Lau", "F"), ("Dr. Benjamin Yeo", "M")
    ]
    
    for i, (name, gender) in enumerate(doctor_names):
        doctor_id = f"DOC{i+1:04d}"
        specialty = SPECIALTIES[i % len(SPECIALTIES)]
        clinic_id = clinics[i % len(clinics)]
        years_exp = random.randint(5, 25)
        
        # Select 2-4 random languages
        doc_languages = random.sample(LANGUAGES, random.randint(2, 4))
        
        sql = f"""
        INSERT INTO humansa_doctors (
            doctor_id, name, specialty, sub_specialty, qualifications,
            years_experience, languages, gender, clinic_id, region,
            consultation_fee_min, consultation_fee_max, rating,
            consultation_types, special_interests, is_active
        ) VALUES (
            '{doctor_id}', '{name}', '{specialty}', 
            {'NULL' if i % 3 != 0 else f"'{specialty} - Advanced'"},
            ARRAY['MBBS', 'MRCP', 'FRCP'],
            {years_exp},
            ARRAY{doc_languages},
            '{gender}',
            '{clinic_id}',
            '{REGIONS[i % len(REGIONS)]}',
            {80 + i * 5}, {120 + i * 5},
            {round(4.0 + random.random(), 1)},
            ARRAY['In-Person', 'Telemedicine'],
            ARRAY['Preventive Care', 'Chronic Disease Management'],
            TRUE
        );
        """
        
        if execute_sql(sql):
            doctors.append(doctor_id)
            
            # Add availability for each doctor
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
            for day in days:
                if random.random() > 0.2:  # 80% chance of working each day
                    sql_avail = f"""
                    INSERT INTO humansa_doctor_availability (
                        doctor_id, day_of_week, start_time, end_time,
                        consultation_type, is_active
                    ) VALUES (
                        '{doctor_id}', '{day}', '09:00:00', '17:00:00',
                        'both', TRUE
                    );
                    """
                    execute_sql(sql_avail)
    
    print(f"   ✅ Created {len(doctors)} doctors with availability")
    
    # 3. Create test users and patients
    print("👥 Creating users and patient profiles...")
    users = []
    user_data = [
        ("John Smith", "john.smith@email.com", "+65 9123 4567"),
        ("Mary Johnson", "mary.j@email.com", "+65 9234 5678"),
        ("David Brown", "david.b@email.com", "+65 9345 6789"),
        ("Emma Wilson", "emma.w@email.com", "+65 9456 7890"),
        ("Michael Davis", "michael.d@email.com", "+65 9567 8901"),
        ("Sarah Miller", "sarah.m@email.com", "+65 9678 9012"),
        ("James Garcia", "james.g@email.com", "+65 9789 0123"),
        ("Linda Martinez", "linda.m@email.com", "+65 9890 1234"),
        ("Robert Anderson", "robert.a@email.com", "+65 9901 2345"),
        ("Lisa Taylor", "lisa.t@email.com", "+65 9012 3456")
    ]
    
    for i, (name, email, phone) in enumerate(user_data):
        user_id = f"USER{i+1:04d}"
        
        sql = f"""
        INSERT INTO humansa_users (
            user_id, email, phone, created_at, is_active
        ) VALUES (
            '{user_id}', '{email}', '{phone}', NOW(), TRUE
        );
        """
        
        if execute_sql(sql):
            users.append(user_id)
            
            # Create patient profile
            conditions = ["Hypertension", "Diabetes", "Asthma", "Migraine", "Arthritis"]
            allergies = ["Penicillin", "Peanuts", "Shellfish", "Dust", "Pollen"]
            medications = ["Metformin", "Lisinopril", "Aspirin", "Omeprazole", "Atorvastatin"]
            
            user_conditions = random.sample(conditions, random.randint(0, 2))
            user_allergies = random.sample(allergies, random.randint(0, 2))
            user_medications = random.sample(medications, random.randint(0, 2))
            
            medical_history = json.dumps([
                {"condition": cond, "diagnosed": "2020-01-01"} for cond in user_conditions
            ])
            
            current_meds = json.dumps([
                {"name": med, "dosage": f"{random.randint(5, 20)}mg", "frequency": "daily"} 
                for med in user_medications
            ])
            
            sql_profile = f"""
            INSERT INTO humansa_patient_profile (
                user_id, profile_data, medical_history, current_medications,
                allergies, blood_type, preferences
            ) VALUES (
                '{user_id}',
                '{{"name": "{name}", "age": {25 + i * 3}, "gender": "{random.choice(['M', 'F'])}"}}',
                '{medical_history}',
                '{current_meds}',
                ARRAY{user_allergies if user_allergies else ['NULL']},
                '{random.choice(['A+', 'B+', 'O+', 'AB+', 'A-', 'B-', 'O-', 'AB-'])}',
                '{{"preferred_language": "English", "preferred_time": "morning"}}'
            );
            """
            execute_sql(sql_profile)
    
    print(f"   ✅ Created {len(users)} users with patient profiles")
    
    # 4. Create appointment slots for next 30 days
    print("📅 Creating appointment slots...")
    slot_count = 0
    start_date = datetime.now().date()
    
    for doctor_id in doctors[:10]:  # Create slots for first 10 doctors
        for day_offset in range(30):
            date = start_date + timedelta(days=day_offset)
            
            # Skip weekends
            if date.weekday() >= 5:
                continue
            
            # Create hourly slots from 9am to 5pm
            for hour in range(9, 17):
                slot_id = f"SLOT{slot_count+1:06d}"
                
                sql = f"""
                INSERT INTO humansa_appointment_slots (
                    slot_id, doctor_id, date, time, duration_minutes,
                    consultation_type, consultation_fee, is_available
                ) VALUES (
                    '{slot_id}', '{doctor_id}', '{date}', '{hour:02d}:00:00',
                    30, 'In-Person', {100 + (hour-9)*5}, 
                    {'TRUE' if random.random() > 0.3 else 'FALSE'}
                );
                """
                
                if execute_sql(sql):
                    slot_count += 1
    
    print(f"   ✅ Created {slot_count} appointment slots")
    
    # 5. Create some appointments
    print("📋 Creating sample appointments...")
    appointment_count = 0
    
    for i in range(20):
        user_id = random.choice(users)
        doctor_id = random.choice(doctors[:10])
        date = start_date + timedelta(days=random.randint(1, 14))
        hour = random.randint(9, 16)
        
        appointment_id = f"APT{i+1:06d}"
        
        reasons = [
            "Regular checkup", "Follow-up consultation", "Acute illness",
            "Chronic condition management", "Preventive screening"
        ]
        
        sql = f"""
        INSERT INTO humansa_appointments (
            appointment_id, slot_id, user_id, doctor_id, clinic_id,
            appointment_date, appointment_time, consultation_type,
            status, reason_for_visit, consultation_fee, payment_status
        ) VALUES (
            '{appointment_id}', 
            (SELECT slot_id FROM humansa_appointment_slots 
             WHERE doctor_id = '{doctor_id}' AND date = '{date}' 
             AND time = '{hour:02d}:00:00' LIMIT 1),
            '{user_id}', '{doctor_id}',
            (SELECT clinic_id FROM humansa_doctors WHERE doctor_id = '{doctor_id}'),
            '{date}', '{hour:02d}:00:00', 'In-Person',
            '{random.choice(['scheduled', 'completed', 'cancelled'])}',
            '{random.choice(reasons)}',
            {100 + random.randint(0, 50)},
            '{random.choice(['pending', 'paid'])}'
        );
        """
        
        if execute_sql(sql):
            appointment_count += 1
    
    print(f"   ✅ Created {appointment_count} appointments")
    
    # 6. Create health packages
    print("💊 Creating health packages...")
    packages = [
        ("Basic Health Screening", 150, ["Blood Test", "Urine Test", "BMI"]),
        ("Executive Health Package", 500, ["Full Blood Count", "Liver Function", "Kidney Function", "ECG", "X-Ray"]),
        ("Women's Health Package", 350, ["Mammogram", "Pap Smear", "Bone Density", "Hormonal Panel"]),
        ("Senior Citizen Package", 400, ["Comprehensive Blood Test", "Heart Health", "Diabetes Screening", "Vision Test"]),
        ("Pre-Employment Package", 200, ["Basic Blood Test", "X-Ray", "Drug Test", "Fitness Assessment"])
    ]
    
    for i, (name, price, tests) in enumerate(packages):
        package_id = f"PKG{i+1:03d}"
        
        sql = f"""
        INSERT INTO humansa_health_packages (
            package_id, name, description, price, tests,
            suitable_for, preparation, is_active
        ) VALUES (
            '{package_id}', '{name}', 
            'Comprehensive {name.lower()} for your health needs',
            {price}, '{json.dumps(tests)}',
            ARRAY['Adults', '{"Seniors" if "Senior" in name else "Working Adults"}'],
            ARRAY['Fast for 8 hours', 'Bring previous reports'],
            TRUE
        );
        """
        execute_sql(sql)
    
    print(f"   ✅ Created {len(packages)} health packages")
    
    print("\n✅ Test data population completed!")


def verify_data():
    """Verify the populated data."""
    print("\n🔍 Verifying data...")
    
    tables = [
        ("humansa_clinics", "Clinics"),
        ("humansa_doctors", "Doctors"),
        ("humansa_users", "Users"),
        ("humansa_appointment_slots", "Appointment Slots"),
        ("humansa_appointments", "Appointments"),
        ("humansa_health_packages", "Health Packages")
    ]
    
    for table, name in tables:
        count = execute_sql(f"SELECT COUNT(*) FROM {table};", fetch=True)
        if count:
            print(f"   ✅ {name}: {count} records")
        else:
            print(f"   ❌ {name}: No data or error")


def main():
    """Main function."""
    print("🏥 Humansa Test Data Population")
    print("=" * 50)
    
    # Check if container is running
    result = subprocess.run(["docker", "ps", "--filter", "name=humansa_test_postgres", "--format", "{{.Status}}"],
                          capture_output=True, text=True)
    
    if "healthy" not in result.stdout:
        print("❌ Humansa test database is not running!")
        print("   Please run: cd humansa_test_environment && ./setup.sh")
        return
    
    print("✅ Database container is running")
    
    # Generate and populate data
    generate_test_data()
    
    # Verify the data
    verify_data()
    
    print("\n✅ Data population completed successfully!")
    print("   You can now run the V2 tests.")


if __name__ == "__main__":
    main()