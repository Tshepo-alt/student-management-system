# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

# ==================== USER AUTHENTICATION MODELS ====================

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin', 'administrator', 'staff', 'student', 'lecturer', 'finance', 'registrar', 'alumni'), default='student')
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255))
    reset_token = db.Column(db.String(255))
    reset_token_expiry = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)
    login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    student = db.relationship('Student', backref='user', uselist=False, cascade='all, delete-orphan')
    user_roles = db.relationship('UserRole', back_populates='user', foreign_keys='UserRole.user_id', cascade='all, delete-orphan')
    tokens = db.relationship('JWTToken', backref='user', cascade='all, delete-orphan')
    approved_registrations = db.relationship('Registration', foreign_keys='Registration.approved_by', backref='approver')
    processed_payments = db.relationship('Payment', foreign_keys='Payment.processed_by', backref='processor')
    uploaded_materials = db.relationship('CourseMaterial', foreign_keys='CourseMaterial.uploaded_by', backref='uploader')
    notifications = db.relationship('Notification', foreign_keys='Notification.user_id', backref='user')
    audit_logs = db.relationship('AuditLog', foreign_keys='AuditLog.user_id', backref='user')
    supervised_projects = db.relationship('ResearchProject', foreign_keys='ResearchProject.supervisor_id', backref='supervisor')
    verified_documents = db.relationship('StudentDocument', foreign_keys='StudentDocument.verified_by', backref='verifier')
    created_events = db.relationship('AlumniEvent', foreign_keys='AlumniEvent.created_by', backref='creator')
    job_applications = db.relationship('JobApplication', foreign_keys='JobApplication.applicant_id', backref='applicant')
    reviewed_applications = db.relationship('JobApplication', foreign_keys='JobApplication.reviewed_by', backref='reviewer')
    event_registrations = db.relationship('EventRegistration', foreign_keys='EventRegistration.user_id', backref='user')
    system_config_updates = db.relationship('SystemConfig', foreign_keys='SystemConfig.updated_by', backref='updater')
    blocklist_entries = db.relationship('TokenBlocklist', foreign_keys='TokenBlocklist.user_id', backref='user')
    taught_courses = db.relationship('Course', foreign_keys='Course.lecturer_id', backref='lecturer')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_roles(self):
        return [ur.role.role_name for ur in self.user_roles]
    
    def has_role(self, role_name):
        return role_name in self.get_roles()
    
    def is_admin(self):
        return self.role in ['admin', 'administrator'] or self.has_role('admin')
    
    def __repr__(self):
        return f'<User {self.username}>'


class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    permissions = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user_roles = db.relationship('UserRole', back_populates='role', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Role {self.role_name}>'


class UserRole(db.Model):
    __tablename__ = 'user_roles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', back_populates='user_roles', foreign_keys=[user_id])
    role = db.relationship('Role', back_populates='user_roles', foreign_keys=[role_id])
    assigner = db.relationship('User', foreign_keys=[assigned_by])
    
    __table_args__ = (db.UniqueConstraint('user_id', 'role_id', name='unique_user_role'),)


class JWTToken(db.Model):
    __tablename__ = 'jwt_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(500), unique=True, nullable=False)
    refresh_token = db.Column(db.String(500), unique=True)
    token_type = db.Column(db.Enum('access', 'refresh'), default='access')
    expires_at = db.Column(db.DateTime, nullable=False)
    is_revoked = db.Column(db.Boolean, default=False)
    device_info = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at


# ==================== CAMPUS MODELS ====================

class Campus(db.Model):
    __tablename__ = 'campuses'
    
    id = db.Column(db.Integer, primary_key=True)
    campus_code = db.Column(db.String(20), unique=True, nullable=False)
    campus_name = db.Column(db.String(100), nullable=False)
    campus_location = db.Column(db.String(255))
    campus_address = db.Column(db.Text)
    has_accommodation = db.Column(db.Boolean, default=False)
    is_main_campus = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    programs = db.relationship('Program', backref='campus', lazy=True)
    students = db.relationship('Student', backref='campus', lazy=True)
    
    def __repr__(self):
        return f'<Campus {self.campus_name}>'


