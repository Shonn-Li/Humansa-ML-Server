#!/usr/bin/env python3
"""
Populate Humansa test database with comprehensive test data.
"""

import asyncio
import asyncpg
import json
import os
import sys
from datetime import datetime, timedelta, date, time
import random
from typing import List, Dict, Any

# Add parent directories to path
script_dir = os.path.dirname(os.path.abspath(__file__))
humansa_test_dir = os.path.dirname(script_dir)
project_root = os.path.dirname(humansa_test_dir)
sys.path.insert(0, project_root)

# Import test data
from src.humansa.v2.test_data import DOCTORS, CLINICS, HEALTH_PACKAGES, INSURANCE_PROVIDERS


# Test users
TEST_USERS = [
    {
        "user_id": "test_user_001",
        "email": "john.tan@test.com",
        "phone": "+65 9123 4567",
        "profile": {
            "name": "John Tan",
            "age": 35,
            "gender": "Male",
            "occupation": "Software Engineer"
        }
    },
    {
        "user_id": "test_user_002",
        "email": "mary.lim@test.com",
        "phone": "+65 9234 5678",
        "profile": {
            "name": "Mary Lim",
            "age": 58,
            "gender": "Female",
            "occupation": "Teacher"
        },
        "medical_history": [
            {"condition": "Type 2 Diabetes", "diagnosed": "2018-03-15", "status": "ongoing"},
            {"condition": "Hypertension", "diagnosed": "2019-07-22", "status": "controlled"}
        ],
        "current_medications": [
            {"name": "Metformin", "dosage": "500mg", "frequency": "twice daily", "prescriber": "Dr. Sarah Chen"},
            {"name": "Lisinopril", "dosage": "10mg", "frequency": "once daily", "prescriber": "Dr. Sarah Chen"}
        ],
        "allergies": ["Penicillin", "Shellfish"]
    },
    {
        "user_id": "test_user_003",
        "email": "robert.lee@test.com",
        "phone": "+65 9345 6789",
        "profile": {
            "name": "Robert Lee",
            "age": 72,
            "gender": "Male",
            "occupation": "Retired"
        },
        "medical_history": [
            {"condition": "Coronary Artery Disease", "diagnosed": "2015-11-20", "status": "stable"},
            {"condition": "Osteoarthritis", "diagnosed": "2017-04-10", "status": "ongoing"}
        ],
        "blood_type": "O+"
    },
    {
        "user_id": "test_user_004",
        "email": "sarah.wong@test.com",
        "phone": "+65 9456 7890",
        "profile": {
            "name": "Sarah Wong",
            "age": 28,
            "gender": "Female",
            "occupation": "Marketing Manager"
        },
        "allergies": ["Dust mites", "Pollen"]
    },
    {
        "user_id": "test_user_005",
        "email": "david.ng@test.com",
        "phone": "+65 9567 8901",
        "profile": {
            "name": "David Ng",
            "age": 45,
            "gender": "Male",
            "occupation": "Business Owner"
        },
        "medical_history": [
            {"condition": "Asthma", "diagnosed": "2010-05-12", "status": "controlled"}
        ],
        "blood_type": "A+"
    }
]


