/**
 * Stripe Payment Integration
 * Handles all payment processing for Gips College Student Portal
 */

// Stripe Configuration
let stripe;
let elements;
let cardElement;

// Initialize Stripe with your publishable key
function initializeStripe() {
    const stripePublicKey = 'pk_test_51QnFBDQpAhs2bhxJKRVWi5OyO3UaohNOM7A53c3UX5mtBBs423rIVDE8hvoQW26grdRdO6jNfgvQHbJyXYPCwlpl00zBTdoVmR';
    
    try {
        stripe = Stripe(stripePublicKey);
        elements = stripe.elements();
        
        // Create card element
        const cardElementContainer = document.getElementById('cardElement');
        if (cardElementContainer) {
            cardElement = elements.create('card', {
                style: {
                    base: {
                        fontSize: '16px',
                        color: '#32325d',
                        fontFamily: '"Helvetica Neue", Helvetica, sans-serif',
                        '::placeholder': {
                            color: '#aab7c4'
                        }
                    },
                    invalid: {
                        color: '#fa755a',
                        iconColor: '#fa755a'
                    }
                }
            });
            cardElement.mount('#cardElement');
            
            // Handle card errors
            cardElement.addEventListener('change', function(event) {
                const displayError = document.getElementById('cardErrors');
                if (event.error) {
                    displayError.textContent = event.error.message;
                    displayError.style.display = 'block';
                } else {
                    displayError.textContent = '';
                    displayError.style.display = 'none';
                }
            });
            
            console.log('Stripe initialized successfully');
        }
    } catch (error) {
        console.error('Stripe initialization error:', error);
        showNotification('Payment system error. Please try again later.', 'error');
    }
}

/**
 * Create payment intent on backend
 * @param {number} amount - Amount to pay in dollars
 * @param {string} paymentType - Type of payment (exam_fee, accommodation, retake)
 * @param {number} registrationId - Registration ID (optional)
 * @returns {Promise} - Payment intent response
 */
async function createPaymentIntent(amount, paymentType, registrationId = null) {
    try {
        console.log('Creating payment intent:', { amount, paymentType, registrationId });
        
        const data = {
            amount: amount,
            payment_type: paymentType,
            currency: 'usd'
        };

        // Add registration ID if provided
        if (registrationId) {
            if (paymentType === 'exam_fee') {
                data.exam_registration_id = registrationId;
            } else if (paymentType === 'accommodation') {
                data.accommodation_registration_id = registrationId;
            }
        }

        const response = await apiCall('POST', '/api/payments/create-payment-intent', data);
        
        if (response.ok) {
            const result = await response.json();
            console.log('Payment intent created:', result);
            return result;
        } else {
            const error = await response.json();
            throw new Error(error.error || 'Failed to create payment intent');
        }
    } catch (error) {
        console.error('Create Payment Intent Error:', error);
        throw error;
    }
}

/**
 * Process payment with Stripe card element
 * @param {string} clientSecret - Client secret from payment intent
 * @returns {Promise} - Payment result
 */
async function processPayment(clientSecret) {
    try {
        console.log('Processing payment with client secret:', clientSecret);
        
        if (!stripe || !elements) {
            throw new Error('Stripe not initialized');
        }

        if (!cardElement) {
            throw new Error('Card element not found');
        }
        
        // Use confirmCardPayment for one-time payments
        const result = await stripe.confirmCardPayment(clientSecret, {
            payment_method: {
                card: cardElement,
                billing_details: {
                    name: document.getElementById('cardholderName')?.value || 'Student',
                    email: getCurrentUser()?.email || 'student@gipscollege.edu'
                }
            }
        });

        console.log('Payment result:', result);

        if (result.error) {
            throw new Error(result.error.message);
        } else if (result.paymentIntent) {
            if (result.paymentIntent.status === 'succeeded') {
                return {
                    success: true,
                    paymentIntentId: result.paymentIntent.id,
                    status: result.paymentIntent.status
                };
            } else if (result.paymentIntent.status === 'processing') {
                return {
                    success: true,
                    paymentIntentId: result.paymentIntent.id,
                    status: 'processing'
                };
            }
        }
        
        throw new Error('Payment processing failed');
    } catch (error) {
        console.error('Payment Processing Error:', error);
        throw error;
    }
}

/**
 * Confirm payment on backend
 * @param {string} paymentIntentId - Payment intent ID from Stripe
 * @returns {Promise} - Confirmation response
 */
async function confirmPayment(paymentIntentId) {
    try {
        console.log('Confirming payment:', paymentIntentId);
        
        const response = await apiCall('POST', '/api/payments/confirm-payment', {
            paymentIntentId: paymentIntentId
        });

        if (response.ok) {
            const result = await response.json();
            console.log('Payment confirmed:', result);
            return result;
        } else {
            const error = await response.json();
            throw new Error(error.error || 'Failed to confirm payment');
        }
    } catch (error) {
        console.error('Payment Confirmation Error:', error);
        throw error;
    }
}

/**
 * Handle payment form submission (for exams and accommodations)
 * @param {Event} event - Form submit event
 * @param {string} paymentType - Type of payment
 * @param {number} amount - Amount to pay
 * @param {number} registrationId - Registration ID
 */
