from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, DateTimeField, FloatField, TextAreaField, SelectMultipleField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional, Length
from app.models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    name = StringField('Name', validators=[DataRequired()])
    phone = StringField('Phone')
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    student_id = StringField('Student ID')
    certificates = StringField('Certificates')
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

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user and not self.obj:  # Only validate on create
            raise ValidationError('Email already registered')

class AircraftForm(FlaskForm):
    registration = StringField('Registration', validators=[DataRequired()])
    make_model = StringField('Make/Model', validators=[DataRequired()])
    year = IntegerField('Year', validators=[DataRequired()])
    status = SelectField('Status', choices=[
        ('available', 'Available'),
        ('maintenance', 'Maintenance'),
        ('inactive', 'Inactive')
    ])
    submit = SubmitField('Submit')

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
    maintenance_type = SelectField('Maintenance Type', validators=[DataRequired()], coerce=int)
    performed_at = DateTimeField('Performed At', validators=[DataRequired()], format='%Y-%m-%d %H:%M')
    performed_by = SelectField('Performed By', validators=[DataRequired()], coerce=int)
    hobbs_hours = FloatField('Hobbs Hours', validators=[Optional()])
    tach_hours = FloatField('Tach Hours', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Submit')

class SquawkForm(FlaskForm):
    description = TextAreaField('Description', validators=[DataRequired()])
    status = SelectField('Status',
        choices=[
            ('open', 'Open'),
            ('in_progress', 'In Progress'),
            ('resolved', 'Resolved')
        ],
        validators=[DataRequired()]
    )
    resolution_notes = TextAreaField('Resolution Notes', validators=[Optional()])
    submit = SubmitField('Submit')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('new_password')]) 