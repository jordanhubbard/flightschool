from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session, current_app, abort
from flask_login import login_required, current_user
from app.models import User, Aircraft, Booking, CheckIn, CheckOut, Invoice, AuditLog, FlightLog, RecurringBooking, WaitlistEntry, WeatherMinima
from app import db
from app.forms import (
    BookingForm, GoogleCalendarSettingsForm, FlightCheckoutForm, FlightCheckinForm,
    CheckInForm, CheckOutForm, InvoiceForm
)
from datetime import datetime, timedelta, timezone, UTC
from app.calendar_service import GoogleCalendarService
import os

booking_bp = Blueprint('booking', __name__)
calendar_service = GoogleCalendarService()

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

@booking_bp.route('/dashboard')
@login_required
def dashboard():
    """Display the booking dashboard."""
    # Get upcoming bookings
    upcoming_bookings = Booking.query.filter(
        Booking.student_id == current_user.id,
        Booking.start_time > datetime.now(UTC)
    ).order_by(Booking.start_time).all()
    
    # Get available aircraft
    available_aircraft = Aircraft.query.filter_by(status='active').all()
    
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
    if not current_user.is_instructor:
        flash('Access denied. Instructor privileges required.', 'error')
        return redirect(url_for('booking.dashboard'))
    
    instructor_bookings = Booking.query.filter_by(instructor_id=current_user.id).order_by(Booking.start_time).all()
    return render_template('booking/instructor_dashboard.html', bookings=instructor_bookings)

@booking_bp.route('/bookings', methods=['GET', 'POST'])
@login_required
def create_booking():
    if request.method == 'GET':
        form = BookingForm()
        # Set choices for aircraft and instructor select fields
        form.aircraft_id.choices = [(a.id, f"{a.registration} - {a.make} {a.model}")
                                  for a in Aircraft.query.filter_by(status='available').all()]
        form.instructor_id.choices = [(i.id, f"{i.first_name} {i.last_name}")
                                    for i in User.query.filter_by(role='instructor', status='active').all()]
        form.instructor_id.choices.insert(0, (0, 'No Instructor'))
        return render_template('booking/create.html', form=form)
    
    # Handle POST request
    if request.is_json:
        data = request.get_json()
        form = BookingForm(data=data)
    else:
        form = BookingForm()
    
    # Set choices for validation
    form.aircraft_id.choices = [(a.id, f"{a.registration} - {a.make} {a.model}")
                              for a in Aircraft.query.filter_by(status='available').all()]
    form.instructor_id.choices = [(i.id, f"{i.first_name} {i.last_name}")
                                for i in User.query.filter_by(role='instructor', status='active').all()]
    form.instructor_id.choices.insert(0, (0, 'No Instructor'))

    if form.validate_on_submit():
        start_time = form.start_time.data
        end_time = form.end_time.data
        
        # Check for booking conflicts
        conflicts = Booking.query.filter(
            Booking.aircraft_id == form.aircraft_id.data,
            Booking.status != 'cancelled',
            ((Booking.start_time <= start_time) & (Booking.end_time > start_time)) |
            ((Booking.start_time < end_time) & (Booking.end_time >= end_time))
        ).first()
        
        if conflicts:
            if request.is_json:
                return jsonify({
                    'status': 'error',
                    'message': 'This time slot conflicts with another booking'
                }), 409
            flash('This time slot conflicts with another booking', 'error')
            return render_template('booking/create.html', form=form)
        
        # Create the booking
        booking = Booking(
            student_id=current_user.id,
            aircraft_id=form.aircraft_id.data,
            instructor_id=form.instructor_id.data if form.instructor_id.data != 0 else None,
            start_time=start_time,
            end_time=end_time,
            notes=form.notes.data,
            status='pending'
        )
        
        try:
            db.session.add(booking)
            db.session.commit()
            
            if request.is_json:
                return jsonify({
                    'status': 'success',
                    'message': 'Booking created successfully',
                    'booking_id': booking.id
                }), 201
            else:
                flash('Booking created successfully', 'success')
                return redirect(url_for('booking.view_booking', booking_id=booking.id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error creating booking: {str(e)}')
            if request.is_json:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to create booking'
                }), 500
            flash('Failed to create booking', 'error')
            return render_template('booking/create.html', form=form)
    
    if request.is_json:
        return jsonify({
            'status': 'error',
            'errors': form.errors
        }), 400
    else:
        return render_template('booking/create.html', form=form)

