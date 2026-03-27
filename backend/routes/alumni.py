from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from models import db, Alumni, User, Student

alumni_bp = Blueprint('alumni', __name__)

@alumni_bp.route('/profile', methods=['GET'])
@login_required
def get_alumni_profile():
    """Get alumni profile"""
    try:
        alumni = Alumni.query.filter_by(user_id=current_user.id).first()

        if not alumni:
            return jsonify({'error': 'Alumni record not found'}), 404

        profile = {
            'id': alumni.id,
            'student_number': alumni.student_number,
            'name': f"{current_user.first_name} {current_user.last_name}",
            'email': current_user.email,
            'graduation_date': alumni.graduation_date.isoformat() if alumni.graduation_date else None,
            'current_job_title': alumni.current_job_title,
            'company': alumni.company,
            'employment_status': alumni.employment_status,
            'linkedin_url': alumni.linkedin_url,
            'bio': alumni.bio
        }

        return jsonify(profile), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@alumni_bp.route('/profile', methods=['PUT'])
@login_required
def update_alumni_profile():
    """Update alumni profile"""
    try:
        alumni = Alumni.query.filter_by(user_id=current_user.id).first()

        if not alumni:
            return jsonify({'error': 'Alumni record not found'}), 404

        data = request.get_json()

        if 'current_job_title' in data:
            alumni.current_job_title = data['current_job_title']
        if 'company' in data:
            alumni.company = data['company']
        if 'employment_status' in data:
            alumni.employment_status = data['employment_status']
        if 'linkedin_url' in data:
            alumni.linkedin_url = data['linkedin_url']
        if 'bio' in data:
            alumni.bio = data['bio']

        alumni.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'message': 'Alumni profile updated successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@alumni_bp.route('/directory', methods=['GET'])
def get_alumni_directory():
    """Get alumni directory"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        alumni_list = Alumni.query.paginate(page=page, per_page=per_page)

        alumni_data = [{
            'id': alumni.id,
            'name': f"{alumni.user.first_name} {alumni.user.last_name}",
            'company': alumni.company,
            'job_title': alumni.current_job_title,
            'employment_status': alumni.employment_status,
            'linkedin_url': alumni.linkedin_url,
            'graduation_date': alumni.graduation_date.isoformat() if alumni.graduation_date else None
        } for alumni in alumni_list.items]

        return jsonify({
            'alumni': alumni_data,
            'total': alumni_list.total,
            'pages': alumni_list.pages,
            'current_page': page
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@alumni_bp.route('/employment-stats', methods=['GET'])
def get_employment_stats():
    """Get employment statistics"""
    try:
        total_alumni = Alumni.query.count()
        employed = Alumni.query.filter_by(employment_status='employed').count()
        unemployed = Alumni.query.filter_by(employment_status='unemployed').count()
        self_employed = Alumni.query.filter_by(employment_status='self-employed').count()

        stats = {
            'total_alumni': total_alumni,
            'employed': employed,
            'unemployed': unemployed,
            'self_employed': self_employed,
            'employment_rate': (employed / total_alumni * 100) if total_alumni > 0 else 0
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@alumni_bp.route('/search', methods=['GET'])
def search_alumni():
    """Search alumni by name or company"""
    try:
        query = request.args.get('q', '', type=str)

        if len(query) < 2:
            return jsonify({'error': 'Search query too short'}), 400

        alumni_list = Alumni.query.filter(
            (Alumni.user.has(User.first_name.ilike(f'%{query}%'))) |
            (Alumni.user.has(User.last_name.ilike(f'%{query}%'))) |
            (Alumni.company.ilike(f'%{query}%'))
        ).limit(20).all()

        results = [{
            'id': alumni.id,
            'name': f"{alumni.user.first_name} {alumni.user.last_name}",
            'company': alumni.company,
            'job_title': alumni.current_job_title,
            'employment_status': alumni.employment_status
        } for alumni in alumni_list]

        return jsonify(results), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
