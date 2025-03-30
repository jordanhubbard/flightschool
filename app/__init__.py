from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from config import Config
from datetime import datetime

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    # Register blueprints
    from app.routes import auth, admin, booking, main
    app.register_blueprint(auth.bp, url_prefix='/auth')
    app.register_blueprint(admin.bp, url_prefix='/admin')
    app.register_blueprint(booking.bp, url_prefix='/booking')
    app.register_blueprint(main.bp)

    # Add template context processor
    @app.context_processor
    def utility_processor():
        return {'now': datetime.now()}

    # Create database tables
    with app.app_context():
        db.create_all()
        db.session.commit()

    return app

from app.models import User

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id)) 