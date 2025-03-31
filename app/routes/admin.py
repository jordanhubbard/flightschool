from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import User, Aircraft, Booking
from app import db
from datetime import datetime
from functools import wraps
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Email, Optional, Length
from app.forms import UserForm, AircraftForm
from werkzeug.security import generate_password_hash

bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            if request.is_json:
                return jsonify({'error': 'Admin access required'}), 403
            flash('Admin access required', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    instructors = User.query.filter_by(role='instructor').all()
    students = User.query.filter_by(role='student').all()
    aircraft_list = Aircraft.query.all()
    return render_template('admin/dashboard.html', 
                         instructors=instructors, 
                         students=students, 
                         aircraft_list=aircraft_list)

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
    
    if request.method == 'POST':
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
                flash('Error creating user', 'error')
        else:
            flash('Please correct the errors below', 'error')
    
    return render_template('admin/user_form.html', 
                         form=form,
                         user=None, 
                         user_type=user_type,
                         title=f'Create New {user_type.title()}')

@bp.route('/user/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    
    if request.method == 'POST':
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
                flash('Error updating user', 'error')
        else:
            flash('Please correct the errors below', 'error')
    
    return render_template('admin/user_form.html', 
                         form=form,
                         user=user,
                         user_type=user.role,
                         title=f'Edit {user.role.title()}')

@bp.route('/user/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete user"}), 500

@bp.route('/aircraft/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_aircraft():
    form = AircraftForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            aircraft = Aircraft(
                registration=form.registration.data,
                make_model=form.make_model.data,
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
    
    if request.method == 'POST':
        if form.validate_on_submit():
            aircraft.registration = form.registration.data
            aircraft.make_model = form.make_model.data
            aircraft.year = form.year.data
            aircraft.status = form.status.data
            
            try:
                db.session.commit()
                flash('Aircraft updated successfully', 'success')
                return redirect(url_for('admin.dashboard'))
            except Exception as e:
                db.session.rollback()
                flash('Error updating aircraft', 'error')
        else:
            flash('Please correct the errors below', 'error')
    
    return render_template('admin/aircraft_form.html', 
                         form=form,
                         title='Edit Aircraft',
                         aircraft=aircraft,
                         current_year=datetime.now().year)

@bp.route('/aircraft/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_aircraft(id):
    aircraft = Aircraft.query.get_or_404(id)
    try:
        db.session.delete(aircraft)
        db.session.commit()
        return jsonify({"message": "Aircraft deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete aircraft"}), 500

@bp.route('/user/<int:id>/status', methods=['PUT'])
@login_required
@admin_required
def update_user_status(id):
    user = User.query.get_or_404(id)
    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({'error': 'Status is required'}), 400
        
    if data['status'] not in ['active', 'inactive', 'on_leave']:
        return jsonify({'error': 'Invalid status'}), 400
    
    user.status = data['status']
    try:
        db.session.commit()
        return jsonify({'message': 'Status updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update user status'}), 500

@bp.route('/aircraft/<int:id>/status', methods=['PUT'])
@login_required
@admin_required
def update_aircraft_status(id):
    aircraft = Aircraft.query.get_or_404(id)
    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({'error': 'Status is required'}), 400
        
    if data['status'] not in ['available', 'maintenance', 'inactive']:
        return jsonify({'error': 'Invalid status'}), 400
    
    aircraft.status = data['status']
    try:
        db.session.commit()
        return jsonify({'message': 'Status updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update aircraft status'}), 500

@bp.route('/bookings')
@login_required
@admin_required
def manage_bookings():
    bookings = Booking.query.all()
    return render_template('admin/bookings.html', bookings=bookings)

@bp.route('/booking/<int:booking_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    db.session.delete(booking)
    db.session.commit()
    flash('Booking deleted successfully.', 'success')
    return redirect(url_for('admin.manage_bookings'))

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