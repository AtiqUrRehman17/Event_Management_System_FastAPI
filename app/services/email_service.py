import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging
from app.core.config import settings
from datetime import datetime
logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP or Postmark API"""

    @staticmethod
    def send_email(
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email using configured provider.
        Returns True if successful, False otherwise.
        """
        if settings.EMAIL_PROVIDER == "postmark":
            return EmailService._send_via_postmark(to_email, subject, html_content, text_content)
        else:
            return EmailService._send_via_smtp(to_email, subject, html_content, text_content)

    @staticmethod
    def _send_via_smtp(
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email via SMTP (Gmail, etc.)"""
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.DEFAULT_FROM_EMAIL
            msg["To"] = to_email

            # Add plain text version (fallback)
            if text_content:
                part_text = MIMEText(text_content, "plain")
                msg.attach(part_text)

            # Add HTML version
            part_html = MIMEText(html_content, "html")
            msg.attach(part_html)

            # Connect to SMTP server
            if settings.EMAIL_USE_TLS:
                server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT)

            # Login
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)

            # Send email
            server.send_message(msg)
            server.quit()

            logger.info(f"Email sent successfully via SMTP to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email via SMTP to {to_email}: {str(e)}")
            return False

    @staticmethod
    def _send_via_postmark(
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email via Postmark API"""
        try:
            url = "https://api.postmarkapp.com/email"
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Postmark-Server-Token": settings.POSTMARK_API_TOKEN
            }
            
            payload = {
                "From": settings.DEFAULT_FROM_EMAIL,
                "To": to_email,
                "Subject": subject,
                "HtmlBody": html_content,
                "TextBody": text_content or html_content,
                "MessageStream": "outbound"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                logger.info(f"Email sent successfully via Postmark to {to_email}")
                return True
            else:
                logger.error(f"Postmark API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email via Postmark to {to_email}: {str(e)}")
            return False

    # ==================== VERIFICATION EMAILS ====================

    @staticmethod
    def send_verification_email(to_email: str, username: str, verification_token: str) -> bool:
        """Send email verification link to user"""
        api_verify_endpoint = "/api/v1/auth/verify-email"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #2196F3;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border: 1px solid #ddd;
                    border-top: none;
                    border-radius: 0 0 5px 5px;
                }}
                .token-box {{
                    background-color: #f0f0f0;
                    padding: 15px;
                    border-radius: 5px;
                    font-family: monospace;
                    font-size: 16px;
                    word-break: break-all;
                    margin: 20px 0;
                    border-left: 4px solid #2196F3;
                }}
                .footer {{
                    margin-top: 20px;
                    font-size: 12px;
                    color: #777;
                    text-align: center;
                }}
                .warning {{
                    color: #e74c3c;
                    font-size: 14px;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Welcome to Event Management System!</h2>
            </div>
            <div class="content">
                <p>Hello <strong>{username}</strong>,</p>
                <p>Thank you for registering with Event Management System. Please verify your email address to activate your account.</p>
                <p>Use the token below to verify your email:</p>
                <div class="token-box">
                    <strong>Verification Token:</strong> {verification_token}
                </div>
                <p>To verify your email, make a POST request to:</p>
                <div class="token-box">
                    <strong>API Endpoint:</strong> {api_verify_endpoint}<br>
                    <strong>Request Body:</strong><br>
                    {{<br>
                    &nbsp;&nbsp;"token": "{verification_token}"<br>
                    }}
                </div>
                <p class="warning"><strong>⚠️ This verification token will expire in {settings.VERIFICATION_TOKEN_EXPIRE_MINUTES} minutes ({int(settings.VERIFICATION_TOKEN_EXPIRE_MINUTES / 60)} hours).</strong></p>
                <p>If you didn't create an account with us, please ignore this email.</p>
                <hr>
                <p>Once verified, you'll have full access to all features including booking events and managing your profile.</p>
            </div>
            <div class="footer">
                <p>Event Management System &copy; 2024 | Email Verification</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Welcome to Event Management System!

        Hello {username},

        Thank you for registering. Please verify your email address to activate your account.

        Use the token below to verify your email:

        Verification Token: {verification_token}

        To verify your email, make a POST request to:
        API Endpoint: {api_verify_endpoint}
        Request Body: {{"token": "{verification_token}"}}

        This verification token will expire in {settings.VERIFICATION_TOKEN_EXPIRE_MINUTES} minutes ({int(settings.VERIFICATION_TOKEN_EXPIRE_MINUTES / 60)} hours).

        If you didn't create an account with us, please ignore this email.

        Event Management System
        """

        return EmailService.send_email(
            to_email=to_email,
            subject="Verify Your Email - Event Management System",
            html_content=html_content,
            text_content=text_content
        )

    @staticmethod
    def send_verification_confirmation(to_email: str, username: str) -> bool:
        """Send confirmation email after successful email verification"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border: 1px solid #ddd;
                    border-top: none;
                    border-radius: 0 0 5px 5px;
                }}
                .footer {{
                    margin-top: 20px;
                    font-size: 12px;
                    color: #777;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Email Verified Successfully!</h2>
            </div>
            <div class="content">
                <p>Hello <strong>{username}</strong>,</p>
                <p>Your email address has been successfully verified.</p>
                <p>You can now:</p>
                <ul>
                    <li>Login to your account</li>
                    <li>Browse and book events</li>
                    <li>Manage your profile</li>
                    <li>View your booking history</li>
                </ul>
                <p>Thank you for joining Event Management System!</p>
            </div>
            <div class="footer">
                <p>Event Management System &copy; 2024 | Email Verified</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Email Verified Successfully!

        Hello {username},

        Your email address has been successfully verified.

        You can now login to your account and start using all features of Event Management System.

        Thank you for joining!

        Event Management System
        """

        return EmailService.send_email(
            to_email=to_email,
            subject="Email Verified Successfully - Event Management System",
            html_content=html_content,
            text_content=text_content
        )

    # ==================== PASSWORD RESET EMAILS ====================

    @staticmethod
    def send_password_reset_email(to_email: str, username: str, reset_token: str) -> bool:
        """Send password reset email with reset token"""
        api_reset_endpoint = "/api/v1/auth/reset-password"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border: 1px solid #ddd;
                    border-top: none;
                    border-radius: 0 0 5px 5px;
                }}
                .token-box {{
                    background-color: #f0f0f0;
                    padding: 15px;
                    border-radius: 5px;
                    font-family: monospace;
                    font-size: 16px;
                    word-break: break-all;
                    margin: 20px 0;
                    border-left: 4px solid #4CAF50;
                }}
                .footer {{
                    margin-top: 20px;
                    font-size: 12px;
                    color: #777;
                    text-align: center;
                }}
                .warning {{
                    color: #e74c3c;
                    font-size: 14px;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Password Reset Request</h2>
            </div>
            <div class="content">
                <p>Hello <strong>{username}</strong>,</p>
                <p>We received a request to reset your password.</p>
                <div class="token-box">
                    <strong>Reset Token:</strong> {reset_token}
                </div>
                <p>To reset your password, make a POST request to:</p>
                <code>POST {api_reset_endpoint}</code>
                <p>With JSON body:</p>
                <code>{{"token": "{reset_token}", "new_password": "your_new_password", "confirm_password": "your_new_password"}}</code>
                <p class="warning"><strong>⚠️ This token will expire in {settings.RESET_TOKEN_EXPIRE_MINUTES} minutes.</strong></p>
                <p>If you didn't request this password reset, please ignore this email.</p>
            </div>
            <div class="footer">
                <p>Event Management System &copy; 2024 | Password Reset</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Password Reset Request

        Hello {username},

        We received a request to reset your password.

        Your Reset Token: {reset_token}

        To reset your password, make a POST request to:
        API Endpoint: {api_reset_endpoint}
        
        Request Body:
        {{
            "token": "{reset_token}",
            "new_password": "your_new_password",
            "confirm_password": "your_new_password"
        }}

        This token will expire in {settings.RESET_TOKEN_EXPIRE_MINUTES} minutes.

        If you didn't request this password reset, please ignore this email.

        Event Management System
        """

        return EmailService.send_email(
            to_email=to_email,
            subject="Password Reset Request - Event Management System",
            html_content=html_content,
            text_content=text_content
        )

    @staticmethod
    def send_password_reset_confirmation(to_email: str, username: str) -> bool:
        """Send confirmation email after successful password reset"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border: 1px solid #ddd;
                    border-top: none;
                    border-radius: 0 0 5px 5px;
                }}
                .footer {{
                    margin-top: 20px;
                    font-size: 12px;
                    color: #777;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Password Changed Successfully</h2>
            </div>
            <div class="content">
                <p>Hello <strong>{username}</strong>,</p>
                <p>Your password has been successfully changed.</p>
                <p>If you made this change, you can now log in with your new password.</p>
                <p><strong>If you did not change your password:</strong></p>
                <p>Please contact our support team immediately.</p>
            </div>
            <div class="footer">
                <p>Event Management System &copy; 2024 | Password Changed</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Password Changed Successfully

        Hello {username},

        Your password has been successfully changed.

        If you made this change, you can now log in with your new password.

        If you did not change your password, please contact our support team immediately.

        Event Management System
        """

        return EmailService.send_email(
            to_email=to_email,
            subject="Password Changed Successfully - Event Management System",
            html_content=html_content,
            text_content=text_content
        )

    # ==================== WAITLIST EMAILS ====================

    @staticmethod
    def send_waitlist_joined_email(to_email: str, username: str, event_title: str, position: int) -> bool:
        """Send confirmation email when user joins waitlist"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: #f39c12;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    padding: 30px;
                    background: #f9f9f9;
                    border: 1px solid #ddd;
                    border-top: none;
                    border-radius: 0 0 5px 5px;
                }}
                .position {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #f39c12;
                }}
                .footer {{
                    margin-top: 20px;
                    font-size: 12px;
                    color: #777;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Waitlist Confirmation</h2>
                </div>
                <div class="content">
                    <p>Hello <strong>{username}</strong>,</p>
                    <p>You have been added to the waitlist for:</p>
                    <h3>{event_title}</h3>
                    <p>Your current position in line is: <span class="position">#{position}</span></p>
                    <p>You will receive an email notification when a spot becomes available. You will have 48 hours to confirm your spot.</p>
                    <p>Thank you for your patience!</p>
                </div>
                <div class="footer">
                    <p>Event Management System &copy; 2024 | Waitlist</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Waitlist Confirmation
        
        Hello {username},
        
        You have been added to the waitlist for: {event_title}
        
        Your current position in line is: #{position}
        
        You will receive an email notification when a spot becomes available. You will have 48 hours to confirm your spot.
        
        Thank you for your patience!
        """

        return EmailService.send_email(
            to_email=to_email,
            subject=f"Waitlist Confirmation - {event_title}",
            html_content=html_content,
            text_content=text_content
        )

    @staticmethod
    def send_waitlist_notification_email(
        to_email: str, 
        username: str, 
        event_title: str, 
        event_id: int, 
        expires_at: datetime
    ) -> bool:
        """Send notification when a spot becomes available"""
        expires_str = expires_at.strftime("%B %d, %Y at %I:%M %p")
        confirm_url = f"/api/v1/waitlist/{event_id}/confirm"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: #2ecc71;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    padding: 30px;
                    background: #f9f9f9;
                    border: 1px solid #ddd;
                    border-top: none;
                    border-radius: 0 0 5px 5px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background: #3498db;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .warning {{
                    color: #e74c3c;
                }}
                .footer {{
                    margin-top: 20px;
                    font-size: 12px;
                    color: #777;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>A Spot Has Opened Up! 🎉</h2>
                </div>
                <div class="content">
                    <p>Hello <strong>{username}</strong>,</p>
                    <p>Good news! A spot has become available for:</p>
                    <h3>{event_title}</h3>
                    <p>You have been selected from the waitlist to claim this spot.</p>
                    <p><strong>You must confirm your interest within 48 hours.</strong></p>
                    <p>Expires: <strong>{expires_str}</strong></p>
                    <div style="text-align: center;">
                        <a href="{confirm_url}" class="button">Confirm My Spot</a>
                    </div>
                    <p class="warning">If you don't confirm within 48 hours, this spot will be offered to the next person in line.</p>
                    <p>To claim your spot, click the button above or visit your dashboard.</p>
                </div>
                <div class="footer">
                    <p>Event Management System &copy; 2024 | Waitlist Notification</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        A Spot Has Opened Up!
        
        Hello {username},
        
        Good news! A spot has become available for: {event_title}
        
        You have been selected from the waitlist to claim this spot.
        
        You must confirm your interest within 48 hours.
        
        Expires: {expires_str}
        
        To confirm your spot, visit: {confirm_url}
        
        If you don't confirm within 48 hours, this spot will be offered to the next person in line.
        """

        return EmailService.send_email(
            to_email=to_email,
            subject=f"Spot Available! - {event_title}",
            html_content=html_content,
            text_content=text_content
        )

    # ==================== BOOKING CONFIRMATION EMAILS ====================

    @staticmethod
    def send_booking_confirmation_email(to_email: str, username: str, event_title: str, booking_id: int, seats: int, total_price: float) -> bool:
        """Send booking confirmation email"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: #3498db;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    padding: 30px;
                    background: #f9f9f9;
                    border: 1px solid #ddd;
                    border-top: none;
                    border-radius: 0 0 5px 5px;
                }}
                .details {{
                    background: white;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 15px 0;
                }}
                .footer {{
                    margin-top: 20px;
                    font-size: 12px;
                    color: #777;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Booking Confirmation!</h2>
                </div>
                <div class="content">
                    <p>Hello <strong>{username}</strong>,</p>
                    <p>Your booking has been confirmed for:</p>
                    <h3>{event_title}</h3>
                    <div class="details">
                        <p><strong>Booking ID:</strong> #{booking_id}</p>
                        <p><strong>Number of Seats:</strong> {seats}</p>
                        <p><strong>Total Paid:</strong> ${total_price:.2f}</p>
                    </div>
                    <p>Thank you for booking with us!</p>
                </div>
                <div class="footer">
                    <p>Event Management System &copy; 2024 | Booking Confirmation</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Booking Confirmation!
        
        Hello {username},
        
        Your booking has been confirmed for: {event_title}
        
        Booking ID: #{booking_id}
        Number of Seats: {seats}
        Total Paid: ${total_price:.2f}
        
        Thank you for booking with us!
        """

        return EmailService.send_email(
            to_email=to_email,
            subject=f"Booking Confirmed - {event_title}",
            html_content=html_content,
            text_content=text_content
        )