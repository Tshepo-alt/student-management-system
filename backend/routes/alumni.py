# backend/routes/alumni.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import traceback

from models import db, User, Student, Alumni, JobListing, JobApplication, Notification

alumni_bp = Blueprint('alumni', __name__)

# Helper to get student name
def get_student_name(user_id):
    student = Student.query.filter_by(user_id=user_id).first()
    if student:
        return f"{student.first_name} {student.last_name}"
    user = User.query.get(user_id)
    return user.username if user else 'Alumni'

# ============================================
# STATS ENDPOINT
# ============================================
@alumni_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_alumni_stats():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        # Get alumni record for current user (if exists)
        alumni = Alumni.query.filter_by(user_id=user_id).first()
        
        # Count total alumni
        total_alumni = Alumni.query.count()
        employed = Alumni.query.filter_by(employment_status='employed').count()
        self_employed = Alumni.query.filter_by(employment_status='self_employed').count()
        studying = Alumni.query.filter_by(employment_status='studying').count()
        unemployed = Alumni.query.filter_by(employment_status='unemployed').count()
        
        # Jobs posted by this alumni
        jobs_posted = 0
        if alumni:
            jobs_posted = JobListing.query.filter_by(alumni_id=alumni.id).count()
        
        stats = {
            'total_alumni': total_alumni,
            'employed': employed,
            'self_employed': self_employed,
            'studying': studying,
            'unemployed': unemployed,
            'jobs_posted': jobs_posted,
            'employment_rate': round((employed / total_alumni * 100) if total_alumni > 0 else 0, 1)
        }
        return jsonify(stats), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# PROFILE ENDPOINT
# ============================================
@alumni_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_alumni_profile():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        alumni = Alumni.query.filter_by(user_id=user_id).first()
        student = Student.query.filter_by(user_id=user_id).first()
        user = User.query.get(user_id)
        
        if not alumni:
            return jsonify({'error': 'Alumni record not found'}), 404
        
        profile = {
            'id': alumni.id,
            'student_number': alumni.student_number,
            'name': get_student_name(user_id),
            'email': user.email if user else '',
            'graduation_year': alumni.graduation_year,
            'graduation_date': alumni.graduation_date.isoformat() if alumni.graduation_date else None,
            'program_name': student.program.program_name if student and student.program else None,
            'job_title': alumni.job_title,
            'company': alumni.company,
            'employment_status': alumni.employment_status,
            'linkedin_url': alumni.linkedin_url,
            'bio': alumni.bio,
            'skills': alumni.skills if isinstance(alumni.skills, list) else (json.loads(alumni.skills) if alumni.skills else []),
            'is_verified': alumni.is_verified
        }
        return jsonify(profile), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@alumni_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_alumni_profile():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        alumni = Alumni.query.filter_by(user_id=user_id).first()
        if not alumni:
            return jsonify({'error': 'Alumni record not found'}), 404
        
        data = request.get_json()
        
        if 'job_title' in data:
            alumni.job_title = data['job_title']
        if 'company' in data:
            alumni.company = data['company']
        if 'employment_status' in data:
            alumni.employment_status = data['employment_status']
        if 'linkedin_url' in data:
            alumni.linkedin_url = data['linkedin_url']
        if 'bio' in data:
            alumni.bio = data['bio']
        if 'skills' in data:
            alumni.skills = data['skills']
        
        alumni.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'Profile updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# JOBS / RECOMMENDED ENDPOINT
# ============================================
@alumni_bp.route('/jobs/recommended', methods=['GET'])
@jwt_required()
def get_recommended_jobs():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        limit = request.args.get('limit', 3, type=int)
        
        # Get alumni record
        alumni = Alumni.query.filter_by(user_id=user_id).first()
        
        # Get recent job listings (fallback: all active jobs)
        # For personalized recommendations, match skills with job requirements (placeholder)
        jobs = JobListing.query.filter_by(is_active=True).order_by(JobListing.created_at.desc()).limit(limit).all()
        
        result = []
        for job in jobs:
            result.append({
                'id': job.id,
                'title': job.title,
                'company': job.company,
                'location': job.location,
                'type': job.type,
                'salary_range': job.salary_range,
                'deadline': job.deadline.isoformat() if job.deadline else None,
                'posted_by': job.alumni.user.username if job.alumni and job.alumni.user else 'Alumni',
                'posted_at': job.created_at.isoformat() if job.created_at else None
            })
        return jsonify(result), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# ACTIVITY ENDPOINT
