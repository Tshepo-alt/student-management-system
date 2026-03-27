from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from models import db, ExamRegistration, Student, Course, Payment

exams_bp = Blueprint('exams', __name__)

@exams_bp.route('/supplementary', methods=['GET'])
@login_required
def get_supplementary_exams():
    """Get available supplementary exams"""
    try:
        student = Student.query.filter_by(user_id=current_user.id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        # Get courses for student's program
        courses = Course.query.filter_by(program_id=student.program_id).all()

        exams_data = [{
            'id': course.id,
            'course_code': course.code,
            'course_name': course.name,
            'credits': course.credits,
            'supplementary_fee': 50.00  # Default fee, can be customized
        } for course in courses]

        return jsonify(exams_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@exams_bp.route('/supplementary/register', methods=['POST'])
@login_required
def register_supplementary():
    """Register for supplementary exam"""
    try:
        student = Student.query.filter_by(user_id=current_user.id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        data = request.get_json()

        if 'course_id' not in data:
            return jsonify({'error': 'Course ID required'}), 400

        course = Course.query.get(data['course_id'])
        if not course:
            return jsonify({'error': 'Course not found'}), 404

        # Check if already registered
        existing = ExamRegistration.query.filter_by(
            student_id=student.id,
            course_id=data['course_id'],
            exam_type='supplementary',
            status='registered'
        ).first()

        if existing:
            return jsonify({'error': 'Already registered for this supplementary exam'}), 409

        # Create exam registration
        exam_registration = ExamRegistration(
            student_id=student.id,
            course_id=data['course_id'],
            exam_type='supplementary',
            fee=50.00,  # Standard supplementary exam fee
            payment_status='pending'
        )

        db.session.add(exam_registration)
        db.session.commit()

        return jsonify({
            'message': 'Supplementary exam registration successful',
            'registration_id': exam_registration.id,
            'fee': exam_registration.fee,
            'payment_status': exam_registration.payment_status
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@exams_bp.route('/retakes', methods=['GET'])
@login_required
def get_retake_exams():
    """Get available retake exams"""
    try:
        student = Student.query.filter_by(user_id=current_user.id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        # Get courses for student's program
        courses = Course.query.filter_by(program_id=student.program_id).all()

        exams_data = [{
            'id': course.id,
            'course_code': course.code,
            'course_name': course.name,
            'credits': course.credits,
            'retake_fee': 75.00  # Default fee, can be customized
        } for course in courses]

        return jsonify(exams_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@exams_bp.route('/retakes/register', methods=['POST'])
@login_required
def register_retake():
    """Register for retake exam"""
    try:
        student = Student.query.filter_by(user_id=current_user.id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        data = request.get_json()

        if 'course_id' not in data:
            return jsonify({'error': 'Course ID required'}), 400

        course = Course.query.get(data['course_id'])
        if not course:
            return jsonify({'error': 'Course not found'}), 404

        # Check if already registered
        existing = ExamRegistration.query.filter_by(
            student_id=student.id,
            course_id=data['course_id'],
            exam_type='retake',
            status='registered'
        ).first()

        if existing:
            return jsonify({'error': 'Already registered for this retake exam'}), 409

        # Create exam registration
        exam_registration = ExamRegistration(
            student_id=student.id,
            course_id=data['course_id'],
            exam_type='retake',
            fee=75.00,  # Standard retake exam fee
            payment_status='pending'
        )

        db.session.add(exam_registration)
        db.session.commit()

        return jsonify({
            'message': 'Retake exam registration successful',
            'registration_id': exam_registration.id,
            'fee': exam_registration.fee,
            'payment_status': exam_registration.payment_status
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@exams_bp.route('/my-registrations', methods=['GET'])
@login_required
def get_my_exam_registrations():
    """Get current student's exam registrations"""
    try:
        student = Student.query.filter_by(user_id=current_user.id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        registrations = ExamRegistration.query.filter_by(student_id=student.id).all()

        registrations_data = [{
            'id': registration.id,
            'course_code': registration.course.code,
            'course_name': registration.course.name,
            'exam_type': registration.exam_type,
            'fee': registration.fee,
            'status': registration.status,
            'payment_status': registration.payment_status,
            'registration_date': registration.registration_date.isoformat(),
            'exam_date': registration.exam_date.isoformat() if registration.exam_date else None
        } for registration in registrations]

        return jsonify(registrations_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@exams_bp.route('/registration/<int:registration_id>', methods=['GET'])
@login_required
def get_exam_registration(registration_id):
    """Get specific exam registration details"""
    try:
        student = Student.query.filter_by(user_id=current_user.id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        registration = ExamRegistration.query.get(registration_id)

        if not registration or registration.student_id != student.id:
            return jsonify({'error': 'Registration not found or unauthorized'}), 404

        registration_data = {
            'id': registration.id,
            'course_code': registration.course.code,
            'course_name': registration.course.name,
            'exam_type': registration.exam_type,
            'fee': registration.fee,
            'status': registration.status,
            'payment_status': registration.payment_status,
            'registration_date': registration.registration_date.isoformat(),
            'exam_date': registration.exam_date.isoformat() if registration.exam_date else None
        }

        return jsonify(registration_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@exams_bp.route('/registration/<int:registration_id>/cancel', methods=['POST'])
@login_required
def cancel_exam_registration(registration_id):
    """Cancel exam registration"""
    try:
        student = Student.query.filter_by(user_id=current_user.id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        registration = ExamRegistration.query.get(registration_id)

        if not registration or registration.student_id != student.id:
            return jsonify({'error': 'Registration not found or unauthorized'}), 404

        if registration.status == 'completed':
            return jsonify({'error': 'Cannot cancel completed exam'}), 400

        if registration.payment_status == 'paid':
            return jsonify({'error': 'Cannot cancel paid exam. Please request a refund.'}), 400

        registration.status = 'cancelled'
        db.session.commit()

        return jsonify({'message': 'Exam registration cancelled successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
