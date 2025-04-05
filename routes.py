import logging
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from app import db
from models import User, Student, Course, Attendance, Fingerprint
from forms import (
    LoginForm, RegistrationForm, StudentForm, CourseForm, EnrollmentForm, 
    FingerprintEnrollForm, AttendanceForm, SearchForm
)
from fingerprint_sensor import FingerprintSensor
from attendance_manager import AttendanceManager

logger = logging.getLogger(__name__)

# Initialize fingerprint sensor
fingerprint_sensor = FingerprintSensor()
attendance_manager = AttendanceManager()

def register_routes(app):
    """Register all routes with the Flask application"""
    
    @app.route('/')
    def index():
        """Home page route"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('index.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login route"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
            
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            
            if user is None or not user.check_password(form.password.data):
                flash('Invalid username or password', 'danger')
                return redirect(url_for('login'))
                
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('dashboard')
                
            flash('Login successful', 'success')
            return redirect(next_page)
            
        return render_template('login.html', title='Sign In', form=form)
    
    @app.route('/logout')
    def logout():
        """User logout route"""
        logout_user()
        flash('You have been logged out', 'info')
        return redirect(url_for('index'))
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """User registration route"""
        # Check if this is the first user (make them admin)
        is_first_user = User.query.count() == 0
        
        form = RegistrationForm()
        if form.validate_on_submit():
            user = User(
                username=form.username.data,
                email=form.email.data,
                is_admin=is_first_user or form.is_admin.data
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
            
        return render_template('register.html', title='Register', form=form, is_first_user=is_first_user)
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Dashboard route showing attendance statistics"""
        # Get recent attendance data
        recent_attendance = Attendance.query.order_by(Attendance.timestamp.desc()).limit(10).all()
        
        # Get attendance statistics
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        today_attendance_count = Attendance.query.filter(
            Attendance.timestamp.between(today_start, today_end)
        ).count()
        
        # Get weekly attendance data for chart
        week_start = today - timedelta(days=today.weekday())
        week_dates = [(week_start + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
        
        weekly_data = []
        for day_date in week_dates:
            day_start = datetime.strptime(day_date, '%Y-%m-%d')
            day_end = day_start + timedelta(days=1)
            
            day_count = Attendance.query.filter(
                Attendance.timestamp.between(day_start, day_end),
                Attendance.status == 'present'
            ).count()
            
            weekly_data.append({
                'date': day_date,
                'count': day_count
            })
        
        # Get course statistics
        courses = Course.query.all()
        course_stats = []
        
        for course in courses:
            total = Attendance.query.filter_by(course_id=course.id).count()
            present = Attendance.query.filter_by(course_id=course.id, status='present').count()
            
            attendance_rate = (present / total) * 100 if total > 0 else 0
            
            course_stats.append({
                'course': course,
                'total': total,
                'present': present,
                'rate': round(attendance_rate, 1)
            })
        
        return render_template(
            'dashboard.html', 
            title='Dashboard',
            recent_attendance=recent_attendance,
            today_attendance=today_attendance_count,
            weekly_data=weekly_data,
            course_stats=course_stats
        )
    
    @app.route('/students', methods=['GET'])
    @login_required
    def students():
        """List all students"""
        search_form = SearchForm()
        all_students = Student.query.order_by(Student.last_name).all()
        return render_template('students.html', title='Students', students=all_students, form=search_form)
    
    @app.route('/students/add', methods=['GET', 'POST'])
    @login_required
    def add_student():
        """Add a new student"""
        form = StudentForm()
        form.courses.choices = [(c.id, f"{c.course_code} - {c.title}") for c in Course.query.all()]
        
        if form.validate_on_submit():
            student = Student(
                student_id=form.student_id.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                email=form.email.data
            )
            
            # Add to course if selected
            if form.courses.data:
                course = Course.query.get(form.courses.data)
                if course:
                    student.courses.append(course)
            
            db.session.add(student)
            db.session.commit()
            
            flash(f'Student {student.first_name} {student.last_name} has been added!', 'success')
            return redirect(url_for('students'))
            
        return render_template('students.html', title='Add Student', form=form, add_mode=True)
    
    @app.route('/students/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_student(id):
        """Edit a student"""
        student = Student.query.get_or_404(id)
        form = StudentForm(obj=student)
        form.courses.choices = [(c.id, f"{c.course_code} - {c.title}") for c in Course.query.all()]
        
        # Store original values for validation
        form.original_student_id = student.student_id
        form.original_email = student.email
        
        if form.validate_on_submit():
            student.student_id = form.student_id.data
            student.first_name = form.first_name.data
            student.last_name = form.last_name.data
            student.email = form.email.data
            
            # Update course enrollment if selected
            if form.courses.data:
                course = Course.query.get(form.courses.data)
                if course and course not in student.courses:
                    student.courses.append(course)
            
            db.session.commit()
            flash(f'Student {student.first_name} {student.last_name} has been updated!', 'success')
            return redirect(url_for('students'))
            
        return render_template('students.html', title='Edit Student', form=form, student=student)
    
    @app.route('/students/delete/<int:id>', methods=['POST'])
    @login_required
    def delete_student(id):
        """Delete a student"""
        student = Student.query.get_or_404(id)
        db.session.delete(student)
        db.session.commit()
        flash(f'Student {student.first_name} {student.last_name} has been deleted!', 'success')
        return redirect(url_for('students'))
    
    @app.route('/courses', methods=['GET'])
    @login_required
    def courses():
        """List all courses"""
        all_courses = Course.query.all()
        return render_template('courses.html', title='Courses', courses=all_courses)
    
    @app.route('/courses/add', methods=['GET', 'POST'])
    @login_required
    def add_course():
        """Add a new course"""
        form = CourseForm()
        
        if form.validate_on_submit():
            course = Course(
                course_code=form.course_code.data,
                title=form.title.data,
                description=form.description.data,
                user_id=current_user.id  # Assign to current teacher/admin
            )
            
            db.session.add(course)
            db.session.commit()
            
            flash(f'Course {course.title} has been added!', 'success')
            return redirect(url_for('courses'))
            
        return render_template('courses.html', title='Add Course', form=form, add_mode=True)
    
    @app.route('/enroll', methods=['GET', 'POST'])
    @login_required
    def enroll():
        """Fingerprint enrollment page"""
        form = FingerprintEnrollForm()
        form.student.choices = [(s.id, f"{s.student_id} - {s.first_name} {s.last_name}") 
                               for s in Student.query.order_by(Student.last_name).all()]
        
        if form.validate_on_submit():
            student = Student.query.get(form.student.data)
            finger_id = form.finger_id.data
            
            # Start the enrollment process
            session['enrollment_student_id'] = student.id
            session['enrollment_finger_id'] = finger_id
            
            flash(f'Place {student.first_name}\'s finger on the sensor to begin enrollment...', 'info')
            
            # In a real system, this would trigger the fingerprint sensor to start enrollment
            fingerprint_sensor.start_enrollment()
            
            return render_template('enroll.html', title='Fingerprint Enrollment', 
                                  form=form, enrolling=True, student=student)
        
        return render_template('enroll.html', title='Fingerprint Enrollment', form=form)
    
    @app.route('/enroll/status', methods=['GET'])
    @login_required
    def enrollment_status():
        """AJAX endpoint to check enrollment status"""
        if 'enrollment_student_id' not in session:
            return jsonify({'status': 'error', 'message': 'No enrollment in progress'})
        
        # Check with the fingerprint sensor for status
        status = fingerprint_sensor.get_enrollment_status()
        
        if status['status'] == 'complete':
            # If enrollment is complete, save the fingerprint
            student_id = session.pop('enrollment_student_id', None)
            finger_id = session.pop('enrollment_finger_id', None)
            
            if student_id and finger_id is not None:
                student = Student.query.get(student_id)
                
                # Check if this finger is already enrolled
                existing = Fingerprint.query.filter_by(
                    student_id=student.id, 
                    finger_id=finger_id
                ).first()
                
                if existing:
                    # Update existing fingerprint
                    existing.template_data = status['data']
                    db.session.commit()
                else:
                    # Create new fingerprint record
                    fingerprint = Fingerprint(
                        student_id=student.id,
                        finger_id=finger_id,
                        template_data=status['data']
                    )
                    db.session.add(fingerprint)
                    db.session.commit()
        
        return jsonify(status)
    
    @app.route('/attendance', methods=['GET', 'POST'])
    @login_required
    def attendance():
        """View and record attendance"""
        # Form for manual attendance recording
        form = AttendanceForm()
        form.student.choices = [(s.id, f"{s.student_id} - {s.first_name} {s.last_name}") 
                               for s in Student.query.order_by(Student.last_name).all()]
        form.course.choices = [(c.id, f"{c.course_code} - {c.title}") 
                               for c in Course.query.all()]
        
        if form.validate_on_submit():
            # Record manual attendance
            attendance = Attendance(
                student_id=form.student.data,
                course_id=form.course.data,
                status=form.status.data,
                timestamp=datetime.utcnow()
            )
            
            db.session.add(attendance)
            db.session.commit()
            
            student = Student.query.get(form.student.data)
            course = Course.query.get(form.course.data)
            
            flash(f'Attendance recorded for {student.first_name} {student.last_name} in {course.title}', 'success')
            return redirect(url_for('attendance'))
        
        # Get attendance records for display
        attendance_records = (Attendance.query
                              .join(Student)
                              .join(Course)
                              .order_by(Attendance.timestamp.desc())
                              .limit(100)
                              .all())
        
        return render_template('attendance.html', title='Attendance', 
                               form=form, attendance_records=attendance_records)
    
    @app.route('/scan', methods=['GET'])
    @login_required
    def scan():
        """Page to scan fingerprint for attendance"""
        courses = Course.query.all()
        return render_template('scan.html', title='Scan Fingerprint', courses=courses)
    
    @app.route('/scan/verify', methods=['POST'])
    @login_required
    def verify_fingerprint():
        """AJAX endpoint to verify a fingerprint and record attendance"""
        course_id = request.form.get('course_id')
        
        if not course_id:
            return jsonify({'status': 'error', 'message': 'Course is required'})
        
        # In a real system, this would trigger the fingerprint sensor to scan
        # and compare against stored templates
        result = fingerprint_sensor.verify_fingerprint()
        
        if result['status'] == 'match':
            # Record attendance for the matched student
            attendance = attendance_manager.record_attendance(
                student_id=result['student_id'],
                course_id=int(course_id),
                status='present'
            )
            
            if attendance:
                student = Student.query.get(result['student_id'])
                return jsonify({
                    'status': 'success', 
                    'message': f'Attendance recorded for {student.first_name} {student.last_name}'
                })
            else:
                return jsonify({'status': 'error', 'message': 'Failed to record attendance'})
        else:
            return jsonify({'status': 'error', 'message': result['message']})
    
    @app.route('/sync', methods=['GET'])
    @login_required
    def sync_data():
        """Sync attendance data with central server"""
        # This would handle the sync operation with the remote server
        # For our demo, we'll just simulate success
        result = attendance_manager.sync_attendance_data()
        
        if result['status'] == 'success':
            flash(f'Successfully synced {result["count"]} attendance records', 'success')
        else:
            flash(f'Sync failed: {result["message"]}', 'danger')
            
        return redirect(url_for('attendance'))
