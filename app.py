# app.py
import sys
import os
from pathlib import Path
from datetime import datetime

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / 'backend'))

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import logging
import traceback
from sqlalchemy import text  # <-- Added for safe raw SQL

# Load environment variables
load_dotenv()

# Now import after adding to path
from models import db, User
from config import config

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

    print("\n" + "="*60)
    print(f"🚀 Starting GIPS College Student Management System")
    print(f"📌 Environment: {config_name.upper()} mode")
    print("="*60)

    # Initialize Flask with correct static folder
    app = Flask(__name__, 
                static_folder='frontend',
                static_url_path='')

    # Load configuration
    app.config.from_object(config[config_name])

    # Ensure required secret keys are present (config already does this, but double-check)
    if not app.config.get('SECRET_KEY') or app.config.get('SECRET_KEY') == 'dev-secret-key-change-in-production':
        raise ValueError("SECRET_KEY must be set in environment variables (FLASK_SECRET_KEY)")

    # Ensure upload folder exists
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    for subdir in ['documents', 'assignments', 'research', 'attachments', 'profiles']:
        os.makedirs(os.path.join(upload_folder, subdir), exist_ok=True)

    # Print configuration summary (hide sensitive parts)
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    # Mask password in log for security
    if '@' in db_uri:
        parts = db_uri.split('@')
        if ':' in parts[0]:
            user_pass = parts[0].split(':')
            if len(user_pass) == 2:
                masked_uri = f"{user_pass[0]}:****@{parts[1]}"
            else:
                masked_uri = db_uri
        else:
            masked_uri = db_uri
    else:
        masked_uri = db_uri
    print(f"📊 Database: {masked_uri}")
    print(f"📧 Email Notifications: {'Enabled' if app.config.get('CHATBOT_ENABLE_EMAIL') else 'Disabled'}")
    print(f"📁 Upload Folder: {app.config.get('UPLOAD_FOLDER', 'uploads')}")
    print(f"🔐 JWT Secret: {'Configured' if app.config.get('JWT_SECRET_KEY') else 'Using Default'}")

    # Initialize extensions
    db.init_app(app)
    CORS(app, resources={
        r"/api/*": {"origins": "*"},
        r"/uploads/*": {"origins": "*"}
    })

    # Setup JWT
    jwt = JWTManager(app)

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
        """Check if token is revoked"""
        try:
            jti = jwt_payload["jti"]
            from models import TokenBlocklist
            token = TokenBlocklist.query.filter_by(jti=jti).first()
            return token is not None
        except:
            return False

    # Setup login manager (for session-based auth)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except:
            return None

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Please log in to access this resource'
        }), 401

    # Create database tables and initialize chatbot
    with app.app_context():
        print("\n📁 Setting up database...")
        try:
            db.create_all()
            print("✅ Database tables created/verified!")

            # Check if tables were created successfully
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"   📊 Tables in database: {len(tables)}")
            for table in tables[:10]:
                print(f"      - {table}")
            if len(tables) > 10:
                print(f"      ... and {len(tables) - 10} more")

        except Exception as e:
            print(f"⚠️ Database setup warning: {e}")
            logger.error(f"Database setup error: {e}")

        # Initialize chatbot with Flask app
        print("\n🤖 Initializing Chatbot...")
        try:
            from backend.utils.chatbot import StudentManagementChatbot
            chatbot = StudentManagementChatbot(app=app)
            app.config['CHATBOT'] = chatbot
            print("✅ Chatbot initialized successfully!")
            print(f"   📍 Database: {app.config.get('CHATBOT_DB_PATH', 'database/chatbot.db')}")
            print(f"   🎫 Max tickets per student: {app.config.get('CHATBOT_MAX_TICKETS_PER_STUDENT', 5)}")
            print(f"   📧 Email notifications: {'Enabled' if app.config.get('CHATBOT_ENABLE_EMAIL') else 'Disabled'}")
            if hasattr(chatbot, 'departments'):
                print(f"   🏢 Departments: {len(chatbot.departments)}")
        except ImportError as e:
            print(f"⚠️ Chatbot import error: {e}")
            print("   Chatbot module not found. Chatbot will not be available.")
            app.config['CHATBOT'] = None
        except Exception as e:
            print(f"⚠️ Chatbot initialization error: {e}")
            traceback.print_exc()
            print("   Chatbot will not be available until fixed.")
            app.config['CHATBOT'] = None

    # ==================== REGISTER BLUEPRINTS ====================
    print("\n📌 Registering API endpoints...")
    blueprints_registered = []

    # Auth routes
    try:
        from routes.auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        blueprints_registered.append('auth')
        print("   ✅ Auth routes registered")
    except ImportError as e:
        print(f"   ⚠️ Auth routes not available: {e}")
    except Exception as e:
        print(f"   ⚠️ Error registering auth routes: {e}")

    # Students routes
    try:
        from routes.students import students_bp
        app.register_blueprint(students_bp, url_prefix='/api/students')
        blueprints_registered.append('students')
        print("   ✅ Students routes registered")
    except ImportError as e:
        print(f"   ⚠️ Students routes not available: {e}")
    except Exception as e:
        print(f"   ⚠️ Error registering students routes: {e}")

    # API routes
    try:
        from backend.routes.api import api_bp
        app.register_blueprint(api_bp, url_prefix='/api')
        blueprints_registered.append('api')
        print("   ✅ API routes registered")
    except ImportError as e:
        print(f"   ⚠️ API routes not available: {e}")
    except Exception as e:
        print(f"   ⚠️ Error registering API routes: {e}")

    # Chatbot routes
    try:
        from backend.routes.chatbot_routes import chatbot_bp
        app.register_blueprint(chatbot_bp, url_prefix='/api/chatbot')
        blueprints_registered.append('chatbot')
        print("   ✅ Chatbot routes registered")
    except ImportError as e:
        print(f"   ⚠️ Chatbot routes not available: {e}")
    except Exception as e:
        print(f"   ⚠️ Error registering chatbot routes: {e}")

    # ==================== ADMIN BLUEPRINT ====================
    try:
        from backend.routes.admin import admin_bp
        app.register_blueprint(admin_bp, url_prefix='/api/admin')
        blueprints_registered.append('admin')
        print("   ✅ Admin routes registered")
        print("   📍 Admin endpoints available at /api/admin/*")
    except ImportError as e:
        print(f"   ⚠️ Admin routes not available: {e}")
        print("   To fix: Create backend/routes/admin.py with the required admin blueprint")
    except Exception as e:
        print(f"   ⚠️ Error registering admin routes: {e}")
        logger.error(f"Admin routes registration error: {e}")
        traceback.print_exc()

    # ==================== ONLINE CLASSES BLUEPRINT ====================
    try:
        from backend.routes.online_classes import online_classes_bp
        # Ensure blueprint has a URL prefix; if not set in blueprint, set it here
        app.register_blueprint(online_classes_bp, url_prefix='/api/classes')
        blueprints_registered.append('online_classes')
        print("   ✅ Online Classes routes registered")
        print("   📍 Online Classes endpoints available at /api/classes/*")
    except ImportError as e:
        print(f"   ⚠️ Online Classes routes not available: {e}")
        print("   To fix: Create backend/routes/online_classes.py with the required blueprint")
    except Exception as e:
        print(f"   ⚠️ Error registering online classes routes: {e}")
        logger.error(f"Online classes routes registration error: {e}")
        traceback.print_exc()

    # ==================== FRONTEND SERVING ====================

    @app.route('/')
    def index():
        """Serve the main frontend page"""
        try:
            # Check if index.html exists in frontend folder
            if os.path.exists(os.path.join('frontend', 'index.html')):
                return send_from_directory('frontend', 'index.html')
        except Exception:
            pass

        # Fallback to API info
        return jsonify({
            'message': 'GIPS College Student Management System API',
            'version': '2.0.0',
            'status': 'running',
            'environment': config_name,
            'datetime': datetime.now().isoformat(),
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
            'blueprints': blueprints_registered
        }), 200

    @app.route('/pages/<path:filename>')
    def serve_pages(filename):
        """Serve pages from the pages folder"""
        try:
            return send_from_directory('frontend/pages', filename)
        except Exception as e:
            logger.error(f"Error serving page {filename}: {e}")
            return jsonify({'error': 'Page not found', 'path': filename}), 404

    @app.route('/css/<path:filename>')
    def serve_css(filename):
        """Serve CSS files"""
        try:
            return send_from_directory('frontend/css', filename)
        except Exception:
            return jsonify({'error': 'CSS file not found'}), 404

    @app.route('/js/<path:filename>')
    def serve_js(filename):
        """Serve JavaScript files"""
        try:
            return send_from_directory('frontend/js', filename)
        except Exception:
            return jsonify({'error': 'JS file not found'}), 404

    @app.route('/images/<path:filename>')
    def serve_images(filename):
        """Serve image files"""
        try:
            return send_from_directory('frontend/images', filename)
        except Exception:
            return jsonify({'error': 'Image not found'}), 404

    @app.route('/<path:filename>')
    def serve_static(filename):
        """Serve other static files from frontend root"""
        # Skip API and special paths to avoid interfering with blueprint routes
        if filename.startswith('api/') or filename.startswith('uploads/'):
            return jsonify({'error': 'Not found'}), 404
        try:
            # Check if file exists in frontend root
            if os.path.exists(os.path.join('frontend', filename)):
                return send_from_directory('frontend', filename)
        except Exception:
            pass
        return jsonify({'error': 'File not found', 'path': filename}), 404

    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        """Serve uploaded files (documents, assignments, etc.)"""
        try:
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
        except Exception as e:
            logger.error(f"Error serving upload {filename}: {e}")
            return jsonify({'error': 'File not found'}), 404

    # ==================== API ROUTES ====================

    @app.route('/api', methods=['GET'])
    def api_root():
        """API root endpoint"""
        return jsonify({
            'name': 'GIPS College Student Management System API',
            'version': '2.0.0',
            'status': 'operational',
            'environment': config_name,
            'timestamp': datetime.now().isoformat(),
            'blueprints': blueprints_registered
        }), 200

    @app.route('/api/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        chatbot_status = 'available' if app.config.get('CHATBOT') else 'unavailable'

        # Check database connection using safe text()
        db_status = 'connected'
        try:
            db.session.execute(text('SELECT 1'))
        except Exception as e:
            db_status = 'disconnected'
            logger.error(f"Database connection error: {e}")

        return jsonify({
            'status': 'OK',
            'message': 'Server is running',
            'environment': config_name,
            'timestamp': datetime.now().isoformat(),
            'services': {
                'database': {'status': db_status},
                'chatbot': {'status': chatbot_status},
                'blueprints': blueprints_registered
            }
        }), 200

    @app.route('/api/chatbot-info', methods=['GET'])
    def chatbot_info():
        """Get chatbot information"""
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
        db.session.rollback()
        logger.error(f"Server error: {error}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'Internal server error',
            'timestamp': datetime.now().isoformat()
        }), 500

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Forbidden'}), 403

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized'}), 401

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request'}), 400

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({'error': 'Method not allowed'}), 405

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({'error': 'File too large'}), 413

    # ==================== REQUEST LOGGING ====================

    @app.before_request
    def log_request_info():
        """Log incoming requests"""
        if request.path.startswith('/api/'):
            logger.info(f"📨 {request.method} {request.path}")

    print("\n" + "="*60)
    print("✅ Application initialization complete!")
    print("="*60)

    return app


