from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from config import Config
from datetime import datetime
import os

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()
csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure instance directory exists
    instance_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'instance'))
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)

    # Ensure secret key is set
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = 'dev-key-please-change-in-production'

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    # Register blueprints
    from app.routes import auth, admin, booking, main, maintenance
    app.register_blueprint(auth.bp, url_prefix='/auth')
    app.register_blueprint(admin.bp, url_prefix='/admin')
    app.register_blueprint(booking.bp, url_prefix='/booking')
    app.register_blueprint(main.bp)
    app.register_blueprint(maintenance.bp)

    # Add template context processor
    @app.context_processor
    def utility_processor():
        return {'now': datetime.now()}

    # Create database tables
    with app.app_context():
        db.create_all()
        db.session.commit()

    from app.errors import init_error_handlers
    init_error_handlers(app)

    return app

from app.models import User, Aircraft, Booking, CheckIn, CheckOut, Invoice

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id)) 