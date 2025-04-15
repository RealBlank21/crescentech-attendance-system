import bcrypt
import jwt
from datetime import datetime, timedelta
from .db import DatabaseOperations
import os
from dotenv import load_dotenv

load_dotenv()

class AuthenticationManager:
    def __init__(self):
        self.db = DatabaseOperations()
        self.JWT_SECRET = os.getenv('JWT_SECRET_KEY', 'fallback-secret-key')
        self.JWT_EXPIRATION = timedelta(hours=24)

    def hash_password(self, password):
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed_password.decode('utf-8')

    def verify_password(self, password, hashed_password):
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except ValueError:
            return False

    def generate_token(self, user_id, role):
        """Generate a JWT token for authenticated users"""
        payload = {
            'user_id': user_id,
            'role': role,
            'exp': datetime.utcnow() + self.JWT_EXPIRATION
        }
        return jwt.encode(payload, self.JWT_SECRET, algorithm='HS256')

    def verify_token(self, token):
        """Verify a JWT token and return the payload if valid"""
        try:
            payload = jwt.decode(token, self.JWT_SECRET, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def login(self, email, password):
        """Authenticate a user and return a token if successful"""
        user = self.db.get_user_by_email(email)
        if not user:
            return None, "User not found"

        if not self.verify_password(password, user['password']):
            return None, "Invalid password"

        token = self.generate_token(user['user_id'], user['role'])
        return token, None

    def register_user(self, username, email, password, role='Staff', profile_picture_url=None):
        """Register a new user"""
        # Check if email already exists
        existing_user = self.db.get_user_by_email(email)
        if existing_user:
            return False, "Email already registered"

        # Hash the password
        hashed_password = self.hash_password(password)

        # Insert the new user
        query = """
            INSERT INTO User (username, email, password, role, profile_picture_url)
            VALUES (%s, %s, %s, %s, %s)
        """
        success, _ = self.db.execute_query(
            query, 
            (username, email, hashed_password, role, profile_picture_url)
        )

        if not success:
            return False, "Failed to register user"

        return True, None

    def require_auth(self, token):
        """Decorator-like function to verify authentication"""
        payload = self.verify_token(token)
        if not payload:
            return None, "Invalid or expired token"
        
        user = self.db.get_user_by_id(payload['user_id'])
        if not user:
            return None, "User not found"
            
        return user, None

    def require_admin(self, token):
        """Verify that the authenticated user is an admin"""
        user, error = self.require_auth(token)
        if error:
            return None, error
            
        if user['role'] != 'Admin':
            return None, "Admin access required"
            
        return user, None