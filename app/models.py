from app import db, login_manager
from flask_login import UserMixin, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class AnonymousUser(AnonymousUserMixin):
    """Anonymous user class for unauthenticated users."""
    def __init__(self):
        self.id = None
        self.email = None
        self.first_name = None
        self.last_name = None
        self.role = None
        self.status = 'inactive'
        self.is_admin = False
        self.is_instructor = False
        self.is_student = False

    @property
    def is_active(self):
        return False

    @property
    def is_authenticated(self):
        return False

    @property
    def is_anonymous(self):
        return True

    def get_id(self):
        return None

    def __repr__(self):
        return '<AnonymousUser>'

# Configure login manager to use custom anonymous user class
login_manager.anonymous_user = AnonymousUser

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    name = db.Column(db.String(128))  # Full name, computed from first_name and last_name
    phone = db.Column(db.String(20))
    address = db.Column(db.String(256))
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='student')  # student, instructor, admin
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
    flight_logs = db.relationship('FlightLog', backref='pilot', foreign_keys='FlightLog.pic_id')
    endorsements_given = db.relationship('Endorsement', backref='instructor', foreign_keys='Endorsement.instructor_id')
    endorsements_received = db.relationship('Endorsement', backref='student', foreign_keys='Endorsement.student_id')
    documents = db.relationship('Document', backref='user')
    audit_logs = db.relationship('AuditLog', backref='user')
    waitlist_entries = db.relationship('WaitlistEntry', backref='student', foreign_keys='WaitlistEntry.student_id')
    recurring_bookings = db.relationship('RecurringBooking', backref='student', foreign_keys='RecurringBooking.student_id')
    
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

    @property
    def is_active(self):
        return self.status == 'active'

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
    make = db.Column(db.String(50))
    model = db.Column(db.String(50))
    type = db.Column(db.String(50))  # Optional now
    make_model = db.Column(db.String(100))  # For backward compatibility
    description = db.Column(db.Text)
    year = db.Column(db.Integer)  # Year of manufacture
    status = db.Column(db.String(20), nullable=False, default='available')  # available, maintenance, retired
    category = db.Column(db.String(50))  # single_engine_land, multi_engine_land, etc.
    engine_type = db.Column(db.String(20))  # piston, turboprop, jet
    num_engines = db.Column(db.Integer, default=1)
    ifr_equipped = db.Column(db.Boolean, default=False)
    gps = db.Column(db.Boolean, default=False)
    autopilot = db.Column(db.Boolean, default=False)
    rate_per_hour = db.Column(db.Float, nullable=False)  # Aircraft rental rate per hour
    hobbs_time = db.Column(db.Float)  # Current hobbs time
    tach_time = db.Column(db.Float)  # Current tach time
    last_maintenance = db.Column(db.DateTime)  # Last maintenance date
    image_filename = db.Column(db.String(100))  # Filename for aircraft image
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    maintenance_status = db.Column(db.String(50), default='airworthy')  # airworthy, maintenance_due, grounded
    next_maintenance_date = db.Column(db.DateTime)
    next_maintenance_hours = db.Column(db.Float)
    insurance_expiry = db.Column(db.DateTime)
    registration_expiry = db.Column(db.DateTime)
    recurring_bookings = db.relationship('RecurringBooking', backref='aircraft')
    waitlist_entries = db.relationship('WaitlistEntry', backref='aircraft')
    # Relationships
    maintenance_records = db.relationship('MaintenanceRecord', backref='aircraft', lazy=True)
    squawks = db.relationship('Squawk', backref='aircraft', lazy=True)
    bookings = db.relationship('Booking', backref='aircraft', lazy='dynamic')
    check_ins = db.relationship('CheckIn', backref='aircraft', lazy='dynamic')

    def __init__(self, **kwargs):
        # Handle backward compatibility
        if 'tail_number' in kwargs and 'registration' not in kwargs:
            kwargs['registration'] = kwargs.pop('tail_number')
        
        # Handle make and model fields
        if 'make' in kwargs and 'model' in kwargs and 'make_model' not in kwargs:
            kwargs['make_model'] = f"{kwargs['make']} {kwargs['model']}"
        elif 'make_model' in kwargs and 'make' not in kwargs and 'model' not in kwargs:
            # Try to split make_model into make and model
            parts = kwargs['make_model'].split(' ', 1)
            if len(parts) > 1:
                kwargs['make'] = parts[0]
                kwargs['model'] = parts[1]
            else:
                kwargs['make'] = kwargs['make_model']
                kwargs['model'] = ''
        
        # Handle type field for backward compatibility
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
            'make': self.make,
            'model': self.model,
            'make_model': self.make_model,
            'type': self.type,
            'description': self.description,
            'year': self.year,
            'status': self.status,
            'category': self.category,
            'engine_type': self.engine_type,
            'num_engines': self.num_engines,
            'ifr_equipped': self.ifr_equipped,
            'gps': self.gps,
            'autopilot': self.autopilot,
            'rate_per_hour': self.rate_per_hour,
            'hobbs_time': self.hobbs_time,
            'tach_time': self.tach_time,
            'last_maintenance': self.last_maintenance.isoformat() if self.last_maintenance else None,
            'image_filename': self.image_filename,
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
    cancellation_reason = db.Column(db.String(50))  # weather, mechanical, personal, other
    cancellation_notes = db.Column(db.Text)
    weather_briefing = db.Column(db.JSON)  # Store weather briefing data
    notification_sent = db.Column(db.Boolean, default=False)
    recurring_booking_id = db.Column(db.Integer, db.ForeignKey('recurring_booking.id'), nullable=True)
    # Relationships
    check_in = db.relationship('CheckIn', backref='booking', uselist=False)
    check_out = db.relationship('CheckOut', backref='booking', uselist=False)
    invoice = db.relationship('Invoice', backref='booking', uselist=False)
    flight_log = db.relationship('FlightLog', backref='booking', uselist=False)
    
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
    
    @property
    def timestamp(self):
        return self.check_in_time

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

