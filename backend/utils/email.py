from flask import render_template_string, current_app
from flask_mail import Mail, Message
from datetime import datetime
import secrets
import os
import logging

logger = logging.getLogger(__name__)

mail = Mail()

class EmailService:
    """Handle email notifications for GIPS College Student Management System"""
    
    # ==================== UTILITY METHODS ====================
    
    @staticmethod
    def generate_verification_token():
        """Generate a secure verification token"""
        return secrets.token_urlsafe(32)
    
    
    # ==================== EXISTING EMAIL METHODS (ENHANCED) ====================
    
    @staticmethod
    def send_registration_confirmation(user_email, first_name, student_number, program_name=None, campus_name=None):
        """Send registration confirmation email - ENHANCED VERSION"""
        try:
            subject = "[GIPS College] Welcome to Student Portal - Registration Confirmation"
            
            program_info = f"<p><strong>Program:</strong> {program_name}</p>" if program_name else ""
            campus_info = f"<p><strong>Campus:</strong> {campus_name}</p>" if campus_name else ""
            
            body = f"""
            <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #003366; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                        .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                        .footer {{ background-color: #f0f0f0; padding: 15px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 5px 5px; }}
                        .info-box {{ background-color: #e7f3ff; padding: 15px; border-left: 4px solid #2196F3; margin: 15px 0; }}
                        .button {{ background-color: #003366; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 10px 0; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>🎓 Welcome to GIPS College Student Portal</h1>
                            <p>Registration Confirmation</p>
                        </div>
                        
                        <div class="content">
                            <h2>Hello {first_name},</h2>
                            
                            <p>Thank you for registering with GIPS College! Your registration has been successful.</p>
                            
                            <div class="info-box">
                                <strong>📋 Your Registration Details:</strong><br>
                                <strong>Student Number:</strong> {student_number}<br>
                                {program_info}
                                {campus_info}
                                <strong>Registration Date:</strong> {datetime.now().strftime('%d %B %Y at %H:%M')}
                            </div>
                            
                            <h3>Next Steps:</h3>
                            <ol>
                                <li>Log in to the portal with your email and password</li>
                                <li>Complete your profile information</li>
                                <li>Upload required documents</li>
                                <li>Wait for admission approval</li>
                            </ol>
                            
                            <p>You can now log in to the portal using your email and password.</p>
                            
                            <p>Best regards,<br><strong>GIPS College Administration</strong></p>
                        </div>
                        
                        <div class="footer">
                            <p>&copy; 2026 GIPS College. All rights reserved.</p>
                            <p>Contact: admissions@gipscollege.edu.bw | +267 712 345 683</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            msg = Message(subject=subject, recipients=[user_email], html=body)
            mail.send(msg)
            logger.info(f"Registration confirmation email sent to {user_email}")
            return True
        except Exception as e:
            logger.error(f"Error sending registration confirmation email: {str(e)}")
            print(f"Error sending email: {str(e)}")
            return False
    
    
    @staticmethod
    def send_assignment_submission_confirmation(user_email, first_name, assignment_title):
        """Send assignment submission confirmation"""
        try:
            subject = f"[GIPS College] Assignment Submitted - {assignment_title}"
            
            body = f"""
            <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #003366; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                        .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                        .footer {{ background-color: #f0f0f0; padding: 15px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 5px 5px; }}
                        .info-box {{ background-color: #e7f3ff; padding: 15px; border-left: 4px solid #2196F3; margin: 15px 0; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>✅ Assignment Submission Confirmation</h2>
                        </div>
                        
                        <div class="content">
                            <p>Dear {first_name},</p>
                            <p>Your assignment <strong>{assignment_title}</strong> has been submitted successfully.</p>
                            
                            <div class="info-box">
                                <strong>📝 Submission Details:</strong><br>
                                <strong>Assignment:</strong> {assignment_title}<br>
                                <strong>Submission Time:</strong> {datetime.now().strftime('%d %B %Y at %H:%M')}
                            </div>
                            
                            <p>You will receive feedback from your instructor shortly.</p>
                            <p>Best regards,<br><strong>GIPS College Administration</strong></p>
                        </div>
                        
                        <div class="footer">
                            <p>&copy; 2026 GIPS College. All rights reserved.</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            msg = Message(subject=subject, recipients=[user_email], html=body)
            mail.send(msg)
            logger.info(f"Assignment submission confirmation email sent to {user_email}")
            return True
        except Exception as e:
            logger.error(f"Error sending assignment submission email: {str(e)}")
            print(f"Error sending email: {str(e)}")
            return False
    
    
    @staticmethod
    def send_exam_registration_confirmation(user_email, first_name, course_name, exam_type, fee):
        """Send exam registration confirmation"""
        try:
            subject = f"[GIPS College] {exam_type.title()} Exam Registration - {course_name}"
            
            body = f"""
            <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #003366; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                        .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                        .footer {{ background-color: #f0f0f0; padding: 15px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 5px 5px; }}
                        .info-box {{ background-color: #e7f3ff; padding: 15px; border-left: 4px solid #2196F3; margin: 15px 0; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>📝 Exam Registration Confirmation</h2>
                        </div>
                        
                        <div class="content">
                            <p>Dear {first_name},</p>
                            <p>You have successfully registered for a {exam_type} exam.</p>
                            
                            <div class="info-box">
                                <strong>📋 Exam Details:</strong><br>
                                <strong>Course:</strong> {course_name}<br>
                                <strong>Exam Type:</strong> {exam_type.title()}<br>
                                <strong>Fee:</strong> P {fee}
                            </div>
                            
                            <p>Please proceed to make payment through the portal if required.</p>
                            <p>Best regards,<br><strong>GIPS College Administration</strong></p>
                        </div>
                        
                        <div class="footer">
                            <p>&copy; 2026 GIPS College. All rights reserved.</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            msg = Message(subject=subject, recipients=[user_email], html=body)
            mail.send(msg)
            logger.info(f"Exam registration confirmation email sent to {user_email}")
            return True
        except Exception as e:
            logger.error(f"Error sending exam registration email: {str(e)}")
            print(f"Error sending email: {str(e)}")
            return False
    
    
    @staticmethod
    def send_payment_confirmation(user_email, first_name, amount, payment_type, receipt_number=None):
        """Send payment confirmation - ENHANCED VERSION"""
        try:
            subject = f"[GIPS College] Payment Confirmation - P {amount}"
            
            receipt_info = f"<p><strong>Receipt Number:</strong> {receipt_number}</p>" if receipt_number else ""
            
            body = f"""
            <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #28a745; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                        .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                        .footer {{ background-color: #f0f0f0; padding: 15px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 5px 5px; }}
                        .info-box {{ background-color: #e7f3ff; padding: 15px; border-left: 4px solid #2196F3; margin: 15px 0; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>💳 Payment Confirmation</h2>
                        </div>
                        
                        <div class="content">
                            <p>Dear {first_name},</p>
                            <p>Your payment has been processed successfully.</p>
                            
                            <div class="info-box">
                                <strong>💰 Payment Details:</strong><br>
                                <strong>Amount:</strong> P {amount}<br>
                                <strong>Payment Type:</strong> {payment_type.replace('_', ' ').title()}<br>
                                {receipt_info}
                                <strong>Payment Date:</strong> {datetime.now().strftime('%d %B %Y at %H:%M')}
                            </div>
                            
                            <p>Thank you for your payment. Please keep this receipt for your records.</p>
                            <p>Best regards,<br><strong>GIPS College Administration</strong></p>
                        </div>
                        
                        <div class="footer">
                            <p>&copy; 2026 GIPS College. All rights reserved.</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            msg = Message(subject=subject, recipients=[user_email], html=body)
            mail.send(msg)
            logger.info(f"Payment confirmation email sent to {user_email}")
            return True
        except Exception as e:
            logger.error(f"Error sending payment confirmation email: {str(e)}")
            print(f"Error sending email: {str(e)}")
            return False
    
    
    @staticmethod
    def send_accommodation_confirmation(user_email, first_name, accommodation_name, price):
        """Send accommodation registration confirmation"""
        try:
            subject = f"[GIPS College] Accommodation Registration - {accommodation_name}"
            
            body = f"""
            <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #003366; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                        .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                        .footer {{ background-color: #f0f0f0; padding: 15px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 5px 5px; }}
                        .info-box {{ background-color: #e7f3ff; padding: 15px; border-left: 4px solid #2196F3; margin: 15px 0; }}
                        .highlight {{ background-color: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; margin: 15px 0; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>🏠 Accommodation Registration Confirmation</h2>
                        </div>
                        
                        <div class="content">
                            <p>Dear {first_name},</p>
                            <p>Your accommodation request has been received.</p>
                            
                            <div class="info-box">
                                <strong>🏢 Accommodation Details:</strong><br>
                                <strong>Accommodation:</strong> {accommodation_name}<br>
                                <strong>Price per Semester:</strong> P {price}<br>
                                <strong>Request Date:</strong> {datetime.now().strftime('%d %B %Y')}
                            </div>
                            
                            <div class="highlight">
                                <strong>⏳ Status:</strong> Your request is pending approval. You will receive an update within 5-7 business days.
                            </div>
                            
                            <p>Best regards,<br><strong>GIPS College Administration</strong></p>
                        </div>
                        
                        <div class="footer">
                            <p>&copy; 2026 GIPS College. All rights reserved.</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            msg = Message(subject=subject, recipients=[user_email], html=body)
            mail.send(msg)
            logger.info(f"Accommodation confirmation email sent to {user_email}")
            return True
        except Exception as e:
            logger.error(f"Error sending accommodation confirmation email: {str(e)}")
            print(f"Error sending email: {str(e)}")
            return False
    
    
    # ==================== NEW EMAIL METHODS ====================
    
    @staticmethod
    def send_password_reset(user_email, first_name, reset_token, user_id):
        """Send password reset link email"""
        try:
            frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:5000')
            reset_link = f"{frontend_url}/pages/reset-password.html?token={reset_token}&user_id={user_id}"
            
            subject = "[GIPS College] 🔐 Password Reset Request"
            
            body = f"""
            <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #dc3545; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                        .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                        .footer {{ background-color: #f0f0f0; padding: 15px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 5px 5px; }}
                        .button {{ background-color: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 20px 0; font-weight: bold; }}
                        .warning {{ background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 15px 0; }}
                        .code {{ background-color: #f0f0f0; padding: 10px; border-radius: 4px; font-family: monospace; font-size: 12px; word-break: break-all; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>🔐 Password Reset Request</h1>
                        </div>
                        
                        <div class="content">
                            <p>Hello {first_name},</p>
                            
                            <p>We received a request to reset your password. If you made this request, click the button below to create a new password:</p>
                            
                            <center>
                                <a href="{reset_link}" class="button">🔑 Reset My Password</a>
                            </center>
                            
                            <p><strong>Or copy and paste this link in your browser:</strong></p>
                            <div class="code">{reset_link}</div>
                            
                            <div class="warning">
                                <strong>⚠️ Important:</strong> This password reset link will expire in 1 hour. If you did not request a password reset, please ignore this email and your password will remain unchanged.
                            </div>
                            
                            <h3>For Your Security:</h3>
                            <ul>
                                <li>Never share this link with anyone</li>
                                <li>GIPS College staff will never ask for your password via email</li>
                                <li>If you did not request this reset, your account may be compromised. Contact IT support immediately</li>
                            </ul>
                            
                            <p>
                                <strong>IT Support:</strong> it@gipscollege.edu.bw<br>
                                <strong>Phone:</strong> +267 712 345 678
                            </p>
                            
                            <p>Best regards,<br><strong>GIPS College Administration</strong></p>
                        </div>
                        
                        <div class="footer">
                            <p>&copy; 2026 GIPS College. All rights reserved.</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            msg = Message(subject=subject, recipients=[user_email], html=body)
            mail.send(msg)
            logger.info(f"Password reset email sent to {user_email}")
            return True
        except Exception as e:
            logger.error(f"Error sending password reset email: {str(e)}")
            print(f"Error sending email: {str(e)}")
            return False
    
    
    @staticmethod
    def send_email_verification(user_email, first_name, verification_token, user_id):
        """Send email verification link"""
        try:
            frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:5000')
            verification_link = f"{frontend_url}/pages/verify-email.html?token={verification_token}&user_id={user_id}"
            
            subject = "[GIPS College] 📧 Verify Your Email Address"
            
            body = f"""
            <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #17a2b8; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                        .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                        .footer {{ background-color: #f0f0f0; padding: 15px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 5px 5px; }}
                        .button {{ background-color: #17a2b8; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 20px 0; font-weight: bold; }}
                        .highlight {{ background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 15px 0; }}
                        .code {{ background-color: #f0f0f0; padding: 10px; border-radius: 4px; font-family: monospace; font-size: 12px; word-break: break-all; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>✉️ Email Verification Required</h1>
                        </div>
                        
                        <div class="content">
                            <p>Hello {first_name},</p>
                            
                            <p>Thank you for registering with GIPS College! To complete your registration and verify your email address, please click the button below:</p>
                            
                            <center>
                                <a href="{verification_link}" class="button">✓ Verify My Email</a>
                            </center>
                            
                            <p><strong>Or copy and paste this link in your browser:</strong></p>
                            <div class="code">{verification_link}</div>
                            
                            <div class="highlight">
                                <strong>⏱️ Note:</strong> This verification link will expire in 24 hours. If you did not create this account, please ignore this email.
                            </div>
                            
                            <h3>Security Tip:</h3>
                            <p>Never share this verification link with anyone else. GIPS College staff will never ask for this link via email.</p>
                            
                            <p>Best regards,<br><strong>GIPS College Administration</strong></p>
                        </div>
                        
                        <div class="footer">
                            <p>&copy; 2026 GIPS College. All rights reserved.</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            msg = Message(subject=subject, recipients=[user_email], html=body)
            mail.send(msg)
            logger.info(f"Email verification link sent to {user_email}")
            return True
        except Exception as e:
            logger.error(f"Error sending email verification: {str(e)}")
            print(f"Error sending email: {str(e)}")
            return False
    
    
    @staticmethod
    def send_admission_decision(user_email, first_name, status, program_name=None, message=None):
        """Send admission decision (acceptance/rejection)"""
        try:
            if status.lower() == 'accepted':
                subject = "[GIPS College] 🎉 Congratulations! Your Application Has Been Accepted"
                header_color = "#28a745"
                emoji = "✅"
                status_text = "ACCEPTED"
            else:
                subject = "[GIPS College] 📋 Application Status Update"
                header_color = "#6c757d"
                emoji = "📋"
                status_text = "UNDER REVIEW / REJECTED"
            
            frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:5000')
            program_info = f"<p><strong>Program:</strong> {program_name}</p>" if program_name else ""
            message_text = f"<p>{message}</p>" if message else ""
            
            body = f"""
            <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: {header_color}; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                        .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                        .footer {{ background-color: #f0f0f0; padding: 15px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 5px 5px; }}
                        .button {{ background-color: {header_color}; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 20px 0; font-weight: bold; }}
                        .info-box {{ background-color: #e7f3ff; padding: 15px; border-left: 4px solid #2196F3; margin: 15px 0; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>{emoji} Application Status</h1>
                        </div>
                        
                        <div class="content">
                            <p>Dear {first_name},</p>
                            
                            <div class="info-box">
                                <strong>📌 Application Status:</strong> {status_text}<br>
                                {program_info}
                                <strong>Decision Date:</strong> {datetime.now().strftime('%d %B %Y')}
                            </div>
                            
                            {message_text}
                            
                            <p>Log in to your student portal to view detailed information and proceed with next steps.</p>
                            
                            <center>
                                <a href="{frontend_url}/pages/login.html" class="button">📱 Go to Portal</a>
                            </center>
                            
                            <h3>Need Help?</h3>
                            <p>
                                <strong>Admissions Office:</strong> admissions@gipscollege.edu.bw<br>
                                <strong>Phone:</strong> +267 712 345 683<br>
                                <strong>Office Hours:</strong> Monday - Friday, 08:00 - 17:00
                            </p>
                            
                            <p>Best regards,<br><strong>GIPS College Administration</strong></p>
                        </div>
                        
                        <div class="footer">
                            <p>&copy; 2026 GIPS College. All rights reserved.</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            msg = Message(subject=subject, recipients=[user_email], html=body)
            mail.send(msg)
            logger.info(f"Admission decision email sent to {user_email}")
            return True
        except Exception as e:
            logger.error(f"Error sending admission decision email: {str(e)}")
            print(f"Error sending email: {str(e)}")
            return False