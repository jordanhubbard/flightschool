from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from config import Config
from datetime import datetime

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    # Register blueprints
    from app.routes import auth, main, booking
    from app.routes.admin import bp as admin_bp
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(booking.bp, url_prefix='/booking')

    # Add template context processor
    @app.context_processor
    def utility_processor():
        return {'now': datetime.now()}

    # Create database tables
    with app.app_context():
        db.create_all()
        db.session.commit()

    return app 