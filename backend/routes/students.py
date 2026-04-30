# backend/routes/students.py
from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
import csv
import io
import os
import traceback
from werkzeug.utils import secure_filename

from models import db, Student, Module, Program, ExamRegistration, AccommodationRegistration, Registration, Enrollment, Campus, FeesConfig, AcademicRecord, User, Course, AcademicYear, Semester, ProgramModule, OnlineMeeting, Notification, StudentQuery
from backend.utils.email import EmailService  # <-- ADD THIS IMPORT

# MOODLE INTEGRATION: import the Moodle client and configuration
from services.moodle_integration import MoodleClient
from config import MOODLE_URL, MOODLE_API_TOKEN

students_bp = Blueprint('students', __name__)

# MOODLE INTEGRATION: initialise the Moodle client once
moodle = MoodleClient(MOODLE_URL, MOODLE_API_TOKEN)

# ============================================
# Helper for file uploads
# ============================================
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, subfolder=''):
    """Save file and return relative path."""
    if not file or file.filename == '':
        return None
    if not allowed_file(file.filename):
        raise ValueError("File type not allowed. Allowed: pdf, jpg, jpeg, png")
    filename = secure_filename(f"{datetime.utcnow().timestamp()}_{file.filename}")
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    documents_dir = os.path.join(upload_folder, 'documents', subfolder)
    os.makedirs(documents_dir, exist_ok=True)
    path = os.path.join(documents_dir, filename)
    file.save(path)
    return path

# ============================================
# DASHBOARD
# ============================================
@students_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        program = student.program
        campus = student.campus

        current_reg = Registration.query.filter_by(
            student_id=student.id,
            registration_status='approved'
        ).order_by(Registration.created_at.desc()).first()

        current_courses = []
        if current_reg:
            enrollments = Enrollment.query.filter_by(registration_id=current_reg.id, status='registered').all()
            current_courses = [{'id': e.module.id, 'code': e.module.module_code, 'name': e.module.module_name} for e in enrollments if e.module]

        credits_earned = student.total_credits_earned or 0
        total_credits_needed = program.total_credits if program and program.total_credits else 0
        completion_percent = (credits_earned / total_credits_needed * 100) if total_credits_needed > 0 else 0

        gpa_trend = 'steady'
        previous_academic = AcademicRecord.query.filter_by(student_id=student.id).order_by(AcademicRecord.created_at.desc()).first()
        if previous_academic and student.current_gpa:
            if student.current_gpa > previous_academic.semester_gpa:
                gpa_trend = 'up'
            elif student.current_gpa < previous_academic.semester_gpa:
                gpa_trend = 'down'

        registered_exams = ExamRegistration.query.filter_by(student_id=student.id).count()
        exam_fees_due = sum(e.fee or 0 for e in ExamRegistration.query.filter_by(student_id=student.id, payment_status='pending').all())

        accommodation = AccommodationRegistration.query.filter_by(student_id=student.id).order_by(AccommodationRegistration.created_at.desc()).first()
        accommodation_status = accommodation.status if accommodation else 'Not Applied'
        room_number = accommodation.allocated_room_number if accommodation else None
        block_name = accommodation.allocated_block if accommodation else None

        total_fees = 0
        paid_amount = 0
        outstanding = 0
        if current_reg:
            total_fees = current_reg.total_fees or 0
            paid_amount = current_reg.paid_amount or 0
            outstanding = total_fees - paid_amount
            if student.is_government_sponsored:
                outstanding = (current_reg.supplementary_exam_fees or 0) + (current_reg.resit_fees or 0) + (current_reg.retake_fees or 0)

        dashboard_data = {
            'student_number': student.student_number,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'email': student.email,
            'phone': student.phone,
            'program_name': program.program_name if program else None,
            'program_code': program.program_code if program else None,
            'campus_name': campus.campus_name if campus else None,
            'academic_status': student.academic_status,
            'current_gpa': float(student.current_gpa) if student.current_gpa else 0.0,
            'credits_earned': credits_earned,
            'completion_percent': round(completion_percent, 1),
            'gpa_trend': gpa_trend,
            'current_courses': current_courses,
            'current_year': student.current_year,
            'is_government_sponsored': student.is_government_sponsored,
            'wants_accommodation': student.wants_accommodation,
            'accommodation_status': accommodation_status,
            'room_number': room_number,
            'block_name': block_name,
            'registered_exams': registered_exams,
            'exam_fees_due': exam_fees_due,
            'total_fees': total_fees,
            'paid_amount': paid_amount,
            'outstanding_balance': outstanding
        }

        return jsonify(dashboard_data), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# PROFILE (for semester registration page)
