# SMTP Configuration Guide - Quick Start

## Problem Solved
The SMTP feature was not working because:
1. The application wasn't loading `.env` file (even though `python-dotenv` was in requirements)
2. Only database-stored SMTP settings were supported
3. SMTP connection logic had issues with SSL/TLS ports

## Changes Made

### 1. Environment Variable Support
- Added `load_dotenv()` in `app.py` to load `.env` file
- Modified `get_smtp_config()` to fallback to environment variables if database is empty

### 2. Fixed SMTP Connection Issues
- Fixed port 465 (SSL) vs port 587 (STARTTLS) handling
- Increased connection timeout from 10s to 30s
- Added detailed error logging for troubleshooting

### 3. Documentation & Tools
- Created `.env.example` with examples for Gmail, Office 365, etc.
- Created `README.md` with complete setup guide
- Created `test_smtp.py` for easy SMTP testing

## How to Use

### Method 1: Using .env File (Recommended)

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit .env and add your SMTP credentials:**
   ```env
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   SMTP_USE_TLS=true
   ```

3. **For Gmail users - Get an App Password:**
   - Go to Google Account → Security → 2-Step Verification
   - Scroll down to "App passwords"
   - Generate a new app password
   - Use this password in your `.env` file

4. **Test your configuration:**
   ```bash
   python test_smtp.py
   ```

### Method 2: Using Admin Panel

1. Start the application
2. Login as admin
3. Go to Settings → Email (SMTP) Configuration
4. Fill in your SMTP details
5. Click "Send Test Email" to verify

## Testing Your SMTP Setup

### Option A: Using test_smtp.py
```bash
python test_smtp.py
```

This will:
- Check if SMTP settings are configured
- Test connection to SMTP server
- Optionally send a test email

### Option B: Using the Admin Panel
1. Login to admin panel
2. Go to Settings
3. Scroll to "Email (SMTP) Configuration"
4. Enter a test email address
5. Click "Send Test Email"

## Common Issues & Solutions

### Issue: "SMTP Authentication failed"
**For Gmail:**
- You MUST use an App Password, not your regular password
- Enable 2-Step Verification first
- Generate App Password: Google Account → Security → App passwords

**For other providers:**
- Verify username and password are correct
- Check if your email provider requires app-specific passwords

### Issue: "Connection timeout"
- Check your firewall/network settings
- Verify SMTP host and port are correct
- Try alternative port (587 instead of 465, or vice versa)

### Issue: "SSL/TLS errors"
**For port 587 (STARTTLS):**
```env
SMTP_PORT=587
SMTP_USE_TLS=true
```

**For port 465 (SSL):**
```env
SMTP_PORT=465
SMTP_USE_TLS=false
```

## SMTP Provider Settings

### Gmail
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
```

### Office 365
```env
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your-email@company.com
SMTP_PASSWORD=your-password
SMTP_USE_TLS=true
```

### Outlook.com
```env
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=your-email@outlook.com
SMTP_PASSWORD=your-password
SMTP_USE_TLS=true
```

## Troubleshooting Steps

1. **Verify .env file is loaded:**
   ```bash
   python test_smtp.py
   ```

2. **Check application logs:**
   The application now logs detailed SMTP errors including:
   - Connection attempts
   - Authentication status
   - Specific error messages

3. **Try the test script:**
   ```bash
   python test_smtp.py
   ```
   It will guide you through each step and show exactly where the problem is.

4. **Common mistakes:**
   - Using regular password instead of App Password (Gmail)
   - Wrong port number
   - Wrong TLS setting for the port
   - Firewall blocking SMTP ports

## Priority of Settings

The application checks settings in this order:
1. **Database settings** (Admin Panel) - Used if configured
2. **Environment variables** (.env file) - Used as fallback

This means you can:
- Use .env for initial setup
- Later switch to Admin Panel if preferred
- Or keep using .env (settings persist across restarts)

## Need Help?

If you're still having issues:
1. Run `python test_smtp.py` and share the output
2. Check the application logs for error messages
3. Verify your SMTP provider's documentation for correct settings
4. For Gmail, ensure you're using an App Password, not your regular password

## Files Modified

- `app.py` - Added dotenv loading
- `utils/email_service.py` - Added env fallback and better error handling
- `.env.example` - Created with examples
- `README.md` - Created with full documentation
- `test_smtp.py` - Created for testing
