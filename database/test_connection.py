#!/usr/bin/env python3
"""
Test PostgreSQL database connection
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from database.db import engine, DB_URL
    from sqlalchemy import text
    
    print("🔍 Testing database connection...")
    print(f"📡 Connection URL: {DB_URL.split('@')[0]}@****")  # Hide password
    
    # Test connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"Connection successful!")
        print(f"PostgreSQL version: {version.split(',')[0]}")
        return True
        
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\n💡 Troubleshooting:")
    print("1. Make sure PostgreSQL is running:")
    print("   sudo systemctl status postgresql")
    print("\n2. Verify your credentials in .env file")
    print("\n3. Create the database and user:")
    print("   sudo -u postgres psql")
    print("   CREATE DATABASE price_tracker;")
    print("   CREATE USER price_tracker_user WITH PASSWORD 'pass@123';")
    print("   GRANT ALL PRIVILEGES ON DATABASE price_tracker TO price_tracker_user;")
    print("   \\c price_tracker")
    print("   GRANT ALL ON SCHEMA public TO price_tracker_user;")
    return False
