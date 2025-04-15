import mysql.connector
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

load_dotenv()

class DatabaseConnection:
    def __init__(self):
        self.MYSQL_USERNAME = os.getenv("MYSQL_USERNAME")
        self.MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
        self.MYSQL_HOST = os.getenv("MYSQL_HOST")
        self.MYSQL_PORT = os.getenv("MYSQL_PORT")
        self.MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

    def connect(self):
        try:
            connection = mysql.connector.connect(
                host=self.MYSQL_HOST,
                user=self.MYSQL_USERNAME,
                password=self.MYSQL_PASSWORD,
                database=self.MYSQL_DATABASE
            )
            return connection
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return None

class DatabaseOperations:
    def __init__(self):
        self.db = DatabaseConnection()

    def execute_query(self, query, params=None):
        """Execute a database query with proper cursor and connection management"""
        conn = None
        cursor = None
        try:
            conn = self.db.connect()
            if conn is None:
                return False, None
            
            cursor = conn.cursor(dictionary=True)
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith("SELECT"):
                result = cursor.fetchall()
                return True, result
            else:
                conn.commit()
                return True, None
                
        except Exception as e:
            print(f"Database error: {e}")
            if conn and not conn.in_transaction:
                conn.rollback()
            return False, None
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_user_by_id(self, user_id):
        query = "SELECT * FROM User WHERE user_id = %s"
        success, result = self.execute_query(query, (user_id,))
        return result[0] if success and result else None

    def get_user_by_email(self, email):
        query = "SELECT * FROM User WHERE email = %s"
        success, result = self.execute_query(query, (email,))
        return result[0] if success and result else None

    def get_user_timesheet(self, user_id, start_date=None, end_date=None):
        query = """
            SELECT * FROM Timesheet 
            WHERE user_id = %s
            AND (%s IS NULL OR date >= %s)
            AND (%s IS NULL OR date <= %s)
            ORDER BY date DESC, time_in DESC
        """
        success, result = self.execute_query(query, (user_id, start_date, start_date, end_date, end_date))
        return result if success else []

    def get_user_leaves(self, user_id, status=None):
        query = """
            SELECT * FROM LeaveRecord 
            WHERE user_id = %s
            AND (%s IS NULL OR status = %s)
            ORDER BY created_at DESC
        """
        success, result = self.execute_query(query, (user_id, status, status))
        return result if success else []

    def insert_timesheet(self, user_id, time_in, time_out, date, notes=None):
        query = """
            INSERT INTO Timesheet (user_id, time_in, time_out, date, notes)
            VALUES (%s, %s, %s, %s, %s)
        """
        return self.execute_query(query, (user_id, time_in, time_out, date, notes))[0]

    def insert_leave(self, user_id, leave_type, start_date, end_date, reason, document_url=None):
        query = """
            INSERT INTO LeaveRecord (user_id, leave_type, start_date, end_date, reason, document_url)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        return self.execute_query(query, (user_id, leave_type, start_date, end_date, reason, document_url))[0]

    def update_leave_status(self, leave_id, status):
        query = "UPDATE LeaveRecord SET status = %s WHERE leave_id = %s"
        return self.execute_query(query, (status, leave_id))[0]

    def update_user_profile(self, user_id, profile_picture_url=None):
        query = "UPDATE User SET profile_picture_url = %s WHERE user_id = %s"
        return self.execute_query(query, (profile_picture_url, user_id))[0]

    def get_today_timesheet(self, user_id):
        """Get today's timesheet entry for the user"""
        query = """
            SELECT * FROM Timesheet 
            WHERE user_id = %s AND date = CURDATE()
        """
        success, result = self.execute_query(query, (user_id,))
        return result[0] if success and result else None

    def record_time_in(self, user_id):
        """Record time in for today"""
        query = """
            INSERT INTO Timesheet (user_id, time_in, date)
            VALUES (%s, NOW(), CURDATE())
        """
        return self.execute_query(query, (user_id,))[0]

    def record_time_out(self, user_id):
        """Record time out for today"""
        query = """
            UPDATE Timesheet 
            SET time_out = NOW()
            WHERE user_id = %s 
            AND date = CURDATE() 
            AND time_out IS NULL
        """
        return self.execute_query(query, (user_id,))[0]

    def update_timesheet_note(self, user_id, note):
        """Update the note for today's timesheet entry"""
        query = """
            UPDATE Timesheet 
            SET notes = %s
            WHERE user_id = %s 
            AND date = CURDATE()
        """
        return self.execute_query(query, (note, user_id))[0]

    def get_total_staff_count(self):
        """Get the total number of staff users"""
        query = "SELECT COUNT(*) as count FROM User WHERE role = 'Staff'"
        success, result = self.execute_query(query)
        return result[0]['count'] if success and result else 0

    def get_staff_present_today(self):
        """Get the count of staff present today (excluding admins)"""
        query = """
            SELECT COUNT(DISTINCT t.user_id) as count 
            FROM Timesheet t
            JOIN User u ON t.user_id = u.user_id
            WHERE t.date = CURDATE()
            AND u.role = 'Staff'
        """
        success, result = self.execute_query(query)
        return result[0]['count'] if success and result else 0

    def get_pending_leaves_count(self):
        """Get the count of pending leave requests (excluding admins)"""
        query = """
            SELECT COUNT(*) as count 
            FROM LeaveRecord l
            JOIN User u ON l.user_id = u.user_id
            WHERE l.status = 'Pending'
            AND u.role = 'Staff'
        """
        success, result = self.execute_query(query)
        return result[0]['count'] if success and result else 0

    def get_today_attendance_all_staff(self):
        """Get today's attendance records for all staff with usernames (excluding admins)"""
        query = """
            SELECT t.*, u.username 
            FROM Timesheet t
            JOIN User u ON t.user_id = u.user_id
            WHERE t.date = CURDATE()
            AND u.role = 'Staff'
            ORDER BY t.time_in DESC
        """
        success, result = self.execute_query(query)
        return result if success else []

    def get_pending_leave_requests(self):
        """Get all pending leave requests with user details (excluding admins)"""
        query = """
            SELECT l.*, u.username 
            FROM LeaveRecord l
            JOIN User u ON l.user_id = u.user_id
            WHERE l.status = 'Pending'
            AND u.role = 'Staff'
            ORDER BY l.created_at ASC
        """
        success, result = self.execute_query(query)
        return result if success else []

    def get_working_hours(self):
        """Get configured working hours"""
        query = "SELECT * FROM WorkingHours ORDER BY day_type"
        success, result = self.execute_query(query)
        return result if success else []

    def update_working_hours(self, day_type, start_time, end_time, admin_id):
        """Update working hours configuration"""
        query = """
            UPDATE WorkingHours 
            SET start_time = %s, end_time = %s, updated_by = %s 
            WHERE day_type = %s
        """
        return self.execute_query(query, (start_time, end_time, admin_id, day_type))[0]

    def get_expected_working_minutes(self, date):
        """Get expected working minutes for a given date
        
        Args:
            date: datetime.date object
            
        Returns:
            int: Expected working minutes for the day, 0 if Sunday
        """
        # Skip Sundays
        if date.isoweekday() == 7:  # Sunday
            return 0
            
        # Get working hours configuration
        day_type = 'Saturday' if date.isoweekday() == 6 else 'Weekday'
        query = "SELECT start_time, end_time FROM WorkingHours WHERE day_type = %s"
        success, result = self.execute_query(query, (day_type,))
        
        if not success or not result:
            return 0
            
        working_hours = result[0]
        
        # Convert timedelta to time object
        start_seconds = int(working_hours['start_time'].total_seconds())
        end_seconds = int(working_hours['end_time'].total_seconds())
        
        start_time = datetime.min.time().replace(
            hour=start_seconds // 3600,
            minute=(start_seconds % 3600) // 60
        )
        end_time = datetime.min.time().replace(
            hour=end_seconds // 3600,
            minute=(end_seconds % 3600) // 60
        )
        
        # Calculate minutes between start and end time
        start_dt = datetime.combine(date, start_time)
        end_dt = datetime.combine(date, end_time)
        return int((end_dt - start_dt).total_seconds() / 60)

    def get_actual_working_minutes(self, user_id, date):
        """Get actual working minutes for a given date and user
        
        Args:
            user_id: int
            date: datetime.date object
            
        Returns:
            int: Actual working minutes for the day, including overtime
        """
        # First check if this is a working day
        if date.isoweekday() == 7:  # Sunday
            return 0
            
        # Check for timesheet entry
        query = """
            SELECT time_in, time_out, notes 
            FROM Timesheet 
            WHERE user_id = %s AND date = %s AND time_out IS NOT NULL
        """
        success, result = self.execute_query(query, (user_id, date))
        
        if not success or not result:
            return 0
            
        entry = result[0]
        
        # If this is a leave entry, count it as full day
        notes = entry.get('notes') or ''  # Handle NULL notes
        if 'leave' in notes.lower():
            return self.get_expected_working_minutes(date)
            
        # Get working hours for this day
        day_type = 'Saturday' if date.isoweekday() == 6 else 'Weekday'
        query = "SELECT start_time, end_time FROM WorkingHours WHERE day_type = %s"
        success, result = self.execute_query(query, (day_type,))
        
        if not success or not result:
            return 0
            
        # Convert the actual times to datetime objects
        actual_start = datetime.combine(date, entry['time_in'].time())
        actual_end = datetime.combine(date, entry['time_out'].time())
        
        # Calculate actual minutes worked including overtime
        if actual_end > actual_start:
            minutes_worked = int((actual_end - actual_start).total_seconds() / 60)
            return minutes_worked
            
        return 0

    def calculate_time_owed(self, user_id, start_date=None, end_date=None):
        """Calculate total time owed by a user
        
        A positive number means the user owes time (worked less than expected)
        A negative number means the user worked extra hours
        
        Args:
            user_id: int
            start_date: datetime.date, defaults to 6 days ago (to get Mon-Sat)
            end_date: datetime.date, defaults to today
            
        Returns:
            int: Total minutes owed
        """
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.now().date()
        if not start_date:
            # Calculate start date to get last 6 working days (Mon-Sat)
            # If today is Sunday, go back 7 days to get last Saturday
            days_to_subtract = 7 if end_date.isoweekday() == 7 else 6
            start_date = end_date - timedelta(days=days_to_subtract)
            
        total_minutes_owed = 0
        current_date = start_date
        
        # Check for approved leaves in this period
        leave_query = """
            SELECT start_date, end_date
            FROM LeaveRecord
            WHERE user_id = %s 
            AND status = 'Approved'
            AND ((start_date BETWEEN %s AND %s) 
                OR (end_date BETWEEN %s AND %s)
                OR (start_date <= %s AND end_date >= %s))
        """
        success, leaves = self.execute_query(
            leave_query, 
            (user_id, start_date, end_date, start_date, end_date, start_date, end_date)
        )
        approved_leave_dates = set()
        
        if success and leaves:
            for leave in leaves:
                leave_start = leave['start_date']
                leave_end = leave['end_date']
                current = leave_start
                while current <= leave_end:
                    # Only include Mon-Sat for leaves
                    if current.isoweekday() <= 6:  
                        approved_leave_dates.add(current)
                    current += timedelta(days=1)
        
        # Calculate for each day in the range
        while current_date <= end_date:
            # Skip if this is a Sunday
            if current_date.isoweekday() == 7:
                current_date += timedelta(days=1)
                continue
                
            # Get expected working minutes for this day
            expected_minutes = self.get_expected_working_minutes(current_date)
            
            if current_date in approved_leave_dates:
                # For approved leave days, actual = expected (no time owed)
                actual_minutes = expected_minutes
            else:
                # Get actual working minutes
                actual_minutes = self.get_actual_working_minutes(user_id, current_date)
            
            # Add the difference to total
            # Positive = time owed, Negative = extra time worked
            total_minutes_owed += expected_minutes - actual_minutes
            current_date += timedelta(days=1)
            
        return total_minutes_owed

    def get_all_staff_time_owed(self):
        """Get time owed for all staff members from their first to last timesheet entry
        
        For missing dates:
        - Sundays are ignored
        - Mon-Sat: Count as full day owed (both time_in and time_out set to start time)
        
        Returns a list of dictionaries with:
            - user_id: int
            - username: str
            - total_minutes_owed: int
        """
        # Get all staff users
        query = "SELECT user_id, username FROM User WHERE role = 'Staff'"
        success, staff_users = self.execute_query(query)
        
        if not success:
            return []
            
        result = []
        
        for user in staff_users:
            # Get first and last timesheet dates for this user
            date_range_query = """
                SELECT MIN(date) as first_date, MAX(date) as last_date
                FROM Timesheet
                WHERE user_id = %s
            """
            success, date_range = self.execute_query(date_range_query, (user['user_id'],))
            
            if not success or not date_range or not date_range[0]['first_date']:
                continue
                
            start_date = date_range[0]['first_date']
            end_date = date_range[0]['last_date']
            
            # Get all timesheet entries within the date range
            timesheet_query = """
                SELECT date, time_in, time_out, notes
                FROM Timesheet
                WHERE user_id = %s
                AND date BETWEEN %s AND %s
            """
            success, timesheet_entries = self.execute_query(
                timesheet_query, 
                (user['user_id'], start_date, end_date)
            )
            
            if not success:
                continue
                
            # Convert timesheet entries to a set of dates for easy lookup
            timesheet_dates = {entry['date'] for entry in timesheet_entries}
            
            total_minutes_owed = 0
            current_date = start_date
            
            # Get approved leaves in this period
            leave_query = """
                SELECT start_date, end_date
                FROM LeaveRecord
                WHERE user_id = %s 
                AND status = 'Approved'
                AND ((start_date BETWEEN %s AND %s) 
                    OR (end_date BETWEEN %s AND %s)
                    OR (start_date <= %s AND end_date >= %s))
            """
            success, leaves = self.execute_query(
                leave_query, 
                (user['user_id'], start_date, end_date, start_date, end_date, start_date, end_date)
            )
            
            # Create set of approved leave dates
            approved_leave_dates = set()
            if success and leaves:
                for leave in leaves:
                    leave_start = leave['start_date']
                    leave_end = leave['end_date']
                    current = leave_start
                    while current <= leave_end:
                        if current.isoweekday() <= 6:  # Only include Mon-Sat
                            approved_leave_dates.add(current)
                        current += timedelta(days=1)
            
            # Process each date in the range
            while current_date <= end_date:
                # Skip Sundays
                if current_date.isoweekday() == 7:
                    current_date += timedelta(days=1)
                    continue
                    
                expected_minutes = self.get_expected_working_minutes(current_date)
                
                if current_date in approved_leave_dates:
                    # For approved leave days, actual = expected (no time owed)
                    actual_minutes = expected_minutes
                elif current_date in timesheet_dates:
                    # For days with timesheet entries, calculate actual minutes
                    actual_minutes = self.get_actual_working_minutes(user['user_id'], current_date)
                else:
                    # For missing workdays, owe the full day
                    actual_minutes = 0
                
                total_minutes_owed += expected_minutes - actual_minutes
                current_date += timedelta(days=1)
            
            result.append({
                'user_id': user['user_id'],
                'username': user['username'],
                'total_minutes_owed': total_minutes_owed
            })
            
        # Sort by most time owed
        return sorted(result, key=lambda x: x['total_minutes_owed'], reverse=True)

    def get_working_hours_for_date(self, date):
        """Get working hours configuration for a specific date"""
        day_type = 'Saturday' if date.weekday() == 5 else 'Weekday'
        
        query = """
            SELECT start_time, end_time
            FROM WorkingHours
            WHERE day_type = %s
        """
        success, result = self.execute_query(query, (day_type,))
        return result[0] if success and result else None

    def create_leave_timesheet_entry(self, user_id, date, reason):
        """Create a timesheet entry for an approved leave day"""
        working_hours = self.get_working_hours_for_date(date)
        if not working_hours:
            return False

        # Convert timedelta to time object
        start_seconds = int(working_hours['start_time'].total_seconds())
        end_seconds = int(working_hours['end_time'].total_seconds())
        
        start_time = datetime.min.time().replace(
            hour=start_seconds // 3600,
            minute=(start_seconds % 3600) // 60
        )
        end_time = datetime.min.time().replace(
            hour=end_seconds // 3600,
            minute=(end_seconds % 3600) // 60
        )
        
        # Combine date with working hours
        time_in = datetime.combine(date, start_time)
        time_out = datetime.combine(date, end_time)
        
        # Delete any existing timesheet entry for this date
        delete_query = """
            DELETE FROM Timesheet
            WHERE user_id = %s AND date = %s
        """
        self.execute_query(delete_query, (user_id, date))
        
        # Insert new timesheet entry with leave information
        query = """
            INSERT INTO Timesheet (user_id, time_in, time_out, date, notes)
            VALUES (%s, %s, %s, %s, %s)
        """
        return self.execute_query(query, (user_id, time_in, time_out, date, reason))[0]

    def process_approved_leave(self, leave_id, status):
        """Process leave approval by updating status and creating timesheet entries"""
        # First get the leave record
        query = """
            SELECT user_id, start_date, end_date, reason
            FROM LeaveRecord
            WHERE leave_id = %s
        """
        success, result = self.execute_query(query, (leave_id,))
        if not success or not result:
            return False

        leave = result[0]
        
        # Update leave status
        status_update = self.update_leave_status(leave_id, status)
        if not status_update:
            return False

        # If approved, create timesheet entries for each day of the leave
        if status == 'Approved':
            current_date = leave['start_date']
            while current_date <= leave['end_date']:
                # Skip Sundays
                if current_date.weekday() != 6:
                    self.create_leave_timesheet_entry(
                        leave['user_id'],
                        current_date,
                        f"On {leave['reason']} leave"
                    )
                current_date += timedelta(days=1)

        return True

    def delete_staff(self, user_id):
        """Delete a staff member and all their related records
        
        Args:
            user_id: int
            
        Returns:
            bool: True if successful, False otherwise
        """
        conn = None
        cursor = None
        try:
            conn = self.db.connect()
            if conn is None:
                return False
            
            # Create cursor with dictionary=True
            cursor = conn.cursor(dictionary=True)
            
            # Start transaction
            conn.start_transaction()
            
            # First verify this is not an admin
            cursor.execute("SELECT role FROM User WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            if not user or user['role'] == 'Admin':
                conn.rollback()
                return False
            
            # Delete timesheet records
            cursor.execute("DELETE FROM Timesheet WHERE user_id = %s", (user_id,))
            
            # Delete leave records
            cursor.execute("DELETE FROM LeaveRecord WHERE user_id = %s", (user_id,))
            
            # Finally delete the user
            cursor.execute("DELETE FROM User WHERE user_id = %s", (user_id,))
            
            # Commit transaction
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error deleting staff: {e}")
            if conn and conn.is_connected():
                conn.rollback()
            return False
            
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()