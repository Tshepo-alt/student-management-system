# backend/utils/email.py
from flask import current_app
from flask_mail import Mail, Message
from datetime import datetime
import secrets
import logging

logger = logging.getLogger(__name__)

mail = Mail()

class EmailService:
    """Professional email notifications for GIPS College"""

    @staticmethod
    def _get_base_url():
        return current_app.config.get('FRONTEND_URL', 'https://student-management-system-lks1.onrender.com')

    @staticmethod
    def _get_logo_url():
        return f"{EmailService._get_base_url()}/images/gipslogo.jpg"

    @staticmethod
    def _get_college_info():
        return {
            'name': 'GIPS College',
            'phone': '+267 712345600',
            'email': 'info@gipscollege.edu.bw',
            'address': '123 University Way, Gaborone, Botswana',
            'website': 'https://gipscollege.edu.bw'
        }

    @staticmethod
    def _get_html_template(title, content, button_text=None, button_url=None):
        college = EmailService._get_college_info()
        logo_url = EmailService._get_logo_url()
        year = datetime.now().year
        button_html = f'<div style="text-align: center;"><a href="{button_url}" class="button">{button_text}</a></div>' if button_text and button_url else ''

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background-color: #f4f7fc;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 20px auto;
                    background-color: #ffffff;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                }}
                .header {{
                    background: linear-gradient(135deg, #1a2a3a 0%, #2c3e50 100%);
                    padding: 20px 30px;
                    text-align: center;
                }}
                .logo {{
                    max-width: 150px;
                    margin-bottom: 10px;
                }}
                .college-name {{
                    color: #ffffff;
                    font-size: 24px;
                    font-weight: 600;
                    letter-spacing: 1px;
                }}
                .content {{
                    padding: 30px;
                    color: #333333;
                    line-height: 1.6;
                }}
                .button {{
                    display: inline-block;
                    background-color: #2c7da0;
                    color: #ffffff !important;
                    text-decoration: none;
                    padding: 12px 28px;
                    border-radius: 30px;
                    font-weight: 600;
                    margin: 20px 0;
                }}
                .footer {{
                    background-color: #eef2f7;
                    padding: 20px;
                    text-align: center;
                    font-size: 12px;
                    color: #7f8c8d;
                    border-top: 1px solid #dce5ec;
                }}
                .footer a {{
                    color: #2c7da0;
                    text-decoration: none;
                }}
                .social-links {{
                    margin-top: 10px;
                }}
                .info-box {{
                    background-color: #e7f3ff;
                    padding: 15px;
                    border-left: 4px solid #2196F3;
                    margin: 15px 0;
                }}
                .warning-box {{
                    background-color: #fff3cd;
                    padding: 15px;
                    border-left: 4px solid #ffc107;
                    margin: 15px 0;
                }}
                .code {{
                    background-color: #f0f0f0;
                    padding: 10px;
                    border-radius: 4px;
                    font-family: monospace;
                    font-size: 12px;
                    word-break: break-all;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="{logo_url}" alt="{college['name']}" class="logo" onerror="this.onerror=null; this.src='https://via.placeholder.com/150?text=GIPS';">
                    <div class="college-name">{college['name']}</div>
                </div>
                <div class="content">
                    {content}
                    {button_html}
                </div>
                <div class="footer">
                    <p>{college['name']}<br>
                    {college['address']}<br>
                    Phone: {college['phone']} | Email: {college['email']}</p>
                    <p>&copy; {year} {college['name']}. All rights reserved.</p>
                    <div class="social-links">
                        <a href="https://facebook.com/gipscollege">Facebook</a> |
                        <a href="https://twitter.com/gipscollege">Twitter</a> |
                        <a href="https://linkedin.com/school/gipscollege">LinkedIn</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    def generate_verification_token():
        return secrets.token_urlsafe(32)

    # ---------- Registration confirmation ----------
    @staticmethod
    def send_registration_confirmation(user_email, first_name, student_number, program_name=None, campus_name=None):
        try:
            subject = "[GIPS College] Welcome – Registration Confirmation"
            program_info = f"<strong>Program:</strong> {program_name}<br>" if program_name else ""
            campus_info = f"<strong>Campus:</strong> {campus_name}<br>" if campus_name else ""

            content = f"""
            <h2>Hello {first_name},</h2>
            <p>Thank you for registering with GIPS College. Your registration has been successful.</p>
            <div class="info-box">
                <strong>Registration details</strong><br>
                <strong>Student number:</strong> {student_number}<br>
                {program_info}{campus_info}
                <strong>Date:</strong> {datetime.now().strftime('%d %B %Y at %H:%M')}
            </div>
            <p><strong>Next steps</strong></p>
            <ul>
                <li>Log in to the portal with your email and password</li>
                <li>Complete your profile information</li>
                <li>Upload required documents</li>
                <li>Wait for admission approval</li>
            </ul>
            <p>Best regards,<br>GIPS College Administration</p>
            """
            button_text = "Log in to portal"
            button_url = f"{EmailService._get_base_url()}/pages/login.html"
            html = EmailService._get_html_template(subject, content, button_text, button_url)
            plain = f"Hello {first_name},\n\nThank you for registering with GIPS College. Your student number is {student_number}.\n\nLog in at {EmailService._get_base_url()}/pages/login.html\n\nBest regards,\nGIPS College"
            msg = Message(subject=subject, recipients=[user_email], html=html, body=plain)
            mail.send(msg)
            return True
        except Exception as e:
            logger.error(f"Registration email error: {e}")
            return False

    # ---------- Assignment submission ----------
    @staticmethod
    def send_assignment_submission_confirmation(user_email, first_name, assignment_title):
        try:
            subject = f"[GIPS College] Assignment submitted – {assignment_title}"
            content = f"""
            <p>Dear {first_name},</p>
            <p>Your assignment <strong>{assignment_title}</strong> has been submitted successfully.</p>
            <div class="info-box">
                <strong>Submission details</strong><br>
                <strong>Assignment:</strong> {assignment_title}<br>
                <strong>Time:</strong> {datetime.now().strftime('%d %B %Y at %H:%M')}
            </div>
            <p>You will receive feedback from your instructor shortly.</p>
            <p>Best regards,<br>GIPS College Administration</p>
            """
            button_text = "View assignments"
            button_url = f"{EmailService._get_base_url()}/pages/my-modules.html"
            html = EmailService._get_html_template(subject, content, button_text, button_url)
            plain = f"Dear {first_name},\n\nYour assignment '{assignment_title}' has been submitted.\n\nBest regards,\nGIPS College"
            msg = Message(subject=subject, recipients=[user_email], html=html, body=plain)
            mail.send(msg)
            return True
        except Exception as e:
            logger.error(f"Assignment email error: {e}")
            return False

    # ---------- Exam registration ----------
    @staticmethod
    def send_exam_registration_confirmation(user_email, first_name, course_name, exam_type, fee):
        try:
            subject = f"[GIPS College] Exam registration – {course_name}"
            content = f"""
            <p>Dear {first_name},</p>
            <p>You have successfully registered for a {exam_type} exam.</p>
            <div class="info-box">
                <strong>Exam details</strong><br>
                <strong>Course:</strong> {course_name}<br>
                <strong>Type:</strong> {exam_type.title()}<br>
                <strong>Fee:</strong> P {fee}
            </div>
            <p>Please proceed to make payment through the portal if required.</p>
            <p>Best regards,<br>GIPS College Administration</p>
            """
            button_text = "View exam dashboard"
            button_url = f"{EmailService._get_base_url()}/pages/exams.html"
            html = EmailService._get_html_template(subject, content, button_text, button_url)
            plain = f"Dear {first_name},\n\nYou have registered for {exam_type} exam in {course_name}. Fee: P{fee}\n\nBest regards,\nGIPS College"
            msg = Message(subject=subject, recipients=[user_email], html=html, body=plain)
            mail.send(msg)
            return True
        except Exception as e:
            logger.error(f"Exam email error: {e}")
            return False

    # ---------- Payment confirmation ----------
    @staticmethod
    def send_payment_confirmation(user_email, first_name, amount, payment_type, receipt_number=None):
        try:
            subject = f"[GIPS College] Payment confirmed – P {amount}"
            receipt_info = f"<strong>Receipt number:</strong> {receipt_number}<br>" if receipt_number else ""
            content = f"""
            <p>Dear {first_name},</p>
            <p>Your payment has been processed successfully.</p>
            <div class="info-box">
                <strong>Payment details</strong><br>
                <strong>Amount:</strong> P {amount}<br>
                <strong>Type:</strong> {payment_type.replace('_', ' ').title()}<br>
                {receipt_info}
                <strong>Date:</strong> {datetime.now().strftime('%d %B %Y at %H:%M')}
            </div>
            <p>Thank you for your payment. Please keep this receipt for your records.</p>
            <p>Best regards,<br>GIPS College Administration</p>
            """
            button_text = "View payment history"
            button_url = f"{EmailService._get_base_url()}/pages/payments.html"
            html = EmailService._get_html_template(subject, content, button_text, button_url)
            plain = f"Dear {first_name},\n\nYour payment of P{amount} for {payment_type} has been confirmed. Receipt: {receipt_number}\n\nThank you.\nGIPS College"
            msg = Message(subject=subject, recipients=[user_email], html=html, body=plain)
            mail.send(msg)
            return True
        except Exception as e:
            logger.error(f"Payment email error: {e}")
            return False

    # ---------- Accommodation registration ----------
    @staticmethod
    def send_accommodation_confirmation(user_email, first_name, accommodation_name, price):
        try:
            subject = f"[GIPS College] Accommodation registration – {accommodation_name}"
            content = f"""
            <p>Dear {first_name},</p>
            <p>Your accommodation request has been received.</p>
            <div class="info-box">
                <strong>Accommodation details</strong><br>
                <strong>Accommodation:</strong> {accommodation_name}<br>
                <strong>Price per semester:</strong> P {price}<br>
                <strong>Request date:</strong> {datetime.now().strftime('%d %B %Y')}
            </div>
            <div class="warning-box">
                <strong>Status:</strong> Your request is pending approval. You will receive an update within 5‑7 business days.
            </div>
            <p>Best regards,<br>GIPS College Administration</p>
            """
            button_text = "Track accommodation"
            button_url = f"{EmailService._get_base_url()}/pages/accommodation-status.html"
            html = EmailService._get_html_template(subject, content, button_text, button_url)
            plain = f"Dear {first_name},\n\nYour accommodation request for {accommodation_name} has been received and is pending approval.\n\nBest regards,\nGIPS College"
            msg = Message(subject=subject, recipients=[user_email], html=html, body=plain)
            mail.send(msg)
            return True
        except Exception as e:
            logger.error(f"Accommodation email error: {e}")
            return False

    # ---------- Password reset ----------
    @staticmethod
    def send_password_reset(user_email, first_name, reset_token, user_id):
        try:
            frontend_url = EmailService._get_base_url()
            reset_link = f"{frontend_url}/pages/reset-password.html?token={reset_token}&user_id={user_id}"
            subject = "[GIPS College] Password reset request"
            content = f"""
            <p>Hello {first_name},</p>
            <p>We received a request to reset your password. If you made this request, click the button below to set a new password.</p>
            <p><strong>This link will expire in 1 hour.</strong></p>
            <div class="warning-box">
                <strong>Security tip:</strong> Never share this link with anyone. GIPS College staff will never ask for your password by email.
            </div>
            """
            button_text = "Reset password"
            button_url = reset_link
            html = EmailService._get_html_template(subject, content, button_text, button_url)
            plain = f"Hello {first_name},\n\nReset your password using this link (valid for 1 hour): {reset_link}\n\nIf you did not request this, please ignore this email.\n\nGIPS College"
            msg = Message(subject=subject, recipients=[user_email], html=html, body=plain)
            mail.send(msg)
            return True
        except Exception as e:
            logger.error(f"Password reset email error: {e}")
            return False

    # ---------- Email verification ----------
    @staticmethod
    def send_email_verification(user_email, first_name, verification_token, user_id):
        try:
            frontend_url = EmailService._get_base_url()
            verification_link = f"{frontend_url}/pages/verify-email.html?token={verification_token}&user_id={user_id}"
            subject = "[GIPS College] Verify your email address"
            content = f"""
            <p>Hello {first_name},</p>
            <p>Thank you for registering with GIPS College. To complete your registration, please verify your email address by clicking the button below.</p>
            <p><strong>This link will expire in 24 hours.</strong></p>
            <div class="warning-box">
                <strong>Security tip:</strong> Never share this verification link with anyone else.
            </div>
            """
            button_text = "Verify email"
            button_url = verification_link
            html = EmailService._get_html_template(subject, content, button_text, button_url)
            plain = f"Hello {first_name},\n\nVerify your email using this link (valid for 24 hours): {verification_link}\n\nIf you did not create an account, please ignore this email.\n\nGIPS College"
            msg = Message(subject=subject, recipients=[user_email], html=html, body=plain)
            mail.send(msg)
            return True
        except Exception as e:
            logger.error(f"Email verification error: {e}")
            return False

    # ---------- Admission decision ----------
    @staticmethod
    def send_admission_decision(user_email, first_name, status, program_name=None, message=None):
        try:
            if status.lower() == 'accepted':
                button_text = "Complete registration"
                button_url = f"{EmailService._get_base_url()}/pages/semester-registration.html"
                content_intro = f"<h2>Congratulations, {first_name}!</h2><p>We are pleased to inform you that your application to GIPS College has been <strong style='color:#2c7da0;'>ACCEPTED</strong>.</p>"
            else:
                button_text = "Contact admissions"
                button_url = f"{EmailService._get_base_url()}/pages/contact.html"
                content_intro = f"<h2>Dear {first_name},</h2><p>Thank you for applying to GIPS College. After careful review, we regret to inform you that your application has not been successful at this time.</p>"

            program_info = f"<strong>Program:</strong> {program_name}<br>" if program_name else ""
            message_text = f"<p>{message}</p>" if message else ""

            subject = "[GIPS College] Application status update"
            content = f"""
            {content_intro}
            {program_info}
            {message_text}
            <p>Please log in to your student portal for further details and next steps.</p>
            """
            html = EmailService._get_html_template(subject, content, button_text, button_url)
            plain = f"Dear {first_name},\n\nYour admission decision: {status.upper()}.\n\nPlease log in to your portal for details.\n\nGIPS College"
            msg = Message(subject=subject, recipients=[user_email], html=html, body=plain)
            mail.send(msg)
            return True
        except Exception as e:
            logger.error(f"Admission decision email error: {e}")
            return False