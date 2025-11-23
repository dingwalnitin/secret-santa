# app.py
import eventlet
eventlet.monkey_patch() 

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, current_app
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager
from config import Config
from models import db, Admin, User, Assignment, ChatMessage, SystemSettings, LoginAttempt, ChatMessageGifter, ChatMessageGiftee
from utils.email_service import EmailService
from utils.assignment_logic import AssignmentGenerator
from utils.auth import admin_required, user_required, check_rate_limit, log_login_attempt
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from keepalive import keep_db_alive
import threading
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Patch SQLAlchemy engine options



app = Flask(__name__)
app.config.from_object(Config)


# Patch SQLAlchemy engine options
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 1500,
    "pool_timeout": 30,
    "max_overflow": 10,
    "pool_size": 5,
}


# Initialize extensions
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*", sync_mode='eventlet')

# Create database tables
with app.app_context():
    db.create_all()

    # Initialize system settings if not exists
    if not SystemSettings.query.first():
        settings = SystemSettings()
        db.session.add(settings)
        db.session.commit()

    # Check if admin exists, if not redirect to admin creation
    if not Admin.query.first():
        app.config['FIRST_RUN'] = True
    else:
        app.config['FIRST_RUN'] = False
threading.Thread(target=keep_db_alive, daemon=True).start()

# ==================== HOME & REGISTRATION ====================
@app.route('/')
def index():
    settings = SystemSettings.query.first()

    # Check if first run (no admin)
    if app.config.get('FIRST_RUN', False):
        return redirect(url_for('admin_setup'))

    return render_template('index.html',
                           phase=settings.phase,
                           registration_open=settings.registration_open)

@app.route('/register', methods=['GET', 'POST'])
def register():
    settings = SystemSettings.query.first()

    # Check if registration is open
    if settings.phase != 1 or not settings.registration_open:
        flash('Registration is currently closed', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        emp_id = request.form.get('emp_id', '').strip()
        email = request.form.get('email', '').strip().lower()
        address = request.form.get('address', '').strip()
        preferences = request.form.get('preferences', '').strip()

        # Validation
        if not all([name, emp_id, email, preferences]):
            flash('All fields except address are required', 'error')
            return render_template('register.html',
                                   budget=app.config['GIFT_BUDGET'])

        # Check company domain if configured
        if app.config.get('COMPANY_DOMAIN'):
            if not email.endswith(app.config["COMPANY_DOMAIN"]):
                flash(f'Email must be from {app.config["COMPANY_DOMAIN"]}', 'error')
                return render_template('register.html',
                                       budget=app.config['GIFT_BUDGET'])

        # Check if emp_id or email already exists
        if User.query.filter_by(emp_id=emp_id).first():
            flash('Employee ID already registered', 'error')
            return render_template('register.html',
                                   budget=app.config['GIFT_BUDGET'])

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html',
                                   budget=app.config['GIFT_BUDGET'])

        # Create user
        user = User(
            name=name,
            emp_id=emp_id,
            email=email,
            address=address,
            preferences=preferences
        )

        db.session.add(user)
        db.session.commit()

        # Send confirmation email
        try:
            EmailService.send_registration_confirmation(user)
        except Exception as e:
            app.logger.error(f"Failed to send confirmation email: {str(e)}")

        return render_template('register_success.html', user=user)

    return render_template('register.html',
                           budget=app.config['GIFT_BUDGET'])

# ==================== USER LOGIN & AUTHENTICATION ====================
@app.route('/login', methods=['GET', 'POST'])
def user_login():
    settings = SystemSettings.query.first()

    # Check if Phase 2 is active
    if settings.phase != 2:
        flash('Login is only available during Phase 2', 'info')
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        emp_id = request.form.get('emp_id', '').strip()

        ip_address = request.remote_addr

        # Rate limiting
        if not check_rate_limit(ip_address):
            flash('Too many failed login attempts. Please try again later.', 'error')
            return render_template('login.html')

        user = User.query.filter_by(email=email, emp_id=emp_id).first()

        if user:
            session['user_id'] = user.id
            session.permanent = True
            user.last_login = datetime.utcnow()
            db.session.commit()

            log_login_attempt(ip_address, email, True)

            return redirect(url_for('user_dashboard'))
        else:
            log_login_attempt(ip_address, email, False)
            flash('Invalid email or employee ID', 'error')

    return render_template('login.html')

