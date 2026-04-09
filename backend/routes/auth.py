# backend/routes/auth.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import re
import traceback as tb
import json

from models import db, User, Student, Program, Campus, Registration

auth_bp = Blueprint('auth', __name__)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(char.islower() for char in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one digit"
    return True, "Password is valid"

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new applicant (student application)"""
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        print(f"[AUTH] Registration data received: {data}")

        # Required fields
        required_fields = [
            'email', 'password', 'first_name', 'last_name', 'phone', 
            'program_id', 'campus_id'
        ]
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        # Validate email
        if not validate_email(data['email']):
            return jsonify({'error': 'Invalid email format'}), 400

        # Validate password
        is_valid, message = validate_password(data['password'])
        if not is_valid:
            return jsonify({'error': message}), 400

        # Check if email already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 409

        # Validate program
        try:
            program_id = int(data['program_id'])
            program = Program.query.get(program_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid program ID'}), 400

        if not program:
            return jsonify({'error': 'Program not found'}), 404

        # Validate campus
        try:
            campus_id = int(data['campus_id'])
            campus = Campus.query.get(campus_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid campus ID'}), 400

        if not campus:
            return jsonify({'error': 'Campus not found'}), 404

        # Check if program is offered at selected campus
        if program.campus_id != campus_id:
            return jsonify({'error': 'Program not offered at selected campus'}), 400

        # Check BGCSE points
        try:
            bgcse_points = int(data.get('bgcse_points', 0))
        except ValueError:
            bgcse_points = 0

        is_ovc = data.get('is_ovc', 'false').lower() in ['true', '1', 'yes']
        is_government_sponsored = data.get('is_government_sponsored', 'false').lower() in ['true', '1', 'yes']
        wants_accommodation = data.get('wants_accommodation', 'false').lower() in ['true', '1', 'yes']

        # Check BGCSE requirements
        min_points = program.min_bgcse_points if hasattr(program, 'min_bgcse_points') else 32
        if bgcse_points < min_points and not is_ovc:
            return jsonify({'error': f'Minimum {min_points} points required or OVC status'}), 400

        # Create user with role 'student' (admission_status will control access)
        user = User(
            username=data.get('username', data['email']),
            email=data['email'],
            password_hash=generate_password_hash(data['password']),
            role='student',
            is_active=True,
            is_verified=False
        )

        db.session.add(user)
        db.session.flush()

        # Generate student number (temporary until admission accepted, but we generate now)
        year = datetime.now().year
        student_count = Student.query.count() + 1
        student_number = f"GIPS/{year}/{student_count:05d}"

        # Parse date of birth
        date_of_birth = None
        if data.get('date_of_birth'):
            try:
                date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            except:
                pass

        # Create student record with admission_status = 'pending'
        student = Student(
            user_id=user.id,
            student_number=student_number,
            first_name=data['first_name'],
            last_name=data['last_name'],
            initials=data.get('initials'),
            email=data['email'],
            phone=data.get('phone'),
            alternative_phone=data.get('alternative_phone'),
            physical_address=data.get('physical_address'),
            postal_address=data.get('postal_address'),
            date_of_birth=date_of_birth,
            place_of_birth=data.get('place_of_birth'),
            nationality=data.get('nationality', 'Botswana'),
            id_number=data.get('id_number'),
            passport_number=data.get('passport_number'),
            passport_expiry=data.get('passport_expiry'),
            tr_number=data.get('tr_number'),
            is_government_sponsored=is_government_sponsored,
            dtef_sponsor_number=data.get('dtef_sponsor_number'),
            sponsorship_letter_path=data.get('sponsorship_letter_path'),
            campus_id=campus_id,
            wants_accommodation=wants_accommodation,
            bgcse_points=bgcse_points,
            bgcse_year=data.get('bgcse_year'),
            bgcse_school=data.get('bgcse_school'),
            is_ovc=is_ovc,
            social_worker_name=data.get('social_worker_name'),
            social_worker_contact=data.get('social_worker_contact'),
            program_id=program.id,
            enrollment_date=datetime.now().date(),
            admission_status='pending'  # All applications start as pending
        )

        db.session.add(student)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Application submitted successfully. You will be notified once reviewed.',
            'student_number': student.student_number,
            'email': user.email,
            'user_id': user.id,
            'campus': campus.campus_name,
            'program': program.program_name,
            'is_government_sponsored': is_government_sponsored,
            'wants_accommodation': wants_accommodation,
            'admission_status': 'pending'
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"[AUTH] Registration error: {e}")
        tb.print_exc()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user - JWT-based authentication, with redirect based on status"""
    try:
        # Safely obtain request data as a dictionary
        data = None
        
        # Try to get JSON data
        if request.is_json:
            data = request.get_json(silent=True)
        
        # If not a dict, try to parse raw body as JSON
        if not isinstance(data, dict):
            try:
                data = json.loads(request.get_data(as_text=True))
            except:
                data = {}
        
        # Last fallback: form data
        if not isinstance(data, dict):
            data = request.form.to_dict()
        
        # If still not a dict, return error
        if not isinstance(data, dict):
            return jsonify({'error': 'Invalid request data. Expected JSON.'}), 400

        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400

        # Find user by email or username
        user = User.query.filter(
            (User.email == email) | (User.username == email)
        ).first()

        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'error': 'Invalid email or password'}), 401

        if not user.is_active:
            return jsonify({'error': 'Account is inactive'}), 403

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Get student info (may be None for users who don't have a student record)
        student = Student.query.filter_by(user_id=user.id).first()

        # Determine redirect URL based on admission and registration status
        redirect_url = None
        if student:
            if student.admission_status == 'pending':
                redirect_url = '/pages/application-status.html'
            elif student.admission_status == 'accepted':
                # Check if there is an active/approved registration for current semester
                current_reg = Registration.query.filter_by(
                    student_id=student.id,
                    registration_status='approved'
                ).order_by(Registration.created_at.desc()).first()
                if not current_reg:
                    redirect_url = '/pages/semester-registration.html'
                else:
                    redirect_url = '/pages/student-dashboard.html'
            else:
                redirect_url = '/pages/student-dashboard.html'
        else:
            # For non-student users (admin, lecturer, etc.)
            if user.role == 'admin':
                redirect_url = '/pages/admin-dashboard.html'
            elif user.role == 'lecturer':
                redirect_url = '/pages/lecturer-dashboard.html'
            elif user.role == 'finance':
                redirect_url = '/pages/finance-dashboard.html'
            elif user.role == 'registrar':
                redirect_url = '/pages/registrar-dashboard.html'
            elif user.role == 'staff':
                redirect_url = '/pages/staff-dashboard.html'
            else:
                redirect_url = '/pages/student-dashboard.html'

        # Create tokens
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                'role': user.role,
                'email': user.email
            }
        )
        refresh_token = create_refresh_token(identity=str(user.id))

        return jsonify({
            'success': True,
            'message': 'Login successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'redirect_url': redirect_url,
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'first_name': student.first_name if student else '',
                'last_name': student.last_name if student else '',
                'role': user.role,
                'student_number': student.student_number if student else None,
                'is_government_sponsored': student.is_government_sponsored if student else False,
                'campus_id': student.campus_id if student else None,
                'wants_accommodation': student.wants_accommodation if student else False,
                'admission_status': student.admission_status if student else None
            }
        }), 200

    except Exception as e:
        # Log full traceback to console (Render logs)
        tb.print_exc()
        # Return full traceback in response for debugging (temporary)
        return jsonify({
            'error': str(e),
            'traceback': tb.format_exc()
        }), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    try:
        current_user_id = get_jwt_identity()
        
        # Convert to int for database query (since identity is string)
        user_id = int(current_user_id) if current_user_id else None
        user = User.query.get(user_id) if user_id else None
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'success': True,
            'access_token': access_token
        }), 200
    except Exception as e:
        print(f"[AUTH] Refresh error: {e}")
        tb.print_exc()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify if token is valid"""
    try:
        current_user_id = get_jwt_identity()
        
        user_id = int(current_user_id) if current_user_id else None
        user = User.query.get(user_id) if user_id else None
        
        if not user:
            return jsonify({'valid': False}), 401
        
        return jsonify({
            'valid': True,
            'user_id': user.id,
            'role': user.role
        }), 200
    except Exception as e:
        print(f"[AUTH] Verify error: {e}")
        return jsonify({'valid': False}), 401


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user - JWT doesn't require server-side logout, client just removes token"""
    return jsonify({'message': 'Logged out successfully'}), 200


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile (works for all roles)"""
    try:
        current_user_id = get_jwt_identity()
        
        user_id = int(current_user_id) if current_user_id else None
        user = User.query.get(user_id) if user_id else None
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        student = Student.query.filter_by(user_id=user.id).first()

        profile = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': student.first_name if student else '',
            'last_name': student.last_name if student else '',
            'phone': student.phone if student else '',
            'role': user.role,
            'is_verified': user.is_verified if hasattr(user, 'is_verified') else False,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'student_number': student.student_number if student else None,
            'program_id': student.program_id if student else None,
            'program_name': student.program.program_name if student and student.program else None,
            'campus_id': student.campus_id if student else None,
            'campus_name': student.campus.campus_name if student and student.campus else None,
            'current_year': student.current_year if student else None,
            'current_gpa': float(student.current_gpa) if student and student.current_gpa else 0,
            'is_government_sponsored': student.is_government_sponsored if student else False,
            'wants_accommodation': student.wants_accommodation if student else False,
            'admission_status': student.admission_status if student else None
        }

        return jsonify(profile), 200

    except Exception as e:
        print(f"[AUTH] Profile error: {e}")
        tb.print_exc()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415

        current_user_id = get_jwt_identity()
        
        user_id = int(current_user_id) if current_user_id else None
        user = User.query.get(user_id) if user_id else None
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        data = request.get_json()
        student = Student.query.filter_by(user_id=user.id).first()

        if not student:
            return jsonify({'error': 'Student profile not found'}), 404

        # Update fields
        if 'first_name' in data:
            student.first_name = data['first_name']
        if 'last_name' in data:
            student.last_name = data['last_name']
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
        if 'wants_accommodation' in data:
            student.wants_accommodation = data['wants_accommodation']

        user.updated_at = datetime.utcnow()
        student.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Profile updated successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"[AUTH] Update profile error: {e}")
        tb.print_exc()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415

        current_user_id = get_jwt_identity()
        
        user_id = int(current_user_id) if current_user_id else None
        user = User.query.get(user_id) if user_id else None
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        data = request.get_json()

        if not data.get('old_password') or not data.get('new_password'):
            return jsonify({'error': 'Old and new password required'}), 400

        if not check_password_hash(user.password_hash, data['old_password']):
            return jsonify({'error': 'Old password is incorrect'}), 401

        is_valid, message = validate_password(data['new_password'])
        if not is_valid:
            return jsonify({'error': message}), 400

        user.password_hash = generate_password_hash(data['new_password'])
        user.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"[AUTH] Change password error: {e}")
        tb.print_exc()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
            
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
            
        user = User.query.filter_by(email=email).first()
        
        # For security, always return success even if email doesn't exist
        return jsonify({
            'success': True,
            'message': 'If an account exists with that email, you will receive password reset instructions.'
        }), 200
        
    except Exception as e:
        print(f"[AUTH] Forgot password error: {e}")
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/reset-password/<token>', methods=['POST'])
def reset_password(token):
    """Reset password with token (placeholder)"""
    # This would be implemented with email functionality
    return jsonify({
        'message': 'Password reset endpoint - to be implemented',
        'token': token
    }), 200


@auth_bp.route('/admin/create', methods=['POST'])
def create_admin():
    """Create admin user (protected, should only be accessible in development)"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
            
        data = request.get_json()
        
        # Check if admin already exists
        admin_exists = User.query.filter_by(role='admin').first()
        if admin_exists:
            return jsonify({'error': 'Admin user already exists'}), 409
            
        # Create admin user
        admin_user = User(
            username=data.get('username', 'admin'),
            email=data.get('email', 'admin@gipscollege.edu.bw'),
            password_hash=generate_password_hash(data.get('password', 'Admin@2026!')),
            role='admin',
            is_active=True,
            is_verified=True
        )
        
        db.session.add(admin_user)
        db.session.flush()
        
        # Create student record for admin
        admin_student = Student(
            user_id=admin_user.id,
            student_number=f"ADMIN-{admin_user.username.upper()}",
            first_name=data.get('first_name', 'System'),
            last_name=data.get('last_name', 'Administrator'),
            email=admin_user.email,
            is_active=True
        )
        
        db.session.add(admin_student)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Admin user created successfully',
            'email': admin_user.email,
            'username': admin_user.username
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"[AUTH] Create admin error: {e}")
        tb.print_exc()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/campuses', methods=['GET'])
def get_campuses():
    """Get all campuses for registration"""
    try:
        from models import Campus
        
        campuses = Campus.query.all()
        result = []
        for campus in campuses:
            result.append({
                'id': campus.id,
                'campus_code': campus.campus_code,
                'campus_name': campus.campus_name,
                'campus_location': campus.campus_location,
                'has_accommodation': campus.has_accommodation,
                'is_main_campus': campus.is_main_campus
            })
        return jsonify(result), 200
    except Exception as e:
        print(f"[AUTH] Get campuses error: {e}")
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/campuses/<int:campus_id>/programs', methods=['GET'])
def get_campus_programs(campus_id):
    """Get programs available at a specific campus"""
    try:
        from models import Program
        
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
                'min_bgcse_points': program.min_bgcse_points,
                'description': program.description
            })
        return jsonify(result), 200
    except Exception as e:
        print(f"[AUTH] Get campus programs error: {e}")
        return jsonify({'error': str(e)}), 500