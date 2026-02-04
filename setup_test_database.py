#!/usr/bin/env python3
"""
Setup script for test database - Run this ONCE to initialize the test database.
After running this, you can run tests multiple times without reinitializing.

Database credentials can be set via environment variables:
- TEST_DB_USER: PostgreSQL username (default: testuser)
- TEST_DB_PASS: PostgreSQL password (default: testpass)
- TEST_DB_NAME: PostgreSQL database name (default: pricesnapdb)
- TEST_DATABASE_URL: Full database URL (overrides individual settings)

For CI/CD, use GitHub Secrets instead of hardcoding credentials.
"""
import os
import sys

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from database.models import Base


def get_test_database_url():
    """Get test database URL from environment or construct from individual settings."""
    # Check for full URL first
    if os.getenv("TEST_DATABASE_URL"):
        return os.getenv("TEST_DATABASE_URL")
    
    # Otherwise construct from individual settings
    db_user = os.getenv("TEST_DB_USER", "testuser")
    db_pass = os.getenv("TEST_DB_PASS", "testpass")
    db_name = os.getenv("TEST_DB_NAME", "pricesnapdb")
    db_host = os.getenv("TEST_DB_HOST", "localhost")
    db_port = os.getenv("TEST_DB_PORT", "5432")
    
    return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"


def setup_test_database():
    """Create test database and tables once."""
    print("🗄️  Setting up test database...")
    
    TEST_DATABASE_URL = get_test_database_url()
    
    # Mask password in display
    masked_url = TEST_DATABASE_URL.split('@')[0] + '@****'
    print(f"📍 Database URL: {masked_url}")
    
    try:
        # Create engine
        engine = create_engine(TEST_DATABASE_URL)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful!")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ All database tables created successfully!")
        
        # List created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\n📋 Tables created: {', '.join(tables)}")
        
        print("\n🎉 Test database setup complete!")
        print("You can now run tests multiple times with:")
        print("   python -m pytest tests/ -v")
        
        engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n📋 Prerequisites:")
        print("1. PostgreSQL must be running")
        print("2. Run these commands to create database/user:")
        print("   sudo -u postgres psql -c \"CREATE USER $TEST_DB_USER WITH PASSWORD '$TEST_DB_PASS';\"")
        print("   sudo -u postgres psql -c \"CREATE DATABASE $TEST_DB_NAME OWNER $TEST_DB_USER;\"")
        print("\n📝 Or set environment variables:")
        print("   export TEST_DB_USER=your_username")
        print("   export TEST_DB_PASS=your_password")
        print("   export TEST_DB_NAME=your_database")
        return False


if __name__ == '__main__':
    setup_test_database()

