import os
import jwt
import datetime
from flask import Blueprint, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import logging
from mail import EmailSender
from Crypto.Cipher import AES
import base64

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a Blueprint for authorization
auth_bp = Blueprint('auth', __name__)

# Database configuration
db = SQLAlchemy()

# Get the secret key, allowed domains, and token expiry duration from environment variables
secret_key = os.getenv('SECRET_KEY')
allowed_domains = os.getenv('ALLOWED_DOMAINS', '').split(',')
token_expiry_days = int(os.getenv('TOKEN_EXPIRY_DAYS', '0'))
token_expiry_minutes = int(os.getenv('TOKEN_EXPIRY_MINUTES', '60'))
encryption_key = os.getenv('ENCRYPTION_KEY')

if not secret_key:
    logger.error('Secret key not found in environment variables.')
    raise EnvironmentError('Secret key not found in environment variables.')

if not allowed_domains:
    logger.error('Allowed domains not found in environment variables.')
    raise EnvironmentError('Allowed domains not found in environment variables.')

if not encryption_key:
    encryption_key = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')
    logger.warning('Encryption key not found in environment variables. A new key has been generated.')

email_sender = None

def init_email_sender(sender):
    global email_sender
    email_sender = sender

# Encryption setup
def encrypt_token(token):
    cipher = AES.new(encryption_key[:32].encode('utf-8'), AES.MODE_EAX)
    nonce = cipher.nonce
    ciphertext, tag = cipher.encrypt_and_digest(token.encode('utf-8'))
    return base64.urlsafe_b64encode(nonce + ciphertext).decode('utf-8')

def decrypt_token(encrypted_token, encryption_key):
    encrypted_token = base64.urlsafe_b64decode(encrypted_token.encode('utf-8'))
    nonce = encrypted_token[:16]
    ciphertext = encrypted_token[16:]
    cipher = AES.new(encryption_key[:32].encode('utf-8'), AES.MODE_EAX, nonce=nonce)
    token = cipher.decrypt(ciphertext).decode('utf-8')
    return token

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    time_to_live = db.Column(db.String(120), nullable=False)
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f'<User {self.email}>'

def generate_token(email, secret_key, expiration_days, expiration_minutes):
    try:
        expiry = datetime.datetime.utcnow() + datetime.timedelta(days=expiration_days, minutes=expiration_minutes)
        payload = {
            'email': email,
            'exp': expiry,
            'iat': datetime.datetime.utcnow(),
            'TimeToLive': expiry.strftime('%Y-%m-%d %H:%M:%S')
        }
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        return token, payload['TimeToLive']
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        raise

def verify_token(token, secret_key):
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload, True
    except jwt.ExpiredSignatureError:
        logger.warning('Token has expired')
        return 'Token has expired', False
    except jwt.InvalidTokenError:
        logger.warning('Invalid token')
        return 'Invalid token', False
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return str(e), False

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    name = data.get('name')
    admin_header = request.headers.get('admin')
    is_admin = admin_header == 'true'

    if not email or not name:
        return jsonify({"message": "Email and name are required"}), 400

    # Check if email domain is allowed
    email_domain = email.split('@')[-1]
    if email_domain not in allowed_domains:
        return jsonify({"message": f"Email domain {email_domain} is not allowed"}), 400

    token, time_to_live = generate_token(email, secret_key, token_expiry_days, token_expiry_minutes)
    encrypted_token = encrypt_token(token) if is_admin else None

    user = User.query.filter_by(email=email).first()
    if not user:
        new_user = User(email=email, name=name, time_to_live=time_to_live)
        db.session.add(new_user)
        db.session.commit()
    else:
        user.name = name  
        user.time_to_live = time_to_live
        db.session.commit()
    
    email_body = f"Here is your access token:\n\n{token}\n\nThis token is valid until {time_to_live}."
    email_sender.send_email(email, "Your Access Token", email_body)
    
    response = {"message": "User registered successfully and email sent"}
    if is_admin:
        response["token"] = encrypted_token

    return jsonify(response), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    admin_header = request.headers.get('admin')
    is_admin = admin_header == 'true'

    user = User.query.filter_by(email=email).first()
    if user:
        token, time_to_live = generate_token(email, secret_key, token_expiry_days, token_expiry_minutes)
        encrypted_token = encrypt_token(token) if is_admin else None
        user.time_to_live = time_to_live
        db.session.commit()
        email_body = f"Here is your access token:\n\n{token}\n\nThis token is valid until {time_to_live}."
        email_sender.send_email(email, "Your Access Token", email_body)
        
        response = {"message": "Token sent to your email"}
        if is_admin:
            response["token"] = encrypted_token
        
        return jsonify(response), 200
    else:
        return jsonify({"message": "Email not registered"}), 401

@auth_bp.route('/protected', methods=['GET'])
def protected():
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            token = auth_header.split(" ")[1]
            payload, is_valid = verify_token(token, secret_key)
            if is_valid:
                return jsonify({"message": f"Welcome {payload['email']}!"}), 200
            else:
                return jsonify({"message": payload}), 401
        except IndexError:
            return jsonify({"message": "Token format invalid"}), 401
    else:
        return jsonify({"message": "Token not provided"}), 401

@auth_bp.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    users_list = [{'id': user.id, 'email': user.email, 'name': user.name, 'time_to_live': user.time_to_live, 'date_added': user.date_added} for user in users]
    return jsonify(users_list)

@auth_bp.route('/delete_user', methods=['DELETE'])
def delete_user():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({"message": "Email is required"}), 400
    
    user = User.query.filter_by(email=email).first()
    if user:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": f"User with email {email} has been deleted."}), 200
    else:
        return jsonify({"message": f"No user found with email {email}."}), 404

@auth_bp.route('/decrypt', methods=['POST'])
def decrypt():
    data = request.get_json()
    encrypted_token = data.get('token')
    encryption_key_param = data.get('encryption_key')
    
    if not encrypted_token or not encryption_key_param:
        return jsonify({"message": "Token and encryption key are required"}), 400
    
    try:
        decrypted_token = decrypt_token(encrypted_token, encryption_key_param)
        return jsonify({"message": "Token decrypted successfully", "token": decrypted_token}), 200
    except Exception as e:
        logger.error(f"Error decrypting token: {e}")
        return jsonify({"message": "Error decrypting token"}), 500
