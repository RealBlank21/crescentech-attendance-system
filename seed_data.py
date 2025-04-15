from database_setup import insert_user, insert_timesheet, insert_leave, connect_to_database
from datetime import datetime, timedelta
import random

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

# Leave types and reasons
leave_types = ['Medical', 'Vacation', 'Personal']
medical_reasons = ["Doctor's appointment", "Feeling unwell", "Dental checkup"]
vacation_reasons = ["Family vacation", "Short trip", "Taking a break"]
personal_reasons = ["Family matter", "Personal errands", "Important appointment"]

def get_random_time_variation():
    """Returns a random number of minutes (0-15) for varying check-in/out times"""
    return timedelta(minutes=random.randint(0, 15))

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
    """Create 3 months of timesheet entries for each user"""
    start_date = datetime.now() - timedelta(days=90)
    end_date = datetime.now()
    current_date = start_date

    while current_date <= end_date:
        if is_working_day(current_date):
            work_start, work_end = get_working_hours(current_date)
            
            for username, user_id in user_ids.items():
                if username == "admin":  # Skip timesheet entries for admin
                    continue

                # 90% chance of attendance, 10% chance of absence
                if random.random() < 0.9:
                    # Add some randomness to check-in/out times
                    time_in = work_start + get_random_time_variation()
                    time_out = work_end + get_random_time_variation()
                    
                    insert_timesheet(
                        user_id=user_id,
                        time_in=time_in,
                        time_out=time_out,
                        date=current_date.date(),
                        notes="Regular working day"
                    )
        
        current_date += timedelta(days=1)

def create_leave_records(user_ids):
    """Create leave records for users"""
    for username, user_id in user_ids.items():
        if username == "admin":  # Skip leave records for admin
            continue
        
        # Create 2-3 leave records per user
        num_leaves = random.randint(2, 3)
        for _ in range(num_leaves):
            # Random leave duration between 1-3 days
            duration = random.randint(1, 3)
            # Random start date within the last 3 months
            start_date = datetime.now() - timedelta(days=random.randint(1, 85))
            end_date = start_date + timedelta(days=duration)
            
            leave_type = random.choice(leave_types)
            
            # Select appropriate reason based on leave type
            if leave_type == 'Medical':
                reason = random.choice(medical_reasons)
            elif leave_type == 'Vacation':
                reason = random.choice(vacation_reasons)
            else:
                reason = random.choice(personal_reasons)
                
            insert_leave(
                user_id=user_id,
                leave_type=leave_type,
                start_date=start_date.date(),
                end_date=end_date.date(),
                reason=reason
            )

def main():
    print("Starting to seed data...")
    
    # Create users and get their IDs
    print("Creating users...")
    user_ids = create_users()
    
    # Create timesheet entries
    print("Creating timesheet entries...")
    create_timesheet_entries(user_ids)
    
    # Create leave records
    print("Creating leave records...")
    create_leave_records(user_ids)
    
    print("Data seeding completed!")

if __name__ == "__main__":
    main()