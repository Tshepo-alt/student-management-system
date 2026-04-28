# ============================================
# FIX MODULE PATH: Add project root to sys.path
# ============================================
import sys
from pathlib import Path

# Add the project root directory to the Python module search path.
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# ============================================
# STANDARD IMPORTS
# ============================================
import os
from datetime import datetime, timedelta
import json
import base64
import traceback
import logging

from flask import Flask, jsonify, send_from_directory, request, redirect, make_response
from flask_cors import CORS
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from dotenv import load_dotenv
from urllib.parse import urlparse, urlunparse

# Load environment variables
load_dotenv()

# Now import after adding to path
from models import db, User
from config import config
from backend.utils.email import mail

# Import OAuth2 components from auth.py
from backend.routes.auth import (
    authorization, PasswordGrant, AuthorizationCodeGrant, load_user_from_token
)

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_app(config_name=None):
    """Application factory"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    print("\n" + "="*70)
    print(f"🚀 Starting GIPS College Student Management System")
    print(f"📌 Environment: {config_name.upper()} mode")
    print(f"🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    # Initialize Flask with correct static folder
    app = Flask(__name__, 
                static_folder='frontend',
                static_url_path='')

    # Security cookie settings
    app.config.update(
        SESSION_COOKIE_SECURE=True,           # Send session cookie only over HTTPS
        SESSION_COOKIE_HTTPONLY=True,         # Prevent JavaScript access
        SESSION_COOKIE_SAMESITE='Lax',        # Good CSRF protection
        PERMANENT_SESSION_LIFETIME=timedelta(days=31)  # Session expires after 31 days
    )

    # Load base configuration
    try:
        app.config.from_object(config[config_name])
        print(f"✅ Configuration loaded: {config_name}")
    except KeyError as e:
        print(f"❌ Configuration error - unknown config: {e}")
        raise
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        traceback.print_exc()
        raise

    # ============================================
    # DATABASE CONFIGURATION FOR MYSQL ON RENDER (Aiven)
    # ============================================
    print("\n📊 Database Configuration:")
    
    # Get DATABASE_URL from environment
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL not set!")
        print("   Please set DATABASE_URL environment variable")
        raise ValueError("DATABASE_URL environment variable must be set")
    
    # Parse the URL to extract components and add SSL parameters if needed
    parsed = urlparse(database_url)
    
    # Ensure we use pymysql driver
    if parsed.scheme in ('mysql', 'mysql+pymysql'):
        scheme = 'mysql+pymysql'
    else:
        scheme = parsed.scheme
    
    # Rebuild URI without query string (SSL will be handled via connect_args)
    clean_parsed = parsed._replace(query='')
    clean_uri = urlunparse(clean_parsed._replace(scheme=scheme))
    
    app.config['SQLALCHEMY_DATABASE_URI'] = clean_uri
    
    # Check if SSL is required (Aiven, or any cloud MySQL)
    host = parsed.hostname or ''
    ssl_required = '.aivencloud.com' in host or os.getenv('MYSQL_SSL_REQUIRED', 'False').lower() == 'true'
    
    # Build engine options
    engine_options = {
        'pool_size': int(os.getenv('SQLALCHEMY_POOL_SIZE', 10)),
        'pool_recycle': int(os.getenv('SQLALCHEMY_POOL_RECYCLE', 3600)),
        'pool_pre_ping': True,
        'pool_timeout': 30,
        'max_overflow': 20,
    }
    
    # Add SSL configuration if required
    if ssl_required:
        ca_cert = os.getenv('MYSQL_SSL_CA')
        if ca_cert and os.path.exists(ca_cert):
            ssl_dict = {'ca': ca_cert}
        else:
            ssl_dict = {'ssl': True}
        engine_options['connect_args'] = {'ssl': ssl_dict}
        print(f"   🔒 SSL enabled for database connection")
    else:
        engine_options['connect_args'] = {}
    
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = engine_options
    
    # Determine database type
    if 'mysql' in clean_uri.lower():
        db_type = "MySQL"
    elif 'postgresql' in clean_uri.lower():
        db_type = "PostgreSQL"
    else:
        db_type = "Unknown"
    
    print(f"   Database Type: {db_type}")
    
    # Mask sensitive parts for logging
    masked_uri = clean_uri
    if '@' in masked_uri:
        parts = masked_uri.split('@')
        if ':' in parts[0]:
            user_pass = parts[0].split(':')
            if len(user_pass) == 2:
                masked_uri = f"{user_pass[0]}:****@{parts[1]}"
    print(f"   Masked URI: {masked_uri}")
    print(f"   Engine options: pool_size={engine_options['pool_size']}, recycle={engine_options['pool_recycle']}, ssl={'Yes' if ssl_required else 'No'}")

    # ============================================
    # WRITE GOOGLE CREDENTIALS FILE FROM ENVIRONMENT VARIABLE
    # ============================================
    google_creds_b64 = os.environ.get('GOOGLE_CREDENTIALS_JSON_BASE64')
    if google_creds_b64:
        creds_dir = os.path.join(os.path.dirname(__file__), 'backend', 'config')
        os.makedirs(creds_dir, exist_ok=True)
        creds_path = os.path.join(creds_dir, 'gips-meet-key.json')
        try:
            with open(creds_path, 'wb') as f:
                f.write(base64.b64decode(google_creds_b64))
            print(f"\n✅ Google credentials written to {creds_path}")
        except Exception as e:
            print(f"\n⚠️  Failed to write Google credentials: {e}")
            logger.warning(f"Google credentials error: {e}")
    else:
        print("\n⚠️  GOOGLE_CREDENTIALS_JSON_BASE64 not set, online classes may not work")

    # Ensure required secret keys are present
    if not app.config.get('SECRET_KEY') or app.config.get('SECRET_KEY') == 'dev-secret-key-change-in-production':
        raise ValueError("❌ SECRET_KEY must be set in environment variables (FLASK_SECRET_KEY)")

    # Ensure upload folder exists
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    for subdir in ['documents', 'assignments', 'research', 'attachments', 'profiles']:
        os.makedirs(os.path.join(upload_folder, subdir), exist_ok=True)

    # Print configuration summary
    print(f"\n⚙️  Configuration Summary:")
    print(f"   📧 Email Service: {'✅ Enabled' if app.config.get('MAIL_USERNAME') else '❌ Disabled'}")
    print(f"   📁 Upload Folder: {upload_folder}")
    print(f"   🔐 JWT Secret: {'✅ Configured' if app.config.get('JWT_SECRET_KEY') else '❌ Not set'}")
    print(f"   🔗 CORS: Enabled for all origins")
    print(f"   🎓 Moodle Integration: {'✅ Enabled' if app.config.get('MOODLE_URL') and app.config.get('MOODLE_API_TOKEN') else '❌ Not configured'}")

    # ============================================
    # INITIALIZE EXTENSIONS
    # ============================================
    
    print("\n🔧 Initializing Extensions:")
    
    # Initialize Database
    try:
        db.init_app(app)
        print("   ✅ SQLAlchemy initialized")
    except Exception as e:
        print(f"   ❌ SQLAlchemy initialization failed: {e}")
        traceback.print_exc()
        raise
    
    # Initialize CORS
    try:
        CORS(app, resources={
            r"/api/*": {"origins": "*"},
            r"/uploads/*": {"origins": "*"}
        })
        print("   ✅ CORS initialized")
    except Exception as e:
        print(f"   ⚠️  CORS initialization warning: {e}")
        logger.warning(f"CORS init error: {e}")

    # Initialize Flask-Mail
    try:
        mail.init_app(app)
        print("   ✅ Flask-Mail initialized")
        if app.config.get('MAIL_USERNAME'):
            print(f"      📧 Email enabled: {app.config.get('MAIL_USERNAME')}")
        else:
            print(f"      📧 Email disabled: Configure MAIL_USERNAME to enable")
    except Exception as e:
        print(f"   ⚠️  Flask-Mail initialization warning: {e}")
        logger.warning(f"Mail init error: {e}")

    # Setup JWT
    try:
        jwt = JWTManager(app)
        print("   ✅ JWT Manager initialized")
    except Exception as e:
        print(f"   ❌ JWT Manager initialization failed: {e}")
        raise

    # JWT callbacks
    @jwt.unauthorized_loader
    def unauthorized_response(callback):
        return jsonify({
            'error': 'Missing or invalid token',
            'message': 'Please provide a valid access token',
            'status': 401
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_response(error):
        return jsonify({
            'error': 'Invalid token',
            'message': str(error),
            'status': 401
        }), 401

    @jwt.expired_token_loader
    def expired_token_response(jwt_header, jwt_payload):
        return jsonify({
            'error': 'Token has expired',
            'message': 'Please refresh your token or login again',
            'status': 401
        }), 401

    @jwt.revoked_token_loader
    def revoked_token_response(jwt_header, jwt_payload):
        return jsonify({
            'error': 'Token has been revoked',
            'message': 'Please login again',
            'status': 401
        }), 401

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        try:
            jti = jwt_payload["jti"]
            from models import TokenBlocklist
            token = TokenBlocklist.query.filter_by(jti=jti).first()
            return token is not None
        except Exception as e:
            logger.debug(f"Token blocklist check error: {e}")
            return False

    # Setup login manager
    try:
        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'
        login_manager.login_message = 'Please log in to access this page.'
        login_manager.login_message_category = 'info'
        print("   ✅ Login Manager initialized")
    except Exception as e:
        print(f"   ❌ Login Manager initialization failed: {e}")
        raise

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception as e:
            logger.debug(f"User loader error: {e}")
            return None

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Please log in to access this resource'
        }), 401

    # ============================================
    # OAUTH2 SERVER INITIALIZATION (for Moodle SSO)
    # ============================================
    print("\n🔐 Initializing OAuth2 Server for Moodle SSO:")
    try:
        authorization.init_app(app)
        authorization.register_grant(PasswordGrant)
        authorization.register_grant(AuthorizationCodeGrant)
        print("   ✅ OAuth2 Authorization Server initialized")
        print("      📌 Grants registered: Password, Authorization Code")
        app._oauth2_codes = {}
        print("      📌 Using in-memory code store (development mode)")
    except Exception as e:
        print(f"   ❌ OAuth2 Server initialization failed: {e}")
        logger.error(f"OAuth2 init error: {e}")
        raise

    # ============================================
    # DATABASE AND INITIALIZATION
    # ============================================
    
    # Create database tables and initialize chatbot
    with app.app_context():
        print("\n📁 Setting up Database:")
        try:
            print("   Creating database tables...")
            # Test connection first
            try:
                from sqlalchemy import text
                with db.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                print("   ✅ Database connection verified before creating tables")
            except Exception as conn_err:
                print(f"   ❌ Database connection failed: {conn_err}")
                traceback.print_exc()
                raise
            
            # Create all tables
            db.create_all()
            print("   ✅ Database tables created/verified!")
            
            # List tables
            try:
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                tables = inspector.get_table_names()
                print(f"   📊 Total tables in database: {len(tables)}")
                if tables:
                    print("   📋 Tables created:")
                    for i, table in enumerate(sorted(tables), 1):
                        print(f"      {i:2d}. {table}")
                else:
                    print("   ⚠️  No tables found in database")
            except Exception as e:
                print(f"   ⚠️  Could not list tables: {e}")
                logger.warning(f"Table inspection error: {e}")
                
        except Exception as e:
            print(f"   ❌ Database setup error: {e}")
            logger.error(f"Database setup error: {e}")
            traceback.print_exc()
            print("   ⚠️  Continuing despite database setup error – some features may not work")

        print("\n🤖 Initializing Chatbot:")
        try:
            from backend.utils.chatbot import StudentManagementChatbot
            chatbot = StudentManagementChatbot(app=app)
            app.config['CHATBOT'] = chatbot
            print("   ✅ Chatbot initialized successfully!")
            print(f"      📍 Database: {app.config.get('CHATBOT_DB_PATH', 'database/chatbot.db')}")
            if hasattr(chatbot, 'departments'):
                print(f"      🏢 Departments configured: {len(chatbot.departments)}")
        except ImportError as e:
            print(f"   ⚠️  Chatbot import error: {e}")
            print("      Chatbot module not found. Chatbot will not be available.")
            app.config['CHATBOT'] = None
        except Exception as e:
            print(f"   ⚠️  Chatbot initialization error: {e}")
            traceback.print_exc()
            logger.error(f"Chatbot initialization error: {e}")
            app.config['CHATBOT'] = None

    # ==================== REGISTER BLUEPRINTS ====================
    print("\n📌 Registering API Blueprints:")
    blueprints_registered = []
    blueprints_failed = []

    blueprints_to_register = [
        ('Auth', 'backend.routes.auth', 'auth_bp', '/api/auth'),
        ('Students', 'backend.routes.students', 'students_bp', '/api/students'),
        ('API', 'backend.routes.api', 'api_bp', '/api'),
        ('Chatbot', 'backend.routes.chatbot_routes', 'chatbot_bp', '/api/chatbot'),
        ('Admin', 'backend.routes.admin', 'admin_bp', '/api/admin'),
        ('Online Classes', 'backend.routes.online_classes', 'online_classes_bp', '/api/classes'),
        ('Lecturer', 'backend.routes.lecturer', 'lecturer_bp', '/api/lecturer'),
        ('Payments', 'backend.routes.payments', 'payments_bp', '/api/payments'),
        ('Accommodation', 'backend.routes.accomodation', 'accommodation_bp', '/api/accommodation'),
        ('Alumni', 'backend.routes.alumni', 'alumni_bp', '/api/alumni'),
    ]

    for name, module_path, blueprint_var, url_prefix in blueprints_to_register:
        try:
            module = __import__(module_path, fromlist=[blueprint_var])
            blueprint = getattr(module, blueprint_var)
            app.register_blueprint(blueprint, url_prefix=url_prefix)
            blueprints_registered.append(name.lower().replace(' ', '_'))
            print(f"   ✅ {name:20s} routes registered ({url_prefix})")
            logger.info(f"{name} blueprint registered at {url_prefix}")
        except ImportError as e:
            error_msg = f"Import Error: {str(e)}"
            print(f"   ❌ {name:20s} routes FAILED - {error_msg}")
            blueprints_failed.append((name, error_msg))
            logger.error(f"{name} blueprint import failed: {e}")
        except AttributeError as e:
            error_msg = f"Blueprint not found: {blueprint_var}"
            print(f"   ❌ {name:20s} routes FAILED - {error_msg}")
            blueprints_failed.append((name, error_msg))
            logger.error(f"{name} blueprint attribute error: {e}")
        except Exception as e:
            error_msg = f"Unknown Error: {str(e)}"
            print(f"   ❌ {name:20s} routes FAILED - {error_msg}")
            blueprints_failed.append((name, error_msg))
            logger.error(f"{name} blueprint registration failed: {e}")
            traceback.print_exc()

    print(f"\n📊 Blueprint Registration Summary:")
    print(f"   ✅ Registered: {len(blueprints_registered)}/10")
    print(f"   ❌ Failed: {len(blueprints_failed)}/10")
    
    if blueprints_failed:
        print(f"\n⚠️  Failed blueprints:")
        for name, error in blueprints_failed:
            print(f"   - {name}: {error}")

    # ==================== FRONTEND SERVING ====================

    @app.route('/')
    def index():
        """Serve the main index.html or fallback to API info."""
        try:
            if os.path.exists(os.path.join('frontend', 'index.html')):
                return send_from_directory('frontend', 'index.html')
        except Exception:
            pass
        return jsonify({
            'message': 'GIPS College Student Management System API',
            'version': '2.0.0',
            'status': 'running',
            'environment': config_name,
            'database': 'MySQL',
            'datetime': datetime.now().isoformat(),
            'email_service': '✅ Enabled' if app.config.get('MAIL_USERNAME') else '❌ Disabled',
            'moodle_integration': {
                'configured': bool(app.config.get('MOODLE_URL') and app.config.get('MOODLE_API_TOKEN')),
                'url': app.config.get('MOODLE_URL')
            },
            'endpoints': {
                'api': '/api',
                'health': '/api/health',
                'chatbot': '/api/chatbot/health',
                'auth': '/api/auth/login',
                'students': '/api/students',
                'dashboard': '/api/students/dashboard',
                'admin': '/api/admin/stats',
                'online_classes': '/api/classes/*'
            },
            'blueprints_registered': blueprints_registered,
            'blueprints_failed_count': len(blueprints_failed)
        }), 200

    @app.route('/index.html')
    def redirect_index():
        """Redirect old /index.html to root."""
        return redirect('/')

    @app.route('/pages/<path:filename>')
    def serve_pages(filename):
        try:
            return send_from_directory('frontend/pages', filename)
        except Exception as e:
            logger.error(f"Error serving page {filename}: {e}")
            return jsonify({'error': 'Page not found', 'path': filename}), 404

    # ============================================
    # PWA SUPPORT: Manifest and Service Worker
    # ============================================
    @app.route('/manifest.json')
    def manifest():
        """Serve the PWA manifest.json with proper caching."""
        return send_from_directory('frontend', 'manifest.json')

    @app.route('/service-worker.js')
    def service_worker():
        """Serve the service worker with no-cache headers and proper scope."""
        response = make_response(send_from_directory('frontend', 'service-worker.js'))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Service-Worker-Allowed'] = '/'
        return response

    # ============================================
    # PUBLIC PAGES (no authentication required)
    # Served directly from frontend/ folder
    # ============================================
    @app.route('/privacy')
    def privacy_page():
        """Serve the privacy notice page - PUBLIC ACCESS"""
        try:
            return send_from_directory('frontend', 'privacy.html')
        except Exception as e:
            logger.error(f"Error serving privacy page: {e}")
            return jsonify({'error': 'Privacy page not found'}), 404

    @app.route('/contacts')
    def contacts_page():
        """Serve the contacts page - PUBLIC ACCESS"""
        try:
            return send_from_directory('frontend', 'contacts.html')
        except Exception as e:
            logger.error(f"Error serving contacts page: {e}")
            return jsonify({'error': 'Contacts page not found'}), 404

    @app.route('/terms')
    def terms_page():
        """Serve the Terms of Service page - PUBLIC ACCESS"""
        try:
            return send_from_directory('frontend', 'terms.html')
        except Exception as e:
            logger.error(f"Error serving terms page: {e}")
            return jsonify({'error': 'Terms page not found'}), 404

    @app.route('/about')
    def about_page():
        """Serve the About Us page - PUBLIC ACCESS"""
        try:
            return send_from_directory('frontend', 'about.html')
        except Exception as e:
            logger.error(f"Error serving about page: {e}")
            return jsonify({'error': 'About page not found'}), 404

    @app.route('/css/<path:filename>')
    def serve_css(filename):
        try:
            return send_from_directory('frontend/css', filename)
        except Exception:
            return jsonify({'error': 'CSS file not found'}), 404

    @app.route('/js/<path:filename>')
    def serve_js(filename):
        try:
            return send_from_directory('frontend/js', filename)
        except Exception:
            return jsonify({'error': 'JS file not found'}), 404

    @app.route('/images/<path:filename>')
    def serve_images(filename):
        try:
            return send_from_directory('frontend/images', filename)
        except Exception:
            return jsonify({'error': 'Image not found'}), 404

    @app.route('/favicon/<path:filename>')
    def serve_favicon(filename):
        try:
            return send_from_directory('frontend/favicon', filename)
        except Exception:
            return jsonify({'error': 'Favicon not found'}), 404

    @app.route('/<path:filename>')
    def serve_static(filename):
        # Prevent serving API or upload routes through this catch-all
        if filename.startswith('api/') or filename.startswith('uploads/'):
            return jsonify({'error': 'Not found'}), 404
        try:
            if os.path.exists(os.path.join('frontend', filename)):
                return send_from_directory('frontend', filename)
        except Exception:
            pass
        return jsonify({'error': 'File not found', 'path': filename}), 404

    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        try:
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
        except Exception as e:
            logger.error(f"Error serving upload {filename}: {e}")
            return jsonify({'error': 'File not found'}), 404

    # ==================== API ROUTES ====================

    @app.route('/api', methods=['GET'])
    def api_root():
        return jsonify({
            'name': 'GIPS College Student Management System API',
            'version': '2.0.0',
            'status': 'operational',
            'environment': config_name,
            'database': 'MySQL',
            'email_service': 'Configured' if app.config.get('MAIL_USERNAME') else 'Not configured',
            'moodle_integration': {
                'configured': bool(app.config.get('MOODLE_URL') and app.config.get('MOODLE_API_TOKEN')),
                'url': app.config.get('MOODLE_URL')
            },
            'timestamp': datetime.now().isoformat(),
            'blueprints_registered': blueprints_registered,
            'blueprints_count': len(blueprints_registered),
            'blueprints_failed': len(blueprints_failed)
        }), 200

    @app.route('/api/health', methods=['GET'])
    def health():
        chatbot_status = 'available' if app.config.get('CHATBOT') else 'unavailable'
        db_status = 'connected'
        email_status = 'configured' if app.config.get('MAIL_USERNAME') else 'not_configured'
        
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            db_status = 'connected'
        except Exception as e:
            db_status = 'disconnected'
            logger.error(f"Health check database error: {e}")
        
        return jsonify({
            'status': 'OK',
            'message': 'Server is running',
            'environment': config_name,
            'database': 'MySQL',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'database': {
                    'status': db_status,
                    'type': 'MySQL'
                },
                'chatbot': {
                    'status': chatbot_status
                },
                'email': {
                    'status': email_status,
                    'features': [
                        'registration_confirmation',
                        'password_reset',
                        'email_verification',
                        'admission_decision',
                        'payment_confirmation'
                    ]
                },
                'moodle': {
                    'configured': bool(app.config.get('MOODLE_URL') and app.config.get('MOODLE_API_TOKEN')),
                    'url': app.config.get('MOODLE_URL')
                },
                'blueprints': {
                    'registered': len(blueprints_registered),
                    'failed': len(blueprints_failed),
                    'list': blueprints_registered
                }
            }
        }), 200

    @app.route('/api/chatbot-info', methods=['GET'])
    def chatbot_info():
        chatbot = app.config.get('CHATBOT')
        if not chatbot:
            return jsonify({'available': False, 'message': 'Chatbot not available'}), 503
        return jsonify({
            'available': True,
            'version': '1.0.0',
            'capabilities': [
                'Access issue resolution',
                'Ticket creation and tracking',
                'FAQ responses',
                'Department routing'
            ],
            'departments': list(chatbot.departments.keys()) if hasattr(chatbot, 'departments') else [],
            'max_tickets_per_student': app.config.get('CHATBOT_MAX_TICKETS_PER_STUDENT', 5),
            'response_time': 'Immediate for FAQs, 2-48 hours for tickets'
        }), 200

    # ==================== ERROR HANDLERS ====================

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Resource not found',
            'path': request.path,
            'method': request.method,
            'timestamp': datetime.now().isoformat()
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        try:
            db.session.rollback()
        except:
            pass
        logger.error(f"Server error: {error}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'Internal server error',
            'timestamp': datetime.now().isoformat()
        }), 500

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Forbidden', 'status': 403}), 403

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request', 'status': 400}), 400

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({'error': 'Method not allowed', 'status': 405}), 405

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({'error': 'File too large', 'status': 413}), 413

    # ==================== REQUEST LOGGING ====================

    @app.before_request
    def log_request_info():
        if request.path.startswith('/api/'):
            logger.info(f"📨 {request.method} {request.path}")

    print("\n" + "="*70)
    print("✅ Application initialization complete!")
    print("="*70 + "\n")

    return app


if __name__ == '__main__':
    app = create_app()

    print("\n" + "="*70)
    print("🎓 GIPS College Student Portal - Backend Server")
    print("="*70)
    print("✅ Server running on http://127.0.0.1:5000")
    print("✅ Press CTRL+C to stop")
    print("\n📌 Database: MySQL on Render")
    print("\n📌 Available Pages:")
    print("   🏠 http://localhost:5000/                 - Home Page")
    print("   🔐 http://localhost:5000/pages/login.html - Login Page")
    print("   📝 http://localhost:5000/pages/register.html - Register Page")
    print("   📊 http://localhost:5000/pages/student-dashboard.html - Dashboard")
    print("   💬 http://localhost:5000/pages/chatbot.html - Chatbot Support")
    print("   👑 http://localhost:5000/pages/admin.html - Admin Dashboard")
    print("   📜 http://localhost:5000/privacy           - Privacy Notice")
    print("   📞 http://localhost:5000/contacts          - Contacts Page")
    print("   ⚖️  http://localhost:5000/terms             - Terms of Service")
    print("   ℹ️  http://localhost:5000/about             - About Us")
    print("\n📌 Core API Endpoints:")
    print("   💚 GET  /api/health        - Health Check")
    print("   💚 GET  /api              - API Root")
    print("   🤖 GET  /api/chatbot-info  - Chatbot Info")
    print("\n📌 Authentication Endpoints (WITH EMAIL):")
    print("   🔐 POST /api/auth/register                    - Register")
    print("   🔐 POST /api/auth/login                       - Login")
    print("   🔐 POST /api/auth/forgot-password             - Request password reset")
    print("   🔐 POST /api/auth/reset-password/<token>      - Reset password")
    print("   📧 POST /api/auth/verify-email/<token>        - Verify email")
    print("   🔄 POST /api/auth/refresh                     - Refresh token")
    print("   🔐 GET  /api/auth/profile                     - Get profile")
    print("   🔐 PUT  /api/auth/profile                     - Update profile")
    print("   🔐 POST /api/auth/change-password             - Change password")
    print("   🏕  GET  /api/auth/campuses                    - Get campuses")
    print("   🏕  GET  /api/auth/campuses/<id>              - Get campus by ID")
    print("   📚 GET  /api/auth/campuses/<id>/programs      - Get programs at campus")
    print("\n📌 OAuth2 Endpoints (for Moodle SSO):")
    print("   🔑 GET  /oauth2/authorize   - Authorization endpoint")
    print("   🔑 POST /oauth2/token       - Token endpoint")
    print("   🔑 GET  /oauth2/userinfo    - Userinfo endpoint")
    print("\n📌 Admin Endpoints:")
    print("   👑 GET  /api/admin/stats               - Admin Statistics")
    print("   👑 GET  /api/admin/users               - Admin Users List")
    print("   👑 GET  /api/admin/students            - Admin Students List")
    print("   👑 GET  /api/admin/programs            - Admin Programs List")
    print("   👑 GET  /api/admin/modules             - Admin Modules List")
    print("   👑 POST /api/admin/users               - Create Admin User")
    print("   👑 PUT  /api/admin/users/<id>          - Update User")
    print("   👑 DELETE /api/admin/users/<id>        - Delete User")
    print("\n📌 Student Endpoints:")
    print("   📚 GET  /api/students/dashboard        - Student Dashboard")
    print("   📚 GET  /api/students/profile          - Student Profile")
    print("   📚 GET  /api/students/courses          - Enrolled Courses")
    print("   📚 GET  /api/students/grades           - Student Grades")
    print("\n📌 Online Classes Endpoints:")
    print("   🎥 POST /api/classes/course/<id>/start     - Start Live Class")
    print("   🎥 GET  /api/classes/course/<id>/meeting   - Get Meeting Info")
    print("   🎥 GET  /api/classes/course/<id>/join      - Embedded Meeting Page")
    print("   🎥 POST /api/classes/course/<id>/end       - End Live Class")
    print("\n📌 Payment Endpoints:")
    print("   💳 GET  /api/payments/config                    - Get Stripe config")
    print("   💳 POST /api/payments/create-payment-intent     - Create Payment Intent")
    print("   💳 POST /api/payments/confirm-payment           - Confirm Payment")
    print("   💳 GET  /api/payments/history                   - Payment History")
    print("   💳 GET  /api/payments/outstanding               - Outstanding Fees")
    print("\n📌 Chatbot Endpoints:")
    print("   🤖 POST /api/chatbot/create-ticket        - Create Support Ticket")
    print("   🤖 GET  /api/chatbot/tickets              - Get Your Tickets")
    print("   🤖 GET  /api/chatbot/faqs                 - Get FAQs")
    print("\n📌 Accommodation Endpoints:")
    print("   🏠 POST /api/accommodation/apply              - Apply for Accommodation")
    print("   🏠 GET  /api/accommodation/applications       - Your Applications")
    print("   🏠 GET  /api/accommodation/admin/applications - All Applications (Admin)")
    print("   🏠 GET  /api/accommodation/admin/rooms        - All Rooms (Admin)")
    print("\n📌 Lecturer Endpoints:")
    print("   👨‍🏫 GET  /api/lecturer/courses            - My Courses")
    print("   👨‍🏫 GET  /api/lecturer/students           - My Students")
    print("   👨‍🏫 POST /api/lecturer/create-assignment   - Create Assignment")
    print("\n📌 Alumni Endpoints:")
    print("   👥 GET  /api/alumni/profile               - Alumni Profile")
    print("   👥 GET  /api/alumni/jobs/recommended      - Job Recommendations")
    print("   👥 GET  /api/alumni/stats                 - Alumni Statistics")
    print("\n📌 Email Features (INTEGRATED):")
    print("   ✉️  ✅ Registration confirmation emails")
    print("   🔐  ✅ Password reset emails with 1-hour secure tokens")
    print("   📧  ✅ Email verification with 24-hour tokens")
    print("   ✅  ✅ Admission decision notifications")
    print("   💳  ✅ Payment confirmation emails")
    print("   📋  ✅ Secure token validation and expiry")
    print("="*70 + "\n")

    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    try:
        app.run(debug=debug, host=host, port=port)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        print(f"\n❌ Failed to start server: {e}")
        traceback.print_exc()
        sys.exit(1)