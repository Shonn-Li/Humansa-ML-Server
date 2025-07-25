# Humansa v2 Complete Test Environment Setup

## What Has Been Created

### 1. Database Schema (`test_environment/setup_humansa_test_db.sql`)
Complete PostgreSQL database schema with all necessary tables:

- **humansa_users** - Base user authentication table
- **humansa_patient_profile** - Extended patient information 
- **humansa_clinics** - Clinic locations and details
- **humansa_doctors** - Doctor profiles and specialties
- **humansa_doctor_availability** - Working hours per doctor
- **humansa_appointment_slots** - Available time slots
- **humansa_appointments** - Booked appointments
- **humansa_conversation_history** - Chat history storage
- **humansa_health_packages** - Health screening packages
- **humansa_insurance_providers** - Insurance company list
- **humansa_patient_insurance** - Patient insurance records

### 2. Test Data Population Script (`test_environment/populate_humansa_test_data.py`)
Comprehensive script that populates:

- **5 Test Users** with varying medical histories:
  - John Tan (35, healthy)
  - Mary Lim (58, diabetes & hypertension)
  - Robert Lee (72, heart disease)
  - Sarah Wong (28, allergies)
  - David Ng (45, asthma)

- **10 Doctors** across specialties:
  - General Practice (2)
  - Cardiology (2)
  - Dermatology, Pediatrics, Orthopedics, Gastroenterology, Psychiatry, OB/GYN (1 each)

- **5 Clinics** in different Singapore regions:
  - Orchard (Multi-specialty)
  - Tampines (Family)
  - Mount Elizabeth (Heart Center)
  - Jurong (Skin & Laser)
  - Ang Mo Kio (Children's)

- **Dynamic Appointment Slots**:
  - 30 days of slots generated per doctor
  - Based on doctor availability
  - 70% available, 30% booked
  - Sample appointments created

### 3. Database-Connected Tools (`src/humansa/v2/tools/db_medical_tools.py`)
Real database integration for:

- `search_doctors()` - Search by specialty, language, location, gender
- `check_doctor_availability()` - Real-time slot availability
- `book_appointment_slot()` - Actual booking with transaction support
- `get_user_appointments()` - Retrieve user's appointments
- `cancel_appointment()` - Cancel with slot release
- `get_clinic_info()` - Clinic details and doctor counts

### 4. Docker Environment (`test_environment/docker-compose.test.yml`)
- PostgreSQL with pgvector on port 5454
- PgAdmin on port 5455
- Isolated test environment

### 5. Test Cases (`test_humansa_v2_comprehensive.py`)
20 comprehensive test cases covering:
- Emergency detection
- Doctor search (multiple criteria)
- Appointment booking flow
- Medication interactions
- Patient profiles
- Multi-turn conversations
- Insurance queries
- Complex multi-agent scenarios

## How to Set Up and Run

### Step 1: Start the Test Database
```bash
cd test_environment
docker-compose -f docker-compose.test.yml up -d
```

### Step 2: Create Virtual Environment
```bash
python3 -m venv humansa-test-venv
source humansa-test-venv/bin/activate
pip install asyncpg psycopg2-binary quart quart-cors aiohttp
```

### Step 3: Run Database Setup
```bash
# First, create the schema
psql -h localhost -p 5454 -U youwo -d youwoai -f setup_humansa_test_db.sql

# Then populate with test data
DB_PORT=5454 python3 populate_humansa_test_data.py
```

### Step 4: Start ML Server with Test DB
```bash
export DB_PORT=5454
export OPENAI_API_KEY=your_key_here
python3 -m src.main
```

### Step 5: Run Tests
```bash
python3 test_humansa_v2_comprehensive.py
```

## Database Access

### PostgreSQL Direct Access
```bash
psql -h localhost -p 5454 -U youwo -d youwoai
# Password: youwo123
```

### PgAdmin Web Interface
- URL: http://localhost:5455
- Email: admin@humansa.test
- Password: admin123

### Sample Queries
```sql
-- View all doctors
SELECT * FROM humansa_doctors;

-- Check available slots for next week
SELECT * FROM humansa_appointment_slots 
WHERE is_available = true 
AND date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
ORDER BY date, time;

-- View user appointments
SELECT a.*, d.name as doctor_name, c.name as clinic_name
FROM humansa_appointments a
JOIN humansa_doctors d ON a.doctor_id = d.doctor_id
JOIN humansa_clinics c ON a.clinic_id = c.clinic_id
WHERE a.user_id = 'test_user_002';
```

## API Endpoints with Database

The v2 endpoints now support full database operations:

- `POST /v2/humansa/chat` - Uses DB for doctor/clinic lookups
- `POST /v2/humansa/appointment/search` - Real slot availability
- `POST /v2/humansa/appointment/book` - Actual booking with DB transactions
- `GET /v2/humansa/patient/profile` - Stored patient data
- `PUT /v2/humansa/patient/profile` - Update patient records

## Key Features Implemented

1. **Real Appointment Booking**
   - Transactional slot reservation
   - Prevents double booking
   - Automatic slot release on cancellation

2. **Persistent Patient Data**
   - Medical history tracking
   - Current medications
   - Allergies and preferences
   - Conversation history

3. **Dynamic Availability**
   - Based on doctor working hours
   - Real-time slot status
   - Multiple consultation types (in-person/telemedicine)

4. **Comprehensive Search**
   - Multi-criteria doctor search
   - Location-based clinic finding
   - Specialty and language filtering

## Testing the System

### Test Scenario 1: Book an Appointment
```python
# Search for cardiologist
POST /v2/humansa/chat
{
  "user_id": "test_user_002",
  "messages": [{"role": "user", "content": "I need to see a cardiologist"}]
}

# System finds Dr. Rajesh Kumar, shows availability
# User selects a slot
# System books appointment, updates database
```

### Test Scenario 2: Emergency Detection
```python
# Emergency symptoms
POST /v2/humansa/chat
{
  "user_id": "test_user_003",
  "messages": [{"role": "user", "content": "Severe chest pain and can't breathe"}]
}

# System triggers emergency response
# Provides immediate guidance
```

### Test Scenario 3: Medication Check
```python
# Check interactions
POST /v2/humansa/chat
{
  "user_id": "test_user_002",
  "messages": [{"role": "user", "content": "Can I take ibuprofen with my diabetes meds?"}]
}

# System checks current medications (Metformin, Lisinopril)
# Provides interaction information
```

## Troubleshooting

### Port Already in Use
```bash
# Find what's using port 5454
lsof -i :5454

# Stop existing container
docker stop <container_name>
```

### Module Not Found Errors
```bash
# Make sure you're in virtual environment
source humansa-test-venv/bin/activate

# Install all dependencies
pip install -r requirements-test.txt
```

### Database Connection Issues
```bash
# Check if database is running
docker ps | grep humansa_test_postgres

# Check logs
docker logs humansa_test_postgres
```

## Summary

The Humansa v2 test environment provides:
- ✅ Complete database schema with 11 tables
- ✅ Realistic test data for Singapore healthcare
- ✅ 10 doctors, 5 clinics, 5 test patients
- ✅ 30 days of appointment slots
- ✅ Full CRUD operations for appointments
- ✅ Patient profile management
- ✅ Real-time availability checking
- ✅ Transaction support for bookings
- ✅ 20 comprehensive test cases
- ✅ Docker-based isolated environment

The system is ready for full integration testing with actual database operations.