import mysql.connector
from dotenv import load_dotenv
import os
import bcrypt
load_dotenv()

MYSQL_USERNAME = os.getenv("MYSQL_USERNAME")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

def hash_password(password):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

def authenticate_password(password, hashed_password):
    try:
      return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
      return False #In case the hash is malformed.

def connect_to_mysql():
    try:
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USERNAME,
            password=MYSQL_PASSWORD
        )
        print("Connected to MySQL server successfully.")
        return connection
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None
    
def connect_to_database():
    try:
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USERNAME,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        print(f"Connected to database {MYSQL_DATABASE} successfully.")
        return connection
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

def drop_database():
    conn = None
    cursor = None

    try:
        conn = connect_to_mysql()

        if conn is None:
            print("Failed to connect to MySQL server.")
            return
        
        cursor = conn.cursor()

        db_name = MYSQL_DATABASE
        
        cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`") 
        conn.commit()
        print(f"Database {db_name} dropped successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def create_database():
    conn = None
    cursor = None

    try:
        conn = connect_to_mysql()

        if conn is None:
            print("Failed to connect to MySQL server.")
            return
        
        cursor = conn.cursor()

        db_name = MYSQL_DATABASE
        
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`") 
        conn.commit()
        print(f"Database {db_name} created successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def create_tables():
    conn = None
    cursor = None

    try:
        conn = connect_to_database()

        if conn is None:
            print("Failed to connect to MySQL server.")
            return

        cursor = conn.cursor()

        create_users_table_query = """
        CREATE TABLE IF NOT EXISTS User (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            profile_picture_url VARCHAR(2048),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            role ENUM('Admin', 'Staff')
        )
        """

        create_timesheet_table_query = """
        CREATE TABLE IF NOT EXISTS Timesheet (
            timesheet_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            time_in TIMESTAMP NULL,
            time_out TIMESTAMP NULL,
            total_time TIME GENERATED ALWAYS AS (
                CASE
                    WHEN time_out IS NOT NULL THEN TIMEDIFF(time_out, time_in)
                    ELSE NULL
                END
            ) VIRTUAL,
            date DATE,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES User(user_id)
        );
        """

        create_leave_table_query = """
        CREATE TABLE IF NOT EXISTS LeaveRecord (
            leave_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            leave_type ENUM('Medical', 'Vacation', 'Personal', 'Other') NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            status ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Pending',
            reason TEXT,
            document_url VARCHAR(2048),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES User(user_id)
        );
        """

        create_working_hours_table_query = """
        CREATE TABLE IF NOT EXISTS WorkingHours (
            id INT AUTO_INCREMENT PRIMARY KEY,
            day_type ENUM('Weekday', 'Saturday') NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            updated_by INT,
            FOREIGN KEY (updated_by) REFERENCES User(user_id)
        );
        """

        cursor.execute(create_users_table_query)
        cursor.execute(create_timesheet_table_query)
        cursor.execute(create_leave_table_query)
        cursor.execute(create_working_hours_table_query)
        
        # Insert default working hours if table is empty
        cursor.execute("SELECT COUNT(*) FROM WorkingHours")
        if cursor.fetchone()[0] == 0:
            default_values = [
                ('Weekday', '09:00:00', '17:30:00', None),
                ('Saturday', '09:00:00', '13:00:00', None)
            ]
            cursor.executemany(
                "INSERT INTO WorkingHours (day_type, start_time, end_time, updated_by) VALUES (%s, %s, %s, %s)",
                default_values
            )

        conn.commit()
        print("Tables created successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def insert_user(username, email, password, role, profile_picture_url=None):
    conn = None
    cursor = None

    try:
        conn = connect_to_database()

        if conn is None:
            print("Failed to connect to MySQL server.")
            return False

        cursor = conn.cursor()

        hashed_password = hash_password(password)
        insert_user_query = """
            INSERT INTO User (username, email, password, role, profile_picture_url)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_user_query, (username, email, hashed_password, role, profile_picture_url))

        conn.commit()
        print("User inserted successfully.")
        return True

    except Exception as e:
        print(f"An error occurred while inserting user: {e}")
        return False

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def insert_timesheet(user_id, time_in, time_out, date, notes):
    conn = None
    cursor = None

    try:
        conn = connect_to_database()

        if conn is None:
            print("Failed to connect to MySQL server.")
            return False

        cursor = conn.cursor()

        insert_timesheet_query = """
            INSERT INTO Timesheet (user_id, time_in, time_out, date, notes)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_timesheet_query, (user_id, time_in, time_out, date, notes))

        conn.commit()
        print("Timesheet entry inserted successfully.")
        return True

    except Exception as e:
        print(f"An error occurred while inserting timesheet: {e}")
        return False

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def insert_leave(user_id, leave_type, start_date, end_date, reason, document_url=None):
    conn = None
    cursor = None

    try:
        conn = connect_to_database()

        if conn is None:
            print("Failed to connect to MySQL server.")
            return False

        cursor = conn.cursor()

        insert_leave_query = """
            INSERT INTO LeaveRecord (user_id, leave_type, start_date, end_date, reason, document_url)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_leave_query, (user_id, leave_type, start_date, end_date, reason, document_url))

        conn.commit()
        print("Leave request inserted successfully.")
        return True

    except Exception as e:
        print(f"An error occurred while inserting leave request: {e}")
        return False

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    drop_database()
    create_database()
    create_tables()
    insert_user("admin", "realblank21@gmail.com", "admin123", "Admin")