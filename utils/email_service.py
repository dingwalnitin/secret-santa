# utils/email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import render_template, current_app
from models import SystemSettings

# utils/email_service.py (replace send_email method)

class EmailService:
    @staticmethod
    def get_smtp_config():
        settings = SystemSettings.query.first()
        if not settings:
            return None

        return {
            'host': settings.smtp_host,
            'port': settings.smtp_port,
            'user': settings.smtp_user,
            'password': settings.get_smtp_password(),
            'use_tls': settings.smtp_use_tls
        }

    @staticmethod
    def send_email(to_email, subject, html_content, text_content=None):
        config = EmailService.get_smtp_config()
        if not config or not all([config.get('host'), config.get('user'), config.get('password')]):
            current_app.logger.error("SMTP not configured properly")
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = config['user']
            msg['To'] = to_email

            if text_content:
                part1 = MIMEText(text_content, 'plain')
                msg.attach(part1)

            part2 = MIMEText(html_content, 'html')
            msg.attach(part2)

            # Use SMTP_SSL for port 465, otherwise use starttls()
            if config.get('port') == 465:
                server = smtplib.SMTP_SSL(config['host'], config['port'], timeout=10)
                server.ehlo()
            else:
                server = smtplib.SMTP(config['host'], config['port'], timeout=10)
                server.ehlo()
                if config.get('use_tls', True):
                    server.starttls()
                    server.ehlo()

            server.login(config['user'], config['password'])
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            current_app.logger.error(f"Error sending email: {str(e)}")
            return False
    
    @staticmethod
    def send_registration_confirmation(user):
        html_content = render_template('emails/registration_confirmation.html', 
                                      user=user,
                                      budget=current_app.config['GIFT_BUDGET'])
        
        text_content = f"""
        Hi {user.name},
        
        Thank you for registering for Secret Santa!
        
        Your Details:
        - Employee ID: {user.emp_id}
        - Email: {user.email}
        - Gift Preferences: {user.preferences}
        
        You will receive your Secret Santa match when Phase 2 begins. Stay tuned!
        
        Best regards,
        Secret Santa Team
        """
        
        return EmailService.send_email(
            user.email,
            "Secret Santa Registration Confirmed",
            html_content,
            text_content
        )
    
    @staticmethod
    def send_phase2_announcement(user, login_url):
        html_content = render_template('emails/phase2_announcement.html',
                                      user=user,
                                      login_url=login_url)
        
        text_content = f"""
        Hi {user.name},
        
        Exciting news! The Secret Santa assignments are ready!
        
        Login to discover your giftee:
        {login_url}
        
        Use your email ({user.email}) and Employee ID ({user.emp_id}) to login.
        
        Best regards,
        Secret Santa Team
        """
        
        return EmailService.send_email(
            user.email,
            "Your Secret Santa Match is Ready!",
            html_content,
            text_content
        )
    
    @staticmethod
    def send_new_message_notification(user, is_gifter):
        role = "Secret Santa" if is_gifter else "your giftee"
        
        html_content = f"""
        <html>
            <body>
                <h2>New Message!</h2>
                <p>Hi {user.name},</p>
                <p>You have received a new message from {role} in the Secret Santa chat.</p>
                <p><a href="{{{{ url }}}}">Click here to view</a></p>
            </body>
        </html>
        """
        
        text_content = f"""
        Hi {user.name},
        
        You have received a new message from {role} in the Secret Santa chat.
        
        Login to view your messages.
        """
        
        return EmailService.send_email(
            user.email,
            "New Secret Santa Message",
            html_content,
            text_content
        )
