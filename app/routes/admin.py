from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app.models import User, Aircraft, Booking, MaintenanceRecord, MaintenanceType, MaintenanceRecord, Squawk, Document, WeatherMinima
from datetime import datetime, timedelta
from app import db
from functools import wraps

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Decorator to require admin access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Display admin dashboard."""
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(status='active').count(),
        'total_aircraft': Aircraft.query.count(),
        'available_aircraft': Aircraft.query.filter_by(status='available').count(),
        'pending_bookings': Booking.query.filter_by(status='pending').count(),
        'maintenance_due': MaintenanceRecord.query.filter_by(status='due').count()
    }
    return render_template('admin/dashboard.html', stats=stats)


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """Display user management page."""
    users = User.query.order_by(User.last_name).all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/aircraft')
@login_required
@admin_required
def aircraft():
    """Display aircraft management page."""
    aircraft = Aircraft.query.order_by(Aircraft.registration).all()
    return render_template('admin/aircraft.html', aircraft=aircraft)


@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    """Display reports page."""
    return render_template('admin/reports.html')


@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    """Display admin settings page."""
    return render_template('admin/settings.html')


@admin_bp.route('/schedule')
@login_required
@admin_required
def schedule():
    """Display master schedule."""
    start_date = datetime.now()
    end_date = start_date + timedelta(days=30)
    bookings = Booking.query.filter(
        Booking.start_time >= start_date,
        Booking.start_time <= end_date
    ).order_by(Booking.start_time).all()
    return render_template('admin/schedule.html', bookings=bookings)


@admin_bp.route('/maintenance/records')
@login_required
@admin_required
def maintenance_records():
    """Display maintenance records."""
    records = MaintenanceRecord.query.order_by(MaintenanceRecord.date.desc()).all()
    return render_template('admin/maintenance_records.html', records=records)


@admin_bp.route('/squawks')
@login_required
@admin_required
def squawks():
    """Display aircraft squawks."""
    return render_template('admin/squawks.html')


@admin_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    """Display audit logs."""
    return render_template('admin/audit_logs.html')


@admin_bp.route('/weather-minima')
@login_required
@admin_required
def weather_minima():
    """Display weather minima settings."""
    return render_template('admin/weather_minima.html')


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
@admin_required
def edit_user(id):
    """Edit an existing user."""
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
        db.session.delete(aircraft)
        db.session.commit()
        flash('Aircraft deleted successfully', 'success')
        return redirect(url_for('admin.dashboard'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting aircraft: {str(e)}')
        flash('Failed to delete aircraft. Please try again.', 'error')


@admin_bp.route('/calendar/oauth')
@login_required
@admin_required
def calendar_oauth():
    """Start Google Calendar OAuth2 flow for admin settings."""
    return redirect(url_for('settings.calendar_authorize'))


@admin_bp.route('/calendar/callback')
@login_required
@admin_required
def calendar_callback():
    """Handle Google Calendar OAuth2 callback for admin settings."""
    return redirect(url_for('settings.calendar_callback'))


@admin_bp.route('/maintenance/types')
@login_required
@admin_required
def maintenance_types():
    """Display maintenance types."""
    types = MaintenanceType.query.order_by(MaintenanceType.name).all()
    return render_template('admin/maintenance_types.html', types=types)


@admin_bp.route('/instructors')
@login_required
@admin_required
def instructors():
    """Display instructor management page."""
    instructors = User.query.filter_by(is_instructor=True).order_by(User.last_name).all()
    return render_template('admin/instructors.html', instructors=instructors)


@admin_bp.route('/instructor/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_instructor():
    """Create a new instructor."""
    return redirect(url_for('admin.create_user'))


@admin_bp.route('/endorsements')
@login_required
@admin_required
def endorsements():
    """Display endorsement management page."""
    return render_template('admin/endorsements.html')


@admin_bp.route('/documents')
@login_required
@admin_required
def documents():
    """Display document management page."""
    return render_template('admin/documents.html')


@admin_bp.route('/waitlist')
@login_required
@admin_required
def waitlist():
    """Display waitlist management page."""
    waitlist_entries = Booking.query.filter_by(status='waitlist').order_by(Booking.created_at).all()
    return render_template('admin/waitlist.html', entries=waitlist_entries)


@admin_bp.route('/recurring-bookings')
@login_required
@admin_required
def recurring_bookings():
    """Display recurring bookings management page."""
    recurring = Booking.query.filter_by(is_recurring=True).order_by(Booking.start_time).all()
    return render_template('admin/recurring_bookings.html', bookings=recurring)


@admin_bp.route('/flight-logs')
@login_required
@admin_required
def flight_logs():
    """Display flight logs management page."""
    return render_template('admin/flight_logs.html')
