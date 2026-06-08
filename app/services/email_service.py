import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging
from app.core.config import settings

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
            # Use Postmark API (more reliable than SMTP)
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

    @staticmethod
    def send_password_reset_email(to_email: str, username: str, reset_token: str) -> bool:
        """
        Send password reset email with reset token
        """
        api_reset_endpoint = "/api/v1/auth/reset-password"

        # HTML email template (same as before)
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
                <p>We received a request to reset your password for your Event Management System account.</p>
                <p>Use the token below to reset your password:</p>
                <div class="token-box">
                    <strong>Reset Token:</strong> {reset_token}
                </div>
                <p>To reset your password, make a POST request to:</p>
                <div class="token-box">
                    <strong>API Endpoint:</strong> {api_reset_endpoint}<br>
                    <strong>Request Body:</strong><br>
                    {{<br>
                    &nbsp;&nbsp;"token": "{reset_token}",<br>
                    &nbsp;&nbsp;"new_password": "your_new_password",<br>
                    &nbsp;&nbsp;"confirm_password": "your_new_password"<br>
                    }}
                </div>
                <p class="warning"><strong>⚠️ This token will expire in {settings.RESET_TOKEN_EXPIRE_MINUTES} minutes.</strong></p>
                <p>If you didn't request this password reset, please ignore this email. Your password will remain unchanged.</p>
                <hr>
                <p>For security reasons, never share this token with anyone.</p>
            </div>
            <div class="footer">
                <p>Event Management System &copy; 2024 | Secure Password Reset</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Password Reset Request

        Hello {username},

        We received a request to reset your password for your Event Management System account.

        Use the token below to reset your password:

        Reset Token: {reset_token}

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
        """
        Send confirmation email after successful password reset
        """
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
                <p>Please contact our support team immediately to secure your account.</p>
                <hr>
                <p>For security reasons, we recommend:</p>
                <ul>
                    <li>Use a strong, unique password</li>
                    <li>Never share your password with anyone</li>
                    <li>Enable two-factor authentication if available</li>
                </ul>
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