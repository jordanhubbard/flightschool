from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email
from app.models import User
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from app.forms import LoginForm, RegistrationForm, AccountSettingsForm
from app.calendar_service import GoogleCalendarService
from datetime import datetime, UTC
import logging

bp = Blueprint('auth', __name__)
calendar_service = GoogleCalendarService()

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password', 'danger')
            return render_template('auth/login.html', title='Sign In', form=form)
        
        if not user.is_active:
            flash('Your account is inactive. Please contact support.', 'warning')
            return render_template('auth/login.html', title='Sign In', form=form)
        
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('main.index')
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Sign In', form=form)

@bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/account-settings', methods=['GET', 'POST'])
@login_required
def account_settings():
    """Handle account settings."""
    form = AccountSettingsForm(obj=current_user)
    if form.validate_on_submit():
        try:
            current_user.first_name = form.first_name.data
            current_user.last_name = form.last_name.data
            current_user.phone = form.phone.data
            current_user.address = form.address.data
            if form.password.data:
                current_user.set_password(form.password.data)
            db.session.commit()
            flash('Account settings updated successfully', 'success')
            return redirect(url_for('auth.account_settings'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Account settings update error: {str(e)}')
            flash('Failed to update account settings. Please try again.', 'error')
    
    return render_template('auth/account_settings.html', form=form)

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Handle account settings."""
    form = AccountSettingsForm()
    if form.validate_on_submit():
        try:
            current_user.first_name = form.first_name.data
            current_user.last_name = form.last_name.data
            current_user.phone = form.phone.data
            
            if form.password.data:
                current_user.set_password(form.password.data)
            
            db.session.commit()
            flash('Your settings have been updated.', 'success')
            return redirect(url_for('auth.settings'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Settings update error: {str(e)}')
            flash('An error occurred while updating settings. Please try again.', 'danger')
    
    elif request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.phone.data = current_user.phone
    
    return render_template('auth/settings.html', title='Account Settings', form=form)

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
        db.session.rollback()
        current_app.logger.error(f'Google Calendar connection error: {str(e)}')
        flash(f'Error connecting to Google Calendar: {str(e)}', 'error')
    
    return redirect(url_for('auth.settings'))

@bp.route('/google-disconnect', methods=['POST'])
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
    
    return redirect(url_for('auth.settings'))

@bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information."""
    try:
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.phone = request.form.get('phone')
        current_user.address = request.form.get('address')
        db.session.commit()
        flash('Profile updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Profile update error: {str(e)}')
        flash('Failed to update profile. Please try again.', 'error')
    
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
    
    try:
        current_user.set_password(new_password)
        db.session.commit()
        flash('Password changed successfully', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Password change error: {str(e)}')
        flash('Failed to change password. Please try again.', 'error')
    
    return redirect(url_for('auth.settings'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(
                email=form.email.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                phone=form.phone.data,
                status='pending'
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please wait for admin approval.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Registration error: {str(e)}')
            flash('An error occurred during registration. Please try again.', 'danger')
    
    return render_template('auth/register.html', title='Register', form=form)
