from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session, current_app, abort
from flask_login import login_required, current_user
from app.models import User, Aircraft, Booking, CheckIn, CheckOut, Invoice
from app import db
from app.forms import (
    BookingForm, GoogleCalendarSettingsForm, FlightCheckoutForm, FlightCheckinForm,
    CheckInForm, CheckOutForm, InvoiceForm
)
from datetime import datetime, timedelta
from app.calendar_service import GoogleCalendarService
import os

bp = Blueprint('booking', __name__)
calendar_service = GoogleCalendarService()

@bp.route('/google-auth')
@login_required
def google_auth():
    """Start Google Calendar OAuth2 flow."""
    authorization_url = calendar_service.get_authorization_url()
    return redirect(authorization_url)

@bp.route('/google-callback')
@login_required
def google_callback():
    """Handle Google Calendar OAuth2 callback."""
    code = request.args.get('code')
    if not code:
        flash('Failed to authenticate with Google Calendar')
        return redirect(url_for('booking.dashboard'))
    
    try:
        credentials = calendar_service.handle_callback(code)
        session['google_credentials'] = credentials.to_json()
        flash('Successfully connected to Google Calendar')
    except Exception as e:
        flash(f'Error connecting to Google Calendar: {str(e)}')
    
    return redirect(url_for('booking.dashboard'))

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
    instructors = User.query.filter(User.is_instructor == True).all()
    user_bookings = Booking.query.filter_by(student_id=current_user.id).order_by(Booking.start_time).all()
    has_google_auth = current_user.google_calendar_enabled if hasattr(current_user, 'google_calendar_enabled') else False
    return render_template('booking/dashboard.html',
                         aircraft=aircraft,
                         instructors=instructors,
                         bookings=user_bookings,
                         has_google_auth=has_google_auth)

@bp.route('/instructor/dashboard')
@login_required
def instructor_dashboard():
    if not current_user.is_instructor:
        flash('Access denied. Instructor privileges required.', 'error')
        return redirect(url_for('booking.dashboard'))
    
    instructor_bookings = Booking.query.filter_by(instructor_id=current_user.id).order_by(Booking.start_time).all()
    return render_template('booking/instructor_dashboard.html', bookings=instructor_bookings)

@bp.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    """Create a new booking."""
    form = BookingForm()
    aircraft = Aircraft.query.filter_by(status='available').all()
    instructors = User.query.filter(User.is_instructor == True).all()
    
    form.aircraft_id.choices = [(a.id, f"{a.registration} - {a.make_model}") for a in aircraft]
    form.instructor_id.choices = [(i.id, f"{i.first_name} {i.last_name}") for i in instructors]
    form.instructor_id.choices.insert(0, (0, "No Instructor"))
    
    if form.validate_on_submit():
        start_time = form.start_time.data
        duration = form.duration.data
        end_time = start_time + timedelta(hours=duration)
        
        # Check for conflicts
        aircraft_id = form.aircraft_id.data
        instructor_id = form.instructor_id.data if form.instructor_id.data != 0 else None
        
        existing_booking = Booking.query.filter(
            Booking.aircraft_id == aircraft_id,
            Booking.status != 'cancelled',
            Booking.start_time < end_time,
            Booking.end_time > start_time
        ).first()
        
        if existing_booking:
            flash('Time slot is not available', 'error')
            return render_template('booking/book.html', form=form)
        
        if instructor_id:
            instructor_booking = Booking.query.filter(
                Booking.instructor_id == instructor_id,
                Booking.status != 'cancelled',
                Booking.start_time < end_time,
                Booking.end_time > start_time
            ).first()
            
            if instructor_booking:
                flash('Instructor is not available at this time', 'error')
                return render_template('booking/book.html', form=form)
        
        booking = Booking(
            student_id=current_user.id,
            aircraft_id=aircraft_id,
            instructor_id=instructor_id,
            start_time=start_time,
            end_time=end_time,
            status='confirmed'
        )
        
        db.session.add(booking)
        db.session.commit()
        
        flash('Booking created successfully', 'success')
        return redirect(url_for('booking.list_bookings'))
    
    return render_template('booking/book.html', form=form)

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
    
    # Delete Google Calendar events for all relevant users
    if booking.instructor and booking.instructor.google_calendar_enabled:
        try:
            calendar_service.delete_event(booking.google_calendar_event_id, booking.instructor)
        except Exception as e:
            flash(f'Failed to delete instructor\'s Google Calendar event: {str(e)}')
    
    if current_user.google_calendar_enabled:
        try:
            calendar_service.delete_event(booking.google_calendar_event_id, current_user)
        except Exception as e:
            flash(f'Failed to delete your Google Calendar event: {str(e)}')
    
    admin = User.query.filter_by(is_admin=True).first()
    if admin and admin.google_calendar_enabled:
        try:
            calendar_service.delete_event(booking.google_calendar_event_id, admin)
        except Exception as e:
            flash(f'Failed to delete admin\'s Google Calendar event: {str(e)}')
    
    booking.status = 'cancelled'
    db.session.commit()
    flash('Booking cancelled successfully.', 'success')
    return redirect(url_for('booking.dashboard'))

