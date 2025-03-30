#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Aircraft, User, Booking

def load_test_data():
    app = create_app()
    
    with app.app_context():
        # Clear existing data
        Booking.query.delete()
        Aircraft.query.delete()
        User.query.filter(User.is_admin == False).delete()
        
        # Load test data
        with open('tests/test_data.json', 'r') as f:
            data = json.load(f)
        
        # Create aircraft
        aircraft_map = {}  # To store registration -> id mapping
        for aircraft_data in data['aircraft']:
            aircraft = Aircraft(**aircraft_data)
            db.session.add(aircraft)
            db.session.flush()  # This will assign the id
            aircraft_map[aircraft.registration] = aircraft.id
        
        # Create instructors
        instructor_map = {}  # To store email -> id mapping
        for instructor_data in data['instructors']:
            # Split name into first_name and last_name
            name_parts = instructor_data['name'].split(' ', 1)
            instructor = User(
                email=instructor_data['email'],
                first_name=name_parts[0],
                last_name=name_parts[1] if len(name_parts) > 1 else '',
                name=instructor_data['name'],
                phone=instructor_data['phone'],
                is_admin=instructor_data['is_admin'],
                certificates=','.join(instructor_data['certificates'])
            )
            instructor.set_password('password123')  # Set a default password
            db.session.add(instructor)
            db.session.flush()  # This will assign the id
            instructor_map[instructor.email] = instructor.id
        
        # Create students
        student_map = {}  # To store email -> id mapping
        for student_data in data['students']:
            # Split name into first_name and last_name
            name_parts = student_data['name'].split(' ', 1)
            student = User(
                email=student_data['email'],
                first_name=name_parts[0],
                last_name=name_parts[1] if len(name_parts) > 1 else '',
                name=student_data['name'],
                phone=student_data['phone'],
                student_id=student_data['student_id'],
                is_admin=False
            )
            student.set_password('password123')  # Set a default password
            db.session.add(student)
            db.session.flush()  # This will assign the id
            student_map[student.email] = student.id

        # Create bookings
        for booking_data in data['bookings']:
            booking = Booking(
                student_id=student_map[booking_data['student_email']],
                instructor_id=instructor_map[booking_data['instructor_email']],
                aircraft_id=aircraft_map[booking_data['registration']],
                start_time=datetime.fromisoformat(booking_data['start_time']),
                end_time=datetime.fromisoformat(booking_data['end_time']),
                status=booking_data['status']
            )
            db.session.add(booking)

        db.session.commit()
        print("Test data loaded successfully!")
        print("\nDefault login credentials:")
        print("Admin: john.smith@flightschool.com / password123")
        print("Instructor: sarah.jones@flightschool.com / password123")
        print("Student 1: student1@example.com / password123")
        print("Student 2: student2@example.com / password123")

if __name__ == '__main__':
    load_test_data() 