# ==================== ACADEMIC STRUCTURE MODELS ====================

class Faculty(db.Model):
    __tablename__ = 'faculties'
    
    id = db.Column(db.Integer, primary_key=True)
    faculty_code = db.Column(db.String(20), unique=True, nullable=False)
    faculty_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    dean_name = db.Column(db.String(100))
    dean_email = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    departments = db.relationship('Department', backref='faculty', cascade='all, delete-orphan')
    programs = db.relationship('Program', backref='faculty', cascade='all, delete-orphan')


class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculties.id'))
    department_code = db.Column(db.String(20), unique=True, nullable=False)
    department_name = db.Column(db.String(100), nullable=False)
    hod_name = db.Column(db.String(100))
    hod_email = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    programs = db.relationship('Program', backref='department', cascade='all, delete-orphan')


class ProgramType(db.Model):
    __tablename__ = 'program_types'
    
    id = db.Column(db.Integer, primary_key=True)
    type_code = db.Column(db.String(10), unique=True, nullable=False)
    type_name = db.Column(db.String(50), nullable=False)
    duration_years = db.Column(db.Integer)
    description = db.Column(db.Text)
    
    programs = db.relationship('Program', backref='program_type', cascade='all, delete-orphan')


class Program(db.Model):
    __tablename__ = 'programs'
    
    id = db.Column(db.Integer, primary_key=True)
    program_code = db.Column(db.String(20), unique=True, nullable=False)
    program_name = db.Column(db.String(255), nullable=False)
    program_type_id = db.Column(db.Integer, db.ForeignKey('program_types.id'))
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculties.id'))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    campus_id = db.Column(db.Integer, db.ForeignKey('campuses.id'))
    duration_years = db.Column(db.Integer, nullable=False)
    total_credits = db.Column(db.Integer)
    min_bgcse_points = db.Column(db.Integer, default=32)
    description = db.Column(db.Text)
    career_opportunities = db.Column(db.Text)
    entry_requirements = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    students = db.relationship('Student', backref='program', cascade='all, delete-orphan')
    program_modules = db.relationship('ProgramModule', backref='program', cascade='all, delete-orphan')
    alumni = db.relationship('Alumni', backref='program', cascade='all, delete-orphan')
    courses = db.relationship('Course', backref='program', cascade='all, delete-orphan')
    yearly_fees = db.relationship('YearlyFees', backref='program', cascade='all, delete-orphan')


class YearlyFees(db.Model):
    __tablename__ = 'yearly_fees'
    
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'), nullable=False)
    year_number = db.Column(db.Integer, nullable=False)
    registration_fee = db.Column(db.Numeric(10,2), nullable=False)
    id_card_fee = db.Column(db.Numeric(10,2), nullable=False)
    e_library_fee = db.Column(db.Numeric(10,2), nullable=False)
    exam_fee = db.Column(db.Numeric(10,2), nullable=False)
    tuition_fee = db.Column(db.Numeric(10,2), nullable=False)
    total_fee = db.Column(db.Numeric(10,2))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('program_id', 'year_number', name='unique_program_year'),)