@booking_bp.route('/bookings/<int:booking_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def view_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Check if user has permission to view this booking
    if not (current_user.is_admin or 
            current_user.id == booking.student_id or 
            current_user.id == booking.instructor_id):
        if request.is_json:
            return jsonify({
                'status': 'error',
                'message': 'You do not have permission to view this booking'
            }), 403
        else:
            flash('You do not have permission to view this booking', 'error')
            return redirect(url_for('main.index'))
    
    if request.method == 'GET':
        if request.is_json:
            return jsonify({
                'status': 'success',
                'booking': {
                    'id': booking.id,
                    'student': booking.student.full_name,
                    'aircraft': booking.aircraft.registration,
                    'instructor': booking.instructor.full_name if booking.instructor else None,
                    'start_time': booking.start_time.isoformat(),
                    'end_time': booking.end_time.isoformat(),
                    'status': booking.status,
                    'notes': booking.notes
                }
            })
        else:
            return render_template('booking/view.html', booking=booking)
    
    elif request.method == 'PUT':
        if not (current_user.is_admin or current_user.id == booking.student_id):
            return jsonify({
                'status': 'error',
                'message': 'You do not have permission to modify this booking'
            }), 403
        
        data = request.get_json()
        form = BookingForm(data=data)
        
        if form.validate():
            booking.start_time = form.start_time.data
            booking.end_time = form.end_time.data
            booking.notes = form.notes.data
            booking.instructor_id = form.instructor_id.data if form.instructor_id.data != 0 else None
            
            db.session.commit()
            return jsonify({
                'status': 'success',
                'message': 'Booking updated successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'errors': form.errors
            }), 400
    
    elif request.method == 'DELETE':
        if not (current_user.is_admin or current_user.id == booking.student_id):
            return jsonify({
                'status': 'error',
                'message': 'You do not have permission to delete this booking'
            }), 403
        
        db.session.delete(booking)
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Booking deleted successfully'
        })

