from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from app.authentication import AuthenticationManager
from app.db import DatabaseOperations
from functools import wraps
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO

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
                         staff_list=staff_list,
                         today=datetime.now())

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
    employment_date_str = data.get('employment_date')

    print("Employement Date: " + employment_date_str)

    # Validate required fields
    if not all([username, email, password, role, employment_date_str]):
        return jsonify({
            'success': False,
            'message': 'Missing required fields'
        })
    
    try:
        # Convert string date to datetime.date object
        employment_date = datetime.strptime(employment_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({
            'success': False,
            'message': 'Invalid employment date format'
        })

    # Register the new user
    success, error = auth_manager.register_user(
        username=username,
        email=email,
        password=password,
        role=role,
        employment_date=employment_date
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

@app.route('/get_staff_timesheet')
@login_required
def get_staff_timesheet():
    # Verify that the user is an admin
    user, _ = auth_manager.require_auth(session['token'])
    if user['role'] != 'Admin':
        return jsonify({
            'success': False,
            'message': 'Unauthorized access'
        })

    staff_id = request.args.get('staff_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not all([staff_id, start_date, end_date]):
        return jsonify({
            'success': False,
            'message': 'Missing required parameters'
        })
    
    try:
        # Convert string dates to datetime objects
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Use our existing database method to get timesheet entries
        timesheet_entries = db.get_user_timesheet(staff_id, start_date, end_date)
        
        # Format the timesheet data
        timesheet_data = []
        for entry in timesheet_entries:
            status = 'Present'
            if entry['notes'] and 'leave' in entry['notes'].lower():
                status = 'On Leave'
            
            timesheet_data.append({
                'date': entry['date'].strftime('%Y-%m-%d'),
                'time_in': entry['time_in'].strftime('%I:%M %p') if entry['time_in'] else None,
                'time_out': entry['time_out'].strftime('%I:%M %p') if entry['time_out'] else None,
                'total_hours': str(entry['total_time']) if entry['total_time'] else None,
                'status': status,
                'notes': entry['notes'] or '-'
            })
        
        return jsonify({
            'success': True,
            'timesheet': timesheet_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/logout')
def logout():
    session.pop('token', None)
    return redirect(url_for('login'))

@app.route('/generate_report', methods=['POST'])
@login_required
def generate_report():
    user, _ = auth_manager.require_auth(session['token'])
    
    # Verify that the user is an admin
    if user['role'] != 'Admin':
        return jsonify({
            'success': False,
            'message': 'Unauthorized access'
        }), 403
    
    data = request.get_json()
    print("Received data:", data)  # Debug print
    
    start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
    end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
    print(f"Date range: {start_date} to {end_date}")  # Debug print
    
    # Create a BytesIO buffer to store the PDF
    buffer = BytesIO()
    
    # Create the PDF document
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Add title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30
    )
    elements.append(Paragraph(f"Timesheet Report ({start_date} to {end_date})", title_style))
    elements.append(Spacer(1, 20))
    
    # Get all staff users
    query = "SELECT user_id, username FROM User WHERE role = 'Staff'"
    success, staff_users = db.execute_query(query)
    print(f"Staff users found: {len(staff_users) if success and staff_users else 0}")  # Debug print
    
    if not success or not staff_users:
        return jsonify({
            'success': False,
            'message': 'Failed to fetch staff users'
        }), 500
    
    # Calculate time owed and total hours worked for each staff member in the specified date range
    time_owed_data = [['Staff Name', 'Time Owed', 'Total Hours']]
    for staff in staff_users:
        # Calculate time owed for the specified date range
        time_owed = db.calculate_time_owed(staff['user_id'], start_date, end_date)
        hours = abs(time_owed) // 60
        minutes = abs(time_owed) % 60
        time_str = f"{'+ ' if time_owed < 0 else '- '}{hours} hours {minutes} minutes"
        
        # Calculate total hours worked
        query = """
            SELECT 
                SUM(TIME_TO_SEC(TIMEDIFF(time_out, time_in))) / 3600 as total_hours
            FROM Timesheet 
            WHERE user_id = %s 
            AND date BETWEEN %s AND %s
            AND time_in IS NOT NULL 
            AND time_out IS NOT NULL
        """
        success, result = db.execute_query(query, (staff['user_id'], start_date, end_date))
        total_hours = result[0]['total_hours'] if success and result and result[0]['total_hours'] is not None else 0
        total_hours_str = f"{total_hours:.2f} hours"
        
        time_owed_data.append([staff['username'], time_str, total_hours_str])
    
    time_owed_table = Table(time_owed_data, colWidths=[200, 200, 100])
    time_owed_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF225C')),  # Updated color
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(Paragraph("Staff Time Summary", styles['Heading2']))
    elements.append(Spacer(1, 10))
    elements.append(time_owed_table)
    elements.append(Spacer(1, 30))
    
    # Get leave records for all staff
    query = """
        SELECT u.username, l.start_date, l.end_date, l.leave_type, l.status
        FROM LeaveRecord l
        JOIN User u ON l.user_id = u.user_id
        WHERE l.start_date BETWEEN %s AND %s
        OR l.end_date BETWEEN %s AND %s
        OR (l.start_date <= %s AND l.end_date >= %s)
        ORDER BY l.start_date
    """
    print("Executing leave records query with params:", (start_date, end_date, start_date, end_date, start_date, end_date))  # Debug print
    success, leave_records = db.execute_query(query, (start_date, end_date, start_date, end_date, start_date, end_date))
    print(f"Leave records query success: {success}")  # Debug print
    print(f"Number of leave records found: {len(leave_records) if success and leave_records else 0}")  # Debug print
    
    if success and leave_records:
        # Create leave records table
        leave_data = [['Staff Name', 'Leave Type', 'Start Date', 'End Date', 'Status']]
        for record in leave_records:
            leave_data.append([
                record['username'],
                record['leave_type'],
                record['start_date'].strftime('%Y-%m-%d'),
                record['end_date'].strftime('%Y-%m-%d'),
                record['status']
            ])
        
        leave_table = Table(leave_data, colWidths=[150, 100, 100, 100, 100])
        leave_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF225C')),  # Updated color
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(Paragraph("Leave Records", styles['Heading2']))
        elements.append(Spacer(1, 10))
        elements.append(leave_table)
    
    # Build the PDF
    doc.build(elements)
    
    # Move to the beginning of the BytesIO buffer
    buffer.seek(0)
    
    # Return the PDF file
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'timesheet_report_{start_date}_to_{end_date}.pdf',
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)