class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    course_name = db.Column(db.String(255), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'))
    lecturer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    semester = db.Column(db.Integer)
    year_level = db.Column(db.Integer)
    description = db.Column(db.Text)
    meeting_link = db.Column(db.String(500))
    meeting_platform = db.Column(db.Enum('google_meet', 'zoom', 'none'), default='none')
    meeting_id = db.Column(db.String(100))
    meeting_password = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    student_courses = db.relationship('StudentCourse', backref='course', cascade='all, delete-orphan')
    online_meetings = db.relationship('OnlineMeeting', backref='course', cascade='all, delete-orphan')
    exam_registrations = db.relationship('ExamRegistration', backref='course', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Course {self.course_code}>'


class Module(db.Model):
    __tablename__ = 'modules'
    
    id = db.Column(db.Integer, primary_key=True)
    module_code = db.Column(db.String(20), unique=True, nullable=False)
    module_name = db.Column(db.String(255), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    year_level = db.Column(db.Integer, nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    module_type = db.Column(db.Enum('core', 'elective', 'specialization'), default='core')
    has_practicals = db.Column(db.Boolean, default=False)
    nqf_level = db.Column(db.Integer)
    description = db.Column(db.Text)
    prerequisites = db.Column(db.Text)
    recommended_reading = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    # === MOODLE INTEGRATION FIELD ===
    moodle_course_id = db.Column(db.Integer, nullable=True, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    program_modules = db.relationship('ProgramModule', backref='module', cascade='all, delete-orphan')
    enrollments = db.relationship('Enrollment', backref='module', cascade='all, delete-orphan')
    course_materials = db.relationship('CourseMaterial', backref='module', cascade='all, delete-orphan')
    assignments = db.relationship('Assignment', backref='module', cascade='all, delete-orphan')


class ProgramModule(db.Model):
    __tablename__ = 'program_modules'
    
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=False)
    is_compulsory = db.Column(db.Boolean, default=True)
    elective_group = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('program_id', 'module_id', name='unique_program_module'),)


# ==================== ONLINE CLASSES MODELS ====================

class OnlineMeeting(db.Model):
    __tablename__ = 'online_meetings'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    meeting_link = db.Column(db.String(500), nullable=False)
    meeting_platform = db.Column(db.Enum('google_meet', 'zoom'), nullable=False)
    meeting_id = db.Column(db.String(100))
    meeting_password = db.Column(db.String(50))
    scheduled_start = db.Column(db.DateTime)
    scheduled_end = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer, default=60)
    is_active = db.Column(db.Boolean, default=True)
    recorded = db.Column(db.Boolean, default=False)
    recording_url = db.Column(db.String(500))
    attendees_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    
    attendees = db.relationship('MeetingAttendee', backref='meeting', cascade='all, delete-orphan')


class MeetingAttendee(db.Model):
    __tablename__ = 'meeting_attendees'
    
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey('online_meetings.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    joined_at = db.Column(db.DateTime)
    left_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('meeting_id', 'student_id', name='unique_meeting_student'),)


# ==================== STUDENT MODELS ====================

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    student_number = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    initials = db.Column(db.String(10))
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20))
    alternative_phone = db.Column(db.String(20))
    physical_address = db.Column(db.Text)
    postal_address = db.Column(db.Text)
    date_of_birth = db.Column(db.Date)
    place_of_birth = db.Column(db.String(100))
    nationality = db.Column(db.String(100))
    id_number = db.Column(db.String(50))
    passport_number = db.Column(db.String(50))
    passport_expiry = db.Column(db.Date)
    tr_number = db.Column(db.String(50))
    is_government_sponsored = db.Column(db.Boolean, default=False)
    dtef_sponsor_number = db.Column(db.String(100))
    sponsorship_letter_path = db.Column(db.String(500))
    campus_id = db.Column(db.Integer, db.ForeignKey('campuses.id'))
    wants_accommodation = db.Column(db.Boolean, default=False)
    bgcse_points = db.Column(db.Integer)
    bgcse_year = db.Column(db.Integer)
    bgcse_school = db.Column(db.String(255))
    previous_qualifications = db.Column(db.JSON)
    is_ovc = db.Column(db.Boolean, default=False)
    social_worker_name = db.Column(db.String(200))
    social_worker_contact = db.Column(db.String(100))
    social_worker_letter_path = db.Column(db.String(500))
    emergency_contact_name = db.Column(db.String(200))
    emergency_contact_phone = db.Column(db.String(20))
    emergency_contact_relationship = db.Column(db.String(100))
    emergency_contact_address = db.Column(db.Text)
    next_of_kin_name = db.Column(db.String(200))
    next_of_kin_relationship = db.Column(db.String(100))
    next_of_kin_phone = db.Column(db.String(20))
    next_of_kin_address = db.Column(db.Text)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'))
    current_year = db.Column(db.Integer, default=1)
    enrollment_date = db.Column(db.Date)
    expected_graduation = db.Column(db.Date)
    admission_status = db.Column(db.Enum('pending', 'accepted', 'rejected', 'deferred', 'graduated'), default='pending')
    academic_status = db.Column(db.Enum('good_standing', 'probation', 'suspended', 'graduated'), default='good_standing')
    current_gpa = db.Column(db.Numeric(3,2))
    total_credits_earned = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # === REGISTRATION DOCUMENTS FIELDS ===
    bgcse_certificate_path = db.Column(db.String(500))
    id_document_path = db.Column(db.String(500))
    passport_photo_path = db.Column(db.String(500))
    
    # === MOODLE INTEGRATION FIELD ===
    moodle_user_id = db.Column(db.Integer, nullable=True, unique=True, index=True)
    
    # Relationships
    documents = db.relationship('StudentDocument', backref='student', cascade='all, delete-orphan')
    registrations = db.relationship('Registration', backref='student', cascade='all, delete-orphan')
    enrollments = db.relationship('Enrollment', backref='student', cascade='all, delete-orphan')
    payments = db.relationship('Payment', foreign_keys='Payment.student_id', backref='student', cascade='all, delete-orphan')
    academic_records = db.relationship('AcademicRecord', backref='student', cascade='all, delete-orphan')
    research_projects = db.relationship('ResearchProject', backref='student', cascade='all, delete-orphan')
    attachments = db.relationship('Attachment', backref='student', cascade='all, delete-orphan')
    agreements = db.relationship('StudentAgreement', backref='student', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', foreign_keys='Notification.student_id', backref='student')
    assignment_submissions = db.relationship('AssignmentSubmission', backref='student', cascade='all, delete-orphan')
    exam_registrations = db.relationship('ExamRegistration', backref='student', cascade='all, delete-orphan')
    accommodation_applications = db.relationship('AccommodationRegistration', backref='student', cascade='all, delete-orphan')
    alumni_profile = db.relationship('Alumni', backref='student', uselist=False, cascade='all, delete-orphan')
    student_courses = db.relationship('StudentCourse', backref='student', cascade='all, delete-orphan')
    meeting_attendances = db.relationship('MeetingAttendee', backref='student', cascade='all, delete-orphan')
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f'<Student {self.student_number}>'


class StudentCourse(db.Model):
    __tablename__ = 'student_courses'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    enrollment_date = db.Column(db.Date)
    status = db.Column(db.Enum('registered', 'dropped', 'completed', 'failed'), default='registered')
    grade = db.Column(db.String(5))
    grade_points = db.Column(db.Numeric(3,2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', name='unique_student_course'),)


class StudentDocument(db.Model):
    __tablename__ = 'student_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    document_type = db.Column(db.Enum('bgcse_transcript', 'other_certificate', 'supporting_letter', 'id_document', 'passport_photo', 'passport_copy', 'omang_copy', 'sponsorship_letter', 'dtef_letter'), nullable=False)
    document_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified = db.Column(db.Boolean, default=False)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    verified_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)


# ==================== ACCOMMODATION MODELS ====================

class Accommodation(db.Model):
    __tablename__ = 'accommodations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True)
    location = db.Column(db.String(255))
    price_per_semester = db.Column(db.Numeric(10, 2), default=0)
    total_rooms = db.Column(db.Integer, default=0)
    available_rooms = db.Column(db.Integer, default=0)
    amenities = db.Column(db.JSON)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AccommodationRoom(db.Model):
    __tablename__ = 'accommodation_rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    block_name = db.Column(db.String(20), nullable=False)
    room_number = db.Column(db.String(10), nullable=False)
    room_type = db.Column(db.Enum('bachelor_pad', 'three_bed'), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    current_occupants = db.Column(db.Integer, default=0)
    has_kitchen = db.Column(db.Boolean, default=True)
    has_shower = db.Column(db.Boolean, default=True)
    has_study_table = db.Column(db.Boolean, default=True)
    has_bed = db.Column(db.Boolean, default=True)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    registrations = db.relationship('AccommodationRegistration', backref='allocated_room', foreign_keys='AccommodationRegistration.allocated_room_id')
    
    __table_args__ = (db.UniqueConstraint('block_name', 'room_number', name='unique_block_room'),)


class AccommodationRule(db.Model):
    __tablename__ = 'accommodation_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    rule_title = db.Column(db.String(200), nullable=False)
    rule_description = db.Column(db.Text, nullable=False)
    is_mandatory = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AccommodationRegistration(db.Model):
    __tablename__ = 'accommodation_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'))
    wants_accommodation = db.Column(db.Boolean, default=False)
    block_preference = db.Column(db.String(50))
    room_type = db.Column(db.Enum('bachelor_pad', 'three_bed'), default='bachelor_pad')
    has_accepted_rules = db.Column(db.Boolean, default=False)
    emergency_contact_name = db.Column(db.String(200))
    emergency_contact_phone = db.Column(db.String(20))
    emergency_contact_relationship = db.Column(db.String(100))
    medical_conditions = db.Column(db.Text)
    dietary_requirements = db.Column(db.Text)
    status = db.Column(db.Enum('pending', 'approved', 'rejected', 'waitlisted', 'allocated'), default='pending')
    allocated_room_id = db.Column(db.Integer, db.ForeignKey('accommodation_rooms.id'))
    allocated_room_number = db.Column(db.String(20))
    allocated_block = db.Column(db.String(20))
    agreement_signed = db.Column(db.Boolean, default=False)
    check_in_date = db.Column(db.Date)
    check_out_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('student_id', 'registration_id', name='unique_student_accommodation'),)


