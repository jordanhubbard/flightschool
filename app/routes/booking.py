from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session, current_app, abort
from flask_login import login_required, current_user
from app.models import User, Aircraft, Booking, CheckIn, CheckOut, Invoice, AuditLog, FlightLog, RecurringBooking, WaitlistEntry, WeatherMinima
from app import db
from app.forms import (
    BookingForm,
    GoogleCalendarSettingsForm,
    FlightCheckoutForm,
    FlightCheckinForm,
    CheckInForm,
    CheckOutForm,
    InvoiceForm)
from datetime import datetime, timedelta, timezone, UTC
from app.calendar_service import GoogleCalendarService
import os
from sqlalchemy import and_, or_

booking_bp = Blueprint('booking', __name__)
calendar_service = GoogleCalendarService()


def get_aircraft(aircraft_id):
    """Get aircraft by ID."""
    return Aircraft.query.get(aircraft_id)


def get_instructor(instructor_id):
    """Get instructor by ID."""
    if instructor_id == 0:
        return None
    return User.query.get(instructor_id)


def get_daily_schedule(date):
    """Get schedule for all aircraft and instructors for a given date."""
    start_of_day = datetime.combine(
        date, datetime.min.time()).replace(
        tzinfo=UTC)
    end_of_day = datetime.combine(
        date, datetime.max.time()).replace(
        tzinfo=UTC)

    # Get all bookings for the day
    bookings = Booking.query.filter(
        Booking.start_time >= start_of_day,
        Booking.end_time <= end_of_day,
        Booking.status != 'cancelled'
    ).all()

    # Organize bookings by aircraft and instructor
    schedule = {
        'aircraft': {},
        'instructors': {}
    }

    # Initialize schedule for all aircraft
    for aircraft in Aircraft.query.filter_by(status='available').all():
        schedule['aircraft'][aircraft.id] = {
            'aircraft': aircraft,
            'bookings': [b for b in bookings if b.aircraft_id == aircraft.id]
        }

    # Initialize schedule for all instructors
    for instructor in User.query.filter_by(
            role='instructor', status='active').all():
        schedule['instructors'][instructor.id] = {
            'instructor': instructor,
            'bookings': [b for b in bookings if b.instructor_id == instructor.id]
        }

    return schedule


@booking_bp.route('/google-auth')
@login_required
def google_auth():
    """Start Google Calendar OAuth2 flow."""
    authorization_url = calendar_service.get_authorization_url()
    return redirect(authorization_url)


