from database_setup import insert_user, insert_timesheet, connect_to_database, hash_password
from datetime import datetime, timedelta

# Test users data with employment dates
users = [
    {
        "username": "Adli (Admin)",
        "email": "realblank21@gmail.com",
        "password": "admin123",
        "role": "Admin",
        "employment_date": "2023-01-01"
    },
    {
        "username": "Adli",
        "email": "realblanket21@gmail.com",
        "password": "password123",
        "role": "Staff",
        "employment_date": "2023-02-15"
    },
    {
        "username": "Maisarah",
        "email": "Maisarah@gmail.com",
        "password": "password123",
        "role": "Staff",
        "employment_date": "2023-03-01"
    },
    {
        "username": "Wani",
        "email": "Wani@gmail.com",
        "password": "password123",
        "role": "Staff",
        "employment_date": "2023-04-15"
    },
    {
        "username": "Amal",
        "email": "Amal@gmail.com",
        "password": "password123",
        "role": "Staff",
        "employment_date": "2023-05-01"
    }
]

def is_working_day(date):
    """Check if the given date is a working day"""
    return date.weekday() < 6  # Monday (0) to Saturday (5)

def get_working_hours(date):
    """Returns working hours for the given date"""
    if date.weekday() == 5:  # Saturday
        return datetime.combine(date, datetime.min.time().replace(hour=9)), \
               datetime.combine(date, datetime.min.time().replace(hour=13))
    else:  # Monday to Friday
        return datetime.combine(date, datetime.min.time().replace(hour=9)), \
               datetime.combine(date, datetime.min.time().replace(hour=17, minute=30))

def create_users():
    """Create test users"""
    user_ids = {}
    conn = connect_to_database()
    cursor = conn.cursor()
    
    for user in users:
        try:
            # Insert user with employment date
            cursor.execute("""
                INSERT INTO User (username, email, password, role, employment_date)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                user["username"],
                user["email"],
                hash_password(user["password"]),
                user["role"],
                user["employment_date"]
            ))
            conn.commit()
            
            # Get the user_id for the created user
            cursor.execute("SELECT user_id FROM User WHERE username = %s", (user["username"],))
            user_id = cursor.fetchone()[0]
            user_ids[user["username"]] = user_id
            
        except Exception as e:
            print(f"Error creating user {user['username']}: {e}")
            conn.rollback()
    
    cursor.close()
    conn.close()
    return user_ids

def create_timesheet_entries(user_ids):
    """Create 3 months of timesheet entries for each user with perfect attendance"""
    start_date = datetime.now() - timedelta(days=90)
    end_date = datetime.now()
    current_date = start_date

    conn = connect_to_database()
    cursor = conn.cursor()

    while current_date <= end_date:
        if is_working_day(current_date):
            work_start, work_end = get_working_hours(current_date)
            
            for username, user_id in user_ids.items():
                if username == "Adli (Admin)":  # Skip timesheet entries for admin
                    continue

                try:
                    cursor.execute("""
                        INSERT INTO Timesheet (user_id, time_in, time_out, date, notes)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        user_id,
                        work_start,
                        work_end,
                        current_date.date(),
                        "Regular working day"
                    ))
                except Exception as e:
                    print(f"Error creating timesheet entry for {username}: {e}")
                    continue
        
        current_date += timedelta(days=1)
    
    conn.commit()
    cursor.close()
    conn.close()

def create_leave_records(user_ids):
    """Create leave records for staff members with perfect examples"""
    conn = connect_to_database()
    cursor = conn.cursor()
    
    # Example leave records for each staff member
    leave_records = [
        # Adli's leaves
        {
            "username": "Adli",
            "leaves": [
                {
                    "type": "Vacation",
                    "start_date": datetime.now() - timedelta(days=30),
                    "end_date": datetime.now() - timedelta(days=28),
                    "status": "Approved",
                    "reason": "Family vacation"
                },
                {
                    "type": "Medical",
                    "start_date": datetime.now() - timedelta(days=15),
                    "end_date": datetime.now() - timedelta(days=14),
                    "status": "Approved",
                    "reason": "Medical appointment"
                }
            ]
        },
        # Maisarah's leaves
        {
            "username": "Maisarah",
            "leaves": [
                {
                    "type": "Personal",
                    "start_date": datetime.now() - timedelta(days=45),
                    "end_date": datetime.now() - timedelta(days=44),
                    "status": "Approved",
                    "reason": "Personal matters"
                }
            ]
        },
        # Wani's leaves
        {
            "username": "Wani",
            "leaves": [
                {
                    "type": "Vacation",
                    "start_date": datetime.now() - timedelta(days=60),
                    "end_date": datetime.now() - timedelta(days=55),
                    "status": "Approved",
                    "reason": "Annual leave"
                }
            ]
        },
        # Amal's leaves
        {
            "username": "Amal",
            "leaves": [
                {
                    "type": "Medical",
                    "start_date": datetime.now() - timedelta(days=20),
                    "end_date": datetime.now() - timedelta(days=18),
                    "status": "Approved",
                    "reason": "Medical leave"
                }
            ]
        }
    ]
    
    for record in leave_records:
        username = record["username"]
        user_id = user_ids.get(username)
        
        if not user_id:
            continue
            
        for leave in record["leaves"]:
            try:
                cursor.execute("""
                    INSERT INTO LeaveRecord 
                    (user_id, leave_type, start_date, end_date, status, reason)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    leave["type"],
                    leave["start_date"].date(),
                    leave["end_date"].date(),
                    leave["status"],
                    leave["reason"]
                ))
            except Exception as e:
                print(f"Error creating leave record for {username}: {e}")
                continue
    
    conn.commit()
    cursor.close()
    conn.close()

def update_working_hours():
    """Update working hours with standard times"""
    conn = connect_to_database()
    cursor = conn.cursor()
    
    try:
        # Update weekday hours
        cursor.execute("""
            UPDATE WorkingHours 
            SET start_time = %s, end_time = %s 
            WHERE day_type = 'Weekday'
        """, ('09:00:00', '17:30:00'))
        
        # Update Saturday hours
        cursor.execute("""
            UPDATE WorkingHours 
            SET start_time = %s, end_time = %s 
            WHERE day_type = 'Saturday'
        """, ('09:00:00', '13:00:00'))
        
        conn.commit()
    except Exception as e:
        print(f"Error updating working hours: {e}")
        conn.rollback()
    
    cursor.close()
    conn.close()

def main():
    print("Starting to seed data (perfect case example)...")
    
    # Create users and get their IDs
    print("Creating users...")
    user_ids = create_users()
    
    # Create timesheet entries
    print("Creating timesheet entries...")
    create_timesheet_entries(user_ids)
    
    # Create leave records
    print("Creating leave records...")
    create_leave_records(user_ids)
    
    # Update working hours
    print("Updating working hours...")
    update_working_hours()
    
    print("Data seeding completed!")

if __name__ == "__main__":
    main()