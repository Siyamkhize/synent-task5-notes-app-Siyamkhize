import os
import sys
import pymysql
from app import create_app
from models import db

def ensure_database_exists():
    """Connects to the MySQL server and creates the database if it doesn't exist."""
    print("Checking if the database exists on MySQL server...")
    
    # Configuration for connecting to the server itself (no database specified)
    host = "localhost"
    user = "root"
    password = "" # Default XAMPP password is empty
    db_name = "notes_db"
    
    try:
        # Connect to MySQL server
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # Create the database if it doesn't exist
            print(f"Ensuring database '{db_name}' exists...")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            print(f"Database '{db_name}' is ready.")
            
        connection.close()
    except Exception as e:
        print(f"Error connecting to MySQL server: {e}")
        print("\nMake sure your XAMPP MySQL server is running.")
        print("Default connection: host='localhost', user='root', password='' (empty)")
        sys.exit(1)

def initialize_tables():
    """Initializes the database by creating all tables defined in models.py."""
    print("Initializing tables via SQLAlchemy...")
    
    # Create the Flask app instance
    app = create_app()
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("Successfully created all database tables!")
            
            # Print connection info for verification
            db_uri = app.config.get("SQLALCHEMY_DATABASE_URI")
            print(f"Connected via SQLAlchemy to: {db_uri}")
            
        except Exception as e:
            print(f"Error initializing tables: {e}")
            sys.exit(1)

if __name__ == "__main__":
    # 1. Create the database container on the server
    ensure_database_exists()
    
    # 2. Use SQLAlchemy to create the tables inside that database
    initialize_tables()
    
    print("\nDatabase setup complete! You can now run 'python app.py'.")
