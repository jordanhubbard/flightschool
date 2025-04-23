from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app.models import Booking, Aircraft, User
from datetime import datetime, timedelta

booking_bp = Blueprint('booking', __name__)


@booking_bp.route('/bookings', methods=['GET'])
@login_required
def list():
    """List all bookings."""
    if current_user.is_admin:
        bookings = Booking.query.order_by(Booking.start_time.desc()).all()
    else:
        bookings = Booking.query.filter_by(student_id=current_user.id).order_by(Booking.start_time.desc()).all()
    
    return render_template('booking/list.html', bookings=bookings)


@booking_bp.route('/dashboard')
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