class WeatherMinima(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50))  # VFR, IFR, etc.
    ceiling_min = db.Column(db.Integer)  # Minimum ceiling in feet
    visibility_min = db.Column(db.Float)  # Minimum visibility in statute miles
    wind_max = db.Column(db.Integer)     # Maximum wind in knots
    crosswind_max = db.Column(db.Integer) # Maximum crosswind component
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FlightLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    pic_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sic_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    flight_date = db.Column(db.DateTime, nullable=False)
    route = db.Column(db.String(200))
    remarks = db.Column(db.Text)
    weather_conditions = db.Column(db.String(50))  # VFR, MVFR, IFR, LIFR
    ground_instruction = db.Column(db.Float)
    dual_received = db.Column(db.Float)
    pic_time = db.Column(db.Float)
    sic_time = db.Column(db.Float)
    cross_country = db.Column(db.Float)
    night = db.Column(db.Float)
    actual_instrument = db.Column(db.Float)
    simulated_instrument = db.Column(db.Float)
    landings_day = db.Column(db.Integer)
    landings_night = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Endorsement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(100), nullable=False)  # solo, BFR, IPC, etc.
    description = db.Column(db.Text, nullable=False)
    expiration = db.Column(db.DateTime, nullable=True)
    document_url = db.Column(db.String(500))  # URL to stored endorsement document
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50))  # medical, certificate, insurance, etc.
    filename = db.Column(db.String(255))
    url = db.Column(db.String(500))
    expiration = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    table_name = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer, nullable=False)
    changes = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WaitlistEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    aircraft_id = db.Column(db.Integer, db.ForeignKey('aircraft.id'), nullable=False)
    requested_date = db.Column(db.DateTime, nullable=False)
    time_preference = db.Column(db.String(20))  # morning, afternoon, evening
    duration_hours = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, fulfilled, expired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RecurringBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    aircraft_id = db.Column(db.Integer, db.ForeignKey('aircraft.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = db.Column(db.Time, nullable=False)
    duration_hours = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)