@app.route('/logout')
def user_logout():
    session.pop('user_id', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))

# ==================== USER DASHBOARD ====================
@app.route('/dashboard')
@user_required
def user_dashboard():
    user = User.query.get(session['user_id'])

    # Find assignment where user is either gifter or giftee
    assignment = Assignment.query.filter(
        (Assignment.gifter_user_id == user.id) | (Assignment.giftee_user_id == user.id)
    ).first()

    if not assignment:
        flash('No assignment found. Please contact admin.', 'error')
        return redirect(url_for('index'))

    # Determine the user's role for this assignment
    is_gifter = (assignment.gifter_user_id == user.id)

    # Provide both objects to the template so it can render both chat cards
    gifter = assignment.gifter
    giftee = assignment.giftee

    # Unread counts:
    # - unread_gifter_chat: unread messages in the "as gifter" view (messages sent by giftee)
    # - unread_giftee_chat: unread messages in the "as giftee" view (messages sent by gifter)
    try:
        unread_gifter_chat = ChatMessageGifter.query.filter_by(
            assignment_id=assignment.id,
            sender_type='giftee',
            read=False
        ).count()
    except Exception:
        # If role-specific tables don't exist (legacy), fallback to ChatMessage
        unread_gifter_chat = ChatMessage.query.filter_by(
            assignment_id=assignment.id,
            sender_type='giftee',
            read=False
        ).count()

    try:
        unread_giftee_chat = ChatMessageGiftee.query.filter_by(
            assignment_id=assignment.id,
            sender_type='gifter',
            read=False
        ).count()
    except Exception:
        unread_giftee_chat = ChatMessage.query.filter_by(
            assignment_id=assignment.id,
            sender_type='gifter',
            read=False
        ).count()

    # If reveal not completed, direct to reveal flow
    if not assignment.reveal_completed:
        return redirect(url_for('reveal'))

    return render_template(
        'user/dashboard.html',
        user=user,
        gifter=gifter,
        giftee=giftee,
        assignment=assignment,
        is_gifter=is_gifter,
        unread_gifter_chat=unread_gifter_chat,
        unread_giftee_chat=unread_giftee_chat,
        budget=current_app.config['GIFT_BUDGET']
    )
# ==================== REVEAL ANIMATION ====================
@app.route('/reveal')
@user_required
def reveal():
    user = User.query.get(session['user_id'])
    assignment = Assignment.query.filter_by(gifter_user_id=user.id).first()

    if not assignment:
        flash('No assignment found', 'error')
        return redirect(url_for('user_dashboard'))

    if assignment.reveal_completed:
        return redirect(url_for('user_dashboard'))

    # Get giftee name (all cards/segments will show this)
    giftee_name = assignment.giftee.name

    return render_template('user/reveal.html',
                           giftee_name=giftee_name,
                           animation_type='spin')  # or 'scratch'

@app.route('/api/complete-reveal', methods=['POST'])
@user_required
def complete_reveal():
    user = User.query.get(session['user_id'])
    assignment = Assignment.query.filter_by(gifter_user_id=user.id).first()

    if assignment and not assignment.reveal_completed:
        assignment.reveal_completed = True
        assignment.reveal_time = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True})

    return jsonify({'success': False}), 400

