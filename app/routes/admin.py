from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import User, Aircraft, Booking
from app import db
from datetime import datetime
from functools import wraps
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired, Email, Optional

bp = Blueprint('admin', __name__)

class InstructorForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Optional()])
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    phone = StringField('Phone', validators=[DataRequired()])
    
    # FAA Flight Instructor Certificates and Ratings
    certificates = SelectMultipleField('Certificates and Ratings', 
        choices=[
            ('CFI', 'Certified Flight Instructor (CFI)'),
            ('CFII', 'Certified Flight Instructor - Instrument (CFII)'),
            ('MEI', 'Multi-Engine Instructor (MEI)'),
            ('AGI', 'Advanced Ground Instructor'),
            ('IGI', 'Instrument Ground Instructor'),
            ('BGI', 'Basic Ground Instructor'),
            ('RHE', 'Remote Pilot Instructor'),
            ('SPI', 'Sport Pilot Instructor'),
            ('GLS', 'Glider Instructor'),
            ('HGI', 'Helicopter Instructor'),
            ('RPI', 'Rotorcraft Instructor'),
            ('LTA', 'Lighter-Than-Air Instructor'),
            ('WSC', 'Weight-Shift Control Instructor'),
            ('PPC', 'Powered Parachute Instructor'),
            ('TGI', 'Temporary Ground Instructor')
        ],
        validators=[DataRequired()]
    )

class StudentForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    phone = StringField('Phone', validators=[Optional()])
    address = StringField('Address', validators=[Optional()])
    student_id = StringField('Student ID', validators=[Optional()])
    status = SelectField('Status', 
        choices=[
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('on_leave', 'On Leave')
        ],
        validators=[DataRequired()]
    )

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need to be an admin to access this page.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@login_required
@admin_required
def dashboard():
    users = User.query.all()
    aircraft = Aircraft.query.all()
    bookings = Booking.query.all()
    instructors = User.query.filter_by(is_instructor=True).all()
    return render_template('admin/dashboard.html', 
                         users=users, 
                         aircraft=aircraft, 
                         bookings=bookings,
                         instructors=instructors)

@bp.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@bp.route('/aircraft')
@login_required
@admin_required
def manage_aircraft():
    aircraft = Aircraft.query.all()
    return render_template('admin/aircraft.html', aircraft=aircraft)

@bp.route('/instructor')
@bp.route('/instructor/')
@login_required
@admin_required
def instructor_list():
    instructors = User.query.filter_by(is_instructor=True).all()
    return render_template('admin/instructor_list.html', instructors=instructors)

@bp.route('/bookings')
@login_required
@admin_required
def manage_bookings():
    bookings = Booking.query.all()
    return render_template('admin/bookings.html', bookings=bookings)

