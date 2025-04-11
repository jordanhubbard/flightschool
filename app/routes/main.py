from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, session
from flask_login import login_required, current_user
from app.models import User, Aircraft, Booking
from app import db

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('main/index.html')

@bp.route('/about')
def about():
    return render_template('main/about.html')

@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # Here you would typically send an email or save to database
        # For now, we'll just show a success message
        flash('Thank you for your message! We will get back to you soon.', 'success')
        return redirect(url_for('main.contact'))
        
    return render_template('main/contact.html')

@bp.route('/profile')
@login_required
def profile():
    return render_template('main/profile.html', user=current_user)

@bp.route('/training')
def training():
    return render_template('main/training.html')

@bp.route('/aircraft')
def aircraft():
    aircraft_list = Aircraft.query.all()
    return render_template('main/aircraft.html', aircraft=aircraft_list)

@bp.route('/faq')
def faq():
    return render_template('main/faq.html')

@bp.route('/debug')
def debug():
    """Debug route to check authentication status."""
    return render_template('debug.html') 