# Continue to Part 2...
# ==================== CHAT FUNCTIONALITY ====================
@app.route('/chat')
@user_required
def chat():
    user = User.query.get(session['user_id'])
    assignment = Assignment.query.filter(
        (Assignment.gifter_user_id == user.id) | (Assignment.giftee_user_id == user.id)
    ).first()
    settings = SystemSettings.query.first()

    if not assignment or not assignment.reveal_completed:
        flash('Please complete the reveal first', 'error')
        return redirect(url_for('reveal'))

    if not settings.chat_enabled:
        flash('Chat is currently disabled', 'error')
        return redirect(url_for('user_dashboard'))

    # Determine role and pick the right table
    is_gifter = (assignment.gifter_user_id == user.id)

    if is_gifter:
        messages = ChatMessageGifter.query.filter_by(assignment_id=assignment.id).order_by(ChatMessageGifter.timestamp).all()
        # Mark messages from giftee as read in gifter table
        ChatMessageGifter.query.filter_by(assignment_id=assignment.id, sender_type='giftee', read=False).update({'read': True})
    else:
        messages = ChatMessageGiftee.query.filter_by(assignment_id=assignment.id).order_by(ChatMessageGiftee.timestamp).all()
        # Mark messages from gifter as read in giftee table
        ChatMessageGiftee.query.filter_by(assignment_id=assignment.id, sender_type='gifter', read=False).update({'read': True})

    db.session.commit()

    # Convert role-specific model objects to a common shape for template (use to_dict)
    messages_list = [m.to_dict() for m in messages]

    return render_template('user/chat.html',
                           user=user,
                           assignment=assignment,
                           messages=messages_list,
                           is_gifter=is_gifter)

# ==================== ADMIN SETUP (First Run) ====================
@app.route('/admin/setup', methods=['GET', 'POST'])
def admin_setup():
    # Check if admin already exists
    if Admin.query.first():
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        if not all([name, email, password]):
            flash('All fields are required', 'error')
            return render_template('admin/setup.html')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('admin/setup.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters', 'error')
            return render_template('admin/setup.html')

        # Create admin
        admin = Admin(name=name, email=email)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()

        app.config['FIRST_RUN'] = False

        flash('Admin account created successfully! Please login.', 'success')
        return redirect(url_for('admin_login'))

    return render_template('admin/setup.html')

# ==================== ADMIN LOGIN ====================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        ip_address = request.remote_addr

        # Rate limiting
        if not check_rate_limit(ip_address):
            flash('Too many failed login attempts. Please try again later.', 'error')
            return render_template('admin/login.html')

        admin = Admin.query.filter_by(email=email).first()

        if admin and admin.check_password(password):
            session['admin_id'] = admin.id
            session.permanent = True
            admin.last_login = datetime.utcnow()
            db.session.commit()

            log_login_attempt(ip_address, email, True)

            return redirect(url_for('admin_dashboard'))
        else:
            log_login_attempt(ip_address, email, False)
            flash('Invalid email or password', 'error')

    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('admin_login'))

# ==================== ADMIN DASHBOARD ====================
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    settings = SystemSettings.query.first()

    stats = {
        'total_participants': User.query.count(),
        'assignments_generated': settings.assignments_generated,
        'reveals_completed': Assignment.query.filter_by(reveal_completed=True).count(),
        'total_messages': ChatMessage.query.count(),
        'phase': settings.phase
    }

    return render_template('admin/dashboard.html', stats=stats, settings=settings)

# ==================== ADMIN PARTICIPANTS ====================
@app.route('/admin/participants')
@admin_required
def admin_participants():
    participants = User.query.all()
    return render_template('admin/participants.html', participants=participants)

