import flask
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.security import generate_password_hash, check_password_hash # Added for password hashing
import uuid # Moved import to top


# Initialize Flask app
app = Flask(__name__)
# Enable CORS
CORS(app)
# Configure the database URI
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///default.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Recommended to disable to save resources

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False) # Increased length for hash
    # A unique link_id will be generated for each user to share
    link_id = db.Column(db.String(80), unique=True, nullable=False)
    feedbacks = db.relationship('Feedback', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>' # Changed to username for better representation

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # How the anonymous user knows the person (e.g., classmate, colleague)
    anon_identifier = db.Column(db.String(200), nullable=True)
    feedback_text = db.Column(db.Text, nullable=False)
    context_text = db.Column(db.Text, nullable=True)
    # Optional email from the anonymous user
    anon_email = db.Column(db.String(120), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f'<Feedback {self.id} for User {self.user_id}>'

# Helper function to generate a unique link_id (you might want a more robust solution)
# import uuid # Moved to top
def generate_unique_link_id():
    return str(uuid.uuid4())[:8] # Example: first 8 chars of a UUID

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), 400

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'message': 'Username, email, and password are required'}), 400

    if User.query.filter_by(username=username).first() is not None:
        return jsonify({'message': 'Username already exists'}), 409 # 409 Conflict
    
    if User.query.filter_by(email=email).first() is not None:
        return jsonify({'message': 'Email already registered'}), 409

    hashed_password = generate_password_hash(password)
    new_link_id = generate_unique_link_id()
    # Ensure link_id is unique (though collision is highly unlikely with UUIDs)
    while User.query.filter_by(link_id=new_link_id).first() is not None:
        new_link_id = generate_unique_link_id()

    new_user = User(
        username=username,
        email=email,
        password_hash=hashed_password,
        link_id=new_link_id
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        'message': 'User registered successfully', 
        'user_id': new_user.id,
        'username': new_user.username,
        'link_id': new_user.link_id
    }), 201

@app.route('/api/users', methods=['POST'])
def create_user():
    # This endpoint might be deprecated or re-purposed if all user creation goes through /api/auth/register
    # For now, it remains as a simple way to create a user with just a link_id,
    # but it doesn't set username, email, or password.
    # Consider if this is still needed or how it should interact with the new registration flow.
    new_link_id = generate_unique_link_id()
    # Ensure link_id is unique
    while User.query.filter_by(link_id=new_link_id).first() is not None:
        new_link_id = generate_unique_link_id()
    
    new_user = User(link_id=new_link_id)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User created successfully', 'link_id': new_link_id, 'user_id': new_user.id}), 201

@app.route('/api/feedback/<link_id>', methods=['POST'])
def submit_feedback(link_id):
    user = User.query.filter_by(link_id=link_id).first()
    if not user:
        return jsonify({'message': 'User not found for this link'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), 400

    feedback_text = data.get('feedback_text')
    if not feedback_text:
        return jsonify({'message': 'Feedback text is required'}), 400

    anon_identifier = data.get('anon_identifier')
    context_text = data.get('context_text')
    anon_email = data.get('anon_email')

    new_feedback = Feedback(
        user_id=user.id,
        anon_identifier=anon_identifier,
        feedback_text=feedback_text,
        context_text=context_text,
        anon_email=anon_email
    )
    db.session.add(new_feedback)
    db.session.commit()

    return jsonify({'message': 'Feedback submitted successfully', 'feedback_id': new_feedback.id}), 201

if __name__ == '__main__':
    # Note: For development only. Use a proper WSGI server for production.
    app.run(debug=True, port=os.getenv('PORT', 5001))

