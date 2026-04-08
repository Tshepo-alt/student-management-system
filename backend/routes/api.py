# backend/routes/api.py
from flask import Blueprint, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid
import json
import traceback
import csv
import io
from functools import wraps
from sqlalchemy import func, text, and_, or_

api_bp = Blueprint('api', __name__)

# ==================== Helper Functions ====================

def admin_required():
    """Decorator to check if user is admin - FIXED VERSION"""
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorated_view(*args, **kwargs):
            try:
                current_user_id = get_jwt_identity()
                from models import User
                
                user_id = int(current_user_id) if current_user_id else None
                user = User.query.get(user_id) if user_id else None
                
                print(f"[DEBUG] Admin check - User ID: {current_user_id}")
                print(f"[DEBUG] User email: {user.email if user else 'None'}")
                print(f"[DEBUG] User role: {user.role if user else 'None'}")
                
                if not user:
                    print("[DEBUG] User not found")
                    return jsonify({'error': 'User not found'}), 404
                
                admin_roles = ['admin', 'administrator', 'Admin', 'Administrator', 'ADMIN']
                is_admin = user.role in admin_roles
                
                if hasattr(user, 'is_admin') and not is_admin:
                    is_admin = user.is_admin()
                
                print(f"[DEBUG] Is admin: {is_admin}")
                
                if not is_admin:
                    print(f"[DEBUG] Access denied - role: {user.role}")
                    return jsonify({'error': 'Admin access required'}), 403
                
                print("[DEBUG] Admin access granted")
                return fn(*args, **kwargs)
            except Exception as e:
                print(f"Admin required error: {e}")
                traceback.print_exc()
                return jsonify({'error': str(e)}), 500
        return decorated_view
    return wrapper