@app.route('/admin/participants/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_participant(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        user.name = request.form.get('name', '').strip()
        user.email = request.form.get('email', '').strip().lower()
        user.address = request.form.get('address', '').strip()
        user.preferences = request.form.get('preferences', '').strip()

        db.session.commit()
        flash('Participant updated successfully', 'success')
        return redirect(url_for('admin_participants'))

    return render_template('admin/edit_participant.html', user=user)

@app.route('/admin/participants/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_participant(user_id):
    user = User.query.get_or_404(user_id)

    # Delete related assignments and messages
    Assignment.query.filter(
        (Assignment.gifter_user_id == user_id) | (Assignment.giftee_user_id == user_id)
    ).delete()

    db.session.delete(user)
    db.session.commit()

    flash('Participant deleted successfully', 'success')
    return redirect(url_for('admin_participants'))

@app.route('/admin/participants/export')
@admin_required
def export_participants():
    import csv
    from io import StringIO
    from flask import make_response

    participants = User.query.all()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Name', 'Employee ID', 'Email', 'Preferences', 'Address', 'Registered On'])

    for user in participants:
        writer.writerow([
            user.name,
            user.emp_id,
            user.email,
            user.preferences,
            user.address,
            user.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=participants.csv"
    output.headers["Content-type"] = "text/csv"
    return output

# ==================== ADMIN ASSIGNMENTS ====================
@app.route('/admin/assignments')
@admin_required
def admin_assignments():
    settings = SystemSettings.query.first()
    assignments = AssignmentGenerator.get_assignment_map()

    return render_template('admin/assignments.html',
                           assignments=assignments,
                           settings=settings)

@app.route('/admin/assignments/generate', methods=['POST'])
@admin_required
def generate_assignments():
    try:
        count = AssignmentGenerator.generate_assignments()

        settings = SystemSettings.query.first()
        settings.assignments_generated = True
        db.session.commit()

        flash(f'Successfully generated {count} assignments', 'success')
    except Exception as e:
        flash(f'Error generating assignments: {str(e)}', 'error')

    return redirect(url_for('admin_assignments'))

@app.route('/admin/assignments/export')
@admin_required
def export_assignments():
    import csv
    from io import StringIO
    from flask import make_response

    assignments = AssignmentGenerator.get_assignment_map()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Gifter Name', 'Gifter Email', 'Giftee Name', 'Giftee Email', 'Giftee Preferences', 'Reveal Completed'])

    for assignment in assignments:
        writer.writerow([
            assignment['gifter']['name'],
            assignment['gifter']['email'],
            assignment['giftee']['name'],
            assignment['giftee']['email'],
            assignment['giftee']['preferences'],
            'Yes' if assignment['reveal_completed'] else 'No'
        ])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=assignments.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/admin/assignments/<int:assignment_id>/override', methods=['POST'])
@admin_required
def override_assignment(assignment_id):
    new_giftee_id = request.form.get('new_giftee_id', type=int)

    if not new_giftee_id:
        flash('Invalid giftee selection', 'error')
        return redirect(url_for('admin_assignments'))

    assignment = Assignment.query.get_or_404(assignment_id)

    # Validate no self-assignment
    if assignment.gifter_user_id == new_giftee_id:
        flash('Cannot assign a person to themselves', 'error')
        return redirect(url_for('admin_assignments'))

    assignment.giftee_user_id = new_giftee_id
    assignment.reveal_completed = False
    assignment.reveal_time = None
    db.session.commit()

    flash('Assignment updated successfully', 'success')
    return redirect(url_for('admin_assignments'))

# ==================== ADMIN SETTINGS ====================
@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    settings = SystemSettings.query.first()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_phase':
            new_phase = request.form.get('phase', type=int)
            if new_phase in [1, 2]:
                settings.phase = new_phase

                # If moving to Phase 2, notify all users
                if new_phase == 2:
                    users = User.query.all()
                    for user in users:
                        try:
                            login_url = url_for('user_login', _external=True)
                            EmailService.send_phase2_announcement(user, login_url)
                        except Exception as e:
                            app.logger.error(f"Failed to send email to {user.email}: {str(e)}")

                db.session.commit()
                flash(f'Phase updated to {new_phase}', 'success')

        elif action == 'toggle_registration':
            settings.registration_open = not settings.registration_open
            db.session.commit()
            status = "opened" if settings.registration_open else "closed"
            flash(f'Registration {status}', 'success')

        elif action == 'toggle_chat':
            settings.chat_enabled = not settings.chat_enabled
            db.session.commit()
            status = "enabled" if settings.chat_enabled else "disabled"
            flash(f'Chat {status}', 'success')

        elif action == 'update_smtp':
            settings.smtp_host = request.form.get('smtp_host', '').strip()
            settings.smtp_port = request.form.get('smtp_port', type=int)
            settings.smtp_user = request.form.get('smtp_user', '').strip()
            settings.smtp_use_tls = request.form.get('smtp_use_tls') == 'on'

            smtp_password = request.form.get('smtp_password', '').strip()
            if smtp_password:
                settings.set_smtp_password(smtp_password)

            db.session.commit()
            flash('SMTP settings updated successfully', 'success')

        elif action == 'test_email':
            test_email = request.form.get('test_email', '').strip()
            if test_email:
                success = EmailService.send_email(
                    test_email,
                    'Test Email from Secret Santa',
                    '<h2>Test Email</h2><p>Your SMTP configuration is working correctly!</p>',
                    'Test Email - Your SMTP configuration is working correctly!'
                )
                if success:
                    flash('Test email sent successfully', 'success')
                else:
                    flash('Failed to send test email. Check your SMTP settings.', 'error')

        elif action == 'reset_system':
            # Confirm reset
            if request.form.get('confirm_reset') == 'RESET':
                # Archive or delete all data
                Assignment.query.delete()
                ChatMessage.query.delete()
                User.query.delete()
                LoginAttempt.query.delete()

                settings.phase = 1
                settings.assignments_generated = False
                settings.registration_open = True

                db.session.commit()
                flash('System reset successfully. Ready for next year!', 'success')
            else:
                flash('Reset cancelled. Type RESET to confirm.', 'warning')

        return redirect(url_for('admin_settings'))

    return render_template('admin/settings.html', settings=settings)
@app.route('/chat/gifter')
@user_required
def chat_as_gifter():
    user = User.query.get(session['user_id'])
    assignment = Assignment.query.filter_by(gifter_user_id=user.id).first()

    messages = ChatMessageGifter.query \
        .filter_by(assignment_id=assignment.id) \
        .order_by(ChatMessageGifter.timestamp).all()

    # Mark read (messages from giftee)
    ChatMessageGifter.query.filter_by(
        assignment_id=assignment.id,
        sender_type='giftee',
        read=False
    ).update({'read': True})
    db.session.commit()

    return render_template(
        'user/chat.html',
        messages=[m.to_dict() for m in messages],
        assignment=assignment,
        is_gifter=True,
        chat_mode='gifter'
    )


@app.route('/chat/giftee')
@user_required
def chat_as_giftee():
    user = User.query.get(session['user_id'])
    assignment = Assignment.query.filter_by(giftee_user_id=user.id).first()

    messages = ChatMessageGiftee.query \
        .filter_by(assignment_id=assignment.id) \
        .order_by(ChatMessageGiftee.timestamp).all()

    # Mark read (messages from gifter)
    ChatMessageGiftee.query.filter_by(
        assignment_id=assignment.id,
        sender_type='gifter',
        read=False
    ).update({'read': True})
    db.session.commit()

    return render_template(
        'user/chat.html',
        messages=[m.to_dict() for m in messages],
        assignment=assignment,
        is_gifter=False,
        chat_mode='giftee'
    )

# ==================== ADMIN CHAT MONITORING ====================
@app.route('/admin/chats')
@admin_required
def admin_chats():
    settings = SystemSettings.query.first()
    if not settings.admin_can_view_chats:
        flash('Chat monitoring is disabled', 'warning')
        return redirect(url_for('admin_dashboard'))

    assignments = Assignment.query.filter_by(reveal_completed=True).all()
    chat_data = []

    for assignment in assignments:
        # get messages from both tables and merge
        msgs_g = ChatMessageGifter.query.filter_by(assignment_id=assignment.id).all()
        msgs_q = ChatMessageGiftee.query.filter_by(assignment_id=assignment.id).all()
        # Prefer whichever has content; they should generally be identical
        combined = sorted(
            [m.to_dict() for m in msgs_g] + [m.to_dict() for m in msgs_q],
            key=lambda x: x['timestamp']
        )
        chat_data.append({
            'assignment': assignment,
            'gifter': assignment.gifter,
            'giftee': assignment.giftee,
            'messages': combined
        })

    return render_template('admin/chats.html', chat_data=chat_data)

# ==================== SOCKETIO CHAT EVENTS ====================
from flask import session as flask_session
# Note: models already imported at top

@socketio.on('connect')
def handle_connect():
    # We keep connect minimal. Client should call join_chat explicitly.
    # This prevents reliance on session being available during handshake.
    current_app.logger.debug('Socket connected (sid=%s)', request.sid if hasattr(request, 'sid') else 'unknown')

@socketio.on('disconnect')
def handle_disconnect():
    # Nothing special to do here; rooms are left automatically when socket disconnects.
    current_app.logger.debug('Socket disconnected')

@socketio.on('join_chat')
def handle_join_chat(data):
    """
    Client requests to join a chat room for an assignment.
    Expects: { assignment_id: <int> }
    """
    try:
        user_id = flask_session.get('user_id')
        if not user_id:
            emit('join_ack', {'success': False, 'error': 'Not authenticated'})
            return

        assignment_id = data.get('assignment_id')
        if not assignment_id:
            emit('join_ack', {'success': False, 'error': 'Missing assignment_id'})
            return

        assignment = Assignment.query.get(int(assignment_id))
        if not assignment:
            emit('join_ack', {'success': False, 'error': 'Assignment not found'})
            return

        # Validate user is part of assignment
        if assignment.gifter_user_id != user_id and assignment.giftee_user_id != user_id:
            emit('join_ack', {'success': False, 'error': 'Not part of this assignment'})
            return

        room = f'chat_{assignment.id}'
        join_room(room)
        emit('join_ack', {'success': True, 'room': room})
        current_app.logger.info(f'User {user_id} joined room {room}')
    except Exception as e:
        current_app.logger.exception('Error in join_chat')
        emit('join_ack', {'success': False, 'error': str(e)})

@socketio.on('typing')
def handle_typing(data):
    """
    Typing indicator.
    Expects: { typing: True/False, assignment_id: <id> }
    """
    try:
        user_id = flask_session.get('user_id')
        if not user_id:
            return
        assignment_id = data.get('assignment_id')
        typing = data.get('typing', False)
        if not assignment_id:
            return
        room = f'chat_{int(assignment_id)}'
        emit('user_typing', {'typing': typing}, room=room, include_self=False)
    except Exception:
        current_app.logger.exception('Error in typing handler')

@socketio.on('send_message')
def handle_message(data):
    """
    Expects: { message: "...", assignment_id: <id> }
    Stores message into both role-specific chat tables (so each participant views messages
    under their own 'context' table).
    """
    try:
        user_id = flask_session.get('user_id')
        if not user_id:
            emit('error_message', {'error': 'Not authenticated'})
            return

        message_text = (data.get('message') or '').strip()
        assignment_id = data.get('assignment_id')
        if not message_text:
            return
        if not assignment_id:
            emit('error_message', {'error': 'Missing assignment_id'})
            return

        assignment = Assignment.query.get(int(assignment_id))
        if not assignment:
            emit('error_message', {'error': 'Assignment not found'})
            return
        if not assignment.reveal_completed:
            emit('error_message', {'error': 'Reveal not completed yet'})
            return

        # Determine sender_type
        if assignment.gifter_user_id == user_id:
            sender_type = 'gifter'
        elif assignment.giftee_user_id == user_id:
            sender_type = 'giftee'
        else:
            emit('error_message', {'error': 'Not participant of this assignment'})
            return

        # Persist to the legacy single table for backward compatibility if desired
        # (optional) - keep existing table behavior
        message = ChatMessage(
            assignment_id=assignment.id,
            sender_type=sender_type,
            message_text=message_text
        )
        db.session.add(message)

        # Persist to role-specific tables:
        gm = ChatMessageGifter(
            assignment_id=assignment.id,
            sender_type=sender_type,
            message_text=message_text
        )
        qm = ChatMessageGiftee(
            assignment_id=assignment.id,
            sender_type=sender_type,
            message_text=message_text
        )
        db.session.add(gm)
        db.session.add(qm)

        db.session.commit()

        payload = {
            'id': message.id,
            'sender_type': message.sender_type,
            'message_text': message.message_text,
            'timestamp': message.timestamp.isoformat()
        }

        room = f'chat_{assignment.id}'
        emit('new_message', payload, room=room)

        # Send email notification to the other party (best-effort)
        try:
            if sender_type == 'gifter':
                EmailService.send_new_message_notification(assignment.giftee, True)
            else:
                EmailService.send_new_message_notification(assignment.gifter, False)
        except Exception:
            current_app.logger.exception('Failed to send notification email')
    except Exception:
        current_app.logger.exception('Error in send_message handler')
        emit('error_message', {'error': 'Server error while sending message'})

@socketio.on('giftee_send_message')
def handle_giftee_message(data):
    # Backwards compatibility: reuse send_message handler
    handle_message(data)

# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# ==================== RUN APPLICATION ====================
if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
