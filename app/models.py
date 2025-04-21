from flask_login import UserMixin, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask import url_for
from app import db, login_manager


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
    # Full name, computed from first_name and last_name
    name = db.Column(db.String(128))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(256))
    password_hash = db.Column(db.String(128))
    # student, instructor, admin
    role = db.Column(db.String(20), default='student')
    is_admin = db.Column(db.Boolean, default=False)
    is_instructor = db.Column(db.Boolean, default=False)
    student_id = db.Column(db.String(20), unique=True)
    certificates = db.Column(db.String(200))
    # active, unavailable, inactive
    status = db.Column(db.String(20), default='active')
    # Instructor rate per hour
    instructor_rate_per_hour = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Google Calendar integration
    # Store JSON credentials
    google_calendar_credentials = db.Column(db.Text, nullable=True)
    google_calendar_enabled = db.Column(db.Boolean, default=False)
    google_calendar_token = db.Column(db.String(500))
    google_calendar_refresh_token = db.Column(db.String(500))
    google_calendar_token_expiry = db.Column(db.DateTime)
    google_calendar_id = db.Column(db.String(100))

    # Relationships
    bookings_as_student = db.relationship(
        'Booking',
        backref='student',
        lazy='dynamic',
        foreign_keys='Booking.student_id'
    )
    bookings_as_instructor = db.relationship(
        'Booking',
        backref='instructor',
        lazy='dynamic',
        foreign_keys='Booking.instructor_id'
    )
    check_ins = db.relationship(
        'CheckIn',
        backref='instructor',
        lazy='dynamic'
    )
    check_outs = db.relationship(
        'CheckOut',
        backref='instructor',
        lazy='dynamic'
    )
    created_maintenance_types = db.relationship(
        'MaintenanceType',
        backref='created_by'
    )
    performed_maintenance = db.relationship(
        'MaintenanceRecord',
        backref='performed_by'
    )
    reported_squawks = db.relationship(
        'Squawk',
        foreign_keys='Squawk.reported_by_id',
        backref='reported_by'
    )
    resolved_squawks = db.relationship(
        'Squawk',
        foreign_keys='Squawk.resolved_by_id',
        backref='resolved_by'
    )
    flight_logs = db.relationship(
        'FlightLog',
        backref='pilot',
        foreign_keys='FlightLog.pic_id'
    )
    endorsements_given = db.relationship(
        'Endorsement',
        backref='instructor',
        foreign_keys='Endorsement.instructor_id'
    )
    endorsements_received = db.relationship(
        'Endorsement',
        backref='student',
        foreign_keys='Endorsement.student_id'
    )
    documents = db.relationship('Document', backref='user')
    audit_logs = db.relationship('AuditLog', backref='user')
    waitlist_entries = db.relationship(
        'WaitlistEntry',
        backref='student',
        foreign_keys='WaitlistEntry.student_id'
    )
    recurring_bookings = db.relationship(
        'RecurringBooking',
        backref='student',
        foreign_keys='RecurringBooking.student_id'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return self.email or "Unknown"

    def __repr__(self):
        return f'<User {self.email}>'

    @property
    def is_active(self):
        return self.status == 'active'


class MaintenanceType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    # Calendar interval in days
    interval_days = db.Column(db.Integer)
    # Operating hours interval
    interval_hours = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    # Relationships
    maintenance_records = db.relationship(
        'MaintenanceRecord',
        backref='maintenance_type',
        lazy='dynamic'
    )

    def __repr__(self):
        return f'<MaintenanceType {self.name}>'


class EquipmentStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aircraft_id = db.Column(
        db.Integer,
        db.ForeignKey('aircraft.id'),
        nullable=False
    )
    # radio, nav, transponder, etc.
    equipment_type = db.Column(db.String(50), nullable=False)
    # Specific equipment name/model
    equipment_name = db.Column(db.String(100), nullable=False)
    # operational, degraded, inoperative
    status = db.Column(db.String(20), default='operational')
    last_inspection = db.Column(db.DateTime)
    next_inspection = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    maintenance_records = db.relationship(
        'MaintenanceRecord',
        backref='equipment',
        primaryjoin=(
            "and_(MaintenanceRecord.aircraft_id==EquipmentStatus.aircraft_id, "
            "MaintenanceRecord.equipment_id==EquipmentStatus.id)"
        )
    )

    def __repr__(self):
        return (
            f'<EquipmentStatus {self.equipment_type} - '
            f'{self.equipment_name}>'
        )

    @property
    def is_operational(self):
        return self.status == 'operational'

    @property
    def requires_inspection(self):
        if self.next_inspection:
            return datetime.utcnow() >= self.next_inspection
        return False


class MaintenanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aircraft_id = db.Column(
        db.Integer,
        db.ForeignKey('aircraft.id'),
        nullable=False
    )
    maintenance_type_id = db.Column(
        db.Integer,
        db.ForeignKey('maintenance_type.id'),
        nullable=False
    )
    equipment_id = db.Column(
        db.Integer,
        db.ForeignKey('equipment_status.id'),
        nullable=True
    )
    performed_at = db.Column(db.DateTime, nullable=False)
    performed_by_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )
    notes = db.Column(db.Text)
    hobbs_hours = db.Column(db.Float)
    tach_hours = db.Column(db.Float)
    # List of parts replaced
    parts_replaced = db.Column(db.JSON)
    # Hours spent on maintenance
    labor_hours = db.Column(db.Float)
    # Total cost of maintenance
    cost = db.Column(db.Float)
    # When this maintenance is due again
    next_due_date = db.Column(db.DateTime)
    # Hours until this maintenance is due again
    next_due_hours = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Removed property: aircraft (conflicts with SQLAlchemy relationship backref)

    @property
    def maintenance_type_obj(self):
        return MaintenanceType.query.get(self.maintenance_type_id)

    def __repr__(self):
        return f'<MaintenanceRecord {self.id}>'


