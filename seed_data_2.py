from database_setup import insert_user, insert_timesheet, connect_to_database
from datetime import datetime, timedelta

# Test users data
users = [
    {
        "username": "Adli (Admin)",
        "email": "realblank21@gmail.com",
        "password": "admin123",
        "role": "Admin"
    },
    {
        "username": "Adli",
        "email": "realblanket21@gmail.com",
        "password": "password123",
        "role": "Staff"
    },
    {
        "username": "Maisarah",
        "email": "Maisarah@gmail.com",
        "password": "password123",
        "role": "Staff"
    },
    {
        "username": "Wani",
        "email": "Wani@gmail.com",
        "password": "password123",
        "role": "Staff"
    },
    {
        "username": "Amal",
        "email": "Amal@gmail.com",
        "password": "password123",
        "role": "Staff"
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
    for user in users:
        success = insert_user(
            username=user["username"],
            email=user["email"],
            password=user["password"],
            role=user["role"]
        )
        if success:
            # Get the user_id for the created user
            conn = connect_to_database()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM User WHERE username = %s", (user["username"],))
            user_id = cursor.fetchone()[0]
            user_ids[user["username"]] = user_id
            cursor.close()
            conn.close()
    
    return user_ids

def create_timesheet_entries(user_ids):
    """Create 3 months of timesheet entries for each user with exact working hours"""
    start_date = datetime.now() - timedelta(days=90)
    end_date = datetime.now()
    current_date = start_date

    while current_date <= end_date:
        if is_working_day(current_date):
            work_start, work_end = get_working_hours(current_date)
            
            for username, user_id in user_ids.items():
                if username == "Adli (Admin)":  # Skip timesheet entries for admin
                    continue

                # Everyone checks in and out exactly on time
                insert_timesheet(
                    user_id=user_id,
                    time_in=work_start,
                    time_out=work_end,
                    date=current_date.date(),
                    notes="Regular working day"
                )
        
        current_date += timedelta(days=1)

def main():
    print("Starting to seed data (perfect attendance)...")
    
    # Create users and get their IDs
    print("Creating users...")
    user_ids = create_users()
    
    # Create timesheet entries
    print("Creating timesheet entries...")
    create_timesheet_entries(user_ids)
    
    print("Data seeding completed!")

if __name__ == "__main__":
    main()