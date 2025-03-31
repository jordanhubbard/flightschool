from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session, current_app
from flask_login import login_required, current_user
from app.models import User, Aircraft, Booking
from app import db
from app.forms import BookingForm, GoogleCalendarSettingsForm, FlightCheckoutForm, FlightCheckinForm
from datetime import datetime, timedelta
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import oauthlib.oauth2.rfc6749.errors

bp = Blueprint('booking', __name__)

# Google Calendar API settings
GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI")],
        "scopes": ["https://www.googleapis.com/auth/calendar"]
    }
}

@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_instructor:
        return redirect(url_for('booking.instructor_dashboard'))
    aircraft = Aircraft.query.filter_by(status='available').all()
    instructors = User.query.filter(User.certificates.isnot(None)).all()  # Get users with certificates (instructors)
    user_bookings = Booking.query.filter_by(student_id=current_user.id).order_by(Booking.start_time).all()
    return render_template('booking/dashboard.html',
                         aircraft=aircraft,
                         instructors=instructors,
                         bookings=user_bookings)

@bp.route('/instructor/dashboard')
@login_required
def instructor_dashboard():
    if not current_user.is_instructor:
        flash('Access denied. Instructor privileges required.', 'error')
        return redirect(url_for('booking.dashboard'))
    
    instructor_bookings = Booking.query.filter_by(instructor_id=current_user.id).order_by(Booking.start_time).all()
    return render_template('booking/instructor_dashboard.html', bookings=instructor_bookings)

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

@bp.route('/booking/<int:booking_id>')
@login_required
def view_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if not (current_user.is_admin or booking.student_id == current_user.id or booking.instructor_id == current_user.id):
        flash('Access denied.', 'error')
        return redirect(url_for('booking.dashboard'))
    return render_template('booking/view.html', booking=booking)

