from database_setup import insert_user, insert_timesheet, connect_to_database, hash_password
from datetime import datetime, timedelta
import random

# Test users data with employment dates
users = [
    {
        "username": "Adli (Admin)",
        "email": "realblank21@gmail.com",
        "password": "admin123",
        "role": "Admin",
        "employment_date": "2025-02-25"
    },
    {
        "username": "Adli",
        "email": "realblanket21@gmail.com",
        "password": "password123",
        "role": "Staff",
        "employment_date": "2025-02-25"
    },
    {
        "username": "Maisarah",
        "email": "Maisarah@gmail.com",
        "password": "password123",
        "role": "Staff",
        "employment_date": "2025-02-25"
    },
    {
        "username": "Wani",
        "email": "Wani@gmail.com",
        "password": "password123",
        "role": "Staff",
        "employment_date": "2025-02-25"
    },
    {
        "username": "Amal",
        "email": "Amal@gmail.com",
        "password": "password123",
        "role": "Staff",
        "employment_date": "2025-02-25"
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
    """Create timesheet entries with randomized patterns"""
    # Start from employment date
    start_date = datetime.strptime("2025-02-25", "%Y-%m-%d")
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

                # Random patterns for each user
                pattern = random.random()
                
                if pattern < 0.05:  # 5% chance of absence
                    continue
                elif pattern < 0.15:  # 10% chance of late arrival
                    time_in = work_start + timedelta(minutes=random.randint(15, 45))
                    time_out = work_end + timedelta(minutes=random.randint(0, 30))
                elif pattern < 0.25:  # 10% chance of early arrival
                    time_in = work_start - timedelta(minutes=random.randint(15, 30))
                    time_out = work_end - timedelta(minutes=random.randint(0, 15))
                else:  # 75% chance of normal attendance
                    time_in = work_start + timedelta(minutes=random.randint(-5, 5))
                    time_out = work_end + timedelta(minutes=random.randint(-5, 5))

                try:
                    cursor.execute("""
                        INSERT INTO Timesheet (user_id, time_in, time_out, date, notes)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        user_id,
                        time_in,
                        time_out,
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
    """Create randomized leave records for staff members"""
    leave_types = ['Medical', 'Vacation', 'Personal', 'Other']
    statuses = ['Pending', 'Approved', 'Rejected']
    
    conn = connect_to_database()
    cursor = conn.cursor()
    
    for username, user_id in user_ids.items():
        if username == "Adli (Admin)":  # Skip leave records for admin
            continue
            
        # Create 3-5 leave records per staff
        for _ in range(random.randint(3, 5)):
            # Random start date between employment date and now
            start_date = datetime.strptime("2025-02-25", "%Y-%m-%d") + timedelta(days=random.randint(1, 60))
            # Random duration between 1-7 days
            end_date = start_date + timedelta(days=random.randint(1, 7))
            
            # Ensure end date doesn't exceed current date
            if end_date > datetime.now():
                end_date = datetime.now()
            
            try:
                cursor.execute("""
                    INSERT INTO LeaveRecord 
                    (user_id, leave_type, start_date, end_date, status, reason)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    random.choice(leave_types),
                    start_date.date(),
                    end_date.date(),
                    random.choice(statuses),
                    f"{random.choice(leave_types)} leave request for {username}"
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
    print("Starting to seed data (randomized patterns)...")
    
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