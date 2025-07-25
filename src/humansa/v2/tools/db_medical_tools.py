"""
Database-connected medical tools for Humansa v2.
These tools interact with the actual PostgreSQL database.
"""

from typing import Dict, Any, List, Optional
import json
from datetime import datetime, timedelta, date
import asyncpg


class DatabaseMedicalTools:
    """Medical tools that interact with the database."""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def search_doctors(
        self,
        specialty: Optional[str] = None,
        name: Optional[str] = None,
        location: Optional[str] = None,
        language: Optional[str] = None,
        gender: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for doctors based on criteria."""
        query = """
            SELECT 
                d.*,
                c.name as clinic_name,
                c.address as clinic_address,
                c.phone as clinic_phone,
                c.nearest_mrt
            FROM humansa_doctors d
            JOIN humansa_clinic c ON d.clinic_id = c.clinic_id
            WHERE d.is_active = true
        """
        
        conditions = []
        params = []
        param_count = 0
        
        if specialty:
            param_count += 1
            conditions.append(f"LOWER(d.specialty) LIKE LOWER(${param_count})")
            params.append(f"%{specialty}%")
            
        if name:
            param_count += 1
            conditions.append(f"LOWER(d.name) LIKE LOWER(${param_count})")
            params.append(f"%{name}%")
            
        if location:
            param_count += 1
            conditions.append(f"(LOWER(d.region) = LOWER(${param_count}) OR LOWER(c.region) = LOWER(${param_count}))")
            params.append(location)
            
        if language:
            param_count += 1
            conditions.append(f"${param_count} = ANY(d.languages)")
            params.append(language)
            
        if gender:
            param_count += 1
            conditions.append(f"LOWER(d.gender) = LOWER(${param_count})")
            params.append(gender)
        
        if conditions:
            query += " AND " + " AND ".join(conditions)
            
        query += " ORDER BY d.rating DESC, d.years_experience DESC"
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
        results = []
        for row in rows:
            results.append({
                "doctor_id": row['doctor_id'],
                "name": row['name'],
                "specialty": row['specialty'],
                "sub_specialty": row['sub_specialty'],
                "qualifications": row['qualifications'],
                "languages": row['languages'],
                "gender": row['gender'],
                "clinic_name": row['clinic_name'],
                "location": row['region'],
                "address": row['clinic_address'],
                "rating": float(row['rating']),
                "years_experience": row['years_experience'],
                "consultation_fee": {
                    "min": row['consultation_fee_min'],
                    "max": row['consultation_fee_max']
                },
                "consultation_types": row['consultation_types'],
                "availability_status": "Available"
            })
            
        return results
    
    async def check_doctor_availability(
        self,
        doctor_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check doctor availability for specific dates."""
        if not date_from:
            date_from = date.today().strftime("%Y-%m-%d")
        if not date_to:
            date_to = (date.today() + timedelta(days=14)).strftime("%Y-%m-%d")
        
        # Get doctor info
        async with self.db_pool.acquire() as conn:
            doctor = await conn.fetchrow("""
                SELECT d.*, c.name as clinic_name
                FROM humansa_doctors d
                JOIN humansa_clinic c ON d.clinic_id = c.clinic_id
                WHERE d.doctor_id = $1
            """, doctor_id)
            
            if not doctor:
                return {"error": "Doctor not found"}
            
            # Get available slots
            slots = await conn.fetch("""
                SELECT * FROM humansa_appointment_slots
                WHERE doctor_id = $1
                AND date >= $2::date
                AND date <= $3::date
                AND is_available = true
                ORDER BY date, time
            """, doctor_id, date_from, date_to)
            
            # Group by date
            availability_by_date = {}
            for slot in slots:
                date_str = slot['date'].strftime("%Y-%m-%d")
                if date_str not in availability_by_date:
                    availability_by_date[date_str] = {
                        "date": date_str,
                        "times": [],
                        "types": set()
                    }
                availability_by_date[date_str]["times"].append(
                    slot['time'].strftime("%H:%M")
                )
                availability_by_date[date_str]["types"].add(slot['consultation_type'])
            
            # Convert to list
            available_slots = []
            for date_info in availability_by_date.values():
                available_slots.append({
                    "date": date_info["date"],
                    "times": sorted(date_info["times"]),
                    "type": "both" if len(date_info["types"]) > 1 else list(date_info["types"])[0]
                })
            
            # Find next available
            next_available = None
            if slots:
                next_slot = slots[0]
                next_available = {
                    "date": next_slot['date'].strftime("%Y-%m-%d"),
                    "time": next_slot['time'].strftime("%H:%M"),
                    "type": next_slot['consultation_type'],
                    "consultation_fee": next_slot['consultation_fee']
                }
        
        return {
            "doctor_id": doctor_id,
            "doctor_name": doctor['name'],
            "specialty": doctor['specialty'],
            "clinic_name": doctor['clinic_name'],
            "date_range": {
                "from": date_from,
                "to": date_to
            },
            "available_slots": available_slots[:7],
            "next_available": next_available,
            "total_available_slots": len(slots)
        }
    
    async def book_appointment_slot(
        self,
        slot_id: str,
        user_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Book an appointment slot."""
        async with self.db_pool.acquire() as conn:
            # Start transaction
            async with conn.transaction():
                # Check if slot is available
                slot = await conn.fetchrow("""
                    SELECT s.*, d.name as doctor_name, d.specialty, c.name as clinic_name
                    FROM humansa_appointment_slots s
                    JOIN humansa_doctors d ON s.doctor_id = d.doctor_id
                    JOIN humansa_clinic c ON d.clinic_id = c.clinic_id
                    WHERE s.slot_id = $1 AND s.is_available = true
                    FOR UPDATE
                """, slot_id)
                
                if not slot:
                    return {"error": "Slot not available"}
                
                # Mark slot as unavailable
                await conn.execute("""
                    UPDATE humansa_appointment_slots
                    SET is_available = false
                    WHERE slot_id = $1
                """, slot_id)
                
                # Create appointment
                appointment_id = f"apt_{datetime.now().timestamp()}_{user_id}"
                
                await conn.execute("""
                    INSERT INTO humansa_appointments (
                        appointment_id, slot_id, user_id, doctor_id, clinic_id,
                        appointment_date, appointment_time, consultation_type,
                        status, reason_for_visit, consultation_fee, confirmed_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                    appointment_id,
                    slot_id,
                    user_id,
                    slot['doctor_id'],
                    slot['clinic_id'],
                    slot['date'],
                    slot['time'],
                    slot['consultation_type'],
                    'scheduled',
                    reason or 'General consultation',
                    slot['consultation_fee'],
                    datetime.now()
                )
        
        return {
            "status": "success",
            "appointment_id": appointment_id,
            "details": {
                "doctor": slot['doctor_name'],
                "specialty": slot['specialty'],
                "clinic": slot['clinic_name'],
                "date": slot['date'].strftime("%Y-%m-%d"),
                "time": slot['time'].strftime("%H:%M"),
                "type": slot['consultation_type'],
                "duration": f"{slot['duration_minutes']} minutes",
                "fee": slot['consultation_fee']
            }
        }
    
    async def get_user_appointments(
        self,
        user_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user's appointments."""
        query = """
            SELECT 
                a.*,
                d.name as doctor_name,
                d.specialty,
                c.name as clinic_name,
                c.address as clinic_address,
                c.phone as clinic_phone
            FROM humansa_appointments a
            JOIN humansa_doctors d ON a.doctor_id = d.doctor_id
            JOIN humansa_clinic c ON a.clinic_id = c.clinic_id
            WHERE a.user_id = $1
        """
        
        params = [user_id]
        if status:
            query += " AND a.status = $2"
            params.append(status)
            
        query += " ORDER BY a.appointment_date DESC, a.appointment_time DESC"
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        
        results = []
        for row in rows:
            results.append({
                "appointment_id": row['appointment_id'],
                "doctor": row['doctor_name'],
                "specialty": row['specialty'],
                "clinic": row['clinic_name'],
                "address": row['clinic_address'],
                "date": row['appointment_date'].strftime("%Y-%m-%d"),
                "time": row['appointment_time'].strftime("%H:%M"),
                "type": row['consultation_type'],
                "status": row['status'],
                "reason": row['reason_for_visit'],
                "fee": row['consultation_fee'],
                "created_at": row['created_at'].isoformat()
            })
            
        return results
    
    async def cancel_appointment(
        self,
        appointment_id: str,
        user_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel an appointment."""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # Get appointment details
                appointment = await conn.fetchrow("""
                    SELECT * FROM humansa_appointments
                    WHERE appointment_id = $1 AND user_id = $2 AND status = 'scheduled'
                """, appointment_id, user_id)
                
                if not appointment:
                    return {"error": "Appointment not found or cannot be cancelled"}
                
                # Update appointment status
                await conn.execute("""
                    UPDATE humansa_appointments
                    SET status = 'cancelled',
                        cancelled_at = $1,
                        cancellation_reason = $2
                    WHERE appointment_id = $3
                """, datetime.now(), reason or 'User requested', appointment_id)
                
                # Make slot available again
                await conn.execute("""
                    UPDATE humansa_appointment_slots
                    SET is_available = true
                    WHERE slot_id = $1
                """, appointment['slot_id'])
        
        return {
            "status": "success",
            "message": "Appointment cancelled successfully",
            "appointment_id": appointment_id
        }
    
    async def get_clinic_info(
        self,
        clinic_name: Optional[str] = None,
        location: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get information about clinics."""
        query = """
            SELECT c.*, COUNT(d.doctor_id) as doctor_count
            FROM humansa_clinic c
            LEFT JOIN humansa_doctors d ON c.clinic_id = d.clinic_id
            WHERE 1=1
        """
        
        conditions = []
        params = []
        param_count = 0
        
        if clinic_name:
            param_count += 1
            conditions.append(f"LOWER(c.name) LIKE LOWER(${param_count})")
            params.append(f"%{clinic_name}%")
            
        if location:
            param_count += 1
            conditions.append(f"(LOWER(c.region) = LOWER(${param_count}) OR LOWER(c.address) LIKE LOWER(${param_count}))")
            params.append(location if not location.startswith('%') else f"%{location}%")
        
        if conditions:
            query += " AND " + " AND ".join(conditions)
            
        query += " GROUP BY c.clinic_id ORDER BY c.name"
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
        results = []
        for row in rows:
            results.append({
                "clinic_id": row['clinic_id'],
                "name": row['name'],
                "type": row['type'],
                "region": row['region'],
                "address": row['address'],
                "phone": row['phone'],
                "email": row['email'],
                "operating_hours": json.loads(row['operating_hours']) if row['operating_hours'] else {},
                "facilities": row['facilities'],
                "parking": row['parking'],
                "wheelchair_accessible": row['wheelchair_accessible'],
                "nearest_mrt": row['nearest_mrt'],
                "total_doctors": row['doctor_count']
            })
            
        return results


# Create wrapper functions that match the original tool signatures
_db_pool = None

def set_db_pool(pool):
    """Set the database pool for the tools."""
    global _db_pool
    _db_pool = pool

async def search_doctors(**kwargs):
    """Search doctors using database."""
    if not _db_pool:
        # Fallback to test data if no DB
        from ..test_data import search_doctors as test_search
        return test_search(**kwargs)
    
    tools = DatabaseMedicalTools(_db_pool)
    return await tools.search_doctors(**kwargs)

async def check_doctor_availability(**kwargs):
    """Check doctor availability using database."""
    if not _db_pool:
        # Fallback to test data if no DB
        from ..test_data import generate_appointment_slots
        doctor_id = kwargs.get('doctor_id')
        slots = generate_appointment_slots(doctor_id)
        # Format similar to DB response
        return {
            "doctor_id": doctor_id,
            "available_slots": [],
            "next_available": None
        }
    
    tools = DatabaseMedicalTools(_db_pool)
    return await tools.check_doctor_availability(**kwargs)

async def book_appointment_slot(**kwargs):
    """Book appointment slot using database."""
    if not _db_pool:
        return {"error": "Database not connected"}
    
    tools = DatabaseMedicalTools(_db_pool)
    return await tools.book_appointment_slot(**kwargs)

async def get_clinic_info(**kwargs):
    """Get clinic info using database."""
    if not _db_pool:
        # Fallback to test data if no DB
        from ..test_data import CLINICS
        return CLINICS
    
    tools = DatabaseMedicalTools(_db_pool)
    return await tools.get_clinic_info(**kwargs)