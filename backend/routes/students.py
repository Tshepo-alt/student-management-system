# backend/routes/students.py
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
import csv
import io
import traceback

from models import db, Student, Module, Program, ExamRegistration, AccommodationRegistration, Registration, Enrollment, Campus, FeesConfig, AcademicRecord, User

students_bp = Blueprint('students', __name__)


@students_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    """Get student dashboard information"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        # Get program info
        program = Program.query.get(student.program_id)
        campus = Campus.query.get(student.campus_id)

        # Get pending exams
        pending_exams = ExamRegistration.query.filter_by(
            student_id=student.id,
            status='registered',
            payment_status='pending'
        ).count()

        # Get accommodation status
        accommodation = AccommodationRegistration.query.filter_by(
            student_id=student.id
        ).order_by(AccommodationRegistration.created_at.desc()).first()

        # Get current registration
        current_reg = Registration.query.filter_by(
            student_id=student.id,
            registration_status='approved'
        ).order_by(Registration.created_at.desc()).first()

        # Calculate fees
        total_fees = 0
        paid_amount = 0
        outstanding = 0
        
        if current_reg:
            total_fees = current_reg.total_fees or 0
            paid_amount = current_reg.paid_amount or 0
            outstanding = total_fees - paid_amount
            
            # For government sponsored students, only show supplementary/resit/retake fees
            if student.is_government_sponsored:
                outstanding = (current_reg.supplementary_exam_fees or 0) + \
                              (current_reg.resit_fees or 0) + \
                              (current_reg.retake_fees or 0)

        # Calculate exam fees due
        exam_fees_due = sum(e.fee or 0 for e in ExamRegistration.query.filter_by(
            student_id=student.id,
            payment_status='pending'
        ).all())

        dashboard_data = {
            'student': {
                'id': student.id,
                'student_number': student.student_number,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'email': student.email,
                'phone': student.phone,
                'current_year': student.current_year
            },
            'program': {
                'id': program.id if program else None,
                'name': program.program_name if program else None,
                'code': program.program_code if program else None
            },
            'campus': {
                'id': campus.id if campus else None,
                'name': campus.campus_name if campus else None,
                'has_accommodation': campus.has_accommodation if campus else False
            },
            'academic_status': student.academic_status,
            'gpa': float(student.current_gpa) if student.current_gpa else 0,
            'total_credits_earned': student.total_credits_earned,
            'enrollment_date': student.enrollment_date.isoformat() if student.enrollment_date else None,
            'sponsorship_type': 'Government Sponsored' if student.is_government_sponsored else 'Self Sponsored',
            'wants_accommodation': student.wants_accommodation,
            'accommodation_status': accommodation.status if accommodation else 'Not Applied',
            'accommodation_room': accommodation.allocated_room_number if accommodation else None,
            'pending_exams': pending_exams,
            'exam_fees_due': exam_fees_due,
            'total_fees': total_fees,
            'paid_amount': paid_amount,
            'outstanding_balance': outstanding
        }

        return jsonify(dashboard_data), 200

    except Exception as e:
        print(f"Dashboard error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@students_bp.route('/courses', methods=['GET'])
@jwt_required()
def get_courses():
    """Get student's enrolled modules/courses"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        # Get current registration
        current_reg = Registration.query.filter_by(
            student_id=student.id,
            registration_status='approved'
        ).order_by(Registration.created_at.desc()).first()

        if not current_reg:
            return jsonify({'courses': [], 'message': 'No active registration'}), 200

        # Get enrolled modules
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
        print(f"Get courses error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@students_bp.route('/<int:student_id>', methods=['GET'])
@jwt_required()
def get_student(student_id):
    """Get student information (admin/staff only)"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        requesting_student = Student.query.filter_by(user_id=user_id).first()
        
        # Check if user is admin or staff
        user = User.query.get(user_id)
        is_admin = user and (user.role in ['admin', 'administrator', 'staff'])
        
        # Only allow if admin/staff or the student themselves
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
        print(f"Get student error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@students_bp.route('/<int:student_id>', methods=['PUT'])
@jwt_required()
def update_student(student_id):
    """Update student information"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.get(student_id)
        
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        # Check permissions
        user = User.query.get(user_id)
        is_admin = user and (user.role in ['admin', 'administrator', 'staff'])
        
        if not is_admin and user_id != student.user_id:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request data'}), 400

        # Fields that can be updated by student
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

        # Fields that can only be updated by admin/staff
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
        print(f"Update student error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@students_bp.route('/my-profile', methods=['GET'])
@jwt_required()
def get_my_profile():
    """Get current student's own profile"""
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
        print(f"Get profile error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@students_bp.route('/register-module', methods=['POST'])
@jwt_required()
def register_module():
    """Register student for a module/course"""
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

        # Check if module is appropriate for student's year level
        if module.year_level != student.current_year:
            return jsonify({'error': 'Module not available for your current year'}), 400

        # Get current registration
        current_reg = Registration.query.filter_by(
            student_id=student.id,
            registration_status='approved'
        ).order_by(Registration.created_at.desc()).first()

        if not current_reg:
            return jsonify({
                'error': 'No active registration found. Please complete semester registration first.'
            }), 400

        # Check if already registered
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
        print(f"Register module error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@students_bp.route('/my-modules', methods=['GET'])
@jwt_required()
def get_my_modules():
    """Get modules the current student is enrolled in"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        # Get current registration
        current_reg = Registration.query.filter_by(
            student_id=student.id,
            registration_status='approved'
        ).order_by(Registration.created_at.desc()).first()

        if not current_reg:
            return jsonify({'modules': [], 'message': 'No active registration'}), 200

        enrollments = Enrollment.query.filter_by(
            registration_id=current_reg.id,
            status='registered'
        ).all()

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
                    'enrollment_date': enrollment.enrollment_date.isoformat() if enrollment.enrollment_date else None,
                    'status': enrollment.status,
                    'grade': enrollment.grade,
                    'grade_points': float(enrollment.grade_points) if enrollment.grade_points else None
                })

        return jsonify({
            'modules': modules_data,
            'count': len(modules_data),
            'total_credits': sum(m['credits'] for m in modules_data)
        }), 200

    except Exception as e:
        print(f"Get my modules error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@students_bp.route('/my-results', methods=['GET'])
@jwt_required()
def get_my_results():
    """Get current student's academic results"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        # Get all completed enrollments with grades
        enrollments = Enrollment.query.filter_by(
            student_id=student.id,
            status='completed'
        ).order_by(Enrollment.created_at.desc()).all()

        # Get academic records
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
        print(f"Get results error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@students_bp.route('/export-my-transcript', methods=['GET'])
@jwt_required()
def export_my_transcript():
    """Export student's transcript as CSV"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()
        
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        # Get all completed enrollments
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
        print(f"Export transcript error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@students_bp.route('/accommodation-status', methods=['GET'])
@jwt_required()
def get_accommodation_status():
    """Get student's accommodation application status"""
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
        print(f"Get accommodation status error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500