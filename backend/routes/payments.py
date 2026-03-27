"""
Payment Routes - Stripe Integration
With Government Sponsorship Support and Installment Plans
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import stripe
import os
import traceback

from models import db, Payment, Student, ExamRegistration, AccommodationRegistration, Registration, FeesConfig

payments_bp = Blueprint('payments', __name__)

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Fee constants
SUPPLEMENTARY_FEE = 300
RESIT_FEE = 600
RETAKE_FEE = 1000
REGULAR_EXAM_FEE = 500

def calculate_fees(student, payment_type, amount=None):
    """Calculate fees based on sponsorship and payment type"""
    if student.is_government_sponsored:
        # Government sponsored students are exempt from regular fees
        if payment_type in ['registration', 'tuition', 'accommodation', 'exam']:
            return 0, True
        # But must pay for supplementary, resit, retake
        elif payment_type == 'supplementary':
            return SUPPLEMENTARY_FEE, False
        elif payment_type == 'resit':
            return RESIT_FEE, False
        elif payment_type == 'retake':
            return RETAKE_FEE, False
        else:
            return amount or 0, False
    else:
        # Self sponsored students pay all fees
        if payment_type == 'supplementary':
            return SUPPLEMENTARY_FEE, False
        elif payment_type == 'resit':
            return RESIT_FEE, False
        elif payment_type == 'retake':
            return RETAKE_FEE, False
        else:
            return amount or 0, False


@payments_bp.route('/create-payment-intent', methods=['POST'])
@jwt_required()
def create_payment_intent():
    """Create a Stripe payment intent"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        data = request.get_json()

        # Validate required fields
        required_fields = ['amount', 'payment_type']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields: amount, payment_type'}), 400

        try:
            amount = float(data['amount'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid amount format'}), 400

        payment_type = data['payment_type']
        currency = data.get('currency', 'bwp').lower()
        description = data.get('description', 'GIPS College Fee Payment')
        installment_plan = data.get('installment_plan', False)
        installment_months = data.get('installment_months', 3)

        # Validate amount
        if amount <= 0:
            return jsonify({'error': 'Amount must be greater than 0'}), 400

        # Validate currency
        if currency not in ['usd', 'bwp', 'zar']:
            return jsonify({'error': 'Invalid currency'}), 400

        # Calculate fee based on sponsorship
        calculated_amount, is_exempt = calculate_fees(student, payment_type, amount)
        
        if is_exempt:
            return jsonify({
                'message': 'This fee is exempted for government sponsored students',
                'is_exempt': True,
                'amount': 0
            }), 200

        # Convert to cents for Stripe
        amount_cents = int(amount * 100)

        # Create metadata
        metadata = {
            'student_id': str(student.id),
            'student_number': student.student_number,
            'payment_type': payment_type,
            'user_email': student.email,
            'installment_plan': str(installment_plan)
        }

        # Add related IDs if provided
        if 'exam_registration_id' in data:
            metadata['exam_registration_id'] = str(data['exam_registration_id'])
        if 'accommodation_registration_id' in data:
            metadata['accommodation_registration_id'] = str(data['accommodation_registration_id'])
        if 'registration_id' in data:
            metadata['registration_id'] = str(data['registration_id'])

        # Create Stripe payment intent
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=currency,
            metadata=metadata,
            receipt_email=student.email,
            description=description,
            statement_descriptor=f"GIPS COLLEGE {payment_type.upper()}"
        )

        # Create payment record in database
        payment = Payment(
            student_id=student.id,
            amount=amount,
            currency=currency.upper(),
            payment_type=payment_type,
            stripe_payment_intent_id=intent.id,
            status='pending',
            payment_reference=intent.client_secret,
            notes=f"Installment plan: {installment_plan} months" if installment_plan else None
        )

        # Link to specific registration if provided
        if 'exam_registration_id' in data:
            payment.exam_registration_id = data['exam_registration_id']
        if 'accommodation_registration_id' in data:
            payment.accommodation_registration_id = data['accommodation_registration_id']
        if 'registration_id' in data:
            payment.registration_id = data['registration_id']

        db.session.add(payment)
        db.session.commit()

        return jsonify({
            'clientSecret': intent.client_secret,
            'paymentIntentId': intent.id,
            'amount': amount,
            'currency': currency,
            'message': 'Payment intent created successfully',
            'is_exempt': False
        }), 200

    except stripe.error.CardError as e:
        return jsonify({'error': f'Card error: {e.user_message}'}), 400
    except stripe.error.RateLimitError:
        return jsonify({'error': 'Too many requests. Please try again later.'}), 429
    except stripe.error.InvalidRequestError as e:
        return jsonify({'error': f'Invalid request: {str(e)}'}), 400
    except stripe.error.AuthenticationError:
        return jsonify({'error': 'Authentication error with payment service'}), 401
    except stripe.error.APIConnectionError:
        return jsonify({'error': 'Payment service connection error'}), 503
    except Exception as e:
        db.session.rollback()
        print(f"Payment Intent Error: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to create payment intent'}), 500


@payments_bp.route('/confirm-payment', methods=['POST'])
@jwt_required()
def confirm_payment():
    """Confirm payment after successful Stripe charge"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        data = request.get_json()

        if 'paymentIntentId' not in data:
            return jsonify({'error': 'Payment Intent ID required'}), 400

        payment_intent_id = data['paymentIntentId']

        # Get payment intent from Stripe
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        except stripe.error.InvalidRequestError:
            return jsonify({'error': 'Invalid payment intent ID'}), 400

        # Verify payment was successful
        if intent.status != 'succeeded':
            return jsonify({
                'error': f'Payment not successful. Status: {intent.status}'
            }), 400

        # Get payment record from database
        payment = Payment.query.filter_by(
            stripe_payment_intent_id=payment_intent_id,
            student_id=student.id
        ).first()

        if not payment:
            return jsonify({'error': 'Payment record not found'}), 404

        # Update payment status
        payment.status = 'completed'
        payment.payment_date = datetime.utcnow()
        payment.transaction_id = intent.id

        # Update related exam registration
        if payment.exam_registration_id:
            exam_reg = ExamRegistration.query.get(payment.exam_registration_id)
            if exam_reg:
                exam_reg.payment_status = 'paid'
                print(f"Exam registration {exam_reg.id} marked as paid")

        # Update related accommodation registration
        if payment.accommodation_registration_id:
            accom_reg = AccommodationRegistration.query.get(payment.accommodation_registration_id)
            if accom_reg:
                accom_reg.payment_status = 'paid'
                print(f"Accommodation registration {accom_reg.id} marked as paid")

        # Update related registration
        if payment.registration_id:
            reg = Registration.query.get(payment.registration_id)
            if reg:
                reg.paid_amount = (reg.paid_amount or 0) + payment.amount
                if reg.paid_amount >= (reg.total_fees or 0):
                    reg.payment_status = 'completed'
                else:
                    reg.payment_status = 'partial'
                print(f"Registration {reg.id} updated with payment")

        db.session.commit()

        return jsonify({
            'message': 'Payment confirmed successfully',
            'paymentId': payment.id,
            'amount': payment.amount,
            'currency': payment.currency,
            'status': payment.status,
            'payment_date': payment.payment_date.isoformat()
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Confirm Payment Error: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to confirm payment'}), 500


@payments_bp.route('/installment-plan', methods=['POST'])
@jwt_required()
def create_installment_plan():
    """Create an installment plan for self-sponsored students"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        if student.is_government_sponsored:
            return jsonify({'error': 'Government sponsored students are exempt from fees'}), 400

        data = request.get_json()
        total_amount = float(data.get('total_amount', 0))
        months = int(data.get('months', 3))
        registration_id = data.get('registration_id')

        if total_amount <= 0:
            return jsonify({'error': 'Invalid total amount'}), 400

        if months not in [2, 3, 4, 6]:
            return jsonify({'error': 'Installment months must be 2, 3, 4, or 6'}), 400

        # Calculate installment amounts
        installment_amount = total_amount / months
        start_date = datetime.utcnow().date()
        
        installments = []
        for i in range(months):
            due_date = start_date + timedelta(days=30 * (i + 1))
            installments.append({
                'installment_number': i + 1,
                'amount': installment_amount,
                'due_date': due_date.isoformat(),
                'status': 'pending'
            })

        # Create payment record for the installment plan
        payment = Payment(
            student_id=student.id,
            registration_id=registration_id,
            amount=total_amount,
            currency='BWP',
            payment_type='installment_plan',
            status='pending',
            notes=f'Installment plan over {months} months',
            payment_reference=f'INST-{datetime.now().strftime("%Y%m%d%H%M%S")}-{student.id}'
        )
        
        db.session.add(payment)
        db.session.commit()

        return jsonify({
            'success': True,
            'installment_plan_id': payment.id,
            'total_amount': total_amount,
            'months': months,
            'installment_amount': installment_amount,
            'installments': installments,
            'message': f'Installment plan created successfully. Pay {installment_amount:.2f} per month for {months} months.'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Installment plan error: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to create installment plan'}), 500


@payments_bp.route('/history', methods=['GET'])
@jwt_required()
def get_payment_history():
    """Get student's payment history"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # Query payments
        paginated_payments = Payment.query.filter_by(
            student_id=student.id
        ).order_by(Payment.created_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        payments_list = []
        for payment in paginated_payments.items:
            payments_list.append({
                'id': payment.id,
                'amount': float(payment.amount),
                'currency': payment.currency,
                'payment_type': payment.payment_type,
                'status': payment.status,
                'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                'created_at': payment.created_at.isoformat(),
                'stripe_payment_intent_id': payment.stripe_payment_intent_id,
                'receipt_number': payment.receipt_number,
                'notes': payment.notes
            })

        # Calculate total paid and outstanding
        total_paid = sum(p.amount for p in Payment.query.filter_by(
            student_id=student.id,
            status='completed'
        ).all())

        # Get outstanding fees from registration
        registration = Registration.query.filter_by(
            student_id=student.id,
            registration_status='approved'
        ).first()
        
        outstanding = 0
        if registration:
            outstanding = (registration.total_fees or 0) - (registration.paid_amount or 0)

        return jsonify({
            'payments': payments_list,
            'total': paginated_payments.total,
            'pages': paginated_payments.pages,
            'current_page': page,
            'per_page': per_page,
            'total_paid': float(total_paid),
            'outstanding_balance': float(outstanding)
        }), 200

    except Exception as e:
        print(f"Get Payment History Error: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to retrieve payment history'}), 500


@payments_bp.route('/<int:payment_id>', methods=['GET'])
@jwt_required()
def get_payment_details(payment_id):
    """Get specific payment details"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        payment = Payment.query.filter_by(
            id=payment_id,
            student_id=student.id
        ).first()

        if not payment:
            return jsonify({'error': 'Payment not found'}), 404

        return jsonify({
            'id': payment.id,
            'amount': float(payment.amount),
            'currency': payment.currency,
            'payment_type': payment.payment_type,
            'status': payment.status,
            'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
            'created_at': payment.created_at.isoformat(),
            'updated_at': payment.updated_at.isoformat(),
            'stripe_payment_intent_id': payment.stripe_payment_intent_id,
            'receipt_number': payment.receipt_number,
            'transaction_id': payment.transaction_id,
            'notes': payment.notes,
            'exam_registration_id': payment.exam_registration_id,
            'accommodation_registration_id': payment.accommodation_registration_id,
            'registration_id': payment.registration_id
        }), 200

    except Exception as e:
        print(f"Get Payment Details Error: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to retrieve payment details'}), 500


@payments_bp.route('/outstanding', methods=['GET'])
@jwt_required()
def get_outstanding_fees():
    """Get student's outstanding fees"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        registration = Registration.query.filter_by(
            student_id=student.id,
            registration_status='approved'
        ).order_by(Registration.created_at.desc()).first()

        outstanding = {
            'total_fees': 0,
            'paid_amount': 0,
            'outstanding_balance': 0,
            'supplementary_fees': 0,
            'resit_fees': 0,
            'retake_fees': 0,
            'exempted_amount': 0
        }

        if registration:
            outstanding['total_fees'] = float(registration.total_fees or 0)
            outstanding['paid_amount'] = float(registration.paid_amount or 0)
            outstanding['outstanding_balance'] = outstanding['total_fees'] - outstanding['paid_amount']
            outstanding['supplementary_fees'] = float(registration.supplementary_exam_fees or 0)
            outstanding['resit_fees'] = float(registration.resit_fees or 0)
            outstanding['retake_fees'] = float(registration.retake_fees or 0)
            outstanding['exempted_amount'] = float(registration.exempted_amount or 0)

        # For government sponsored students, only show supplementary/resit/retake
        if student.is_government_sponsored:
            outstanding['outstanding_balance'] = (
                outstanding['supplementary_fees'] + 
                outstanding['resit_fees'] + 
                outstanding['retake_fees']
            )

        # Get pending exam fees
        pending_exams = ExamRegistration.query.filter_by(
            student_id=student.id,
            payment_status='pending'
        ).all()
        
        outstanding['pending_exam_fees'] = sum(e.fee or 0 for e in pending_exams)
        outstanding['pending_exam_count'] = len(pending_exams)

        return jsonify(outstanding), 200

    except Exception as e:
        print(f"Get outstanding fees error: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to retrieve outstanding fees'}), 500


@payments_bp.route('/<int:payment_id>/refund', methods=['POST'])
@jwt_required()
def request_refund(payment_id):
    """Request refund for a payment"""
    try:
        current_user_id = get_jwt_identity()
        user_id = int(current_user_id) if current_user_id else None
        student = Student.query.filter_by(user_id=user_id).first()

        if not student:
            return jsonify({'error': 'Student record not found'}), 404

        payment = Payment.query.filter_by(
            id=payment_id,
            student_id=student.id
        ).first()

        if not payment:
            return jsonify({'error': 'Payment not found'}), 404

        # Check if payment can be refunded
        if payment.status != 'completed':
            return jsonify({
                'error': f'Cannot refund payment with status: {payment.status}'
            }), 400

        # Check if payment is within refund window (30 days)
        if payment.payment_date and (datetime.utcnow() - payment.payment_date).days > 30:
            return jsonify({'error': 'Refund window expired (30 days)'}), 400

        # Create refund with Stripe
        try:
            if payment.stripe_payment_intent_id:
                refund = stripe.Refund.create(
                    payment_intent=payment.stripe_payment_intent_id
                )
                refund_id = refund.id
                refund_status = refund.status
            else:
                # For non-Stripe payments, manual refund
                refund_id = None
                refund_status = 'manual_required'

            # Update payment status
            payment.status = 'refunded'

            # Update related registrations
            if payment.exam_registration_id:
                exam_reg = ExamRegistration.query.get(payment.exam_registration_id)
                if exam_reg:
                    exam_reg.payment_status = 'refunded'

            if payment.accommodation_registration_id:
                accom_reg = AccommodationRegistration.query.get(payment.accommodation_registration_id)
                if accom_reg:
                    accom_reg.payment_status = 'refunded'

            if payment.registration_id:
                reg = Registration.query.get(payment.registration_id)
                if reg:
                    reg.paid_amount = (reg.paid_amount or 0) - payment.amount
                    reg.payment_status = 'pending'

            db.session.commit()

            return jsonify({
                'message': 'Refund processed successfully',
                'refund_id': refund_id,
                'amount': float(payment.amount),
                'status': refund_status
            }), 200

        except stripe.error.InvalidRequestError as e:
            return jsonify({'error': f'Stripe error: {str(e)}'}), 400

    except Exception as e:
        db.session.rollback()
        print(f"Refund Error: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to process refund'}), 500


@payments_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    try:
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')

        webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')

        if not webhook_secret:
            print("STRIPE_WEBHOOK_SECRET not configured")
            return jsonify({'error': 'Webhook not configured'}), 400

        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                webhook_secret
            )
        except ValueError:
            return jsonify({'error': 'Invalid payload'}), 400
        except stripe.error.SignatureVerificationError:
            return jsonify({'error': 'Invalid signature'}), 400

        # Handle payment_intent.succeeded
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            print(f"Payment succeeded: {payment_intent['id']}")

            # Update payment record
            payment = Payment.query.filter_by(
                stripe_payment_intent_id=payment_intent['id']
            ).first()

            if payment:
                payment.status = 'completed'
                payment.payment_date = datetime.utcnow()
                payment.transaction_id = payment_intent['id']
                
                # Update related exam registration
                if payment.exam_registration_id:
                    exam_reg = ExamRegistration.query.get(payment.exam_registration_id)
                    if exam_reg:
                        exam_reg.payment_status = 'paid'
                
                # Update related accommodation registration
                if payment.accommodation_registration_id:
                    accom_reg = AccommodationRegistration.query.get(payment.accommodation_registration_id)
                    if accom_reg:
                        accom_reg.payment_status = 'paid'
                
                db.session.commit()
                print(f"Payment record updated: {payment.id}")

        # Handle payment_intent.payment_failed
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            print(f"Payment failed: {payment_intent['id']}")

            payment = Payment.query.filter_by(
                stripe_payment_intent_id=payment_intent['id']
            ).first()

            if payment:
                payment.status = 'failed'
                db.session.commit()

        # Handle charge.refunded
        elif event['type'] == 'charge.refunded':
            charge = event['data']['object']
            print(f"Charge refunded: {charge['id']}")
            
            # Find payment by transaction_id
            payment = Payment.query.filter_by(transaction_id=charge['id']).first()
            if payment:
                payment.status = 'refunded'
                db.session.commit()

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        print(f"Webhook Error: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Webhook processing failed'}), 500