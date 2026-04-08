# backend/routes/online_classes.py
from flask import Blueprint, request, jsonify, render_template_string
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import logging

from models import db, Course, User
from utils.meeting_helper import create_google_meet_link

logger = logging.getLogger(__name__)

online_classes_bp = Blueprint('online_classes', __name__, url_prefix='/api/classes')

# ============================================
# HTML TEMPLATES
# ============================================

# Template for students (embedded meeting)
EMBEDDED_MEETING_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ course_name }} - Live Class | GIPS College</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', 'Poppins', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #f5f7fa 0%, #eef2f7 100%); 
            min-height: 100vh; 
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; padding: 20px; border-radius: 20px; margin-bottom: 20px; 
        }
        .header h1 { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; font-size: 1.5rem; }
        .meeting-container { 
            background: white; border-radius: 20px; padding: 20px; 
            box-shadow: 0 4px 12px rgba(0,0,0,0.05); min-height: 600px; 
        }
        .meeting-frame { width: 100%; height: 600px; border: none; border-radius: 12px; }
        .info-panel { 
            background: #f8fafc; padding: 15px; border-radius: 12px; margin-top: 15px; 
            display: flex; gap: 15px; flex-wrap: wrap; justify-content: space-between; align-items: center; 
        }
        .btn { 
            padding: 10px 20px; border: none; border-radius: 12px; cursor: pointer; font-weight: 600; 
            display: inline-flex; align-items: center; gap: 8px; text-decoration: none; 
        }
        .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .btn-secondary { background: #e2e8f0; color: #4a5568; }
        .btn-secondary:hover { background: #cbd5e0; }
        .waiting-message { text-align: center; padding: 100px; }
        .waiting-message i { font-size: 64px; color: #a0aec0; margin-bottom: 20px; }
        .refresh-btn { margin-top: 20px; }
        @media (max-width: 768px) { .meeting-frame { height: 400px; } .header h1 { font-size: 1.2rem; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fas fa-video"></i> Live Class: {{ course_name }}</h1>
            <p><i class="fas fa-user"></i> Instructor: {{ instructor_name }} | <i class="fas fa-clock"></i> {{ date }}</p>
        </div>
        <div class="meeting-container">
            {% if meeting_url %}
            <iframe class="meeting-frame" src="{{ meeting_url }}" allow="camera; microphone; fullscreen; display-capture" allowfullscreen></iframe>
            {% else %}
            <div class="waiting-message">
                <i class="fas fa-video-slash"></i>
                <h3>No active meeting at this time</h3>
                <p>The meeting link will appear here when the instructor starts the session.</p>
                <button class="btn btn-primary refresh-btn" onclick="location.reload()">
                    <i class="fas fa-sync-alt"></i> Refresh
                </button>
            </div>
            {% endif %}
        </div>
        <div class="info-panel">
            <div><i class="fas fa-info-circle"></i> Meeting may be recorded for review purposes</div>
            <button class="btn btn-secondary" onclick="window.location.href='/pages/student-dashboard.html'">
                <i class="fas fa-arrow-left"></i> Back to Dashboard
            </button>
        </div>
    </div>
</body>
</html>
'''

# Template for lecturers (manage page)
LECTURER_MEETING_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ course_name }} - Manage Live Class | GIPS College</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', 'Poppins', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #f5f7fa 0%, #eef2f7 100%); 
            min-height: 100vh; 
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 30px; }
        .card { background: white; border-radius: 20px; padding: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .card h2 { color: #2d3748; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
        .btn { padding: 12px 24px; border: none; border-radius: 12px; cursor: pointer; font-weight: 600; display: inline-flex; align-items: center; gap: 8px; }
        .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-secondary { background: #e2e8f0; color: #4a5568; }
        .meeting-info { background: #f8fafc; padding: 20px; border-radius: 16px; margin: 20px 0; }
        .meeting-link { word-break: break-all; color: #667eea; margin: 10px 0; }
        .status-active { color: #28a745; font-weight: bold; }
        .status-inactive { color: #dc3545; font-weight: bold; }
        .start-btn {
            background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%);
            color: white;
            padding: 14px 28px;
            font-size: 1.1rem;
        }
        .start-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(40,167,69,0.4);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h2><i class="fas fa-chalkboard-teacher"></i> Manage Live Class: {{ course_name }}</h2>
            
            {% if meeting_active and meeting_link %}
            <div class="meeting-info">
                <p><strong><i class="fas fa-info-circle"></i> Current Meeting Status:</strong> <span class="status-active">● LIVE NOW</span></p>
                <p><strong><i class="fas fa-link"></i> Meeting Link:</strong></p>
                <p class="meeting-link">{{ meeting_link }}</p>
                <div style="display: flex; gap: 15px; margin-top: 15px;">
                    <button class="btn btn-primary" onclick="window.open('{{ meeting_link }}', '_blank')">
                        <i class="fas fa-video"></i> Join Meeting
                    </button>
                    <button class="btn btn-danger" onclick="endMeeting()">
                        <i class="fas fa-stop"></i> End Live Class
                    </button>
                    <button class="btn btn-secondary" onclick="copyLink()">
                        <i class="fas fa-copy"></i> Copy Link
                    </button>
                </div>
            </div>
            {% else %}
            <p>Start a new live class session for your students using Google Meet.</p>
            <div style="text-align: center; margin: 30px 0;">
                <button class="btn start-btn" onclick="startMeeting()">
                    <i class="fab fa-google"></i> Start Google Meet
                </button>
            </div>
            {% endif %}
        </div>
        
        <div class="card">
            <h2><i class="fas fa-users"></i> Student Instructions</h2>
            <ul style="margin-left: 20px; line-height: 1.8;">
                <li><i class="fas fa-link"></i> Share the meeting link with your students</li>
                <li><i class="fas fa-video"></i> Students can join directly from their dashboard</li>
                <li><i class="fas fa-clock"></i> Meeting links remain active until you end the class</li>
                <li><i class="fas fa-chalkboard"></i> You can record sessions for later review</li>
            </ul>
        </div>
        
        <button class="btn btn-secondary" onclick="window.location.href='/pages/lecturer-dashboard.html'">
            <i class="fas fa-arrow-left"></i> Back to Dashboard
        </button>
    </div>
    
    <script>
        const courseId = {{ course_id }};
        
        async function startMeeting() {
            const response = await fetch(`/api/classes/course/${courseId}/start`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ platform: 'google_meet' })
            });
            
            const data = await response.json();
            if (data.success) {
                alert(`Meeting started successfully!`);
                window.location.reload();
            } else {
                alert('Error: ' + data.error);
            }
        }
        
        async function endMeeting() {
            if (!confirm('Are you sure you want to end this live class?')) return;
            
            const response = await fetch(`/api/classes/course/${courseId}/end`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            if (data.success) {
                alert('Meeting ended successfully!');
                window.location.reload();
            } else {
                alert('Error: ' + data.error);
            }
        }
        
        function copyLink() {
            const link = '{{ meeting_link }}';
            navigator.clipboard.writeText(link);
            alert('Meeting link copied to clipboard!');
        }
    </script>
</body>
</html>
'''

# ============================================
# ENDPOINTS
# ============================================

@online_classes_bp.route('/course/<int:course_id>/start', methods=['POST'])
@jwt_required()
def start_online_class(course_id):
    """Lecturer starts an online class meeting (Google Meet only)"""
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    
    if user.role not in ['lecturer', 'admin']:
        return jsonify({'error': 'Only lecturers can start online classes'}), 403
    
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    if user.role == 'lecturer' and course.lecturer_id != user.id:
        return jsonify({'error': 'You are not assigned to this course'}), 403
    
    # Only Google Meet is supported
    meeting_url = create_google_meet_link(course.name, user.email)
    if not meeting_url:
        return jsonify({'error': 'Failed to create Google Meet link. Please check your calendar permissions.'}), 500
    
    course.meeting_link = meeting_url
    course.meeting_platform = 'google_meet'
    db.session.commit()
    
    logger.info(f"Online class started for course {course.code} by {user.email}")
    
    return jsonify({
        'success': True,
        'meeting_link': meeting_url,
        'platform': 'google_meet',
        'message': 'Meeting started successfully'
    }), 200


@online_classes_bp.route('/course/<int:course_id>/meeting', methods=['GET'])
@jwt_required()
def get_meeting_info(course_id):
    """Get meeting information for a course (for both lecturers and students)"""
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    # No need to check enrollment here – frontend will handle visibility
    return jsonify({
        'is_active': course.meeting_link is not None,
        'meeting_link': course.meeting_link,
        'platform': getattr(course, 'meeting_platform', None),
        'meeting_id': getattr(course, 'meeting_id', None),
        'meeting_password': getattr(course, 'meeting_password', None),
        'started_at': course.updated_at.isoformat() if course.updated_at else None
    }), 200


@online_classes_bp.route('/course/<int:course_id>/join', methods=['GET'])
def join_class_embedded(course_id):
    """Embedded meeting page for students (keeps them within the portal)"""
    course = Course.query.get(course_id)
    if not course:
        return "Course not found", 404
    
    instructor = User.query.get(course.lecturer_id) if course.lecturer_id else None
    instructor_name = f"{instructor.first_name} {instructor.last_name}" if instructor else "Staff"
    
    return render_template_string(
        EMBEDDED_MEETING_TEMPLATE,
        course_name=course.name,
        instructor_name=instructor_name,
        meeting_url=course.meeting_link,
        date=datetime.now().strftime("%B %d, %Y at %I:%M %p")
    )


@online_classes_bp.route('/course/<int:course_id>/manage', methods=['GET'])
@jwt_required()
def manage_class_page(course_id):
    """Lecturer management page for online class"""
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    
    if user.role not in ['lecturer', 'admin']:
        return "Unauthorized", 403
    
    course = Course.query.get(course_id)
    if not course:
        return "Course not found", 404
    
    return render_template_string(
        LECTURER_MEETING_TEMPLATE,
        course_name=course.name,
        course_id=course.id,
        meeting_active=course.meeting_link is not None,
        meeting_link=course.meeting_link or ''
    )


@online_classes_bp.route('/course/<int:course_id>/end', methods=['POST'])
@jwt_required()
def end_online_class(course_id):
    """End online class – clear meeting link"""
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    
    if user.role not in ['lecturer', 'admin']:
        return jsonify({'error': 'Only lecturers can end online classes'}), 403
    
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    if user.role == 'lecturer' and course.lecturer_id != user.id:
        return jsonify({'error': 'You are not assigned to this course'}), 403
    
    meeting_link = course.meeting_link
    course.meeting_link = None
    if hasattr(course, 'meeting_id'):
        course.meeting_id = None
    if hasattr(course, 'meeting_password'):
        course.meeting_password = None
    db.session.commit()
    
    logger.info(f"Online class ended for course {course.code} by {user.email}")
    
    return jsonify({
        'success': True,
        'message': 'Meeting ended successfully',
        'meeting_link': meeting_link
    }), 200


@online_classes_bp.route('/course/<int:course_id>/status', methods=['GET'])
def get_meeting_status(course_id):
    """Public endpoint to check if a meeting is active (no auth required)"""
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    return jsonify({
        'is_active': course.meeting_link is not None,
        'course_name': course.name,
        'course_code': getattr(course, 'code', None)
    }), 200


@online_classes_bp.route('/lecturer/courses', methods=['GET'])
@jwt_required()
def get_lecturer_courses():
    """Get all courses for a lecturer with meeting status (used by lecturer dashboard)"""
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    
    if user.role not in ['lecturer', 'admin']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if user.role == 'lecturer':
        courses = Course.query.filter_by(lecturer_id=user.id).all()
    else:
        courses = Course.query.all()
    
    result = []
    for course in courses:
        result.append({
            'id': course.id,
            'code': getattr(course, 'code', f"CRS{course.id:03d}"),
            'name': course.name,
            'students': 0,  # You can populate this from an enrollment table
            'semester': 'Semester 1',  # Placeholder, can be dynamic
            'meeting_active': course.meeting_link is not None,
            'meeting_link': course.meeting_link
        })
    
    return jsonify({
        'courses': result,
        'total': len(result)
    }), 200


@online_classes_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for online classes module"""
    return jsonify({
        'status': 'healthy',
        'module': 'online_classes',
        'version': '1.0.0',
        'features': ['Google Meet', 'Embedded Meeting']
    }), 200