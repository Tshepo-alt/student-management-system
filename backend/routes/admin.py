# backend/routes/admin.py
from flask import Blueprint, jsonify, request, send_file, current_app
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

from models import db, User, Student, Program, Module, Accommodation, Registration, Payment, Notification, TokenBlocklist, Campus, AccommodationRegistration, AccommodationRoom, AcademicRecord, ExamRegistration, FeesConfig, Course, Enrollment, StaffQuery, SystemConfig, ProgramModule

# ========== MOODLE INTEGRATION IMPORTS ==========
from services.moodle_integration import MoodleClient
from config import MOODLE_URL, MOODLE_API_TOKEN

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# ==================== AUTHENTICATION & AUTHORIZATION ====================

def is_admin(user_id):
    """Check if user has admin, registrar, or finance role (admin access)"""
    user = User.query.get(user_id)
    if not user:
        return False
    return user.role in ['admin', 'administrator', 'registrar', 'finance']

def admin_required(f):
    """Decorator to check admin/registrar/finance access"""
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
            'pending_registrations': Registration.query.filter_by(registration_status='pending').count(),
            'pending_payments': Payment.query.filter_by(status='pending').count(),
            'open_tickets': Notification.query.filter_by(notification_type='ticket', is_read=False).count() if Notification else 0,
            'available_rooms': AccommodationRoom.query.filter_by(is_available=True).count(),
            'pending_accommodation': AccommodationRegistration.query.filter_by(status='pending').count(),
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
                'current_gpa': float(student.current_gpa) if student.current_gpa else None,
                'total_credits_earned': getattr(student, 'total_credits_earned', 0),
                'is_government_sponsored': student.is_government_sponsored,
                'wants_accommodation': student.wants_accommodation,
                'enrollment_date': student.enrollment_date.isoformat() if student.enrollment_date else None,
                'created_at': student.created_at.isoformat() if student.created_at else None,
                'moodle_user_id': student.moodle_user_id if hasattr(student, 'moodle_user_id') else None
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
    try:
        data = request.get_json()
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 409
        user = User(
            username=data['email'],
            email=data['email'],
            password_hash=generate_password_hash(data.get('password', 'Student123!')),
            role='student',
            is_active=True
        )
        db.session.add(user)
        db.session.flush()
        year = datetime.now().year
        student_count = Student.query.count() + 1
        student_number = f"GIPS/{year}/{student_count:05d}"
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
        try:
            moodle = MoodleClient(MOODLE_URL, MOODLE_API_TOKEN)
            moodle_user_id = moodle.create_user(
                username=student_number,
                password=data.get('password', 'Student123!'),
                firstname=student.first_name,
                lastname=student.last_name,
                email=student.email
            )
            student.moodle_user_id = moodle_user_id
            current_app.logger.info(f"Moodle user created for {student.email} with ID {moodle_user_id}")
        except Exception as e:
            current_app.logger.error(f"Moodle user creation failed for {student.email}: {e}")
        db.session.commit()
        return jsonify({
            'message': 'Student created successfully',
            'student_id': student.id,
            'student_number': student_number,
            'moodle_user_id': student.moodle_user_id
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"Create student error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/students/<int:student_id>/approve', methods=['POST'])
@jwt_required()
@admin_required
def approve_student(student_id):
    try:
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        student.admission_status = 'accepted'
        db.session.commit()
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

@admin_bp.route('/students/<int:student_id>/approve-admission', methods=['POST'])
@jwt_required()
@admin_required
def approve_student_admission(student_id):
    try:
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        if student.admission_status != 'pending':
            return jsonify({'error': f'Admission status is already {student.admission_status}'}), 400
        student.admission_status = 'accepted'
        db.session.commit()
        if Notification:
            notification = Notification(
                user_id=student.user_id,
                title='Admission Approved',
                message=f'Congratulations! Your admission to GIPS College has been approved. Please proceed to semester registration.',
                notification_type='success'
            )
            db.session.add(notification)
            db.session.commit()
        return jsonify({'message': 'Student admission approved successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/students/<int:student_id>/reject', methods=['POST'])
@jwt_required()
@admin_required
def reject_student(student_id):
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
    try:
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        enrollments = Enrollment.query.filter_by(student_id=student.id, status='completed').order_by(Enrollment.created_at.desc()).all()
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
        academic_records = AcademicRecord.query.filter_by(student_id=student.id).order_by(AcademicRecord.created_at.desc()).all()
        records = [{
            'semester_gpa': float(rec.semester_gpa) if rec.semester_gpa else 0,
            'cumulative_gpa': float(rec.cumulative_gpa) if rec.cumulative_gpa else 0,
            'academic_status': rec.academic_status,
            'dean_list': rec.dean_list,
            'created_at': rec.created_at.isoformat()
        } for rec in academic_records]
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
    try:
        campuses = Campus.query.all()
        result = [{
            'id': c.id,
            'campus_code': c.campus_code,
            'campus_name': c.campus_name,
            'campus_location': c.campus_location,
            'campus_address': c.campus_address,
            'has_accommodation': c.has_accommodation,
            'is_main_campus': c.is_main_campus,
            'program_count': Program.query.filter_by(campus_id=c.id).count(),
            'student_count': Student.query.filter_by(campus_id=c.id).count()
        } for c in campuses]
        return jsonify(result), 200
    except Exception as e:
        print(f"Get campuses error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/campuses', methods=['POST'])
@jwt_required()
@admin_required
def create_campus():
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
        return jsonify({'message': 'Campus created successfully', 'campus_id': campus.id}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Create campus error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/campuses/<int:campus_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_campus(campus_id):
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
    try:
        programs = Program.query.all()
        result = [{
            'id': p.id,
            'program_code': p.program_code,
            'program_name': p.program_name,
            'duration_years': getattr(p, 'duration_years', 3),
            'total_credits': getattr(p, 'total_credits', 0),
            'min_bgcse_points': p.min_bgcse_points,
            'description': getattr(p, 'description', ''),
            'campus_id': p.campus_id,
            'campus_name': p.campus.campus_name if p.campus else None,
            'is_active': getattr(p, 'is_active', True)
        } for p in programs]
        return jsonify(result), 200
    except Exception as e:
        print(f"Get programs error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/programs', methods=['POST'])
@jwt_required()
@admin_required
def create_program():
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
        return jsonify({'message': 'Program created successfully', 'program_id': program.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/programs/<int:program_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_program(program_id):
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
    try:
        program = Program.query.get(program_id)
        if not program:
            return jsonify({'error': 'Program not found'}), 404
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
    try:
        modules = Module.query.all()
        result = [{
            'id': m.id,
            'module_code': m.module_code,
            'module_name': m.module_name,
            'credits': m.credits,
            'year_level': getattr(m, 'year_level', 1),
            'semester': getattr(m, 'semester', 1),
            'module_type': getattr(m, 'module_type', 'core'),
            'has_practicals': getattr(m, 'has_practicals', False),
            'description': getattr(m, 'description', ''),
            'prerequisites': getattr(m, 'prerequisites', ''),
            'moodle_course_id': getattr(m, 'moodle_course_id', None)
        } for m in modules]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/modules', methods=['POST'])
@jwt_required()
@admin_required
def create_module():
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
        db.session.flush()
        try:
            moodle = MoodleClient(MOODLE_URL, MOODLE_API_TOKEN)
            moodle_course_id = moodle.create_course(
                fullname=module.module_name,
                shortname=module.module_code,
                categoryid=1
            )
            module.moodle_course_id = moodle_course_id
            current_app.logger.info(f"Moodle course created for module {module.module_code} with ID {moodle_course_id}")
        except Exception as e:
            current_app.logger.error(f"Moodle course creation failed for module {module.module_code}: {e}")
        db.session.commit()
        return jsonify({'message': 'Module created successfully', 'module_id': module.id, 'moodle_course_id': module.moodle_course_id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/modules/<int:module_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_module(module_id):
    try:
        module = Module.query.get(module_id)
        if not module:
            return jsonify({'error': 'Module not found'}), 404
        data = request.get_json()
        if 'module_code' in data:
            module.module_code = data['module_code']
        if 'module_name' in data:
            module.module_name = data['module_name']
        if 'credits' in data:
            module.credits = data['credits']
        if 'year_level' in data:
            module.year_level = data['year_level']
        if 'semester' in data:
            module.semester = data['semester']
        if 'module_type' in data:
            module.module_type = data['module_type']
        if 'description' in data:
            module.description = data['description']
        if 'prerequisites' in data:
            module.prerequisites = data['prerequisites']
        if 'has_practicals' in data:
            module.has_practicals = data['has_practicals']
        db.session.commit()
        return jsonify({
            'id': module.id,
            'module_code': module.module_code,
            'module_name': module.module_name,
            'credits': module.credits,
            'year_level': module.year_level,
            'semester': module.semester,
            'module_type': module.module_type,
            'description': module.description,
            'prerequisites': module.prerequisites,
            'has_practicals': module.has_practicals
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/modules/<int:module_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_module(module_id):
    try:
        module = Module.query.get(module_id)
        if not module:
            return jsonify({'error': 'Module not found'}), 404
        if ProgramModule.query.filter_by(module_id=module_id).first():
            return jsonify({'error': 'Cannot delete module – it is assigned to one or more programs.'}), 400
        db.session.delete(module)
        db.session.commit()
        return jsonify({'message': 'Module deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== PROGRAM-MODULE MAPPING ====================
@admin_bp.route('/program-modules', methods=['GET'])
@jwt_required()
@admin_required
def get_program_modules():
    try:
        mappings = db.session.query(ProgramModule, Program, Module).join(
            Program, ProgramModule.program_id == Program.id
        ).join(Module, ProgramModule.module_id == Module.id).all()
        result = [{
            'id': pm.id,
            'program_id': prog.id,
            'program_name': prog.program_name,
            'module_id': mod.id,
            'module_code': mod.module_code,
            'module_name': mod.module_name,
            'credits': mod.credits,
            'compulsory': pm.is_compulsory
        } for pm, prog, mod in mappings]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/program-modules', methods=['POST'])
@jwt_required()
@admin_required
def create_program_module():
    try:
        data = request.get_json()
        program_id = data.get('program_id')
        module_id = data.get('module_id')
        is_compulsory = data.get('is_compulsory', True)
        if not program_id or not module_id:
            return jsonify({'error': 'program_id and module_id required'}), 400
        existing = ProgramModule.query.filter_by(program_id=program_id, module_id=module_id).first()
        if existing:
            return jsonify({'error': 'Module already assigned to this program'}), 409
        pm = ProgramModule(
            program_id=program_id,
            module_id=module_id,
            is_compulsory=is_compulsory
        )
        db.session.add(pm)
        db.session.commit()
        program = Program.query.get(program_id)
        module = Module.query.get(module_id)
        return jsonify({
            'id': pm.id,
            'program_id': program.id,
            'program_name': program.program_name,
            'module_id': module.id,
            'module_code': module.module_code,
            'module_name': module.module_name,
            'credits': module.credits,
            'compulsory': pm.is_compulsory
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/program-modules/<int:pm_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_program_module(pm_id):
    try:
        pm = ProgramModule.query.get(pm_id)
        if not pm:
            return jsonify({'error': 'Mapping not found'}), 404
        db.session.delete(pm)
        db.session.commit()
        return jsonify({'message': 'Mapping removed'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== LECTURER & COURSE ASSIGNMENT ====================
@admin_bp.route('/lecturers', methods=['GET'])
@jwt_required()
@admin_required
def get_lecturers():
    try:
        lecturers = User.query.filter(User.role.in_(['lecturer', 'staff'])).all()
        result = [{
            'id': lec.id,
            'username': lec.username,
            'email': lec.email,
            'role': lec.role,
            'is_active': lec.is_active
        } for lec in lecturers]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/courses/unassigned', methods=['GET'])
@jwt_required()
@admin_required
def get_unassigned_courses():
    try:
        courses = Course.query.filter((Course.lecturer_id == None) | (Course.lecturer_id == 0)).all()
        result = [{
            'id': c.id,
            'course_code': c.course_code,
            'course_name': c.course_name,
            'credits': c.credits,
            'semester': c.semester,
            'year_level': c.year_level,
            'program_name': c.program.program_name if c.program else None
        } for c in courses]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/courses/<int:course_id>/assign-lecturer', methods=['POST'])
@jwt_required()
@admin_required
def assign_lecturer_to_course(course_id):
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
            return jsonify({'error': 'Invalid lecturer ID'}), 400
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
    try:
        courses = Course.query.filter_by(lecturer_id=lecturer_id).all()
        result = [{
            'id': c.id,
            'course_code': c.course_code,
            'course_name': c.course_name,
            'credits': c.credits,
            'semester': c.semester,
            'year_level': c.year_level,
            'enrolled_students': len(c.student_courses) if c.student_courses else 0
        } for c in courses]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== PAYMENT MANAGEMENT ====================
@admin_bp.route('/payments', methods=['GET'])
@jwt_required()
@admin_required
def get_all_payments():
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
    try:
        total_revenue = db.session.query(func.sum(Payment.amount)).filter(Payment.status == 'completed').scalar() or 0
        completed_count = Payment.query.filter_by(status='completed').count()
        pending_total = db.session.query(func.sum(Payment.amount)).filter(Payment.status == 'pending').scalar() or 0
        pending_count = Payment.query.filter_by(status='pending').count()
        today = datetime.utcnow().date()
        today_start = datetime(today.year, today.month, today.day)
        today_end = today_start + timedelta(days=1)
        today_collections = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'completed',
            Payment.payment_date >= today_start,
            Payment.payment_date < today_end
        ).scalar() or 0
        month_start = datetime(today.year, today.month, 1)
        month_collections = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'completed',
            Payment.payment_date >= month_start
        ).scalar() or 0
        by_type = {}
        type_results = db.session.query(Payment.payment_type, func.sum(Payment.amount)).filter(Payment.status == 'completed').group_by(Payment.payment_type).all()
        for ptype, total in type_results:
            by_type[ptype] = float(total)
        recent = Payment.query.order_by(Payment.created_at.desc()).limit(5).all()
        recent_list = [{
            'student_name': f"{Student.query.get(p.student_id).first_name} {Student.query.get(p.student_id).last_name}" if p.student_id else 'Unknown',
            'amount': float(p.amount),
            'status': p.status,
            'date': p.created_at.isoformat(),
            'id': p.id
        } for p in recent]
        stats = {
            'total_revenue': float(total_revenue),
            'completed_count': completed_count,
            'pending_total': float(pending_total),
            'pending_count': pending_count,
            'outstanding_amount': float(pending_total),
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
    try:
        accs = Accommodation.query.all()
        result = [{
            'id': a.id,
            'name': a.name,
            'code': a.code,
            'location': a.location,
            'price_per_semester': float(a.price_per_semester) if a.price_per_semester else 0,
            'total_rooms': a.total_rooms,
            'available_rooms': a.available_rooms,
            'description': getattr(a, 'description', ''),
            'amenities': getattr(a, 'amenities', []),
            'is_active': getattr(a, 'is_active', True)
        } for a in accs]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/accommodation/rooms', methods=['GET'])
@jwt_required()
@admin_required
def get_accommodation_rooms():
    try:
        rooms = AccommodationRoom.query.all()
        result = [{
            'id': r.id,
            'block_name': r.block_name,
            'room_number': r.room_number,
            'room_type': r.room_type,
            'capacity': r.capacity,
            'current_occupants': r.current_occupants,
            'is_available': r.is_available,
            'has_kitchen': r.has_kitchen,
            'has_shower': r.has_shower,
            'has_study_table': r.has_study_table,
            'has_bed': r.has_bed
        } for r in rooms]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/accommodation/applications', methods=['GET'])
@jwt_required()
@admin_required
def get_accommodation_registrations():
    try:
        apps = AccommodationRegistration.query.order_by(AccommodationRegistration.created_at.desc()).all()
        result = []
        for app in apps:
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
        application.status = 'allocated'
        application.allocated_room_id = room.id
        application.allocated_room_number = room.room_number
        application.allocated_block = room.block_name
        room.current_occupants += 1
        if room.current_occupants >= room.capacity:
            room.is_available = False
        db.session.commit()
        if application.student and application.student.user_id:
            notification = Notification(
                user_id=application.student.user_id,
                title='Accommodation Allocated',
                message=f'You have been allocated room {room.room_number} in Block {room.block_name}. Please check in within 48 hours.',
                notification_type='success'
            )
            db.session.add(notification)
            db.session.commit()
        return jsonify({'message': 'Accommodation allocated successfully', 'room_number': room.room_number, 'block': room.block_name}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Allocate accommodation error: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== STAFF QUERIES MANAGEMENT ====================
@admin_bp.route('/tickets', methods=['GET'])
@jwt_required()
@admin_required
def get_staff_queries():
    try:
        status = request.args.get('status')
        priority = request.args.get('priority')
        limit = request.args.get('limit', type=int)
        query = StaffQuery.query.order_by(StaffQuery.created_at.desc())
        if status:
            query = query.filter_by(status=status)
        if priority:
            query = query.filter_by(priority=priority)
        if limit:
            query = query.limit(limit)
        queries = query.all()
        return jsonify([q.to_dict() for q in queries]), 200
    except Exception as e:
        print(f"Get staff queries error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/tickets/<int:ticket_id>', methods=['GET'])
@jwt_required()
@admin_required
def get_staff_query(ticket_id):
    try:
        ticket = StaffQuery.query.get(ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        return jsonify(ticket.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/tickets', methods=['POST'])
@jwt_required()
def create_staff_query():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))
        if not user:
            return jsonify({'error': 'User not found'}), 404
        data = request.get_json()
        if not data.get('subject') or not data.get('message'):
            return jsonify({'error': 'Missing fields'}), 400
        student = Student.query.filter_by(user_id=user.id).first()
        staff_name = f"{student.first_name} {student.last_name}" if student else user.username
        department = data.get('department') or (student.program.program_name if student and student.program else 'General')
        ticket = StaffQuery(
            staff_id=user.id,
            staff_name=staff_name,
            staff_email=user.email,
            department=department,
            subject=data['subject'],
            message=data['message'],
            priority=data.get('priority', 'medium'),
            status='pending',
            responses=[]
        )
        db.session.add(ticket)
        db.session.commit()
        return jsonify(ticket.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/tickets/<int:ticket_id>/respond', methods=['POST'])
@jwt_required()
@admin_required
def respond_to_ticket(ticket_id):
    try:
        ticket = StaffQuery.query.get(ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        data = request.get_json()
        message = data.get('message')
        if not message:
            return jsonify({'error': 'Response message required'}), 400
        current_user_id = get_jwt_identity()
        user = User.query.get(int(current_user_id))
        admin_name = user.username or 'Registrar'
        response_entry = {
            'admin': admin_name,
            'message': message,
            'date': datetime.utcnow().isoformat()
        }
        if not ticket.responses:
            ticket.responses = []
        ticket.responses.append(response_entry)
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'Response added', 'responses': ticket.responses}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/tickets/<int:ticket_id>/resolve', methods=['POST'])
@jwt_required()
@admin_required
def resolve_ticket(ticket_id):
    try:
        ticket = StaffQuery.query.get(ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        ticket.status = 'resolved'
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'Ticket resolved'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/tickets/stats', methods=['GET'])
@jwt_required()
@admin_required
def get_ticket_stats():
    try:
        total = StaffQuery.query.count()
        pending = StaffQuery.query.filter_by(status='pending').count()
        resolved = StaffQuery.query.filter_by(status='resolved').count()
        high_priority = StaffQuery.query.filter_by(priority='high', status='pending').count()
        return jsonify({'total': total, 'pending': pending, 'resolved': resolved, 'high_priority': high_priority}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== REGISTRATION MANAGEMENT (REGISTRAR) ====================
@admin_bp.route('/registrations/pending', methods=['GET'])
@jwt_required()
@admin_required
def get_pending_registrations():
    try:
        registrations = Registration.query.filter_by(registration_status='pending').order_by(Registration.created_at.desc()).all()
        result = []
        for reg in registrations:
            student = Student.query.get(reg.student_id)
            if not student:
                continue
            enrollments = Enrollment.query.filter_by(registration_id=reg.id, status='registered').all()
            modules = [f"{e.module.module_code} - {e.module.module_name}" for e in enrollments if e.module]
            prev_records = AcademicRecord.query.filter_by(student_id=student.id).order_by(AcademicRecord.created_at.desc()).first()
            prev_results = [{'semester_gpa': float(prev_records.semester_gpa) if prev_records else 0, 'academic_status': prev_records.academic_status if prev_records else 'N/A'}] if prev_records else []
            result.append({
                'id': reg.id,
                'student_number': student.student_number,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'program': student.program.program_name if student.program else 'N/A',
                'semester': f"Semester {reg.semester.semester_number} ({reg.academic_year.year_name})" if reg.semester and reg.academic_year else 'N/A',
                'year_of_study': reg.year_of_study,
                'sponsorship': 'government' if student.is_government_sponsored else 'private',
                'modules': modules,
                'previous_results': prev_results,
                'gpa': float(student.current_gpa) if student.current_gpa else None,
                'status': reg.registration_status
            })
        return jsonify(result), 200
    except Exception as e:
        print(f"Error fetching pending registrations: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/registrations/approved', methods=['GET'])
@jwt_required()
@admin_required
def get_approved_registrations():
    try:
        registrations = Registration.query.filter_by(registration_status='approved').order_by(Registration.created_at.desc()).all()
        result = []
        for reg in registrations:
            student = Student.query.get(reg.student_id)
            if not student:
                continue
            enrollments = Enrollment.query.filter_by(registration_id=reg.id, status='registered').all()
            modules = [f"{e.module.module_code} - {e.module.module_name}" for e in enrollments if e.module]
            result.append({
                'id': reg.id,
                'student_number': student.student_number,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'program': student.program.program_name if student.program else 'N/A',
                'semester': f"Semester {reg.semester.semester_number} ({reg.academic_year.year_name})" if reg.semester and reg.academic_year else 'N/A',
                'year_of_study': reg.year_of_study,
                'sponsorship': 'government' if student.is_government_sponsored else 'private',
                'modules': modules,
                'status': reg.registration_status
            })
        return jsonify(result), 200
    except Exception as e:
        print(f"Error fetching approved registrations: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/registrations/rejected', methods=['GET'])
@jwt_required()
@admin_required
def get_rejected_registrations():
    try:
        registrations = Registration.query.filter_by(registration_status='rejected').order_by(Registration.created_at.desc()).all()
        result = []
        for reg in registrations:
            student = Student.query.get(reg.student_id)
            if not student:
                continue
            enrollments = Enrollment.query.filter_by(registration_id=reg.id, status='registered').all()
            modules = [f"{e.module.module_code} - {e.module.module_name}" for e in enrollments if e.module]
            result.append({
                'id': reg.id,
                'student_number': student.student_number,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'program': student.program.program_name if student.program else 'N/A',
                'semester': f"Semester {reg.semester.semester_number} ({reg.academic_year.year_name})" if reg.semester and reg.academic_year else 'N/A',
                'year_of_study': reg.year_of_study,
                'sponsorship': 'government' if student.is_government_sponsored else 'private',
                'modules': modules,
                'status': reg.registration_status
            })
        return jsonify(result), 200
    except Exception as e:
        print(f"Error fetching rejected registrations: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/registrations/<int:reg_id>/approve', methods=['POST'])
@jwt_required()
@admin_required
def approve_registration(reg_id):
    try:
        registration = Registration.query.get(reg_id)
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404
        if registration.registration_status != 'pending':
            return jsonify({'error': f'Registration already {registration.registration_status}'}), 400
        registration.registration_status = 'approved'
        registration.approved_by = get_jwt_identity()
        registration.approved_at = datetime.utcnow()
        db.session.commit()
        student = Student.query.get(registration.student_id)
        if student and student.user_id:
            notification = Notification(user_id=student.user_id, title='Registration Approved', message='Your semester registration has been approved.', notification_type='success')
            db.session.add(notification)
            db.session.commit()
        return jsonify({'message': 'Registration approved successfully'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error approving registration: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/registrations/<int:reg_id>/reject', methods=['POST'])
@jwt_required()
@admin_required
def reject_registration(reg_id):
    try:
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        registration = Registration.query.get(reg_id)
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404
        if registration.registration_status != 'pending':
            return jsonify({'error': f'Registration already {registration.registration_status}'}), 400
        registration.registration_status = 'rejected'
        registration.notes = f"Rejected by Registrar: {reason}"
        db.session.commit()
        student = Student.query.get(registration.student_id)
        if student and student.user_id:
            notification = Notification(user_id=student.user_id, title='Registration Rejected', message=f'Your semester registration was rejected. Reason: {reason}.', notification_type='error')
            db.session.add(notification)
            db.session.commit()
        return jsonify({'message': 'Registration rejected'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error rejecting registration: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== SYSTEM SETTINGS ====================
@admin_bp.route('/settings', methods=['GET'])
@jwt_required()
@admin_required
def get_settings():
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
    try:
        data = request.get_json()
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

# ==================== PERSISTENT SYSTEM CONFIGURATION ====================
@admin_bp.route('/config', methods=['GET'])
@jwt_required()
@admin_required
def get_system_config():
    try:
        configs = SystemConfig.query.all()
        result = {}
        for cfg in configs:
            result[cfg.config_key] = cfg.get_value()
        defaults = {'ENABLE_2FA_FOR_STAFF': False, 'ENABLE_EMAIL_VERIFICATION': True, 'ENABLE_CHATBOT': True, 'ENABLE_ONLINE_CLASSES': True, 'SESSION_TIMEOUT_MINUTES': 30, 'MAX_LOGIN_ATTEMPTS': 5}
        for k, v in defaults.items():
            if k not in result:
                result[k] = v
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/config', methods=['POST'])
@jwt_required()
@admin_required
def update_system_config():
    try:
        data = request.get_json()
        for key, value in data.items():
            cfg = SystemConfig.query.filter_by(config_key=key).first()
            if not cfg:
                if isinstance(value, bool):
                    cfg_type = 'boolean'
                elif isinstance(value, int):
                    cfg_type = 'integer'
                elif isinstance(value, float):
                    cfg_type = 'float'
                elif isinstance(value, dict) or isinstance(value, list):
                    cfg_type = 'json'
                else:
                    cfg_type = 'string'
                cfg = SystemConfig(config_key=key, config_type=cfg_type, updated_by=get_jwt_identity())
                db.session.add(cfg)
            cfg.set_value(value)
            cfg.updated_at = datetime.utcnow()
            cfg.updated_by = get_jwt_identity()
        db.session.commit()
        return jsonify({'message': 'Configuration saved'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== CSV EXPORTS ====================
@admin_bp.route('/export/government-sponsored', methods=['GET'])
@jwt_required()
@admin_required
def export_government_sponsored():
    try:
        students = Student.query.filter_by(is_government_sponsored=True, is_active=True).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Student Number','First Name','Last Name','Email','Phone','Program','Campus','Current Year','Current GPA','Previous Semester GPA','Enrollment Date','Academic Status','DTEF Sponsor Number'])
        for s in students:
            prev = AcademicRecord.query.filter_by(student_id=s.id).order_by(AcademicRecord.created_at.desc()).first()
            writer.writerow([s.student_number, s.first_name, s.last_name, s.email, s.phone or '', s.program.program_name if s.program else '', s.campus.campus_name if s.campus else '', s.current_year, float(s.current_gpa) if s.current_gpa else 0, float(prev.semester_gpa) if prev else 0, s.enrollment_date.isoformat() if s.enrollment_date else '', s.academic_status, s.dtef_sponsor_number or ''])
        output.seek(0)
        return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')), mimetype='text/csv', as_attachment=True, download_name=f'government_sponsored_students_{datetime.now().strftime("%Y%m%d")}.csv')
    except Exception as e:
        print(f"Export error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/export/self-sponsored', methods=['GET'])
@jwt_required()
@admin_required
def export_self_sponsored():
    try:
        students = Student.query.filter_by(is_government_sponsored=False, is_active=True).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Student Number','First Name','Last Name','Email','Phone','Program','Campus','Current Year','Current GPA','Previous Semester GPA','Enrollment Date','Academic Status','Outstanding Balance'])
        for s in students:
            registrations = Registration.query.filter_by(student_id=s.id).all()
            outstanding = sum((reg.total_fees or 0) - (reg.paid_amount or 0) for reg in registrations)
            prev = AcademicRecord.query.filter_by(student_id=s.id).order_by(AcademicRecord.created_at.desc()).first()
            writer.writerow([s.student_number, s.first_name, s.last_name, s.email, s.phone or '', s.program.program_name if s.program else '', s.campus.campus_name if s.campus else '', s.current_year, float(s.current_gpa) if s.current_gpa else 0, float(prev.semester_gpa) if prev else 0, s.enrollment_date.isoformat() if s.enrollment_date else '', s.academic_status, f"P{outstanding:,.2f}"])
        output.seek(0)
        return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')), mimetype='text/csv', as_attachment=True, download_name=f'self_sponsored_students_{datetime.now().strftime("%Y%m%d")}.csv')
    except Exception as e:
        print(f"Export error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/export/accommodation-applicants', methods=['GET'])
@jwt_required()
@admin_required
def export_accommodation_applicants():
    try:
        apps = AccommodationRegistration.query.filter_by(status='pending').all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Student Number','Student Name','Program','Campus','Room Type','Block Preference','Emergency Contact','Medical Conditions','Application Date','Status'])
        for a in apps:
            s = Student.query.get(a.student_id)
            writer.writerow([s.student_number if s else '', f"{s.first_name} {s.last_name}" if s else '', s.program.program_name if s and s.program else '', s.campus.campus_name if s and s.campus else '', a.room_type, a.block_preference or '', f"{a.emergency_contact_name} ({a.emergency_contact_phone})", a.medical_conditions or '', a.created_at.strftime('%Y-%m-%d'), a.status])
        output.seek(0)
        return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')), mimetype='text/csv', as_attachment=True, download_name=f'accommodation_applicants_{datetime.now().strftime("%Y%m%d")}.csv')
    except Exception as e:
        print(f"Export error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ==================== REPORTS ====================
@admin_bp.route('/reports/students', methods=['GET'])
@jwt_required()
@admin_required
def get_student_report():
    try:
        report = {
            'total_students': Student.query.count(),
            'government_sponsored': Student.query.filter_by(is_government_sponsored=True).count(),
            'self_sponsored': Student.query.filter_by(is_government_sponsored=False).count(),
            'by_program': {},
            'by_campus': {},
            'by_year': {},
            'by_status': {},
            'by_admission': {}
        }
        for p in Program.query.all():
            report['by_program'][p.program_name] = Student.query.filter_by(program_id=p.id).count()
        for c in Campus.query.all():
            report['by_campus'][c.campus_name] = Student.query.filter_by(campus_id=c.id).count()
        for y in range(1,5):
            report['by_year'][f'Year {y}'] = Student.query.filter_by(current_year=y).count()
        for s in ['good_standing','probation','suspended','graduated']:
            report['by_status'][s] = Student.query.filter_by(academic_status=s).count()
        for a in ['accepted','pending','rejected','deferred','graduated']:
            report['by_admission'][a] = Student.query.filter_by(admission_status=a).count()
        return jsonify(report), 200
    except Exception as e:
        print(f"Report error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/reports/payments', methods=['GET'])
@jwt_required()
@admin_required
def get_payment_report():
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
            'by_payment_type': {}
        }
        for method in ['cash','bank_transfer','card','mobile_money']:
            total = sum(p.amount for p in payments if p.payment_method == method and p.status == 'completed')
            report['by_method'][method] = float(total)
        for ptype in ['registration','tuition','supplementary','resit','retake','accommodation']:
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
    try:
        db.session.execute(text('SELECT 1'))
        db_status = 'connected'
    except Exception as e:
        db_status = f'disconnected: {str(e)}'
    return jsonify({'status': 'healthy' if db_status == 'connected' else 'degraded', 'database': db_status, 'users': User.query.count(), 'students': Student.query.count(), 'timestamp': datetime.now().isoformat()}), 200

# ==================== ERROR HANDLERS ====================
@admin_bp.errorhandler(500)
def admin_internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@admin_bp.errorhandler(404)
def admin_not_found(error):
    return jsonify({'error': 'Resource not found'}), 404