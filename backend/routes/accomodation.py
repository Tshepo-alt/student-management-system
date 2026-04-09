# backend/routes/accommodation.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import traceback

from models import db, User, Student, Campus, AccommodationRegistration, AccommodationRoom, AccommodationRule, Notification

accommodation_bp = Blueprint('accommodation', __name__)


# ============================================
# ACCOMMODATION RULES ROUTES
# ============================================

@accommodation_bp.route('/rules', methods=['GET'])
@jwt_required()
def get_accommodation_rules():
    """Get all accommodation rules"""
    try:
        rules = AccommodationRule.query.order_by(AccommodationRule.display_order).all()
        
        result = []
        for rule in rules:
            result.append({
                'id': rule.id,
                'rule_title': rule.rule_title,
                'rule_description': rule.rule_description,
                'is_mandatory': rule.is_mandatory,
                'display_order': rule.display_order,
                'created_at': rule.created_at.isoformat() if rule.created_at else None
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[ACCOMMODATION] Get rules error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@accommodation_bp.route('/rules/acknowledge', methods=['POST'])
@jwt_required()
def acknowledge_rules():
    """Acknowledge that student has read and accepted accommodation rules"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        data = request.get_json()
        acknowledged = data.get('acknowledged', False)
        
        if not acknowledged:
            return jsonify({'error': 'Must acknowledge rules'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        student = Student.query.filter_by(user_id=user.id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        
        # Create notification for acknowledgment
        notification = Notification(
            student_id=student.id,
            title="Accommodation Rules Acknowledged",
            message="You have successfully acknowledged the GIPS Student Village rules and regulations.",
            notification_type="success"
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Rules acknowledged successfully',
            'acknowledged_at': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ACCOMMODATION] Acknowledge rules error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# ACCOMMODATION ROOM ROUTES
# ============================================

@accommodation_bp.route('/rooms', methods=['GET'])
@jwt_required()
def get_available_rooms():
    """Get available accommodation rooms (GIPS Student Village)"""
    try:
        campus_id = request.args.get('campus_id', type=int)
        room_type = request.args.get('room_type')
        
        query = AccommodationRoom.query.filter_by(is_available=True)
        
        if campus_id:
            campus = Campus.query.get(campus_id)
            if campus and campus.has_accommodation:
                pass
            else:
                return jsonify([]), 200
        
        if room_type:
            query = query.filter_by(room_type=room_type)
        
        rooms = query.all()
        
        blocks = {}
        for room in rooms:
            if room.block_name not in blocks:
                blocks[room.block_name] = {
                    'block_name': room.block_name,
                    'total_rooms': 0,
                    'available_rooms': 0,
                    'bachelor_pads': 0,
                    'three_bed_rooms': 0,
                    'rooms': []
                }
            
            blocks[room.block_name]['total_rooms'] += 1
            if room.is_available:
                blocks[room.block_name]['available_rooms'] += 1
            
            if room.room_type == 'bachelor_pad':
                blocks[room.block_name]['bachelor_pads'] += 1
            else:
                blocks[room.block_name]['three_bed_rooms'] += 1
            
            blocks[room.block_name]['rooms'].append({
                'room_number': room.room_number,
                'room_type': room.room_type,
                'capacity': room.capacity,
                'current_occupants': room.current_occupants,
                'is_available': room.is_available,
                'has_kitchen': room.has_kitchen,
                'has_shower': room.has_shower,
                'has_study_table': room.has_study_table,
                'has_bed': room.has_bed
            })
        
        result = list(blocks.values())
        
        total_rooms = sum(b['total_rooms'] for b in result)
        available_rooms = sum(b['available_rooms'] for b in result)
        
        return jsonify({
            'blocks': result,
            'total_rooms': total_rooms,
            'available_rooms': available_rooms,
            'occupancy_rate': ((total_rooms - available_rooms) / total_rooms * 100) if total_rooms > 0 else 0
        }), 200
        
    except Exception as e:
        print(f"[ACCOMMODATION] Get rooms error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@accommodation_bp.route('/rooms/<string:block>/<string:room_number>', methods=['GET'])
@jwt_required()
def get_room_details(block, room_number):
    """Get specific room details"""
    try:
        room = AccommodationRoom.query.filter_by(
            block_name=block,
            room_number=room_number
        ).first()
        
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        
        result = {
            'id': room.id,
            'block_name': room.block_name,
            'room_number': room.room_number,
            'room_type': room.room_type,
            'capacity': room.capacity,
            'current_occupants': room.current_occupants,
            'is_available': room.is_available,
            'has_kitchen': room.has_kitchen,
            'has_shower': room.has_shower,
            'has_study_table': room.has_study_table,
            'has_bed': room.has_bed
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[ACCOMMODATION] Get room details error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# ACCOMMODATION APPLICATION ROUTES
# ============================================

@accommodation_bp.route('/apply', methods=['POST'])
@jwt_required()
def apply_for_accommodation():
    """Submit accommodation application"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        data = request.get_json()
        
        required_fields = ['room_type', 'emergency_contact_name', 'emergency_contact_phone', 'has_accepted_rules']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        student = Student.query.filter_by(user_id=user.id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        
        campus = Campus.query.get(student.campus_id)
        if not campus or not campus.has_accommodation:
            return jsonify({'error': 'Accommodation is not available at your campus'}), 400
        
        existing_application = AccommodationRegistration.query.filter_by(
            student_id=student.id
        ).filter(
            AccommodationRegistration.status.in_(['pending', 'approved', 'allocated'])
        ).first()
        
        if existing_application:
            return jsonify({
                'error': 'You already have an active accommodation application',
                'application_id': existing_application.id,
                'status': existing_application.status
            }), 409
        
        room_type = data.get('room_type')
        if room_type not in ['bachelor_pad', 'three_bed']:
            return jsonify({'error': 'Invalid room type. Must be bachelor_pad or three_bed'}), 400
        
        available_rooms = AccommodationRoom.query.filter_by(
            room_type=room_type,
            is_available=True
        ).count()
        
        if available_rooms == 0:
            return jsonify({'error': f'No {room_type} rooms available at the moment'}), 400
        
        from models import Registration, AcademicYear, Semester
        current_registration = Registration.query.filter_by(
            student_id=student.id,
            registration_status='approved'
        ).order_by(Registration.created_at.desc()).first()
        
        if not current_registration:
            current_year = AcademicYear.query.filter_by(is_current=True).first()
            current_semester = Semester.query.filter_by(is_active=True).first()
            
            if current_year and current_semester:
                registration = Registration(
                    student_id=student.id,
                    academic_year_id=current_year.id,
                    semester_id=current_semester.id,
                    year_of_study=student.current_year or 1,
                    registration_date=datetime.utcnow().date(),
                    sponsorship_type='government_sponsored' if student.is_government_sponsored else 'private',
                    registration_status='approved',
                    payment_status='completed' if student.is_government_sponsored else 'pending'
                )
                db.session.add(registration)
                db.session.flush()
                current_registration = registration
        
        accommodation_reg = AccommodationRegistration(
            student_id=student.id,
            registration_id=current_registration.id if current_registration else None,
            wants_accommodation=True,
            block_preference=data.get('block_preference'),
            room_type=room_type,
            has_accepted_rules=data.get('has_accepted_rules', False),
            emergency_contact_name=data.get('emergency_contact_name'),
            emergency_contact_phone=data.get('emergency_contact_phone'),
            emergency_contact_relationship=data.get('emergency_contact_relationship'),
            medical_conditions=data.get('medical_conditions'),
            dietary_requirements=data.get('dietary_requirements'),
            status='pending'
        )
        
        db.session.add(accommodation_reg)
        student.wants_accommodation = True
        student.updated_at = datetime.utcnow()
        
        notification = Notification(
            student_id=student.id,
            title="Accommodation Application Submitted",
            message=f"Your accommodation application ({room_type.replace('_', ' ').title()}) has been submitted successfully. You will receive a response within 48 hours.",
            notification_type="info"
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Accommodation application submitted successfully',
            'application_id': accommodation_reg.id,
            'status': accommodation_reg.status,
            'room_type': room_type,
            'applied_at': accommodation_reg.created_at.isoformat() if accommodation_reg.created_at else None
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"[ACCOMMODATION] Apply error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@accommodation_bp.route('/status', methods=['GET'])
@jwt_required()
def get_accommodation_status():
    """Get current student's accommodation application status"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        student = Student.query.filter_by(user_id=user.id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        
        registration = AccommodationRegistration.query.filter_by(
            student_id=student.id
        ).order_by(AccommodationRegistration.created_at.desc()).first()
        
        if not registration:
            return jsonify({
                'has_applied': False,
                'wants_accommodation': student.wants_accommodation,
                'message': 'No accommodation application found'
            }), 200
        
        status_map = {
            'pending': {'display': 'Pending Review', 'icon': '⏳', 'class': 'badge-pending'},
            'approved': {'display': 'Approved', 'icon': '✅', 'class': 'badge-approved'},
            'rejected': {'display': 'Rejected', 'icon': '❌', 'class': 'badge-rejected'},
            'waitlisted': {'display': 'Waitlisted', 'icon': '📋', 'class': 'badge-waitlisted'},
            'allocated': {'display': 'Room Allocated', 'icon': '🏠', 'class': 'badge-allocated'},
            'checked_in': {'display': 'Checked In', 'icon': '🔑', 'class': 'badge-checked-in'}
        }
        
        status_info = status_map.get(registration.status, {'display': registration.status, 'icon': '📌', 'class': ''})
        
        allocated_room = None
        if registration.allocated_room_number and registration.allocated_block:
            room = AccommodationRoom.query.filter_by(
                room_number=registration.allocated_room_number,
                block_name=registration.allocated_block
            ).first()
            if room:
                allocated_room = {
                    'room_number': room.room_number,
                    'block_name': room.block_name,
                    'room_type': room.room_type,
                    'capacity': room.capacity,
                    'current_occupants': room.current_occupants
                }
        
        result = {
            'has_applied': True,
            'application_id': registration.id,
            'status': registration.status,
            'status_display': status_info['display'],
            'status_icon': status_info['icon'],
            'status_class': status_info['class'],
            'room_type': registration.room_type,
            'room_type_display': 'Bachelor Pad (2 students per room)' if registration.room_type == 'bachelor_pad' else 'Three-Bed Room (6 students per room)',
            'block_preference': registration.block_preference,
            'allocated_block': registration.allocated_block,
            'allocated_room_number': registration.allocated_room_number,
            'allocated_room': allocated_room,
            'check_in_date': registration.check_in_date.isoformat() if registration.check_in_date else None,
            'check_out_date': registration.check_out_date.isoformat() if registration.check_out_date else None,
            'agreement_signed': registration.agreement_signed,
            'emergency_contact': {
                'name': registration.emergency_contact_name,
                'phone': registration.emergency_contact_phone,
                'relationship': registration.emergency_contact_relationship
            },
            'medical_conditions': registration.medical_conditions,
            'dietary_requirements': registration.dietary_requirements,
            'applied_date': registration.created_at.isoformat() if registration.created_at else None,
            'last_updated': registration.updated_at.isoformat() if registration.updated_at else None
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[ACCOMMODATION] Get status error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@accommodation_bp.route('/cancel', methods=['POST'])
@jwt_required()
def cancel_accommodation():
    """Cancel accommodation application"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        student = Student.query.filter_by(user_id=user.id).first()
        if not student:
            return jsonify({'error': 'Student profile not found'}), 404
        
        registration = AccommodationRegistration.query.filter_by(
            student_id=student.id
        ).filter(
            AccommodationRegistration.status.in_(['pending', 'approved', 'waitlisted'])
        ).order_by(AccommodationRegistration.created_at.desc()).first()
        
        if not registration:
            return jsonify({'error': 'No active accommodation application found'}), 404
        
        print(f"[ACCOMMODATION] Student {student.student_number} cancelled application: {reason}")
        
        registration.status = 'cancelled'
        registration.updated_at = datetime.utcnow()
        student.wants_accommodation = False
        
        notification = Notification(
            student_id=student.id,
            title="Accommodation Application Cancelled",
            message=f"Your accommodation application has been cancelled. Reason: {reason}",
            notification_type="warning"
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Accommodation application cancelled successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ACCOMMODATION] Cancel error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# ADMIN ACCOMMODATION ROUTES
# ============================================

@accommodation_bp.route('/admin/applications', methods=['GET'])
@jwt_required()
def get_all_applications():
    """Get all accommodation applications (Admin only)"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator', 'staff']:
            return jsonify({'error': 'Admin access required'}), 403
        
        status_filter = request.args.get('status')
        
        query = AccommodationRegistration.query.join(Student).join(User)
        
        if status_filter:
            query = query.filter(AccommodationRegistration.status == status_filter)
        
        registrations = query.order_by(AccommodationRegistration.created_at.desc()).all()
        
        result = []
        for reg in registrations:
            result.append({
                'id': reg.id,
                'student_id': reg.student_id,
                'student_number': reg.student.student_number if reg.student else None,
                'student_name': f"{reg.student.first_name} {reg.student.last_name}" if reg.student else None,
                'email': reg.student.email if reg.student else None,
                'room_type': reg.room_type,
                'block_preference': reg.block_preference,
                'allocated_block': reg.allocated_block,
                'allocated_room_number': reg.allocated_room_number,
                'status': reg.status,
                'emergency_contact_name': reg.emergency_contact_name,
                'emergency_contact_phone': reg.emergency_contact_phone,
                'medical_conditions': reg.medical_conditions,
                'created_at': reg.created_at.isoformat() if reg.created_at else None,
                'updated_at': reg.updated_at.isoformat() if reg.updated_at else None
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[ACCOMMODATION] Get all applications error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ==================== ADD MISSING /admin/allocations ENDPOINT ====================
@accommodation_bp.route('/admin/allocations', methods=['GET'])
@jwt_required()
def get_all_allocations():
    """Get all allocated accommodations (Admin only)"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator', 'staff']:
            return jsonify({'error': 'Admin access required'}), 403
        
        allocations = AccommodationRegistration.query.filter(
            AccommodationRegistration.status == 'allocated'
        ).order_by(AccommodationRegistration.updated_at.desc()).all()
        
        result = []
        for alloc in allocations:
            student = Student.query.get(alloc.student_id)
            result.append({
                'id': alloc.id,
                'student_id': alloc.student_id,
                'student_name': f"{student.first_name} {student.last_name}" if student else 'Unknown',
                'student_number': student.student_number if student else 'N/A',
                'room_type': alloc.room_type,
                'allocated_block': alloc.allocated_block,
                'allocated_room_number': alloc.allocated_room_number,
                'allocated_at': alloc.updated_at.isoformat() if alloc.updated_at else None,
                'status': alloc.status
            })
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[ACCOMMODATION] Get allocations error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@accommodation_bp.route('/admin/rooms', methods=['GET'])
@jwt_required()
def get_all_rooms():
    """Get all rooms with occupancy details (Admin only)"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator', 'staff']:
            return jsonify({'error': 'Admin access required'}), 403
        
        block_filter = request.args.get('block')
        
        query = AccommodationRoom.query
        
        if block_filter:
            query = query.filter_by(block_name=block_filter)
        
        rooms = query.order_by(AccommodationRoom.block_name, AccommodationRoom.room_number).all()
        
        result = []
        for room in rooms:
            occupants = AccommodationRegistration.query.filter_by(
                allocated_block=room.block_name,
                allocated_room_number=room.room_number,
                status='allocated'
            ).all()
            
            occupant_list = []
            for occ in occupants:
                if occ.student:
                    occupant_list.append({
                        'student_number': occ.student.student_number,
                        'student_name': f"{occ.student.first_name} {occ.student.last_name}",
                        'check_in_date': occ.check_in_date.isoformat() if occ.check_in_date else None
                    })
            
            result.append({
                'id': room.id,
                'block_name': room.block_name,
                'room_number': room.room_number,
                'room_type': room.room_type,
                'capacity': room.capacity,
                'current_occupants': room.current_occupants,
                'is_available': room.is_available,
                'occupants': occupant_list,
                'has_kitchen': room.has_kitchen,
                'has_shower': room.has_shower,
                'has_study_table': room.has_study_table,
                'has_bed': room.has_bed
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[ACCOMMODATION] Get all rooms error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@accommodation_bp.route('/admin/applications/<int:application_id>/approve', methods=['POST'])
@jwt_required()
def approve_application(application_id):
    """Approve accommodation application and allocate room (Admin only)"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator', 'staff']:
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        allocated_block = data.get('allocated_block')
        allocated_room_number = data.get('allocated_room_number')
        
        registration = AccommodationRegistration.query.get(application_id)
        if not registration:
            return jsonify({'error': 'Application not found'}), 404
        
        if registration.status != 'pending':
            return jsonify({'error': f'Application already {registration.status}'}), 400
        
        if allocated_block and allocated_room_number:
            room = AccommodationRoom.query.filter_by(
                block_name=allocated_block,
                room_number=allocated_room_number,
                is_available=True
            ).first()
            
            if not room:
                return jsonify({'error': 'Room not available'}), 400
            
            if room.current_occupants >= room.capacity:
                return jsonify({'error': 'Room is at full capacity'}), 400
            
            room.current_occupants += 1
            if room.current_occupants >= room.capacity:
                room.is_available = False
            
            registration.allocated_block = allocated_block
            registration.allocated_room_number = allocated_room_number
        else:
            room_type = registration.room_type
            room = AccommodationRoom.query.filter_by(
                room_type=room_type,
                is_available=True
            ).first()
            
            if not room:
                return jsonify({'error': f'No {room_type} rooms available'}), 400
            
            room.current_occupants += 1
            if room.current_occupants >= room.capacity:
                room.is_available = False
            
            registration.allocated_block = room.block_name
            registration.allocated_room_number = room.room_number
        
        registration.status = 'allocated'
        registration.updated_at = datetime.utcnow()
        
        notification = Notification(
            student_id=registration.student_id,
            title="Accommodation Approved!",
            message=f"Your accommodation application has been approved. You have been allocated Room {registration.allocated_room_number}, Block {registration.allocated_block}. Please check in on the designated date.",
            notification_type="success"
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Application approved and room allocated',
            'allocated_block': registration.allocated_block,
            'allocated_room_number': registration.allocated_room_number
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ACCOMMODATION] Approve application error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@accommodation_bp.route('/admin/applications/<int:application_id>/reject', methods=['POST'])
@jwt_required()
def reject_application(application_id):
    """Reject accommodation application (Admin only)"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator', 'staff']:
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        rejection_reason = data.get('reason', 'No reason provided')
        
        registration = AccommodationRegistration.query.get(application_id)
        if not registration:
            return jsonify({'error': 'Application not found'}), 404
        
        if registration.status != 'pending':
            return jsonify({'error': f'Application already {registration.status}'}), 400
        
        registration.status = 'rejected'
        registration.updated_at = datetime.utcnow()
        
        notification = Notification(
            student_id=registration.student_id,
            title="Accommodation Application Update",
            message=f"Your accommodation application has been reviewed and was not approved. Reason: {rejection_reason}. Please contact the Accommodation Office for more information.",
            notification_type="error"
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Application rejected'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ACCOMMODATION] Reject application error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@accommodation_bp.route('/admin/applications/<int:application_id>/waitlist', methods=['POST'])
@jwt_required()
def waitlist_application(application_id):
    """Add application to waitlist (Admin only)"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator', 'staff']:
            return jsonify({'error': 'Admin access required'}), 403
        
        registration = AccommodationRegistration.query.get(application_id)
        if not registration:
            return jsonify({'error': 'Application not found'}), 404
        
        if registration.status != 'pending':
            return jsonify({'error': f'Application already {registration.status}'}), 400
        
        registration.status = 'waitlisted'
        registration.updated_at = datetime.utcnow()
        
        notification = Notification(
            student_id=registration.student_id,
            title="Accommodation Application Update",
            message="Your application has been placed on the waitlist. We will notify you when a room becomes available.",
            notification_type="info"
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Application moved to waitlist'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ACCOMMODATION] Waitlist application error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@accommodation_bp.route('/admin/rooms/<int:room_id>/maintenance', methods=['PUT'])
@jwt_required()
def update_room_maintenance(room_id):
    """Update room availability for maintenance (Admin only)"""
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        
        user = User.query.get(user_id)
        if not user or user.role not in ['admin', 'administrator', 'staff']:
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        is_available = data.get('is_available')
        
        if is_available is None:
            return jsonify({'error': 'is_available field required'}), 400
        
        room = AccommodationRoom.query.get(room_id)
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        
        room.is_available = is_available
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Room {"marked available" if is_available else "marked unavailable for maintenance"}',
            'room_number': room.room_number,
            'block': room.block_name
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ACCOMMODATION] Update room maintenance error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================
# ACCOMMODATION STATISTICS
# ============================================

@accommodation_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_accommodation_statistics():
    """Get accommodation statistics"""
    try:
        total_rooms = AccommodationRoom.query.count()
        available_rooms = AccommodationRoom.query.filter_by(is_available=True).count()
        
        bachelor_pads = AccommodationRoom.query.filter_by(room_type='bachelor_pad').count()
        bachelor_pads_available = AccommodationRoom.query.filter_by(room_type='bachelor_pad', is_available=True).count()
        
        three_bed_rooms = AccommodationRoom.query.filter_by(room_type='three_bed').count()
        three_bed_available = AccommodationRoom.query.filter_by(room_type='three_bed', is_available=True).count()
        
        total_applications = AccommodationRegistration.query.count()
        pending_applications = AccommodationRegistration.query.filter_by(status='pending').count()
        approved_applications = AccommodationRegistration.query.filter_by(status='approved').count()
        allocated_applications = AccommodationRegistration.query.filter_by(status='allocated').count()
        waitlisted_applications = AccommodationRegistration.query.filter_by(status='waitlisted').count()
        rejected_applications = AccommodationRegistration.query.filter_by(status='rejected').count()
        
        total_capacity = sum(room.capacity for room in AccommodationRoom.query.all())
        current_occupants = sum(room.current_occupants for room in AccommodationRoom.query.all())
        occupancy_rate = (current_occupants / total_capacity * 100) if total_capacity > 0 else 0
        
        return jsonify({
            'rooms': {
                'total': total_rooms,
                'available': available_rooms,
                'bachelor_pads': {
                    'total': bachelor_pads,
                    'available': bachelor_pads_available
                },
                'three_bed_rooms': {
                    'total': three_bed_rooms,
                    'available': three_bed_available
                }
            },
            'applications': {
                'total': total_applications,
                'pending': pending_applications,
                'approved': approved_applications,
                'allocated': allocated_applications,
                'waitlisted': waitlisted_applications,
                'rejected': rejected_applications
            },
            'occupancy': {
                'total_capacity': total_capacity,
                'current_occupants': current_occupants,
                'occupancy_rate': round(occupancy_rate, 1)
            }
        }), 200
        
    except Exception as e:
        print(f"[ACCOMMODATION] Get statistics error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500