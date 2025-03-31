from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='student')  # student, instructor, admin
    is_admin = db.Column(db.Boolean, default=False)
    is_instructor = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='active')
    certificates = db.Column(db.String(500))
    student_id = db.Column(db.String(20))
    address = db.Column(db.String(200))
    name = db.Column(db.String(128))  # Full name, computed from first_name and last_name
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Google Calendar Integration
    google_calendar_enabled = db.Column(db.Boolean, default=False)
    google_calendar_token = db.Column(db.String(500))
    google_calendar_refresh_token = db.Column(db.String(500))
    google_calendar_token_expiry = db.Column(db.DateTime)
    google_calendar_id = db.Column(db.String(100))
    
    # Relationships
    bookings_as_student = db.relationship('Booking', backref='student', lazy='dynamic',
                                        foreign_keys='Booking.student_id')
    bookings_as_instructor = db.relationship('Booking', backref='instructor', lazy='dynamic',
                                           foreign_keys='Booking.instructor_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.name
    
    def __repr__(self):
        return f'<User {self.email}>'

class MaintenanceType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    interval_days = db.Column(db.Integer)  # Calendar interval in days
    interval_hours = db.Column(db.Float)   # Operating hours interval
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_by = db.relationship('User', backref='created_maintenance_types')
    
    # Relationships
    maintenance_records = db.relationship('MaintenanceRecord', backref='maintenance_type', lazy='dynamic')
    
    def __repr__(self):
        return f'<MaintenanceType {self.name}>'

class MaintenanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aircraft_id = db.Column(db.Integer, db.ForeignKey('aircraft.id'), nullable=False)
    maintenance_type_id = db.Column(db.Integer, db.ForeignKey('maintenance_type.id'), nullable=False)
    performed_at = db.Column(db.DateTime, nullable=False)
    performed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    performed_by = db.relationship('User', backref='performed_maintenance')
    notes = db.Column(db.Text)
    hobbs_hours = db.Column(db.Float)
    tach_hours = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<MaintenanceRecord {self.id}>'

class Squawk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aircraft_id = db.Column(db.Integer, db.ForeignKey('aircraft.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    reported_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reported_by = db.relationship('User', foreign_keys=[reported_by_id], backref='reported_squawks')
    status = db.Column(db.String(20), default='open')  # open, in_progress, resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    resolved_by = db.relationship('User', foreign_keys=[resolved_by_id], backref='resolved_squawks')
    resolution_notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Squawk {self.id}>'

class Aircraft(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    registration = db.Column(db.String(10), unique=True, nullable=False)
    tail_number = db.Column(db.String(10), unique=True)  # For backward compatibility
    type = db.Column(db.String(50))  # Optional now
    make_model = db.Column(db.String(50), nullable=False)  # Required field for aircraft model
    year = db.Column(db.Integer)  # Year of manufacture
    status = db.Column(db.String(20), nullable=False, default='available')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    maintenance_records = db.relationship('MaintenanceRecord', backref='aircraft', lazy=True)
    squawks = db.relationship('Squawk', backref='aircraft', lazy=True)
    bookings = db.relationship('Booking', backref='aircraft', lazy=True)

    def __init__(self, **kwargs):
        if 'tail_number' in kwargs and 'registration' not in kwargs:
            kwargs['registration'] = kwargs.pop('tail_number')
        if 'make_model' in kwargs and 'type' not in kwargs:
            kwargs['type'] = kwargs['make_model']
        super().__init__(**kwargs)

    @property
    def tail_number(self):
        return self.registration

    @tail_number.setter
    def tail_number(self, value):
        self.registration = value

    def __repr__(self):
        return f'<Aircraft {self.registration}>'

    def to_dict(self):
        return {
            'id': self.id,
            'registration': self.registration,
            'tail_number': self.registration,  # For backward compatibility
            'type': self.type,
            'make_model': self.make_model,
            'year': self.year,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Optional instructor
    aircraft_id = db.Column(db.Integer, db.ForeignKey('aircraft.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Check-out details
    checkout_time = db.Column(db.DateTime)
    checkout_hobbs = db.Column(db.Float)
    checkout_tach = db.Column(db.Float)
    checkout_squawks = db.Column(db.Text)
    checkout_comments = db.Column(db.Text)
    checkout_instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Check-in details
    checkin_time = db.Column(db.DateTime)
    checkin_hobbs = db.Column(db.Float)
    checkin_tach = db.Column(db.Float)
    checkin_squawks = db.Column(db.Text)
    checkin_comments = db.Column(db.Text)
    checkin_instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Additional relationships
    checkout_instructor = db.relationship('User', foreign_keys=[checkout_instructor_id], backref=db.backref('checkout_flights'))
    checkin_instructor = db.relationship('User', foreign_keys=[checkin_instructor_id], backref=db.backref('checkin_flights'))
    
    def __repr__(self):
        return f'<Booking {self.id}>' 