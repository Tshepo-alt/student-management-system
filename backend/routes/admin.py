# backend/routes/admin.py
from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
import csv
import io
import traceback
from sqlalchemy import func, text

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import db, User, Student, Program, Module, Accommodation, Registration, Payment, Notification, TokenBlocklist, Campus, AccommodationRegistration, AccommodationRoom, AcademicRecord, ExamRegistration, FeesConfig, Course, Enrollment

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# ==================== AUTHENTICATION & AUTHORIZATION ====================

def is_admin(user_id):
    """Check if user has admin, registrar, or finance role (admin access)"""
    user = User.query.get(user_id)
    if not user:
        return False
    # Allow admin, administrator, registrar, and finance for dashboard access
    return user.role in ['admin', 'administrator', 'registrar', 'finance']

def admin_required(f):
    """Decorator to check admin/registrar/finance access (for read operations)"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        if not is_admin(int(current_user_id)):
            return jsonify({'error': 'Access denied. Admin, Registrar, or Finance privileges required.'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ==================== DASHBOARD STATISTICS ====================

@admin_bp.route('/stats', methods=['GET'])
@jwt_required()
@admin_required
def get_stats():
    """Get system statistics for admin dashboard"""
    try:
        stats = {
            'total_users': User.query.count(),
            'total_students': Student.query.count(),
            'total_programs': Program.query.count(),
            'total_modules': Module.query.count(),
            'total_campuses': Campus.query.count(),
            'total_accommodations': Accommodation.query.count(),
            'active_users': User.query.filter_by(is_active=True).count(),
            'admins': User.query.filter(User.role.in_(['admin', 'administrator'])).count(),
            'students': User.query.filter_by(role='student').count(),
            'lecturers': User.query.filter_by(role='lecturer').count(),
            'staff': User.query.filter_by(role='staff').count(),
            'government_sponsored': Student.query.filter_by(is_government_sponsored=True).count(),
            'self_sponsored': Student.query.filter_by(is_government_sponsored=False).count(),
            'pending_registrations': Registration.query.filter_by(registration_status='pending').count() if hasattr(Registration, 'registration_status') else 0,
            'pending_payments': Payment.query.filter_by(status='pending').count(),
            'open_tickets': Notification.query.filter_by(notification_type='ticket', is_read=False).count() if Notification else 0,
            'available_rooms': AccommodationRoom.query.filter_by(is_available=True).count() if AccommodationRoom else 0,
            'pending_accommodation': AccommodationRegistration.query.filter_by(status='pending').count() if AccommodationRegistration else 0,
            'wants_accommodation': Student.query.filter_by(wants_accommodation=True).count()
        }
        return jsonify(stats), 200
    except Exception as e:
        print(f"Stats error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ==================== USER MANAGEMENT ====================

@admin_bp.route('/users', methods=['GET'])
@jwt_required()
@admin_required
def get_users():
    """Get all users"""
    try:
        users = User.query.all()
        result = []
        for user in users:
            student = Student.query.filter_by(user_id=user.id).first()
            result.append({
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'first_name': student.first_name if student else None,
                'last_name': student.last_name if student else None,
                'role': user.role,
                'is_active': user.is_active,
                'is_verified': getattr(user, 'is_verified', True),
                'is_government_sponsored': student.is_government_sponsored if student else False,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if hasattr(user, 'last_login') and user.last_login else None
            })
        return jsonify(result), 200
    except Exception as e:
        print(f"Get users error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_user(user_id):
    """Update user details"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if 'first_name' in data or 'last_name' in data:
            student = Student.query.filter_by(user_id=user_id).first()
            if student:
                if 'first_name' in data:
                    student.first_name = data['first_name']
                if 'last_name' in data:
                    student.last_name = data['last_name']
        
        if 'email' in data:
            user.email = data['email']
            user.username = data['email']
        if 'role' in data:
            user.role = data['role']
        if 'is_active' in data:
            user.is_active = data['is_active']
        
        db.session.commit()
        return jsonify({'message': 'User updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Update user error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_user(user_id):
    """Delete user (soft delete)"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.is_active = False
        db.session.commit()
        return jsonify({'message': 'User deactivated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== STUDENT MANAGEMENT ====================

@admin_bp.route('/students', methods=['GET'])
@jwt_required()
@admin_required
def get_students():
    """Get all students (filter by admission_status if provided)"""
    try:
        status = request.args.get('status')
        query = Student.query
        if status:
            query = query.filter_by(admission_status=status)
        students = query.all()
        
        result = []
        for student in students:
            program = Program.query.get(student.program_id) if student.program_id else None
            campus = Campus.query.get(student.campus_id) if student.campus_id else None
            result.append({
                'id': student.id,
                'user_id': student.user_id,
                'student_number': student.student_number,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'email': student.email,
                'phone': getattr(student, 'phone', ''),
                'program_id': student.program_id,
                'program_name': program.program_name if program else None,
                'campus_id': student.campus_id,
                'campus_name': campus.campus_name if campus else None,
                'admission_status': getattr(student, 'admission_status', 'pending'),
                'academic_status': getattr(student, 'academic_status', 'active'),
                'current_year': getattr(student, 'current_year', 1),
                'current_gpa': float(student.current_gpa) if hasattr(student, 'current_gpa') and student.current_gpa else None,
                'total_credits_earned': getattr(student, 'total_credits_earned', 0),
                'is_government_sponsored': student.is_government_sponsored,
                'wants_accommodation': student.wants_accommodation,
                'enrollment_date': student.enrollment_date.isoformat() if hasattr(student, 'enrollment_date') and student.enrollment_date else None,
                'created_at': student.created_at.isoformat() if hasattr(student, 'created_at') and student.created_at else None
            })
        return jsonify(result), 200
    except Exception as e:
        print(f"Get students error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/students', methods=['POST'])
@jwt_required()
@admin_required
def create_student():
    """Create a new student"""
    try:
        data = request.get_json()
        
        # Check if email exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 409
        
        # Create user
        user = User(
            username=data['email'],
            email=data['email'],
            password_hash=generate_password_hash(data.get('password', 'Student123!')),
            role='student',
            is_active=True
        )
        db.session.add(user)
        db.session.flush()
        
        # Generate student number
        year = datetime.now().year
        student_count = Student.query.count() + 1
        student_number = f"GIPS/{year}/{student_count:05d}"
        
        # Create student
        student = Student(
            user_id=user.id,
            student_number=student_number,
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            phone=data.get('phone', ''),
            program_id=data.get('program_id'),
            campus_id=data.get('campus_id'),
            is_government_sponsored=data.get('is_government_sponsored', False),
            wants_accommodation=data.get('wants_accommodation', False),
            enrollment_date=datetime.now().date(),
            admission_status='accepted'
        )
        db.session.add(student)
        db.session.commit()
        
        return jsonify({
            'message': 'Student created successfully',
            'student_id': student.id,
            'student_number': student_number
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"Create student error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/students/<int:student_id>/approve', methods=['POST'])
@jwt_required()
@admin_required
def approve_student(student_id):
    """Approve student registration"""
    try:
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        student.admission_status = 'accepted'
        db.session.commit()
        
        # Create notification
        if Notification:
            notification = Notification(
                user_id=student.user_id,
                title='Registration Approved',
                message=f'Your registration has been approved. Welcome to GIPS College!',
                notification_type='success'
            )
            db.session.add(notification)
            db.session.commit()
        
        return jsonify({'message': 'Student approved successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/students/<int:student_id>/reject', methods=['POST'])
@jwt_required()
@admin_required
def reject_student(student_id):
    """Reject student registration"""
    try:
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        student.admission_status = 'rejected'
        db.session.commit()
        
        return jsonify({'message': 'Student rejected'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/students/<int:student_id>/results', methods=['GET'])
@jwt_required()
@admin_required
def get_student_results(student_id):
    """Get student results for admin view"""
    try:
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        # Get enrollments with grades
        enrollments = Enrollment.query.filter_by(
            student_id=student.id,
            status='completed'
        ).order_by(Enrollment.created_at.desc()).all()
        
        results = []
        for enrollment in enrollments:
            if enrollment.module:
                results.append({
                    'module_code': enrollment.module.module_code,
                    'module_name': enrollment.module.module_name,
                    'credits': enrollment.module.credits,
                    'semester': enrollment.module.semester,
                    'year_level': enrollment.module.year_level,
                    'grade': enrollment.grade,
                    'grade_points': float(enrollment.grade_points) if enrollment.grade_points else 0,
                    'is_supplementary': enrollment.is_supplementary,
                    'is_resit': enrollment.is_resit,
                    'is_retake': enrollment.is_retake
                })
        
        # Get academic records
        academic_records = AcademicRecord.query.filter_by(
            student_id=student.id
        ).order_by(AcademicRecord.created_at.desc()).all()
        
        records = []
        for record in academic_records:
            records.append({
                'semester_gpa': float(record.semester_gpa) if record.semester_gpa else 0,
                'cumulative_gpa': float(record.cumulative_gpa) if record.cumulative_gpa else 0,
                'academic_status': record.academic_status,
                'dean_list': record.dean_list,
                'created_at': record.created_at.isoformat()
            })
        
        return jsonify({
            'student': {
                'id': student.id,
                'student_number': student.student_number,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'program': student.program.program_name if student.program else None,
                'current_year': student.current_year,
                'current_gpa': float(student.current_gpa) if student.current_gpa else 0,
                'academic_status': student.academic_status,
                'is_government_sponsored': student.is_government_sponsored
            },
            'results': results,
            'academic_records': records
        }), 200
        
    except Exception as e:
        print(f"Get student results error: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== CAMPUS MANAGEMENT ====================

@admin_bp.route('/campuses', methods=['GET'])
@jwt_required()
@admin_required
def get_campuses():
    """Get all campuses"""
    try:
        campuses = Campus.query.all()
        result = []
        for campus in campuses:
            result.append({
                'id': campus.id,
                'campus_code': campus.campus_code,
                'campus_name': campus.campus_name,
                'campus_location': campus.campus_location,
                'campus_address': campus.campus_address,
                'has_accommodation': campus.has_accommodation,
                'is_main_campus': campus.is_main_campus,
                'program_count': Program.query.filter_by(campus_id=campus.id).count(),
                'student_count': Student.query.filter_by(campus_id=campus.id).count()
            })
        return jsonify(result), 200
    except Exception as e:
        print(f"Get campuses error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/campuses', methods=['POST'])
@jwt_required()
@admin_required
def create_campus():
    """Create a new campus"""
    try:
        data = request.get_json()
        
        campus = Campus(
            campus_code=data['campus_code'],
            campus_name=data['campus_name'],
            campus_location=data.get('campus_location'),
            campus_address=data.get('campus_address'),
            has_accommodation=data.get('has_accommodation', False),
            is_main_campus=data.get('is_main_campus', False)
        )
        db.session.add(campus)
        db.session.commit()
        
        return jsonify({
            'message': 'Campus created successfully',
            'campus_id': campus.id
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"Create campus error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/campuses/<int:campus_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_campus(campus_id):
    """Update campus details"""
    try:
        campus = Campus.query.get(campus_id)
        if not campus:
            return jsonify({'error': 'Campus not found'}), 404
        
        data = request.get_json()
        
        if 'campus_code' in data:
            campus.campus_code = data['campus_code']
        if 'campus_name' in data:
            campus.campus_name = data['campus_name']
        if 'campus_location' in data:
            campus.campus_location = data['campus_location']
        if 'campus_address' in data:
            campus.campus_address = data['campus_address']
        if 'has_accommodation' in data:
            campus.has_accommodation = data['has_accommodation']
        if 'is_main_campus' in data:
            campus.is_main_campus = data['is_main_campus']
        
        db.session.commit()
        return jsonify({'message': 'Campus updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== PROGRAM MANAGEMENT ====================

@admin_bp.route('/programs', methods=['GET'])
@jwt_required()
@admin_required
def get_programs():
    """Get all programs"""
    try:
        programs = Program.query.all()
        result = []
        for program in programs:
            campus = Campus.query.get(program.campus_id) if program.campus_id else None
            result.append({
                'id': program.id,
                'program_code': program.program_code,
                'program_name': program.program_name,
                'duration_years': getattr(program, 'duration_years', 3),
                'total_credits': getattr(program, 'total_credits', 0),
                'min_bgcse_points': program.min_bgcse_points,
                'description': getattr(program, 'description', ''),
                'campus_id': program.campus_id,
                'campus_name': campus.campus_name if campus else None,
                'is_active': getattr(program, 'is_active', True)
            })
        return jsonify(result), 200
    except Exception as e:
        print(f"Get programs error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/programs', methods=['POST'])
@jwt_required()
@admin_required
def create_program():
    """Create a new program"""
    try:
        data = request.get_json()
        
        program = Program(
            program_code=data['program_code'],
            program_name=data['program_name'],
            campus_id=data.get('campus_id'),
            duration_years=data.get('duration_years', 3),
            total_credits=data.get('total_credits', 0),
            min_bgcse_points=data.get('min_bgcse_points', 32),
            description=data.get('description', ''),
            is_active=True
        )
        db.session.add(program)
        db.session.commit()
        
        return jsonify({
            'message': 'Program created successfully',
            'program_id': program.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/programs/<int:program_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_program(program_id):
    """Update program details"""
    try:
        program = Program.query.get(program_id)
        if not program:
            return jsonify({'error': 'Program not found'}), 404
        
        data = request.get_json()
        
        if 'program_code' in data:
            program.program_code = data['program_code']
        if 'program_name' in data:
            program.program_name = data['program_name']
        if 'campus_id' in data:
            program.campus_id = data['campus_id']
        if 'duration_years' in data:
            program.duration_years = data['duration_years']
        if 'total_credits' in data:
            program.total_credits = data['total_credits']
        if 'min_bgcse_points' in data:
            program.min_bgcse_points = data['min_bgcse_points']
        if 'description' in data:
            program.description = data['description']
        if 'is_active' in data:
            program.is_active = data['is_active']
        
        db.session.commit()
        return jsonify({'message': 'Program updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/programs/<int:program_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_program(program_id):
    """Delete a program"""
    try:
        program = Program.query.get(program_id)
        if not program:
            return jsonify({'error': 'Program not found'}), 404
        
        # Check if program has enrolled students
        if Student.query.filter_by(program_id=program_id).first():
            return jsonify({'error': 'Cannot delete program with enrolled students'}), 400
        
        db.session.delete(program)
        db.session.commit()
        return jsonify({'message': 'Program deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== MODULE MANAGEMENT ====================

@admin_bp.route('/modules', methods=['GET'])
@jwt_required()
@admin_required
def get_modules():
    """Get all modules"""
    try:
        modules = Module.query.all()
        result = []
        for module in modules:
            result.append({
                'id': module.id,
                'module_code': module.module_code,
                'module_name': module.module_name,
                'credits': module.credits,
                'year_level': getattr(module, 'year_level', 1),
                'semester': getattr(module, 'semester', 1),
                'module_type': getattr(module, 'module_type', 'core'),
                'has_practicals': getattr(module, 'has_practicals', False),
                'description': getattr(module, 'description', ''),
                'prerequisites': getattr(module, 'prerequisites', '')
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/modules', methods=['POST'])
@jwt_required()
@admin_required
def create_module():
    """Create a new module"""
    try:
        data = request.get_json()
        
        module = Module(
            module_code=data['module_code'],
            module_name=data['module_name'],
            credits=data['credits'],
            year_level=data.get('year_level', 1),
            semester=data.get('semester', 1),
            module_type=data.get('module_type', 'core'),
            has_practicals=data.get('has_practicals', False),
            description=data.get('description', ''),
            prerequisites=data.get('prerequisites', '')
        )
        db.session.add(module)
        db.session.commit()
        
        return jsonify({
            'message': 'Module created successfully',
            'module_id': module.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== LECTURER & COURSE ASSIGNMENT ====================

@admin_bp.route('/lecturers', methods=['GET'])
@jwt_required()
@admin_required
def get_lecturers():
    """Get all users with role lecturer or staff"""
    try:
        lecturers = User.query.filter(User.role.in_(['lecturer', 'staff'])).all()
        result = []
        for lec in lecturers:
            result.append({
                'id': lec.id,
                'username': lec.username,
                'email': lec.email,
                'role': lec.role,
                'is_active': lec.is_active
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/courses/unassigned', methods=['GET'])
@jwt_required()
@admin_required
def get_unassigned_courses():
    """Get courses that have no lecturer assigned"""
    try:
        courses = Course.query.filter(
            (Course.lecturer_id == None) | (Course.lecturer_id == 0)
        ).all()
        result = []
        for course in courses:
            result.append({
                'id': course.id,
                'course_code': course.course_code,
                'course_name': course.course_name,
                'credits': course.credits,
                'semester': course.semester,
                'year_level': course.year_level,
                'program_name': course.program.program_name if course.program else None
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/courses/<int:course_id>/assign-lecturer', methods=['POST'])
@jwt_required()
@admin_required
def assign_lecturer_to_course(course_id):
    """Assign a lecturer to a course"""
    try:
        data = request.get_json()
        lecturer_id = data.get('lecturer_id')
        if not lecturer_id:
            return jsonify({'error': 'lecturer_id required'}), 400
        
        course = Course.query.get(course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        lecturer = User.query.get(lecturer_id)
        if not lecturer or lecturer.role not in ['lecturer', 'staff']:
            return jsonify({'error': 'Invalid lecturer ID or user is not a lecturer'}), 400
        
        course.lecturer_id = lecturer_id
        db.session.commit()
        
        return jsonify({
            'message': f'Course {course.course_code} assigned to {lecturer.username}',
            'course_id': course.id,
            'lecturer_id': lecturer.id,
            'lecturer_name': lecturer.username
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/courses/by-lecturer/<int:lecturer_id>', methods=['GET'])
@jwt_required()
@admin_required
def get_courses_by_lecturer(lecturer_id):
    """Get all courses assigned to a specific lecturer"""
    try:
        courses = Course.query.filter_by(lecturer_id=lecturer_id).all()
        result = []
        for course in courses:
            result.append({
                'id': course.id,
                'course_code': course.course_code,
                'course_name': course.course_name,
                'credits': course.credits,
                'semester': course.semester,
                'year_level': course.year_level,
                'enrolled_students': len(course.student_courses) if course.student_courses else 0
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== PAYMENT MANAGEMENT (for finance dashboard) ====================

@admin_bp.route('/payments', methods=['GET'])
@jwt_required()
@admin_required
def get_all_payments():
    """Get all payments (with optional limit for dashboard)"""
    try:
        limit = request.args.get('limit', default=10, type=int)
        payments = Payment.query.order_by(Payment.created_at.desc()).limit(limit).all()
        
        result = []
        for payment in payments:
            student = Student.query.get(payment.student_id)
            result.append({
                'id': payment.id,
                'student_name': f"{student.first_name} {student.last_name}" if student else 'Unknown',
                'student_number': student.student_number if student else 'N/A',
                'amount': float(payment.amount),
                'currency': payment.currency,
                'payment_type': payment.payment_type,
                'status': payment.status,
                'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                'created_at': payment.created_at.isoformat(),
                'receipt_number': payment.receipt_number
            })
        return jsonify(result), 200
    except Exception as e:
        print(f"Get all payments error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/payments/stats', methods=['GET'])
@jwt_required()
@admin_required
def get_payment_stats():
    """Get payment statistics for finance dashboard"""
    try:
        # Total revenue (completed payments)
        total_revenue = db.session.query(func.sum(Payment.amount)).filter(Payment.status == 'completed').scalar() or 0
        
        # Pending payments total
        pending_total = db.session.query(func.sum(Payment.amount)).filter(Payment.status == 'pending').scalar() or 0
        
        # Count of pending payments
        pending_count = Payment.query.filter_by(status='pending').count()
        
        # Today's collections
        today = datetime.utcnow().date()
        today_start = datetime(today.year, today.month, today.day)
        today_end = today_start + timedelta(days=1)
        today_collections = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'completed',
            Payment.payment_date >= today_start,
            Payment.payment_date < today_end
        ).scalar() or 0
        
        # This month's collections
        month_start = datetime(today.year, today.month, 1)
        month_collections = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'completed',
            Payment.payment_date >= month_start
        ).scalar() or 0
        
        # By payment type
        by_type = {}
        type_results = db.session.query(Payment.payment_type, func.sum(Payment.amount)).filter(Payment.status == 'completed').group_by(Payment.payment_type).all()
        for ptype, total in type_results:
            by_type[ptype] = float(total)
        
        # Recent transactions (last 5)
        recent = Payment.query.order_by(Payment.created_at.desc()).limit(5).all()
        recent_list = []
        for p in recent:
            student = Student.query.get(p.student_id)
            recent_list.append({
                'student_name': f"{student.first_name} {student.last_name}" if student else 'Unknown',
                'amount': float(p.amount),
                'status': p.status,
                'date': p.created_at.isoformat()
            })
        
        stats = {
            'total_revenue': float(total_revenue),
            'pending_total': float(pending_total),
            'pending_count': pending_count,
            'today_collections': float(today_collections),
            'month_collections': float(month_collections),
            'by_payment_type': by_type,
            'recent_transactions': recent_list
        }
        return jsonify(stats), 200
    except Exception as e:
        print(f"Payment stats error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ==================== ACCOMMODATION MANAGEMENT ====================

@admin_bp.route('/accommodations', methods=['GET'])
@jwt_required()
@admin_required
def get_accommodations():
    """Get all accommodations"""
    try:
        accommodations = Accommodation.query.all()
        result = []
        for acc in accommodations:
            result.append({
                'id': acc.id,
                'name': acc.name,
                'code': acc.code,
                'location': acc.location,
                'price_per_semester': float(acc.price_per_semester) if acc.price_per_semester else 0,
                'total_rooms': acc.total_rooms,
                'available_rooms': acc.available_rooms,
                'description': getattr(acc, 'description', ''),
                'amenities': getattr(acc, 'amenities', []),
                'is_active': getattr(acc, 'is_active', True)
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/accommodation/rooms', methods=['GET'])
@jwt_required()
@admin_required
def get_accommodation_rooms():
    """Get all accommodation rooms"""
    try:
        rooms = AccommodationRoom.query.all()
        result = []
        for room in rooms:
            result.append({
                'id': room.id,
                'block_name': room.block_name,
                'room_number': room.room_number,
                'room_type': room.room_type,
                'capacity': room.capacity,
                'current_occupants': room.current_occupants,
                'is_available': room.is_available,
                'has_kitchen': room.has_kitchen,
                'has_shower': room.has_shower,
                'has_study_table': room.has_study_table,
                'has_bed': room.has_bed
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/accommodation/applications', methods=['GET'])
@jwt_required()
@admin_required
def get_accommodation_registrations():
    """Get all accommodation applications"""
    try:
        applications = AccommodationRegistration.query.order_by(AccommodationRegistration.created_at.desc()).all()
        result = []
        for app in applications:
            student = Student.query.get(app.student_id)
            result.append({
                'id': app.id,
                'student_id': app.student_id,
                'student_name': f"{student.first_name} {student.last_name}" if student else 'Unknown',
                'student_number': student.student_number if student else 'N/A',
                'program': student.program.program_name if student and student.program else None,
                'room_type': app.room_type,
                'block_preference': app.block_preference,
                'status': app.status,
                'allocated_room_number': app.allocated_room_number,
                'allocated_block': app.allocated_block,
                'created_at': app.created_at.isoformat()
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/accommodation/applications/<int:app_id>/allocate', methods=['POST'])
@jwt_required()
@admin_required
def allocate_accommodation(app_id):
    """Allocate accommodation room to student"""
    try:
        data = request.get_json()
        application = AccommodationRegistration.query.get(app_id)
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        
        room_id = data.get('room_id')
        room = AccommodationRoom.query.get(room_id)
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        
        if not room.is_available:
            return jsonify({'error': 'Room not available'}), 400
        
        # Update application
        application.status = 'allocated'
        application.allocated_room_id = room.id
        application.allocated_room_number = room.room_number
        application.allocated_block = room.block_name
        
        # Update room occupancy
        room.current_occupants += 1
        if room.current_occupants >= room.capacity:
            room.is_available = False
        
        db.session.commit()
        
        # Create notification
        if application.student and application.student.user_id:
            notification = Notification(
                user_id=application.student.user_id,
                title='Accommodation Allocated',
                message=f'You have been allocated room {room.room_number} in Block {room.block_name}. Please check in within 48 hours.',
                notification_type='success'
            )
            db.session.add(notification)
            db.session.commit()
        
        return jsonify({
            'message': 'Accommodation allocated successfully',
            'room_number': room.room_number,
            'block': room.block_name
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"Allocate accommodation error: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== CSV EXPORTS ====================

@admin_bp.route('/export/government-sponsored', methods=['GET'])
@jwt_required()
@admin_required
def export_government_sponsored():
    """Export government sponsored students data to CSV"""
    try:
        students = Student.query.filter_by(
            is_government_sponsored=True,
            is_active=True
        ).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'Student Number', 'First Name', 'Last Name', 'Email', 'Phone',
            'Program', 'Campus', 'Current Year', 'Current GPA', 'Previous Semester GPA',
            'Enrollment Date', 'Academic Status', 'DTEF Sponsor Number'
        ])
        
        for student in students:
            # Get previous semester GPA
            previous_record = AcademicRecord.query.filter_by(
                student_id=student.id
            ).order_by(AcademicRecord.created_at.desc()).first()
            
            writer.writerow([
                student.student_number,
                student.first_name,
                student.last_name,
                student.email,
                student.phone or '',
                student.program.program_name if student.program else '',
                student.campus.campus_name if student.campus else '',
                student.current_year,
                float(student.current_gpa) if student.current_gpa else 0,
                float(previous_record.semester_gpa) if previous_record and previous_record.semester_gpa else 0,
                student.enrollment_date.isoformat() if student.enrollment_date else '',
                student.academic_status,
                student.dtef_sponsor_number or ''
            ])
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'government_sponsored_students_{datetime.now().strftime("%Y%m%d")}.csv'
        )
        
    except Exception as e:
        print(f"Export error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/export/self-sponsored', methods=['GET'])
@jwt_required()
@admin_required
def export_self_sponsored():
    """Export self sponsored students data to CSV"""
    try:
        students = Student.query.filter_by(
            is_government_sponsored=False,
            is_active=True
        ).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'Student Number', 'First Name', 'Last Name', 'Email', 'Phone',
            'Program', 'Campus', 'Current Year', 'Current GPA', 'Previous Semester GPA',
            'Enrollment Date', 'Academic Status', 'Outstanding Balance'
        ])
        
        for student in students:
            # Get outstanding balance
            registrations = Registration.query.filter_by(student_id=student.id).all()
            outstanding = sum((reg.total_fees or 0) - (reg.paid_amount or 0) for reg in registrations)
            
            previous_record = AcademicRecord.query.filter_by(
                student_id=student.id
            ).order_by(AcademicRecord.created_at.desc()).first()
            
            writer.writerow([
                student.student_number,
                student.first_name,
                student.last_name,
                student.email,
                student.phone or '',
                student.program.program_name if student.program else '',
                student.campus.campus_name if student.campus else '',
                student.current_year,
                float(student.current_gpa) if student.current_gpa else 0,
                float(previous_record.semester_gpa) if previous_record and previous_record.semester_gpa else 0,
                student.enrollment_date.isoformat() if student.enrollment_date else '',
                student.academic_status,
                f"P{outstanding:,.2f}"
            ])
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'self_sponsored_students_{datetime.now().strftime("%Y%m%d")}.csv'
        )
        
    except Exception as e:
        print(f"Export error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/export/accommodation-applicants', methods=['GET'])
@jwt_required()
@admin_required
def export_accommodation_applicants():
    """Export accommodation applicants data to CSV"""
    try:
        applications = AccommodationRegistration.query.filter_by(
            status='pending'
        ).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'Student Number', 'Student Name', 'Program', 'Campus', 'Room Type',
            'Block Preference', 'Emergency Contact', 'Medical Conditions',
            'Application Date', 'Status'
        ])
        
        for app in applications:
            student = Student.query.get(app.student_id)
            writer.writerow([
                student.student_number if student else '',
                f"{student.first_name} {student.last_name}" if student else '',
                student.program.program_name if student and student.program else '',
                student.campus.campus_name if student and student.campus else '',
                app.room_type,
                app.block_preference or '',
                f"{app.emergency_contact_name} ({app.emergency_contact_phone})" if app.emergency_contact_name else '',
                app.medical_conditions or '',
                app.created_at.strftime('%Y-%m-%d'),
                app.status
            ])
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'accommodation_applicants_{datetime.now().strftime("%Y%m%d")}.csv'
        )
        
    except Exception as e:
        print(f"Export error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ==================== SYSTEM SETTINGS ====================

@admin_bp.route('/settings', methods=['GET'])
@jwt_required()
@admin_required
def get_settings():
    """Get system settings"""
    try:
        settings = {
            'academic_year': '2025/2026',
            'current_semester': 2,
            'registration_start': '2026-01-15',
            'registration_end': '2026-02-15',
            'late_fee': 500,
            'application_fee': 500,
            'registration_fee': 2000,
            'exam_fee': 500,
            'supplementary_exam_fee': 300,
            'resit_exam_fee': 600,
            'retake_exam_fee': 1000,
            'accommodation_deposit': 5000,
            'session_timeout': 30,
            'max_login_attempts': 5
        }
        return jsonify(settings), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/settings', methods=['PUT'])
@jwt_required()
@admin_required
def update_settings():
    """Update system settings"""
    try:
        data = request.get_json()
        
        # Update FeesConfig if provided
        if 'supplementary_exam_fee' in data:
            fee = FeesConfig.query.filter_by(fee_type='supplementary').first()
            if fee:
                fee.amount = data['supplementary_exam_fee']
        
        if 'resit_exam_fee' in data:
            fee = FeesConfig.query.filter_by(fee_type='resit').first()
            if fee:
                fee.amount = data['resit_exam_fee']
        
        if 'retake_exam_fee' in data:
            fee = FeesConfig.query.filter_by(fee_type='retake').first()
            if fee:
                fee.amount = data['retake_exam_fee']
        
        db.session.commit()
        return jsonify({'message': 'Settings updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== REPORTS ====================

@admin_bp.route('/reports/students', methods=['GET'])
@jwt_required()
@admin_required
def get_student_report():
    """Generate student enrollment report"""
    try:
        students = Student.query.all()
        programs = Program.query.all()
        campuses = Campus.query.all()
        
        report = {
            'total_students': len(students),
            'government_sponsored': Student.query.filter_by(is_government_sponsored=True).count(),
            'self_sponsored': Student.query.filter_by(is_government_sponsored=False).count(),
            'by_program': {},
            'by_campus': {},
            'by_year': {},
            'by_status': {},
            'by_admission': {},
            'enrollment_trend': []
        }
        
        for program in programs:
            count = Student.query.filter_by(program_id=program.id).count()
            report['by_program'][program.program_name] = count
        
        for campus in campuses:
            count = Student.query.filter_by(campus_id=campus.id).count()
            report['by_campus'][campus.campus_name] = count
        
        for year in range(1, 5):
            count = Student.query.filter_by(current_year=year).count()
            report['by_year'][f'Year {year}'] = count
        
        statuses = ['good_standing', 'probation', 'suspended', 'graduated']
        for status in statuses:
            count = Student.query.filter_by(academic_status=status).count()
            report['by_status'][status] = count
        
        admission_statuses = ['accepted', 'pending', 'rejected', 'deferred', 'graduated']
        for status in admission_statuses:
            count = Student.query.filter_by(admission_status=status).count()
            report['by_admission'][status] = count
        
        return jsonify(report), 200
    except Exception as e:
        print(f"Report error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/reports/payments', methods=['GET'])
@jwt_required()
@admin_required
def get_payment_report():
    """Generate payment report"""
    try:
        payments = Payment.query.all()
        
        total_revenue = sum(p.amount for p in payments if p.status == 'completed')
        pending_amount = sum(p.amount for p in payments if p.status == 'pending')
        
        report = {
            'total_revenue': float(total_revenue),
            'pending_amount': float(pending_amount),
            'total_transactions': len(payments),
            'completed_transactions': len([p for p in payments if p.status == 'completed']),
            'by_method': {},
            'by_payment_type': {},
            'monthly_trend': []
        }
        
        methods = ['cash', 'bank_transfer', 'card', 'mobile_money']
        for method in methods:
            total = sum(p.amount for p in payments if p.payment_method == method and p.status == 'completed')
            report['by_method'][method] = float(total)
        
        payment_types = ['registration', 'tuition', 'supplementary', 'resit', 'retake', 'accommodation']
        for ptype in payment_types:
            if hasattr(Payment, 'payment_type'):
                total = sum(p.amount for p in payments if getattr(p, 'payment_type', '') == ptype and p.status == 'completed')
                report['by_payment_type'][ptype] = float(total)
        
        return jsonify(report), 200
    except Exception as e:
        print(f"Payment report error: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== SYSTEM HEALTH ====================

@admin_bp.route('/health', methods=['GET'])
@jwt_required()
@admin_required
def system_health():
    """Get system health status"""
    try:
        # Check database connection
        db_status = 'connected'
        try:
            db.session.execute(text('SELECT 1'))
        except Exception as e:
            db_status = f'disconnected: {str(e)}'
        
        # Get counts
        users = User.query.count()
        students = Student.query.count()
        
        return jsonify({
            'status': 'healthy' if db_status == 'connected' else 'degraded',
            'database': db_status,
            'users': users,
            'students': students,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== ERROR HANDLERS ====================

@admin_bp.errorhandler(500)
def admin_internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@admin_bp.errorhandler(404)
def admin_not_found(error):
    return jsonify({'error': 'Resource not found'}), 404