class Squawk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aircraft_id = db.Column(
        db.Integer,
        db.ForeignKey('aircraft.id'),
        nullable=False
    )
    description = db.Column(db.Text, nullable=False)
    reported_by_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )
    # open, in_progress, resolved
    status = db.Column(db.String(20), default='open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    resolved_at = db.Column(db.DateTime)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    resolution_notes = db.Column(db.Text)

    def __repr__(self):
        return f'<Squawk {self.id}>'


class Aircraft(db.Model):
    """Aircraft model."""
    id = db.Column(db.Integer, primary_key=True)
    registration = db.Column(db.String(10), unique=True, nullable=False)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer)
    description = db.Column(db.Text)
    # available, maintenance, retired
    status = db.Column(db.String(20), default='available')
    # single_engine_land, multi_engine_land, etc.
    category = db.Column(db.String(50))
    # piston, turboprop, jet
    engine_type = db.Column(db.String(20))
    num_engines = db.Column(db.Integer, default=1)
    ifr_equipped = db.Column(db.Boolean, default=False)
    gps = db.Column(db.Boolean, default=False)
    autopilot = db.Column(db.Boolean, default=False)
    rate_per_hour = db.Column(db.Float, nullable=False)
    hobbs_time = db.Column(db.Float)
    tach_time = db.Column(db.Float)
    last_maintenance = db.Column(db.DateTime)
    image_filename = db.Column(db.String(255))

    # Relationships
    recurring_bookings = db.relationship(
        'RecurringBooking',
        backref='aircraft'
    )
    waitlist_entries = db.relationship(
        'WaitlistEntry',
        backref='aircraft'
    )
    maintenance_records = db.relationship(
        'MaintenanceRecord',
        backref='aircraft',
        lazy=True
    )
    squawks = db.relationship('Squawk', backref='aircraft', lazy=True)
    bookings = db.relationship('Booking', backref='aircraft', lazy='dynamic')
    check_ins = db.relationship('CheckIn', backref='aircraft', lazy='dynamic')
    equipment_items = db.relationship(
        'EquipmentStatus',
        backref=db.backref('parent_aircraft', lazy=True)
    )
    flight_logs = db.relationship(
        'FlightLog',
        backref='aircraft',
        lazy='dynamic'
    )

    @property
    def image_url(self):
        """Get the URL for the aircraft's image."""
        if self.image_filename:
            return url_for(
                'static',
                filename=f'images/aircraft/{self.image_filename}'
            )
        # Default images based on category and engine type
        if self.category == 'single_engine_land':
            if self.engine_type == 'piston':
                return url_for(
                    'static',
                    filename='images/aircraft/cessna172.jpg'
                )
            elif self.engine_type == 'turboprop':
                return url_for(
                    'static',
                    filename='images/aircraft/tbm930.jpg'
                )
        elif self.category == 'multi_engine_land':
            if self.engine_type == 'piston':
                return url_for(
                    'static',
                    filename='images/aircraft/baron58.jpg'
                )
            elif self.engine_type == 'turboprop':
                return url_for(
                    'static',
                    filename='images/aircraft/kingair350.jpg'
                )
            elif self.engine_type == 'jet':
                return url_for(
                    'static',
                    filename='images/aircraft/citation.jpg'
                )
        return url_for('static', filename='images/aircraft/default.jpg')

    @property
    def display_name(self):
        """Return a display name for the aircraft."""
        return f"{self.registration} ({self.make} {self.model})"

    @property
    def time_to_maintenance(self):
        """Return hours until next maintenance is due."""
        if not self.hobbs_time or not self.last_maintenance:
            return None
        return self.hobbs_time - self.last_maintenance

    @property
    def days_to_maintenance(self):
        """Return days until next maintenance is due."""
        if not self.last_maintenance:
            return None
        return (datetime.utcnow() - self.last_maintenance).days

    @property
    def is_available(self):
        """Check if aircraft is available for booking."""
        return self.status == 'available'

    def __repr__(self):
        return f'<Aircraft {self.registration}>'


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )
    instructor_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=True
    )
    aircraft_id = db.Column(
        db.Integer,
        db.ForeignKey('aircraft.id'),
        nullable=False
    )
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')
    booking_type = db.Column(db.String(50), default='training')
    lesson_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    google_calendar_event_id = db.Column(db.String(255), nullable=True)
    cancellation_reason = db.Column(db.String(50))
    cancellation_notes = db.Column(db.Text)
    weather_briefing = db.Column(db.JSON)
    weather_conditions = db.Column(db.JSON)
    notification_sent = db.Column(db.Boolean, default=False)
    recurring_booking_id = db.Column(
        db.Integer,
        db.ForeignKey('recurring_booking.id'),
        nullable=True
    )
    notes = db.Column(db.Text)

    # Relationships
    check_in = db.relationship('CheckIn', backref='booking', uselist=False)
    check_out = db.relationship('CheckOut', backref='booking', uselist=False)
    invoice = db.relationship('Invoice', backref='booking', uselist=False)
    flight_log = db.relationship('FlightLog', backref='booking', uselist=False)

    def __repr__(self):
        return f'<Booking {self.id}>'


