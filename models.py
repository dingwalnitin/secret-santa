# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from cryptography.fernet import Fernet
import json

db = SQLAlchemy()

class SystemSettings(db.Model):
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    phase = db.Column(db.Integer, default=1)  # 1 or 2
    smtp_host = db.Column(db.String(255))
    smtp_port = db.Column(db.Integer, default=587)
    smtp_user = db.Column(db.String(255))
    smtp_password_encrypted = db.Column(db.Text)
    smtp_use_tls = db.Column(db.Boolean, default=True)
    encryption_key = db.Column(db.Text)
    assignments_generated = db.Column(db.Boolean, default=False)
    registration_open = db.Column(db.Boolean, default=True)
    chat_enabled = db.Column(db.Boolean, default=True)
    admin_can_view_chats = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_smtp_password(self, password):
        if not self.encryption_key:
            self.encryption_key = Fernet.generate_key().decode()
        f = Fernet(self.encryption_key.encode())
        self.smtp_password_encrypted = f.encrypt(password.encode()).decode()
    
    def get_smtp_password(self):
        if not self.smtp_password_encrypted or not self.encryption_key:
            return None
        f = Fernet(self.encryption_key.encode())
        return f.decrypt(self.smtp_password_encrypted.encode()).decode()


class Admin(UserMixin, db.Model):
    __tablename__ = 'admin'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    emp_id = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    address = db.Column(db.Text)
    preferences = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    as_gifter = db.relationship('Assignment', foreign_keys='Assignment.gifter_user_id', backref='gifter', lazy=True)
    as_giftee = db.relationship('Assignment', foreign_keys='Assignment.giftee_user_id', backref='giftee', lazy=True)


class Assignment(db.Model):
    __tablename__ = 'assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    gifter_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    giftee_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reveal_completed = db.Column(db.Boolean, default=False)
    reveal_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('ChatMessage', backref='assignment', lazy=True, cascade='all, delete-orphan')
    
    __table_args__ = (
        db.UniqueConstraint('gifter_user_id', 'giftee_user_id', name='unique_assignment'),
    )


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    sender_type = db.Column(db.String(20), nullable=False)  # 'gifter' or 'giftee'
    message_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'sender_type': self.sender_type,
            'message_text': self.message_text,
            'timestamp': self.timestamp.isoformat(),
            'read': self.read
        }


class LoginAttempt(db.Model):
    __tablename__ = 'login_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120))
    success = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
class ChatMessageGifter(db.Model):
    __tablename__ = 'chat_messages_gifter'
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    sender_type = db.Column(db.String(20), nullable=False)  # 'gifter' or 'giftee'
    message_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'sender_type': self.sender_type,
            'message_text': self.message_text,
            'timestamp': self.timestamp.isoformat(),
            'read': self.read
        }

class ChatMessageGiftee(db.Model):
    __tablename__ = 'chat_messages_giftee'
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    sender_type = db.Column(db.String(20), nullable=False)  # 'gifter' or 'giftee'
    message_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'sender_type': self.sender_type,
            'message_text': self.message_text,
            'timestamp': self.timestamp.isoformat(),
            'read': self.read
        }
