"""
Payment Service - Handle payment processing
Currently supports: Cash on Delivery (COD)
Future: Credit cards, digital wallets, etc.
"""

from datetime import datetime
from flask import jsonify

# Payment methods
PAYMENT_METHODS = {
    'cash': 'Cash on Delivery',
    'card': 'Credit/Debit Card',
    'wallet': 'Digital Wallet'
}

# Payment statuses
PAYMENT_STATUS = {
    'pending': 'Awaiting payment',
    'completed': 'Payment completed',
    'failed': 'Payment failed',
    'cancelled': 'Payment cancelled',
    'refunded': 'Payment refunded'
}

class PaymentProcessor:
    """Handle payment processing"""
    
    def __init__(self, db_engine='sqlite'):
        self.db_engine = db_engine
    
    def process_cash_on_delivery(self, order_id, amount, customer_info=None):
        """
        Process Cash on Delivery payment
        Returns: {'success': bool, 'transaction_id': str, 'status': str, 'message': str}
        """
        try:
            # For COD, we just record that payment will be collected at delivery
            transaction_id = f'COD-{order_id}-{int(datetime.now().timestamp())}'
            
            return {
                'success': True,
                'transaction_id': transaction_id,
                'status': 'pending',
                'message': f'Cash on Delivery confirmed. Amount: {amount}',
                'method': 'cash',
                'amount': amount,
                'created_at': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'status': 'failed',
                'message': 'Failed to process Cash on Delivery'
            }
    
    def process_card_payment(self, order_id, amount, card_token):
        """
        Process Credit/Debit Card payment
        In production, integrate with Stripe, PayMongo, etc.
        """
        try:
            # This is a placeholder - in production, integrate with actual payment gateway
            transaction_id = f'CARD-{order_id}-{int(datetime.now().timestamp())}'
            
            return {
                'success': True,
                'transaction_id': transaction_id,
                'status': 'completed',
                'message': 'Payment processed successfully',
                'method': 'card',
                'amount': amount,
                'created_at': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'status': 'failed',
                'message': 'Payment processing failed'
            }
    
    def verify_payment(self, transaction_id):
        """Verify payment status"""
        try:
            # Placeholder for payment verification
            # In production, check with payment gateway
            return {
                'verified': True,
                'transaction_id': transaction_id,
                'status': 'completed'
            }
        except Exception as e:
            return {
                'verified': False,
                'error': str(e)
            }
    
    def refund_payment(self, transaction_id, amount, reason=''):
        """Refund a payment"""
        try:
            refund_id = f'REFUND-{transaction_id}-{int(datetime.now().timestamp())}'
            
            return {
                'success': True,
                'refund_id': refund_id,
                'original_transaction': transaction_id,
                'amount': amount,
                'reason': reason,
                'status': 'processed',
                'created_at': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Refund processing failed'
            }

# Global payment processor instance
payment_processor = PaymentProcessor()

def process_payment(order_id, amount, method='cash', **kwargs):
    """
    Main function to process payments
    
    Args:
        order_id: Order ID
        amount: Payment amount
        method: Payment method ('cash', 'card', 'wallet')
        **kwargs: Additional parameters for the payment method
    
    Returns:
        Payment result dictionary
    """
    if method == 'cash':
        return payment_processor.process_cash_on_delivery(order_id, amount, kwargs.get('customer_info'))
    elif method == 'card':
        return payment_processor.process_card_payment(order_id, amount, kwargs.get('card_token'))
    else:
        return {
            'success': False,
            'error': f'Unsupported payment method: {method}',
            'message': f'Payment method "{method}" is not supported'
        }

def verify_payment(transaction_id):
    """Verify payment status"""
    return payment_processor.verify_payment(transaction_id)

def refund_payment(transaction_id, amount, reason=''):
    """Refund a payment"""
    return payment_processor.refund_payment(transaction_id, amount, reason)
