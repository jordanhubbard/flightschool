from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app.models import User, Aircraft, Booking, MaintenanceType, MaintenanceRecord, Squawk, Endorsement, Document, WeatherMinima, AuditLog, WaitlistEntry, RecurringBooking, FlightLog
from app import db
from datetime import datetime
from functools import wraps
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Email, Optional, Length
from app.forms import UserForm, AircraftForm, MaintenanceTypeForm, MaintenanceRecordForm, SquawkForm
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_app.logger.debug(f"Checking admin access for user: {current_user}")
        current_app.logger.debug(f"User authenticated: {current_user.is_authenticated}")
        current_app.logger.debug(f"User role: {current_user.role}")
        
        if not current_user.is_authenticated:
            current_app.logger.debug("User not authenticated")
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('auth.login'))
        
        if current_user.role != 'admin':
            current_app.logger.debug("User not admin")
            if request.is_json:
                return jsonify({'error': 'Admin access required'}), 403
            flash('Admin access required', 'error')
            return redirect(url_for('auth.login'))
        
        current_app.logger.debug("Admin access granted")
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard view."""
    # Get counts for dashboard
    instructor_count = User.query.filter_by(role='instructor', status='active').count()
    student_count = User.query.filter_by(role='student', status='active').count()
    aircraft_count = Aircraft.query.filter_by(status='available').count()
    
    # Get recent bookings
    recent_bookings = Booking.query.order_by(Booking.start_time.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         instructor_count=instructor_count,
                         student_count=student_count,
                         aircraft_count=aircraft_count,
                         recent_bookings=recent_bookings)

@admin_bp.route('/calendar/settings')
@login_required
@admin_required
def calendar_settings():
    return render_template('admin/calendar_settings.html')

@admin_bp.route('/calendar/oauth')
@login_required
@admin_required
def calendar_oauth():
    # Google OAuth configuration
    GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    CLIENT_ID = 'your-client-id'  # This should come from config
    REDIRECT_URI = url_for('admin.calendar_callback', _external=True)
    SCOPE = 'https://www.googleapis.com/auth/calendar'
    
    params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': SCOPE,
        'response_type': 'code',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    auth_url = f"{GOOGLE_AUTH_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
    return redirect(auth_url)

@admin_bp.route('/calendar/callback')
@login_required
@admin_required
def calendar_callback():
    # Handle the OAuth callback
    code = request.args.get('code')
    if not code:
        flash('Failed to authenticate with Google Calendar', 'error')
        return redirect(url_for('admin.calendar_settings'))
    
    # TODO: Exchange code for tokens
    flash('Successfully connected to Google Calendar', 'success')
    return redirect(url_for('admin.calendar_settings'))

@admin_bp.route('/schedule')
@login_required
@admin_required
def schedule():
    bookings = Booking.query.order_by(Booking.start_time).all()
    return render_template('admin/schedule.html', bookings=bookings)

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    return render_template('admin/reports.html')

@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    return render_template('admin/settings.html')

@admin_bp.route('/user/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    user_type = request.args.get('type', 'student')
    if user_type not in ['student', 'instructor']:
        flash('Invalid user type', 'error')
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('admin/user_create.html', user_type=user_type), 400

        status = request.form.get('status')
        if status not in ['active', 'inactive', 'pending']:
            flash('Invalid status value', 'error')
            return render_template('admin/user_create.html', user_type=user_type), 400

        try:
            user = User(
                email=email,
                first_name=request.form.get('first_name'),
                last_name=request.form.get('last_name'),
                phone=request.form.get('phone'),
                role=user_type,
                status=status
            )
            
            if user_type == 'instructor':
                user.certificates = request.form.get('certificates', '')
                rate = request.form.get('instructor_rate_per_hour')
                if rate:
                    try:
                        user.instructor_rate_per_hour = float(rate)
                    except ValueError:
                        flash('Invalid instructor rate', 'error')
                        return render_template('admin/user_create.html', user_type=user_type), 400

            db.session.add(user)
            db.session.commit()
            flash('User created successfully', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Failed to create user', 'error')
            return render_template('admin/user_create.html', user_type=user_type), 400

    return render_template('admin/user_create.html', user_type=user_type)

@admin_bp.route('/user/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    
    if request.method == 'POST':
        email = request.form.get('email')
        if email != user.email and User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('admin/user_edit.html', user=user), 400

        status = request.form.get('status')
        if status not in ['active', 'inactive', 'pending']:
            flash('Invalid status value', 'error')
            return render_template('admin/user_edit.html', user=user), 400

        try:
            user.email = email
            user.first_name = request.form.get('first_name')
            user.last_name = request.form.get('last_name')
            user.phone = request.form.get('phone')
            user.status = status
            
            if user.role == 'instructor':
                user.certificates = request.form.get('certificates', '')
                rate = request.form.get('instructor_rate_per_hour')
                if rate:
                    try:
                        user.instructor_rate_per_hour = float(rate)
                    except ValueError:
                        flash('Invalid instructor rate', 'error')
                        return render_template('admin/user_edit.html', user=user), 400

            db.session.commit()
            flash('User updated successfully', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Failed to update user', 'error')
            return render_template('admin/user_edit.html', user=user), 400

    return render_template('admin/user_edit.html', user=user)

@admin_bp.route('/user/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    try:
        db.session.delete(user)
        db.session.commit()
        if request.is_json:
            return jsonify({'message': 'User deleted successfully'}), 200
        flash('User deleted successfully', 'success')
        return redirect(url_for('admin.dashboard'))
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': 'Failed to delete user'}), 400
        flash('Failed to delete user', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/aircraft/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_aircraft():
    form = AircraftForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            aircraft = Aircraft(
                registration=form.registration.data,
                make=form.make.data,
                model=form.model.data,
                year=form.year.data,
                status=form.status.data,
                category=form.category.data,
                engine_type=form.engine_type.data,
                num_engines=form.num_engines.data,
                ifr_equipped=form.ifr_equipped.data,
                gps=form.gps.data,
                autopilot=form.autopilot.data,
                rate_per_hour=form.rate_per_hour.data,
                hobbs_time=form.hobbs_time.data,
                tach_time=form.tach_time.data,
                last_maintenance=form.last_maintenance.data,
                description=form.description.data
            )
            try:
                db.session.add(aircraft)
                db.session.commit()
                flash('Aircraft created successfully', 'success')
                return redirect(url_for('admin.dashboard'))
            except Exception as e:
                db.session.rollback()
                flash('Error adding aircraft', 'error')
        else:
            flash('Please correct the errors below', 'error')
    
    return render_template('admin/aircraft_form.html', 
                         form=form,
                         title='Create New Aircraft',
                         current_year=datetime.now().year)

@admin_bp.route('/aircraft/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_aircraft(id):
    aircraft = Aircraft.query.get_or_404(id)
    form = AircraftForm(obj=aircraft)
    if form.validate_on_submit():
        aircraft.registration = form.registration.data
        aircraft.make = form.make.data
        aircraft.model = form.model.data
        aircraft.year = form.year.data
        aircraft.status = form.status.data
        aircraft.category = form.category.data
        aircraft.engine_type = form.engine_type.data
        aircraft.num_engines = form.num_engines.data
        aircraft.ifr_equipped = form.ifr_equipped.data
        aircraft.gps = form.gps.data
        aircraft.autopilot = form.autopilot.data
        aircraft.rate_per_hour = form.rate_per_hour.data
        aircraft.hobbs_time = form.hobbs_time.data
        aircraft.tach_time = form.tach_time.data
        aircraft.last_maintenance = form.last_maintenance.data
        aircraft.description = form.description.data
        db.session.commit()
        flash('Aircraft updated successfully', 'success')
        return redirect(url_for('admin.aircraft_list'))
    return render_template('admin/aircraft_form.html', form=form, title='Edit Aircraft')

@admin_bp.route('/aircraft/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_aircraft(id):
    aircraft = Aircraft.query.get_or_404(id)
    db.session.delete(aircraft)
    db.session.commit()
    return jsonify({'message': 'Aircraft deleted successfully'}), 200

@admin_bp.route('/user/<int:id>/status', methods=['PUT'])
@login_required
@admin_required
def update_user_status(id):
    user = User.query.get_or_404(id)
    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({'error': 'Status is required'}), 400
        
    status = data['status']
    if status not in ['active', 'inactive']:
        return jsonify({'error': 'Invalid status value'}), 400
        
    try:
        user.status = status
        db.session.commit()
        flash('User status updated successfully', 'success')
        return jsonify({'message': 'Status updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/maintenance/types', methods=['GET', 'POST'])
@login_required
@admin_required
def maintenance_types():
    form = MaintenanceTypeForm()
    if form.validate_on_submit():
        maintenance_type = MaintenanceType(
            name=form.name.data,
            description=form.description.data,
            interval_days=form.interval_days.data,
            interval_hours=form.interval_hours.data
        )
        db.session.add(maintenance_type)
        db.session.commit()
        flash('Maintenance type added successfully', 'success')
        return redirect(url_for('admin.maintenance_types'))
    
    maintenance_types = MaintenanceType.query.all()
    return render_template('admin/maintenance_types.html', 
                         form=form, 
                         maintenance_types=maintenance_types)

@admin_bp.route('/maintenance/records', methods=['GET', 'POST'])
@login_required
@admin_required
def maintenance_records():
    form = MaintenanceRecordForm()
    form.maintenance_type.choices = [(mt.id, mt.name) for mt in MaintenanceType.query.all()]
    form.performed_by.choices = [(u.id, f"{u.first_name} {u.last_name}") for u in User.query.filter_by(role='mechanic').all()]
    
    if form.validate_on_submit():
        record = MaintenanceRecord(
            maintenance_type_id=form.maintenance_type.data,
            performed_at=form.performed_at.data,
            performed_by_id=form.performed_by.data,
            hobbs_hours=form.hobbs_hours.data,
            tach_hours=form.tach_hours.data,
            notes=form.notes.data
        )
        db.session.add(record)
        db.session.commit()
        flash('Maintenance record added successfully', 'success')
        return redirect(url_for('admin.maintenance_records'))
    
    records = MaintenanceRecord.query.order_by(MaintenanceRecord.performed_at.desc()).all()
    return render_template('admin/maintenance_records.html', 
                         form=form, 
                         records=records)

@admin_bp.route('/squawks', methods=['GET', 'POST'])
@login_required
@admin_required
def squawks():
    form = SquawkForm()
    if form.validate_on_submit():
        squawk = Squawk(
            description=form.description.data,
            status=form.status.data,
            resolution_notes=form.resolution_notes.data
        )
        db.session.add(squawk)
        db.session.commit()
        flash('Squawk added successfully', 'success')
        return redirect(url_for('admin.squawks'))
    
    squawks = Squawk.query.order_by(Squawk.created_at.desc()).all()
    return render_template('admin/squawks.html', 
                         form=form, 
                         squawks=squawks)

@admin_bp.route('/booking/<int:booking_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    if request.method == 'POST':
        try:
            start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M')
            status = request.form.get('status')
            
            booking.start_time = start_time
            booking.end_time = end_time
            booking.status = status
            
            db.session.commit()
            flash('Booking updated successfully.', 'success')
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            flash('Error updating booking. Please check the form data.', 'error')
            return redirect(url_for('admin.dashboard'))
    
    return render_template('admin/edit_booking.html', booking=booking)

@admin_bp.route('/aircraft')
@login_required
@admin_required
def aircraft_list():
    """List all aircraft."""
    aircraft = Aircraft.query.all()
    return render_template('admin/aircraft_list.html', aircraft=aircraft)

@admin_bp.route('/aircraft/add', methods=['GET', 'POST'])
@login_required
@admin_required
def aircraft_add():
    form = AircraftForm()
    if form.validate_on_submit():
        aircraft = Aircraft(
            registration=form.registration.data,
            make=form.make.data,
            model=form.model.data,
            year=form.year.data,
            category=form.category.data,
            rate_per_hour=form.rate_per_hour.data,
            status=form.status.data
        )
        db.session.add(aircraft)
        db.session.commit()
        flash('Aircraft added successfully', 'success')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/aircraft_form.html', form=form, title='Add Aircraft')

@admin_bp.route('/instructors')
@login_required
@admin_required
def instructor_list():
    """List all instructors."""
    instructors = User.query.filter_by(role='instructor').all()
    return render_template('admin/instructor_list.html', instructors=instructors)

@admin_bp.route('/users')
@login_required
@admin_required
def user_list():
    """List all users."""
    users = User.query.all()
    return render_template('admin/user_form.html', users=users)

@admin_bp.route('/instructor/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_instructor():
    return redirect(url_for('admin.create_user', type='instructor'))

@admin_bp.route('/instructor/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_instructor(id):
    return redirect(url_for('admin.edit_user', id=id))

@admin_bp.route('/aircraft/<int:id>/status', methods=['PUT'])
@login_required
@admin_required
def update_aircraft_status(id):
    """Update aircraft status."""
    aircraft = Aircraft.query.get_or_404(id)
    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({'error': 'Status is required'}), 400
        
    if data['status'] not in ['available', 'maintenance', 'unavailable', 'retired']:
        return jsonify({'error': 'Invalid status'}), 400
    
    aircraft.status = data['status']
    db.session.commit()
    
    return jsonify({'message': 'Status updated successfully'}), 200 

@admin_bp.route('/endorsements', methods=['GET'])
@login_required
@admin_required
def endorsements():
    """List all endorsements."""
    endorsements = Endorsement.query.all()
    return render_template('admin/endorsements.html', endorsements=endorsements)

@admin_bp.route('/endorsements/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@admin_required
def manage_endorsement(id):
    """Manage a specific endorsement."""
    endorsement = Endorsement.query.get_or_404(id)
    
    if request.method == 'GET':
        return render_template('admin/endorsement_form.html', endorsement=endorsement)
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        # Update endorsement
        endorsement.type = data.get('type', endorsement.type)
        endorsement.description = data.get('description', endorsement.description)
        endorsement.expiration = datetime.fromisoformat(data['expiration']) if data.get('expiration') else None
        endorsement.document_url = data.get('document_url', endorsement.document_url)
        
        try:
            db.session.commit()
            return jsonify({'message': 'Endorsement updated successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            db.session.delete(endorsement)
            db.session.commit()
            return jsonify({'message': 'Endorsement deleted successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

@admin_bp.route('/documents', methods=['GET'])
@login_required
@admin_required
def documents():
    """List all documents."""
    documents = Document.query.all()
    return render_template('admin/documents.html', documents=documents)

@admin_bp.route('/documents/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@admin_required
def manage_document(id):
    """Manage a specific document."""
    document = Document.query.get_or_404(id)
    
    if request.method == 'GET':
        return render_template('admin/document_form.html', document=document)
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        # Update document
        document.type = data.get('type', document.type)
        document.filename = data.get('filename', document.filename)
        document.url = data.get('url', document.url)
        document.expiration = datetime.fromisoformat(data['expiration']) if data.get('expiration') else None
        
        try:
            db.session.commit()
            return jsonify({'message': 'Document updated successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            db.session.delete(document)
            db.session.commit()
            return jsonify({'message': 'Document deleted successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

@admin_bp.route('/weather-minima', methods=['GET', 'POST'])
@login_required
@admin_required
def weather_minima():
    """Manage weather minima."""
    if request.method == 'GET':
        minima = WeatherMinima.query.all()
        return render_template('admin/weather_minima.html', minima=minima)
    
    elif request.method == 'POST':
        data = request.get_json()
        
        # Create new weather minima
        minima = WeatherMinima(
            category=data['category'],
            ceiling_min=data['ceiling_min'],
            visibility_min=data['visibility_min'],
            wind_max=data['wind_max'],
            crosswind_max=data['crosswind_max']
        )
        
        try:
            db.session.add(minima)
            db.session.commit()
            return jsonify({'message': 'Weather minima created successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

@admin_bp.route('/weather-minima/<int:id>', methods=['PUT', 'DELETE'])
@login_required
@admin_required
def manage_weather_minima(id):
    """Manage a specific weather minima."""
    minima = WeatherMinima.query.get_or_404(id)
    
    if request.method == 'PUT':
        data = request.get_json()
        
        # Update weather minima
        minima.category = data.get('category', minima.category)
        minima.ceiling_min = data.get('ceiling_min', minima.ceiling_min)
        minima.visibility_min = data.get('visibility_min', minima.visibility_min)
        minima.wind_max = data.get('wind_max', minima.wind_max)
        minima.crosswind_max = data.get('crosswind_max', minima.crosswind_max)
        
        try:
            db.session.commit()
            return jsonify({'message': 'Weather minima updated successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            db.session.delete(minima)
            db.session.commit()
            return jsonify({'message': 'Weather minima deleted successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

@admin_bp.route('/audit-logs', methods=['GET'])
@login_required
@admin_required
def audit_logs():
    """View audit logs."""
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).all()
    return render_template('admin/audit_logs.html', logs=logs)

@admin_bp.route('/waitlist', methods=['GET'])
@login_required
@admin_required
def waitlist():
    """View and manage waitlist entries."""
    entries = WaitlistEntry.query.filter_by(status='active').all()
    return render_template('admin/waitlist.html', entries=entries)

@admin_bp.route('/waitlist/<int:id>', methods=['PUT'])
@login_required
@admin_required
def update_waitlist_entry(id):
    """Update a waitlist entry."""
    entry = WaitlistEntry.query.get_or_404(id)
    data = request.get_json()
    
    entry.status = data.get('status', entry.status)
    
    try:
        db.session.commit()
        return jsonify({'message': 'Waitlist entry updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/recurring-bookings', methods=['GET'])
@login_required
@admin_required
def recurring_bookings():
    """View and manage recurring bookings."""
    bookings = RecurringBooking.query.all()
    return render_template('admin/recurring_bookings.html', bookings=bookings)

@admin_bp.route('/recurring-bookings/<int:id>', methods=['PUT', 'DELETE'])
@login_required
@admin_required
def manage_recurring_booking(id):
    """Manage a recurring booking."""
    booking = RecurringBooking.query.get_or_404(id)
    
    if request.method == 'PUT':
        data = request.get_json()
        
        # Update recurring booking
        booking.instructor_id = data.get('instructor_id', booking.instructor_id)
        booking.aircraft_id = data.get('aircraft_id', booking.aircraft_id)
        booking.day_of_week = data.get('day_of_week', booking.day_of_week)
        if 'start_time' in data:
            booking.start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        booking.duration_hours = data.get('duration_hours', booking.duration_hours)
        if 'end_date' in data:
            booking.end_date = datetime.fromisoformat(data['end_date'])
        booking.status = data.get('status', booking.status)
        
        try:
            db.session.commit()
            return jsonify({'message': 'Recurring booking updated successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            db.session.delete(booking)
            db.session.commit()
            return jsonify({'message': 'Recurring booking deleted successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

@admin_bp.route('/flight-logs', methods=['GET'])
@login_required
@admin_required
def flight_logs():
    """View flight logs."""
    logs = FlightLog.query.order_by(FlightLog.flight_date.desc()).all()
    return render_template('admin/flight_logs.html', logs=logs)

@admin_bp.route('/flight-logs/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@admin_required
def manage_flight_log(id):
    """Manage a flight log."""
    log = FlightLog.query.get_or_404(id)
    
    if request.method == 'GET':
        return render_template('admin/flight_log_form.html', log=log)
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        # Update flight log
        log.route = data.get('route', log.route)
        log.remarks = data.get('remarks', log.remarks)
        log.weather_conditions = data.get('weather_conditions', log.weather_conditions)
        log.ground_instruction = data.get('ground_instruction', log.ground_instruction)
        log.dual_received = data.get('dual_received', log.dual_received)
        log.pic_time = data.get('pic_time', log.pic_time)
        log.sic_time = data.get('sic_time', log.sic_time)
        log.cross_country = data.get('cross_country', log.cross_country)
        log.night = data.get('night', log.night)
        log.actual_instrument = data.get('actual_instrument', log.actual_instrument)
        log.simulated_instrument = data.get('simulated_instrument', log.simulated_instrument)
        log.landings_day = data.get('landings_day', log.landings_day)
        log.landings_night = data.get('landings_night', log.landings_night)
        
        try:
            db.session.commit()
            return jsonify({'message': 'Flight log updated successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            db.session.delete(log)
            db.session.commit()
            return jsonify({'message': 'Flight log deleted successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500