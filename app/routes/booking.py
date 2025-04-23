from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app.models import Booking, Aircraft, User
from datetime import datetime, timedelta
from app import db
from functools import wraps

booking_bp = Blueprint('booking', __name__)


def instructor_or_admin_required(f):
    """Decorator to require instructor or admin access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_instructor and not current_user.is_admin:
            flash('Permission denied. Instructor or admin privileges required.', 'error')
            return redirect(url_for('booking.list_bookings'))
        return f(*args, **kwargs)
    return decorated_function


def booking_access_required(f):
    """Decorator to check if user has access to the booking."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        booking = Booking.query.get_or_404(kwargs.get('id'))
        if (booking.student_id != current_user.id and 
            booking.instructor_id != current_user.id and 
            not current_user.is_admin):
            flash('Permission denied.', 'error')
            return redirect(url_for('booking.list_bookings'))
        return f(*args, **kwargs)
    return decorated_function


@booking_bp.route('/booking/list')
@login_required
def list_bookings():
    """List all bookings."""
    if current_user.is_admin:
        bookings = Booking.query.order_by(Booking.start_time.desc()).all()
    else:
        bookings = Booking.query.filter_by(student_id=current_user.id).order_by(Booking.start_time.desc()).all()
    
    return render_template('booking/list.html', bookings=bookings)


@booking_bp.route('/booking/dashboard')
@login_required
def dashboard():
    """Display the booking dashboard."""
    upcoming_bookings = Booking.query.filter(
        Booking.student_id == current_user.id,
        Booking.start_time > datetime.now()
    ).order_by(Booking.start_time).all()

    available_aircraft = Aircraft.query.filter_by(status='available').all()
    
    return render_template('booking/dashboard.html',
                         upcoming_bookings=upcoming_bookings,
                         available_aircraft=available_aircraft)


@booking_bp.route('/booking/weather-minima')
@login_required
def weather_minima():
    """Display weather minima requirements."""
    return render_template('booking/weather_minima.html')


@booking_bp.route('/booking/recurring')
@login_required
def recurring_bookings():
    """Display and manage recurring bookings."""
    recurring = Booking.query.filter_by(
        student_id=current_user.id,
        is_recurring=True
    ).order_by(Booking.start_time).all()
    return render_template('booking/recurring.html', bookings=recurring)


@booking_bp.route('/booking/waitlist')
@login_required
def waitlist():
    """Display and manage waitlist entries."""
    waitlist_entries = Booking.query.filter_by(
        student_id=current_user.id,
        status='waitlist'
    ).order_by(Booking.created_at).all()
    return render_template('booking/waitlist.html', entries=waitlist_entries)


@booking_bp.route('/booking/create', methods=['POST'])
@login_required
def create_booking():
    """Create a new booking."""
    aircraft_id = request.form.get('aircraft_id')
    start_time = request.form.get('start_time')
    duration = request.form.get('duration')

    if not all([aircraft_id, start_time, duration]):
        flash('All fields are required.', 'error')
        return redirect(url_for('booking.dashboard'))

    try:
        duration = int(duration)
        if duration <= 0:
            flash('Duration must be greater than 0.', 'error')
            return redirect(url_for('booking.dashboard'))

        start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
        end_time = start_time + timedelta(minutes=duration)

        booking = Booking(
            student_id=current_user.id,
            aircraft_id=aircraft_id,
            start_time=start_time,
            end_time=end_time,
            status='pending'
        )
        db.session.add(booking)
        db.session.commit()
        flash('Booking created successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error creating booking.', 'error')

    return redirect(url_for('booking.dashboard'))


@booking_bp.route('/booking/<int:id>/cancel', methods=['POST'])
@login_required
@booking_access_required
def cancel_booking(id):
    """Cancel a booking."""
    booking = Booking.query.get_or_404(id)
    booking.status = 'cancelled'
    db.session.commit()
    flash('Booking cancelled successfully.', 'success')
    return redirect(url_for('booking.dashboard'))


@booking_bp.route('/booking/<int:id>')
@login_required
@booking_access_required
def view_booking(id):
    """View a specific booking."""
    booking = Booking.query.get_or_404(id)
    return render_template('booking/view.html', booking=booking)