async function handlePaymentSubmit(event, paymentType, amount, registrationId = null) {
    event.preventDefault();

    const paymentForm = document.getElementById('paymentForm');
    const errorElement = document.getElementById('paymentError');
    const successElement = document.getElementById('paymentSuccess');
    const submitButton = paymentForm.querySelector('button[type="submit"]');

    try {
        // Hide previous messages
        if (errorElement) errorElement.style.display = 'none';
        if (successElement) successElement.style.display = 'none';

        // Disable submit button
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = 'Processing...';
        }

        console.log('Payment submission:', { paymentType, amount, registrationId });

        // Validate amount
        if (amount <= 0) {
            throw new Error('Invalid payment amount');
        }

        // Step 1: Create payment intent
        const intentData = await createPaymentIntent(amount, paymentType, registrationId);

        if (!intentData.clientSecret) {
            throw new Error('Failed to get payment client secret');
        }

        // Step 2: Process payment with card
        const paymentResult = await processPayment(intentData.clientSecret);
        
        if (paymentResult.success) {
            // Step 3: Confirm payment on backend
            const confirmation = await confirmPayment(paymentResult.paymentIntentId);
            
            // Show success message
            if (successElement) {
                successElement.innerHTML = `
                    <strong>✅ Payment Successful!</strong><br>
                    Payment ID: ${confirmation.paymentId}<br>
                    Amount: $${confirmation.amount}<br>
                    Thank you for your payment!
                `;
                successElement.style.display = 'block';
            }

            // Clear form
            if (paymentForm) paymentForm.reset();
            if (cardElement) cardElement.clear();

            // Show notification
            showNotification('Payment processed successfully! Redirecting...', 'success', 3000);

            // Redirect after 3 seconds
            setTimeout(() => {
                window.location.reload();
            }, 3000);
        } else {
            throw new Error('Payment was not successful');
        }
    } catch (error) {
        console.error('Payment Error:', error);
        
        const errorMessage = error.message || 'Payment failed. Please try again.';
        
        if (errorElement) {
            errorElement.innerHTML = `<strong>❌ Payment Error:</strong><br>${errorMessage}`;
            errorElement.style.display = 'block';
        }

        showNotification(errorMessage, 'error', 5000);
    } finally {
        // Re-enable submit button
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.textContent = 'Pay Now';
        }
    }
}

/**
 * Get payment history
 * @param {number} page - Page number
 * @returns {Promise} - Payment history
 */
async function getPaymentHistory(page = 1) {
    try {
        const response = await apiCall('GET', `/api/payments/history?page=${page}&per_page=10`);
        
        if (response.ok) {
            return await response.json();
        } else {
            throw new Error('Failed to load payment history');
        }
    } catch (error) {
        console.error('Get Payment History Error:', error);
        throw error;
    }
}

/**
 * Get specific payment details
 * @param {number} paymentId - Payment ID
 * @returns {Promise} - Payment details
 */
async function getPaymentDetails(paymentId) {
    try {
        const response = await apiCall('GET', `/api/payments/${paymentId}`);
        
        if (response.ok) {
            return await response.json();
        } else {
            throw new Error('Failed to load payment details');
        }
    } catch (error) {
        console.error('Get Payment Details Error:', error);
        throw error;
    }
}

/**
 * Request refund for a payment
 * @param {number} paymentId - Payment ID to refund
 * @returns {Promise} - Refund response
 */
async function requestRefund(paymentId) {
    try {
        if (!confirm('Are you sure you want to request a refund? This action cannot be undone.')) {
            return;
        }

        console.log('Requesting refund for payment:', paymentId);

        const response = await apiCall('POST', `/api/payments/${paymentId}/refund`, {});
        
        if (response.ok) {
            const result = await response.json();
            showNotification(`Refund processed successfully! Refund ID: ${result.refund_id}`, 'success');
            return result;
        } else {
            const error = await response.json();
            throw new Error(error.error || 'Refund request failed');
        }
    } catch (error) {
        console.error('Refund Error:', error);
        showNotification(error.message, 'error');
        throw error;
    }
}

/**
 * Display payment receipt
 * @param {object} paymentData - Payment information
 */
function displayPaymentReceipt(paymentData) {
    const receiptHTML = `
        <div class="receipt">
            <h2>Payment Receipt</h2>
            <div class="receipt-item">
                <span>Payment ID:</span>
                <strong>${paymentData.id}</strong>
            </div>
            <div class="receipt-item">
                <span>Amount:</span>
                <strong>$${paymentData.amount.toFixed(2)}</strong>
            </div>
            <div class="receipt-item">
                <span>Payment Type:</span>
                <strong>${paymentData.payment_type.replace('_', ' ').toUpperCase()}</strong>
            </div>
            <div class="receipt-item">
                <span>Status:</span>
                <strong class="badge ${paymentData.status}">${paymentData.status.toUpperCase()}</strong>
            </div>
            <div class="receipt-item">
                <span>Date:</span>
                <strong>${new Date(paymentData.payment_date).toLocaleDateString()}</strong>
            </div>
            <div class="receipt-item">
                <span>Stripe ID:</span>
                <small>${paymentData.stripe_payment_id}</small>
            </div>
            <p class="receipt-note">
                ✅ Thank you for your payment to Gips College!<br>
                A confirmation email has been sent to your registered email address.
            </p>
            <button class="btn btn-primary" onclick="window.print()">Print Receipt</button>
        </div>
    `;
    
    return receiptHTML;
}

