import stripe
import os
from datetime import datetime

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

class StripeHandler:
    """Handle Stripe payment operations"""
    
    @staticmethod
    def create_payment_intent(amount, currency='usd', metadata=None):
        """Create a payment intent"""
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(float(amount) * 100),  # Convert to cents
                currency=currency,
                metadata=metadata or {}
            )
            return {'success': True, 'intent': intent}
        except stripe.error.StripeError as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def confirm_payment_intent(payment_intent_id):
        """Confirm a payment intent"""
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {'success': True, 'intent': intent}
        except stripe.error.StripeError as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def create_refund(payment_intent_id):
        """Create a refund for a payment"""
        try:
            refund = stripe.Refund.create(
                payment_intent=payment_intent_id
            )
            return {'success': True, 'refund': refund}
        except stripe.error.StripeError as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_payment_intent(payment_intent_id):
        """Get payment intent details"""
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {'success': True, 'intent': intent}
        except stripe.error.StripeError as e:
            return {'success': False, 'error': str(e)}