class CheckIn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(
        db.Integer,
        db.ForeignKey('booking.id'),
        nullable=False
    )
    aircraft_id = db.Column(
        db.Integer,
        db.ForeignKey('aircraft.id'),
        nullable=False
    )
    instructor_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=True
    )
    check_in_time = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    hobbs_start = db.Column(db.Float, nullable=False)
    tach_start = db.Column(db.Float, nullable=False)
    instructor_start_time = db.Column(db.DateTime, nullable=True)
    fuel_level = db.Column(db.String(20), nullable=False)
    oil_level = db.Column(db.Float, nullable=False)
    preflight_checklist_completed = db.Column(db.Boolean, default=False)
    weather_conditions_acceptable = db.Column(db.Boolean, default=False)
    equipment_status = db.Column(db.JSON)
    notes = db.Column(db.Text)

    @property
    def timestamp(self):
        return self.check_in_time

    def __repr__(self):
        return f'<CheckIn {self.id}>'


class CheckOut(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(
        db.Integer,
        db.ForeignKey('booking.id'),
        nullable=False
    )
    aircraft_id = db.Column(
        db.Integer,
        db.ForeignKey('aircraft.id'),
        nullable=False
    )
    instructor_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=True
    )
    check_out_time = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    hobbs_end = db.Column(db.Float, nullable=False)
    tach_end = db.Column(db.Float, nullable=False)
    instructor_end_time = db.Column(db.DateTime, nullable=True)
    total_aircraft_time = db.Column(db.Float, nullable=False)
    total_instructor_time = db.Column(db.Float, nullable=True)
    fuel_level_end = db.Column(db.String(20), nullable=False)
    fuel_added = db.Column(db.Float)
    oil_added = db.Column(db.Float)
    number_landings = db.Column(db.Integer, default=0)
    post_flight_checklist_completed = db.Column(db.Boolean, default=False)
    equipment_issues = db.Column(db.JSON)
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<CheckOut {self.id}>'


class FlightLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(
        db.Integer,
        db.ForeignKey('booking.id'),
        nullable=False
    )
    aircraft_id = db.Column(
        db.Integer,
        db.ForeignKey('aircraft.id'),
        nullable=False
    )
    pic_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )
    sic_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=True
    )
    flight_date = db.Column(db.DateTime, nullable=False)
    route = db.Column(db.String(200))
    departure_airport = db.Column(db.String(10))
    arrival_airport = db.Column(db.String(10))
    alternate_airport = db.Column(db.String(10))
    remarks = db.Column(db.Text)
    # VFR, MVFR, IFR, LIFR
    weather_conditions = db.Column(db.String(50))
    # Day VFR, Night VFR, IFR
    flight_conditions = db.Column(db.String(50))
    ground_instruction = db.Column(db.Float)
    dual_received = db.Column(db.Float)
    pic_time = db.Column(db.Float)
    sic_time = db.Column(db.Float)
    cross_country = db.Column(db.Float)
    night = db.Column(db.Float)
    actual_instrument = db.Column(db.Float)
    simulated_instrument = db.Column(db.Float)
    hood_time = db.Column(db.Float)
    landings_day = db.Column(db.Integer)
    landings_night = db.Column(db.Integer)
    # Number of approaches performed
    approaches = db.Column(db.Integer)
    # Types of approaches performed
    approach_types = db.Column(db.JSON)
    # Number of holds performed
    holds = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f'<FlightLog {self.id}>'


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(
        db.Integer,
        db.ForeignKey('booking.id'),
        nullable=False
    )
    aircraft_id = db.Column(
        db.Integer,
        db.ForeignKey('aircraft.id'),
        nullable=False
    )
    student_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )
    instructor_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=True
    )
    invoice_number = db.Column(db.String(20), unique=True, nullable=False)
    invoice_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    aircraft_rate = db.Column(db.Float, nullable=False)
    instructor_rate = db.Column(db.Float, nullable=True)
    aircraft_time = db.Column(db.Float, nullable=False)
    instructor_time = db.Column(db.Float, nullable=True)
    aircraft_total = db.Column(db.Float, nullable=False)
    instructor_total = db.Column(db.Float, nullable=True)
    total_amount = db.Column(db.Float, nullable=False)
    # pending, paid, overdue
    status = db.Column(db.String(20), default='pending')
    payment_date = db.Column(db.DateTime)
    payment_method = db.Column(db.String(50))
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'


class WeatherMinima(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # VFR, IFR, etc.
    category = db.Column(db.String(50))
    # Minimum ceiling in feet
    ceiling_min = db.Column(db.Integer)
    # Minimum visibility in statute miles
    visibility_min = db.Column(db.Float)
    # Maximum wind in knots
    wind_max = db.Column(db.Integer)
    # Maximum crosswind component
    crosswind_max = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<WeatherMinima {self.category}: ceiling {self.ceiling_min}, vis {self.visibility_min}>"


class Endorsement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )
    instructor_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )
    # solo, BFR, IPC, etc.
    type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    expiration = db.Column(db.DateTime, nullable=True)
    # URL to stored endorsement document
    document_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Endorsement {self.id}>'


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )
    # medical, certificate, insurance, etc.
    type = db.Column(db.String(50))
    filename = db.Column(db.String(255))
    url = db.Column(db.String(500))
    expiration = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f'<Document {self.id}>'


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )
    action = db.Column(db.String(50), nullable=False)
    table_name = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer, nullable=False)
    changes = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AuditLog {self.id}>'


class WaitlistEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )
    instructor_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=True
    )
    aircraft_id = db.Column(
        db.Integer,
        db.ForeignKey('aircraft.id'),
        nullable=False
    )
    requested_date = db.Column(db.DateTime, nullable=False)
    # morning, afternoon, evening
    time_preference = db.Column(db.String(20))
    duration_hours = db.Column(db.Float, nullable=False)
    # active, fulfilled, expired
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<WaitlistEntry {self.id}>'


class RecurringBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )
    instructor_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=True
    )
    aircraft_id = db.Column(
        db.Integer,
        db.ForeignKey('aircraft.id'),
        nullable=False
    )
    # 0=Monday, 6=Sunday
    day_of_week = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    duration_hours = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<RecurringBooking {self.id}>'
