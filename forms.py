from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional
from models import User, Student, Course

class LoginForm(FlaskForm):
    """Form for user login"""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    """Form for user registration"""
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    is_admin = BooleanField('Administrator')
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')


class StudentForm(FlaskForm):
    """Form for adding or editing a student"""
    student_id = StringField('Student ID', validators=[DataRequired(), Length(min=3, max=20)])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    courses = SelectField('Courses', coerce=int, validators=[Optional()])
    submit = SubmitField('Save Student')
    
    def validate_student_id(self, student_id):
        # Skip validation if student_id is unchanged during edit
        if hasattr(self, 'original_student_id') and self.original_student_id == student_id.data:
            return
            
        student = Student.query.filter_by(student_id=student_id.data).first()
        if student is not None:
            raise ValidationError('This Student ID is already in use.')
    
    def validate_email(self, email):
        # Skip validation if email is unchanged during edit
        if hasattr(self, 'original_email') and self.original_email == email.data:
            return
            
        if email.data:  # Only validate if email is provided
            student = Student.query.filter_by(email=email.data).first()
            if student is not None:
                raise ValidationError('This email is already in use.')


class CourseForm(FlaskForm):
    """Form for adding or editing a course"""
    course_code = StringField('Course Code', validators=[DataRequired(), Length(min=2, max=20)])
    title = StringField('Course Title', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Save Course')
    
    def validate_course_code(self, course_code):
        # Skip validation if course_code is unchanged during edit
        if hasattr(self, 'original_course_code') and self.original_course_code == course_code.data:
            return
            
        course = Course.query.filter_by(course_code=course_code.data).first()
        if course is not None:
            raise ValidationError('This Course Code is already in use.')


class EnrollmentForm(FlaskForm):
    """Form for enrolling students in courses"""
    student = SelectField('Student', coerce=int, validators=[DataRequired()])
    course = SelectField('Course', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Enroll Student')


class FingerprintEnrollForm(FlaskForm):
    """Form for enrolling a student's fingerprint"""
    student = SelectField('Student', coerce=int, validators=[DataRequired()])
    finger_id = SelectField('Finger', choices=[
        (0, 'Right Thumb'), (1, 'Right Index'), (2, 'Right Middle'), 
        (3, 'Right Ring'), (4, 'Right Little'),
        (5, 'Left Thumb'), (6, 'Left Index'), (7, 'Left Middle'), 
        (8, 'Left Ring'), (9, 'Left Little')
    ], coerce=int, validators=[DataRequired()])
    submit = SubmitField('Start Enrollment')


class AttendanceForm(FlaskForm):
    """Form for manually recording attendance"""
    student = SelectField('Student', coerce=int, validators=[DataRequired()])
    course = SelectField('Course', coerce=int, validators=[DataRequired()])
    status = SelectField('Status', choices=[
        ('present', 'Present'),
        ('late', 'Late'),
        ('absent', 'Absent')
    ], validators=[DataRequired()])
    submit = SubmitField('Record Attendance')


class SearchForm(FlaskForm):
    """Form for searching records"""
    query = StringField('Search', validators=[DataRequired()])
    submit = SubmitField('Search')
