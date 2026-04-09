# backend/routes/lecturer.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import traceback

from models import db, User, Course, Assignment, Module, AssignmentSubmission, Student, Enrollment, OnlineMeeting

lecturer_bp = Blueprint('lecturer', __name__)

# ============================================
# HELPER: Ensure the logged-in user is a lecturer
# ============================================
def require_lecturer():
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id) if current_user_id else None
    user = User.query.get(user_id)
    if not user or user.role not in ['lecturer', 'admin', 'administrator']:
        return None, jsonify({'error': 'Unauthorized: Lecturer access required'}), 403
    return user, None, None

# ============================================
# GET /api/lecturer/courses
# Returns all courses assigned to the lecturer
# ============================================
@lecturer_bp.route('/courses', methods=['GET'])
@jwt_required()
def get_lecturer_courses():
    try:
        user, error_response, status = require_lecturer()
        if error_response:
            return error_response, status

        courses = Course.query.filter_by(lecturer_id=user.id, is_active=True).all()
        result = []
        for course in courses:
            # Count enrolled students via student_courses relationship
            enrolled_count = len(course.student_courses) if course.student_courses else 0
            result.append({
                'id': course.id,
                'course_code': course.course_code,
                'course_name': course.course_name,
                'credits': course.credits,
                'semester': course.semester,
                'year_level': course.year_level,
                'enrolled_students': enrolled_count,
                'meeting_link': course.meeting_link,
                'meeting_platform': course.meeting_platform,
                'is_active': course.is_active
            })
        return jsonify(result), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# GET /api/lecturer/assignments
# Returns assignments for courses taught by the lecturer
# ============================================
@lecturer_bp.route('/assignments', methods=['GET'])
@jwt_required()
def get_lecturer_assignments():
    try:
        user, error_response, status = require_lecturer()
        if error_response:
            return error_response, status

        # Get all courses taught by this lecturer
        courses = Course.query.filter_by(lecturer_id=user.id, is_active=True).all()
        if not courses:
            return jsonify([]), 200

        course_ids = [c.id for c in courses]
        # Get modules that belong to these courses (via program_modules or direct relationship)
        # Your models might have Module.course_id? If not, we need to join via ProgramModule -> Program -> Course.
        # Simpler: assignments are linked to modules; modules are linked to programs; programs have courses.
        # For simplicity, we'll assume assignments are linked to modules, and modules have a course_id column.
        # If not, adjust the query accordingly.
        assignments = Assignment.query.join(Module, Assignment.module_id == Module.id)\
            .filter(Module.course_id.in_(course_ids)).all()
        
        result = []
        for ass in assignments:
            submission_count = len(ass.submissions) if ass.submissions else 0
            result.append({
                'id': ass.id,
                'title': ass.title,
                'description': ass.description,
                'module_name': ass.module.module_name if ass.module else 'Unknown',
                'course_name': ass.module.course.course_name if ass.module and ass.module.course else 'Unknown',
                'due_date': ass.due_date.isoformat() if ass.due_date else None,
                'max_points': ass.max_points,
                'submission_count': submission_count,
                'is_active': ass.is_active
            })
        return jsonify(result), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# GET /api/lecturer/courses/<int:course_id>/students
# Returns students enrolled in a specific course
# ============================================
@lecturer_bp.route('/courses/<int:course_id>/students', methods=['GET'])
@jwt_required()
def get_course_students(course_id):
    try:
        user, error_response, status = require_lecturer()
        if error_response:
            return error_response, status

        course = Course.query.get(course_id)
        if not course or course.lecturer_id != user.id:
            return jsonify({'error': 'Course not found or not assigned to you'}), 404

        students = []
        for sc in course.student_courses:
            if sc.student and sc.status == 'registered':
                students.append({
                    'id': sc.student.id,
                    'student_number': sc.student.student_number,
                    'name': f"{sc.student.first_name} {sc.student.last_name}",
                    'email': sc.student.email
                })
        return jsonify(students), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# POST /api/lecturer/assignments
