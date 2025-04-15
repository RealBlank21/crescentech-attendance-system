from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from app.authentication import AuthenticationManager
from app.db import DatabaseOperations
from functools import wraps
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta

load_dotenv()

# Configure upload folder
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}

app = Flask(__name__)
app.secret_key = os.getenv('JWT_SECRET_KEY', 'fallback-secret-key')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Set session configuration for 90 days persistence
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=90)
auth_manager = AuthenticationManager()
db = DatabaseOperations()

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'token' not in session:
            return redirect(url_for('login'))
        user, error = auth_manager.require_auth(session['token'])
        if error:
            session.pop('token', None)
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'token' in session:
        user, _ = auth_manager.require_auth(session['token'])
        if user['role'] == 'Admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'token' in session:
        user, _ = auth_manager.require_auth(session['token'])
        if user['role'] == 'Admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        token, error = auth_manager.login(email, password)
        
        if error:
            return render_template('login.html', error=error)
        
        # Make the session permanent before setting the token
        session.permanent = True
        session['token'] = token
        
        # Check user role and redirect accordingly
        user, _ = auth_manager.require_auth(token)
        if user['role'] == 'Admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Get the authenticated user
    user, _ = auth_manager.require_auth(session['token'])
    
    # Get date range from query parameters or use default (last 7 days)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)
    
    if request.args.get('start_date'):
        try:
            start_date = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d').date()
        except ValueError:
            pass
            
    if request.args.get('end_date'):
        try:
            end_date = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Get timesheet entries for the user
    timesheet = db.get_user_timesheet(user['user_id'], start_date, end_date)
    
    # Get leave records for the user
    leave_records = db.get_user_leaves(user['user_id'])
    
    # Get time owed using the same method as admin dashboard
    staff_time = db.get_all_staff_time_owed()
    time_owed = 0
    
    # Find current user's time owed from the result
    for staff in staff_time:
        if staff['user_id'] == user['user_id']:
            time_owed = staff['total_minutes_owed']
            break
    
    return render_template('dashboard.html',
                         user=user,
                         timesheet=timesheet,
                         leave_records=leave_records,
                         start_date=start_date.strftime('%Y-%m-%d'),
                         end_date=end_date.strftime('%Y-%m-%d'),
                         time_owed=time_owed)

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    user, _ = auth_manager.require_auth(session['token'])
    
    # Verify that the user is an admin
    if user['role'] != 'Admin':
        return redirect(url_for('dashboard'))
    
    # Get admin dashboard data
    total_staff = db.get_total_staff_count()
    staff_present = db.get_staff_present_today()
    pending_leaves = db.get_pending_leaves_count()
    today_attendance = db.get_today_attendance_all_staff()
    pending_leave_requests = db.get_pending_leave_requests()
    working_hours = db.get_working_hours()
    staff_time_owed = db.get_all_staff_time_owed()
    
    # Get list of all staff for deletion dropdown
    query = "SELECT user_id, username, role FROM User ORDER BY username"
    success, staff_list = db.execute_query(query)
    if not success:
        staff_list = []
    
    return render_template('admin_dashboard.html',
                         user=user,
                         total_staff=total_staff,
                         staff_present=staff_present,
                         pending_leaves=pending_leaves,
                         today_attendance=today_attendance,
                         pending_leave_requests=pending_leave_requests,
                         working_hours=working_hours,
                         staff_time_owed=staff_time_owed,
                         staff_list=staff_list)

@app.route('/update_working_hours', methods=['POST'])
@login_required
def update_working_hours():
    user, _ = auth_manager.require_auth(session['token'])
    
    # Verify that the user is an admin
    if user['role'] != 'Admin':
        return jsonify({
            'success': False,
            'message': 'Unauthorized access'
        })
    
    data = request.get_json()
    day_type = data.get('day_type')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    if not all([day_type, start_time, end_time]):
        return jsonify({
            'success': False,
            'message': 'Missing required fields'
        })
    
    success = db.update_working_hours(day_type, start_time, end_time, user['user_id'])
    
    return jsonify({
        'success': success,
        'message': 'Working hours updated successfully' if success else 'Failed to update working hours'
    })