def save_uploaded_file(file, folder='uploads'):
    """Save uploaded file and return path"""
    if not file or not file.filename:
        return None

    try:
        filename = secure_filename(file.filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{filename}"

        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        upload_path = os.path.join(upload_folder, folder)
        os.makedirs(upload_path, exist_ok=True)

        filepath = os.path.join(upload_path, unique_filename)
        file.save(filepath)

        return f"/uploads/{folder}/{unique_filename}"
    except Exception as e:
        print(f"Error saving file: {e}")
        return None

def calculate_fees(student, exam_type, module_count=1):
    """Calculate fees based on sponsorship and exam type"""
    from models import FeesConfig  # Added missing import
    
    fees = {
        'regular': 0,
        'supplementary': 300,
        'resit': 600,
        'retake': 1000
    }
    
    # Government sponsored students are exempt from regular exam fees
    if student.is_government_sponsored and exam_type == 'regular':
        return 0
    
    return fees.get(exam_type, 500) * module_count

# ==================== Authentication Endpoints ====================

@api_bp.route('/auth/register', methods=['POST'])
def register():
    """Student registration with campus selection and sponsorship"""
    try:
        from models import User, Student, Program, StudentDocument, Campus, db
        from werkzeug.security import generate_password_hash

        if request.is_json:
            data = request.get_json()
            files = {}
        else:
            data = request.form.to_dict()
            files = request.files

        required_fields = ['first_name', 'last_name', 'email', 'username', 'password', 'program_id', 'campus_id']
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 400

        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already taken'}), 400

        try:
            program_id = int(data['program_id'])
            program = Program.query.get(program_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid program ID'}), 400

        if not program:
            return jsonify({'error': 'Invalid program'}), 400

        try:
            campus_id = int(data['campus_id'])
            campus = Campus.query.get(campus_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid campus ID'}), 400

        if not campus:
            return jsonify({'error': 'Invalid campus'}), 400

        # Check if program is offered at selected campus
        if program.campus_id != campus_id:
            return jsonify({'error': 'Program not offered at selected campus'}), 400

        try:
            bgcse_points = int(data.get('bgcse_points', 0))
        except ValueError:
            bgcse_points = 0

        is_ovc = data.get('is_ovc', 'false').lower() in ['true', '1', 'yes']
        is_government_sponsored = data.get('is_government_sponsored', 'false').lower() in ['true', '1', 'yes']
        wants_accommodation = data.get('wants_accommodation', 'false').lower() in ['true', '1', 'yes']

        if bgcse_points < (program.min_bgcse_points if hasattr(program, 'min_bgcse_points') else 32) and not is_ovc:
            return jsonify({'error': f'Minimum {program.min_bgcse_points if hasattr(program, "min_bgcse_points") else 32} points required or OVC status'}), 400

        user = User(
            username=data['username'],
            email=data['email'],
            password_hash=generate_password_hash(data['password']),
            role='student',
            is_active=True,
            is_verified=False
        )

        year = datetime.now().year
        student_count = Student.query.count() + 1
        student_number = f"GIPS/{year}/{student_count:05d}"

        date_of_birth = None
        if data.get('date_of_birth'):
            try:
                date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            except:
                pass

        passport_expiry = None
        if data.get('passport_expiry'):
            try:
                passport_expiry = datetime.strptime(data['passport_expiry'], '%Y-%m-%d').date()
            except:
                pass

        sponsorship_type = data.get('sponsorship_type', 'private')
        
        student = Student(
            user=user,
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
            passport_expiry=passport_expiry,
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
            admission_status='pending' if is_ovc else 'accepted'
        )

        db.session.add(user)
        db.session.add(student)
        db.session.flush()

        # Handle file uploads
        if files:
            for doc_type, file in files.items():
                if file and file.filename:
                    filepath = save_uploaded_file(file, 'documents')
                    if filepath:
                        doc = StudentDocument(
                            student_id=student.id,
                            document_type=doc_type,
                            document_name=file.filename,
                            file_path=filepath
                        )
                        db.session.add(doc)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'student_number': student_number,
            'admission_status': student.admission_status,
            'needs_review': is_ovc
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Registration error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/auth/login', methods=['POST'])
def login():
    """User login - Returns JWT tokens"""
    try:
        from models import User, Student, db

        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request body'}), 400

        email = data.get('email')
        username = data.get('username')
        password = data.get('password')

        if not password:
            return jsonify({'error': 'Password required'}), 400

        if email:
            user = User.query.filter_by(email=email).first()
        elif username:
            user = User.query.filter_by(username=username).first()
        else:
            return jsonify({'error': 'Email or username required'}), 400

        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401

        if not user.is_active:
            return jsonify({'error': 'Account is disabled'}), 401

        user.last_login = datetime.utcnow()
        db.session.commit()

        student = Student.query.filter_by(user_id=user.id).first()

        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={'role': user.role}
        )
        refresh_token = create_refresh_token(identity=str(user.id))

        return jsonify({
            'success': True,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': student.first_name if student else user.username,
                'last_name': student.last_name if student else '',
                'role': user.role,
                'student_number': student.student_number if student else None,
                'is_government_sponsored': student.is_government_sponsored if student else False,
                'campus_id': student.campus_id if student else None
            }
        }), 200

    except Exception as e:
        print(f"Login error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    try:
        from models import User
        current_user_id = get_jwt_identity()
        
        user_id = int(current_user_id) if current_user_id else None
        user = User.query.get(user_id) if user_id else None
        
        if not user:
            return jsonify({'error': 'User not found'}), 401
            
        access_token = create_access_token(
            identity=str(current_user_id),
            additional_claims={'role': user.role}
        )
        return jsonify({'access_token': access_token}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/auth/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify JWT token"""
    try:
        current_user_id = get_jwt_identity()
        from models import User
        
        user_id = int(current_user_id) if current_user_id else None
        user = User.query.get(user_id) if user_id else None
        
        if not user:
            return jsonify({'valid': False, 'error': 'User not found'}), 401
        return jsonify({'valid': True, 'user_id': current_user_id, 'role': user.role}), 200
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)}), 401


@api_bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout (client should discard token)"""
    return jsonify({'message': 'Logged out successfully'}), 200


# ==================== Campus Endpoints ====================

@api_bp.route('/campuses', methods=['GET'])
def get_campuses():
    """Get all campuses"""
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
        print(f"Error getting campuses: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/campuses/<int:campus_id>/programs', methods=['GET'])
def get_campus_programs(campus_id):
    """Get programs by campus"""
    try:
        from models import Program, ProgramType
        
        programs = Program.query.filter_by(campus_id=campus_id, is_active=True).all()
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
        print(f"Error getting campus programs: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== Accommodation Endpoints ====================

@api_bp.route('/accommodation/rooms', methods=['GET'])
@jwt_required()
def get_accommodation_rooms():
    """Get available accommodation rooms"""
    try:
        from models import AccommodationRoom
        
        rooms = AccommodationRoom.query.filter_by(is_available=True).all()
        result = []
        for room in rooms:
            result.append({
                'id': room.id,
                'block_name': room.block_name,
                'room_number': room.room_number,
                'room_type': room.room_type,
                'capacity': room.capacity,
                'current_occupants': room.current_occupants,
                'has_kitchen': room.has_kitchen,
                'has_shower': room.has_shower,
                'has_study_table': room.has_study_table,
                'has_bed': room.has_bed
            })
        return jsonify(result), 200
    except Exception as e:
        print(f"Error getting rooms: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/accommodation/rules', methods=['GET'])
def get_accommodation_rules():
    """Get accommodation rules"""
    try:
        from models import AccommodationRule
        
        rules = AccommodationRule.query.order_by(AccommodationRule.display_order).all()
        result = []
        for rule in rules:
            result.append({
                'id': rule.id,
                'rule_title': rule.rule_title,
                'rule_description': rule.rule_description,
                'is_mandatory': rule.is_mandatory
            })
        return jsonify(result), 200
    except Exception as e:
        print(f"Error getting rules: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/accommodation/apply', methods=['POST'])
@jwt_required()
def apply_accommodation():
    """Apply for accommodation"""
    try:
        from models import Student, AccommodationRegistration, Registration, db
        from models import AccommodationRoom

        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()

        if not student:
            return jsonify({'error': 'Student not found'}), 404

        if not student.wants_accommodation:
            return jsonify({'error': 'You did not opt for accommodation'}), 400

        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415

        data = request.get_json()
        
        # Get current registration
        registration = Registration.query.filter_by(
            student_id=student.id,
            registration_status='approved'
        ).first()

        if not registration:
            return jsonify({'error': 'No active registration found'}), 404

        # Check if already applied
        existing = AccommodationRegistration.query.filter_by(
            student_id=student.id,
            registration_id=registration.id
        ).first()

        if existing:
            return jsonify({'error': 'You already have an accommodation application'}), 400

        # Check if user accepted rules
        if not data.get('has_accepted_rules'):
            return jsonify({'error': 'You must accept the accommodation rules'}), 400

        application = AccommodationRegistration(
            student_id=student.id,
            registration_id=registration.id,
            wants_accommodation=True,
            block_preference=data.get('block_preference'),
            room_type=data.get('room_type', 'bachelor_pad'),
            has_accepted_rules=data.get('has_accepted_rules'),
            emergency_contact_name=data.get('emergency_contact_name'),
            emergency_contact_phone=data.get('emergency_contact_phone'),
            emergency_contact_relationship=data.get('emergency_contact_relationship'),
            medical_conditions=data.get('medical_conditions'),
            dietary_requirements=data.get('dietary_requirements'),
            status='pending'
        )

        db.session.add(application)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Accommodation application submitted successfully',
            'application_id': application.id
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Accommodation apply error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/accommodation/status', methods=['GET'])
@jwt_required()
def get_accommodation_status():
    """Get student's accommodation application status"""
    try:
        from models import Student, AccommodationRegistration

        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()

        if not student:
            return jsonify({'error': 'Student not found'}), 404

        application = AccommodationRegistration.query.filter_by(
            student_id=student.id
        ).order_by(AccommodationRegistration.created_at.desc()).first()

        if not application:
            return jsonify({'status': 'not_applied'}), 200

        return jsonify({
            'id': application.id,
            'status': application.status,
            'block_preference': application.block_preference,
            'room_type': application.room_type,
            'allocated_room_number': application.allocated_room_number,
            'allocated_block': application.allocated_block,
            'created_at': application.created_at.isoformat(),
            'updated_at': application.updated_at.isoformat()
        }), 200

    except Exception as e:
        print(f"Error getting accommodation status: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== Exam Registration with Fees ====================

@api_bp.route('/exams/register', methods=['POST'])
@jwt_required()
def register_exams():
    """Register for exams with proper fee calculation"""
    try:
        from models import Student, ExamRegistration, Module, db, FeesConfig

        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()

        if not student:
            return jsonify({'error': 'Student not found'}), 404

        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request body'}), 400

        module_ids = data.get('module_ids', [])
        exam_type = data.get('exam_type', 'regular')

        if not module_ids:
            return jsonify({'error': 'No modules selected'}), 400

        # Calculate fee based on sponsorship and exam type
        fee_per_module = calculate_fees(student, exam_type)
        
        if fee_per_module == 0 and exam_type != 'regular':
            # Government sponsored students still pay for supplementary/resit/retake
            fee_per_module = 500

        total_fee = len(module_ids) * fee_per_module
        registrations = []

        for module_id in module_ids:
            module = Module.query.get(module_id)
            if not module:
                continue

            existing = ExamRegistration.query.filter_by(
                student_id=student.id,
                module_id=module_id,
                exam_type=exam_type,
                status='registered'
            ).first()

            if existing:
                continue

            payment_status = 'exempted' if (student.is_government_sponsored and exam_type == 'regular') else 'pending'

            registration = ExamRegistration(
                student_id=student.id,
                module_id=module_id,
                exam_type=exam_type,
                fee=fee_per_module,
                fee_type=exam_type,
                is_government_sponsored=student.is_government_sponsored,
                payment_status=payment_status,
                status='registered'
            )
            registrations.append(registration)

        if not registrations:
            return jsonify({'error': 'No valid modules to register'}), 400

        db.session.add_all(registrations)
        db.session.commit()

        reference_number = f"EXAM-{datetime.now().strftime('%Y%m%d%H%M%S')}-{student.id}"

        return jsonify({
            'success': True,
            'reference_number': reference_number,
            'total_amount': total_fee,
            'modules_registered': len(registrations),
            'fee_per_module': fee_per_module,
            'exam_type': exam_type,
            'payment_status': 'exempted' if total_fee == 0 else 'pending'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Exam registration error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ==================== Admin CSV Export Endpoints ====================

@api_bp.route('/admin/export/government-sponsored', methods=['GET'])
@admin_required()
def export_government_sponsored():
    """Export government sponsored students data to CSV"""
    try:
        from models import Student, Program, AcademicRecord, Campus
        
        students = Student.query.filter_by(
            is_government_sponsored=True,
            is_active=True
        ).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Student Number', 'First Name', 'Last Name', 'Email', 'Phone',
            'Program', 'Campus', 'Current Year', 'Current GPA', 'Previous Semester GPA',
            'Enrollment Date', 'Academic Status'
        ])
        
        for student in students:
            # Get previous semester GPA
            previous_record = AcademicRecord.query.filter_by(
                student_id=student.id
            ).order_by(AcademicRecord.created_at.desc()).first()
            
            writer.writerow([
                student.student_number,
                student.first_name,
                student.last_name,
                student.email,
                student.phone or '',
                student.program.program_name if student.program else '',
                student.campus.campus_name if student.campus else '',
                student.current_year,
                float(student.current_gpa) if student.current_gpa else 0,
                float(previous_record.semester_gpa) if previous_record and previous_record.semester_gpa else 0,
                student.enrollment_date.isoformat() if student.enrollment_date else '',
                student.academic_status
            ])
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'government_sponsored_students_{datetime.now().strftime("%Y%m%d")}.csv'
        )
        
    except Exception as e:
        print(f"Export error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/export/self-sponsored', methods=['GET'])
@admin_required()
def export_self_sponsored():
    """Export self sponsored students data to CSV"""
    try:
        from models import Student, Program, AcademicRecord, Campus, Registration
        
        students = Student.query.filter_by(
            is_government_sponsored=False,
            is_active=True
        ).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'Student Number', 'First Name', 'Last Name', 'Email', 'Phone',
            'Program', 'Campus', 'Current Year', 'Current GPA', 'Previous Semester GPA',
            'Enrollment Date', 'Academic Status', 'Outstanding Balance'
        ])
        
        for student in students:
            # Get outstanding balance from registrations
            registrations = Registration.query.filter_by(student_id=student.id).all()
            outstanding = sum((reg.total_fees or 0) - (reg.paid_amount or 0) for reg in registrations)
            
            previous_record = AcademicRecord.query.filter_by(
                student_id=student.id
            ).order_by(AcademicRecord.created_at.desc()).first()
            
            writer.writerow([
                student.student_number,
                student.first_name,
                student.last_name,
                student.email,
                student.phone or '',
                student.program.program_name if student.program else '',
                student.campus.campus_name if student.campus else '',
                student.current_year,
                float(student.current_gpa) if student.current_gpa else 0,
                float(previous_record.semester_gpa) if previous_record and previous_record.semester_gpa else 0,
                student.enrollment_date.isoformat() if student.enrollment_date else '',
                student.academic_status,
                f"P{outstanding:,.2f}"
            ])
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'self_sponsored_students_{datetime.now().strftime("%Y%m%d")}.csv'
        )
        
    except Exception as e:
        print(f"Export error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ==================== Student Dashboard with Fees ====================

@api_bp.route('/students/dashboard', methods=['GET'])
@jwt_required()
def get_student_dashboard():
    """Get student dashboard data with fees based on sponsorship"""
    try:
        from models import User, Student, Registration, Payment, ExamRegistration, FeesConfig

        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        if user.role != 'student':
            return jsonify({'error': 'Student access required'}), 403

        student = Student.query.filter_by(user_id=user.id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404

        # Get current registration
        registration = Registration.query.filter_by(
            student_id=student.id,
            registration_status='approved'
        ).first()

        # Calculate fees
        total_fees = 0
        paid_amount = 0
        outstanding = 0
        
        if registration:
            total_fees = registration.total_fees or 0
            paid_amount = registration.paid_amount or 0
            outstanding = total_fees - paid_amount
            
            # For government sponsored students, only show supplementary/resit/retake fees
            if student.is_government_sponsored:
                outstanding = registration.supplementary_exam_fees + registration.resit_fees + registration.retake_fees

        # Get exam fees
        exam_fees = ExamRegistration.query.filter_by(
            student_id=student.id,
            payment_status='pending'
        ).all()
        exam_fees_total = sum(e.fee or 0 for e in exam_fees)

        return jsonify({
            'user': {
                'id': user.id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'email': user.email
            },
            'student_number': student.student_number,
            'program_name': student.program.program_name if student.program else None,
            'academic_status': student.academic_status,
            'sponsorship_type': 'Government Sponsored' if student.is_government_sponsored else 'Self Sponsored',
            'is_ovc': student.is_ovc,
            'current_gpa': float(student.current_gpa) if student.current_gpa else 0.0,
            'credits_earned': student.total_credits_earned,
            'current_year': student.current_year,
            'campus': student.campus.campus_name if student.campus else None,
            'wants_accommodation': student.wants_accommodation,
            'total_fees': total_fees,
            'paid_amount': paid_amount,
            'outstanding_balance': outstanding,
            'exam_fees_due': exam_fees_total,
            'pending_payments': 0,
            'registered_exams': len(exam_fees),
            'accommodation_status': 'Applied' if student.wants_accommodation else 'Not Applied',
            'room_number': None,
            'recent_activity': []
        }), 200

    except Exception as e:
        print(f"Dashboard error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/students/results', methods=['GET'])
@jwt_required()
def get_student_results():
    """Get student results - only their own"""
    try:
        from models import User, Student, Enrollment, Module, AcademicRecord

        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        student = Student.query.filter_by(user_id=user.id).first()
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        # Get enrollments with grades
        enrollments = Enrollment.query.filter_by(
            student_id=student.id,
            status='completed'
        ).order_by(Enrollment.created_at.desc()).all()

        results = []
        for enrollment in enrollments:
            module = Module.query.get(enrollment.module_id)
            results.append({
                'module_code': module.module_code if module else 'N/A',
                'module_name': module.module_name if module else 'N/A',
                'credits': module.credits if module else 0,
                'grade': enrollment.grade,
                'grade_points': float(enrollment.grade_points) if enrollment.grade_points else 0,
                'semester': module.semester if module else None,
                'year_level': module.year_level if module else None
            })

        # Get academic records
        academic_records = AcademicRecord.query.filter_by(
            student_id=student.id
        ).order_by(AcademicRecord.created_at.desc()).all()

        records = []
        for record in academic_records:
            records.append({
                'semester_gpa': float(record.semester_gpa) if record.semester_gpa else 0,
                'cumulative_gpa': float(record.cumulative_gpa) if record.cumulative_gpa else 0,
                'academic_status': record.academic_status,
                'created_at': record.created_at.isoformat()
            })

        return jsonify({
            'student_number': student.student_number,
            'student_name': student.full_name,
            'program': student.program.program_name if student.program else None,
            'current_gpa': float(student.current_gpa) if student.current_gpa else 0,
            'academic_status': student.academic_status,
            'results': results,
            'academic_records': records
        }), 200

    except Exception as e:
        print(f"Results error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ==================== Admin Student Result View ====================

@api_bp.route('/admin/students/<int:student_id>/results', methods=['GET'])
@admin_required()
def admin_get_student_results(student_id):
    """Get student results for admin/staff to view"""
    try:
        from models import Student, Enrollment, Module, AcademicRecord

        student = Student.query.get(student_id)
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        enrollments = Enrollment.query.filter_by(
            student_id=student.id,
            status='completed'
        ).order_by(Enrollment.created_at.desc()).all()

        results = []
        for enrollment in enrollments:
            module = Module.query.get(enrollment.module_id)
            results.append({
                'module_code': module.module_code if module else 'N/A',
                'module_name': module.module_name if module else 'N/A',
                'credits': module.credits if module else 0,
                'grade': enrollment.grade,
                'grade_points': float(enrollment.grade_points) if enrollment.grade_points else 0,
                'semester': module.semester if module else None,
                'year_level': module.year_level if module else None
            })

        academic_records = AcademicRecord.query.filter_by(
            student_id=student.id
        ).order_by(AcademicRecord.created_at.desc()).all()

        records = []
        for record in academic_records:
            records.append({
                'semester_gpa': float(record.semester_gpa) if record.semester_gpa else 0,
                'cumulative_gpa': float(record.cumulative_gpa) if record.cumulative_gpa else 0,
                'academic_status': record.academic_status,
                'created_at': record.created_at.isoformat()
            })

        return jsonify({
            'student': {
                'id': student.id,
                'student_number': student.student_number,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'program': student.program.program_name if student.program else None,
                'current_year': student.current_year,
                'current_gpa': float(student.current_gpa) if student.current_gpa else 0,
                'academic_status': student.academic_status,
                'is_government_sponsored': student.is_government_sponsored
            },
            'results': results,
            'academic_records': records
        }), 200

    except Exception as e:
        print(f"Admin results error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ==================== Health Check Endpoint ====================

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        from models import db
        db_status = 'connected'
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
        except Exception as e:
            db_status = f'disconnected: {str(e)}'
            
        return jsonify({
            'status': 'healthy' if db_status == 'connected' else 'degraded',
            'database': db_status,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500# backend/routes/api.py
from flask import Blueprint, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid
import json
import traceback
import csv
import io
from functools import wraps
from sqlalchemy import func, text, and_, or_

api_bp = Blueprint('api', __name__)

# ==================== Helper Functions ====================

def admin_required():
    """Decorator to check if user is admin - FIXED VERSION"""
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorated_view(*args, **kwargs):
            try:
                current_user_id = get_jwt_identity()
                from models import User
                
                user_id = int(current_user_id) if current_user_id else None
                user = User.query.get(user_id) if user_id else None
                
                print(f"[DEBUG] Admin check - User ID: {current_user_id}")
                print(f"[DEBUG] User email: {user.email if user else 'None'}")
                print(f"[DEBUG] User role: {user.role if user else 'None'}")
                
                if not user:
                    print("[DEBUG] User not found")
                    return jsonify({'error': 'User not found'}), 404
                
                admin_roles = ['admin', 'administrator', 'Admin', 'Administrator', 'ADMIN']
                is_admin = user.role in admin_roles
                
                if hasattr(user, 'is_admin') and not is_admin:
                    is_admin = user.is_admin()
                
                print(f"[DEBUG] Is admin: {is_admin}")
                
                if not is_admin:
                    print(f"[DEBUG] Access denied - role: {user.role}")
                    return jsonify({'error': 'Admin access required'}), 403
                
                print("[DEBUG] Admin access granted")
                return fn(*args, **kwargs)
            except Exception as e:
                print(f"Admin required error: {e}")
                traceback.print_exc()
                return jsonify({'error': str(e)}), 500
        return decorated_view
    return wrapper

def save_uploaded_file(file, folder='uploads'):
    """Save uploaded file and return path"""
    if not file or not file.filename:
        return None

    try:
        filename = secure_filename(file.filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{filename}"

        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        upload_path = os.path.join(upload_folder, folder)
        os.makedirs(upload_path, exist_ok=True)

        filepath = os.path.join(upload_path, unique_filename)
        file.save(filepath)

        return f"/uploads/{folder}/{unique_filename}"
    except Exception as e:
        print(f"Error saving file: {e}")
        return None

def calculate_fees(student, exam_type, module_count=1):
    """Calculate fees based on sponsorship and exam type"""
    from models import FeesConfig  # Added missing import
    
    fees = {
        'regular': 0,
        'supplementary': 300,
        'resit': 600,
        'retake': 1000
    }
    
    # Government sponsored students are exempt from regular exam fees
    if student.is_government_sponsored and exam_type == 'regular':
        return 0
    
    return fees.get(exam_type, 500) * module_count

# ==================== Authentication Endpoints ====================

@api_bp.route('/auth/register', methods=['POST'])
def register():
    """Student registration with campus selection and sponsorship"""
    try:
        from models import User, Student, Program, StudentDocument, Campus, db
        from werkzeug.security import generate_password_hash

        if request.is_json:
            data = request.get_json()
            files = {}
        else:
            data = request.form.to_dict()
            files = request.files

        required_fields = ['first_name', 'last_name', 'email', 'username', 'password', 'program_id', 'campus_id']
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 400

        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already taken'}), 400

        try:
            program_id = int(data['program_id'])
            program = Program.query.get(program_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid program ID'}), 400

        if not program:
            return jsonify({'error': 'Invalid program'}), 400

        try:
            campus_id = int(data['campus_id'])
            campus = Campus.query.get(campus_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid campus ID'}), 400

        if not campus:
            return jsonify({'error': 'Invalid campus'}), 400

        # Check if program is offered at selected campus
        if program.campus_id != campus_id:
            return jsonify({'error': 'Program not offered at selected campus'}), 400

        try:
            bgcse_points = int(data.get('bgcse_points', 0))
        except ValueError:
            bgcse_points = 0

        is_ovc = data.get('is_ovc', 'false').lower() in ['true', '1', 'yes']
        is_government_sponsored = data.get('is_government_sponsored', 'false').lower() in ['true', '1', 'yes']
        wants_accommodation = data.get('wants_accommodation', 'false').lower() in ['true', '1', 'yes']

        if bgcse_points < (program.min_bgcse_points if hasattr(program, 'min_bgcse_points') else 32) and not is_ovc:
            return jsonify({'error': f'Minimum {program.min_bgcse_points if hasattr(program, "min_bgcse_points") else 32} points required or OVC status'}), 400

        user = User(
            username=data['username'],
            email=data['email'],
            password_hash=generate_password_hash(data['password']),
            role='student',
            is_active=True,
            is_verified=False
        )

        year = datetime.now().year
        student_count = Student.query.count() + 1
        student_number = f"GIPS/{year}/{student_count:05d}"

        date_of_birth = None
        if data.get('date_of_birth'):
            try:
                date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            except:
                pass

        passport_expiry = None
        if data.get('passport_expiry'):
            try:
                passport_expiry = datetime.strptime(data['passport_expiry'], '%Y-%m-%d').date()
            except:
                pass

        sponsorship_type = data.get('sponsorship_type', 'private')
        
        student = Student(
            user=user,
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
            passport_expiry=passport_expiry,
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
            admission_status='pending' if is_ovc else 'accepted'
        )

        db.session.add(user)
        db.session.add(student)
        db.session.flush()

        # Handle file uploads
        if files:
            for doc_type, file in files.items():
                if file and file.filename:
                    filepath = save_uploaded_file(file, 'documents')
                    if filepath:
                        doc = StudentDocument(
                            student_id=student.id,
                            document_type=doc_type,
                            document_name=file.filename,
                            file_path=filepath
                        )
                        db.session.add(doc)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'student_number': student_number,
            'admission_status': student.admission_status,
            'needs_review': is_ovc
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Registration error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/auth/login', methods=['POST'])
def login():
    """User login - Returns JWT tokens"""
    try:
        from models import User, Student, db

        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request body'}), 400

        email = data.get('email')
        username = data.get('username')
        password = data.get('password')

        if not password:
            return jsonify({'error': 'Password required'}), 400

        if email:
            user = User.query.filter_by(email=email).first()
        elif username:
            user = User.query.filter_by(username=username).first()
        else:
            return jsonify({'error': 'Email or username required'}), 400

        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401

        if not user.is_active:
            return jsonify({'error': 'Account is disabled'}), 401

        user.last_login = datetime.utcnow()
        db.session.commit()

        student = Student.query.filter_by(user_id=user.id).first()

        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={'role': user.role}
        )
        refresh_token = create_refresh_token(identity=str(user.id))

        return jsonify({
            'success': True,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': student.first_name if student else user.username,
                'last_name': student.last_name if student else '',
                'role': user.role,
                'student_number': student.student_number if student else None,
                'is_government_sponsored': student.is_government_sponsored if student else False,
                'campus_id': student.campus_id if student else None
            }
        }), 200

    except Exception as e:
        print(f"Login error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    try:
        from models import User
        current_user_id = get_jwt_identity()
        
        user_id = int(current_user_id) if current_user_id else None
        user = User.query.get(user_id) if user_id else None
        
        if not user:
            return jsonify({'error': 'User not found'}), 401
            
        access_token = create_access_token(
            identity=str(current_user_id),
            additional_claims={'role': user.role}
        )
        return jsonify({'access_token': access_token}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/auth/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """Verify JWT token"""
    try:
        current_user_id = get_jwt_identity()
        from models import User
        
        user_id = int(current_user_id) if current_user_id else None
        user = User.query.get(user_id) if user_id else None
        
        if not user:
            return jsonify({'valid': False, 'error': 'User not found'}), 401
        return jsonify({'valid': True, 'user_id': current_user_id, 'role': user.role}), 200
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)}), 401


@api_bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout (client should discard token)"""
    return jsonify({'message': 'Logged out successfully'}), 200


# ==================== Campus Endpoints ====================

@api_bp.route('/campuses', methods=['GET'])
def get_campuses():
    """Get all campuses"""
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
        print(f"Error getting campuses: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/campuses/<int:campus_id>/programs', methods=['GET'])
def get_campus_programs(campus_id):
    """Get programs by campus"""
    try:
        from models import Program, ProgramType
        
        programs = Program.query.filter_by(campus_id=campus_id, is_active=True).all()
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
        print(f"Error getting campus programs: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== Accommodation Endpoints ====================

@api_bp.route('/accommodation/rooms', methods=['GET'])
@jwt_required()
def get_accommodation_rooms():
    """Get available accommodation rooms"""
    try:
        from models import AccommodationRoom
        
        rooms = AccommodationRoom.query.filter_by(is_available=True).all()
        result = []
        for room in rooms:
            result.append({
                'id': room.id,
                'block_name': room.block_name,
                'room_number': room.room_number,
                'room_type': room.room_type,
                'capacity': room.capacity,
                'current_occupants': room.current_occupants,
                'has_kitchen': room.has_kitchen,
                'has_shower': room.has_shower,
                'has_study_table': room.has_study_table,
                'has_bed': room.has_bed
            })
        return jsonify(result), 200
    except Exception as e:
        print(f"Error getting rooms: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/accommodation/rules', methods=['GET'])
def get_accommodation_rules():
    """Get accommodation rules"""
    try:
        from models import AccommodationRule
        
        rules = AccommodationRule.query.order_by(AccommodationRule.display_order).all()
        result = []
        for rule in rules:
            result.append({
                'id': rule.id,
                'rule_title': rule.rule_title,
                'rule_description': rule.rule_description,
                'is_mandatory': rule.is_mandatory
            })
        return jsonify(result), 200
    except Exception as e:
        print(f"Error getting rules: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/accommodation/apply', methods=['POST'])
@jwt_required()
def apply_accommodation():
    """Apply for accommodation"""
    try:
        from models import Student, AccommodationRegistration, Registration, db
        from models import AccommodationRoom

        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()

        if not student:
            return jsonify({'error': 'Student not found'}), 404

        if not student.wants_accommodation:
            return jsonify({'error': 'You did not opt for accommodation'}), 400

        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415

        data = request.get_json()
        
        # Get current registration
        registration = Registration.query.filter_by(
            student_id=student.id,
            registration_status='approved'
        ).first()

        if not registration:
            return jsonify({'error': 'No active registration found'}), 404

        # Check if already applied
        existing = AccommodationRegistration.query.filter_by(
            student_id=student.id,
            registration_id=registration.id
        ).first()

        if existing:
            return jsonify({'error': 'You already have an accommodation application'}), 400

        # Check if user accepted rules
        if not data.get('has_accepted_rules'):
            return jsonify({'error': 'You must accept the accommodation rules'}), 400

        application = AccommodationRegistration(
            student_id=student.id,
            registration_id=registration.id,
            wants_accommodation=True,
            block_preference=data.get('block_preference'),
            room_type=data.get('room_type', 'bachelor_pad'),
            has_accepted_rules=data.get('has_accepted_rules'),
            emergency_contact_name=data.get('emergency_contact_name'),
            emergency_contact_phone=data.get('emergency_contact_phone'),
            emergency_contact_relationship=data.get('emergency_contact_relationship'),
            medical_conditions=data.get('medical_conditions'),
            dietary_requirements=data.get('dietary_requirements'),
            status='pending'
        )

        db.session.add(application)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Accommodation application submitted successfully',
            'application_id': application.id
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Accommodation apply error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/accommodation/status', methods=['GET'])
@jwt_required()
def get_accommodation_status():
    """Get student's accommodation application status"""
    try:
        from models import Student, AccommodationRegistration

        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()

        if not student:
            return jsonify({'error': 'Student not found'}), 404

        application = AccommodationRegistration.query.filter_by(
            student_id=student.id
        ).order_by(AccommodationRegistration.created_at.desc()).first()

        if not application:
            return jsonify({'status': 'not_applied'}), 200

        return jsonify({
            'id': application.id,
            'status': application.status,
            'block_preference': application.block_preference,
            'room_type': application.room_type,
            'allocated_room_number': application.allocated_room_number,
            'allocated_block': application.allocated_block,
            'created_at': application.created_at.isoformat(),
            'updated_at': application.updated_at.isoformat()
        }), 200

    except Exception as e:
        print(f"Error getting accommodation status: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== Exam Registration with Fees ====================

@api_bp.route('/exams/register', methods=['POST'])
@jwt_required()
def register_exams():
    """Register for exams with proper fee calculation"""
    try:
        from models import Student, ExamRegistration, Module, db, FeesConfig

        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()

        if not student:
            return jsonify({'error': 'Student not found'}), 404

        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request body'}), 400

        module_ids = data.get('module_ids', [])
        exam_type = data.get('exam_type', 'regular')

        if not module_ids:
            return jsonify({'error': 'No modules selected'}), 400

        # Calculate fee based on sponsorship and exam type
        fee_per_module = calculate_fees(student, exam_type)
        
        if fee_per_module == 0 and exam_type != 'regular':
            # Government sponsored students still pay for supplementary/resit/retake
            fee_per_module = 500

        total_fee = len(module_ids) * fee_per_module
        registrations = []

        for module_id in module_ids:
            module = Module.query.get(module_id)
            if not module:
                continue

            existing = ExamRegistration.query.filter_by(
                student_id=student.id,
                module_id=module_id,
                exam_type=exam_type,
                status='registered'
            ).first()

            if existing:
                continue

            payment_status = 'exempted' if (student.is_government_sponsored and exam_type == 'regular') else 'pending'

            registration = ExamRegistration(
                student_id=student.id,
                module_id=module_id,
                exam_type=exam_type,
                fee=fee_per_module,
                fee_type=exam_type,
                is_government_sponsored=student.is_government_sponsored,
                payment_status=payment_status,
                status='registered'
            )
            registrations.append(registration)

        if not registrations:
            return jsonify({'error': 'No valid modules to register'}), 400

        db.session.add_all(registrations)
        db.session.commit()

        reference_number = f"EXAM-{datetime.now().strftime('%Y%m%d%H%M%S')}-{student.id}"

        return jsonify({
            'success': True,
            'reference_number': reference_number,
            'total_amount': total_fee,
            'modules_registered': len(registrations),
            'fee_per_module': fee_per_module,
            'exam_type': exam_type,
            'payment_status': 'exempted' if total_fee == 0 else 'pending'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Exam registration error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ==================== Admin CSV Export Endpoints ====================

@api_bp.route('/admin/export/government-sponsored', methods=['GET'])
@admin_required()
def export_government_sponsored():
    """Export government sponsored students data to CSV"""
    try:
        from models import Student, Program, AcademicRecord, Campus
        
        students = Student.query.filter_by(
            is_government_sponsored=True,
            is_active=True
        ).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'Student Number', 'First Name', 'Last Name', 'Email', 'Phone',
            'Program', 'Campus', 'Current Year', 'Current GPA', 'Previous Semester GPA',
            'Enrollment Date', 'Academic Status'
        ])
        
        for student in students:
            # Get previous semester GPA
            previous_record = AcademicRecord.query.filter_by(
                student_id=student.id
            ).order_by(AcademicRecord.created_at.desc()).first()
            
            writer.writerow([
                student.student_number,
                student.first_name,
                student.last_name,
                student.email,
                student.phone or '',
                student.program.program_name if student.program else '',
                student.campus.campus_name if student.campus else '',
                student.current_year,
                float(student.current_gpa) if student.current_gpa else 0,
                float(previous_record.semester_gpa) if previous_record and previous_record.semester_gpa else 0,
                student.enrollment_date.isoformat() if student.enrollment_date else '',
                student.academic_status
            ])
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'government_sponsored_students_{datetime.now().strftime("%Y%m%d")}.csv'
        )
        
    except Exception as e:
        print(f"Export error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/export/self-sponsored', methods=['GET'])
@admin_required()
def export_self_sponsored():
    """Export self sponsored students data to CSV"""
    try:
        from models import Student, Program, AcademicRecord, Campus, Registration
        
        students = Student.query.filter_by(
            is_government_sponsored=False,
            is_active=True
        ).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'Student Number', 'First Name', 'Last Name', 'Email', 'Phone',
            'Program', 'Campus', 'Current Year', 'Current GPA', 'Previous Semester GPA',
            'Enrollment Date', 'Academic Status', 'Outstanding Balance'
        ])
        
        for student in students:
            # Get outstanding balance from registrations
            registrations = Registration.query.filter_by(student_id=student.id).all()
            outstanding = sum((reg.total_fees or 0) - (reg.paid_amount or 0) for reg in registrations)
            
            previous_record = AcademicRecord.query.filter_by(
                student_id=student.id
            ).order_by(AcademicRecord.created_at.desc()).first()
            
            writer.writerow([
                student.student_number,
                student.first_name,
                student.last_name,
                student.email,
                student.phone or '',
                student.program.program_name if student.program else '',
                student.campus.campus_name if student.campus else '',
                student.current_year,
                float(student.current_gpa) if student.current_gpa else 0,
                float(previous_record.semester_gpa) if previous_record and previous_record.semester_gpa else 0,
                student.enrollment_date.isoformat() if student.enrollment_date else '',
                student.academic_status,
                f"P{outstanding:,.2f}"
            ])
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'self_sponsored_students_{datetime.now().strftime("%Y%m%d")}.csv'
        )
        
    except Exception as e:
        print(f"Export error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ==================== Student Dashboard with Fees ====================

@api_bp.route('/students/dashboard', methods=['GET'])
@jwt_required()
def get_student_dashboard():
    """Get student dashboard data with fees based on sponsorship"""
    try:
        from models import User, Student, Registration, Payment, ExamRegistration, FeesConfig

        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        if user.role != 'student':
            return jsonify({'error': 'Student access required'}), 403

        student = Student.query.filter_by(user_id=user.id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404

        # Get current registration
        registration = Registration.query.filter_by(
            student_id=student.id,
            registration_status='approved'
        ).first()

        # Calculate fees
        total_fees = 0
        paid_amount = 0
        outstanding = 0
        
        if registration:
            total_fees = registration.total_fees or 0
            paid_amount = registration.paid_amount or 0
            outstanding = total_fees - paid_amount
            
            # For government sponsored students, only show supplementary/resit/retake fees
            if student.is_government_sponsored:
                outstanding = registration.supplementary_exam_fees + registration.resit_fees + registration.retake_fees

        # Get exam fees
        exam_fees = ExamRegistration.query.filter_by(
            student_id=student.id,
            payment_status='pending'
        ).all()
        exam_fees_total = sum(e.fee or 0 for e in exam_fees)

        return jsonify({
            'user': {
                'id': user.id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'email': user.email
            },
            'student_number': student.student_number,
            'program_name': student.program.program_name if student.program else None,
            'academic_status': student.academic_status,
            'sponsorship_type': 'Government Sponsored' if student.is_government_sponsored else 'Self Sponsored',
            'is_ovc': student.is_ovc,
            'current_gpa': float(student.current_gpa) if student.current_gpa else 0.0,
            'credits_earned': student.total_credits_earned,
            'current_year': student.current_year,
            'campus': student.campus.campus_name if student.campus else None,
            'wants_accommodation': student.wants_accommodation,
            'total_fees': total_fees,
            'paid_amount': paid_amount,
            'outstanding_balance': outstanding,
            'exam_fees_due': exam_fees_total,
            'pending_payments': 0,
            'registered_exams': len(exam_fees),
            'accommodation_status': 'Applied' if student.wants_accommodation else 'Not Applied',
            'room_number': None,
            'recent_activity': []
        }), 200

    except Exception as e:
        print(f"Dashboard error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/students/results', methods=['GET'])
@jwt_required()
def get_student_results():
    """Get student results - only their own"""
    try:
        from models import User, Student, Enrollment, Module, AcademicRecord

        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        student = Student.query.filter_by(user_id=user.id).first()
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        # Get enrollments with grades
        enrollments = Enrollment.query.filter_by(
            student_id=student.id,
            status='completed'
        ).order_by(Enrollment.created_at.desc()).all()

        results = []
        for enrollment in enrollments:
            module = Module.query.get(enrollment.module_id)
            results.append({
                'module_code': module.module_code if module else 'N/A',
                'module_name': module.module_name if module else 'N/A',
                'credits': module.credits if module else 0,
                'grade': enrollment.grade,
                'grade_points': float(enrollment.grade_points) if enrollment.grade_points else 0,
                'semester': module.semester if module else None,
                'year_level': module.year_level if module else None
            })

        # Get academic records
        academic_records = AcademicRecord.query.filter_by(
            student_id=student.id
        ).order_by(AcademicRecord.created_at.desc()).all()

        records = []
        for record in academic_records:
            records.append({
                'semester_gpa': float(record.semester_gpa) if record.semester_gpa else 0,
                'cumulative_gpa': float(record.cumulative_gpa) if record.cumulative_gpa else 0,
                'academic_status': record.academic_status,
                'created_at': record.created_at.isoformat()
            })

        return jsonify({
            'student_number': student.student_number,
            'student_name': student.full_name,
            'program': student.program.program_name if student.program else None,
            'current_gpa': float(student.current_gpa) if student.current_gpa else 0,
            'academic_status': student.academic_status,
            'results': results,
            'academic_records': records
        }), 200

    except Exception as e:
        print(f"Results error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ==================== Admin Student Result View ====================

@api_bp.route('/admin/students/<int:student_id>/results', methods=['GET'])
@admin_required()
def admin_get_student_results(student_id):
    """Get student results for admin/staff to view"""
    try:
        from models import Student, Enrollment, Module, AcademicRecord

        student = Student.query.get(student_id)
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        enrollments = Enrollment.query.filter_by(
            student_id=student.id,
            status='completed'
        ).order_by(Enrollment.created_at.desc()).all()

        results = []
        for enrollment in enrollments:
            module = Module.query.get(enrollment.module_id)
            results.append({
                'module_code': module.module_code if module else 'N/A',
                'module_name': module.module_name if module else 'N/A',
                'credits': module.credits if module else 0,
                'grade': enrollment.grade,
                'grade_points': float(enrollment.grade_points) if enrollment.grade_points else 0,
                'semester': module.semester if module else None,
                'year_level': module.year_level if module else None
            })

        academic_records = AcademicRecord.query.filter_by(
            student_id=student.id
        ).order_by(AcademicRecord.created_at.desc()).all()

        records = []
        for record in academic_records:
            records.append({
                'semester_gpa': float(record.semester_gpa) if record.semester_gpa else 0,
                'cumulative_gpa': float(record.cumulative_gpa) if record.cumulative_gpa else 0,
                'academic_status': record.academic_status,
                'created_at': record.created_at.isoformat()
            })

        return jsonify({
            'student': {
                'id': student.id,
                'student_number': student.student_number,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'program': student.program.program_name if student.program else None,
                'current_year': student.current_year,
                'current_gpa': float(student.current_gpa) if student.current_gpa else 0,
                'academic_status': student.academic_status,
                'is_government_sponsored': student.is_government_sponsored
            },
            'results': results,
            'academic_records': records
        }), 200

    except Exception as e:
        print(f"Admin results error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ==================== Health Check Endpoint ====================

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        from models import db
        db_status = 'connected'
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
        except Exception as e:
            db_status = f'disconnected: {str(e)}'
            
        return jsonify({
            'status': 'healthy' if db_status == 'connected' else 'degraded',
            'database': db_status,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500