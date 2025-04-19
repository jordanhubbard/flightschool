#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime, time

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import (
    Aircraft, User, Booking, MaintenanceType, MaintenanceRecord, Squawk,
    WeatherMinima, FlightLog, Endorsement, Document, AuditLog, WaitlistEntry,
    RecurringBooking
)

def load_test_data():
    app = create_app()
    
    with app.app_context():
        # Clear existing data
        RecurringBooking.query.delete()
        WaitlistEntry.query.delete()
        AuditLog.query.delete()
        Document.query.delete()
        Endorsement.query.delete()
        FlightLog.query.delete()
        WeatherMinima.query.delete()
        Booking.query.delete()
        MaintenanceRecord.query.delete()
        Squawk.query.delete()
        MaintenanceType.query.delete()
        Aircraft.query.delete()
        User.query.delete()
        
        # Load test data
        test_data_path = os.path.join(os.path.dirname(__file__), '..', 'tests', 'test_data.json')
        with open(test_data_path, 'r') as f:
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
        
        # Create weather minima
        for minima_data in data['weather_minima']:
            minima = WeatherMinima(**minima_data)
            db.session.add(minima)
        
        # Create bookings
        booking_map = {}  # To store index -> Booking object mapping
        for idx, booking_data in enumerate(data['bookings'], 1):
            student = user_map[booking_data['student_email']]
            instructor = user_map[booking_data['instructor_email']] if booking_data.get('instructor_email') else None
            aircraft = aircraft_map[booking_data['aircraft_registration']]
            booking = Booking(
                student=student,
                instructor=instructor,
                aircraft=aircraft,
                start_time=datetime.fromisoformat(booking_data['start_time']),
                end_time=datetime.fromisoformat(booking_data['end_time']),
                status=booking_data['status'],
                cancellation_reason=booking_data.get('cancellation_reason'),
                cancellation_notes=booking_data.get('cancellation_notes'),
                weather_briefing=booking_data.get('weather_briefing'),
                notification_sent=booking_data.get('notification_sent', False)
            )
            db.session.add(booking)
            db.session.flush()
            booking_map[idx] = booking
        
        # Create flight logs
        for log_data in data['flight_logs']:
            pic = user_map[log_data['pic_email']]
            sic = user_map[log_data['sic_email']] if log_data.get('sic_email') else None
            booking = booking_map[log_data['booking_id']]
            log = FlightLog(
                booking=booking,
                pic=pic,
                sic=sic,
                flight_date=datetime.fromisoformat(log_data['flight_date']),
                route=log_data['route'],
                remarks=log_data['remarks'],
                weather_conditions=log_data['weather_conditions'],
                ground_instruction=log_data['ground_instruction'],
                dual_received=log_data['dual_received'],
                pic_time=log_data['pic_time'],
                sic_time=log_data['sic_time'],
                cross_country=log_data['cross_country'],
                night=log_data['night'],
                actual_instrument=log_data['actual_instrument'],
                simulated_instrument=log_data['simulated_instrument'],
                landings_day=log_data['landings_day'],
                landings_night=log_data['landings_night']
            )
            db.session.add(log)
        
        # Create endorsements
        for endorsement_data in data['endorsements']:
            student = user_map[endorsement_data['student_email']]
            instructor = user_map[endorsement_data['instructor_email']]
            endorsement = Endorsement(
                student=student,
                instructor=instructor,
                type=endorsement_data['type'],
                description=endorsement_data['description'],
                expiration=datetime.fromisoformat(endorsement_data['expiration']) if endorsement_data.get('expiration') else None,
                document_url=endorsement_data.get('document_url')
            )
            db.session.add(endorsement)
        
        # Create documents
        for doc_data in data['documents']:
            user = user_map[doc_data['user_email']]
            document = Document(
                user=user,
                type=doc_data['type'],
                filename=doc_data['filename'],
                url=doc_data['url'],
                expiration=datetime.fromisoformat(doc_data['expiration']) if doc_data.get('expiration') else None
            )
            db.session.add(document)
        
        # Create waitlist entries
        for entry_data in data['waitlist_entries']:
            student = user_map[entry_data['student_email']]
            instructor = user_map[entry_data['instructor_email']] if entry_data.get('instructor_email') else None
            aircraft = aircraft_map[entry_data['aircraft_registration']]
            entry = WaitlistEntry(
                student=student,
                instructor=instructor,
                aircraft=aircraft,
                requested_date=datetime.fromisoformat(entry_data['requested_date']),
                time_preference=entry_data['time_preference'],
                duration_hours=entry_data['duration_hours'],
                status=entry_data['status']
            )
            db.session.add(entry)
        
        # Create recurring bookings
        for recurring_data in data['recurring_bookings']:
            student = user_map[recurring_data['student_email']]
            instructor = user_map[recurring_data['instructor_email']] if recurring_data.get('instructor_email') else None
            aircraft = aircraft_map[recurring_data['aircraft_registration']]
            recurring = RecurringBooking(
                student=student,
                instructor=instructor,
                aircraft=aircraft,
                day_of_week=recurring_data['day_of_week'],
                start_time=time.fromisoformat(recurring_data['start_time']),
                duration_hours=recurring_data['duration_hours'],
                start_date=datetime.fromisoformat(recurring_data['start_date']),
                end_date=datetime.fromisoformat(recurring_data['end_date']) if recurring_data.get('end_date') else None,
                status=recurring_data['status']
            )
            db.session.add(recurring)
        
        # Create audit logs
        for log_data in data['audit_logs']:
            user = user_map[log_data['user_email']]
            log = AuditLog(
                user=user,
                action=log_data['action'],
                table_name=log_data['table_name'],
                record_id=log_data['record_id'],
                changes=log_data['changes'],
                created_at=datetime.fromisoformat(log_data['created_at'])
            )
            db.session.add(log)

        db.session.commit()
        print("Test data loaded successfully!")
        print("\nLogin credentials from test_data.json:")
        for user_data in data['users']:
            print(f"{user_data['role'].title()}: {user_data['email']} / {user_data['password']}")

if __name__ == '__main__':
    load_test_data()