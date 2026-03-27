# backend/routes/campus.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import traceback
import json

from models import db, User, Student, Campus, Program, Faculty, Department, AccommodationRegistration, AccommodationRoom

campus_bp = Blueprint('campus', __name__)


# ============================================
# CAMPUS MANAGEMENT ROUTES
# ============================================

@campus_bp.route('/campuses', methods=['GET'])
@jwt_required()
def get_all_campuses():
    """Get all campuses with details"""
    try:
        campuses = Campus.query.all()
        result = []
        
        for campus in campuses:
            # Count programs at this campus
            program_count = Program.query.filter_by(campus_id=campus.id, is_active=True).count()
            
            result.append({
                'id': campus.id,
                'campus_code': campus.campus_code,
                'campus_name': campus.campus_name,
                'campus_location': campus.campus_location,
                'campus_address': campus.campus_address,
                'has_accommodation': campus.has_accommodation,
                'is_main_campus': campus.is_main_campus,
                'program_count': program_count,
                'created_at': campus.created_at.isoformat() if campus.created_at else None
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[CAMPUS] Get all campuses error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@campus_bp.route('/campuses/<int:campus_id>', methods=['GET'])
@jwt_required()
def get_campus_by_id(campus_id):
    """Get a specific campus by ID"""
    try:
        campus = Campus.query.get(campus_id)
        
        if not campus:
            return jsonify({'error': 'Campus not found'}), 404
        
        result = {
            'id': campus.id,
            'campus_code': campus.campus_code,
            'campus_name': campus.campus_name,
            'campus_location': campus.campus_location,
            'campus_address': campus.campus_address,
            'has_accommodation': campus.has_accommodation,
            'is_main_campus': campus.is_main_campus,
            'created_at': campus.created_at.isoformat() if campus.created_at else None
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[CAMPUS] Get campus by ID error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@campus_bp.route('/campuses/<int:campus_id>/programs', methods=['GET'])
@jwt_required()
def get_campus_programs(campus_id):
    """Get all programs offered at a specific campus"""
    try:
        campus = Campus.query.get(campus_id)
        
        if not campus:
            return jsonify({'error': 'Campus not found'}), 404
        
        programs = Program.query.filter_by(
            campus_id=campus_id,
            is_active=True
        ).all()
        
        result = []
        for program in programs:
            result.append({
                'id': program.id,
                'program_code': program.program_code,
                'program_name': program.program_name,
                'program_type': program.program_type.type_name if program.program_type else None,
                'duration_years': program.duration_years,
                'total_credits': program.total_credits,
                'min_bgcse_points': program.min_bgcse_points,
                'description': program.description,
                'career_opportunities': program.career_opportunities,
                'faculty_id': program.faculty_id,
                'faculty_name': program.faculty.faculty_name if program.faculty else None,
                'department_id': program.department_id,
                'department_name': program.department.department_name if program.department else None
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[CAMPUS] Get campus programs error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@campus_bp.route('/campuses/<int:campus_id>/programs/filter', methods=['POST'])
@jwt_required()
def filter_campus_programs(campus_id):
    """Filter programs at a campus by faculty or search term"""
    try:
        campus = Campus.query.get(campus_id)
        
        if not campus:
            return jsonify({'error': 'Campus not found'}), 404
        
        data = request.get_json() or {}
        faculty_id = data.get('faculty_id')
        search_term = data.get('search_term', '').strip()
        
        query = Program.query.filter_by(campus_id=campus_id, is_active=True)
        
        if faculty_id:
            query = query.filter_by(faculty_id=faculty_id)
        
        if search_term:
            query = query.filter(
                db.or_(
                    Program.program_name.ilike(f'%{search_term}%'),
                    Program.program_code.ilike(f'%{search_term}%')
                )
            )
        
        programs = query.all()
        
        result = []
        for program in programs:
            result.append({
                'id': program.id,
                'program_code': program.program_code,
                'program_name': program.program_name,
                'program_type': program.program_type.type_name if program.program_type else None,
                'duration_years': program.duration_years,
                'min_bgcse_points': program.min_bgcse_points,
                'description': program.description,
                'faculty_id': program.faculty_id,
                'faculty_name': program.faculty.faculty_name if program.faculty else None
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[CAMPUS] Filter campus programs error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# STUDENT CAMPUS SELECTION ROUTES
# ============================================

@campus_bp.route('/student/selection', methods=['GET'])
@jwt_required()
def get_student_campus_selection():
    """Get the current student's campus and program selection"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        student = Student.query.filter_by(user_id=user_id).first()
        
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        
        result = {
            'student_id': student.id,
            'student_number': student.student_number,
            'campus_id': student.campus_id,
            'campus': None,
            'program_id': student.program_id,
            'program': None,
            'selection_date': student.updated_at.isoformat() if student.updated_at else None,
            'wants_accommodation': student.wants_accommodation,
            'is_government_sponsored': student.is_government_sponsored
        }
        
        if student.campus:
            result['campus'] = {
                'id': student.campus.id,
                'campus_code': student.campus.campus_code,
                'campus_name': student.campus.campus_name,
                'campus_location': student.campus.campus_location,
                'has_accommodation': student.campus.has_accommodation
            }
        
        if student.program:
            result['program'] = {
                'id': student.program.id,
                'program_code': student.program.program_code,
                'program_name': student.program.program_name,
                'duration_years': student.program.duration_years,
                'faculty_name': student.program.faculty.faculty_name if student.program.faculty else None
            }
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[CAMPUS] Get student selection error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@campus_bp.route('/student/selection', methods=['POST'])
@jwt_required()
def update_student_campus_selection():
    """Update student's campus and program selection"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        data = request.get_json()
        campus_id = data.get('campus_id')
        program_id = data.get('program_id')
        notes = data.get('notes')
        
        if not campus_id or not program_id:
            return jsonify({'error': 'Campus ID and Program ID are required'}), 400
        
        student = Student.query.filter_by(user_id=user_id).first()
        
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        
        # Validate campus exists
        campus = Campus.query.get(campus_id)
        if not campus:
            return jsonify({'error': 'Campus not found'}), 404
        
        # Validate program exists and is offered at the selected campus
        program = Program.query.filter_by(id=program_id, campus_id=campus_id, is_active=True).first()
        if not program:
            return jsonify({'error': 'Program not found or not offered at selected campus'}), 404
        
        # Check BGCSE requirements if not OVC
        if not student.is_ovc and student.bgcse_points and student.bgcse_points < program.min_bgcse_points:
            return jsonify({'error': f'Minimum {program.min_bgcse_points} BGCSE points required for this program'}), 400
        
        # Update student selection
        old_campus_id = student.campus_id
        old_program_id = student.program_id
        
        student.campus_id = campus_id
        student.program_id = program_id
        student.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log the change
        print(f"[CAMPUS] Student {student.student_number} updated selection: Campus {old_campus_id}->{campus_id}, Program {old_program_id}->{program_id}")
        
        return jsonify({
            'success': True,
            'message': 'Campus and program selection updated successfully',
            'campus': campus.campus_name,
            'program': program.program_name,
            'wants_accommodation': student.wants_accommodation
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[CAMPUS] Update student selection error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@campus_bp.route('/student/selection/campus', methods=['PUT'])
@jwt_required()
def update_student_campus_only():
    """Update student's campus selection only"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        data = request.get_json()
        campus_id = data.get('campus_id')
        
        if not campus_id:
            return jsonify({'error': 'Campus ID is required'}), 400
        
        student = Student.query.filter_by(user_id=user_id).first()
        
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        
        campus = Campus.query.get(campus_id)
        if not campus:
            return jsonify({'error': 'Campus not found'}), 404
        
        student.campus_id = campus_id
        student.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Campus selection updated successfully',
            'campus': campus.campus_name
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[CAMPUS] Update campus only error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# PROGRAM QUERY ROUTES
# ============================================

@campus_bp.route('/programs', methods=['GET'])
@jwt_required()
def get_all_programs():
    """Get all active programs with optional filtering"""
    try:
        faculty_id = request.args.get('faculty_id', type=int)
        campus_id = request.args.get('campus_id', type=int)
        search = request.args.get('search', '')
        
        query = Program.query.filter_by(is_active=True)
        
        if faculty_id:
            query = query.filter_by(faculty_id=faculty_id)
        
        if campus_id:
            query = query.filter_by(campus_id=campus_id)
        
        if search:
            query = query.filter(
                db.or_(
                    Program.program_name.ilike(f'%{search}%'),
                    Program.program_code.ilike(f'%{search}%')
                )
            )
        
        programs = query.all()
        
        result = []
        for program in programs:
            result.append({
                'id': program.id,
                'program_code': program.program_code,
                'program_name': program.program_name,
                'program_type_id': program.program_type_id,
                'program_type': program.program_type.type_name if program.program_type else None,
                'duration_years': program.duration_years,
                'total_credits': program.total_credits,
                'min_bgcse_points': program.min_bgcse_points,
                'description': program.description,
                'career_opportunities': program.career_opportunities,
                'faculty_id': program.faculty_id,
                'faculty_name': program.faculty.faculty_name if program.faculty else None,
                'department_id': program.department_id,
                'department_name': program.department.department_name if program.department else None,
                'campus_id': program.campus_id,
                'campus_name': program.campus.campus_name if program.campus else None
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[CAMPUS] Get all programs error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@campus_bp.route('/programs/<int:program_id>', methods=['GET'])
@jwt_required()
def get_program_by_id(program_id):
    """Get a specific program by ID with full details"""
    try:
        program = Program.query.get(program_id)
        
        if not program:
            return jsonify({'error': 'Program not found'}), 404
        
        result = {
            'id': program.id,
            'program_code': program.program_code,
            'program_name': program.program_name,
            'program_type_id': program.program_type_id,
            'program_type': program.program_type.type_name if program.program_type else None,
            'duration_years': program.duration_years,
            'total_credits': program.total_credits,
            'min_bgcse_points': program.min_bgcse_points,
            'description': program.description,
            'career_opportunities': program.career_opportunities,
            'entry_requirements': program.entry_requirements,
            'faculty_id': program.faculty_id,
            'faculty_name': program.faculty.faculty_name if program.faculty else None,
            'department_id': program.department_id,
            'department_name': program.department.department_name if program.department else None,
            'campus_id': program.campus_id,
            'campus_name': program.campus.campus_name if program.campus else None,
            'campus_location': program.campus.campus_location if program.campus else None,
            'is_active': program.is_active
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[CAMPUS] Get program by ID error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# FACULTY ROUTES
# ============================================

@campus_bp.route('/faculties', methods=['GET'])
@jwt_required()
def get_all_faculties():
    """Get all faculties"""
    try:
        faculties = Faculty.query.all()
        
        result = []
        for faculty in faculties:
            # Count departments and programs
            department_count = Department.query.filter_by(faculty_id=faculty.id).count()
            program_count = Program.query.filter_by(faculty_id=faculty.id, is_active=True).count()
            
            result.append({
                'id': faculty.id,
                'faculty_code': faculty.faculty_code,
                'faculty_name': faculty.faculty_name,
                'description': faculty.description,
                'dean_name': faculty.dean_name,
                'dean_email': faculty.dean_email,
                'department_count': department_count,
                'program_count': program_count
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[CAMPUS] Get faculties error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@campus_bp.route('/faculties/<int:faculty_id>/departments', methods=['GET'])
@jwt_required()
def get_faculty_departments(faculty_id):
    """Get departments under a specific faculty"""
    try:
        faculty = Faculty.query.get(faculty_id)
        
        if not faculty:
            return jsonify({'error': 'Faculty not found'}), 404
        
        departments = Department.query.filter_by(faculty_id=faculty_id).all()
        
        result = []
        for dept in departments:
            result.append({
                'id': dept.id,
                'department_code': dept.department_code,
                'department_name': dept.department_name,
                'hod_name': dept.hod_name,
                'hod_email': dept.hod_email
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[CAMPUS] Get faculty departments error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@campus_bp.route('/faculties/<int:faculty_id>/programs', methods=['GET'])
@jwt_required()
def get_faculty_programs(faculty_id):
    """Get programs under a specific faculty"""
    try:
        faculty = Faculty.query.get(faculty_id)
        
        if not faculty:
            return jsonify({'error': 'Faculty not found'}), 404
        
        programs = Program.query.filter_by(faculty_id=faculty_id, is_active=True).all()
        
        result = []
        for program in programs:
            result.append({
                'id': program.id,
                'program_code': program.program_code,
                'program_name': program.program_name,
                'duration_years': program.duration_years,
                'min_bgcse_points': program.min_bgcse_points,
                'campus_id': program.campus_id,
                'campus_name': program.campus.campus_name if program.campus else None
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[CAMPUS] Get faculty programs error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# ELIGIBILITY CHECK ROUTES
# ============================================

@campus_bp.route('/eligibility/check', methods=['POST'])
@jwt_required()
def check_eligibility():
    """Check if a student is eligible for a program at a campus"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        data = request.get_json()
        program_id = data.get('program_id')
        campus_id = data.get('campus_id')
        
        if not program_id or not campus_id:
            return jsonify({'error': 'Program ID and Campus ID are required'}), 400
        
        student = Student.query.filter_by(user_id=user_id).first()
        
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        
        program = Program.query.get(program_id)
        if not program:
            return jsonify({'error': 'Program not found'}), 404
        
        campus = Campus.query.get(campus_id)
        if not campus:
            return jsonify({'error': 'Campus not found'}), 404
        
        checks = {
            'program_offered_at_campus': program.campus_id == campus_id,
            'bgcse_requirement_met': student.bgcse_points >= program.min_bgcse_points if student.bgcse_points else False,
            'is_ovc_exempt': student.is_ovc,
            'program_active': program.is_active,
            'campus_has_accommodation': campus.has_accommodation
        }
        
        eligible = (
            checks['program_offered_at_campus'] and
            checks['program_active'] and
            (checks['bgcse_requirement_met'] or checks['is_ovc_exempt'])
        )
        
        return jsonify({
            'eligible': eligible,
            'checks': checks,
            'message': 'You are eligible for this program!' if eligible else 'You do not meet the requirements for this program.',
            'program': {
                'name': program.program_name,
                'min_points': program.min_bgcse_points
            },
            'student': {
                'bgcse_points': student.bgcse_points,
                'is_ovc': student.is_ovc
            }
        }), 200
        
    except Exception as e:
        print(f"[CAMPUS] Check eligibility error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@campus_bp.route('/eligibility/programs', methods=['GET'])
@jwt_required()
def get_eligible_programs():
    """Get all programs the current student is eligible for"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        student = Student.query.filter_by(user_id=user_id).first()
        
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        
        # Get all active programs
        all_programs = Program.query.filter_by(is_active=True).all()
        
        eligible_programs = []
        for program in all_programs:
            is_eligible = False
            if student.is_ovc:
                is_eligible = True
            elif student.bgcse_points and student.bgcse_points >= program.min_bgcse_points:
                is_eligible = True
            
            if is_eligible:
                eligible_programs.append({
                    'id': program.id,
                    'program_code': program.program_code,
                    'program_name': program.program_name,
                    'duration_years': program.duration_years,
                    'min_bgcse_points': program.min_bgcse_points,
                    'campus_id': program.campus_id,
                    'campus_name': program.campus.campus_name if program.campus else None,
                    'faculty_name': program.faculty.faculty_name if program.faculty else None
                })
        
        return jsonify({
            'eligible_programs': eligible_programs,
            'total_eligible': len(eligible_programs),
            'student_bgcse_points': student.bgcse_points,
            'is_ovc': student.is_ovc
        }), 200
        
    except Exception as e:
        print(f"[CAMPUS] Get eligible programs error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# ADMIN CAMPUS MANAGEMENT ROUTES
# ============================================

@campus_bp.route('/admin/campuses', methods=['POST'])
@jwt_required()
def create_campus():
    """Create a new campus (Admin only)"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator']:
            return jsonify({'error': 'Admin access required'}), 403
        
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        data = request.get_json()
        
        # Check if campus code already exists
        existing = Campus.query.filter_by(campus_code=data.get('campus_code')).first()
        if existing:
            return jsonify({'error': 'Campus code already exists'}), 409
        
        campus = Campus(
            campus_code=data.get('campus_code'),
            campus_name=data.get('campus_name'),
            campus_location=data.get('campus_location'),
            campus_address=data.get('campus_address'),
            has_accommodation=data.get('has_accommodation', False),
            is_main_campus=data.get('is_main_campus', False)
        )
        
        db.session.add(campus)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Campus created successfully',
            'campus': {
                'id': campus.id,
                'campus_code': campus.campus_code,
                'campus_name': campus.campus_name
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"[CAMPUS] Create campus error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@campus_bp.route('/admin/campuses/<int:campus_id>', methods=['PUT'])
@jwt_required()
def update_campus(campus_id):
    """Update campus details (Admin only)"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator']:
            return jsonify({'error': 'Admin access required'}), 403
        
        campus = Campus.query.get(campus_id)
        if not campus:
            return jsonify({'error': 'Campus not found'}), 404
        
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        data = request.get_json()
        
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
        
        return jsonify({
            'success': True,
            'message': 'Campus updated successfully',
            'campus': {
                'id': campus.id,
                'campus_code': campus.campus_code,
                'campus_name': campus.campus_name
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[CAMPUS] Update campus error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@campus_bp.route('/admin/campuses/<int:campus_id>', methods=['DELETE'])
@jwt_required()
def delete_campus(campus_id):
    """Delete a campus (Admin only)"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator']:
            return jsonify({'error': 'Admin access required'}), 403
        
        campus = Campus.query.get(campus_id)
        if not campus:
            return jsonify({'error': 'Campus not found'}), 404
        
        # Check if there are students or programs associated
        student_count = Student.query.filter_by(campus_id=campus_id).count()
        program_count = Program.query.filter_by(campus_id=campus_id).count()
        
        if student_count > 0 or program_count > 0:
            return jsonify({
                'error': f'Cannot delete campus. It has {student_count} students and {program_count} programs associated.'
            }), 400
        
        db.session.delete(campus)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Campus deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[CAMPUS] Delete campus error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# STATISTICS ROUTES
# ============================================

@campus_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_campus_statistics():
    """Get campus-wide statistics"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        is_admin = user and user.role in ['admin', 'administrator']
        
        campuses = Campus.query.all()
        result = {
            'total_campuses': len(campuses),
            'campuses': []
        }
        
        for campus in campuses:
            student_count = Student.query.filter_by(campus_id=campus.id).count()
            program_count = Program.query.filter_by(campus_id=campus.id, is_active=True).count()
            accommodation_registrations = 0
            
            if is_admin:
                accommodation_registrations = AccommodationRegistration.query.join(Student).filter(
                    Student.campus_id == campus.id
                ).count()
            
            campus_data = {
                'id': campus.id,
                'campus_name': campus.campus_name,
                'student_count': student_count,
                'program_count': program_count,
                'has_accommodation': campus.has_accommodation,
                'accommodation_registrations': accommodation_registrations if is_admin else None
            }
            
            result['campuses'].append(campus_data)
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[CAMPUS] Get statistics error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
