from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os

from models import db, Assignment, AssignmentSubmission, Student, Course

assignments_bp = Blueprint('assignments', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'zip', 'jpg', 'png', 'jpeg'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@assignments_bp.route('/', methods=['GET'])
@login_required
def get_assignments():
    """Get assignments for student's courses"""
    try:
        student = Student.query.filter_by(user_id=current_user.id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        # Get all courses for student's program
        courses = Course.query.filter_by(program_id=student.program_id).all()
        course_ids = [course.id for course in courses]

        # Get assignments for these courses
        assignments = Assignment.query.filter(Assignment.course_id.in_(course_ids)).all()

        assignments_data = [{
            'id': assignment.id,
            'title': assignment.title,
            'description': assignment.description,
            'course_name': assignment.course.name,
            'due_date': assignment.due_date.isoformat(),
            'max_score': assignment.max_score,
            'created_at': assignment.created_at.isoformat()
        } for assignment in assignments]

        return jsonify(assignments_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@assignments_bp.route('/<int:assignment_id>', methods=['GET'])
@login_required
def get_assignment(assignment_id):
    """Get single assignment details"""
    try:
        assignment = Assignment.query.get(assignment_id)

        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404

        assignment_data = {
            'id': assignment.id,
            'title': assignment.title,
            'description': assignment.description,
            'course_name': assignment.course.name,
            'due_date': assignment.due_date.isoformat(),
            'max_score': assignment.max_score,
            'created_at': assignment.created_at.isoformat()
        }

        return jsonify(assignment_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@assignments_bp.route('/<int:assignment_id>/submit', methods=['POST'])
@login_required
def submit_assignment(assignment_id):
    """Submit assignment"""
    try:
        student = Student.query.filter_by(user_id=current_user.id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        assignment = Assignment.query.get(assignment_id)
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404

        # Check if file is provided
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400

        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(current_app.root_path, '..', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)

        # Save file
        filename = secure_filename(f"{student.student_number}_{assignment_id}_{datetime.utcnow().timestamp()}_{file.filename}")
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        # Check for existing submission
        existing_submission = AssignmentSubmission.query.filter_by(
            assignment_id=assignment_id,
            student_id=student.id
        ).first()

        if existing_submission:
            # Update existing submission
            existing_submission.file_path = filepath
            existing_submission.submission_date = datetime.utcnow()
            existing_submission.status = 'submitted'
        else:
            # Create new submission
            submission = AssignmentSubmission(
                assignment_id=assignment_id,
                student_id=student.id,
                file_path=filepath,
                status='submitted'
            )
            db.session.add(submission)

        db.session.commit()

        return jsonify({'message': 'Assignment submitted successfully'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@assignments_bp.route('/<int:assignment_id>/submissions', methods=['GET'])
@login_required
def get_submissions(assignment_id):
    """Get submissions for an assignment (admin/lecturer)"""
    try:
        if current_user.role not in ['admin', 'lecturer']:
            return jsonify({'error': 'Unauthorized'}), 403

        submissions = AssignmentSubmission.query.filter_by(assignment_id=assignment_id).all()

        submissions_data = [{
            'id': submission.id,
            'student_number': submission.student.student_number,
            'student_name': f"{submission.student.user.first_name} {submission.student.user.last_name}",
            'submission_date': submission.submission_date.isoformat(),
            'score': submission.score,
            'feedback': submission.feedback,
            'status': submission.status
        } for submission in submissions]

        return jsonify(submissions_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@assignments_bp.route('/submission/<int:submission_id>/grade', methods=['POST'])
@login_required
def grade_submission(submission_id):
    """Grade a submission (admin/lecturer)"""
    try:
        if current_user.role not in ['admin', 'lecturer']:
            return jsonify({'error': 'Unauthorized'}), 403

        submission = AssignmentSubmission.query.get(submission_id)
        if not submission:
            return jsonify({'error': 'Submission not found'}), 404

        data = request.get_json()

        if 'score' in data:
            submission.score = data['score']
        if 'feedback' in data:
            submission.feedback = data['feedback']

        submission.status = 'graded'
        db.session.commit()

        return jsonify({'message': 'Submission graded successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@assignments_bp.route('/my-submissions', methods=['GET'])
@login_required
def get_my_submissions():
    """Get current student's submissions"""
    try:
        student = Student.query.filter_by(user_id=current_user.id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        submissions = AssignmentSubmission.query.filter_by(student_id=student.id).all()

        submissions_data = [{
            'id': submission.id,
            'assignment_title': submission.assignment.title,
            'submission_date': submission.submission_date.isoformat(),
            'score': submission.score,
            'feedback': submission.feedback,
            'status': submission.status
        } for submission in submissions]

        return jsonify(submissions_data), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
