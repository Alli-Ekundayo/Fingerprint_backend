from extensions import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    """User model for teachers and administrators"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with courses (a teacher can teach multiple courses)
    courses = db.relationship('Course', backref='teacher', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Student(db.Model):
    """Student model"""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    fingerprints = db.relationship('Fingerprint', backref='student', lazy=True)
    attendances = db.relationship('Attendance', backref='student', lazy=True)
    
    # Many-to-many relationship with courses
    courses = db.relationship('Course', secondary='student_course', backref=db.backref('students', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Student {self.student_id} - {self.first_name} {self.last_name}>'


# Association table for many-to-many relationship between Student and Course
student_course = db.Table('student_course',
    db.Column('student_id', db.Integer, db.ForeignKey('student.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True)
)


class Course(db.Model):
    """Course model"""
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with attendance records
    attendances = db.relationship('Attendance', backref='course', lazy=True)
    
    def __repr__(self):
        return f'<Course {self.course_code} - {self.title}>'


class Attendance(db.Model):
    """Attendance model to log student presence in classes"""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', ondelete="CASCADE"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id', ondelete="CASCADE"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), default='present', nullable=False)  # 'present', 'absent', 'late'
    synced = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Attendance {self.student_id} - {self.course_id} - {self.timestamp}>'


class Fingerprint(db.Model):
    """Fingerprint data model to store fingerprint templates"""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    finger_id = db.Column(db.Integer, nullable=False)  # Usually 0-9 to represent different fingers
    template_data = db.Column(db.LargeBinary, nullable=False)  # Store the actual fingerprint template data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Fingerprint {self.student_id} - Finger {self.finger_id}>'