if __name__ == '__main__':
    # This block runs only when executing directly (e.g., python app.py)
    # For production (gunicorn), this block is ignored.
    app = create_app()

    print("\n" + "="*60)
    print("🎓 GIPS College Student Portal - Backend Server")
    print("="*60)
    print("✅ Server running on http://127.0.0.1:5000")
    print("✅ Press CTRL+C to stop")
    print("\n📌 Available Pages:")
    print("   🏠 http://localhost:5000/                 - Home Page")
    print("   🔐 http://localhost:5000/pages/login.html - Login Page")
    print("   📝 http://localhost:5000/pages/register.html - Register Page")
    print("   📊 http://localhost:5000/pages/student-dashboard.html - Dashboard")
    print("   💬 http://localhost:5000/pages/chatbot.html - Chatbot Support")
    print("   👑 http://localhost:5000/pages/admin.html - Admin Dashboard")
    print("\n📌 API Endpoints:")
    print("   💚 GET  /api/health        - Health Check")
    print("   🤖 GET  /api/chatbot-info  - Chatbot Info")
    print("   🔐 POST /api/auth/login    - Login")
    print("   📝 POST /api/auth/register - Register")
    print("   👑 GET  /api/admin/stats   - Admin Statistics")
    print("   👑 GET  /api/admin/users   - Admin Users List")
    print("   👑 GET  /api/admin/students - Admin Students List")
    print("   👑 GET  /api/admin/programs - Admin Programs List")
    print("   👑 GET  /api/admin/modules  - Admin Modules List")
    print("   👑 POST /api/admin/users    - Create Admin User")
    print("   👑 PUT  /api/admin/users/<id> - Update User")
    print("   👑 DELETE /api/admin/users/<id> - Delete User")
    print("\n📌 Online Classes Endpoints:")
    print("   🎥 POST /api/classes/course/<id>/start     - Start Live Class (Google Meet)")
    print("   🎥 GET  /api/classes/course/<id>/meeting   - Get Meeting Info")
    print("   🎥 GET  /api/classes/course/<id>/join      - Embedded Meeting Page")
    print("   🎥 POST /api/classes/course/<id>/end       - End Live Class")
    print("="*60 + "\n")

    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'

    try:
        app.run(debug=debug, host=host, port=port)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        print(f"\n❌ Failed to start server: {e}")
        sys.exit(1)