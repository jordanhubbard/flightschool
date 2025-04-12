#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Aircraft, User, Booking, MaintenanceType, MaintenanceRecord, Squawk

def load_test_data():
    app = create_app()
    
    with app.app_context():
        # Clear existing data
        Booking.query.delete()
        MaintenanceRecord.query.delete()
        Squawk.query.delete()
        MaintenanceType.query.delete()
        Aircraft.query.delete()
        User.query.delete()
        
        # Load test data
        with open('test_data.json', 'r') as f:
            data = json.load(f)
        
        # Create users first (needed for foreign keys)
        user_map = {}  # To store email -> User object mapping
        for user_data in data['users']:
            user = User(
                email=user_data['email'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                role=user_data['role'],
                is_admin=user_data.get('is_admin', False),
                is_instructor=user_data.get('is_instructor', False),
                status=user_data.get('status', 'active'),
                phone=user_data.get('phone'),
                student_id=user_data.get('student_id'),
                certificates=user_data.get('certificates'),
                instructor_rate_per_hour=user_data.get('instructor_rate_per_hour')
            )
            user.set_password(user_data['password'])
            db.session.add(user)
            db.session.flush()
            user_map[user.email] = user
        
        # Create aircraft
        aircraft_map = {}  # To store registration -> Aircraft object mapping
        for aircraft_data in data['aircraft']:
            aircraft = Aircraft(**aircraft_data)
            db.session.add(aircraft)
            db.session.flush()
            aircraft_map[aircraft.registration] = aircraft
        
        # Create maintenance types
        maint_type_map = {}  # To store name -> MaintenanceType object mapping
        for mtype_data in data['maintenance_types']:
            created_by = user_map[mtype_data.pop('created_by_email')]
            mtype = MaintenanceType(
                name=mtype_data['name'],
                description=mtype_data['description'],
                interval_days=mtype_data.get('interval_days'),
                interval_hours=mtype_data.get('interval_hours'),
                created_by=created_by
            )
            db.session.add(mtype)
            db.session.flush()
            maint_type_map[mtype.name] = mtype
        
        # Create maintenance records
        for record_data in data['maintenance_records']:
            aircraft = aircraft_map[record_data['aircraft_registration']]
            mtype = maint_type_map[record_data['maintenance_type']]
            performed_by = user_map[record_data['performed_by_email']]
            record = MaintenanceRecord(
                aircraft=aircraft,
                maintenance_type=mtype,
                performed_at=datetime.fromisoformat(record_data['performed_at']),
                performed_by=performed_by,
                notes=record_data['notes'],
                hobbs_hours=record_data['hobbs_hours'],
                tach_hours=record_data['tach_hours']
            )
            db.session.add(record)
        
        # Create squawks
        for squawk_data in data['squawks']:
            aircraft = aircraft_map[squawk_data['aircraft_registration']]
            reported_by = user_map[squawk_data['reported_by_email']]
            squawk = Squawk(
                aircraft=aircraft,
                description=squawk_data['description'],
                reported_by=reported_by,
                status=squawk_data['status'],
                created_at=datetime.fromisoformat(squawk_data['created_at'])
            )
            db.session.add(squawk)
        
        # Create bookings
        for booking_data in data['bookings']:
            student = user_map[booking_data['student_email']]
            instructor = user_map[booking_data['instructor_email']] if booking_data.get('instructor_email') else None
            aircraft = aircraft_map[booking_data['aircraft_registration']]
            booking = Booking(
                student=student,
                instructor=instructor,
                aircraft=aircraft,
                start_time=datetime.fromisoformat(booking_data['start_time']),
                end_time=datetime.fromisoformat(booking_data['end_time']),
                status=booking_data['status']
            )
            db.session.add(booking)

        db.session.commit()
        print("Test data loaded successfully!")
        print("\nLogin credentials from test_data.json:")
        for user_data in data['users']:
            print(f"{user_data['role'].title()}: {user_data['email']} / {user_data['password']}")

if __name__ == '__main__':
    load_test_data() 