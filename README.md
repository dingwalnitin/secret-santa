# Secret Santa Application

A Flask-based Secret Santa gift exchange application with email notifications, user dashboard, and chat features.

## Features

- 📝 User registration with preferences
- 🎁 Automated Secret Santa assignments
- 📧 Email notifications (registration, assignments, messages)
- 💬 Anonymous chat between gifter and giftee
- 🎨 Interactive reveal animations (spin wheel, scratch card)
- 👨‍💼 Admin dashboard for managing participants and settings
- 🔒 Secure authentication and encrypted SMTP passwords

## Installation

1. Clone the repository:
```bash
git clone https://github.com/dingwalnitin/secret-santa.git
cd secret-santa
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure SMTP settings (see below)

5. Run the application:
```bash
python app.py
```

6. Open your browser and navigate to `http://localhost:5000`

## SMTP Email Configuration

The application supports two ways to configure SMTP settings:

### Option 1: Environment Variables (.env file) - **Recommended**

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your SMTP credentials:

**For Gmail (recommended - use App Password):**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
```

**For Gmail with SSL (port 465):**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=false
```

**For Office 365:**
```env
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your-email@company.com
SMTP_PASSWORD=your-password
SMTP_USE_TLS=true
```

### Option 2: Admin Panel

1. Start the application
2. Complete the admin setup
3. Go to Admin Dashboard → Settings → Email (SMTP) Configuration
4. Enter your SMTP details and click "Save SMTP Settings"
5. Use the "Test Email" feature to verify your configuration

### Gmail App Password Setup

If you're using Gmail, you **must** use an App Password (not your regular password):

1. Enable 2-Step Verification on your Google Account
2. Go to: Google Account → Security → 2-Step Verification → App passwords
3. Generate a new app password for "Mail"
4. Use this 16-character password in your `.env` file or admin panel

### Testing SMTP Configuration

After configuring SMTP settings:

1. Go to Admin Dashboard → Settings
2. Scroll to "Email (SMTP) Configuration"
3. Enter a test email address
4. Click "Send Test Email"
5. Check if the email was received

### Common SMTP Issues and Solutions

**Issue: "SMTP Authentication failed"**
- For Gmail: Make sure you're using an App Password, not your regular password
- Verify your username and password are correct
- Check if 2-Step Verification is enabled (required for Gmail App Passwords)

**Issue: "Connection timeout"**
- Check your firewall/network settings
- Verify the SMTP host and port are correct
- Try port 587 instead of 465 (or vice versa)

**Issue: "SSL/TLS errors"**
- For port 587: Set `SMTP_USE_TLS=true`
- For port 465: Set `SMTP_USE_TLS=false`

**Issue: Email not sending**
- Check application logs for detailed error messages
- Verify SMTP settings in Admin panel or .env file
- Test with the "Send Test Email" feature in admin panel

### Priority of SMTP Settings

1. **Database settings** (configured via Admin Panel) take priority
2. **Environment variables** (.env file) are used as fallback if database is empty

## Application Workflow

### Phase 1: Registration
1. Admin opens registration
2. Participants register with their details and gift preferences
3. Participants receive confirmation emails

### Phase 2: Assignments
1. Admin generates Secret Santa assignments
2. Admin switches to Phase 2
3. All participants receive notification emails
4. Participants log in to reveal their assigned giftee
5. Participants can chat anonymously with their giftee

## Admin Features

- View and manage all participants
- Generate assignments (ensures no one gets themselves)
- Override assignments if needed
- Control registration and chat
- Monitor chat messages (optional)
- Export participant and assignment data
- System reset for next year

## Technologies Used

- **Backend**: Flask, Flask-SocketIO
- **Database**: SQLAlchemy (SQLite)
- **Real-time**: SocketIO with eventlet
- **Email**: smtplib with encryption
- **Security**: Werkzeug password hashing, Fernet encryption

## License

MIT License

## Support

For issues or questions, please open an issue on GitHub.