@booking_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    """Cancel a booking with a reason."""
    booking = Booking.query.get_or_404(booking_id)
    
    # Check if user has permission to cancel this booking
    if not (current_user.is_admin or 
            current_user.id == booking.student_id or 
            current_user.id == booking.instructor_id):
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.get_json()
    reason = data.get('reason')
    notes = data.get('notes')
    
    if not reason or reason not in ['weather', 'mechanical', 'personal', 'other']:
        return jsonify({'error': 'Invalid cancellation reason'}), 400
    
    booking.status = 'cancelled'
    booking.cancellation_reason = reason
    booking.cancellation_notes = notes
    
    # Create audit log
    log = AuditLog(
        user=current_user,
        action='cancel',
        table_name='booking',
        record_id=booking.id,
        changes={
            'status': ['confirmed', 'cancelled'],
            'cancellation_reason': [None, reason],
            'cancellation_notes': [None, notes]
        }
    )
    db.session.add(log)
    
    try:
        db.session.commit()
        # TODO: Send notifications to affected users
        return jsonify({'message': 'Booking cancelled successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/bookings/<int:booking_id>/checkin', methods=['POST'])
@login_required
def check_in(booking_id):
    """Handle check-in for a booking."""
    booking = Booking.query.get_or_404(booking_id)
    
    # Check if user has permission
    if not (current_user.is_admin or current_user.id == booking.instructor_id):
        return jsonify({'error': 'Permission denied'}), 403
    
    data = request.get_json()
    
    # Validate hobbs and tach times
    try:
        hobbs_start = float(data['hobbs_start'])
        tach_start = float(data['tach_start'])
    except (KeyError, ValueError):
        return jsonify({'error': 'Invalid hobbs or tach times'}), 400
    
    # Create check-in record
    check_in = CheckIn(
        booking=booking,
        aircraft=booking.aircraft,
        instructor=current_user if current_user.is_instructor else None,
        hobbs_start=hobbs_start,
        tach_start=tach_start,
        instructor_start_time=datetime.now(UTC) if current_user.is_instructor else None,
        notes=data.get('notes')
    )
    
    # Update aircraft times
    booking.aircraft.hobbs_time = hobbs_start
    booking.aircraft.tach_time = tach_start
    
    # Update booking status
    booking.status = 'in_progress'
    
    try:
        db.session.add(check_in)
        db.session.commit()
        return jsonify({
            'message': 'Check-in recorded successfully',
            'check_in_id': check_in.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/bookings/<int:booking_id>/checkout', methods=['POST'])
@login_required
def check_out(booking_id):
    """Handle check-out for a booking."""
    booking = Booking.query.get_or_404(booking_id)
    
    # Check if user has permission
    if not (current_user.is_admin or current_user.id == booking.instructor_id):
        return jsonify({'error': 'Permission denied'}), 403
    
    if not booking.check_in:
        return jsonify({'error': 'No check-in record found'}), 400
    
    data = request.get_json()
    
    # Validate hobbs and tach times
    try:
        hobbs_end = float(data['hobbs_end'])
        tach_end = float(data['tach_end'])
        if hobbs_end < booking.check_in.hobbs_start or tach_end < booking.check_in.tach_start:
            return jsonify({'error': 'End times cannot be less than start times'}), 400
    except (KeyError, ValueError):
        return jsonify({'error': 'Invalid hobbs or tach times'}), 400
    
    # Calculate total times
    total_aircraft_time = hobbs_end - booking.check_in.hobbs_start
    total_instructor_time = None
    instructor_end_time = None
    
    if current_user.is_instructor and booking.check_in.instructor_start_time:
        instructor_end_time = datetime.now(UTC)
        total_instructor_time = (instructor_end_time - booking.check_in.instructor_start_time).total_seconds() / 3600
    
    # Create check-out record
    check_out = CheckOut(
        booking=booking,
        aircraft=booking.aircraft,
        instructor=current_user if current_user.is_instructor else None,
        hobbs_end=hobbs_end,
        tach_end=tach_end,
        instructor_end_time=instructor_end_time,
        total_aircraft_time=total_aircraft_time,
        total_instructor_time=total_instructor_time,
        notes=data.get('notes')
    )
    
    # Update aircraft times
    booking.aircraft.hobbs_time = hobbs_end
    booking.aircraft.tach_time = tach_end
    
    # Update booking status
    booking.status = 'completed'
    
    # Create flight log if provided
    if data.get('flight_log'):
        log_data = data['flight_log']
        flight_log = FlightLog(
            booking=booking,
            pic=current_user if current_user.is_instructor else booking.student,
            sic=booking.student if current_user.is_instructor else None,
            flight_date=datetime.now(UTC),
            route=log_data.get('route'),
            remarks=log_data.get('remarks'),
            weather_conditions=log_data.get('weather_conditions'),
            ground_instruction=log_data.get('ground_instruction', 0.0),
            dual_received=total_aircraft_time if not current_user.is_instructor else 0.0,
            pic_time=total_aircraft_time if current_user.is_instructor else 0.0,
            sic_time=total_aircraft_time if not current_user.is_instructor else 0.0,
            cross_country=log_data.get('cross_country', 0.0),
            night=log_data.get('night', 0.0),
            actual_instrument=log_data.get('actual_instrument', 0.0),
            simulated_instrument=log_data.get('simulated_instrument', 0.0),
            landings_day=log_data.get('landings_day', 0),
            landings_night=log_data.get('landings_night', 0)
        )
        db.session.add(flight_log)
    
    try:
        db.session.add(check_out)
        db.session.commit()
        return jsonify({
            'message': 'Check-out recorded successfully',
            'check_out_id': check_out.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/bookings/recurring', methods=['POST'])
@login_required
def create_recurring_booking():
    """Create a recurring booking."""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['aircraft_id', 'day_of_week', 'start_time', 'duration_hours', 'start_date']
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
        duration_hours=float(data['duration_hours']),
        start_date=datetime.fromisoformat(data['start_date']),
        end_date=datetime.fromisoformat(data['end_date']) if data.get('end_date') else None,
        status='active'
    )
    
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
    if current_user.is_admin:
        bookings = Booking.query.order_by(Booking.start_time.desc()).all()
    else:
        bookings = Booking.query.filter_by(student_id=current_user.id).order_by(Booking.start_time.desc()).all()
    return render_template('booking/list.html', bookings=bookings)

@booking_bp.route('/settings/calendar')
@login_required
def calendar_settings():
    form = GoogleCalendarSettingsForm()
    return render_template('booking/calendar_settings.html', form=form)

@booking_bp.route('/settings/calendar/authorize')
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

@booking_bp.route('/settings/calendar/callback')
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

@booking_bp.route('/settings/calendar/disconnect')
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

@booking_bp.route('/booking/<int:id>/checkout', methods=['GET', 'POST'])
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

@booking_bp.route('/check-in/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def check_in(booking_id):
    """Handle check-in for a booking."""
    booking = Booking.query.get_or_404(booking_id)
    
    # Verify user has permission
    if not (current_user.is_admin or current_user.id == booking.student_id):
        flash('You do not have permission to check in for this booking', 'error')
        return redirect(url_for('booking.dashboard'))
    
    if request.method == 'POST':
        form = CheckInForm()
        if form.validate_on_submit():
            try:
                check_in = CheckIn(
                    booking_id=booking_id,
                    hobbs_start=form.hobbs_start.data,
                    tach_start=form.tach_start.data,
                    instructor_start_time=form.instructor_start_time.data,
                    notes=form.notes.data
                )
                booking.status = 'in_progress'
                db.session.add(check_in)
                db.session.commit()
                flash('Check-in completed successfully', 'success')
                return redirect(url_for('booking.view_booking', booking_id=booking_id))
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
    check_in = CheckIn.query.filter_by(booking_id=booking_id).first_or_404()
    
    # Verify user has permission
    if not (current_user.is_admin or current_user.id == booking.student_id):
        flash('You do not have permission to check out for this booking', 'error')
        return redirect(url_for('booking.dashboard'))
    
    if request.method == 'POST':
        form = CheckOutForm()
        if form.validate_on_submit():
            try:
                check_out = CheckOut(
                    booking_id=booking_id,
                    hobbs_end=form.hobbs_end.data,
                    tach_end=form.tach_end.data,
                    instructor_end_time=form.instructor_end_time.data,
                    notes=form.notes.data
                )
                booking.status = 'completed'
                db.session.add(check_out)
                db.session.commit()
                flash('Check-out completed successfully', 'success')
                return redirect(url_for('booking.view_booking', booking_id=booking_id))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f'Error during check-out: {str(e)}')
                flash('Failed to complete check-out', 'error')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{field}: {error}', 'error')
    
    form = CheckOutForm()
    return render_template('booking/check_out.html', booking=booking, check_in=check_in, form=form)

@booking_bp.route('/booking/<int:id>/invoice', methods=['GET', 'POST'])
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

    return render_template('booking/invoice.html', form=form, booking=booking, check_out=booking.check_out)

@booking_bp.route('/booking/<int:booking_id>/cancel', methods=['POST'])
@login_required
def alt_cancel_booking(booking_id):
    """Alternative route for canceling a booking (to match test expectations)."""
    return cancel_booking(booking_id)
