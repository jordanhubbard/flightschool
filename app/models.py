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
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    name = db.Column(db.String(128))  # Full name, computed from first_name and last_name
    phone = db.Column(db.String(20))
    address = db.Column(db.String(256))
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    is_instructor = db.Column(db.Boolean, default=False)
    student_id = db.Column(db.String(20), unique=True)
    certificates = db.Column(db.String(200))
    status = db.Column(db.String(20), default='active')  # active, unavailable, inactive
    instructor_rate_per_hour = db.Column(db.Float)  # Instructor rate per hour
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Google Calendar integration
    google_calendar_credentials = db.Column(db.Text, nullable=True)  # Store JSON credentials
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
    check_ins = db.relationship('CheckIn', backref='instructor', lazy='dynamic')
    check_outs = db.relationship('CheckOut', backref='instructor', lazy='dynamic')
    created_maintenance_types = db.relationship('MaintenanceType', backref='created_by')
    performed_maintenance = db.relationship('MaintenanceRecord', backref='performed_by')
    reported_squawks = db.relationship('Squawk', foreign_keys='Squawk.reported_by_id', backref='reported_by')
    resolved_squawks = db.relationship('Squawk', foreign_keys='Squawk.resolved_by_id', backref='resolved_by')
    
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
    status = db.Column(db.String(20), default='open')  # open, in_progress, resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    resolution_notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Squawk {self.id}>'

class Aircraft(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    registration = db.Column(db.String(10), unique=True, nullable=False)
    tail_number = db.Column(db.String(10), unique=True)  # For backward compatibility
    type = db.Column(db.String(50))  # Optional now
    make_model = db.Column(db.String(100), nullable=False)  # Required field for aircraft model
    year = db.Column(db.Integer)  # Year of manufacture
    status = db.Column(db.String(20), nullable=False, default='available')  # available, maintenance, retired
    rate_per_hour = db.Column(db.Float, nullable=False)  # Aircraft rental rate per hour
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    maintenance_records = db.relationship('MaintenanceRecord', backref='aircraft', lazy=True)
    squawks = db.relationship('Squawk', backref='aircraft', lazy=True)
    bookings = db.relationship('Booking', backref='aircraft', lazy='dynamic')
    check_ins = db.relationship('CheckIn', backref='aircraft', lazy='dynamic')

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
            'rate_per_hour': self.rate_per_hour,
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
    google_calendar_event_id = db.Column(db.String(255), nullable=True)  # Store Google Calendar event ID
    
    # Relationships
    check_in = db.relationship('CheckIn', backref='booking', uselist=False)
    check_out = db.relationship('CheckOut', backref='booking', uselist=False)
    invoice = db.relationship('Invoice', backref='booking', uselist=False)
    
    def __repr__(self):
        return f'<Booking {self.id}>'

class CheckIn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    aircraft_id = db.Column(db.Integer, db.ForeignKey('aircraft.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    check_in_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    hobbs_start = db.Column(db.Float, nullable=False)
    tach_start = db.Column(db.Float, nullable=False)
    instructor_start_time = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<CheckIn {self.id}>'

class CheckOut(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    aircraft_id = db.Column(db.Integer, db.ForeignKey('aircraft.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    check_out_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    hobbs_end = db.Column(db.Float, nullable=False)
    tach_end = db.Column(db.Float, nullable=False)
    instructor_end_time = db.Column(db.DateTime, nullable=True)
    total_aircraft_time = db.Column(db.Float, nullable=False)  # Calculated from hobbs_end - hobbs_start
    total_instructor_time = db.Column(db.Float, nullable=True)  # Calculated from instructor_end_time - instructor_start_time
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<CheckOut {self.id}>'

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    aircraft_id = db.Column(db.Integer, db.ForeignKey('aircraft.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    invoice_number = db.Column(db.String(20), unique=True, nullable=False)
    invoice_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    aircraft_rate = db.Column(db.Float, nullable=False)
    instructor_rate = db.Column(db.Float, nullable=True)
    aircraft_time = db.Column(db.Float, nullable=False)
    instructor_time = db.Column(db.Float, nullable=True)
    aircraft_total = db.Column(db.Float, nullable=False)
    instructor_total = db.Column(db.Float, nullable=True)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, paid, overdue
    payment_date = db.Column(db.DateTime)
    payment_method = db.Column(db.String(50))
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number}>' 