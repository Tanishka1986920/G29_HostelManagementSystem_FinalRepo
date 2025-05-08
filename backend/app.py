from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hostel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'super-secret-key'  # Change in production
app.config['JWT_TOKEN_LOCATION'] = ['headers']

db = SQLAlchemy(app)
jwt = JWTManager(app)

# Models
class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin or student

class Room(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    number = db.Column(db.String(10), unique=True, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='available')  # available, occupied

class Student(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)

class Booking(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = db.Column(db.String(36), db.ForeignKey('student.id'), nullable=False)
    room_id = db.Column(db.String(36), db.ForeignKey('room.id'), nullable=False)
    booking_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Notice(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LeaveRequest(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = db.Column(db.String(36), db.ForeignKey('student.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, approved, rejected
    request_date = db.Column(db.DateTime, default=datetime.utcnow)

# Notice Routes
@app.route('/api/notices', methods=['GET'])
@jwt_required()
def get_notices():
    notices = Notice.query.order_by(Notice.created_at.desc()).all()
    return jsonify([{'id': n.id, 'title': n.title, 'content': n.content, 'created_at': n.created_at.isoformat()} for n in notices]), 200

@app.route('/api/notices', methods=['POST'])
@jwt_required()
def create_notice():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'message': 'Admin access required'}), 403
    data = request.get_json()
    notice = Notice(title=data['title'], content=data['content'])
    db.session.add(notice)
    db.session.commit()
    return jsonify({'message': 'Notice created'}), 201

# Leave Request Routes
@app.route('/api/leave-requests', methods=['GET'])
@jwt_required()
def get_leave_requests():
    claims = get_jwt()
    if claims.get('role') == 'admin':
        leave_requests = LeaveRequest.query.order_by(LeaveRequest.request_date.desc()).all()
    else:
        # For students, show only their leave requests
        identity = get_jwt_identity()
        student = Student.query.filter_by(user_id=identity).first()
        if not student:
            return jsonify({'message': 'Student not found'}), 404
        leave_requests = LeaveRequest.query.filter_by(student_id=student.id).order_by(LeaveRequest.request_date.desc()).all()
    return jsonify([{
        'id': lr.id,
        'student_id': lr.student_id,
        'reason': lr.reason,
        'status': lr.status,
        'request_date': lr.request_date.isoformat()
    } for lr in leave_requests]), 200

@app.route('/api/leave-requests', methods=['POST'])
@jwt_required()
def create_leave_request():
    claims = get_jwt()
    if claims.get('role') != 'student':
        return jsonify({'message': 'Student access required'}), 403
    data = request.get_json()
    identity = get_jwt_identity()
    student = Student.query.filter_by(user_id=identity).first()
    if not student:
        return jsonify({'message': 'Student not found'}), 404
    leave_request = LeaveRequest(student_id=student.id, reason=data['reason'])
    db.session.add(leave_request)
    db.session.commit()
    return jsonify({'message': 'Leave request created'}), 201

@app.route('/api/leave-requests/<id>', methods=['PATCH'])
@jwt_required()
def update_leave_request_status(id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'message': 'Admin access required'}), 403
    leave_request = LeaveRequest.query.get_or_404(id)
    data = request.get_json()
    status = data.get('status')
    if status not in ['pending', 'approved', 'rejected']:
        return jsonify({'message': 'Invalid status'}), 400
    leave_request.status = status
    db.session.commit()
    return jsonify({'message': 'Leave request status updated'}), 200

# Authentication Routes
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        access_token = create_access_token(identity=user.id, additional_claims={'role': user.role})
        return jsonify({'access_token': access_token}), 200
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'student')
    name = data.get('name')
    email = data.get('email')
    
    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 400
    
    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role=role
    )
    db.session.add(user)
    db.session.commit()
    
    if role == 'student':
        student = Student(name=name, email=email, user_id=user.id)
        db.session.add(student)
        db.session.commit()
    
    return jsonify({'message': 'User registered successfully'}), 201

# Room Routes
@app.route('/api/rooms', methods=['GET'])
@jwt_required()
def get_rooms():
    rooms = Room.query.all()
    return jsonify([{'id': r.id, 'number': r.number, 'type': r.type, 'status': r.status} for r in rooms]), 200

from flask_jwt_extended import get_jwt
@app.route('/api/rooms', methods=['POST'])
@jwt_required()
def create_room():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'message': 'Admin access required'}), 403
    data = request.get_json()
    room = Room(number=data['number'], type=data['type'])
    db.session.add(room)
    db.session.commit()
    return jsonify({'message': 'Room created'}), 201

@app.route('/api/rooms/<id>', methods=['PUT'])
@jwt_required()
def update_room(id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'message': 'Admin access required'}), 403
    room = Room.query.get_or_404(id)
    data = request.get_json()
    room.number = data.get('number', room.number)
    room.type = data.get('type', room.type)
    room.status = data.get('status', room.status)
    db.session.commit()
    return jsonify({'message': 'Room updated'}), 200

@app.route('/api/rooms/<id>', methods=['DELETE'])
@jwt_required()
def delete_room(id):
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'message': 'Admin access required'}), 403
    room = Room.query.get_or_404(id)
    db.session.delete(room)
    db.session.commit()
    return jsonify({'message': 'Room deleted'}), 200

# Student Routes
@app.route('/api/students', methods=['GET'])
@jwt_required()
def get_students():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'message': 'Admin access required'}), 403
    students = Student.query.all()
    return jsonify([{'id': s.id, 'name': s.name, 'email': s.email} for s in students]), 200

# Booking Routes
@app.route('/api/bookings', methods=['GET'])
@jwt_required()
def get_bookings():
    bookings = Booking.query.all()
    return jsonify([{
        'id': b.id,
        'student_id': b.student_id,
        'room_id': b.room_id,
        'booking_date': b.booking_date.isoformat()
    } for b in bookings]), 200

@app.route('/api/bookings', methods=['POST'])
@jwt_required()
def create_booking():
    data = request.get_json()
    room = Room.query.get_or_404(data['room_id'])
    if room.status != 'available':
        return jsonify({'message': 'Room not available'}), 400
    booking = Booking(student_id=data['student_id'], room_id=data['room_id'])
    room.status = 'occupied'
    db.session.add(booking)
    db.session.commit()
    return jsonify({'message': 'Booking created'}), 201

from flask import current_app

@app.route('/api/test-token', methods=['GET'])
@jwt_required()
def test_token():
    from flask import request
    auth_header = request.headers.get('Authorization', None)
    claims = get_jwt()
    current_app.logger.info(f"Authorization header: {auth_header}")
    current_app.logger.info(f"JWT claims: {claims}")
    return jsonify({'claims': claims}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
