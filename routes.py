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
from fingerprint_sensor_module import FingerPrintSensor
from attendance_manager import AttendanceManager

logger = logging.getLogger(__name__)

# Initialize fingerprint sensor with ESP32 IP address
fingerprint_sensor = FingerPrintSensor("192.168.43.215")  # Replace with your ESP32's IP
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
        try:
            student = Student.query.get_or_404(id)
            
            # First delete all fingerprints associated with the student
            Fingerprint.query.filter_by(student_id=student.id).delete()
            
            # Then delete all attendance records associated with the student
            Attendance.query.filter_by(student_id=student.id).delete()
            
            # Remove the student from all courses (many-to-many relationship)
            student.courses = []
            
            # Finally delete the student
            db.session.delete(student)
            db.session.commit()
            
            flash(f'Student {student.first_name} {student.last_name} has been deleted!', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting student {id}: {str(e)}")
            flash(f'Failed to delete student. Error: {str(e)}', 'danger')
        
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
        
    @app.route('/courses/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_course(id):
        """Edit a course"""
        course = Course.query.get_or_404(id)
        form = CourseForm()
        
        # Only the creator or an admin can edit the course
        if course.user_id != current_user.id and not current_user.is_admin:
            flash('You do not have permission to edit this course.', 'danger')
            return redirect(url_for('courses'))
            
        if form.validate_on_submit():
            course.course_code = form.course_code.data
            course.title = form.title.data
            course.description = form.description.data
            
            db.session.commit()
            flash(f'Course {course.title} has been updated!', 'success')
            return redirect(url_for('courses'))
            
        # Pre-populate form with existing data
        if request.method == 'GET':
            form.course_code.data = course.course_code
            form.title.data = course.title
            form.description.data = course.description
            
        return render_template('courses.html', title='Edit Course', 
                              form=form, edit_mode=True, course=course)
                              
    @app.route('/courses/manage_students/<int:id>', methods=['GET', 'POST'])
    @login_required
    def manage_course_students(id):
        """Manage students enrolled in a course"""
        course = Course.query.get_or_404(id)
        form = EnrollmentForm()
        
        # Populate student choices - exclude already enrolled students
        enrolled_student_ids = [s.id for s in course.students]
        available_students = Student.query.filter(~Student.id.in_(enrolled_student_ids) if enrolled_student_ids else True).all()
        
        form.student.choices = [(s.id, f"{s.student_id} - {s.first_name} {s.last_name}") 
                               for s in available_students]
        
        if form.validate_on_submit() and available_students:
            student = Student.query.get(form.student.data)
            if student:
                course.students.append(student)
                db.session.commit()
                flash(f'{student.first_name} {student.last_name} enrolled in {course.title}!', 'success')
                return redirect(url_for('manage_course_students', id=course.id))
        
        return render_template('manage_course_students.html', title='Manage Students', 
                              course=course, form=form)
                              
    @app.route('/courses/remove_student/<int:course_id>/<int:student_id>', methods=['POST'])
    @login_required
    def remove_student_from_course(course_id, student_id):
        """Remove a student from a course"""
        course = Course.query.get_or_404(course_id)
        student = Student.query.get_or_404(student_id)
        
        if student in course.students:
            course.students.remove(student)
            db.session.commit()
            flash(f'{student.first_name} {student.last_name} removed from {course.title}!', 'success')
        
        return redirect(url_for('manage_course_students', id=course_id))
        
    @app.route('/courses/attendance/<int:id>')
    @login_required
    def course_attendance(id):
        """View attendance for a specific course"""
        course = Course.query.get_or_404(id)
        
        # Get the attendance records for this course
        attendance_records = Attendance.query.filter_by(course_id=course.id).order_by(Attendance.timestamp.desc()).all()
        
        # Group records by date
        grouped_records = {}
        for record in attendance_records:
            date_str = record.timestamp.strftime('%Y-%m-%d')
            if date_str not in grouped_records:
                grouped_records[date_str] = []
            grouped_records[date_str].append(record)
        
        return render_template('course_attendance.html', title=f'Attendance - {course.course_code}',
                              course=course, grouped_records=grouped_records)
                            
    @app.route('/courses/delete/<int:id>', methods=['POST'])
    @login_required
    def delete_course(id):
        """Delete a course"""
        course = Course.query.get_or_404(id)
        
        # Only the creator or an admin can delete the course
        if course.user_id != current_user.id and not current_user.is_admin:
            flash('You do not have permission to delete this course.', 'danger')
            return redirect(url_for('courses'))
            
        try:
            # First delete all attendance records for this course
            Attendance.query.filter_by(course_id=course.id).delete()
            
            # Remove all students from the course (many-to-many relationship)
            course.students = []
            
            # Finally delete the course
            db.session.delete(course)
            db.session.commit()
            
            flash(f'Course {course.course_code} - {course.title} has been deleted!', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting course {id}: {str(e)}")
            flash(f'Failed to delete course. Error: {str(e)}', 'danger')
        
        return redirect(url_for('courses'))
    
    @app.route('/enroll', methods=['GET', 'POST'])
    @login_required
    def enroll():
        """Fingerprint enrollment page"""
        form = FingerprintEnrollForm()
        form.student.choices = [(s.id, f"{s.student_id} - {s.first_name} {s.last_name}") 
                               for s in Student.query.order_by(Student.last_name).all()]
        
        if form.validate_on_submit():
            student = Student.query.get(form.student.data)
            
            # Get next available ID from ESP32
            try:
                response = fingerprint_sensor.get_next_fingerprint_id()
                if not response.get('success'):
                    flash('Failed to get next available fingerprint ID. Please try again.', 'error')
                    return redirect(url_for('enroll'))
                
                finger_id = response.get('nextId')
                if not finger_id:
                    flash('Fingerprint sensor memory is full. Please delete some fingerprints first.', 'error')
                    return redirect(url_for('enroll'))
                
                # Check if this finger is already enrolled
                existing = Fingerprint.query.filter_by(
                    student_id=student.id, 
                    finger_id=finger_id
                ).first()
                
                if existing:
                    flash(f'This finger is already enrolled for {student.first_name}. Please choose a different finger.', 'warning')
                    return redirect(url_for('enroll'))
                
                # Store enrollment info in session
                session['enrollment_student_id'] = student.id
                session['enrollment_finger_id'] = finger_id
            except Exception as e:
                logger.error(f"Error getting next fingerprint ID: {str(e)}")
                flash('Failed to communicate with fingerprint sensor. Please check the connection.', 'error')
                return redirect(url_for('enroll'))
            
            # Start enrollment on ESP32
            try:
                response = fingerprint_sensor.start_enrollment()
                if not response:
                    flash('Failed to start enrollment process. Please try again.', 'error')
                    return redirect(url_for('enroll'))
                    
                flash(f'Place {student.first_name}\'s finger on the sensor to begin enrollment...', 'info')
                return render_template('enroll.html', title='Fingerprint Enrollment', 
                                     form=form, enrolling=True, student=student)
                                     
            except Exception as e:
                logger.error(f"Error starting enrollment: {str(e)}")
                flash('Failed to communicate with fingerprint sensor. Please check the connection.', 'error')
                return redirect(url_for('enroll'))
        
        return render_template('enroll.html', title='Fingerprint Enrollment', form=form)

    @app.route('/enroll/status', methods=['GET'])
    @login_required
    def enrollment_status():
        """AJAX endpoint to check enrollment status"""
        if 'enrollment_student_id' not in session:
            return jsonify({'status': 'error', 'message': 'No enrollment in progress'})
        
        try:
            # Get status from ESP32
            status = fingerprint_sensor.get_enrollment_status()
            
            # If enrollment is complete, save the fingerprint template
            if status['status'] == 'complete' and 'template_data' in status:
                student_id = session.pop('enrollment_student_id', None)
                finger_id = session.pop('enrollment_finger_id', None)
                
                if student_id and finger_id is not None:
                    student = Student.query.get(student_id)
                    
                    # Create new fingerprint record
                    fingerprint = Fingerprint(
                        student_id=student.id,
                        finger_id=finger_id,
                        template_data=status['template_data'],
                        created_at=datetime.utcnow()
                    )
                    
                    try:
                        db.session.add(fingerprint)
                        db.session.commit()
                        logger.info(f"Fingerprint enrolled for student {student.id}, finger {finger_id}")
                    except Exception as e:
                        logger.error(f"Database error saving fingerprint: {str(e)}")
                        db.session.rollback()
                        return jsonify({
                            'status': 'error',
                            'message': 'Failed to save fingerprint to database'
                        })
            
            return jsonify(status)
            
        except Exception as e:
            logger.error(f"Error checking enrollment status: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to communicate with fingerprint sensor'
            })

    @app.route('/enroll/process', methods=['POST'])
    @login_required
    def process_enrollment():
        """AJAX endpoint to process fingerprint enrollment"""
        if 'enrollment_student_id' not in session:
            return jsonify({'status': 'error', 'message': 'No enrollment in progress'})

        try:
            student_id = session['enrollment_student_id']
            finger_id = session['enrollment_finger_id']

            # Start enrollment process on ESP32
            result = fingerprint_sensor.enroll_finger(finger_id)
            
            if result.get('success'):
                # Create new fingerprint record in database
                fingerprint = Fingerprint(
                    student_id=student_id,
                    finger_id=finger_id,
                    created_at=datetime.utcnow()
                )
                
                db.session.add(fingerprint)
                db.session.commit()

                # Clear enrollment session data
                session.pop('enrollment_student_id', None)
                session.pop('enrollment_finger_id', None)

                student = Student.query.get(student_id)
                return jsonify({
                    'status': 'success',
                    'message': f'Successfully enrolled fingerprint for {student.first_name} {student.last_name}'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': result.get('message', 'Enrollment failed')
                })

        except Exception as e:
            logger.error(f"Error during enrollment: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Enrollment error: {str(e)}'
            })
    
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
        
        try:
            # Attempt to connect to the sensor if not already connected
            if not fingerprint_sensor.is_connected:
                if not fingerprint_sensor.connect():
                    return jsonify({
                        'status': 'error',
                        'message': 'Failed to connect to fingerprint sensor'
                    })

            # Verify fingerprint using ESP32
            result = fingerprint_sensor.verify_finger()
            
            if result.get('success'):
                finger_id = result.get('finger_id')
                # Look up the student by their enrolled fingerprint
                fingerprint = Fingerprint.query.filter_by(finger_id=finger_id).first()
                
                if not fingerprint:
                    return jsonify({
                        'status': 'error',
                        'message': 'Fingerprint found but not enrolled in system'
                    })

                # Record attendance for the matched student
                attendance = attendance_manager.record_attendance(
                    student_id=fingerprint.student_id,
                    course_id=int(course_id),
                    status='present'
                )
                
                if attendance:
                    student = Student.query.get(fingerprint.student_id)
                    return jsonify({
                        'status': 'success', 
                        'message': f'Attendance recorded for {student.first_name} {student.last_name}'
                    })
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Failed to record attendance in database'
                    })
            else:
                return jsonify({
                    'status': 'error',
                    'message': result.get('message', 'No match found')
                })
                
        except Exception as e:
            logger.error(f"Error during fingerprint verification: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Verification error: {str(e)}'
            })
    
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

    @app.route('/api/enrollment/available', methods=['GET'])
    @login_required
    def get_unenrolled_students():
        """Get list of students who don't have fingerprints enrolled"""
        try:
            # Query for students without fingerprint records
            unenrolled_students = Student.query\
                .outerjoin(Fingerprint)\
                .filter(Fingerprint.id.is_(None))\
                .all()
            
            students_data = []
            for student in unenrolled_students:
                students_data.append({
                    'id': student.id,
                    'student_id': student.student_id,
                    'first_name': student.first_name,
                    'last_name': student.last_name
                })
            
            return jsonify(students_data), 200
            
        except Exception as e:
            logger.error(f"Error fetching unenrolled students: {str(e)}")
            return jsonify({'error': 'Failed to fetch unenrolled students'}), 500

    @app.route('/api/enrollment/save', methods=['POST'])
    @login_required
    def save_enrollment():
        """Save a new fingerprint enrollment"""
        try:
            data = request.get_json()
            
            if not data or 'student_id' not in data or 'fingerprint_id' not in data:
                return jsonify({'error': 'Missing required data'}), 400
                
            student = Student.query.get(data['student_id'])
            if not student:
                return jsonify({'error': 'Student not found'}), 404
                
            # Check if fingerprint ID is already in use
            existing_print = Fingerprint.query.filter_by(fingerprint_id=data['fingerprint_id']).first()
            if existing_print:
                return jsonify({'error': 'Fingerprint ID already in use'}), 409
                
            # Create new fingerprint record
            new_fingerprint = Fingerprint(
                student_id=student.id,
                fingerprint_id=data['fingerprint_id'],
                enrolled_at=datetime.utcnow()
            )
            
            db.session.add(new_fingerprint)
            db.session.commit()
            
            logger.info(f"Fingerprint enrolled for student {student.id} with ID {data['fingerprint_id']}")
            return jsonify({'message': 'Enrollment saved successfully'}), 200
            
        except Exception as e:
            logger.error(f"Error saving enrollment: {str(e)}")
            db.session.rollback()
            return jsonify({'error': 'Failed to save enrollment'}), 500