@bp.route('/list')
@login_required
def list_bookings():
    """List all bookings for the current user."""
    if current_user.is_admin:
        bookings = Booking.query.all()
    elif current_user.is_instructor:
        bookings = Booking.query.filter_by(instructor_id=current_user.id).all()
    else:
        bookings = Booking.query.filter_by(student_id=current_user.id).all()
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

@bp.route('/check-in/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def check_in_booking(booking_id):
    """Check in for a booking."""
    booking = Booking.query.get_or_404(booking_id)
    if not (current_user.is_admin or booking.student_id == current_user.id or booking.instructor_id == current_user.id):
        flash('Access denied.', 'error')
        return redirect(url_for('booking.dashboard'))
    
    form = CheckInForm()
    if form.validate_on_submit():
        check_in = CheckIn(
            booking_id=booking.id,
            aircraft_id=booking.aircraft_id,
            instructor_id=booking.instructor_id,
            hobbs_start=form.hobbs_start.data,
            tach_start=form.tach_start.data,
            notes=form.notes.data
        )
        
        booking.status = 'in_progress'
        db.session.add(check_in)
        db.session.commit()
        
        flash('Check-in completed successfully', 'success')
        return redirect(url_for('booking.view_booking', booking_id=booking.id))
    
    return render_template('booking/check_in.html', booking=booking, form=form)

@bp.route('/check-out/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def check_out_booking(booking_id):
    """Check out from a booking."""
    booking = Booking.query.get_or_404(booking_id)
    check_in = CheckIn.query.filter_by(booking_id=booking.id).first_or_404()
    form = CheckOutForm()
    
    if form.validate_on_submit():
        check_out = CheckOut(
            booking_id=booking.id,
            aircraft_id=booking.aircraft_id,
            instructor_id=booking.instructor_id,
            hobbs_end=form.hobbs_end.data,
            tach_end=form.tach_end.data,
            total_aircraft_time=form.hobbs_end.data - check_in.hobbs_start,
            notes=form.notes.data
        )
        
        booking.status = 'completed'
        db.session.add(check_out)
        db.session.commit()
        
        flash('Check-out completed successfully', 'success')
        return redirect(url_for('booking.view_booking', booking_id=booking.id))
    
    return render_template('booking/check_out.html', booking=booking, check_in=check_in, form=form)

@bp.route('/booking/<int:id>/invoice', methods=['GET', 'POST'])
@login_required
def generate_invoice(id):
    booking = Booking.query.get_or_404(id)
    if not (current_user.is_admin or booking.student_id == current_user.id or booking.instructor_id == current_user.id):
        abort(403)

    if not booking.check_out:
        flash('Cannot generate invoice without checking out first.')
        return redirect(url_for('booking.view_booking', booking_id=id))

    form = InvoiceForm()
    if form.validate_on_submit():
        invoice = Invoice(
            booking_id=booking.id,
            aircraft_id=booking.aircraft_id,
            student_id=booking.student_id,
            invoice_number=form.invoice_number.data,
            aircraft_rate=form.aircraft_rate.data,
            instructor_rate=form.instructor_rate.data if form.instructor_rate.data else None,
            aircraft_time=form.aircraft_time.data,
            instructor_time=form.instructor_time.data if form.instructor_time.data else None,
            notes=form.notes.data,
            status='pending'
        )
        db.session.add(invoice)
        db.session.commit()
        flash('Invoice generated successfully.')
        return redirect(url_for('booking.view_booking', booking_id=id))

    # Pre-fill form with calculated values
    if not form.is_submitted():
        form.aircraft_time.data = booking.check_out.hobbs_end - booking.check_in.hobbs_start
        if booking.instructor_id and booking.check_out.instructor_end_time and booking.check_in.instructor_start_time:
            form.instructor_time.data = (booking.check_out.instructor_end_time - booking.check_in.instructor_start_time).total_seconds() / 3600

    return render_template('booking/invoice.html', form=form, booking=booking)

@bp.route('/booking/<int:booking_id>/cancel', methods=['POST'])
@login_required
def alt_cancel_booking(booking_id):
    """Alternative route for canceling a booking (to match test expectations)."""
    return cancel_booking(booking_id)