# Create a new assignment for a module
# ============================================
@lecturer_bp.route('/assignments', methods=['POST'])
@jwt_required()
def create_assignment():
    try:
        user, error_response, status = require_lecturer()
        if error_response:
            return error_response, status

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request data'}), 400

        module_id = data.get('module_id')
        title = data.get('title')
        description = data.get('description', '')
        due_date_str = data.get('due_date')
        max_points = data.get('max_points', 100)
        submission_type = data.get('submission_type', 'file')

        if not module_id or not title or not due_date_str:
            return jsonify({'error': 'Missing required fields: module_id, title, due_date'}), 400

        # Verify the module belongs to a course taught by this lecturer
        module = Module.query.get(module_id)
        if not module or not module.course or module.course.lecturer_id != user.id:
            return jsonify({'error': 'Module not found or not under your course'}), 404

        due_date = datetime.fromisoformat(due_date_str)

        assignment = Assignment(
            module_id=module_id,
            title=title,
            description=description,
            due_date=due_date,
            max_points=max_points,
            submission_type=submission_type,
            is_active=True
        )
        db.session.add(assignment)
        db.session.commit()

        return jsonify({
            'message': 'Assignment created successfully',
            'assignment_id': assignment.id
        }), 201
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# PUT /api/lecturer/assignments/<int:assignment_id>
# Update an existing assignment
# ============================================
@lecturer_bp.route('/assignments/<int:assignment_id>', methods=['PUT'])
@jwt_required()
def update_assignment(assignment_id):
    try:
        user, error_response, status = require_lecturer()
        if error_response:
            return error_response, status

        assignment = Assignment.query.get(assignment_id)
        if not assignment or not assignment.module.course or assignment.module.course.lecturer_id != user.id:
            return jsonify({'error': 'Assignment not found or not authorized'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request data'}), 400

        if 'title' in data:
            assignment.title = data['title']
        if 'description' in data:
            assignment.description = data['description']
        if 'due_date' in data:
            assignment.due_date = datetime.fromisoformat(data['due_date'])
        if 'max_points' in data:
            assignment.max_points = data['max_points']
        if 'submission_type' in data:
            assignment.submission_type = data['submission_type']
        if 'is_active' in data:
            assignment.is_active = data['is_active']

        assignment.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'message': 'Assignment updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# GET /api/lecturer/assignments/<int:assignment_id>/submissions
# Returns all submissions for an assignment
# ============================================
@lecturer_bp.route('/assignments/<int:assignment_id>/submissions', methods=['GET'])
@jwt_required()
def get_submissions(assignment_id):
    try:
        user, error_response, status = require_lecturer()
        if error_response:
            return error_response, status

        assignment = Assignment.query.get(assignment_id)
        if not assignment or not assignment.module.course or assignment.module.course.lecturer_id != user.id:
            return jsonify({'error': 'Assignment not found or not authorized'}), 404

        submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment_id).all()
        result = []
        for sub in submissions:
            result.append({
                'id': sub.id,
                'student_name': f"{sub.student.first_name} {sub.student.last_name}" if sub.student else 'Unknown',
                'student_number': sub.student.student_number if sub.student else 'N/A',
                'submitted_at': sub.submitted_at.isoformat() if sub.submitted_at else None,
                'score': sub.score,
                'grade': sub.grade,
                'status': sub.status,
                'feedback': sub.feedback,
                'file_path': sub.file_path
            })
        return jsonify(result), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# POST /api/lecturer/submissions/<int:submission_id>/grade
# Grade a student's submission
# ============================================
@lecturer_bp.route('/submissions/<int:submission_id>/grade', methods=['POST'])
@jwt_required()
def grade_submission(submission_id):
    try:
        user, error_response, status = require_lecturer()
        if error_response:
            return error_response, status

        submission = AssignmentSubmission.query.get(submission_id)
        if not submission or not submission.assignment.module.course or submission.assignment.module.course.lecturer_id != user.id:
            return jsonify({'error': 'Submission not found or not authorized'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request data'}), 400

        score = data.get('score')
        feedback = data.get('feedback', '')

        if score is None:
            return jsonify({'error': 'Score is required'}), 400

        submission.score = score
        submission.feedback = feedback
        submission.status = 'graded'
        submission.graded_at = datetime.utcnow()
        submission.graded_by = user.id

        # Optionally convert score to letter grade
        if submission.assignment.max_points:
            percentage = (score / submission.assignment.max_points) * 100
            if percentage >= 90:
                submission.grade = 'A'
            elif percentage >= 80:
                submission.grade = 'B'
            elif percentage >= 70:
                submission.grade = 'C'
            elif percentage >= 60:
                submission.grade = 'D'
            else:
                submission.grade = 'F'

        db.session.commit()

        return jsonify({'message': 'Submission graded successfully'}), 200
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# POST /api/lecturer/start-class/<int:course_id>
# Alternative endpoint for starting a live class (if online_classes blueprint is not used)
# But we can rely on the existing online_classes blueprint.
# For completeness, we'll include a wrapper that calls the same logic.
# ============================================
@lecturer_bp.route('/start-class/<int:course_id>', methods=['POST'])
@jwt_required()
def start_class(course_id):
    try:
        user, error_response, status = require_lecturer()
        if error_response:
            return error_response, status

        course = Course.query.get(course_id)
        if not course or course.lecturer_id != user.id:
            return jsonify({'error': 'Course not found or not assigned to you'}), 404

        # Delegate to the existing online_classes blueprint's start function
        # To avoid duplication, you can import and call the function from online_classes.py
        # But for now, we'll return a placeholder (the actual start logic should be in online_classes.py)
        # The lecturer dashboard probably uses /api/classes/course/<id>/start, not this endpoint.
        return jsonify({'error': 'Please use /api/classes/course/<id>/start'}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500