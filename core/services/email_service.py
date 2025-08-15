# email_service.py
import os
import smtplib
from email.mime import text as mime_text
from email.mime import multipart as mime_multipart
from flask import current_app
import logging

# Optional SendGrid import - only used if configured
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
        self.from_email = os.getenv('FROM_EMAIL', 'contact@teacherfy.ai')
        self.frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        
        # SMTP Configuration for free email services
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')  # Use App Password for Gmail
        self.use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'

    def send_job_completion_email(self, to_email, job_id, resource_types, download_url=None, error=None):
        """Send email notification when background job completes"""
        try:
            if error:
                subject = "Resource Generation Failed - Teacherfy.ai"
                content = self._create_error_email_content(job_id, resource_types, error)
            else:
                subject = "Your Resources are Ready! - Teacherfy.ai"
                content = self._create_success_email_content(job_id, resource_types, download_url)

            # Try SendGrid first (if configured)
            if self._is_sendgrid_configured():
                return self._send_via_sendgrid(to_email, subject, content)
            
            # Fall back to SMTP (free option)
            elif self._is_smtp_configured():
                return self._send_via_smtp(to_email, subject, content)
            
            else:
                logger.warning("No email service configured, skipping email notification")
                return False

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def _is_sendgrid_configured(self):
        """Check if SendGrid is configured and available"""
        return (SENDGRID_AVAILABLE and 
                self.sendgrid_api_key and 
                self.sendgrid_api_key != 'your_sendgrid_api_key_here')

    def _is_smtp_configured(self):
        """Check if SMTP is configured"""
        return (self.smtp_username and 
                self.smtp_password and 
                self.smtp_server)

    def _send_via_sendgrid(self, to_email, subject, content):
        """Send email via SendGrid (paid service)"""
        try:
            sg = SendGridAPIClient(api_key=self.sendgrid_api_key)
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject,
                html_content=content
            )
            response = sg.send(message)
            logger.info(f"Email sent via SendGrid to {to_email}, status: {response.status_code}")
            return True
        except Exception as e:
            logger.error(f"SendGrid email failed: {str(e)}")
            return False

    def _send_via_smtp(self, to_email, subject, content):
        """Send email via SMTP (free option with Gmail, Outlook, etc.)"""
        try:
            # Create message
            msg = mime_multipart.MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # Add HTML content
            html_part = mime_text.MIMEText(content, 'html')
            msg.attach(html_part)
            
            # Connect to server and send
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()
            
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent via SMTP to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"SMTP email failed: {str(e)}")
            return False

    def _create_success_email_content(self, job_id, resource_types, download_url):
        """Create HTML email content for successful job completion"""
        resources_text = ", ".join(resource_types) if isinstance(resource_types, list) else str(resource_types)

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Resources Ready - Teacherfy.ai</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; color: white; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0; font-size: 28px;">🎉 Your Resources are Ready!</h1>
            </div>
            
            <div style="background: white; padding: 30px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 10px 10px;">
                <p style="font-size: 18px; margin-bottom: 20px;">Great news! Your AI-generated educational resources have been created successfully.</p>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #495057; margin-top: 0;">Generated Resources:</h3>
                    <p style="font-size: 16px; margin: 5px 0;"><strong>{resources_text}</strong></p>
                    <p style="font-size: 14px; color: #6c757d; margin: 5px 0;">Job ID: {job_id}</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{self.frontend_url}" 
                       style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block; font-size: 16px;">
                        View Your Resources
                    </a>
                </div>
                
                <p style="color: #6c757d; font-size: 14px; margin-top: 30px;">
                    Your resources are ready for download in your Teacherfy.ai dashboard. If you have any questions, please don't hesitate to contact our support team.
                </p>
            </div>
            
            <div style="text-align: center; padding: 20px; color: #6c757d; font-size: 12px;">
                <p>© 2024 Teacherfy.ai - AI-Powered Educational Resources</p>
            </div>
        </body>
        </html>
        """

    def _create_error_email_content(self, job_id, resource_types, error):
        """Create HTML email content for failed job"""
        resources_text = ", ".join(resource_types) if isinstance(resource_types, list) else str(resource_types)

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Resource Generation Issue - Teacherfy.ai</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: #dc3545; padding: 30px; text-align: center; color: white; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0; font-size: 28px;">⚠️ Resource Generation Issue</h1>
            </div>
            
            <div style="background: white; padding: 30px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 10px 10px;">
                <p style="font-size: 18px; margin-bottom: 20px;">We encountered an issue while generating your educational resources.</p>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #495057; margin-top: 0;">Requested Resources:</h3>
                    <p style="font-size: 16px; margin: 5px 0;"><strong>{resources_text}</strong></p>
                    <p style="font-size: 14px; color: #6c757d; margin: 5px 0;">Job ID: {job_id}</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{self.frontend_url}" 
                       style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; font-weight: bold; display: inline-block; font-size: 16px;">
                        Try Again
                    </a>
                </div>
                
                <p style="color: #6c757d; font-size: 14px; margin-top: 30px;">
                    Please try generating your resources again. If the issue persists, our support team has been notified and will assist you shortly.
                </p>
            </div>
            
            <div style="text-align: center; padding: 20px; color: #6c757d; font-size: 12px;">
                <p>© 2024 Teacherfy.ai - AI-Powered Educational Resources</p>
            </div>
        </body>
        </html>
        """

# Initialize email service
email_service = EmailService()