# backend/routes/export.py
from flask import Blueprint, request, jsonify, Response, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import csv
import io
import traceback
import json

from models import db, User, Student, Program, Campus, Faculty, Department, Registration, Payment, AcademicRecord, AccommodationRegistration, AccommodationRoom

export_bp = Blueprint('export', __name__)


# ============================================
# HELPER FUNCTIONS
# ============================================

def format_date(date_obj):
    """Format date object to string"""
    if date_obj:
        return date_obj.strftime('%Y-%m-%d')
    return ''


def format_datetime(dt_obj):
    """Format datetime object to string"""
    if dt_obj:
        return dt_obj.strftime('%Y-%m-%d %H:%M:%S')
    return ''


def format_currency(amount):
    """Format amount as currency"""
    if amount is None:
        return '0.00'
    return f'{amount:.2f}'


def generate_csv_response(data, filename, headers):
    """Generate CSV response for download"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(headers)
    
    # Write data
    for row in data:
        writer.writerow(row)
    
    # Create response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename={filename}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            'Content-Type': 'text/csv'
        }
    )


# ============================================
# STUDENT DATA EXPORTS
# ============================================

@export_bp.route('/students', methods=['GET'])
@jwt_required()
def export_students():
    """Export all students to CSV"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator', 'registrar', 'staff']:
            return jsonify({'error': 'Access denied. Admin or Registrar access required.'}), 403
        
        # Get filter parameters
        program_id = request.args.get('program_id', type=int)
        campus_id = request.args.get('campus_id', type=int)
        sponsorship = request.args.get('sponsorship')
        academic_status = request.args.get('academic_status')
        
        query = Student.query.join(User).filter(User.is_active == True)
        
        if program_id:
            query = query.filter(Student.program_id == program_id)
        if campus_id:
            query = query.filter(Student.campus_id == campus_id)
        if sponsorship:
            if sponsorship.lower() == 'government':
                query = query.filter(Student.is_government_sponsored == True)
            elif sponsorship.lower() == 'private':
                query = query.filter(Student.is_government_sponsored == False)
        if academic_status:
            query = query.filter(Student.academic_status == academic_status)
        
        students = query.all()
        
        headers = [
            'Student Number', 'First Name', 'Last Name', 'Email', 'Phone',
            'Program', 'Campus', 'Year of Study', 'Current GPA', 'Academic Status',
            'Sponsorship Type', 'OVC Status', 'Wants Accommodation', 'BGCSE Points',
            'Enrollment Date', 'Expected Graduation'
        ]
        
        data = []
        for student in students:
            data.append([
                student.student_number,
                student.first_name,
                student.last_name,
                student.email,
                student.phone or '',
                student.program.program_name if student.program else '',
                student.campus.campus_name if student.campus else '',
                str(student.current_year or ''),
                f'{student.current_gpa:.2f}' if student.current_gpa else '0.00',
                student.academic_status.replace('_', ' ').title() if student.academic_status else '',
                'Government Sponsored' if student.is_government_sponsored else 'Private/ Self Sponsored',
                'Yes' if student.is_ovc else 'No',
                'Yes' if student.wants_accommodation else 'No',
                str(student.bgcse_points or ''),
                format_date(student.enrollment_date),
                format_date(student.expected_graduation)
            ])
        
        return generate_csv_response(data, 'students_export', headers)
        
    except Exception as e:
        print(f"[EXPORT] Export students error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@export_bp.route('/students/<int:student_id>', methods=['GET'])
@jwt_required()
def export_student_details(student_id):
    """Export single student details to CSV"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        student = Student.query.get(student_id)
        
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        # Check permissions
        student_user = User.query.get(student.user_id)
        if user.role not in ['admin', 'administrator', 'registrar', 'staff'] and user.id != student.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        headers = [
            'Field', 'Value'
        ]
        
        data = [
            ['Student Number', student.student_number],
            ['First Name', student.first_name],
            ['Last Name', student.last_name],
            ['Initials', student.initials or ''],
            ['Email', student.email],
            ['Phone', student.phone or ''],
            ['Alternative Phone', student.alternative_phone or ''],
            ['Physical Address', student.physical_address or ''],
            ['Postal Address', student.postal_address or ''],
            ['Date of Birth', format_date(student.date_of_birth)],
            ['Place of Birth', student.place_of_birth or ''],
            ['Nationality', student.nationality or 'Botswana'],
            ['ID Number', student.id_number or ''],
            ['Passport Number', student.passport_number or ''],
            ['Program', student.program.program_name if student.program else ''],
            ['Campus', student.campus.campus_name if student.campus else ''],
            ['Year of Study', str(student.current_year or '')],
            ['Current GPA', f'{student.current_gpa:.2f}' if student.current_gpa else '0.00'],
            ['Academic Status', student.academic_status.replace('_', ' ').title() if student.academic_status else ''],
            ['Sponsorship Type', 'Government Sponsored' if student.is_government_sponsored else 'Private/ Self Sponsored'],
            ['DTEF Sponsor Number', student.dtef_sponsor_number or ''],
            ['OVC Status', 'Yes' if student.is_ovc else 'No'],
            ['Social Worker Name', student.social_worker_name or ''],
            ['Social Worker Contact', student.social_worker_contact or ''],
            ['BGCSE Points', str(student.bgcse_points or '')],
            ['BGCSE Year', str(student.bgcse_year or '')],
            ['BGCSE School', student.bgcse_school or ''],
            ['Wants Accommodation', 'Yes' if student.wants_accommodation else 'No'],
            ['Enrollment Date', format_date(student.enrollment_date)],
            ['Expected Graduation', format_date(student.expected_graduation)],
            ['Emergency Contact Name', student.emergency_contact_name or ''],
            ['Emergency Contact Phone', student.emergency_contact_phone or ''],
            ['Emergency Contact Relationship', student.emergency_contact_relationship or ''],
            ['Created At', format_datetime(student.created_at)],
            ['Last Updated', format_datetime(student.updated_at)]
        ]
        
        return generate_csv_response(data, f'student_{student.student_number}', headers)
        
    except Exception as e:
        print(f"[EXPORT] Export student details error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# ACADEMIC DATA EXPORTS
# ============================================

@export_bp.route('/academic-records', methods=['GET'])
@jwt_required()
def export_academic_records():
    """Export academic records to CSV"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator', 'registrar', 'lecturer']:
            return jsonify({'error': 'Access denied. Admin or Registrar access required.'}), 403
        
        program_id = request.args.get('program_id', type=int)
        academic_year = request.args.get('academic_year')
        
        query = AcademicRecord.query.join(Student).join(Registration)
        
        if program_id:
            query = query.filter(Student.program_id == program_id)
        
        records = query.all()
        
        headers = [
            'Student Number', 'Student Name', 'Program', 'Semester GPA',
            'Cumulative GPA', 'Credits Earned', 'Academic Status',
            'Dean\'s List', 'Class Standing', 'Semester', 'Academic Year'
        ]
        
        data = []
        for record in records:
            data.append([
                record.student.student_number if record.student else '',
                f"{record.student.first_name} {record.student.last_name}" if record.student else '',
                record.student.program.program_name if record.student and record.student.program else '',
                f'{record.semester_gpa:.2f}' if record.semester_gpa else '0.00',
                f'{record.cumulative_gpa:.2f}' if record.cumulative_gpa else '0.00',
                str(record.total_credits_earned or '0'),
                record.academic_status.replace('_', ' ').title() if record.academic_status else '',
                'Yes' if record.dean_list else 'No',
                record.class_standing or '',
                record.registration.semester.semester_name if record.registration and record.registration.semester else '',
                record.registration.academic_year.year_name if record.registration and record.registration.academic_year else ''
            ])
        
        return generate_csv_response(data, 'academic_records', headers)
        
    except Exception as e:
        print(f"[EXPORT] Export academic records error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@export_bp.route('/grades', methods=['GET'])
@jwt_required()
def export_grades():
    """Export student grades to CSV"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator', 'registrar', 'lecturer']:
            return jsonify({'error': 'Access denied.'}), 403
        
        program_id = request.args.get('program_id', type=int)
        semester_id = request.args.get('semester_id', type=int)
        
        from models import Enrollment
        
        query = Enrollment.query.join(Student).join(Module)
        
        if program_id:
            query = query.filter(Student.program_id == program_id)
        if semester_id:
            query = query.filter(Module.semester == semester_id)
        
        enrollments = query.all()
        
        headers = [
            'Student Number', 'Student Name', 'Module Code', 'Module Name',
            'Credits', 'Grade', 'Grade Points', 'Status', 'Semester'
        ]
        
        data = []
        for enrollment in enrollments:
            data.append([
                enrollment.student.student_number if enrollment.student else '',
                f"{enrollment.student.first_name} {enrollment.student.last_name}" if enrollment.student else '',
                enrollment.module.module_code if enrollment.module else '',
                enrollment.module.module_name if enrollment.module else '',
                str(enrollment.module.credits) if enrollment.module else '',
                enrollment.grade or '',
                f'{enrollment.grade_points:.2f}' if enrollment.grade_points else '0.00',
                enrollment.status,
                f"Semester {enrollment.module.semester}" if enrollment.module else ''
            ])
        
        return generate_csv_response(data, 'grades_export', headers)
        
    except Exception as e:
        print(f"[EXPORT] Export grades error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# FINANCIAL DATA EXPORTS
# ============================================

@export_bp.route('/payments', methods=['GET'])
@jwt_required()
def export_payments():
    """Export payment records to CSV"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator', 'finance']:
            return jsonify({'error': 'Access denied. Finance access required.'}), 403
        
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        status = request.args.get('status')
        
        query = Payment.query.join(Student)
        
        if start_date:
            query = query.filter(Payment.payment_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(Payment.payment_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        if status:
            query = query.filter(Payment.status == status)
        
        payments = query.order_by(Payment.payment_date.desc()).all()
        
        headers = [
            'Receipt Number', 'Student Number', 'Student Name', 'Amount',
            'Payment Date', 'Payment Method', 'Payment Type', 'Status',
            'Transaction ID', 'Is Government Payment'
        ]
        
        data = []
        for payment in payments:
            data.append([
                payment.receipt_number or '',
                payment.student.student_number if payment.student else '',
                f"{payment.student.first_name} {payment.student.last_name}" if payment.student else '',
                format_currency(payment.amount),
                format_date(payment.payment_date),
                payment.payment_method.replace('_', ' ').title() if payment.payment_method else '',
                payment.payment_type.replace('_', ' ').title() if payment.payment_type else '',
                payment.status,
                payment.transaction_id or '',
                'Yes' if payment.is_government_payment else 'No'
            ])
        
        return generate_csv_response(data, 'payments_export', headers)
        
    except Exception as e:
        print(f"[EXPORT] Export payments error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@export_bp.route('/fees-summary', methods=['GET'])
@jwt_required()
def export_fees_summary():
    """Export fees summary by student"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator', 'finance']:
            return jsonify({'error': 'Access denied.'}), 403
        
        from models import Registration, FeesConfig
        
        students = Student.query.filter_by(is_active=True).all()
        
        headers = [
            'Student Number', 'Student Name', 'Program', 'Sponsorship',
            'Registration Fee', 'Tuition Fee', 'Total Fees', 'Amount Paid',
            'Outstanding Balance', 'Payment Status'
        ]
        
        data = []
        for student in students:
            # Get registrations
            registrations = Registration.query.filter_by(student_id=student.id).all()
            
            total_fees = 0
            total_paid = 0
            
            for reg in registrations:
                total_fees += reg.total_fees or 0
                total_paid += reg.paid_amount or 0
            
            outstanding = total_fees - total_paid
            
            data.append([
                student.student_number,
                f"{student.first_name} {student.last_name}",
                student.program.program_name if student.program else '',
                'Government Sponsored' if student.is_government_sponsored else 'Private',
                '0.00' if student.is_government_sponsored else format_currency(2000),
                '0.00' if student.is_government_sponsored else format_currency(8500 * (student.current_year or 1)),
                format_currency(total_fees),
                format_currency(total_paid),
                format_currency(outstanding),
                'Paid' if outstanding <= 0 else 'Balance Due'
            ])
        
        return generate_csv_response(data, 'fees_summary', headers)
        
    except Exception as e:
        print(f"[EXPORT] Export fees summary error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# ACCOMMODATION DATA EXPORTS
# ============================================

@export_bp.route('/accommodation/applications', methods=['GET'])
@jwt_required()
def export_accommodation_registrations():
    """Export accommodation applications to CSV"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator', 'staff']:
            return jsonify({'error': 'Access denied.'}), 403
        
        status_filter = request.args.get('status')
        
        query = AccommodationRegistration.query.join(Student)
        
        if status_filter:
            query = query.filter(AccommodationRegistration.status == status_filter)
        
        applications = query.order_by(AccommodationRegistration.created_at.desc()).all()
        
        headers = [
            'Application ID', 'Student Number', 'Student Name', 'Email',
            'Room Type', 'Block Preference', 'Allocated Block',
            'Allocated Room', 'Status', 'Emergency Contact',
            'Emergency Phone', 'Medical Conditions', 'Applied Date'
        ]
        
        data = []
        for app in applications:
            data.append([
                str(app.id),
                app.student.student_number if app.student else '',
                f"{app.student.first_name} {app.student.last_name}" if app.student else '',
                app.student.email if app.student else '',
                'Bachelor Pad' if app.room_type == 'bachelor_pad' else 'Three-Bed Room',
                app.block_preference or '',
                app.allocated_block or '',
                app.allocated_room_number or '',
                app.status.upper(),
                app.emergency_contact_name or '',
                app.emergency_contact_phone or '',
                (app.medical_conditions or '')[:100],
                format_datetime(app.created_at)
            ])
        
        return generate_csv_response(data, 'accommodation_registrations', headers)
        
    except Exception as e:
        print(f"[EXPORT] Export accommodation applications error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@export_bp.route('/accommodation/rooms', methods=['GET'])
@jwt_required()
def export_accommodation_rooms():
    """Export room occupancy details to CSV"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator', 'staff']:
            return jsonify({'error': 'Access denied.'}), 403
        
        rooms = AccommodationRoom.query.order_by(AccommodationRoom.block_name, AccommodationRoom.room_number).all()
        
        headers = [
            'Block', 'Room Number', 'Room Type', 'Capacity',
            'Current Occupants', 'Available', 'Has Kitchen', 'Has Shower',
            'Has Study Table', 'Has Bed'
        ]
        
        data = []
        for room in rooms:
            data.append([
                room.block_name,
                room.room_number,
                'Bachelor Pad' if room.room_type == 'bachelor_pad' else 'Three-Bed Room',
                str(room.capacity),
                str(room.current_occupants),
                'Yes' if room.is_available else 'No',
                'Yes' if room.has_kitchen else 'No',
                'Yes' if room.has_shower else 'No',
                'Yes' if room.has_study_table else 'No',
                'Yes' if room.has_bed else 'No'
            ])
        
        return generate_csv_response(data, 'accommodation_rooms', headers)
        
    except Exception as e:
        print(f"[EXPORT] Export accommodation rooms error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# PROGRAM AND CAMPUS DATA EXPORTS
# ============================================

@export_bp.route('/programs', methods=['GET'])
@jwt_required()
def export_programs():
    """Export programs list to CSV"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator', 'registrar', 'staff']:
            return jsonify({'error': 'Access denied.'}), 403
        
        faculty_id = request.args.get('faculty_id', type=int)
        
        query = Program.query.filter_by(is_active=True)
        
        if faculty_id:
            query = query.filter_by(faculty_id=faculty_id)
        
        programs = query.all()
        
        headers = [
            'Program Code', 'Program Name', 'Program Type', 'Duration (Years)',
            'Total Credits', 'Min BGCSE Points', 'Faculty', 'Department',
            'Campus'
        ]
        
        data = []
        for program in programs:
            data.append([
                program.program_code,
                program.program_name,
                program.program_type.type_name if program.program_type else '',
                str(program.duration_years),
                str(program.total_credits or ''),
                str(program.min_bgcse_points or ''),
                program.faculty.faculty_name if program.faculty else '',
                program.department.department_name if program.department else '',
                program.campus.campus_name if program.campus else ''
            ])
        
        return generate_csv_response(data, 'programs_export', headers)
        
    except Exception as e:
        print(f"[EXPORT] Export programs error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@export_bp.route('/campuses', methods=['GET'])
@jwt_required()
def export_campuses():
    """Export campuses list to CSV"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator', 'registrar', 'staff']:
            return jsonify({'error': 'Access denied.'}), 403
        
        campuses = Campus.query.all()
        
        headers = [
            'Campus Code', 'Campus Name', 'Location', 'Address',
            'Has Accommodation', 'Main Campus'
        ]
        
        data = []
        for campus in campuses:
            # Count programs at this campus
            program_count = Program.query.filter_by(campus_id=campus.id).count()
            
            data.append([
                campus.campus_code,
                campus.campus_name,
                campus.campus_location or '',
                (campus.campus_address or '')[:100],
                'Yes' if campus.has_accommodation else 'No',
                'Yes' if campus.is_main_campus else 'No'
            ])
        
        return generate_csv_response(data, 'campuses_export', headers)
        
    except Exception as e:
        print(f"[EXPORT] Export campuses error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# ADMISSIONS DATA EXPORTS
# ============================================

@export_bp.route('/admissions', methods=['GET'])
@jwt_required()
def export_admissions():
    """Export admissions data to CSV"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator', 'registrar']:
            return jsonify({'error': 'Access denied.'}), 403
        
        status = request.args.get('status')
        academic_year = request.args.get('academic_year')
        
        query = Student.query
        
        if status:
            query = query.filter(Student.admission_status == status)
        
        students = query.all()
        
        headers = [
            'Student Number', 'Student Name', 'Email', 'Program', 'Campus',
            'Admission Status', 'Enrollment Date', 'BGCSE Points', 'Sponsorship',
            'OVC Status'
        ]
        
        data = []
        for student in students:
            data.append([
                student.student_number,
                f"{student.first_name} {student.last_name}",
                student.email,
                student.program.program_name if student.program else '',
                student.campus.campus_name if student.campus else '',
                student.admission_status.upper() if student.admission_status else '',
                format_date(student.enrollment_date),
                str(student.bgcse_points or ''),
                'Government' if student.is_government_sponsored else 'Private',
                'Yes' if student.is_ovc else 'No'
            ])
        
        return generate_csv_response(data, 'admissions_export', headers)
        
    except Exception as e:
        print(f"[EXPORT] Export admissions error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# DASHBOARD STATISTICS EXPORT
# ============================================

@export_bp.route('/statistics', methods=['GET'])
@jwt_required()
def export_statistics():
    """Export dashboard statistics to CSV"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator']:
            return jsonify({'error': 'Access denied.'}), 403
        
        # Student statistics by program
        programs = Program.query.filter_by(is_active=True).all()
        program_stats = []
        for program in programs:
            count = Student.query.filter_by(program_id=program.id, is_active=True).count()
            program_stats.append([
                program.program_code,
                program.program_name,
                str(count)
            ])
        
        # Student statistics by campus
        campuses = Campus.query.all()
        campus_stats = []
        for campus in campuses:
            count = Student.query.filter_by(campus_id=campus.id, is_active=True).count()
            campus_stats.append([
                campus.campus_code,
                campus.campus_name,
                str(count)
            ])
        
        # Create combined CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['GIPS COLLEGE - STATISTICS EXPORT'])
        writer.writerow([f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
        writer.writerow([])
        
        writer.writerow(['STUDENTS BY PROGRAM'])
        writer.writerow(['Program Code', 'Program Name', 'Student Count'])
        writer.writerows(program_stats)
        
        writer.writerow([])
        writer.writerow(['STUDENTS BY CAMPUS'])
        writer.writerow(['Campus Code', 'Campus Name', 'Student Count'])
        writer.writerows(campus_stats)
        
        # Summary statistics
        total_students = Student.query.filter_by(is_active=True).count()
        gov_sponsored = Student.query.filter_by(is_government_sponsored=True, is_active=True).count()
        private_sponsored = total_students - gov_sponsored
        ovc_students = Student.query.filter_by(is_ovc=True, is_active=True).count()
        wants_accommodation = Student.query.filter_by(wants_accommodation=True, is_active=True).count()
        
        writer.writerow([])
        writer.writerow(['SUMMARY STATISTICS'])
        writer.writerow(['Total Active Students', str(total_students)])
        writer.writerow(['Government Sponsored', str(gov_sponsored)])
        writer.writerow(['Private Sponsored', str(private_sponsored)])
        writer.writerow(['OVC Students', str(ovc_students)])
        writer.writerow(['Want Accommodation', str(wants_accommodation)])
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=statistics_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                'Content-Type': 'text/csv'
            }
        )
        
    except Exception as e:
        print(f"[EXPORT] Export statistics error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# CUSTOM EXPORT ROUTE
# ============================================

@export_bp.route('/custom', methods=['POST'])
@jwt_required()
def custom_export():
    """Export custom data based on query"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator']:
            return jsonify({'error': 'Access denied.'}), 403
        
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        data = request.get_json()
        table = data.get('table')
        fields = data.get('fields', [])
        filters = data.get('filters', {})
        
        if not table or not fields:
            return jsonify({'error': 'Table name and fields are required'}), 400
        
        # Map table names to models
        table_map = {
            'students': Student,
            'programs': Program,
            'campuses': Campus,
            'payments': Payment,
            'accommodation': AccommodationRegistration
        }
        
        model = table_map.get(table.lower())
        if not model:
            return jsonify({'error': f'Table {table} not available for export'}), 400
        
        # Build query
        query = model.query
        
        # Apply filters (simplified)
        for key, value in filters.items():
            if hasattr(model, key):
                query = query.filter(getattr(model, key) == value)
        
        records = query.all()
        
        # Extract data based on fields
        export_data = []
        for record in records:
            row = []
            for field in fields:
                if hasattr(record, field):
                    value = getattr(record, field)
                    if isinstance(value, datetime):
                        value = format_datetime(value)
                    elif value is None:
                        value = ''
                    row.append(str(value))
                else:
                    row.append('')
            export_data.append(row)
        
        return generate_csv_response(export_data, f'{table}_export', fields)
        
    except Exception as e:
        print(f"[EXPORT] Custom export error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
