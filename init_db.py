import sys
from database.db import init_db, engine, DB_URL
from sqlalchemy import text

def test_connection():
    """Test database connection before initializing"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f" Database connection failed: {e}")
        print("\n Please ensure:")
        print("1. PostgreSQL is running")
        print("2. Database and user are created")
        print("3. Credentials in .env are correct")
        print("\n To create database and user, run:")
        print("   sudo -u postgres psql -f database/create_db.sql")
        print("   OR")
        print("   sudo -u postgres psql")
        print("   Then execute the SQL commands from database/create_db.sql")
        return False

if __name__ == '__main__':
    print("🗄️  Initializing database...")
    
    # Check if using PostgreSQL
    if not DB_URL.startswith("sqlite"):
        print("🔍 Testing PostgreSQL connection...")
        if not test_connection():
            sys.exit(1)
        print(" Connection successful!")
    
    try:
        init_db()
        print(" Database initialized successfully!")
        if DB_URL.startswith("sqlite"):
            print(" Database file: price_tracker.db")
        else:
            print(f" Database: {DB_URL.split('/')[-1]}")
    except Exception as e:
        print(f" Error initializing database: {e}")
        sys.exit(1)
