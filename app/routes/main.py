from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from app.models import User

main_bp = Blueprint('main', __name__)


@main_bp.route('/profile')
@login_required
def profile():
    """Display user profile."""
    return render_template('main/profile.html', user=current_user)


@main_bp.route('/about')
def about():
    """Display about page."""
    return render_template('main/about.html')


@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Handle contact form submission."""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        # Here you would typically send an email or save to database
        flash('Thank you for your message! We will get back to you soon.', 'success')
        return redirect(url_for('main.contact'))

    return render_template('main/contact.html')