class HumansaTestDataPopulator:
    def __init__(self, db_config):
        self.db_config = db_config
        self.pool = None
        
    async def connect(self):
        """Create database connection pool."""
        self.pool = await asyncpg.create_pool(**self.db_config)
        
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            
    async def setup_database(self):
        """Run the SQL setup script."""
        print("🔧 Setting up database schema...")
        
        # Read SQL file
        sql_file = os.path.join(os.path.dirname(__file__), 'setup_humansa_test_db.sql')
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        # Execute SQL
        async with self.pool.acquire() as conn:
            await conn.execute(sql_content)
        
        print("✅ Database schema created successfully")
        
    async def populate_clinics(self):
        """Populate clinics table."""
        print("\n🏥 Populating clinics...")
        
        async with self.pool.acquire() as conn:
            for clinic in CLINICS:
                await conn.execute("""
                    INSERT INTO humansa_clinics (
                        clinic_id, name, type, region, address, phone, email,
                        operating_hours, facilities, parking, wheelchair_accessible, nearest_mrt
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (clinic_id) DO NOTHING
                """,
                    clinic['clinic_id'],
                    clinic['name'],
                    clinic['type'],
                    clinic['region'],
                    clinic['address'],
                    clinic['phone'],
                    clinic['email'],
                    json.dumps(clinic['operating_hours']),
                    clinic['facilities'],
                    clinic['parking'],
                    clinic['wheelchair_accessible'],
                    clinic['nearest_mrt']
                )
        
        print(f"✅ Inserted {len(CLINICS)} clinics")
        
    async def populate_doctors(self):
        """Populate doctors table."""
        print("\n👨‍⚕️ Populating doctors...")
        
        async with self.pool.acquire() as conn:
            for doctor in DOCTORS:
                await conn.execute("""
                    INSERT INTO humansa_doctors (
                        doctor_id, name, specialty, sub_specialty, qualifications,
                        years_experience, languages, gender, clinic_id, region,
                        consultation_fee_min, consultation_fee_max, rating,
                        consultation_types, special_interests
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    ON CONFLICT (doctor_id) DO NOTHING
                """,
                    doctor['doctor_id'],
                    doctor['name'],
                    doctor['specialty'],
                    doctor.get('sub_specialty'),
                    doctor['qualifications'],
                    doctor['years_experience'],
                    doctor['languages'],
                    doctor['gender'],
                    doctor['clinic_id'],
                    doctor['region'],
                    doctor['consultation_fee']['min'],
                    doctor['consultation_fee']['max'],
                    doctor['rating'],
                    doctor['consultation_types'],
                    doctor.get('special_interests', [])
                )
                
                # Add availability
                for day in doctor['available_days']:
                    await conn.execute("""
                        INSERT INTO humansa_doctor_availability (
                            doctor_id, day_of_week, start_time, end_time, consultation_type
                        ) VALUES ($1, $2, $3, $4, $5)
                    """,
                        doctor['doctor_id'],
                        day,
                        time(9, 0),  # 9 AM
                        time(17, 0),  # 5 PM
                        'both'
                    )
        
        print(f"✅ Inserted {len(DOCTORS)} doctors with availability")
        
    async def populate_users(self):
        """Populate users and patient profiles."""
        print("\n👤 Populating users and patient profiles...")
        
        async with self.pool.acquire() as conn:
            for user_data in TEST_USERS:
                # Insert user
                await conn.execute("""
                    INSERT INTO humansa_users (user_id, email, phone)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id) DO NOTHING
                """,
                    user_data['user_id'],
                    user_data['email'],
                    user_data['phone']
                )
                
                # Insert patient profile
                profile_data = user_data.get('profile', {})
                medical_history = user_data.get('medical_history', [])
                current_medications = user_data.get('current_medications', [])
                allergies = user_data.get('allergies', [])
                
                await conn.execute("""
                    INSERT INTO humansa_patient_profile (
                        user_id, profile_data, medical_history, current_medications,
                        allergies, blood_type
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (user_id) DO NOTHING
                """,
                    user_data['user_id'],
                    json.dumps(profile_data),
                    json.dumps(medical_history),
                    json.dumps(current_medications),
                    allergies,
                    user_data.get('blood_type')
                )
        
        print(f"✅ Inserted {len(TEST_USERS)} users with patient profiles")
        
    async def populate_appointment_slots(self):
        """Generate and populate appointment slots for the next 30 days."""
        print("\n📅 Generating appointment slots...")
        
        async with self.pool.acquire() as conn:
            start_date = date.today()
            slot_count = 0
            
            for doctor in DOCTORS:
                doctor_id = doctor['doctor_id']
                
                # Get doctor's availability
                availability = await conn.fetch("""
                    SELECT day_of_week, start_time, end_time, consultation_type
                    FROM humansa_doctor_availability
                    WHERE doctor_id = $1 AND is_active = true
                """, doctor_id)
                
                # Generate slots for next 30 days
                for day_offset in range(30):
                    current_date = start_date + timedelta(days=day_offset)
                    weekday = current_date.strftime("%A")
                    
                    # Check if doctor works on this day
                    day_availability = [a for a in availability if a['day_of_week'] == weekday]
                    if not day_availability:
                        continue
                    
                    # Generate time slots
                    for avail in day_availability:
                        start_time = avail['start_time']
                        end_time = avail['end_time']
                        
                        # Create 30-minute slots for GP, 45-minute for specialists
                        slot_duration = 30 if doctor['specialty'] == 'General Practice' else 45
                        
                        current_time = datetime.combine(current_date, start_time)
                        end_datetime = datetime.combine(current_date, end_time)
                        
                        while current_time < end_datetime:
                            slot_id = f"slot_{doctor_id}_{current_date.strftime('%Y%m%d')}_{current_time.strftime('%H%M')}"
                            
                            # Randomly make some slots unavailable (30% booked)
                            is_available = random.random() > 0.3
                            
                            # Random consultation type
                            consultation_type = random.choice(doctor['consultation_types'])
                            
                            # Calculate fee
                            fee = random.randint(
                                doctor['consultation_fee']['min'],
                                doctor['consultation_fee']['max']
                            )
                            
                            await conn.execute("""
                                INSERT INTO humansa_appointment_slots (
                                    slot_id, doctor_id, date, time, duration_minutes,
                                    consultation_type, consultation_fee, is_available
                                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                                ON CONFLICT (slot_id) DO NOTHING
                            """,
                                slot_id,
                                doctor_id,
                                current_date,
                                current_time.time(),
                                slot_duration,
                                consultation_type,
                                fee,
                                is_available
                            )
                            
                            slot_count += 1
                            current_time += timedelta(minutes=slot_duration)
        
        print(f"✅ Generated {slot_count} appointment slots")
        
    async def populate_sample_appointments(self):
        """Create some sample booked appointments."""
        print("\n📋 Creating sample appointments...")
        
        async with self.pool.acquire() as conn:
            # Get some booked slots
            booked_slots = await conn.fetch("""
                SELECT s.*, d.clinic_id
                FROM humansa_appointment_slots s
                JOIN humansa_doctors d ON s.doctor_id = d.doctor_id
                WHERE s.is_available = false
                AND s.date >= CURRENT_DATE
                LIMIT 20
            """)
            
            appointment_count = 0
            user_index = 0
            
            for slot in booked_slots[:10]:  # Create 10 sample appointments
                user = TEST_USERS[user_index % len(TEST_USERS)]
                appointment_id = f"apt_{datetime.now().timestamp()}_{user['user_id']}"
                
                reasons = [
                    "Annual checkup",
                    "Follow-up consultation",
                    "Persistent headache",
                    "Skin rash",
                    "Vaccination",
                    "Blood pressure monitoring",
                    "Diabetes management",
                    "General consultation"
                ]
                
                await conn.execute("""
                    INSERT INTO humansa_appointments (
                        appointment_id, slot_id, user_id, doctor_id, clinic_id,
                        appointment_date, appointment_time, consultation_type,
                        status, reason_for_visit, consultation_fee
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                    appointment_id,
                    slot['slot_id'],
                    user['user_id'],
                    slot['doctor_id'],
                    slot['clinic_id'],
                    slot['date'],
                    slot['time'],
                    slot['consultation_type'],
                    'scheduled',
                    random.choice(reasons),
                    slot['consultation_fee']
                )
                
                appointment_count += 1
                user_index += 1
        
        print(f"✅ Created {appointment_count} sample appointments")
        
    async def populate_health_packages(self):
        """Populate health screening packages."""
        print("\n📋 Populating health packages...")
        
        async with self.pool.acquire() as conn:
            for package in HEALTH_PACKAGES:
                await conn.execute("""
                    INSERT INTO humansa_health_packages (
                        package_id, name, description, price, promotional_price,
                        duration, tests, suitable_for, preparation
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (package_id) DO NOTHING
                """,
                    package['package_id'],
                    package['name'],
                    package.get('description', ''),
                    package['price'],
                    int(package['price'] * 0.9),  # 10% discount
                    package['duration'],
                    json.dumps(package['tests']),
                    package['suitable_for'],
                    package.get('preparation', [])
                )
        
        print(f"✅ Inserted {len(HEALTH_PACKAGES)} health packages")
        
    async def populate_insurance_providers(self):
        """Populate insurance providers."""
        print("\n🏦 Populating insurance providers...")
        
        async with self.pool.acquire() as conn:
            for provider in INSURANCE_PROVIDERS:
                await conn.execute("""
                    INSERT INTO humansa_insurance_providers (
                        name, coverage_type, is_panel
                    ) VALUES ($1, $2, $3)
                    ON CONFLICT (name) DO NOTHING
                """,
                    provider['name'],
                    provider['coverage_type'],
                    provider['panel']
                )
        
        print(f"✅ Inserted {len(INSURANCE_PROVIDERS)} insurance providers")
        
    async def populate_sample_conversations(self):
        """Create sample conversation history."""
        print("\n💬 Creating sample conversation history...")
        
        conversations = [
            {
                "user_id": "test_user_001",
                "conversation_id": "conv_001",
                "messages": [
                    {"role": "user", "content": "I've been having headaches for the past week"},
                    {"role": "assistant", "content": "I understand you've been experiencing headaches. Can you describe the nature of the pain?"},
                    {"role": "user", "content": "It's a throbbing pain on the right side of my head"},
                    {"role": "assistant", "content": "Based on your symptoms, I recommend seeing a doctor. Would you like me to help you find a general practitioner?"}
                ]
            },
            {
                "user_id": "test_user_002",
                "conversation_id": "conv_002",
                "messages": [
                    {"role": "user", "content": "I need to refill my diabetes medication"},
                    {"role": "assistant", "content": "I can help you with that. You're currently on Metformin 500mg twice daily. Would you like to book an appointment with Dr. Sarah Chen for a prescription renewal?"}
                ]
            }
        ]
        
        async with self.pool.acquire() as conn:
            message_count = 0
            for conv in conversations:
                for msg in conv['messages']:
                    await conn.execute("""
                        INSERT INTO humansa_conversation_history (
                            user_id, conversation_id, role, content, metadata
                        ) VALUES ($1, $2, $3, $4, $5)
                    """,
                        conv['user_id'],
                        conv['conversation_id'],
                        msg['role'],
                        msg['content'],
                        json.dumps({})
                    )
                    message_count += 1
        
        print(f"✅ Created {message_count} conversation messages")
        
    async def run(self):
        """Run all population steps."""
        try:
            await self.connect()
            
            # Setup database schema
            await self.setup_database()
            
            # Populate in order (respecting foreign keys)
            await self.populate_clinics()
            await self.populate_doctors()
            await self.populate_users()
            await self.populate_appointment_slots()
            await self.populate_sample_appointments()
            await self.populate_health_packages()
            await self.populate_insurance_providers()
            await self.populate_sample_conversations()
            
            print("\n✅ All test data populated successfully!")
            
            # Show summary
            async with self.pool.acquire() as conn:
                clinic_count = await conn.fetchval("SELECT COUNT(*) FROM humansa_clinics")
                doctor_count = await conn.fetchval("SELECT COUNT(*) FROM humansa_doctors")
                user_count = await conn.fetchval("SELECT COUNT(*) FROM humansa_users")
                slot_count = await conn.fetchval("SELECT COUNT(*) FROM humansa_appointment_slots")
                appointment_count = await conn.fetchval("SELECT COUNT(*) FROM humansa_appointments")
                
                print("\n📊 Database Summary:")
                print(f"  - Clinics: {clinic_count}")
                print(f"  - Doctors: {doctor_count}")
                print(f"  - Users: {user_count}")
                print(f"  - Appointment Slots: {slot_count}")
                print(f"  - Booked Appointments: {appointment_count}")
                
        finally:
            await self.close()


async def main():
    """Main function."""
    # Database configuration
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5454')),  # Test DB port
        'database': os.getenv('DB_NAME', 'youwoai'),
        'user': os.getenv('DB_USER', 'youwo'),
        'password': os.getenv('DB_PASSWORD', 'youwo123')
    }
    
    print("🚀 Humansa Test Data Population Script")
    print("=" * 50)
    print(f"Database: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    
    populator = HumansaTestDataPopulator(db_config)
    await populator.run()


if __name__ == "__main__":
    asyncio.run(main())