@bp.route('/booking/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if not (current_user.is_admin or booking.student_id == current_user.id or booking.instructor_id == current_user.id):
        flash('Access denied.', 'error')
        return redirect(url_for('booking.dashboard'))
    
    booking.status = 'cancelled'
    db.session.commit()
    flash('Booking cancelled successfully.', 'success')
    return redirect(url_for('booking.dashboard'))

@bp.route('/list')
@login_required
def list_bookings():
    if current_user.is_admin:
        bookings = Booking.query.order_by(Booking.start_time).all()
    elif current_user.is_instructor:
        bookings = Booking.query.filter_by(instructor_id=current_user.id).order_by(Booking.start_time).all()
    else:
        bookings = Booking.query.filter_by(student_id=current_user.id).order_by(Booking.start_time).all()
    return render_template('booking/list.html', bookings=bookings)

@bp.route('/settings/calendar')
@login_required
def calendar_settings():
    form = GoogleCalendarSettingsForm()
    return render_template('booking/calendar_settings.html', form=form)

@bp.route('/settings/calendar/authorize')
@login_required
def authorize_google_calendar():
    # Allow insecure transport in development/testing mode
    if current_app.config['TESTING'] or current_app.config['DEBUG']:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    try:
        flow = Flow.from_client_config(
            GOOGLE_CLIENT_CONFIG,
            scopes=GOOGLE_CLIENT_CONFIG['web']['scopes'],
            redirect_uri=GOOGLE_CLIENT_CONFIG['web']['redirect_uris'][0]
        )
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        session['oauth_state'] = state
        return redirect(authorization_url)
    except Exception as e:
        flash(f'Error initiating calendar connection: {str(e)}', 'error')
        return redirect(url_for('booking.calendar_settings'))

@bp.route('/settings/calendar/callback')
@login_required
def google_calendar_callback():
    try:
        # Verify OAuth state to prevent CSRF attacks
        state = request.args.get('state')
        if not state or state != session.get('oauth_state'):
            flash('Invalid OAuth state', 'error')
            return redirect(url_for('booking.calendar_settings'))
        
        # Get authorization code
        code = request.args.get('code')
        if not code:
            flash('No authorization code received', 'error')
            return redirect(url_for('booking.calendar_settings'))
        
        # Exchange code for token
        flow = Flow.from_client_config(
            GOOGLE_CLIENT_CONFIG,
            scopes=GOOGLE_CLIENT_CONFIG['web']['scopes'],
            state=state
        )
        flow.redirect_uri = url_for('booking.google_calendar_callback', _external=True)
        
        # Handle insecure transport in development/testing mode
        if current_app.config['TESTING'] or current_app.config['DEVELOPMENT']:
            os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        
        try:
            flow.fetch_token(code=code)
        except oauthlib.oauth2.rfc6749.errors.InsecureTransportError:
            flash('OAuth 2 requires HTTPS. Please enable HTTPS in production.', 'error')
            return redirect(url_for('booking.calendar_settings'))
        
        # Store credentials
        current_user.google_calendar_credentials = flow.credentials.to_json()
        current_user.google_calendar_enabled = True
        db.session.commit()
        
        # Set session variable for UI state
        session['google_calendar_connected'] = True
        
        flash('Calendar connected successfully', 'success')
        return redirect(url_for('booking.calendar_settings'))
    except Exception as e:
        flash('Error connecting to Google Calendar', 'error')
        return redirect(url_for('booking.calendar_settings'))

@bp.route('/settings/calendar/disconnect')
@login_required
def disconnect_google_calendar():
    try:
        current_user.google_calendar_enabled = False
        current_user.google_calendar_token = None
        current_user.google_calendar_refresh_token = None
        current_user.google_calendar_token_expiry = None
        current_user.google_calendar_id = None
        
        db.session.commit()
        # Clear session variable for UI state
        session.pop('google_calendar_connected', None)
        flash('Google Calendar disconnected successfully', 'success')
    except Exception as e:
        flash(f'Error disconnecting calendar: {str(e)}', 'error')
    
    return redirect(url_for('booking.calendar_settings'))

@bp.route('/booking/<int:id>/checkout', methods=['GET', 'POST'])
@login_required
def checkout_booking(id):
    booking = Booking.query.get_or_404(id)
    
    # Verify user is authorized (student or instructor)
    if not (current_user.id == booking.student_id or 
            (booking.instructor_id and current_user.id == booking.instructor_id)):
        flash('You are not authorized to check out this aircraft', 'error')
        return redirect(url_for('booking.list'))
    
    # Verify booking is confirmed and not already checked out
    if booking.status != 'confirmed':
        flash('This booking is not confirmed', 'error')
        return redirect(url_for('booking.list'))
    
    if booking.checkout_time:
        flash('This aircraft has already been checked out', 'error')
        return redirect(url_for('booking.list'))
    
    form = FlightCheckoutForm()
    if form.validate_on_submit():
        if not form.agree_to_fly.data:
            flash('You must agree to fly the aircraft to check out', 'error')
            return render_template('booking/checkout.html', form=form, booking=booking)
        
        try:
            booking.checkout_time = datetime.utcnow()
            booking.checkout_hobbs = form.hobbs.data
            booking.checkout_tach = form.tach.data
            booking.checkout_squawks = form.squawks.data
            booking.checkout_comments = form.comments.data
            booking.checkout_instructor_id = current_user.id if current_user.is_instructor else None
            booking.status = 'in_progress'
            
            db.session.commit()
            flash('Aircraft checked out successfully', 'success')
            return redirect(url_for('booking.list'))
        except Exception as e:
            db.session.rollback()
            flash('Error checking out aircraft', 'error')
            return render_template('booking/checkout.html', form=form, booking=booking)
    
    return render_template('booking/checkout.html', form=form, booking=booking)

@bp.route('/booking/<int:id>/checkin', methods=['GET', 'POST'])
@login_required
def checkin_booking(id):
    booking = Booking.query.get_or_404(id)
    
    # Verify user is authorized (student or instructor)
    if not (current_user.id == booking.student_id or 
            (booking.instructor_id and current_user.id == booking.instructor_id)):
        flash('You are not authorized to check in this aircraft', 'error')
        return redirect(url_for('booking.list'))
    
    # Verify booking is in progress and not already checked in
    if booking.status != 'in_progress':
        flash('This booking is not in progress', 'error')
        return redirect(url_for('booking.list'))
    
    if booking.checkin_time:
        flash('This aircraft has already been checked in', 'error')
        return redirect(url_for('booking.list'))
    
    form = FlightCheckinForm()
    if form.validate_on_submit():
        try:
            booking.checkin_time = datetime.utcnow()
            booking.checkin_hobbs = form.hobbs.data
            booking.checkin_tach = form.tach.data
            booking.checkin_squawks = form.squawks.data
            booking.checkin_comments = form.comments.data
            booking.checkin_instructor_id = current_user.id if current_user.is_instructor else None
            booking.status = 'completed'
            
            db.session.commit()
            flash('Aircraft checked in successfully', 'success')
            return redirect(url_for('booking.list'))
        except Exception as e:
            db.session.rollback()
            flash('Error checking in aircraft', 'error')
            return render_template('booking/checkin.html', form=form, booking=booking)
    
    return render_template('booking/checkin.html', form=form, booking=booking) 