# ==================== ACADEMIC YEAR & REGISTRATION ====================

class AcademicYear(db.Model):
    __tablename__ = 'academic_years'
    
    id = db.Column(db.Integer, primary_key=True)
    year_name = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    registration_start = db.Column(db.Date)
    registration_end = db.Column(db.Date)
    is_current = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    semesters = db.relationship('Semester', backref='academic_year', cascade='all, delete-orphan')
    registrations = db.relationship('Registration', backref='academic_year', cascade='all, delete-orphan')


class Semester(db.Model):
    __tablename__ = 'semesters'
    
    id = db.Column(db.Integer, primary_key=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'))
    semester_number = db.Column(db.Integer, nullable=False)
    semester_name = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    mid_semester_break_start = db.Column(db.Date)
    mid_semester_break_end = db.Column(db.Date)
    exam_start = db.Column(db.Date)
    exam_end = db.Column(db.Date)
    registration_start = db.Column(db.Date)
    registration_end = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    registrations = db.relationship('Registration', backref='semester', cascade='all, delete-orphan')
    exam_registrations = db.relationship('ExamRegistration', backref='semester', cascade='all, delete-orphan')


class Registration(db.Model):
    __tablename__ = 'registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id'), nullable=False)
    year_of_study = db.Column(db.Integer, nullable=False)
    registration_date = db.Column(db.Date)
    sponsorship_type = db.Column(db.Enum('government_sponsored', 'government_reinstatement', 'government_retake', 'private'), nullable=False)
    sponsorship_letter_path = db.Column(db.String(500))
    ovc_supporting_letter_path = db.Column(db.String(500))
    registration_status = db.Column(db.Enum('pending', 'approved', 'rejected', 'completed'), default='pending')
    payment_status = db.Column(db.Enum('exempted', 'pending', 'partial', 'completed'), default='pending')
    total_fees = db.Column(db.Numeric(10,2))
    paid_amount = db.Column(db.Numeric(10,2), default=0)
    exempted_amount = db.Column(db.Numeric(10,2), default=0)
    supplementary_exam_fees = db.Column(db.Numeric(10,2), default=0)
    resit_fees = db.Column(db.Numeric(10,2), default=0)
    retake_fees = db.Column(db.Numeric(10,2), default=0)
    bgcse_points_verified = db.Column(db.Boolean, default=False)
    documents_verified = db.Column(db.Boolean, default=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    enrollments = db.relationship('Enrollment', backref='registration', cascade='all, delete-orphan')
    payments = db.relationship('Payment', foreign_keys='Payment.registration_id', backref='registration', cascade='all, delete-orphan')
    academic_records = db.relationship('AcademicRecord', backref='registration', cascade='all, delete-orphan')
    research_projects = db.relationship('ResearchProject', backref='registration', cascade='all, delete-orphan')
    attachments = db.relationship('Attachment', backref='registration', cascade='all, delete-orphan')
    agreements = db.relationship('StudentAgreement', backref='registration', cascade='all, delete-orphan')
    accommodation_applications = db.relationship('AccommodationRegistration', backref='registration', cascade='all, delete-orphan')
    
    @property
    def balance(self):
        return (self.total_fees or 0) - (self.paid_amount or 0) - (self.exempted_amount or 0)


class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=False)
    enrollment_date = db.Column(db.Date)
    status = db.Column(db.Enum('registered', 'dropped', 'completed', 'failed'), default='registered')
    grade = db.Column(db.String(5))
    grade_points = db.Column(db.Numeric(3,2))
    is_supplementary = db.Column(db.Boolean, default=False)
    is_resit = db.Column(db.Boolean, default=False)
    is_retake = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('registration_id', 'module_id', name='unique_enrollment'),)


