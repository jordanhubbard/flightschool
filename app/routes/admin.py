from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import User, Aircraft, Booking
from app import db
from datetime import datetime
from functools import wraps
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired, Email

bp = Blueprint('admin', __name__)

class InstructorForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
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
def admin_dashboard():
    users = User.query.all()
    aircraft = Aircraft.query.all()
    bookings = Booking.query.all()
    return render_template('admin/dashboard.html', users=users, aircraft=aircraft, bookings=bookings)

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
        
        if not tail_number or not make_model or not year:
            flash('Please fill in all required fields')
            return redirect(url_for('admin.add_aircraft'))
        
        aircraft = Aircraft(
            tail_number=tail_number,
            make_model=make_model,
            year=int(year),
            status=status
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
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered')
            return redirect(url_for('admin.add_instructor'))
        
        # Join multiple certificates with commas
        certificates = ', '.join(form.certificates.data)
        
        instructor = User(
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            certificates=certificates,
            is_instructor=True,
            status='available'
        )
        instructor.set_password(form.password.data)
        db.session.add(instructor)
        db.session.commit()
        flash('Instructor added successfully')
        return redirect(url_for('admin.instructor_list'))
    
    return render_template('admin/instructor_add.html', form=form)

@bp.route('/instructor/<int:instructor_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_instructor(instructor_id):
    instructor = User.query.get_or_404(instructor_id)
    if not instructor.is_instructor:
        flash('User is not an instructor')
        return redirect(url_for('admin.instructor_list'))
    
    form = InstructorForm(obj=instructor)
    
    if request.method == 'POST':
        instructor.email = request.form.get('email')
        instructor.first_name = request.form.get('first_name')
        instructor.last_name = request.form.get('last_name')
        instructor.phone = request.form.get('phone')
        # Handle certificates as a list and join with commas and spaces
        certificates = request.form.getlist('certificates')
        instructor.certificates = ', '.join(certificates) if certificates else ''
        instructor.status = request.form.get('status', 'active')
        
        db.session.commit()
        flash('Instructor updated successfully')
        return redirect(url_for('admin.instructor_list'))
    
    return render_template('admin/instructor_edit.html', instructor=instructor, form=form)

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
            return redirect(url_for('admin.admin_dashboard'))
            
        except Exception as e:
            flash('Error updating booking. Please check the form data.', 'error')
            return redirect(url_for('admin.admin_dashboard'))
    
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