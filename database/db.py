"""
Database connection and session management (PostgreSQL only)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import os

from database.models import Base

load_dotenv()

# Read DATABASE_URL from environment (e.g., Supabase)
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Configure your Postgres connection string in the environment."
    )

# Create PostgreSQL engine with pooling and connection pre-check
engine = create_engine(
    DB_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
    echo=False  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database - create all tables and seed defaults if needed"""
    Base.metadata.create_all(bind=engine)
    
    # Initialize notification settings if not exists
    db = SessionLocal()
    try:
        from database.models import NotificationSettings
        settings = db.query(NotificationSettings).first()
        if not settings:
            settings = NotificationSettings(email="", phone_number="")
            db.add(settings)
            db.commit()
    finally:
        db.close()


def get_db() -> Session:
    """
    Get database session (context-managed generator)
    
    Usage:
        db = get_db()
        try:
            # Use db session
            pass
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """Get a database session (non-generator version for direct use)"""
    return SessionLocal()
