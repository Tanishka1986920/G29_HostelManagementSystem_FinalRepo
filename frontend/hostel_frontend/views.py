import requests
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse

API_BASE_URL = 'http://localhost:5000/api'

def login_view(request):
    if request.method == 'POST':
        response = requests.post(f'{API_BASE_URL}/login', json={
            'username': request.POST['username'],
            'password': request.POST['password']
        })
        if response.status_code == 200:
            request.session['token'] = response.json()['access_token']
            return redirect('dashboard')
        messages.error(request, 'Invalid credentials')
    return render(request, 'login.html')

def register_view(request):
    if request.method == 'POST':
        response = requests.post(f'{API_BASE_URL}/register', json={
            'username': request.POST['username'],
            'password': request.POST['password'],
            'role': request.POST['role'],
            'name': request.POST['name'],
            'email': request.POST['email']
        })
        if response.status_code == 201:
            messages.success(request, 'Registration successful. Please log in.')
            return redirect('login')
        else:
            try:
                error_message = response.json().get('message', 'Registration failed')
            except Exception:
                error_message = 'Registration failed'
            messages.error(request, error_message)
    return render(request, 'register.html')

def dashboard(request):
    token = request.session.get('token')
    if not token:
        return redirect('login')
    return render(request, 'dashboard.html')

def rooms(request):
    token = request.session.get('token')
    if not token:
        return redirect('login')
    response = requests.get(f'{API_BASE_URL}/rooms', headers={'Authorization': f'Bearer {token}'})
    if response.status_code != 200:
        messages.error(request, f"Failed to load rooms: {response.text}")
        rooms = []
    else:
        rooms = response.json()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            post_response = requests.post(f'{API_BASE_URL}/rooms', json={
                'number': request.POST['number'],
                'type': request.POST['type']
            }, headers={'Authorization': f'Bearer {token}'})
            if post_response.status_code != 201:
                messages.error(request, f"Failed to create room: {post_response.text}")
        elif action == 'update':
            put_response = requests.put(f'{API_BASE_URL}/rooms/{request.POST["id"]}', json={
                'number': request.POST['number'],
                'type': request.POST['type'],
                'status': request.POST['status']
            }, headers={'Authorization': f'Bearer {token}'})
            if put_response.status_code != 200:
                messages.error(request, f"Failed to update room: {put_response.text}")
        elif action == 'delete':
            delete_response = requests.delete(f'{API_BASE_URL}/rooms/{request.POST["id"]}', headers={'Authorization': f'Bearer {token}'})
            if delete_response.status_code != 200:
                messages.error(request, f"Failed to delete room: {delete_response.text}")
        return redirect('rooms')
    return render(request, 'rooms.html', {'rooms': rooms})

def students(request):
    token = request.session.get('token')
    if not token:
        return redirect('login')
    response = requests.get(f'{API_BASE_URL}/students', headers={'Authorization': f'Bearer {token}'})
    if response.status_code != 200:
        messages.error(request, f"Failed to load students: {response.text}")
        students = []
    else:
        students = response.json()
    if request.method == 'POST':
        post_response = requests.post(f'{API_BASE_URL}/register', json={
            'username': request.POST['username'],
            'password': request.POST['password'],
            'role': 'student',
            'name': request.POST['name'],
            'email': request.POST['email']
        })
        if post_response.status_code != 201:
            try:
                error_message = post_response.json().get('message', 'Failed to register student')
            except Exception:
                error_message = 'Failed to register student'
            messages.error(request, error_message)
        return redirect('students')
    return render(request, 'students.html', {'students': students})

def bookings(request):
    token = request.session.get('token')
    if not token:
        return redirect('login')
    response = requests.get(f'{API_BASE_URL}/bookings', headers={'Authorization': f'Bearer {token}'})
    if response.status_code != 200:
        messages.error(request, f"Failed to load bookings: {response.text}")
        bookings = []
    else:
        bookings = response.json()
    rooms_response = requests.get(f'{API_BASE_URL}/rooms', headers={'Authorization': f'Bearer {token}'})
    if rooms_response.status_code != 200:
        messages.error(request, f"Failed to load rooms: {rooms_response.text}")
        rooms = []
    else:
        rooms = rooms_response.json()
    students_response = requests.get(f'{API_BASE_URL}/students', headers={'Authorization': f'Bearer {token}'})
    if students_response.status_code != 200:
        messages.error(request, f"Failed to load students: {students_response.text}")
        students = []
    else:
        students = students_response.json()
    if request.method == 'POST':
        post_response = requests.post(f'{API_BASE_URL}/bookings', json={
            'student_id': request.POST['student_id'],
            'room_id': request.POST['room_id']
        }, headers={'Authorization': f'Bearer {token}'})
        if post_response.status_code != 201:
            messages.error(request, f"Failed to create booking: {post_response.text}")
        return redirect('bookings')
    return render(request, 'bookings.html', {'bookings': bookings, 'rooms': rooms, 'students': students})

def logout_view(request):
    request.session.flush()
    return redirect('login')

def notices(request):
    token = request.session.get('token')
    if not token:
        return redirect('login')
    response = requests.get(f'{API_BASE_URL}/notices', headers={'Authorization': f'Bearer {token}'})
    if response.status_code != 200:
        messages.error(request, f"Failed to load notices: {response.text}")
        notices = []
    else:
        notices = response.json()
    if request.method == 'POST':
        post_response = requests.post(f'{API_BASE_URL}/notices', json={
            'title': request.POST['title'],
            'content': request.POST['content']
        }, headers={'Authorization': f'Bearer {token}'})
        if post_response.status_code != 201:
            messages.error(request, f"Failed to create notice: {post_response.text}")
        return redirect('notices')
    return render(request, 'notices.html', {'notices': notices})

def leave_requests(request):
    token = request.session.get('token')
    if not token:
        return redirect('login')
    response = requests.get(f'{API_BASE_URL}/leave-requests', headers={'Authorization': f'Bearer {token}'})
    if response.status_code != 200:
        messages.error(request, f"Failed to load leave requests: {response.text}")
        leave_requests = []
    else:
        leave_requests = response.json()
    if request.method == 'POST':
        if 'action' in request.POST and request.POST['action'] in ['approve', 'reject']:
            leave_id = request.POST.get('leave_id')
            status = 'approved' if request.POST['action'] == 'approve' else 'rejected'
            patch_response = requests.patch(f'{API_BASE_URL}/leave-requests/{leave_id}', json={'status': status}, headers={'Authorization': f'Bearer {token}'})
            if patch_response.status_code != 200:
                messages.error(request, f"Failed to update leave request status: {patch_response.text}")
            return redirect('leave_requests')
        else:
            post_response = requests.post(f'{API_BASE_URL}/leave-requests', json={
                'reason': request.POST['reason']
            }, headers={'Authorization': f'Bearer {token}'})
            if post_response.status_code != 201:
                messages.error(request, f"Failed to create leave request: {post_response.text}")
            return redirect('leave_requests')
    # Determine user role for template rendering
    user_role = None
    # Decode token to get role claim without external jwt dependency
    import base64
    import json
    try:
        payload_part = token.split('.')[1]
        # Add padding if necessary
        padding = '=' * (-len(payload_part) % 4)
        payload_part += padding
        decoded_bytes = base64.urlsafe_b64decode(payload_part)
        token_data = json.loads(decoded_bytes)
        user_role = token_data.get('role')
    except Exception:
        user_role = None
    return render(request, 'leave_requests.html', {'leave_requests': leave_requests, 'user_role': user_role})
