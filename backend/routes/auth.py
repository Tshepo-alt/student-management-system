# backend/routes/auth.py
from flask import Blueprint, request, jsonify, current_app, redirect, session
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import re
import traceback as tb
import json
import logging
import requests

# OAuth2 imports
from authlib.integrations.flask_oauth2 import (
    AuthorizationServer, ResourceProtector, current_token
)
from authlib.oauth2.rfc6749 import grants
from authlib.oauth2.rfc6749.errors import (
    InvalidClientError, UnauthorizedClientError,
    InvalidGrantError, UnsupportedGrantTypeError
)

from models import db, User, Student, Program, Campus, Registration
from backend.utils.email import EmailService

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

# ============================================
# OAuth2 Server Setup (for Moodle SSO)
# ============================================

# --- Helper Classes for OAuth2 ---

class OAuth2User:
    """Wrapper for user data needed by OAuth2"""
    def __init__(self, user_id, username, email, firstname, lastname):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.firstname = firstname
        self.lastname = lastname

class PasswordGrant(grants.ResourceOwnerPasswordCredentialsGrant):
    """Resource owner password credentials grant (not used by Moodle, but required by Authlib)"""
    def authenticate_user(self, username, password):
        user = User.query.filter((User.email == username) | (User.username == username)).first()
        if user and check_password_hash(user.password_hash, password):
            student = Student.query.filter_by(user_id=user.id).first()
            return OAuth2User(
                user_id=user.id,
                username=user.username,
                email=user.email,
                firstname=student.first_name if student else user.username,
                lastname=student.last_name if student else ''
            )
        return None

    def authenticate_token(self, token):
        return None

class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    """Authorization code grant (used by Moodle)"""
    def authenticate_user(self, authorization_code):
        # This method is called after the user consents.
        # For auto-approval, we can just return the user from the code's saved data.
        # We'll store the user_id in the code's extra data.
        code_data = self.get_authorization_code(authorization_code)
        if not code_data:
            return None
        user_id = code_data.get('user_id')
        if not user_id:
            return None
        user = User.query.get(user_id)
        if not user:
            return None
        student = Student.query.filter_by(user_id=user.id).first()
        return OAuth2User(
            user_id=user.id,
            username=user.username,
            email=user.email,
            firstname=student.first_name if student else user.username,
            lastname=student.last_name if student else ''
        )

    def get_authorization_code(self, code):
        # In a real implementation, you would store codes in a database table.
        # For simplicity, we use a cache dict or store in session.
        # Here we use a simple in-memory store (for development only).
        # For production, create an OAuth2Code model.
        codes = getattr(current_app, '_oauth2_codes', {})
        return codes.get(code)

    def save_authorization_code(self, code, request):
        # Store the code with user info
        codes = getattr(current_app, '_oauth2_codes', {})
        codes[code] = {
            'user_id': request.user.user_id,
            'client_id': request.client.client_id,
            'redirect_uri': request.redirect_uri,
            'scope': request.scope,
            'expires_at': datetime.utcnow() + timedelta(minutes=10)
        }
        current_app._oauth2_codes = codes

class BearerTokenGrant(grants.BearerTokenGrant):
    """Bearer token grant for exchanging code for token"""
    def authenticate_client(self):
        # Basic client authentication
        auth = request.authorization
        if not auth:
            # Try to get from POST body
            client_id = request.form.get('client_id')
            client_secret = request.form.get('client_secret')
            if client_id and client_secret:
                return client_id == current_app.config.get('OAUTH2_CLIENT_ID') and \
                       client_secret == current_app.config.get('OAUTH2_CLIENT_SECRET')
            return False
        return auth.username == current_app.config.get('OAUTH2_CLIENT_ID') and \
               auth.password == current_app.config.get('OAUTH2_CLIENT_SECRET')

    def authenticate_token(self, token):
        # Not needed for this flow
        return None

# Initialize OAuth2 server (to be attached to app in create_app)
authorization = AuthorizationServer()