@booking_bp.route('/google-callback')
@login_required
def google_callback():
    """Handle Google Calendar OAuth2 callback."""
    code = request.args.get('code')
    if not code:
        flash('Failed to authenticate with Google Calendar', 'error')
        return redirect(url_for('booking.dashboard'))

    try:
        credentials = calendar_service.handle_callback(code)
        current_user.google_calendar_credentials = credentials.to_json()
        current_user.google_calendar_enabled = True
        db.session.commit()
        flash('Successfully connected to Google Calendar', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Google Calendar connection error: {str(e)}')
        flash(f'Error connecting to Google Calendar: {str(e)}', 'error')

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


@booking_bp.route('/dashboard')
@login_required
def dashboard():
    """Display the booking dashboard."""
    # DEBUG: Print all bookings for current user
    debug_bookings = Booking.query.filter(Booking.student_id == current_user.id).order_by(Booking.start_time).all()
    for b in debug_bookings:
        print(f"DEBUG: Booking {b.id} start_time={b.start_time} status={b.status}")
    # END DEBUG

    upcoming_bookings = Booking.query.filter(
        Booking.student_id == current_user.id,
        Booking.start_time > datetime.now(UTC)
    ).order_by(Booking.start_time).all()

    # Get available aircraft
    available_aircraft = Aircraft.query.filter_by(status='available').all()

    # Get available instructors
    available_instructors = User.query.filter_by(
        role='instructor',
        status='active'
    ).all()

    return render_template(
        'booking/dashboard.html',
        title='Booking Dashboard',
        upcoming_bookings=upcoming_bookings,
        available_aircraft=available_aircraft,
        available_instructors=available_instructors
    )


@booking_bp.route('/instructor/dashboard')
@login_required
def instructor_dashboard():
    """Display instructor dashboard."""
    if not current_user.is_instructor:
        flash('Access denied. Instructor privileges required.', 'error')
        return redirect(url_for('booking.dashboard'))

    instructor_bookings = Booking.query.filter_by(
        instructor_id=current_user.id
    ).order_by(Booking.start_time).all()

    return render_template(
        'booking/instructor_dashboard.html',
        bookings=instructor_bookings
    )


@booking_bp.route('/bookings', methods=['GET', 'POST'])
@login_required
def create_booking():
    """Create a new booking."""
    form = BookingForm()
    # Always set choices before validation
    form.aircraft_id.choices = [
        (a.id, f"{a.registration} - {a.model}")
        for a in Aircraft.query.filter_by(status='available').all()
    ]
    form.instructor_id.choices = [
        (i.id, f"{i.first_name} {i.last_name}")
        for i in User.query.filter_by(role='instructor', status='active').all()
    ]

    if request.method == 'GET':
        # Set default start_time to now if not set
        if not form.start_time.data:
            form.start_time.data = datetime.utcnow()
        return render_template('booking/book.html', form=form)

    if request.method == 'POST':
        if request.is_json:
            form = BookingForm(data=request.get_json())
            # Set choices again for new form instance
            form.aircraft_id.choices = [
                (a.id, f"{a.registration} - {a.model}")
                for a in Aircraft.query.filter_by(status='available').all()
            ]
            form.instructor_id.choices = [
                (i.id, f"{i.first_name} {i.last_name}")
                for i in User.query.filter_by(role='instructor', status='active').all()
            ]

        if form.validate():
            try:
                # Use new calendar_datetime_start and calendar_datetime_end fields for start_time and duration
                calendar_datetime_start = request.form.get('calendar_datetime_start')
                calendar_datetime_end = request.form.get('calendar_datetime_end')
                from datetime import datetime, timezone
                if calendar_datetime_start and calendar_datetime_end:
                    try:
                        start_dt = datetime.fromisoformat(calendar_datetime_start)
                        end_dt = datetime.fromisoformat(calendar_datetime_end)
                        # Ensure UTC
                        if start_dt.tzinfo is None:
                            start_dt = start_dt.replace(tzinfo=timezone.utc)
                        if end_dt.tzinfo is None:
                            end_dt = end_dt.replace(tzinfo=timezone.utc)
                        form.start_time.data = start_dt
                        # Calculate duration in minutes
                        duration = int((end_dt - start_dt).total_seconds() / 60) + 30
                        form.duration.data = duration
                    except Exception as e:
                        flash(f"Invalid date/time: {e}", 'error')
                        return render_template('booking/book.html', form=form)

                # Create booking
                booking = Booking(
                    student_id=current_user.id,
                    aircraft_id=form.aircraft_id.data,
                    instructor_id=form.instructor_id.data,
                    start_time=form.start_time.data,
                    end_time=form.start_time.data + timedelta(minutes=form.duration.data),
                    status='pending',
                    notes=form.notes.data
                )
                db.session.add(booking)
                db.session.commit()

                if request.is_json:
                    return jsonify({
                        'status': 'success',
                        'message': 'Booking created successfully',
                        'booking_id': booking.id
                    }), 201
                flash('Booking created successfully', 'success')
                return redirect(url_for('booking.dashboard'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f'Booking creation error: {str(e)}')
                if request.is_json:
                    return jsonify({
                        'status': 'error',
                        'message': 'Failed to create booking'
                    }), 500
                flash('Failed to create booking. Please try again.', 'error')
        else:
            if request.is_json:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid form data',
                    'errors': form.errors
                }), 400
            flash('Invalid form data. Please check your input.', 'error')

    return render_template('booking/book.html', form=form)


@booking_bp.route('/bookings/<int:booking_id>', methods=['GET'])
@login_required
def view_booking(booking_id):
    """View a specific booking."""
    booking = Booking.query.get_or_404(booking_id)
    if booking.student_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to view this booking', 'error')
        return redirect(url_for('booking.dashboard'))
    return render_template('booking/view.html', booking=booking)


