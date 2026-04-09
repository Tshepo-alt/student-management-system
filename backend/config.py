# config.py
import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote_plus, urlparse, parse_qs, urlunparse

class Config:
    """Base configuration"""
    
    # ============================================
    # FLASK APPLICATION SETTINGS
    # ============================================
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("FLASK_SECRET_KEY must be set in production")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # ============================================
    # DATABASE CONFIGURATION - MYSQL (using mysql-connector-python)
    # ============================================
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'gips_college_db')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    
    # URL encode password to handle special characters
    encoded_password = quote_plus(MYSQL_PASSWORD)
    
    # Build MySQL connection string
    if os.environ.get('DATABASE_URL'):
        raw_url = os.environ.get('DATABASE_URL')
        # Convert mysql+pymysql to mysql+mysqlconnector and handle SSL params
        if raw_url.startswith('mysql+pymysql://'):
            raw_url = raw_url.replace('mysql+pymysql://', 'mysql+mysqlconnector://')
        # Remove any ?ssl=true or ?ssl-mode=REQUIRED because mysql-connector uses different syntax
        # We'll add ssl-mode=REQUIRED if not present and if SSL is needed
        parsed = urlparse(raw_url)
        query = parse_qs(parsed.query)
        # Ensure ssl-mode=REQUIRED for Aiven (or any cloud MySQL requiring SSL)
        if 'ssl-mode' not in query and 'ssl' not in query:
            # Add ssl-mode=REQUIRED
            new_query = dict(query)
            new_query['ssl-mode'] = ['REQUIRED']
            new_parsed = parsed._replace(query='&'.join(f"{k}={v[0]}" for k, v in new_query.items()))
            raw_url = urlunparse(new_parsed)
        SQLALCHEMY_DATABASE_URI = raw_url
    else:
        SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector://{MYSQL_USER}:{encoded_password}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?ssl-mode=REQUIRED"
    
    # MySQL Engine Options for better performance
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('SQLALCHEMY_POOL_SIZE', 10)),
        'pool_recycle': int(os.environ.get('SQLALCHEMY_POOL_RECYCLE', 3600)),
        'pool_pre_ping': True,
        'pool_timeout': 30,
        'max_overflow': 20
    }
    
    # ============================================
    # JWT CONFIGURATION
    # ============================================
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or os.environ.get('SECRET_KEY')
    if not JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY must be set in production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES_MINUTES', 60)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES_DAYS', 30)))
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES_MINUTES', 60))
    JWT_REFRESH_TOKEN_EXPIRES_DAYS = int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES_DAYS', 30))
    
    # ============================================
    # STRIPE PAYMENT CONFIGURATION
    # ============================================
    STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
    STRIPE_CURRENCY = os.environ.get('STRIPE_CURRENCY', 'BWP')
    
    # ============================================
    # EMAIL CONFIGURATION (SMTP)
    # ============================================
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', MAIL_USERNAME)
    MAIL_SUBJECT_PREFIX = os.environ.get('MAIL_SUBJECT_PREFIX', '[GIPS College]')
    MAIL_USE_TEMPLATES = os.environ.get('MAIL_USE_TEMPLATES', 'True').lower() == 'true'
    
    # ============================================
    # FILE UPLOAD SETTINGS
    # ============================================
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 50 * 1024 * 1024))  # 50 MB
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(os.path.dirname(__file__), 'uploads'))
    
    # Create absolute path for upload folder
    if not os.path.isabs(UPLOAD_FOLDER):
        UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), UPLOAD_FOLDER)
    
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'zip', 'rar', 'jpg', 'jpeg', 'png', 'gif', 'xls', 'xlsx', 'ppt', 'pptx', 'csv', 'mp4', 'mp3'}
    
    # Upload subdirectories
    UPLOAD_DOCUMENTS = os.environ.get('UPLOAD_DOCUMENTS', 'uploads/documents')
    UPLOAD_ASSIGNMENTS = os.environ.get('UPLOAD_ASSIGNMENTS', 'uploads/assignments')
    UPLOAD_RESEARCH = os.environ.get('UPLOAD_RESEARCH', 'uploads/research')
    UPLOAD_ATTACHMENTS = os.environ.get('UPLOAD_ATTACHMENTS', 'uploads/attachments')
    UPLOAD_PROFILE_PICTURES = os.environ.get('UPLOAD_PROFILE_PICTURES', 'uploads/profiles')
    
    # ============================================
    # CHATBOT CONFIGURATION
    # ============================================
    CHATBOT_DB_PATH = os.environ.get('CHATBOT_DB_PATH', 'database/chatbot.db')
    CHATBOT_ENABLE_EMAIL = os.environ.get('CHATBOT_ENABLE_EMAIL', 'False').lower() == 'true'
    CHATBOT_MAX_TICKETS_PER_STUDENT = int(os.environ.get('CHATBOT_MAX_TICKETS_PER_STUDENT', 5))
    CHATBOT_TICKET_EXPIRY_DAYS = int(os.environ.get('CHATBOT_TICKET_EXPIRY_DAYS', 30))
    CHATBOT_USE_AI = os.environ.get('CHATBOT_USE_AI', 'False').lower() == 'true'
    CHATBOT_OPENAI_API_KEY = os.environ.get('CHATBOT_OPENAI_API_KEY')
    
    # ============================================
    # DEPARTMENT CONTACT INFORMATION
    # ============================================
    IT_SUPPORT_EMAIL = os.environ.get('IT_SUPPORT_EMAIL', 'it@gipscollege.edu.bw')
    IT_SUPPORT_PHONE = os.environ.get('IT_SUPPORT_PHONE', '+267712345678')
    IT_SUPPORT_OFFICE = os.environ.get('IT_SUPPORT_OFFICE', 'Room 101, Main Building')
    
    ACADEMIC_EMAIL = os.environ.get('ACADEMIC_EMAIL', 'academic@gipscollege.edu.bw')
    ACADEMIC_PHONE = os.environ.get('ACADEMIC_PHONE', '+267712345679')
    ACADEMIC_OFFICE = os.environ.get('ACADEMIC_OFFICE', 'Room 201, Academic Block')
    
    FINANCE_EMAIL = os.environ.get('FINANCE_EMAIL', 'finance@gipscollege.edu.bw')
    FINANCE_PHONE = os.environ.get('FINANCE_PHONE', '+267712345680')
    FINANCE_OFFICE = os.environ.get('FINANCE_OFFICE', 'Room 301, Finance Building')
    
    STUDENT_SERVICES_EMAIL = os.environ.get('STUDENT_SERVICES_EMAIL', 'studentservices@gipscollege.edu.bw')
    STUDENT_SERVICES_PHONE = os.environ.get('STUDENT_SERVICES_PHONE', '+267712345681')
    STUDENT_SERVICES_OFFICE = os.environ.get('STUDENT_SERVICES_OFFICE', 'Student Center, Ground Floor')
    
    EXAMINATION_EMAIL = os.environ.get('EXAMINATION_EMAIL', 'exams@gipscollege.edu.bw')
    EXAMINATION_PHONE = os.environ.get('EXAMINATION_PHONE', '+267712345682')
    EXAMINATION_OFFICE = os.environ.get('EXAMINATION_OFFICE', 'Room 401, Examination Hall')
    
    ADMISSIONS_EMAIL = os.environ.get('ADMISSIONS_EMAIL', 'admissions@gipscollege.edu.bw')
    ADMISSIONS_PHONE = os.environ.get('ADMISSIONS_PHONE', '+267712345683')
    ADMISSIONS_OFFICE = os.environ.get('ADMISSIONS_OFFICE', 'Room 001, Administration Block')
    
    LIBRARY_EMAIL = os.environ.get('LIBRARY_EMAIL', 'library@gipscollege.edu.bw')
    LIBRARY_PHONE = os.environ.get('LIBRARY_PHONE', '+267712345684')
    LIBRARY_OFFICE = os.environ.get('LIBRARY_OFFICE', 'Library Building, 1st Floor')
    
    CAREER_EMAIL = os.environ.get('CAREER_EMAIL', 'careers@gipscollege.edu.bw')
    CAREER_PHONE = os.environ.get('CAREER_PHONE', '+267712345685')
    CAREER_OFFICE = os.environ.get('CAREER_OFFICE', 'Student Center, 2nd Floor')
    
    # ============================================
    # COLLEGE INFORMATION
    # ============================================
    COLLEGE_NAME = os.environ.get('COLLEGE_NAME', 'GIPS College')
    COLLEGE_SHORT_NAME = os.environ.get('COLLEGE_SHORT_NAME', 'GIPS')
    COLLEGE_WEBSITE = os.environ.get('COLLEGE_WEBSITE', 'https://www.gipscollege.edu.bw')
    COLLEGE_PHONE = os.environ.get('COLLEGE_PHONE', '+267712345600')
    COLLEGE_ADDRESS = os.environ.get('COLLEGE_ADDRESS', '123 University Way, Gaborone, Botswana')
    COLLEGE_PO_BOX = os.environ.get('COLLEGE_PO_BOX', 'PO Box 12345, Gaborone, Botswana')
    COLLEGE_EMAIL = os.environ.get('COLLEGE_EMAIL', 'info@gipscollege.edu.bw')
    
    # ============================================
    # SUPPORT HOURS
    # ============================================
    SUPPORT_HOURS_START = os.environ.get('SUPPORT_HOURS_START', '08:00')
    SUPPORT_HOURS_END = os.environ.get('SUPPORT_HOURS_END', '17:00')
    SUPPORT_HOURS_WEEKDAYS = os.environ.get('SUPPORT_HOURS_WEEKDAYS', 'Monday-Friday')
    SUPPORT_TIMEZONE = os.environ.get('SUPPORT_TIMEZONE', 'Africa/Gaborone')
    EMERGENCY_SUPPORT_PHONE = os.environ.get('EMERGENCY_SUPPORT_PHONE', '+267712345699')
    
    # ============================================
    # SOCIAL MEDIA LINKS
    # ============================================
    FACEBOOK_URL = os.environ.get('FACEBOOK_URL', 'https://facebook.com/gipscollege')
    TWITTER_URL = os.environ.get('TWITTER_URL', 'https://twitter.com/gipscollege')
    INSTAGRAM_URL = os.environ.get('INSTAGRAM_URL', 'https://instagram.com/gipscollege')
    LINKEDIN_URL = os.environ.get('LINKEDIN_URL', 'https://linkedin.com/school/gipscollege')
    YOUTUBE_URL = os.environ.get('YOUTUBE_URL', 'https://youtube.com/gipscollege')
    
    # ============================================
    # SYSTEM FEATURES
    # ============================================
    # Authentication Features
    ENABLE_2FA = os.environ.get('ENABLE_2FA', 'False').lower() == 'true'
    ENABLE_SOCIAL_LOGIN = os.environ.get('ENABLE_SOCIAL_LOGIN', 'False').lower() == 'true'
    ENABLE_EMAIL_VERIFICATION = os.environ.get('ENABLE_EMAIL_VERIFICATION', 'True').lower() == 'true'
    ENABLE_PASSWORD_RESET = os.environ.get('ENABLE_PASSWORD_RESET', 'True').lower() == 'true'
    
    # API Features
    ENABLE_API_DOCS = os.environ.get('ENABLE_API_DOCS', 'True').lower() == 'true'
    ENABLE_API_RATE_LIMITING = os.environ.get('ENABLE_API_RATE_LIMITING', 'True').lower() == 'true'
    API_VERSION = os.environ.get('API_VERSION', 'v1')
    API_TITLE = os.environ.get('API_TITLE', 'GIPS College Student Management System API')
    API_DESCRIPTION = os.environ.get('API_DESCRIPTION', 'Complete API for managing student records, courses, assignments, exams, accommodation, and alumni')
    
    # Chatbot Features
    ENABLE_CHATBOT = os.environ.get('ENABLE_CHATBOT', 'True').lower() == 'true'
    ENABLE_CHATBOT_ANALYTICS = os.environ.get('ENABLE_CHATBOT_ANALYTICS', 'True').lower() == 'true'
    ENABLE_TICKET_AUTO_CLOSE = os.environ.get('ENABLE_TICKET_AUTO_CLOSE', 'True').lower() == 'true'
    ENABLE_AUTO_TICKET_ROUTING = os.environ.get('ENABLE_AUTO_TICKET_ROUTING', 'True').lower() == 'true'
    
    # Notification Features
    ENABLE_EMAIL_NOTIFICATIONS = os.environ.get('ENABLE_EMAIL_NOTIFICATIONS', 'True').lower() == 'true'
    ENABLE_SMS_NOTIFICATIONS = os.environ.get('ENABLE_SMS_NOTIFICATIONS', 'False').lower() == 'true'
    ENABLE_PUSH_NOTIFICATIONS = os.environ.get('ENABLE_PUSH_NOTIFICATIONS', 'False').lower() == 'true'
    
    # ============================================
    # SESSION AND SECURITY
    # ============================================
    SESSION_TIMEOUT_MINUTES = int(os.environ.get('SESSION_TIMEOUT_MINUTES', 30))
    REMEMBER_ME_DAYS = int(os.environ.get('REMEMBER_ME_DAYS', 30))
    PASSWORD_MIN_LENGTH = int(os.environ.get('PASSWORD_MIN_LENGTH', 8))
    PASSWORD_COMPLEXITY = os.environ.get('PASSWORD_COMPLEXITY', 'medium')
    PASSWORD_REQUIRE_UPPERCASE = os.environ.get('PASSWORD_REQUIRE_UPPERCASE', 'True').lower() == 'true'
    PASSWORD_REQUIRE_LOWERCASE = os.environ.get('PASSWORD_REQUIRE_LOWERCASE', 'True').lower() == 'true'
    PASSWORD_REQUIRE_NUMBERS = os.environ.get('PASSWORD_REQUIRE_NUMBERS', 'True').lower() == 'true'
    PASSWORD_REQUIRE_SPECIAL = os.environ.get('PASSWORD_REQUIRE_SPECIAL', 'True').lower() == 'true'
    
    # Security Headers
    SECURITY_HEADERS_ENABLED = os.environ.get('SECURITY_HEADERS_ENABLED', 'True').lower() == 'true'
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5000,http://127.0.0.1:5000')
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
    RATE_LIMIT_DEFAULT = os.environ.get('RATE_LIMIT_DEFAULT', '100 per hour')
    RATE_LIMIT_AUTH = os.environ.get('RATE_LIMIT_AUTH', '5 per minute')
    RATE_LIMIT_API = os.environ.get('RATE_LIMIT_API', '200 per hour')
    RATE_LIMIT_CHATBOT = os.environ.get('RATE_LIMIT_CHATBOT', '10 per minute')
    RATE_LIMIT_UPLOAD = os.environ.get('RATE_LIMIT_UPLOAD', '20 per hour')
    
    # ============================================
    # CACHE CONFIGURATION
    # ============================================
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))
    CACHE_KEY_PREFIX = os.environ.get('CACHE_KEY_PREFIX', 'gips_')
    
    # Redis Cache (for production)
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
    
    # ============================================
    # LOGGING CONFIGURATION
    # ============================================
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', 10485760))  # 10 MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 10))
    LOG_FORMAT = os.environ.get('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # ============================================
    # ACADEMIC CALENDAR
    # ============================================
    # Semester Dates
    SEMESTER_1_START = os.environ.get('SEMESTER_1_START', 'July')
    SEMESTER_1_END = os.environ.get('SEMESTER_1_END', 'December')
    SEMESTER_2_START = os.environ.get('SEMESTER_2_START', 'January')
    SEMESTER_2_END = os.environ.get('SEMESTER_2_END', 'June')
    MID_SEMESTER_BREAK = os.environ.get('MID_SEMESTER_BREAK', 'August')
    
    # Registration Periods
    REGISTRATION_START_DAYS = int(os.environ.get('REGISTRATION_START_DAYS', 30))
    REGISTRATION_END_DAYS = int(os.environ.get('REGISTRATION_END_DAYS', 15))
    LATE_REGISTRATION_FEE = float(os.environ.get('LATE_REGISTRATION_FEE', 500))
    
    # Exam Periods
    EXAM_WEEK_START = os.environ.get('EXAM_WEEK_START', 'Week 14')
    EXAM_WEEK_END = os.environ.get('EXAM_WEEK_END', 'Week 16')
    SUPPLEMENTARY_EXAM_FEE = float(os.environ.get('SUPPLEMENTARY_EXAM_FEE', 500))
    
    # ============================================
    # FEES AND PAYMENTS
    # ============================================
    APPLICATION_FEE = float(os.environ.get('APPLICATION_FEE', 500))
    REGISTRATION_FEE = float(os.environ.get('REGISTRATION_FEE', 2000))
    LATE_REGISTRATION_FEE = float(os.environ.get('LATE_REGISTRATION_FEE', 1000))
    EXAM_FEE_PER_MODULE = float(os.environ.get('EXAM_FEE_PER_MODULE', 500))
    ACCOMMODATION_DEPOSIT = float(os.environ.get('ACCOMMODATION_DEPOSIT', 5000))
    
    # Payment Methods
    ENABLE_STRIPE = os.environ.get('ENABLE_STRIPE', 'True').lower() == 'true'
    ENABLE_MOBILE_MONEY = os.environ.get('ENABLE_MOBILE_MONEY', 'True').lower() == 'true'
    ENABLE_BANK_TRANSFER = os.environ.get('ENABLE_BANK_TRANSFER', 'True').lower() == 'true'
    ENABLE_CASH_PAYMENT = os.environ.get('ENABLE_CASH_PAYMENT', 'True').lower() == 'true'
    
    # Mobile Money Providers
    MOBILE_MONEY_PROVIDERS = os.environ.get('MOBILE_MONEY_PROVIDERS', 'Orange Money,MyZaka,SmartMoney').split(',')
    
    # ============================================
    # BGCSE REQUIREMENTS
    # ============================================
    MIN_BGCSE_POINTS = int(os.environ.get('MIN_BGCSE_POINTS', 32))
    BGCSE_POINTS_OVC_THRESHOLD = int(os.environ.get('BGCSE_POINTS_OVC_THRESHOLD', 28))
    ENABLE_OVC_CONSIDERATION = os.environ.get('ENABLE_OVC_CONSIDERATION', 'True').lower() == 'true'
    
    # ============================================
    # RESEARCH PROJECT SETTINGS
    # ============================================
    RESEARCH_PROJECT_START = os.environ.get('RESEARCH_PROJECT_START', 'January 15')
    RESEARCH_PROJECT_END = os.environ.get('RESEARCH_PROJECT_END', 'March 31')
    INDUSTRIAL_ATTACHMENT_START = os.environ.get('INDUSTRIAL_ATTACHMENT_START', 'April 1')
    INDUSTRIAL_ATTACHMENT_END = os.environ.get('INDUSTRIAL_ATTACHMENT_END', 'June 30')
    
    # ============================================
    # FRONTEND CONFIGURATION
    # ============================================
    FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5000')
    FRONTEND_APP_NAME = os.environ.get('FRONTEND_APP_NAME', 'GIPS College Student Portal')
    FRONTEND_APP_DESCRIPTION = os.environ.get('FRONTEND_APP_DESCRIPTION', 'Student Management System for GIPS College')
    
    # ============================================
    # MAINTENANCE MODE
    # ============================================
    MAINTENANCE_MODE = os.environ.get('MAINTENANCE_MODE', 'False').lower() == 'true'
    MAINTENANCE_MESSAGE = os.environ.get('MAINTENANCE_MESSAGE', 'System is under maintenance. Please check back later.')
    
    # ============================================
    # DEBUGGING
    # ============================================
    DEBUG_TOOLBAR_ENABLED = os.environ.get('DEBUG_TOOLBAR_ENABLED', 'False').lower() == 'true'
    PROFILING_ENABLED = os.environ.get('PROFILING_ENABLED', 'False').lower() == 'true'
    
    # ============================================
    # BACKUP SETTINGS
    # ============================================
    ENABLE_AUTO_BACKUP = os.environ.get('ENABLE_AUTO_BACKUP', 'True').lower() == 'true'
    BACKUP_INTERVAL_DAYS = int(os.environ.get('BACKUP_INTERVAL_DAYS', 7))
    BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', 30))
    BACKUP_PATH = os.environ.get('BACKUP_PATH', 'backups/')
    
    # ============================================
    # GDPR & COMPLIANCE
    # ============================================
    GDPR_COMPLIANT = os.environ.get('GDPR_COMPLIANT', 'True').lower() == 'true'
    DATA_RETENTION_DAYS = int(os.environ.get('DATA_RETENTION_DAYS', 365))
    COOKIE_CONSENT_ENABLED = os.environ.get('COOKIE_CONSENT_ENABLED', 'True').lower() == 'true'
    PRIVACY_POLICY_URL = os.environ.get('PRIVACY_POLICY_URL', '/privacy')
    TERMS_OF_SERVICE_URL = os.environ.get('TERMS_OF_SERVICE_URL', '/terms')
    
    # ============================================
    # ADMIN CONFIGURATION
    # ============================================
    ADMIN_EMAILS = os.environ.get('ADMIN_EMAILS', 'admin@gipscollege.edu.bw,director@gipscollege.edu.bw,registrar@gipscollege.edu.bw,itadmin@gipscollege.edu.bw,financeadmin@gipscollege.edu.bw').split(',')
    SUPER_ADMIN_EMAIL = os.environ.get('SUPER_ADMIN_EMAIL', 'admin@gipscollege.edu.bw')
    
    # ============================================
    # FLASK ENVIRONMENT
    # ============================================
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.environ.get('FLASK_PORT', 5000))