@app.route('/update_leave_status', methods=['POST'])
@login_required
def update_leave_status():
    user, _ = auth_manager.require_auth(session['token'])
    
    # Verify that the user is an admin
    if user['role'] != 'Admin':
        return jsonify({
            'success': False,
            'message': 'Unauthorized access'
        })
    
    data = request.get_json()
    leave_id = data.get('leave_id')
    status = data.get('status')
    
    if not leave_id or not status or status not in ['Approved', 'Rejected']:
        return jsonify({
            'success': False,
            'message': 'Invalid request parameters'
        })
    
    success = db.process_approved_leave(leave_id, status)
    
    return jsonify({
        'success': success,
        'message': f'Leave request {status.lower()} successfully' if success else 'Failed to update leave status'
    })

@app.route('/check_time_status')
@login_required
def check_time_status():
    user, _ = auth_manager.require_auth(session['token'])
    today_entry = db.get_today_timesheet(user['user_id'])
    
    can_time_in = today_entry is None
    can_time_out = today_entry is not None and today_entry['time_out'] is None
    current_note = today_entry['notes'] if today_entry else None
    
    return jsonify({
        'can_time_in': can_time_in,
        'can_time_out': can_time_out,
        'current_note': current_note
    })

@app.route('/save_note', methods=['POST'])
@login_required
def save_note():
    user, _ = auth_manager.require_auth(session['token'])
    data = request.get_json()
    note = data.get('note', '').strip()
    
    success = db.update_timesheet_note(user['user_id'], note)
    
    return jsonify({
        'success': success,
        'message': 'Note saved successfully' if success else 'Failed to save note'
    })

@app.route('/time_in', methods=['POST'])
@login_required
def time_in():
    user, _ = auth_manager.require_auth(session['token'])
    today_entry = db.get_today_timesheet(user['user_id'])
    
    if today_entry:
        return jsonify({
            'success': False,
            'message': 'You have already timed in for today'
        })
    
    success = db.record_time_in(user['user_id'])
    
    return jsonify({
        'success': success,
        'message': 'Time in recorded successfully' if success else 'Failed to record time in'
    })

@app.route('/time_out', methods=['POST'])
@login_required
def time_out():
    user, _ = auth_manager.require_auth(session['token'])
    today_entry = db.get_today_timesheet(user['user_id'])
    
    if not today_entry:
        return jsonify({
            'success': False,
            'message': 'You need to time in first'
        })
    
    if today_entry['time_out']:
        return jsonify({
            'success': False,
            'message': 'You have already timed out for today'
        })
    
    success = db.record_time_out(user['user_id'])
    
    return jsonify({
        'success': success,
        'message': 'Time out recorded successfully' if success else 'Failed to record time out'
    })

@app.route('/submit_leave', methods=['POST'])
@login_required
def submit_leave():
    user, _ = auth_manager.require_auth(session['token'])
    
    leave_type = request.form.get('leave_type')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    reason = request.form.get('reason')
    
    # Handle file upload
    document_url = None
    if 'document' in request.files:
        file = request.files['document']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to filename to make it unique
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            document_url = url_for('static', filename=f'uploads/{filename}')
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format')
        return redirect(url_for('dashboard'))
    
    success = db.insert_leave(
        user_id=user['user_id'],
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        document_url=document_url
    )
    
    if success:
        flash('Leave request submitted successfully')
    else:
        flash('Failed to submit leave request')
    
    return redirect(url_for('dashboard'))

@app.route('/add_user', methods=['POST'])
@login_required
def add_user():
    # Verify that the user is an admin
    user, _ = auth_manager.require_auth(session['token'])
    if user['role'] != 'Admin':
        return jsonify({
            'success': False,
            'message': 'Unauthorized access'
        })

    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')

    # Validate required fields
    if not all([username, email, password, role]):
        return jsonify({
            'success': False,
            'message': 'Missing required fields'
        })

    # Register the new user
    success, error = auth_manager.register_user(
        username=username,
        email=email,
        password=password,
        role=role
    )

    if not success:
        return jsonify({
            'success': False,
            'message': error
        })

    return jsonify({
        'success': True,
        'message': 'User created successfully'
    })

@app.route('/delete_staff', methods=['POST'])
@login_required
def delete_staff():
    # Verify that the user is an admin
    user, _ = auth_manager.require_auth(session['token'])
    if user['role'] != 'Admin':
        return jsonify({
            'success': False,
            'message': 'Unauthorized access'
        })

    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({
            'success': False,
            'message': 'User ID is required'
        })

    success = db.delete_staff(user_id)

    return jsonify({
        'success': success,
        'message': 'Staff member deleted successfully' if success else 'Failed to delete staff member'
    })

@app.route('/logout')
def logout():
    session.pop('token', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)