/**
 * Handle payment error with user-friendly message
 * @param {Error} error - Error object
 * @returns {string} - User-friendly error message
 */
function getPaymentErrorMessage(error) {
    const errorMessages = {
        'Your card was declined': 'Your card was declined. Please try another card or contact your bank.',
        'Your card has insufficient funds': 'Your card has insufficient funds. Please try another payment method.',
        'Your card has expired': 'Your card has expired. Please use a different card.',
        'Incorrect CVC': 'The CVC code you entered is incorrect.',
        'Incorrect zip': 'The zip code you entered is incorrect.',
    };

    for (const [key, message] of Object.entries(errorMessages)) {
        if (error.message.includes(key)) {
            return message;
        }
    }

    return error.message || 'Payment failed. Please try again or contact support.';
}

/**
 * Validate payment form before submission
 * @returns {boolean}
 */
function validatePaymentForm() {
    const cardholderName = document.getElementById('cardholderName');
    
    if (cardholderName && !cardholderName.value.trim()) {
        showNotification('Please enter cardholder name', 'error');
        return false;
    }

    if (!cardElement) {
        showNotification('Card element not initialized', 'error');
        return false;
    }

    return true;
}

/**
 * Format currency for display
 * @param {number} amount - Amount in dollars
 * @returns {string} - Formatted currency
 */
function formatPaymentAmount(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

/**
 * Update payment status display
 * @param {string} status - Payment status
 * @returns {string} - Status badge HTML
 */
function getPaymentStatusBadge(status) {
    const statusColors = {
        'pending': 'warning',
        'completed': 'success',
        'failed': 'danger',
        'refunded': 'info',
        'processing': 'info'
    };

    const color = statusColors[status] || 'secondary';
    return `<span class="badge badge-${color}">${status.toUpperCase()}</span>`;
}

/**
 * Initialize payment page
 * Call this on page load for payment pages
 */
function initializePaymentPage() {
    console.log('Initializing payment page');
    
    // Initialize Stripe
    initializeStripe();
    
    // Setup payment form if it exists
    const paymentForm = document.getElementById('paymentForm');
    if (paymentForm) {
        paymentForm.addEventListener('submit', function(e) {
            if (!validatePaymentForm()) {
                e.preventDefault();
            }
        });
    }

    // Add cardholder name field styling
    const cardholderNameInput = document.getElementById('cardholderName');
    if (cardholderNameInput) {
        cardholderNameInput.addEventListener('focus', function() {
            this.style.borderColor = '#007bff';
        });
        
        cardholderNameInput.addEventListener('blur', function() {
            this.style.borderColor = '#ddd';
        });
    }
}

/**
 * Display payment methods
 */
function displayPaymentMethods() {
    return `
        <div class="payment-methods">
            <h4>Accepted Payment Methods</h4>
            <div class="methods">
                <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 32'%3E%3Crect fill='%231434CB' width='48' height='32' rx='4'/%3E%3Ctext x='24' y='20' text-anchor='middle' fill='white' font-size='12' font-weight='bold'%3EVISA%3C/text%3E%3C/svg%3E" alt="Visa" title="Visa">
                <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 32'%3E%3Crect fill='%23EB001B' width='48' height='32' rx='4'/%3E%3Ctext x='24' y='20' text-anchor='middle' fill='white' font-size='10' font-weight='bold'%3EMasterCard%3C/text%3E%3C/svg%3E" alt="Mastercard" title="Mastercard">
                <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 32'%3E%3Crect fill='%231E1E1E' width='48' height='32' rx='4'/%3E%3Ctext x='24' y='20' text-anchor='middle' fill='white' font-size='8' font-weight='bold'%3EAmerican Express%3C/text%3E%3C/svg%3E" alt="American Express" title="American Express">
                <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 32'%3E%3Crect fill='%231A1F71' width='48' height='32' rx='4'/%3E%3Ctext x='24' y='20' text-anchor='middle' fill='white' font-size='8' font-weight='bold'%3EDiscover%3C/text%3E%3C/svg%3E" alt="Discover" title="Discover">
            </div>
            <p style="font-size: 0.85rem; color: #666; margin-top: 10px;">
                🔒 All transactions are secured with 256-bit SSL encryption
            </p>
        </div>
    `;
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializePaymentPage();
});

// Make functions available globally
window.handlePaymentSubmit = handlePaymentSubmit;
window.requestRefund = requestRefund;
window.getPaymentHistory = getPaymentHistory;
window.displayPaymentReceipt = displayPaymentReceipt;
window.formatPaymentAmount = formatPaymentAmount;
window.getPaymentErrorMessage = getPaymentErrorMessage;