# ==================== ASSIGNMENT MODELS ====================

class Assignment(db.Model):
    __tablename__ = 'assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime, nullable=False)
    max_points = db.Column(db.Integer, default=100)
    submission_type = db.Column(db.Enum('file', 'text'), default='file')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    submissions = db.relationship('AssignmentSubmission', backref='assignment', cascade='all, delete-orphan')


class AssignmentSubmission(db.Model):
    __tablename__ = 'assignment_submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    file_path = db.Column(db.String(500))
    submission_text = db.Column(db.Text)
    comments = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    score = db.Column(db.Integer)
    grade = db.Column(db.String(5))
    feedback = db.Column(db.Text)
    status = db.Column(db.Enum('submitted', 'graded', 'late', 'resubmitted'), default='submitted')
    graded_at = db.Column(db.DateTime)
    graded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('assignment_id', 'student_id', name='unique_assignment_submission'),)


# ==================== EXAM MODELS ====================

class ExamRegistration(db.Model):
    __tablename__ = 'exam_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    exam_type = db.Column(db.Enum('regular', 'supplementary', 'resit', 'retake'), default='regular')
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id'))
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'))
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    exam_date = db.Column(db.DateTime)
    venue = db.Column(db.String(200))
    seat_number = db.Column(db.String(50))
    fee = db.Column(db.Numeric(10,2), default=0)
    fee_type = db.Column(db.Enum('regular', 'supplementary', 'resit', 'retake'), default='regular')
    is_government_sponsored = db.Column(db.Boolean, default=False)
    payment_status = db.Column(db.Enum('exempted', 'pending', 'paid', 'waived'), default='pending')
    payment_reference = db.Column(db.String(100))
    result = db.Column(db.String(5))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', 'exam_type', name='unique_exam_registration'),)