@bp.route('/user/<int:user_id>/delete', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Cannot delete admin users.', 'error')
        return redirect(url_for('admin.manage_users'))
    
    form = FlaskForm()
    
    if request.method == 'GET':
        return render_template('admin/delete_user.html', user=user, form=form)
    
    if form.validate_on_submit():
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully')
        if user.is_instructor:
            return redirect(url_for('admin.instructor_list'))
        return redirect(url_for('admin.manage_users'))
    
    flash('Invalid form submission')
    return redirect(url_for('admin.delete_user', user_id=user_id))

@bp.route('/aircraft/<int:aircraft_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_aircraft(aircraft_id):
    aircraft = Aircraft.query.get_or_404(aircraft_id)
    db.session.delete(aircraft)
    db.session.commit()
    flash('Aircraft deleted successfully.', 'success')
    return redirect(url_for('admin.manage_aircraft'))

@bp.route('/booking/<int:booking_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    db.session.delete(booking)
    db.session.commit()
    flash('Booking deleted successfully.', 'success')
    return redirect(url_for('admin.manage_bookings'))

@bp.route('/aircraft/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_aircraft():
    if request.method == 'POST':
        tail_number = request.form.get('tail_number')
        make_model = request.form.get('make_model')
        year = request.form.get('year')
        status = request.form.get('status', 'available')
        rate_per_hour = request.form.get('rate_per_hour')
        
        if not tail_number or not make_model or not year or not rate_per_hour:
            flash('Please fill in all required fields')
            return redirect(url_for('admin.add_aircraft'))
        
        aircraft = Aircraft(
            tail_number=tail_number,
            make_model=make_model,
            year=int(year),
            status=status,
            rate_per_hour=float(rate_per_hour)
        )
        db.session.add(aircraft)
        db.session.commit()
        flash('Aircraft added successfully')
        return redirect(url_for('admin.manage_aircraft'))
    
    return render_template('admin/add_aircraft.html')

@bp.route('/instructor/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_instructor():
    form = InstructorForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            new_instructor = User(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                email=form.email.data,
                phone=form.phone.data,
                is_instructor=True,
                status='available',
                certificates=', '.join(form.certificates.data)
            )
            new_instructor.set_password(form.password.data)
            
            try:
                db.session.add(new_instructor)
                db.session.commit()
                flash('Instructor added successfully', 'success')
                return redirect(url_for('admin.instructor_list'))
            except Exception as e:
                db.session.rollback()
                flash('Email already registered', 'error')
                return redirect(url_for('admin.add_instructor'))
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{field}: {error}', 'error')
    
    return render_template('admin/add_instructor.html', form=form)

@bp.route('/instructor/<int:instructor_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_instructor(instructor_id):
    instructor = User.query.get_or_404(instructor_id)
    if not instructor.is_instructor:
        flash('User is not an instructor')
        return redirect(url_for('admin.dashboard'))
    
    form = InstructorForm(obj=instructor)
    # Remove password validation for edit form
    form.password.validators = []
    
    # Set the certificates field to a list of certificates
    if instructor.certificates:
        form.certificates.data = [cert.strip() for cert in instructor.certificates.split(',')]
    
    if request.method == 'POST':
        # Handle certificates from form or direct string input
        certificates = request.form.getlist('certificates')
        if not certificates:
            # If certificates is a string, split it
            cert_str = request.form.get('certificates')
            if cert_str:
                certificates = [cert.strip() for cert in cert_str.split(',')]
        
        if certificates:
            instructor.certificates = ', '.join(certificates)
        
        if form.validate_on_submit():
            instructor.email = form.email.data
            instructor.first_name = form.first_name.data
            instructor.last_name = form.last_name.data
            instructor.phone = form.phone.data
            instructor.status = request.form.get('status', 'available')
            
            try:
                db.session.commit()
                flash('Instructor updated successfully', 'success')
                return redirect(url_for('admin.instructor_list'))
            except Exception as e:
                db.session.rollback()
                flash('Error updating instructor. Email may already be in use.', 'error')
                return redirect(url_for('admin.edit_instructor', instructor_id=instructor_id))
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{field}: {error}', 'error')
    
    return render_template('admin/edit_instructor.html', form=form, instructor=instructor)

@bp.route('/instructor/<int:instructor_id>/status', methods=['GET', 'POST'])
@login_required
@admin_required
def instructor_status(instructor_id):
    instructor = User.query.get_or_404(instructor_id)
    if not instructor.is_instructor:
        flash('User is not an instructor')
        return redirect(url_for('admin.instructor_list'))
    
    form = InstructorForm(obj=instructor)
    
    if request.method == 'POST':
        status = request.form.get('status')
        if status not in ['active', 'unavailable']:
            flash('Invalid status')
            return redirect(url_for('admin.instructor_status', instructor_id=instructor_id))
        
        instructor.status = status
        db.session.commit()
        flash('Instructor status updated successfully')
        return redirect(url_for('admin.instructor_list'))
    
    return render_template('admin/instructor_status.html', instructor=instructor, form=form)

@bp.route('/aircraft/<int:aircraft_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_aircraft(aircraft_id):
    aircraft = Aircraft.query.get_or_404(aircraft_id)
    
    if request.method == 'POST':
        aircraft.tail_number = request.form.get('tail_number', aircraft.tail_number)
        aircraft.make_model = request.form.get('make_model', aircraft.make_model)
        aircraft.year = request.form.get('year', aircraft.year)
        aircraft.status = request.form.get('status', aircraft.status)
        
        db.session.commit()
        flash('Aircraft updated successfully.', 'success')
        return redirect(url_for('admin.manage_aircraft'))
    
    return render_template('admin/edit_aircraft.html', aircraft=aircraft)

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

@bp.route('/aircraft/<int:aircraft_id>/status', methods=['POST'])
@login_required
@admin_required
def update_aircraft_status(aircraft_id):
    aircraft = Aircraft.query.get_or_404(aircraft_id)
    status = request.form.get('status')
    if status not in ['available', 'maintenance', 'reserved']:
        flash('Invalid status', 'error')
        return redirect(url_for('admin.manage_aircraft'))
    
    aircraft.status = status
    db.session.commit()
    flash('Aircraft status updated successfully')
    return redirect(url_for('admin.manage_aircraft'))

@bp.route('/student/<int:student_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_student(student_id):
    student = User.query.get_or_404(student_id)
    if student.is_admin or student.is_instructor:
        flash('Invalid student ID', 'error')
        return redirect(url_for('admin.manage_users'))
    
    form = StudentForm(obj=student)
    
    if form.validate_on_submit():
        student.email = form.email.data
        student.first_name = form.first_name.data
        student.last_name = form.last_name.data
        student.phone = form.phone.data
        student.address = form.address.data
        student.student_id = form.student_id.data
        student.status = form.status.data
        
        db.session.commit()
        flash('Student information updated successfully', 'success')
        return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/edit_student.html', student=student, form=form)

@bp.route('/student/<int:student_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_student_password(student_id):
    student = User.query.get_or_404(student_id)
    if student.is_admin or student.is_instructor:
        flash('Invalid student ID', 'error')
        return redirect(url_for('admin.manage_users'))
    
    new_password = request.form.get('new_password')
    if not new_password:
        flash('Please provide a new password', 'error')
        return redirect(url_for('admin.edit_student', student_id=student_id))
    
    student.set_password(new_password)
    db.session.commit()
    flash('Student password reset successfully', 'success')
    return redirect(url_for('admin.edit_student', student_id=student_id))

@bp.route('/student/add', methods=['POST'])
@login_required
@admin_required
def add_student():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    student_id = request.form.get('student_id')
    
    if not all([first_name, last_name, email, phone, student_id]):
        flash('All fields are required.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    # Generate a temporary password
    temp_password = 'ChangeMe123!'
    
    new_student = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        student_id=student_id,
        is_admin=False,
        is_instructor=False,
        status='active'
    )
    new_student.set_password(temp_password)
    
    try:
        db.session.add(new_student)
        db.session.commit()
        flash(f'Student {first_name} {last_name} added successfully. Temporary password: {temp_password}', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error adding student. Email or Student ID may already be in use.', 'error')
    
    return redirect(url_for('admin.dashboard'))

@bp.route('/booking/add', methods=['POST'])
@login_required
@admin_required
def add_booking():
    student_id = request.form.get('student_id')
    instructor_id = request.form.get('instructor_id') or None  # Handle solo flights
    aircraft_id = request.form.get('aircraft_id')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    
    if not all([student_id, aircraft_id, start_time, end_time]):
        flash('Required fields are missing.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    try:
        start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
        end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
        
        if start_time >= end_time:
            flash('End time must be after start time.', 'error')
            return redirect(url_for('admin.dashboard'))
        
        # Check if aircraft is available
        aircraft = Aircraft.query.get(aircraft_id)
        if aircraft.status != 'available':
            flash('Selected aircraft is not available.', 'error')
            return redirect(url_for('admin.dashboard'))
        
        # Check if instructor is available (if not a solo flight)
        if instructor_id:
            instructor = User.query.get(instructor_id)
            if instructor.status != 'available':
                flash('Selected instructor is not available.', 'error')
                return redirect(url_for('admin.dashboard'))
        
        new_booking = Booking(
            student_id=student_id,
            instructor_id=instructor_id,
            aircraft_id=aircraft_id,
            start_time=start_time,
            end_time=end_time,
            status='scheduled'
        )
        
        db.session.add(new_booking)
        db.session.commit()
        flash('Flight schedule added successfully.', 'success')
    except ValueError:
        flash('Invalid date/time format.', 'error')
    except Exception as e:
        db.session.rollback()
        flash('Error adding flight schedule.', 'error')
    
    return redirect(url_for('admin.dashboard')) 