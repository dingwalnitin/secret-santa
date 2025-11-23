#!/usr/bin/env python
"""
Test script to verify SMTP configuration and email sending.
This script can be run independently to test SMTP settings.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_smtp_config():
    """Test SMTP configuration from environment variables"""
    print("=" * 60)
    print("SMTP Configuration Test")
    print("=" * 60)
    
    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = os.environ.get('SMTP_PORT', '587')
    smtp_user = os.environ.get('SMTP_USER')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    smtp_use_tls = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
    
    print(f"\nSMTP_HOST: {smtp_host or 'NOT SET'}")
    print(f"SMTP_PORT: {smtp_port}")
    print(f"SMTP_USER: {smtp_user or 'NOT SET'}")
    print(f"SMTP_PASSWORD: {'*' * len(smtp_password) if smtp_password else 'NOT SET'}")
    print(f"SMTP_USE_TLS: {smtp_use_tls}")
    
    if not smtp_host or not smtp_user or not smtp_password:
        print("\n❌ ERROR: SMTP settings are incomplete!")
        print("Please set SMTP_HOST, SMTP_USER, and SMTP_PASSWORD in your .env file")
        return False
    
    print("\n✓ SMTP settings are configured")
    return True

def test_smtp_connection():
    """Test SMTP connection and authentication"""
    import smtplib
    
    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    smtp_use_tls = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
    
    print("\n" + "=" * 60)
    print("Testing SMTP Connection")
    print("=" * 60)
    
    try:
        server = None
        if smtp_port == 465:
            print(f"\nConnecting to {smtp_host}:465 with SSL...")
            server = smtplib.SMTP_SSL(smtp_host, 465, timeout=30)
        else:
            print(f"\nConnecting to {smtp_host}:{smtp_port}...")
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
            server.ehlo()
            if smtp_use_tls:
                print("Starting TLS...")
                server.starttls()
                server.ehlo()
        
        print(f"Authenticating as {smtp_user}...")
        server.login(smtp_user, smtp_password)
        
        print("\n✓ SMTP connection and authentication successful!")
        server.quit()
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"\n❌ Authentication Error: {e}")
        print("\nTroubleshooting:")
        print("- For Gmail: Make sure you're using an App Password, not your regular password")
        print("- Verify your username and password are correct")
        print("- Check if 2-Step Verification is enabled (required for Gmail)")
        return False
        
    except smtplib.SMTPException as e:
        print(f"\n❌ SMTP Error: {e}")
        return False
        
    except Exception as e:
        print(f"\n❌ Connection Error: {e}")
        print("\nTroubleshooting:")
        print("- Check your network connection")
        print("- Verify the SMTP host and port are correct")
        print("- Try port 587 instead of 465 (or vice versa)")
        return False
    finally:
        if server:
            try:
                server.quit()
            except:
                pass

def send_test_email(recipient):
    """Send a test email"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    smtp_use_tls = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
    
    print("\n" + "=" * 60)
    print("Sending Test Email")
    print("=" * 60)
    print(f"\nRecipient: {recipient}")
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Secret Santa - SMTP Test Email'
        msg['From'] = smtp_user
        msg['To'] = recipient
        
        text_content = """
        Test Email from Secret Santa Application
        
        If you're seeing this email, your SMTP configuration is working correctly!
        
        Configuration used:
        Host: {}
        Port: {}
        User: {}
        TLS: {}
        
        You can now use this application to send Secret Santa emails.
        """.format(smtp_host, smtp_port, smtp_user, smtp_use_tls)
        
        html_content = """
        <html>
          <body>
            <h2>✓ SMTP Test Successful!</h2>
            <p>If you're seeing this email, your SMTP configuration is working correctly!</p>
            <h3>Configuration used:</h3>
            <ul>
              <li><strong>Host:</strong> {}</li>
              <li><strong>Port:</strong> {}</li>
              <li><strong>User:</strong> {}</li>
              <li><strong>TLS:</strong> {}</li>
            </ul>
            <p>You can now use this application to send Secret Santa emails.</p>
          </body>
        </html>
        """.format(smtp_host, smtp_port, smtp_user, smtp_use_tls)
        
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        server = None
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, 465, timeout=30)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
            server.ehlo()
            if smtp_use_tls:
                server.starttls()
                server.ehlo()
        
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
        print("\n✓ Test email sent successfully!")
        print(f"Check {recipient} for the test email.")
        return True
        
    except Exception as e:
        print(f"\n❌ Failed to send test email: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("\nSecret Santa - SMTP Configuration Tester\n")
    
    # Test 1: Check configuration
    if not test_smtp_config():
        sys.exit(1)
    
    # Test 2: Test connection
    if not test_smtp_connection():
        sys.exit(1)
    
    # Test 3: Send test email (optional)
    print("\n" + "=" * 60)
    response = input("\nDo you want to send a test email? (y/n): ").strip().lower()
    if response == 'y':
        recipient = input("Enter recipient email address: ").strip()
        if recipient:
            send_test_email(recipient)
    
    print("\n" + "=" * 60)
    print("Testing Complete!")
    print("=" * 60)