# ============================================
# DEVELOPMENT CONFIGURATION
# ============================================
class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True  # Log SQL queries
    CHATBOT_ENABLE_EMAIL = False  # Disable email in development
    LOG_LEVEL = 'DEBUG'
    
    # CORS for development - allow all origins
    CORS_ORIGINS = '*'
    
    # Debug toolbar
    DEBUG_TOOLBAR_ENABLED = os.environ.get('DEBUG_TOOLBAR_ENABLED', 'True').lower() == 'true'
    PROFILING_ENABLED = os.environ.get('PROFILING_ENABLED', 'False').lower() == 'true'
    
    # Development specific settings
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False


# ============================================
# TESTING CONFIGURATION
# ============================================
class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # Use in-memory SQLite for testing
    SQLALCHEMY_ECHO = False
    CHATBOT_ENABLE_EMAIL = False
    ENABLE_EMAIL_VERIFICATION = False
    WTF_CSRF_ENABLED = False
    RATE_LIMIT_ENABLED = False  # Disable rate limiting for tests
    
    # Testing specific settings
    SECRET_KEY = 'test-secret-key'
    JWT_SECRET_KEY = 'test-jwt-secret-key'


# ============================================
# PRODUCTION CONFIGURATION
# ============================================
class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SQLALCHEMY_ECHO = False
    CHATBOT_ENABLE_EMAIL = True  # Enable email in production
    ENABLE_EMAIL_VERIFICATION = True
    
    # Production security settings
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # CORS for production - restrict to your domain
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'https://gipscollege.edu.bw,https://www.gipscollege.edu.bw')
    
    # Production cache
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'redis')
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Logging in production
    LOG_LEVEL = 'WARNING'
    SQLALCHEMY_ECHO = False
    
    # Rate limiting in production
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_DEFAULT = '50 per hour'
    RATE_LIMIT_AUTH = '3 per minute'
    RATE_LIMIT_API = '100 per hour'
    RATE_LIMIT_CHATBOT = '5 per minute'
    RATE_LIMIT_UPLOAD = '10 per hour'


# ============================================
# STAGING CONFIGURATION
# ============================================
class StagingConfig(ProductionConfig):
    """Staging configuration"""
    DEBUG = True
    TESTING = False
    CHATBOT_ENABLE_EMAIL = False
    SQLALCHEMY_ECHO = True
    LOG_LEVEL = 'DEBUG'
    
    # Staging specific settings
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False


# ============================================
# CONFIGURATION DICTIONARY
# ============================================
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'staging': StagingConfig,
    'default': DevelopmentConfig
}


# ============================================
# HELPER FUNCTION
# ============================================
def get_config(env=None):
    """Get configuration based on environment"""
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])


# ============================================
# INITIALIZATION HELPER
# ============================================
def init_app_config(app):
    """Initialize app configuration from environment and create necessary directories"""
    env = os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[env])
    
    # Create necessary directories
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    if upload_folder:
        os.makedirs(upload_folder, exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('database', exist_ok=True)
    
    # Create upload subdirectories
    for subdir in ['documents', 'assignments', 'research', 'attachments', 'profiles']:
        path = os.path.join(upload_folder, subdir) if upload_folder else subdir
        os.makedirs(path, exist_ok=True)
    
    return app