# ============================================
@students_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_student_profile():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404

        user = User.query.get(user_id)
        program = student.program
        campus = student.campus

        return jsonify({
            'id': student.id,
            'student_number': student.student_number,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'email': student.email,
            'phone': student.phone,
            'program_id': student.program_id,
            'program_name': program.program_name if program else None,
            'program_code': program.program_code if program else None,
            'campus_id': student.campus_id,
            'campus_name': campus.campus_name if campus else None,
            'current_year': student.current_year,
            'is_government_sponsored': student.is_government_sponsored,
            'wants_accommodation': student.wants_accommodation,
            'admission_status': student.admission_status,
            'academic_status': student.academic_status
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# MY MODULES (CURRENT COURSES)
# ============================================
@students_bp.route('/my-modules', methods=['GET'])
@jwt_required()
def get_my_modules():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        current_reg = Registration.query.filter_by(
            student_id=student.id,
            registration_status='approved'
        ).order_by(Registration.created_at.desc()).first()

        if not current_reg:
            return jsonify({'modules': []}), 200

        enrollments = Enrollment.query.filter_by(registration_id=current_reg.id, status='registered').all()
        modules_data = []
        for enrollment in enrollments:
            if enrollment.module:
                modules_data.append({
                    'id': enrollment.module.id,
                    'code': enrollment.module.module_code,
                    'name': enrollment.module.module_name,
                    'credits': enrollment.module.credits,
                    'semester': enrollment.module.semester,
                    'year_level': enrollment.module.year_level,
                    'has_practicals': enrollment.module.has_practicals,
                    'module_type': enrollment.module.module_type,
                    'grade': enrollment.grade,
                    'grade_points': float(enrollment.grade_points) if enrollment.grade_points else None
                })
        return jsonify({'modules': modules_data}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# ACTIVITY FEED
# ============================================
@students_bp.route('/activity', methods=['GET'])
@jwt_required()
def get_activity():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).limit(10).all()
        activities = []
        for n in notifications:
            activities.append({
                'icon': 'fa-bell',
                'description': n.title + ': ' + n.message[:100],
                'date': n.created_at.isoformat()
            })
        if not activities:
            activities.append({
                'icon': 'fa-rocket',
                'description': 'Welcome to GIPS College Student Portal',
                'date': datetime.utcnow().isoformat()
            })
        return jsonify({'activities': activities}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# COURSES (legacy)
# ============================================
@students_bp.route('/courses', methods=['GET'])
@jwt_required()
def get_courses():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        current_reg = Registration.query.filter_by(
            student_id=student.id,
            registration_status='approved'
        ).order_by(Registration.created_at.desc()).first()

        if not current_reg:
            return jsonify({'courses': [], 'message': 'No active registration'}), 200

        enrollments = Enrollment.query.filter_by(
            registration_id=current_reg.id,
            status='registered'
        ).all()

        courses_data = []
        for enrollment in enrollments:
            if enrollment.module:
                courses_data.append({
                    'id': enrollment.module.id,
                    'code': enrollment.module.module_code,
                    'name': enrollment.module.module_name,
                    'credits': enrollment.module.credits,
                    'semester': enrollment.module.semester,
                    'year_level': enrollment.module.year_level,
                    'has_practicals': enrollment.module.has_practicals,
                    'module_type': enrollment.module.module_type,
                    'enrollment_date': enrollment.enrollment_date.isoformat() if enrollment.enrollment_date else None,
                    'grade': enrollment.grade,
                    'grade_points': float(enrollment.grade_points) if enrollment.grade_points else None
                })

        return jsonify({
            'courses': courses_data,
            'count': len(courses_data),
            'current_year': student.current_year
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# GET STUDENT BY ID (admin/staff)
# ============================================
@students_bp.route('/<int:student_id>', methods=['GET'])
@jwt_required()
def get_student(student_id):
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        requesting_student = Student.query.filter_by(user_id=user_id).first()
        user = User.query.get(user_id)
        is_admin = user and (user.role in ['admin', 'administrator', 'staff'])
        if not is_admin and (requesting_student and requesting_student.id != student_id):
            return jsonify({'error': 'Unauthorized'}), 403

        student = Student.query.get(student_id)
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        program = student.program
        campus = student.campus

        student_data = {
            'id': student.id,
            'student_number': student.student_number,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'email': student.email,
            'phone': student.phone,
            'program': program.program_name if program else None,
            'program_code': program.program_code if program else None,
            'campus': campus.campus_name if campus else None,
            'academic_status': student.academic_status,
            'admission_status': student.admission_status,
            'gpa': float(student.current_gpa) if student.current_gpa else 0,
            'current_year': student.current_year,
            'is_government_sponsored': student.is_government_sponsored,
            'wants_accommodation': student.wants_accommodation,
            'enrollment_date': student.enrollment_date.isoformat() if student.enrollment_date else None,
            'created_at': student.created_at.isoformat() if student.created_at else None
        }

        return jsonify(student_data), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# UPDATE STUDENT (admin/staff or self)
# ============================================
@students_bp.route('/<int:student_id>', methods=['PUT'])
@jwt_required()
def update_student(student_id):
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        user = User.query.get(user_id)
        is_admin = user and (user.role in ['admin', 'administrator', 'staff'])
        if not is_admin and user_id != student.user_id:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request data'}), 400

        if 'phone' in data:
            student.phone = data['phone']
        if 'alternative_phone' in data:
            student.alternative_phone = data['alternative_phone']
        if 'physical_address' in data:
            student.physical_address = data['physical_address']
        if 'postal_address' in data:
            student.postal_address = data['postal_address']
        if 'emergency_contact_name' in data:
            student.emergency_contact_name = data['emergency_contact_name']
        if 'emergency_contact_phone' in data:
            student.emergency_contact_phone = data['emergency_contact_phone']
        if 'emergency_contact_relationship' in data:
            student.emergency_contact_relationship = data['emergency_contact_relationship']

        if is_admin:
            if 'gpa' in data:
                student.current_gpa = data['gpa']
            if 'academic_status' in data:
                student.academic_status = data['academic_status']
            if 'admission_status' in data:
                student.admission_status = data['admission_status']
            if 'current_year' in data:
                student.current_year = data['current_year']
            if 'is_government_sponsored' in data:
                student.is_government_sponsored = data['is_government_sponsored']
            if 'wants_accommodation' in data:
                student.wants_accommodation = data['wants_accommodation']
            if 'program_id' in data:
                student.program_id = data['program_id']
            if 'campus_id' in data:
                student.campus_id = data['campus_id']

        student.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'message': 'Student updated successfully',
            'student_id': student.id
        }), 200
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# MY PROFILE (detailed)
# ============================================
@students_bp.route('/my-profile', methods=['GET'])
@jwt_required()
def get_my_profile():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404

        program = student.program
        campus = student.campus

        profile_data = {
            'id': student.id,
            'student_number': student.student_number,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'initials': student.initials,
            'email': student.email,
            'phone': student.phone,
            'alternative_phone': student.alternative_phone,
            'physical_address': student.physical_address,
            'postal_address': student.postal_address,
            'date_of_birth': student.date_of_birth.isoformat() if student.date_of_birth else None,
            'nationality': student.nationality,
            'id_number': student.id_number,
            'program_id': student.program_id,
            'program_name': program.program_name if program else None,
            'program_code': program.program_code if program else None,
            'campus_id': student.campus_id,
            'campus_name': campus.campus_name if campus else None,
            'campus_location': campus.campus_location if campus else None,
            'current_year': student.current_year,
            'current_gpa': float(student.current_gpa) if student.current_gpa else 0,
            'total_credits_earned': student.total_credits_earned,
            'is_ovc': student.is_ovc,
            'is_government_sponsored': student.is_government_sponsored,
            'dtef_sponsor_number': student.dtef_sponsor_number,
            'wants_accommodation': student.wants_accommodation,
            'admission_status': student.admission_status,
            'academic_status': student.academic_status,
            'enrollment_date': student.enrollment_date.isoformat() if student.enrollment_date else None,
            'expected_graduation': student.expected_graduation.isoformat() if student.expected_graduation else None
        }

        return jsonify(profile_data), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# REGISTER MODULE
# ============================================
@students_bp.route('/register-module', methods=['POST'])
@jwt_required()
def register_module():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        data = request.get_json()
        module_id = data.get('module_id')
        if not module_id:
            return jsonify({'error': 'Module ID required'}), 400

        module = Module.query.get(module_id)
        if not module:
            return jsonify({'error': 'Module not found'}), 404

        if module.year_level != student.current_year:
            return jsonify({'error': 'Module not available for your current year'}), 400

        current_reg = Registration.query.filter_by(
            student_id=student.id,
            registration_status='approved'
        ).order_by(Registration.created_at.desc()).first()

        if not current_reg:
            return jsonify({'error': 'No active registration found. Please complete semester registration first.'}), 400

        existing = Enrollment.query.filter_by(
            registration_id=current_reg.id,
            module_id=module_id,
            status='registered'
        ).first()
        if existing:
            return jsonify({'error': 'Already registered for this module'}), 400

        enrollment = Enrollment(
            registration_id=current_reg.id,
            student_id=student.id,
            module_id=module_id,
            enrollment_date=date.today(),
            status='registered'
        )
        db.session.add(enrollment)
        db.session.commit()

        return jsonify({
            'message': 'Successfully registered for module',
            'module': {
                'id': module.id,
                'code': module.module_code,
                'name': module.module_name,
                'credits': module.credits
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# MY RESULTS
# ============================================
@students_bp.route('/my-results', methods=['GET'])
@jwt_required()
def get_my_results():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        enrollments = Enrollment.query.filter_by(
            student_id=student.id,
            status='completed'
        ).order_by(Enrollment.created_at.desc()).all()

        academic_records = AcademicRecord.query.filter_by(
            student_id=student.id
        ).order_by(AcademicRecord.created_at.desc()).all()

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

        records = []
        for record in academic_records:
            records.append({
                'semester_gpa': float(record.semester_gpa) if record.semester_gpa else 0,
                'cumulative_gpa': float(record.cumulative_gpa) if record.cumulative_gpa else 0,
                'academic_status': record.academic_status,
                'dean_list': record.dean_list,
                'class_standing': record.class_standing,
                'created_at': record.created_at.isoformat()
            })

        return jsonify({
            'student': {
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
            'academic_records': records,
            'total_credits_earned': student.total_credits_earned
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# EXPORT TRANSCRIPT
# ============================================
@students_bp.route('/export-my-transcript', methods=['GET'])
@jwt_required()
def export_my_transcript():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        enrollments = Enrollment.query.filter_by(
            student_id=student.id,
            status='completed'
        ).order_by(Enrollment.created_at).all()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(['GIPS COLLEGE STUDENT TRANSCRIPT'])
        writer.writerow(['Student Name:', f'{student.first_name} {student.last_name}'])
        writer.writerow(['Student Number:', student.student_number])
        writer.writerow(['Program:', student.program.program_name if student.program else 'N/A'])
        writer.writerow(['Current GPA:', f"{float(student.current_gpa) if student.current_gpa else 0:.2f}"])
        writer.writerow(['Academic Status:', student.academic_status])
        writer.writerow([])
        writer.writerow(['Module Code', 'Module Name', 'Credits', 'Semester', 'Grade', 'Grade Points'])

        for enrollment in enrollments:
            if enrollment.module:
                writer.writerow([
                    enrollment.module.module_code,
                    enrollment.module.module_name,
                    enrollment.module.credits,
                    f"Semester {enrollment.module.semester}",
                    enrollment.grade or 'N/A',
                    f"{float(enrollment.grade_points) if enrollment.grade_points else 0:.2f}"
                ])

        writer.writerow([])
        writer.writerow(['Total Credits Earned:', student.total_credits_earned])
        writer.writerow(['Cumulative GPA:', f"{float(student.current_gpa) if student.current_gpa else 0:.2f}"])

        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'transcript_{student.student_number}_{datetime.now().strftime("%Y%m%d")}.csv'
        )
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# ACCOMMODATION STATUS
# ============================================
@students_bp.route('/accommodation-status', methods=['GET'])
@jwt_required()
def get_accommodation_status():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        application = AccommodationRegistration.query.filter_by(
            student_id=student.id
        ).order_by(AccommodationRegistration.created_at.desc()).first()

        if not application:
            return jsonify({
                'has_applied': False,
                'status': 'not_applied',
                'wants_accommodation': student.wants_accommodation
            }), 200

        return jsonify({
            'has_applied': True,
            'application_id': application.id,
            'status': application.status,
            'room_type': application.room_type,
            'block_preference': application.block_preference,
            'allocated_room_number': application.allocated_room_number,
            'allocated_block': application.allocated_block,
            'created_at': application.created_at.isoformat(),
            'updated_at': application.updated_at.isoformat(),
            'wants_accommodation': student.wants_accommodation
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# APPLICATION STATUS (admission)
# ============================================
@students_bp.route('/application-status', methods=['GET'])
@jwt_required()
def get_application_status():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        return jsonify({
            'admission_status': student.admission_status,
            'student_number': student.student_number,
            'program_name': student.program.program_name if student.program else None,
            'message': 'Your application is being processed.' if student.admission_status == 'pending' else None
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# CURRENT REGISTRATION (semester)
# ============================================
@students_bp.route('/current-registration', methods=['GET'])
@jwt_required()
def get_current_registration():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        current_reg = Registration.query.filter_by(
            student_id=student.id
        ).order_by(Registration.created_at.desc()).first()

        if not current_reg:
            return jsonify({
                'has_registration': False,
                'status': None,
                'registration_id': None
            }), 200

        return jsonify({
            'has_registration': True,
            'status': current_reg.registration_status,
            'registration_id': current_reg.id,
            'year_of_study': current_reg.year_of_study,
            'created_at': current_reg.created_at.isoformat()
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# CAMPUS DETAILS (for frontend accommodation check)
# ============================================
@students_bp.route('/campuses/<int:campus_id>', methods=['GET'])
@jwt_required()
def get_campus_details(campus_id):
    try:
        campus = Campus.query.get(campus_id)
        if not campus:
            return jsonify({'error': 'Campus not found'}), 404

        return jsonify({
            'id': campus.id,
            'campus_name': campus.campus_name,
            'campus_code': campus.campus_code,
            'campus_location': campus.campus_location,
            'has_accommodation': campus.has_accommodation if hasattr(campus, 'has_accommodation') else False
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# AVAILABLE COURSES (for registration)
# ============================================
@students_bp.route('/available-courses', methods=['GET'])
@jwt_required()
def get_available_courses():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        program_id = request.args.get('program_id', type=int)
        if not program_id:
            program_id = student.program_id

        semester = request.args.get('semester', 1, type=int)

        program_modules = ProgramModule.query.filter_by(program_id=program_id).all()
        module_ids = [pm.module_id for pm in program_modules]

        if not module_ids:
            return jsonify([]), 200

        modules = Module.query.filter(
            Module.id.in_(module_ids),
            Module.year_level == student.current_year,
            Module.semester == semester,
            Module.is_active == True
        ).all()

        courses_data = []
        for module in modules:
            courses_data.append({
                'id': module.id,
                'code': module.module_code,
                'name': module.module_name,
                'credits': module.credits,
                'semester': module.semester,
                'year_level': module.year_level,
                'has_practicals': module.has_practicals,
                'module_type': module.module_type,
                'description': module.description
            })

        return jsonify(courses_data), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# REGISTER SEMESTER (submit registration with accommodation)
# ============================================
@students_bp.route('/register-semester', methods=['POST'])
@jwt_required()
def register_semester():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        if student.admission_status != 'accepted':
            return jsonify({'error': 'Your application has not been accepted yet. Please wait for admission decision.'}), 400

        existing_reg = Registration.query.filter_by(
            student_id=student.id
        ).order_by(Registration.created_at.desc()).first()
        if existing_reg and existing_reg.registration_status in ['pending', 'approved', 'completed']:
            return jsonify({'error': 'You already have a pending or approved registration for this semester.'}), 400

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request data'}), 400

        course_ids = data.get('course_ids', [])
        semester = data.get('semester', 1)
        wants_accommodation = data.get('wants_accommodation', False)
        accepted_rules = data.get('accepted_rules', False)

        if not course_ids:
            return jsonify({'error': 'Please select at least one course to register.'}), 400

        if wants_accommodation and not accepted_rules:
            return jsonify({'error': 'You must accept the accommodation rules and regulations.'}), 400

        program_modules = ProgramModule.query.filter_by(program_id=student.program_id).all()
        available_module_ids = [pm.module_id for pm in program_modules]
        available_modules = Module.query.filter(
            Module.id.in_(available_module_ids),
            Module.year_level == student.current_year,
            Module.semester == semester,
            Module.is_active == True
        ).all()
        valid_module_ids = [m.id for m in available_modules]

        invalid_ids = [cid for cid in course_ids if cid not in valid_module_ids]
        if invalid_ids:
            return jsonify({'error': f'Invalid module(s) selected: {invalid_ids}. They are not available for your program and year.'}), 400

        is_gov_sponsored = student.is_government_sponsored
        registration_fee = 630 if not is_gov_sponsored else 0
        tuition_fee = 32550 if not is_gov_sponsored else 0
        exam_fee_per_module = 5145 if not is_gov_sponsored else 0
        total_fees = registration_fee + tuition_fee + (len(course_ids) * exam_fee_per_module)

        academic_year_obj = AcademicYear.query.filter_by(is_current=True).first()
        if not academic_year_obj:
            academic_year_obj = AcademicYear.query.first()
            if not academic_year_obj:
                return jsonify({'error': 'No academic year configured. Please contact administrator.'}), 500

        semester_obj = Semester.query.filter_by(
            academic_year_id=academic_year_obj.id,
            semester_number=semester
        ).first()
        if not semester_obj:
            return jsonify({'error': f'Semester {semester} not configured for the current academic year.'}), 500

        registration = Registration(
            student_id=student.id,
            academic_year_id=academic_year_obj.id,
            semester_id=semester_obj.id,
            year_of_study=student.current_year,
            registration_date=date.today(),
            sponsorship_type='government_sponsored' if is_gov_sponsored else 'private',
            registration_status='pending',
            payment_status='pending' if total_fees > 0 else 'exempted',
            total_fees=total_fees,
            paid_amount=0,
            exempted_amount=0 if not is_gov_sponsored else registration_fee + tuition_fee,
            bgcse_points_verified=True,
            documents_verified=True
        )

        db.session.add(registration)
        db.session.flush()

        selected_modules = Module.query.filter(Module.id.in_(course_ids)).all()

        for module in selected_modules:
            enrollment = Enrollment(
                registration_id=registration.id,
                student_id=student.id,
                module_id=module.id,
                enrollment_date=date.today(),
                status='registered'
            )
            db.session.add(enrollment)

        if wants_accommodation and is_gov_sponsored:
            campus = Campus.query.get(student.campus_id)
            if campus and campus.has_accommodation:
                accommodation_reg = AccommodationRegistration(
                    student_id=student.id,
                    registration_id=registration.id,
                    wants_accommodation=True,
                    room_type='bachelor_pad',
                    has_accepted_rules=accepted_rules,
                    status='pending'
                )
                db.session.add(accommodation_reg)
                student.wants_accommodation = True
        elif wants_accommodation and not is_gov_sponsored:
            return jsonify({'error': 'Accommodation is only available for government-sponsored students.'}), 400

        # ========== MOODLE INTEGRATION ==========
        try:
            if not student.moodle_user_id:
                temp_password = f"Temp{student.student_number}!"
                moodle_user_id = moodle.create_user(
                    username=student.student_number,
                    password=temp_password,
                    firstname=student.first_name,
                    lastname=student.last_name,
                    email=student.email
                )
                student.moodle_user_id = moodle_user_id
                db.session.add(student)
                db.session.flush()

            for module in selected_modules:
                moodle.enrol_user(student.moodle_user_id, module.id, roleid=5)
        except Exception as moodle_err:
            current_app.logger.error(f"Moodle sync failed for student {student.id}: {moodle_err}")

        db.session.commit()

        # ========== SEND EMAIL CONFIRMATION ==========
        try:
            semester_name = f"Semester {semester} {academic_year_obj.year_name}"
            EmailService.send_semester_registration_confirmation(
                user_email=student.email,
                first_name=student.first_name,
                registration_id=registration.id,
                semester_name=semester_name,
                total_fees=total_fees
            )
        except Exception as email_err:
            current_app.logger.error(f"Failed to send semester registration email to {student.email}: {email_err}")

        return jsonify({
            'success': True,
            'message': 'Semester registration submitted successfully. Pending finance approval.',
            'registration_id': registration.id,
            'total_fees': total_fees,
            'status': registration.registration_status,
            'accommodation_requested': wants_accommodation and is_gov_sponsored
        }), 201

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# ONLINE CLASSES FOR STUDENTS
# ============================================
@students_bp.route('/online-classes', methods=['GET'])
@jwt_required()
def get_student_online_classes():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404

        enrolled_courses = [sc.course_id for sc in student.student_courses if sc.status == 'registered']
        if not enrolled_courses:
            return jsonify({'meetings': []}), 200

        now = datetime.utcnow()
        meetings = OnlineMeeting.query.filter(
            OnlineMeeting.course_id.in_(enrolled_courses),
            OnlineMeeting.is_active == True,
            OnlineMeeting.scheduled_start >= now
        ).order_by(OnlineMeeting.scheduled_start.asc()).all()

        result = []
        for m in meetings:
            result.append({
                'id': m.id,
                'course_code': m.course.course_code,
                'course_name': m.course.course_name,
                'meeting_link': m.meeting_link,
                'meeting_platform': m.meeting_platform,
                'scheduled_start': m.scheduled_start.isoformat() if m.scheduled_start else None,
                'scheduled_end': m.scheduled_end.isoformat() if m.scheduled_end else None,
                'duration_minutes': m.duration_minutes,
                'meeting_id': m.meeting_id,
                'meeting_password': m.meeting_password
            })
        return jsonify({'meetings': result}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# STUDENT STATUS (for frontend checks)
# ============================================
@students_bp.route('/status', methods=['GET'])
@jwt_required()
def get_student_status():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404

        accommodation_applied = AccommodationRegistration.query.filter_by(student_id=student.id).first() is not None
        current_reg = Registration.query.filter_by(
            student_id=student.id,
            registration_status='approved'
        ).order_by(Registration.created_at.desc()).first()

        can_apply_accommodation = False
        if student.admission_status == 'accepted' and student.wants_accommodation and not accommodation_applied:
            campus = Campus.query.get(student.campus_id)
            if campus and campus.has_accommodation:
                can_apply_accommodation = True

        return jsonify({
            'admission_status': student.admission_status,
            'academic_status': student.academic_status,
            'current_year': student.current_year,
            'is_registered': current_reg is not None,
            'can_apply_accommodation': can_apply_accommodation,
            'accommodation_applied': accommodation_applied,
            'has_outstanding_fees': False,
            'message': 'Status retrieved successfully'
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# DOCUMENT MANAGEMENT
# ============================================
@students_bp.route('/documents', methods=['GET'])
@jwt_required()
def get_student_documents():
    """Get all documents uploaded by the student."""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404

        docs = []

        if student.bgcse_certificate_path:
            docs.append({
                'id': 1,
                'document_type': 'bgcse_certificate',
                'file_name': os.path.basename(student.bgcse_certificate_path),
                'file_url': f'/uploads/{student.bgcse_certificate_path}',
                'uploaded_at': student.updated_at.isoformat() if student.updated_at else None
            })

        if student.id_document_path:
            docs.append({
                'id': 2,
                'document_type': 'id_document',
                'file_name': os.path.basename(student.id_document_path),
                'file_url': f'/uploads/{student.id_document_path}',
                'uploaded_at': student.updated_at.isoformat() if student.updated_at else None
            })

        if student.passport_photo_path:
            docs.append({
                'id': 3,
                'document_type': 'passport_photo',
                'file_name': os.path.basename(student.passport_photo_path),
                'file_url': f'/uploads/{student.passport_photo_path}',
                'uploaded_at': student.updated_at.isoformat() if student.updated_at else None
            })

        return jsonify(docs), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@students_bp.route('/documents', methods=['POST'])
@jwt_required()
def upload_student_document():
    """Upload a document (BGCSE certificate, ID copy, passport photo)."""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404

        doc_type = request.form.get('document_type') or request.args.get('document_type')
        if not doc_type:
            return jsonify({'error': 'document_type is required (bgcse_certificate, id_document, passport_photo)'}), 400

        field_map = {
            'bgcse_certificate': 'bgcse_certificate_path',
            'id_document': 'id_document_path',
            'passport_photo': 'passport_photo_path'
        }
        if doc_type not in field_map:
            return jsonify({'error': 'Invalid document_type. Allowed: bgcse_certificate, id_document, passport_photo'}), 400

        file = request.files.get('file')
        if not file:
            return jsonify({'error': 'No file uploaded'}), 400

        subfolder = doc_type
        file_path = save_uploaded_file(file, subfolder)
        if not file_path:
            return jsonify({'error': 'File upload failed'}), 500

        setattr(student, field_map[doc_type], file_path)
        student.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{doc_type} uploaded successfully',
            'file_path': file_path,
            'file_url': f'/uploads/{file_path}'
        }), 200
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# FAILED MODULES (for exam registration)
# ============================================
@students_bp.route('/failed-modules', methods=['GET'])
@jwt_required()
def get_failed_modules():
    """Get modules where student failed and need supplementary/resit/retake."""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404

        failed_enrollments = Enrollment.query.filter(
            Enrollment.student_id == student.id,
            Enrollment.status == 'failed'
        ).all()

        result = []
        for enrollment in failed_enrollments:
            module = enrollment.module
            if not module:
                continue
            attempts = 1  # placeholder
            exam_type = 'supplementary' if attempts == 1 else 'retake'
            fee = 300 if exam_type == 'supplementary' else 600 if exam_type == 'resit' else 1000

            registered = ExamRegistration.query.filter_by(
                student_id=student.id,
                course_id=module.id,
                exam_type=exam_type
            ).first() is not None

            result.append({
                'id': module.id,
                'code': module.module_code,
                'name': module.module_name,
                'previous_grade': enrollment.grade or 'F',
                'exam_type': exam_type,
                'fee': fee,
                'registered': registered
            })

        return jsonify(result), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# REGISTER FOR SUPPLEMENTARY/RETAKE EXAM
# ============================================
@students_bp.route('/exam-registration', methods=['POST'])
@jwt_required()
def register_for_exam():
    """Register for supplementary/resit/retake exam."""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404

        data = request.get_json()
        module_id = data.get('module_id')
        exam_type = data.get('exam_type')

        if not module_id or not exam_type:
            return jsonify({'error': 'module_id and exam_type required'}), 400

        module = Module.query.get(module_id)
        if not module:
            return jsonify({'error': 'Module not found'}), 404

        fee_map = {'supplementary': 300, 'resit': 600, 'retake': 1000}
        fee = fee_map.get(exam_type, 0)

        existing = ExamRegistration.query.filter_by(
            student_id=student.id,
            course_id=module_id,
            exam_type=exam_type
        ).first()
        if existing:
            return jsonify({'error': 'Already registered for this exam'}), 400

        exam_reg = ExamRegistration(
            student_id=student.id,
            course_id=module_id,
            exam_type=exam_type,
            semester_id=None,
            academic_year_id=None,
            registration_date=datetime.utcnow(),
            fee=fee,
            payment_status='pending',
            is_government_sponsored=student.is_government_sponsored
        )
        db.session.add(exam_reg)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Successfully registered for {exam_type} exam',
            'fee': fee,
            'registration_id': exam_reg.id
        }), 201
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# STUDENT QUERIES (SUPPORT TICKETS)
# ============================================
@students_bp.route('/queries', methods=['GET'])
@jwt_required()
def get_student_queries():
    """Get all queries submitted by the logged‑in student."""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404

        queries = StudentQuery.query.filter_by(student_id=student.id).order_by(StudentQuery.created_at.desc()).all()
        return jsonify([q.to_dict() for q in queries]), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@students_bp.route('/queries/<int:query_id>', methods=['GET'])
@jwt_required()
def get_student_query(query_id):
    """Get a specific query by ID (with responses)."""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404

        query = StudentQuery.query.get(query_id)
        if not query or query.student_id != student.id:
            return jsonify({'error': 'Query not found'}), 404

        return jsonify(query.to_dict()), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@students_bp.route('/queries', methods=['POST'])
@jwt_required()
def create_student_query():
    """Create a new query (support ticket)."""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request data'}), 400

        subject = data.get('subject')
        category = data.get('category', 'General')
        message = data.get('message')

        if not subject or not message:
            return jsonify({'error': 'Subject and message are required'}), 400

        query = StudentQuery(
            student_id=student.id,
            subject=subject,
            category=category,
            message=message,
            status='pending',
            responses=[]
        )
        db.session.add(query)
        db.session.commit()

        return jsonify(query.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# AVATAR UPLOAD
# ============================================
@students_bp.route('/avatar', methods=['POST'])
@jwt_required()
def upload_avatar():
    """Upload student profile picture."""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404

        file = request.files.get('avatar')
        if not file:
            return jsonify({'error': 'No file provided'}), 400

        # Placeholder – implement if avatar_path column exists
        return jsonify({
            'success': True,
            'message': 'Avatar updated successfully',
            'avatar_url': '/uploads/avatars/sample.jpg'
        }), 200
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# UPDATE PROFILE (PUT)
# ============================================
@students_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_student_profile():
    """Update student profile (name, email, phone, bio, address, social links, password)."""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request data'}), 400

        moodle_updates = {}
        old_firstname = student.first_name
        old_lastname = student.last_name
        old_email = user.email

        if 'first_name' in data:
            student.first_name = data['first_name']
            moodle_updates['firstname'] = data['first_name']
        if 'last_name' in data:
            student.last_name = data['last_name']
            moodle_updates['lastname'] = data['last_name']
        if 'phone' in data:
            student.phone = data['phone']
        if 'bio' in data:
            student.bio = data['bio']
        if 'address' in data:
            student.physical_address = data['address']
        if 'city' in data:
            student.city = data['city']
        if 'postal_code' in data:
            student.postal_code = data['postal_code']

        if 'email' in data and data['email'] != user.email:
            existing = User.query.filter_by(email=data['email']).first()
            if existing and existing.id != user.id:
                return jsonify({'error': 'Email already in use'}), 409
            user.email = data['email']
            user.username = data['email']
            moodle_updates['email'] = data['email']

        current_pw = data.get('current_password')
        new_pw = data.get('new_password')
        if new_pw:
            if not current_pw:
                return jsonify({'error': 'Current password required to change password'}), 400
            if not user.check_password(current_pw):
                return jsonify({'error': 'Current password is incorrect'}), 401
            if len(new_pw) < 8:
                return jsonify({'error': 'New password must be at least 8 characters'}), 400
            if not any(c.isupper() for c in new_pw) or not any(c.islower() for c in new_pw) or not any(c.isdigit() for c in new_pw):
                return jsonify({'error': 'New password must contain uppercase, lowercase, and digit'}), 400
            user.set_password(new_pw)

        student.updated_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        db.session.commit()

        if student.moodle_user_id and moodle_updates:
            try:
                moodle.update_user(student.moodle_user_id, **moodle_updates)
            except Exception as moodle_err:
                current_app.logger.error(f"Failed to update Moodle user {student.moodle_user_id}: {moodle_err}")

        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': {
                'first_name': student.first_name,
                'last_name': student.last_name,
                'email': user.email,
                'role': user.role
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500