# ==================== FEES CONFIGURATION ====================

class FeesConfig(db.Model):
    __tablename__ = 'fees_config'
    
    id = db.Column(db.Integer, primary_key=True)
    fee_type = db.Column(db.String(50), unique=True, nullable=False)
    fee_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10,2), nullable=False)
    is_government_exempt = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== PAYMENT MODELS ====================

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'), nullable=False)
    amount = db.Column(db.Numeric(10,2), nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.Enum('cash', 'bank_transfer', 'card', 'mobile_money'), nullable=False)
    transaction_id = db.Column(db.String(100))
    receipt_number = db.Column(db.String(100), unique=True)
    status = db.Column(db.Enum('pending', 'completed', 'failed', 'refunded'), default='completed')
    payment_type = db.Column(db.Enum('registration', 'tuition', 'supplementary', 'resit', 'retake', 'accommodation'), nullable=False)
    is_government_payment = db.Column(db.Boolean, default=False)
    payment_reference = db.Column(db.String(100))
    stripe_payment_intent_id = db.Column(db.String(255))
    notes = db.Column(db.Text)
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ==================== ACADEMIC RECORDS ====================

class AcademicRecord(db.Model):
    __tablename__ = 'academic_records'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'), nullable=False)
    semester_gpa = db.Column(db.Numeric(3,2))
    cumulative_gpa = db.Column(db.Numeric(3,2))
    total_credits_earned = db.Column(db.Integer)
    academic_status = db.Column(db.Enum('good_standing', 'probation', 'suspended', 'graduated'), default='good_standing')
    dean_list = db.Column(db.Boolean, default=False)
    class_standing = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('student_id', 'registration_id', name='unique_student_semester'),)