def load_user_from_token(token):
    """Load user from access token for the userinfo endpoint"""
    # For simplicity, we decode the token (assuming it's a JWT signed with same secret)
    # In production, you should store access tokens in a database and validate.
    from authlib.jose import JsonWebToken
    jwt = JsonWebToken(['HS256'])
    try:
        claims = jwt.decode(token, current_app.config.get('JWT_SECRET_KEY'))
        user_id = claims.get('user_id')
        if not user_id:
            return None
        user = User.query.get(user_id)
        if not user:
            return None
        student = Student.query.filter_by(user_id=user.id).first()
        return OAuth2User(
            user_id=user.id,
            username=user.username,
            email=user.email,
            firstname=student.first_name if student else user.username,
            lastname=student.last_name if student else ''
        )
    except Exception:
        return None

resource_protector = ResourceProtector()
resource_protector.register_token_validator(lambda token: load_user_from_token(token) is not None)

# OAuth2 routes (to be added to blueprint)

@auth_bp.route('/oauth2/authorize', methods=['GET'])
def oauth2_authorize():
    """
    OAuth2 authorization endpoint.
    Moodle redirects the user here. The user should be logged into your SMS.
    """
    # Check if user is logged into SMS (using JWT token in Authorization header or session)
    # For simplicity, we'll check the session or a query parameter.
    # In your frontend, you can include the JWT token as a query param.
    token = request.args.get('jwt')
    if token:
        # Validate the JWT token
        from flask_jwt_extended import decode_token
        try:
            decoded = decode_token(token)
            user_id = decoded.get('sub')
            user = User.query.get(int(user_id))
            if not user:
                return jsonify({'error': 'Invalid token'}), 401
            # Set user in session for the rest of the flow
            session['user_id'] = user.id
        except Exception as e:
            return jsonify({'error': str(e)}), 401
    else:
        # If no token, check session
        if 'user_id' not in session:
            # Not logged in: redirect to your SMS login page with return URL
            frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:5000')
            redirect_uri = request.url
            login_url = f"{frontend_url}/login?next={redirect_uri}"
            return redirect(login_url)
        user_id = session['user_id']
        user = User.query.get(user_id)
        if not user:
            session.clear()
            return jsonify({'error': 'User not found'}), 401

    # Auto-approve (skip consent screen) and generate code
    # In production, you might want a consent page.
    client_id = request.args.get('client_id')
    redirect_uri = request.args.get('redirect_uri')
    response_type = request.args.get('response_type')
    state = request.args.get('state')

    # Create a fake client object for validation
    class FakeClient:
        def __init__(self, client_id):
            self.client_id = client_id
            self.redirect_uris = [redirect_uri] if redirect_uri else []
            self.default_redirect_uri = redirect_uri
            self.grant_types = ['authorization_code']
            self.response_types = ['code']

    client = FakeClient(client_id)
    # Store the user info in a temporary code
    code = authorization.create_authorization_code(client, {
        'user_id': user.id
    }, request)

    # Redirect back to Moodle with the code
    return redirect(f"{redirect_uri}?code={code}&state={state}")

@auth_bp.route('/oauth2/token', methods=['POST'])
def oauth2_token():
    """OAuth2 token endpoint (exchanges code for access token)"""
    return authorization.create_token_response()

@auth_bp.route('/oauth2/userinfo', methods=['GET'])
def oauth2_userinfo():
    """OAuth2 userinfo endpoint (returns user details for Moodle)"""
    # Validate the access token
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Missing token'}), 401
    user = load_user_from_token(token)
    if not user:
        return jsonify({'error': 'Invalid token'}), 401
    return jsonify({
        'sub': str(user.user_id),
        'username': user.username,
        'email': user.email,
        'firstname': user.firstname,
        'lastname': user.lastname
    })

# ============================================
# Existing validation functions
# ============================================

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

