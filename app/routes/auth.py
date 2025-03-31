from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app import db
from werkzeug.security import generate_password_hash
from app.forms import LoginForm, RegistrationForm, AccountSettingsForm
from app.calendar_service import GoogleCalendarService

bp = Blueprint('auth', __name__)
calendar_service = GoogleCalendarService()

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login or reset your password.')
            return redirect(url_for('auth.login'))
        
        user = User(
            email=email,
            first_name=request.form.get('first_name'),
            last_name=request.form.get('last_name'),
            address=request.form.get('address'),
            phone=request.form.get('phone')
        )
        user.set_password(request.form.get('password'))
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
        else:
            # Handle raw form data for tests
            email = request.form.get('email')
            password = request.form.get('password')
            user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password if 'password' in locals() else form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            if user.is_admin:
                return redirect(next_page or url_for('admin.dashboard'))
            return redirect(next_page or url_for('booking.dashboard'))
        
        flash('Invalid email or password')
    return render_template('auth/login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out')
    return redirect(url_for('main.index'))

@bp.route('/account-settings', methods=['GET', 'POST'])
@login_required
def account_settings():
    form = AccountSettingsForm()
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.phone = form.phone.data
        if form.password.data:
            current_user.set_password(form.password.data)
        db.session.commit()
        flash('Account settings updated successfully', 'success')
        return redirect(url_for('auth.account_settings'))
    elif request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.phone.data = current_user.phone
    return render_template('auth/account_settings.html', form=form)

@bp.route('/settings')
@login_required
def settings():
    return render_template('auth/settings.html')

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
        flash('Failed to authenticate with Google Calendar', 'error')
        return redirect(url_for('auth.settings'))
    
    try:
        credentials = calendar_service.handle_callback(code)
        current_user.google_calendar_credentials = credentials.to_json()
        current_user.google_calendar_enabled = True
        db.session.commit()
        flash('Successfully connected to Google Calendar', 'success')
    except Exception as e:
        flash(f'Error connecting to Google Calendar: {str(e)}', 'error')
    
    return redirect(url_for('auth.settings'))

@bp.route('/google-disconnect', methods=['POST'])
@login_required
def google_disconnect():
    """Disconnect Google Calendar integration."""
    current_user.google_calendar_credentials = None
    current_user.google_calendar_enabled = False
    db.session.commit()
    flash('Successfully disconnected from Google Calendar', 'success')
    return redirect(url_for('auth.settings'))

@bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information."""
    current_user.first_name = request.form.get('first_name')
    current_user.last_name = request.form.get('last_name')
    current_user.phone = request.form.get('phone')
    current_user.address = request.form.get('address')
    db.session.commit()
    flash('Profile updated successfully', 'success')
    return redirect(url_for('auth.settings'))

@bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password."""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not current_user.check_password(current_password):
        flash('Current password is incorrect', 'error')
        return redirect(url_for('auth.settings'))
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('auth.settings'))
    
    current_user.set_password(new_password)
    db.session.commit()
    flash('Password changed successfully', 'success')
    return redirect(url_for('auth.settings')) 