# ==================== RESEARCH & ATTACHMENT ====================

class ResearchProject(db.Model):
    __tablename__ = 'research_projects'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'), nullable=False)
    project_title = db.Column(db.String(500))
    project_description = db.Column(db.Text)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    supervisor_name = db.Column(db.String(200))
    supervisor_email = db.Column(db.String(255))
    supervisor_phone = db.Column(db.String(20))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.Enum('pending', 'in_progress', 'submitted', 'approved', 'rejected', 'resubmit'), default='pending')
    report_file_path = db.Column(db.String(500))
    presentation_date = db.Column(db.Date)
    grade = db.Column(db.String(5))
    feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Attachment(db.Model):
    __tablename__ = 'attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'), nullable=False)
    company_name = db.Column(db.String(255))
    company_address = db.Column(db.Text)
    company_contact_person = db.Column(db.String(200))
    company_phone = db.Column(db.String(20))
    company_email = db.Column(db.String(255))
    supervisor_name = db.Column(db.String(200))
    supervisor_phone = db.Column(db.String(20))
    supervisor_email = db.Column(db.String(255))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.Enum('pending', 'in_progress', 'completed', 'failed', 'extended'), default='pending')
    report_file_path = db.Column(db.String(500))
    evaluation_score = db.Column(db.Integer)
    certificate_path = db.Column(db.String(500))
    supervisor_feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== ALUMNI MODELS ====================

class Alumni(db.Model):
    __tablename__ = 'alumni'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), unique=True)
    student_number = db.Column(db.String(20), unique=True, nullable=False)
    graduation_year = db.Column(db.Integer)
    graduation_date = db.Column(db.Date)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'))
    job_title = db.Column(db.String(150))
    company = db.Column(db.String(150))
    employment_status = db.Column(db.Enum('employed', 'self_employed', 'freelance', 'studying', 'unemployed'), default='employed')
    linkedin_url = db.Column(db.String(255))
    bio = db.Column(db.Text)
    skills = db.Column(db.JSON)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    jobs_posted = db.relationship('JobListing', backref='alumni', cascade='all, delete-orphan')


class JobListing(db.Model):
    __tablename__ = 'job_listings'
    
    id = db.Column(db.Integer, primary_key=True)
    alumni_id = db.Column(db.Integer, db.ForeignKey('alumni.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(200))
    type = db.Column(db.Enum('full-time', 'part-time', 'contract', 'internship', 'remote'), default='full-time')
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text)
    how_to_apply = db.Column(db.Text)
    application_link = db.Column(db.String(500))
    salary_range = db.Column(db.String(100))
    deadline = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    applications = db.relationship('JobApplication', backref='job_listing', cascade='all, delete-orphan')


class JobApplication(db.Model):
    __tablename__ = 'job_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_listings.id'), nullable=False)
    applicant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    cover_letter = db.Column(db.Text)
    resume_path = db.Column(db.String(500))
    portfolio_url = db.Column(db.String(500))
    status = db.Column(db.Enum('pending', 'reviewed', 'shortlisted', 'interviewed', 'accepted', 'rejected'), default='pending')
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('job_id', 'applicant_id', name='unique_job_application'),)


# ==================== SUPPORT MODELS ====================

