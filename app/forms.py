from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, DateTimeField, FloatField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional, Length
from app.models import User
from datetime import datetime

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
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
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    password = PasswordField('New Password', validators=[Optional(), Length(min=6)])
    password2 = PasswordField('Repeat New Password', validators=[Optional(), EqualTo('password')])
    submit = SubmitField('Update Settings') 