from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import User, Aircraft, Booking, MaintenanceType, MaintenanceRecord, Squawk
from app import db
from datetime import datetime
from functools import wraps
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Email, Optional, Length
from app.forms import UserForm, AircraftForm, MaintenanceTypeForm, MaintenanceRecordForm, SquawkForm
from werkzeug.security import generate_password_hash

bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            if request.is_json:
                return jsonify({'error': 'Admin access required'}), 403
            return render_template('errors/403.html'), 403
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    instructors = User.query.filter_by(role='instructor').all()
    students = User.query.filter_by(role='student').all()
    aircraft_list = Aircraft.query.all()
    maintenance_records = MaintenanceRecord.query.order_by(MaintenanceRecord.performed_at.desc()).limit(5).all()
    open_squawks = Squawk.query.filter_by(status='open').all()
    return render_template('admin/dashboard.html', 
                         instructors=instructors, 
                         students=students, 
                         aircraft_list=aircraft_list,
                         maintenance_records=maintenance_records,
                         open_squawks=open_squawks)

@bp.route('/calendar/settings')
@login_required
@admin_required
def calendar_settings():
    return render_template('admin/calendar_settings.html')

@bp.route('/calendar/oauth')
@login_required
@admin_required
def calendar_oauth():
    return redirect(url_for('booking.authorize_google_calendar'))

@bp.route('/schedule')
@login_required
@admin_required
def schedule():
    bookings = Booking.query.order_by(Booking.start_time).all()
    return render_template('admin/schedule.html', bookings=bookings)

@bp.route('/reports')
@login_required
@admin_required
def reports():
    return render_template('admin/reports.html')

@bp.route('/settings')
@login_required
@admin_required
def settings():
    return render_template('admin/settings.html')

@bp.route('/user/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    user_type = request.args.get('type', 'student')
    form = UserForm()
    
    if form.validate_on_submit():
        user = User(
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            role=user_type,
            status=form.status.data
        )
        if user_type == 'instructor':
            user.certificates = form.certificates.data
        elif user_type == 'student':
            user.student_id = form.student_id.data
        user.set_password('changeme')
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('User created successfully', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Error creating user: Email already registered', 'error')
            return render_template('admin/user_form.html', form=form, user_type=user_type)
    
    return render_template('admin/user_form.html', form=form, user_type=user_type)

@bp.route('/user/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    
    if form.validate_on_submit():
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.phone = form.phone.data
        user.status = form.status.data
        if user.role == 'instructor':
            user.certificates = form.certificates.data
        elif user.role == 'student':
            user.student_id = form.student_id.data
        
        try:
            db.session.commit()
            flash('User updated successfully', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating user: Invalid email address', 'error')
            return render_template('admin/user_form.html', form=form, user=user)
    
    return render_template('admin/user_form.html', form=form, user=user)

@bp.route('/user/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted successfully'}), 200

@bp.route('/aircraft/create', methods=['GET', 'POST'])
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
                status=form.status.data
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

@bp.route('/aircraft/<int:id>/edit', methods=['GET', 'POST'])
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
        db.session.commit()
        flash('Aircraft updated successfully', 'success')
        return redirect(url_for('admin.aircraft_list'))
    return render_template('admin/aircraft_form.html', form=form, title='Edit Aircraft')

@bp.route('/aircraft/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_aircraft(id):
    aircraft = Aircraft.query.get_or_404(id)
    db.session.delete(aircraft)
    db.session.commit()
    return jsonify({'message': 'Aircraft deleted successfully'}), 200

@bp.route('/user/<int:id>/status', methods=['PUT'])
@login_required
@admin_required
def update_user_status(id):
    user = User.query.get_or_404(id)
    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({'error': 'Status is required'}), 400
    
    user.status = data['status']
    db.session.commit()
    return jsonify({'message': 'Status updated successfully'}), 200

@bp.route('/maintenance/types', methods=['GET', 'POST'])
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

@bp.route('/maintenance/records', methods=['GET', 'POST'])
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

@bp.route('/squawks', methods=['GET', 'POST'])
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

@bp.route('/booking/<int:booking_id>/edit', methods=['GET', 'POST'])
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

@bp.route('/aircraft')
@login_required
@admin_required
def aircraft_list():
    """List all aircraft."""
    aircraft = Aircraft.query.all()
    return render_template('admin/aircraft_list.html', aircraft=aircraft)

@bp.route('/aircraft/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_aircraft():
    form = AircraftForm()
    if form.validate_on_submit():
        aircraft = Aircraft(
            registration=form.registration.data,
            make_model=form.make_model.data,
            year=form.year.data,
            status=form.status.data
        )
        db.session.add(aircraft)
        db.session.commit()
        flash('Aircraft added successfully', 'success')
        return redirect(url_for('admin.aircraft_list'))
    return render_template('admin/aircraft_form.html', form=form, title='Add Aircraft')

@bp.route('/instructors')
@login_required
@admin_required
def instructor_list():
    """List all instructors."""
    instructors = User.query.filter_by(is_instructor=True).all()
    return render_template('admin/instructor_list.html', instructors=instructors)

@bp.route('/users')
@login_required
@admin_required
def user_list():
    """List all users."""
    users = User.query.all()
    return render_template('admin/user_list.html', users=users)

@bp.route('/instructor/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_instructor():
    """Create a new instructor."""
    form = UserForm()
    
    if form.validate_on_submit():
        # Check if email already exists
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered', 'error')
            return render_template('admin/instructor_form.html', form=form)
        
        instructor = User(
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            role='instructor',
            is_instructor=True,
            certificates=form.certificates.data,
            status=form.status.data
        )
        instructor.set_password('changeme')  # Default password
        
        db.session.add(instructor)
        db.session.commit()
        
        flash('Instructor created successfully', 'success')
        return redirect(url_for('admin.instructor_list'))
    
    return render_template('admin/instructor_form.html', form=form)

@bp.route('/aircraft/<int:id>/status', methods=['PUT'])
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