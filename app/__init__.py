from flask import Flask, render_template, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from config import config
from datetime import datetime

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
migrate = Migrate()
mail = Mail()
csrf = CSRFProtect()

def create_app(config_name='default'):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    csrf.init_app(app)

    @app.context_processor
    def inject_datetime():
        return dict(datetime=datetime)

    from app.routes import auth, booking, admin, main, maintenance
    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(booking.booking_bp)
    app.register_blueprint(admin.admin_bp, url_prefix='/admin')
    app.register_blueprint(main.main_bp)
    app.register_blueprint(maintenance.maintenance_bp)

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app

from app.models import User, Aircraft, Booking, CheckIn, CheckOut, Invoice

@login_manager.user_loader
def load_user(id):
    """Load user from database."""
    current_app.logger.debug(f"Loading user with ID: {id}")
    user = User.query.get(int(id))
    if user:
        current_app.logger.debug(f"Loaded user: {user}, Role: {user.role}, Is Admin: {user.is_admin}")
    else:
        current_app.logger.debug("User not found")
    return user 