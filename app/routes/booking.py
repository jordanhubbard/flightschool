from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import User, Aircraft, Booking
from app import db
from app.forms import BookingForm
from datetime import datetime, timedelta

bp = Blueprint('booking', __name__)

@bp.route('/dashboard')
@login_required
def dashboard():
    aircraft = Aircraft.query.filter_by(status='available').all()
    instructors = User.query.filter(User.certificates.isnot(None)).all()  # Get users with certificates (instructors)
    user_bookings = Booking.query.filter_by(student_id=current_user.id).order_by(Booking.start_time).all()
    return render_template('booking/dashboard.html',
                         aircraft=aircraft,
                         instructors=instructors,
                         bookings=user_bookings)

@bp.route('/book', methods=['POST'])
@login_required
def create_booking():
    try:
        if request.form.get('start_time'):
            start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
        else:
            start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%d %H:%M')
        
        duration = int(request.form.get('duration', 1))
        aircraft_id = request.form.get('aircraft_id')
        instructor_id = request.form.get('instructor_id')
        
        end_time = start_time + timedelta(hours=duration)
        
        # Check for conflicts
        existing_booking = Booking.query.filter(
            Booking.aircraft_id == aircraft_id,
            Booking.status == 'scheduled',
            Booking.start_time <= end_time,
            Booking.end_time >= start_time
        ).first()
        
        if existing_booking:
            flash('Aircraft is already booked')
            return redirect(url_for('booking.dashboard'))
        
        if instructor_id:
            instructor_booking = Booking.query.filter(
                Booking.instructor_id == instructor_id,
                Booking.status == 'scheduled',
                Booking.start_time <= end_time,
                Booking.end_time >= start_time
            ).first()
            
            if instructor_booking:
                flash('Instructor is already booked')
                return redirect(url_for('booking.dashboard'))
        
        booking = Booking(
            student_id=current_user.id,
            aircraft_id=aircraft_id,
            instructor_id=instructor_id,
            start_time=start_time,
            end_time=end_time,
            status='scheduled'
        )
        
        db.session.add(booking)
        db.session.commit()
        
        flash('Booking created successfully')
        return redirect(url_for('booking.dashboard'))
        
    except Exception as e:
        flash('Error creating booking. Please try again.')
        return redirect(url_for('booking.dashboard'))

@bp.route('/booking/<int:id>/cancel', methods=['POST'])
@login_required
def cancel_booking(id):
    booking = Booking.query.get_or_404(id)
    if booking.student_id != current_user.id:
        flash('You are not authorized to cancel this booking')
        return redirect(url_for('booking.dashboard'))
    
    booking.status = 'cancelled'
    db.session.commit()
    flash('Booking cancelled successfully')
    return redirect(url_for('booking.dashboard'))

@bp.route('/calendar')
@login_required
def calendar_view():
    # Get bookings based on user role
    if current_user.is_admin:
        bookings = Booking.query.all()
    elif current_user.is_instructor:
        bookings = Booking.query.filter(
            (Booking.instructor_id == current_user.id) |
            (Booking.instructor_id.is_(None))
        ).all()
    else:
        bookings = Booking.query.filter_by(student_id=current_user.id).all()
    
    # Format bookings for FullCalendar
    events = []
    for booking in bookings:
        events.append({
            'id': booking.id,
            'title': f"{booking.aircraft.tail_number} - {booking.student.first_name} {booking.student.last_name}",
            'start': booking.start_time.isoformat(),
            'end': booking.end_time.isoformat(),
            'backgroundColor': '#28a745' if booking.status == 'scheduled' else '#6c757d',
            'borderColor': '#28a745' if booking.status == 'scheduled' else '#6c757d',
            'extendedProps': {
                'instructor': f"{booking.instructor.first_name} {booking.instructor.last_name}" if booking.instructor else 'Solo',
                'status': booking.status
            }
        })
    
    return render_template('booking/calendar.html', events=events) 