# ============================================
@alumni_bp.route('/activity', methods=['GET'])
@jwt_required()
def get_alumni_activity():
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        limit = request.args.get('limit', 5, type=int)
        
        # Get notifications for this user
        notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).limit(limit).all()
        
        # Also get job applications and other activity (placeholder)
        activities = []
        for n in notifications:
            activities.append({
                'id': n.id,
                'type': 'notification',
                'title': n.title,
                'message': n.message,
                'created_at': n.created_at.isoformat(),
                'icon': 'fa-bell'
            })
        
        # If no notifications, add a welcome message
        if not activities:
            activities.append({
                'id': 1,
                'type': 'welcome',
                'title': 'Welcome to Alumni Network',
                'message': 'Connect with fellow alumni, share job opportunities, and grow your professional network.',
                'created_at': datetime.utcnow().isoformat(),
                'icon': 'fa-hand-peace'
            })
        
        # Return only up to limit
        return jsonify(activities[:limit]), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# DIRECTORY ENDPOINT (keep existing)
# ============================================
@alumni_bp.route('/directory', methods=['GET'])
@jwt_required()
def get_alumni_directory():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        paginated = Alumni.query.order_by(Alumni.graduation_year.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
        alumni_list = []
        for a in paginated.items:
            user = User.query.get(a.user_id)
            student = Student.query.get(a.student_id) if a.student_id else None
            alumni_list.append({
                'id': a.id,
                'name': f"{student.first_name} {student.last_name}" if student else (user.username if user else 'Unknown'),
                'graduation_year': a.graduation_year,
                'job_title': a.job_title,
                'company': a.company,
                'employment_status': a.employment_status,
                'linkedin_url': a.linkedin_url
            })
        
        return jsonify({
            'alumni': alumni_list,
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page
        }), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# EMPLOYMENT STATS (already have, but add JWT)
# ============================================
@alumni_bp.route('/employment-stats', methods=['GET'])
@jwt_required()
def get_employment_stats():
    try:
        total = Alumni.query.count()
        employed = Alumni.query.filter_by(employment_status='employed').count()
        self_employed = Alumni.query.filter_by(employment_status='self_employed').count()
        studying = Alumni.query.filter_by(employment_status='studying').count()
        unemployed = Alumni.query.filter_by(employment_status='unemployed').count()
        
        stats = {
            'total_alumni': total,
            'employed': employed,
            'self_employed': self_employed,
            'studying': studying,
            'unemployed': unemployed,
            'employment_rate': round((employed / total * 100) if total > 0 else 0, 1)
        }
        return jsonify(stats), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# SEARCH (add JWT)
# ============================================
@alumni_bp.route('/search', methods=['GET'])
@jwt_required()
def search_alumni():
    try:
        query = request.args.get('q', '', type=str)
        if len(query) < 2:
            return jsonify({'error': 'Search query too short'}), 400
        
        # Search by name in Student table or company in Alumni table
        results = []
        # Simple implementation: search by company or job title
        alumni_list = Alumni.query.filter(
            (Alumni.company.ilike(f'%{query}%')) |
            (Alumni.job_title.ilike(f'%{query}%'))
        ).limit(20).all()
        
        for a in alumni_list:
            student = Student.query.get(a.student_id) if a.student_id else None
            results.append({
                'id': a.id,
                'name': f"{student.first_name} {student.last_name}" if student else 'Unknown',
                'job_title': a.job_title,
                'company': a.company,
                'employment_status': a.employment_status
            })
        return jsonify(results), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500