# ============================================
# Existing registration endpoint
# ============================================

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new applicant (student application) - WITH EMAIL CONFIRMATION"""
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

        # ============ SEND REGISTRATION CONFIRMATION EMAIL ============
        email_sent = False
        try:
            student_name = f"{data['first_name']} {data['last_name']}"
            email_sent = EmailService.send_registration_confirmation(
                user_email=data['email'],
                first_name=data['first_name'],
                student_number=student_number,
                program_name=program.program_name,
                campus_name=campus.campus_name
            )
            if email_sent:
                logger.info(f"[AUTH] Registration confirmation email sent to {data['email']}")
            else:
                logger.warning(f"[AUTH] Failed to send registration confirmation email to {data['email']}")
        except Exception as e:
            logger.error(f"[AUTH] Exception while sending registration email: {e}")
            print(f"[AUTH] Failed to send registration email: {e}")
        # ============================================================

        return jsonify({
            'success': True,
            'message': 'Application submitted successfully. You will be notified once reviewed.',
            'email_sent': email_sent,
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
        logger.error(f"[AUTH] Registration error: {e}")
        print(f"[AUTH] Registration error: {e}")
        tb.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# Existing login endpoint
# ============================================

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
            logger.warning(f"[AUTH] Failed login attempt for: {email}")
            return jsonify({'error': 'Invalid email or password'}), 401

        if not user.is_active:
            logger.warning(f"[AUTH] Login attempt for inactive account: {email}")
            return jsonify({'error': 'Account is inactive'}), 403

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        logger.info(f"[AUTH] Successful login for user: {email}")

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

        # Also store user ID in session for OAuth2 flow
        session['user_id'] = user.id

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
        logger.error(f"[AUTH] Login error: {e}")
        tb.print_exc()
        return jsonify({
            'error': str(e),
            'traceback': tb.format_exc()
        }), 500

# ============================================
# Existing token refresh, verify, logout, profile, change-password, forgot-password, reset-password, verify-email, admin/create
# (keep all your existing endpoints unchanged)
# ============================================

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
        logger.info(f"[AUTH] Token refreshed for user: {user.email}")
        
        return jsonify({
            'success': True,
            'access_token': access_token
        }), 200
    except Exception as e:
        logger.error(f"[AUTH] Refresh error: {e}")
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
        logger.error(f"[AUTH] Verify error: {e}")
        print(f"[AUTH] Verify error: {e}")
        return jsonify({'valid': False}), 401


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user - JWT doesn't require server-side logout, client just removes token"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        user = User.query.get(user_id) if user_id else None
        
        if user:
            logger.info(f"[AUTH] User logged out: {user.email}")
            # Clear session for OAuth2
            session.pop('user_id', None)
        
        return jsonify({'message': 'Logged out successfully'}), 200
    except Exception as e:
        logger.error(f"[AUTH] Logout error: {e}")
        return jsonify({'error': str(e)}), 500


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
        logger.error(f"[AUTH] Profile error: {e}")
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
        logger.info(f"[AUTH] Profile updated for user: {user.email}")

        return jsonify({
            'success': True,
            'message': 'Profile updated successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"[AUTH] Update profile error: {e}")
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
            logger.warning(f"[AUTH] Failed password change attempt for user: {user.email}")
            return jsonify({'error': 'Old password is incorrect'}), 401

        is_valid, message = validate_password(data['new_password'])
        if not is_valid:
            return jsonify({'error': message}), 400

        user.password_hash = generate_password_hash(data['new_password'])
        user.updated_at = datetime.utcnow()
        db.session.commit()
        logger.info(f"[AUTH] Password changed for user: {user.email}")

        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"[AUTH] Change password error: {e}")
        print(f"[AUTH] Change password error: {e}")
        tb.print_exc()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset - NOW WITH EMAIL"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
            
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
            
        user = User.query.filter_by(email=email).first()
        
        # Send reset email if user exists
        if user:
            try:
                # Generate reset token
                reset_token = EmailService.generate_verification_token()
                
                # Save token with expiry (1 hour)
                user.reset_token = reset_token
                user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
                db.session.commit()
                
                # Get student name
                student = Student.query.filter_by(user_id=user.id).first()
                student_name = f"{student.first_name} {student.last_name}" if student else user.username
                
                # Send reset email
                email_sent = EmailService.send_password_reset(
                    user_email=email,
                    first_name=student_name.split()[0],  # First name only
                    reset_token=reset_token,
                    user_id=user.id
                )
                
                if email_sent:
                    logger.info(f"[AUTH] Password reset email sent to {email}")
                else:
                    logger.warning(f"[AUTH] Failed to send password reset email to {email}")
                    
            except Exception as e:
                logger.error(f"[AUTH] Error sending password reset email: {e}")
                print(f"[AUTH] Error sending password reset email: {e}")
        
        # For security, always return success even if email doesn't exist
        return jsonify({
            'success': True,
            'message': 'If an account exists with that email, you will receive password reset instructions.'
        }), 200
        
    except Exception as e:
        logger.error(f"[AUTH] Forgot password error: {e}")
        print(f"[AUTH] Forgot password error: {e}")
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/reset-password/<token>', methods=['POST'])
def reset_password(token):
    """Reset password with token"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        data = request.get_json()
        new_password = data.get('new_password')
        user_id = data.get('user_id')
        
        if not new_password or not user_id:
            return jsonify({'error': 'New password and user ID required'}), 400
        
        # Validate password
        is_valid, message = validate_password(new_password)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Find user and verify token
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check token
        if user.reset_token != token:
            logger.warning(f"[AUTH] Invalid reset token for user: {user.email}")
            return jsonify({'error': 'Invalid reset token'}), 401
        
        # Check token expiry
        if not user.reset_token_expiry or datetime.utcnow() > user.reset_token_expiry:
            logger.warning(f"[AUTH] Expired reset token for user: {user.email}")
            return jsonify({'error': 'Reset token has expired'}), 401
        
        # Reset password
        user.password_hash = generate_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"[AUTH] Password reset successful for user: {user.email}")
        
        return jsonify({
            'success': True,
            'message': 'Password reset successfully. You can now log in with your new password.'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"[AUTH] Reset password error: {e}")
        print(f"[AUTH] Reset password error: {e}")
        tb.print_exc()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/verify-email/<token>', methods=['POST'])
def verify_email(token):
    """Verify email address with token"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        # Find user
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check token
        if user.verification_token != token:
            logger.warning(f"[AUTH] Invalid verification token for user: {user.email}")
            return jsonify({'error': 'Invalid verification token'}), 401
        
        # Check token expiry
        if not user.verification_token_expiry or datetime.utcnow() > user.verification_token_expiry:
            logger.warning(f"[AUTH] Expired verification token for user: {user.email}")
            return jsonify({'error': 'Verification token has expired'}), 401
        
        # Mark email as verified
        user.is_verified = True
        user.verification_token = None
        user.verification_token_expiry = None
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"[AUTH] Email verified for user: {user.email}")
        
        return jsonify({
            'success': True,
            'message': 'Email verified successfully. You can now use all features.'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"[AUTH] Email verification error: {e}")
        print(f"[AUTH] Email verification error: {e}")
        tb.print_exc()
        return jsonify({'error': str(e)}), 500


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
        
        logger.info(f"[AUTH] Admin user created: {admin_user.email}")
        
        return jsonify({
            'success': True,
            'message': 'Admin user created successfully',
            'email': admin_user.email,
            'username': admin_user.username
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"[AUTH] Create admin error: {e}")
        print(f"[AUTH] Create admin error: {e}")
        tb.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# Existing campus endpoints (unchanged)
# ============================================

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
        logger.error(f"[AUTH] Get campuses error: {e}")
        print(f"[AUTH] Get campuses error: {e}")
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/campuses/<int:campus_id>', methods=['GET'])
def get_campus_by_id(campus_id):
    """Get a specific campus by ID (used for checking accommodation availability)"""
    try:
        from models import Campus
        
        campus = Campus.query.get(campus_id)
        if not campus:
            return jsonify({'error': 'Campus not found'}), 404
        return jsonify({
            'id': campus.id,
            'campus_code': campus.campus_code,
            'campus_name': campus.campus_name,
            'campus_location': campus.campus_location,
            'has_accommodation': campus.has_accommodation,
            'is_main_campus': campus.is_main_campus
        }), 200
    except Exception as e:
        logger.error(f"[AUTH] Get campus by ID error: {e}")
        print(f"[AUTH] Get campus by ID error: {e}")
        tb.print_exc()
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
        logger.error(f"[AUTH] Get campus programs error: {e}")
        print(f"[AUTH] Get campus programs error: {e}")
        return jsonify({'error': str(e)}), 500