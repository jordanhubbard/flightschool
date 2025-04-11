from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, DateTimeField, FloatField, TextAreaField, SelectMultipleField, IntegerField, FileField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional, Length
from app.models import User
from datetime import datetime
import re

class LoginForm(FlaskForm):
    """Login form."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        if not self.csrf_token.current_token:
            self.csrf_token._get_token()

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    phone = StringField('Phone', validators=[Optional()])
    student_id = StringField('Student ID', validators=[Optional()])
    certificates = StringField('Certificates', validators=[Optional()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class BookingForm(FlaskForm):
    aircraft = SelectField('Aircraft', validators=[DataRequired()], coerce=int)
    instructor = SelectField('Instructor', validators=[DataRequired()], coerce=int)
    start_time = DateTimeField('Start Time', validators=[DataRequired()], format='%Y-%m-%d %H:%M')
    end_time = DateTimeField('End Time', validators=[DataRequired()], format='%Y-%m-%d %H:%M')
    submit = SubmitField('Book Flight')

class GoogleCalendarSettingsForm(FlaskForm):
    enabled = BooleanField('Enable Google Calendar Integration')
    calendar_id = StringField('Calendar ID', validators=[Optional()])
    submit = SubmitField('Save Settings')

class FlightCheckoutForm(FlaskForm):
    hobbs = FloatField('Hobbs Time', validators=[DataRequired()])
    tach = FloatField('Tach Time', validators=[DataRequired()])
    squawks = TextAreaField('Squawks', validators=[Optional()])
    comments = TextAreaField('Comments', validators=[Optional()])
    agree_to_fly = BooleanField('I agree to fly this aircraft', validators=[DataRequired()])
    submit = SubmitField('Check Out')

class FlightCheckinForm(FlaskForm):
    hobbs = FloatField('Hobbs Time', validators=[DataRequired()])
    tach = FloatField('Tach Time', validators=[DataRequired()])
    squawks = TextAreaField('Squawks', validators=[Optional()])
    comments = TextAreaField('Comments', validators=[Optional()])
    submit = SubmitField('Check In')

class UserForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    phone = StringField('Phone')
    status = SelectField('Status', choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('on_leave', 'On Leave')
    ])
    certificates = StringField('Certificates')
    student_id = StringField('Student ID')
    
    def __init__(self, *args, **kwargs):
        self.obj = kwargs.get('obj', None)
        super(UserForm, self).__init__(*args, **kwargs)

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user and not self.obj:  # Only validate on create
            raise ValidationError('Email already registered')

class AircraftForm(FlaskForm):
    registration = StringField('Tail Number', validators=[DataRequired()])
    make = StringField('Make', validators=[DataRequired()])
    model = StringField('Model', validators=[DataRequired()])
    year = IntegerField('Year', validators=[Optional()])
    description = TextAreaField('Description', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('available', 'Available'),
        ('maintenance', 'In Maintenance'),
        ('retired', 'Retired')
    ], validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('single_engine_land', 'Single Engine Land'),
        ('multi_engine_land', 'Multi Engine Land'),
        ('single_engine_sea', 'Single Engine Sea'),
        ('multi_engine_sea', 'Multi Engine Sea'),
        ('helicopter', 'Helicopter')
    ], validators=[Optional()])
    engine_type = SelectField('Engine Type', choices=[
        ('piston', 'Piston'),
        ('turboprop', 'Turboprop'),
        ('jet', 'Jet')
    ], validators=[Optional()])
    num_engines = IntegerField('Number of Engines', default=1, validators=[Optional()])
    ifr_equipped = BooleanField('IFR Equipped')
    gps = BooleanField('GPS')
    autopilot = BooleanField('Autopilot')
    rate_per_hour = FloatField('Hourly Rate', validators=[DataRequired()])
    hobbs_time = FloatField('Current Hobbs Time', validators=[Optional()])
    tach_time = FloatField('Current Tach Time', validators=[Optional()])
    last_maintenance = DateTimeField('Last Maintenance Date', validators=[Optional()], format='%Y-%m-%d')
    image = FileField('Aircraft Image', validators=[Optional()])
    submit = SubmitField('Submit')
    
    def validate_registration(self, field):
        # Ensure tail number follows N-number format (N followed by digits)
        if not re.match(r'^N\d+[A-Z]*$', field.data):
            raise ValidationError('Tail number must be in N-number format (e.g., N12345)')

class InstructorForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    phone = StringField('Phone', validators=[Optional()])
    password = PasswordField('Password', validators=[Optional()])
    certificates = StringField('Certificates', validators=[Optional()], description='Comma-separated list of certificates (e.g., CFI, CFII)')
    status = SelectField('Status',
        choices=[
            ('active', 'Active'),
            ('inactive', 'Inactive')
        ],
        validators=[DataRequired()]
    )
    submit = SubmitField('Submit')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None and user.id != getattr(self, '_user_id', None):
            raise ValidationError('Email already registered.')

class MaintenanceTypeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    interval_days = FloatField('Calendar Interval (days)', validators=[Optional()])
    interval_hours = FloatField('Operating Hours Interval', validators=[Optional()])
    submit = SubmitField('Submit')

class MaintenanceRecordForm(FlaskForm):
    maintenance_type = SelectField('Maintenance Type', coerce=int, validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    hobbs_hours = FloatField('Hobbs Hours', validators=[Optional()])
    tach_hours = FloatField('Tach Hours', validators=[Optional()])
    submit = SubmitField('Submit')

class SquawkForm(FlaskForm):
    description = TextAreaField('Description', validators=[DataRequired()])
    status = SelectField('Status', choices=[
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved')
    ], validators=[DataRequired()])
    resolution_notes = TextAreaField('Resolution Notes', validators=[Optional()])
    submit = SubmitField('Submit')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('new_password')])

class CheckInForm(FlaskForm):
    hobbs_start = FloatField('Hobbs Start Time', validators=[DataRequired()])
    tach_start = FloatField('Tach Start Time', validators=[DataRequired()])
    instructor_start_time = DateTimeField('Instructor Start Time', validators=[Optional()])
    notes = TextAreaField('Notes')
    submit = SubmitField('Check In')

class CheckOutForm(FlaskForm):
    hobbs_end = FloatField('Hobbs End Time', validators=[DataRequired()])
    tach_end = FloatField('Tach End Time', validators=[DataRequired()])
    instructor_end_time = DateTimeField('Instructor End Time', validators=[Optional()])
    notes = TextAreaField('Notes')
    submit = SubmitField('Check Out')

class InvoiceForm(FlaskForm):
    invoice_number = StringField('Invoice Number', validators=[DataRequired()])
    aircraft_rate = FloatField('Aircraft Rate per Hour', validators=[DataRequired()])
    instructor_rate = FloatField('Instructor Rate per Hour', validators=[Optional()])
    aircraft_time = FloatField('Total Aircraft Time', validators=[DataRequired()])
    instructor_time = FloatField('Total Instructor Time', validators=[Optional()])
    notes = TextAreaField('Notes')
    submit = SubmitField('Generate Invoice')

class AccountSettingsForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    phone = StringField('Phone', validators=[Optional()])
    address = StringField('Address', validators=[Optional()])
    password = PasswordField('New Password', validators=[Optional()])
    password2 = PasswordField('Repeat New Password', validators=[EqualTo('password')])
    submit = SubmitField('Update Settings')
