# utils/email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import render_template, current_app
from models import SystemSettings
import os

class EmailService:

    @staticmethod
    def get_smtp_config():
        return {
            'host': 'smtp-relay.brevo.com',
            'port': 587,
            'user': '7e896a001@smtp-brevo.com',
            'password': 'bskzHcT50rOLL8O',
            'use_tls': True
        }

    @staticmethod
    def send_email(to_email, subject, html_content, text_content=None):
        config = EmailService.get_smtp_config()

        if not config or not all([config.get('host'), config.get('user'), config.get('password')]):
            current_app.logger.error("SMTP not configured properly.")
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

            server = None
            try:
                if config.get('port') == 465:
                    current_app.logger.info(f"Connecting to {config['host']}:465 with SSL")
                    server = smtplib.SMTP_SSL(config['host'], 465, timeout=30)
                else:
                    current_app.logger.info(f"Connecting to {config['host']}:{config['port']} with STARTTLS")
                    server = smtplib.SMTP(config['host'], config['port'], timeout=30)
                    server.ehlo()
                    if config.get('use_tls', True):
                        server.starttls()
                        server.ehlo()

                current_app.logger.info(f"Logging in as {config['user']}")
                server.login(config['user'], config['password'])

                current_app.logger.info(f"Sending email to {to_email}")
                server.send_message(msg)
                server.quit()

                current_app.logger.info(f"Email sent successfully to {to_email}")
                return True

            except smtplib.SMTPAuthenticationError as e:
                current_app.logger.error(f"SMTP Authentication failed: {str(e)}")
                return False
            except smtplib.SMTPException as e:
                current_app.logger.error(f"SMTP error: {str(e)}")
                return False
            finally:
                if server:
                    try:
                        server.quit()
                    except:
                        pass

        except Exception as e:
            current_app.logger.error(f"Error sending email: {str(e)}")
            import traceback
            current_app.logger.error(traceback.format_exc())
            return False

    @staticmethod
    def send_registration_confirmation(user):
        html_content = render_template(
            'emails/registration_confirmation.html',
            user=user,
            budget=current_app.config['GIFT_BUDGET']
        )

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
        html_content = render_template(
            'emails/phase2_announcement.html',
            user=user,
            login_url=login_url
        )

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