class StudentAgreement(db.Model):
    __tablename__ = 'student_agreements'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'), nullable=False)
    agreed_to_rules = db.Column(db.Boolean, default=False)
    agreement_date = db.Column(db.Date)
    signature = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CourseMaterial(db.Model):
    __tablename__ = 'course_materials'
    
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'))
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(500))
    material_type = db.Column(db.Enum('lecture_notes', 'assignment', 'reading', 'research_guide', 'presentation', 'lab_manual'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.Enum('info', 'warning', 'success', 'error'), default='info')
    is_read = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def mark_as_read(self):
        self.is_read = True


# ==================== STAFF QUERIES MODEL ====================

class StaffQuery(db.Model):
    __tablename__ = 'staff_queries'
    
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    staff_name = db.Column(db.String(200), nullable=False)
    staff_email = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(100))
    subject = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    priority = db.Column(db.Enum('high', 'medium', 'low'), default='medium')
    status = db.Column(db.Enum('pending', 'resolved'), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    responses = db.Column(db.JSON, default=list)
    
    staff = db.relationship('User', backref='staff_queries')
    
    def to_dict(self):
        return {
            'id': self.id,
            'staff_id': self.staff_id,
            'staff_name': self.staff_name,
            'staff_email': self.staff_email,
            'department': self.department,
            'subject': self.subject,
            'message': self.message,
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'responses': self.responses or []
        }


# ==================== STUDENT QUERIES MODEL (NEW) ====================
class StudentQuery(db.Model):
    __tablename__ = 'student_queries'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), default='General')
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum('pending', 'in-progress', 'resolved'), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    responses = db.Column(db.JSON, default=list)
    
    student = db.relationship('Student', backref='queries')
    
    def to_dict(self):
        return {
            'id': self.id,
            'subject': self.subject,
            'category': self.category,
            'message': self.message,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'responses': self.responses or []
        }


# ==================== AUDIT LOG MODEL ====================

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    table_name = db.Column(db.String(100))
    record_id = db.Column(db.Integer)
    old_values = db.Column(db.JSON)
    new_values = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ==================== TOKEN BLOCKLIST MODEL ====================

class TokenBlocklist(db.Model):
    __tablename__ = 'token_blocklist'
    
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True)
    token_type = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)


# ==================== EVENT MODELS ====================

class AlumniEvent(db.Model):
    __tablename__ = 'alumni_events'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    event_date = db.Column(db.Date, nullable=False)
    event_time = db.Column(db.Time)
    location = db.Column(db.String(255))
    venue = db.Column(db.String(200))
    capacity = db.Column(db.Integer)
    price = db.Column(db.Numeric(10,2), default=0)
    image_url = db.Column(db.String(500))
    is_virtual = db.Column(db.Boolean, default=False)
    meeting_link = db.Column(db.String(500))
    status = db.Column(db.Enum('upcoming', 'ongoing', 'completed', 'cancelled'), default='upcoming')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    registrations = db.relationship('EventRegistration', backref='event', cascade='all, delete-orphan')


class EventRegistration(db.Model):
    __tablename__ = 'event_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('alumni_events.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    attendance_status = db.Column(db.Enum('registered', 'attended', 'cancelled'), default='registered')
    payment_status = db.Column(db.Enum('pending', 'paid', 'free'), default='free')
    payment_reference = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('event_id', 'user_id', name='unique_event_registration'),)


# ==================== SYSTEM CONFIGURATION ====================

class SystemConfig(db.Model):
    __tablename__ = 'system_config'
    
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(100), unique=True, nullable=False)
    config_value = db.Column(db.Text)
    config_type = db.Column(db.Enum('string', 'integer', 'boolean', 'json', 'float'), default='string')
    description = db.Column(db.Text)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_value(self):
        if self.config_type == 'integer':
            return int(self.config_value)
        elif self.config_type == 'boolean':
            return self.config_value.lower() in ['true', '1', 'yes']
        elif self.config_type == 'json':
            return json.loads(self.config_value)
        elif self.config_type == 'float':
            return float(self.config_value)
        return self.config_value
    
    def set_value(self, value):
        if self.config_type == 'json':
            self.config_value = json.dumps(value)
        else:
            self.config_value = str(value)