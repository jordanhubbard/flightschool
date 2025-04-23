from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app
from flask_login import login_required, current_user
from app.models import User, Aircraft, Booking, MaintenanceType, MaintenanceRecord, Squawk, Document, WeatherMinima
from app import db
from datetime import datetime

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Admin dashboard view."""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    
    users = User.query.all()
    aircraft = Aircraft.query.all()
    bookings = Booking.query.order_by(Booking.start_time.desc()).limit(5).all()
    maintenance_records = MaintenanceRecord.query.order_by(MaintenanceRecord.performed_at.desc()).limit(5).all()
    squawks = Squawk.query.order_by(Squawk.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                         users=users,
                         aircraft=aircraft,
                         bookings=bookings,
                         maintenance_records=maintenance_records,
                         squawks=squawks)


@admin_bp.route('/user/create', methods=['GET', 'POST'])
@login_required
def create_user():
    """Create a new user."""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    
    form = UserForm()
    if form.validate_on_submit():
        try:
            user = User(
                email=form.email.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                phone=form.phone.data,
                role=form.role.data,
                status='active'
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('User created successfully', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error creating user: {str(e)}')
            flash('Failed to create user. Please try again.', 'error')
    
    return render_template('admin/create_user.html', form=form)


@admin_bp.route('/user/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    """Edit an existing user."""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        try:
            user.email = form.email.data
            user.first_name = form.first_name.data
            user.last_name = form.last_name.data
            user.phone = form.phone.data
            user.role = form.role.data
            if form.password.data:
                user.set_password(form.password.data)
            db.session.commit()
            flash('User updated successfully', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error updating user: {str(e)}')
            flash('Failed to update user. Please try again.', 'error')
    
    return render_template('admin/edit_user.html', form=form, user=user)


@admin_bp.route('/aircraft/create', methods=['GET', 'POST'])
@login_required
def create_aircraft():
    """Create a new aircraft."""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    
    form = AircraftForm()
    if form.validate_on_submit():
        try:
            aircraft = Aircraft(
                registration=form.registration.data,
                make=form.make.data,
                model=form.model.data,
                year=form.year.data,
                category=form.category.data,
                rate_per_hour=form.rate_per_hour.data,
                status='available',
                time_to_next_oil_change=form.time_to_next_oil_change.data,
                time_to_next_100hr=form.time_to_next_100hr.data,
                date_of_next_annual=form.date_of_next_annual.data
            )
            if form.image.data:
                filename = secure_filename(f"{aircraft.registration.upper()}.jpg")
                image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                form.image.data.save(image_path)
                aircraft.image_filename = filename
            db.session.add(aircraft)
            db.session.commit()
            flash('Aircraft created successfully', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error creating aircraft: {str(e)}')
            flash('Failed to create aircraft. Please try again.', 'error')
    
    return render_template('admin/create_aircraft.html', form=form)


@admin_bp.route('/aircraft/<int:id>/delete', methods=['POST'])
@login_required
def delete_aircraft(id):
    """Delete an aircraft."""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    
    aircraft = Aircraft.query.get_or_404(id)
    try:
        db.session.delete(airircraft)
        db.session.commit()
        flash('Aircraft deleted successfully', 'success')
        return redirect(url_for('admin.dashboard'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting aircraft: {str(e)}')
        flash('Failed to delete aircraft. Please try again.', 'error')