@booking_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    """Cancel a booking."""
    booking = Booking.query.get_or_404(booking_id)
    if booking.student_id != current_user.id and not current_user.is_admin:
        if request.is_json:
            return jsonify({
                'status': 'error',
                'message': 'Permission denied'
            }), 403
        flash('You do not have permission to cancel this booking', 'error')
        return redirect(url_for('booking.dashboard'))

    try:
        booking.status = 'cancelled'
        db.session.commit()
        if request.is_json:
            return jsonify({
                'status': 'success',
                'message': 'Booking cancelled successfully'
            })
        flash('Booking cancelled successfully', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Booking cancellation error: {str(e)}')
        if request.is_json:
            return jsonify({
                'status': 'error',
                'message': 'Failed to cancel booking'
            }), 500
        flash('Failed to cancel booking. Please try again.', 'error')

    return redirect(url_for('booking.dashboard'))


@booking_bp.route('/api/bookings/<int:booking_id>/checkin', methods=['POST'])
@login_required
def api_checkin(booking_id):
    """API endpoint for checking in a booking."""
    booking = Booking.query.get_or_404(booking_id)
    if not booking or booking.status != 'confirmed':
        abort(404)

    # Get check-in data from request
    data = request.get_json()
    if not data:
        abort(400)

    try:
        check_in = CheckIn(
            booking_id=booking.id,
            aircraft_id=booking.aircraft_id,
            instructor_id=booking.instructor_id if booking.instructor_id else None,
            hobbs_start=data.get('hobbs_start'),
            tach_start=data.get('tach_start'),
            notes=data.get('notes'))
        db.session.add(check_in)

        # Update booking status
        booking.status = 'in_progress'

        # Update aircraft hobbs and tach times
        aircraft = booking.aircraft
        aircraft.hobbs_time = data.get('hobbs_start')
        aircraft.tach_time = data.get('tach_start')

        db.session.commit()
        return jsonify({'message': 'Check-in successful'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@booking_bp.route('/api/bookings/<int:booking_id>/checkout', methods=['POST'])
@login_required
def api_checkout(booking_id):
    """API endpoint for checking out a booking."""
    booking = Booking.query.get_or_404(booking_id)
    if not booking or booking.status != 'in_progress':
        abort(404)

    # Get check-out data from request
    data = request.get_json()
    if not data:
        abort(400)

    try:
        check_out = CheckOut(
            booking_id=booking.id,
            aircraft_id=booking.aircraft_id,
            instructor_id=booking.instructor_id if booking.instructor_id else None,
            hobbs_end=data.get('hobbs_end'),
            tach_end=data.get('tach_end'),
            total_aircraft_time=data.get('total_aircraft_time'),
            total_instructor_time=data.get('total_instructor_time'),
            notes=data.get('notes'))
        db.session.add(check_out)

        # Update booking status
        booking.status = 'completed'

        # Update aircraft hobbs and tach times
        aircraft = booking.aircraft
        aircraft.hobbs_time = data.get('hobbs_end')
        aircraft.tach_time = data.get('tach_end')

        db.session.commit()

        # Create invoice
        create_invoice_for_booking(booking)

        return jsonify({'message': 'Check-out successful'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@booking_bp.route('/bookings/recurring', methods=['POST'])
@login_required
def create_recurring_booking():
    """Create a recurring booking."""
    data = request.get_json()

    # Validate required fields
    required_fields = [
        'aircraft_id', 'day_of_week', 'start_time',
        'duration_hours', 'start_date'
    ]
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    # Convert time string to time object
    try:
        start_time = datetime.strptime(data['start_time'], '%H:%M').time()
    except ValueError:
        return jsonify({'error': 'Invalid time format'}), 400

    # Create recurring booking
    recurring = RecurringBooking(
        student=current_user,
        instructor_id=data.get('instructor_id'),
        aircraft_id=data['aircraft_id'],
        day_of_week=data['day_of_week'],
        start_time=start_time,
        duration_hours=float(
            data['duration_hours']),
        start_date=datetime.fromisoformat(
            data['start_date']),
        end_date=datetime.fromisoformat(
            data['end_date']) if data.get('end_date') else None,
        status='active')

    try:
        db.session.add(recurring)
        db.session.commit()
        return jsonify({
            'message': 'Recurring booking created successfully',
            'recurring_id': recurring.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@booking_bp.route('/bookings/waitlist', methods=['POST'])
@login_required
def join_waitlist():
    """Join the waitlist for an aircraft."""
    data = request.get_json()

    # Validate required fields
    required_fields = ['aircraft_id', 'requested_date', 'duration_hours']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    # Create waitlist entry
    entry = WaitlistEntry(
        student=current_user,
        instructor_id=data.get('instructor_id'),
        aircraft_id=data['aircraft_id'],
        requested_date=datetime.fromisoformat(data['requested_date']),
        time_preference=data.get('time_preference'),
        duration_hours=float(data['duration_hours']),
        status='active'
    )

    try:
        db.session.add(entry)
        db.session.commit()
        return jsonify({
            'message': 'Added to waitlist successfully',
            'waitlist_id': entry.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@booking_bp.route('/bookings/waitlist/<int:entry_id>', methods=['DELETE'])
@login_required
def leave_waitlist(entry_id):
    """Remove an entry from the waitlist."""
    entry = WaitlistEntry.query.get_or_404(entry_id)

    if not (current_user.is_admin or current_user.id == entry.student_id):
        return jsonify({'error': 'Permission denied'}), 403

    try:
        db.session.delete(entry)
        db.session.commit()
        return jsonify({'message': 'Removed from waitlist successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@booking_bp.route('/bookings/weather-minima', methods=['GET'])
@login_required
def get_weather_minima():
    """Get weather minima for different categories."""
    minima = WeatherMinima.query.all()
    return jsonify([{
        'id': m.id,
        'category': m.category,
        'ceiling_min': m.ceiling_min,
        'visibility_min': m.visibility_min,
        'wind_max': m.wind_max,
        'crosswind_max': m.crosswind_max
    } for m in minima])


@booking_bp.route('/bookings/<int:booking_id>/weather', methods=['GET'])
@login_required
def get_weather_briefing(booking_id):
    """Get weather briefing for a booking."""
    booking = Booking.query.get_or_404(booking_id)

    # Check if user has permission to view this booking
    if not (current_user.is_admin or
            current_user.id == booking.student_id or
            current_user.id == booking.instructor_id):
        return jsonify({'error': 'Permission denied'}), 403

    if booking.weather_briefing:
        return jsonify(booking.weather_briefing)

    # If no weather briefing exists, fetch from weather service
    # TODO: Implement weather service integration
    return jsonify({'error': 'No weather briefing available'}), 404


@booking_bp.route('/bookings', methods=['GET'])
@login_required
def list():
    """List all bookings."""
    if current_user.is_admin:
        bookings = Booking.query.order_by(Booking.start_time.desc()).all()
    else:
        bookings = Booking.query.filter_by(
            student_id=current_user.id
        ).order_by(Booking.start_time.desc()).all()
    return render_template('booking/list.html', bookings=bookings)


@booking_bp.route('/settings/calendar')
@login_required
def calendar_settings():
    """Display calendar settings."""
    form = GoogleCalendarSettingsForm()
    return render_template('booking/calendar_settings.html', form=form)


@booking_bp.route('/settings/calendar/authorize')
@login_required
def authorize_google_calendar():
    """Authorize Google Calendar integration."""
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


@booking_bp.route('/settings/calendar/callback')
@login_required
def google_calendar_callback():
    """Handle Google Calendar OAuth2 callback."""
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
        flow.redirect_uri = url_for(
            'booking.google_calendar_callback',
            _external=True)

        # Handle insecure transport in development/testing mode
        if current_app.config['TESTING'] or current_app.config['DEVELOPMENT']:
            os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

        try:
            flow.fetch_token(code=code)
        except oauthlib.oauth2.rfc6749.errors.InsecureTransportError:
            flash(
                'OAuth 2 requires HTTPS. Please enable HTTPS in production.',
                'error')
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


@booking_bp.route('/settings/calendar/disconnect')
@login_required
def disconnect_google_calendar():
    """Disconnect Google Calendar integration."""
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


@booking_bp.route('/booking/<int:id>/checkout', methods=['GET', 'POST'])
@login_required
def checkout_booking(id):
    """Handle booking checkout."""
    booking = Booking.query.get_or_404(id)

    # Verify user is authorized (student or instructor)
    if not (current_user.id == booking.student_id or (
            booking.instructor_id and current_user.id == booking.instructor_id)):
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
            return render_template(
                'booking/checkout.html',
                form=form,
                booking=booking)

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
            return render_template(
                'booking/checkout.html',
                form=form,
                booking=booking)

    return render_template('booking/checkout.html', form=form, booking=booking)


@booking_bp.route('/check-in/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def check_in(booking_id):
    """Handle check-in for a booking."""
    booking = Booking.query.get_or_404(booking_id)

    # Verify user has permission
    if not (current_user.is_admin or current_user.id == booking.student_id):
        flash('You do not have permission to check in for this booking', 'error')
        return render_template('error.html', message='Permission denied'), 403

    # Prevent double check-in
    if CheckIn.query.filter_by(booking_id=booking.id).first():
        return render_template('error.html', message='Already checked in for this booking.'), 400

    if request.method == 'POST':
        form = CheckInForm()
        if form.validate_on_submit():
            try:
                check_in = CheckIn(
                    booking_id=booking.id,
                    aircraft_id=booking.aircraft_id,
                    instructor_id=booking.instructor_id if booking.instructor_id else None,
                    hobbs_start=form.hobbs_start.data,
                    tach_start=form.tach_start.data,
                    weather_conditions_acceptable=form.weather_conditions_acceptable.data,
                    notes=form.notes.data
                )
                booking.status = 'in_progress'
                db.session.add(check_in)
                db.session.commit()
                flash('Check-in completed successfully.', 'success')
                return redirect(url_for('booking.dashboard'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f'Error during check-in: {str(e)}')
                flash('Failed to complete check-in', 'error')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{field}: {error}', 'error')

    form = CheckInForm()
    return render_template('booking/check_in.html', booking=booking, form=form)


@booking_bp.route('/check-out/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def check_out(booking_id):
    """Handle check-out for a booking."""
    booking = Booking.query.get_or_404(booking_id)
    check_in = CheckIn.query.filter_by(booking_id=booking_id).first()
    if not check_in:
        return render_template('error.html', message='Must check in before checking out.'), 400

    # Prevent double check-out
    if CheckOut.query.filter_by(booking_id=booking.id).first():
        return render_template('error.html', message='Already checked out for this booking.'), 400

    # Verify user has permission
    if not (current_user.is_admin or current_user.id == booking.student_id):
        flash('You do not have permission to check out for this booking', 'error')
        return render_template('error.html', message='Permission denied'), 403

    if request.method == 'POST':
        form = CheckOutForm()
        if form.validate_on_submit():
            try:
                check_out = CheckOut(
                    booking_id=booking.id,
                    aircraft_id=booking.aircraft_id,
                    instructor_id=booking.instructor_id if booking.instructor_id else None,
                    hobbs_end=form.hobbs_end.data,
                    tach_end=form.tach_end.data,
                    notes=form.notes.data
                )
                booking.status = 'completed'
                db.session.add(check_out)
                db.session.commit()
                flash('Check-out completed successfully', 'success')
                return redirect(url_for('booking.dashboard'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f'Error during check-out: {str(e)}')
                flash('Failed to complete check-out', 'error')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{field}: {error}', 'error')

    form = CheckOutForm()
    return render_template('booking/check_out.html', booking=booking, form=form)


@booking_bp.route('/booking/<int:id>/invoice', methods=['GET', 'POST'])
@login_required
def generate_invoice(id):
    """Generate invoice for a booking."""
    booking = Booking.query.get_or_404(id)
    if not (current_user.is_admin or booking.student_id ==
            current_user.id or booking.instructor_id == current_user.id):
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
            status='pending')
        db.session.add(invoice)
        db.session.commit()
        flash('Invoice generated successfully.')
        return redirect(url_for('booking.view_booking', booking_id=id))

    # Pre-fill form with calculated values
    if not form.is_submitted():
        form.aircraft_time.data = booking.check_out.hobbs_end - booking.check_in.hobbs_start
        if booking.instructor_id and booking.check_out.instructor_end_time and booking.check_in.instructor_start_time:
            form.instructor_time.data = (
                booking.check_out.instructor_end_time - booking.check_in.instructor_start_time
            ).total_seconds() / 3600

    return render_template(
        'booking/invoice.html',
        form=form,
        booking=booking,
        check_out=booking.check_out)


@booking_bp.route('/booking/<int:booking_id>/cancel', methods=['POST'])
@login_required
def alt_cancel_booking(booking_id):
    """Alternative route for canceling a booking (to match test expectations)."""
    return cancel_booking(booking_id)


@booking_bp.route('/recurring-bookings')
@login_required
def recurring_bookings():
    """View recurring bookings."""
    bookings = RecurringBooking.query.filter_by(
        student_id=current_user.id).all()
    return render_template(
        'booking/recurring_bookings.html',
        bookings=bookings)


@booking_bp.route('/waitlist')
@login_required
def waitlist():
    """View waitlist entries."""
    entries = WaitlistEntry.query.filter_by(student_id=current_user.id).all()
    return render_template('booking/waitlist.html', entries=entries)


@booking_bp.route('/google-disconnect', methods=['POST'])
@login_required
def google_disconnect():
    """Disconnect Google Calendar integration."""
    try:
        current_user.google_calendar_credentials = None
        current_user.google_calendar_enabled = False
        db.session.commit()
        flash('Successfully disconnected from Google Calendar', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Google Calendar disconnect error: {str(e)}')
        flash('Failed to disconnect from Google Calendar. Please try again.', 'error')

    return redirect(url_for('booking.dashboard'))


@booking_bp.route('/aircraft/<int:aircraft_id>/info', methods=['GET'])
def aircraft_info(aircraft_id):
    from app.models import Aircraft
    aircraft = Aircraft.query.get_or_404(aircraft_id)
    return render_template('booking/aircraft_info.html', aircraft=aircraft)
