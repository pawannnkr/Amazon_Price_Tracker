"""
Test database configuration for PostgreSQL testing.
Provides isolated test database engine and session management.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import os

# Load test environment variables first
load_dotenv(dotenv_path='.env.test')

from database.models import Base

# Get test database URL from environment
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://price_tracker_user:pass@123@localhost:5432/price_tracker_test"
)

# Create PostgreSQL engine for testing with connection pooling
test_engine = create_engine(
    TEST_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
    echo=False  # Set to True for SQL query debugging
)

# Create session factory for tests
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create scoped session for thread safety
TestSession = scoped_session(TestSessionLocal)


def init_test_db():
    """Initialize test database - create all tables"""
    Base.metadata.create_all(bind=test_engine)


def drop_test_db():
    """Drop all tables from test database (use with caution!)"""
    Base.metadata.drop_all(bind=test_engine)


def get_test_db() -> Session:
    """
    Get test database session (context-managed generator)
    
    Usage:
        db = get_test_db()
        try:
            # Use db session
            pass
        finally:
            db.close()
    """
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_test_db_session() -> Session:
    """Get a test database session (non-generator version for direct use)"""
    return TestSessionLocal()


def check_test_db_connection() -> bool:
    """
    Check if test database connection is working.
    Returns True if connection successful, False otherwise.
    """
    try:
        from sqlalchemy import text
        
        with test_engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Test database connection successful!")
            print(f"   PostgreSQL version: {version.split(',')[0]}")
        return True
            
    except Exception as e:
        print(f"❌ Test database connection failed: {e}")
        print("\n💡 To set up the test database:")
        print("1. Make sure PostgreSQL is running")
        print("2. Create the test database:")
        print("   sudo -u postgres psql")
        print("   CREATE DATABASE price_tracker_test;")
        print("   CREATE USER price_tracker_user WITH PASSWORD 'pass@123';")
        print("   GRANT ALL PRIVILEGES ON DATABASE price_tracker_test TO price_tracker_user;")
        print("   \\c price_tracker_test")
        print("   GRANT ALL ON SCHEMA public TO price_tracker_user;")
        return False


# For pytest fixtures - create a fresh database for each test session
@pytest.fixture(scope="session")
def _test_engine():
    """Session-scoped test engine."""
    return test_engine


@pytest.fixture(scope="session")
def _test_db_tables(_test_engine):
    """Create tables once per test session, then drop after all tests."""
    # Create all tables
    Base.metadata.create_all(bind=_test_engine)
    yield
    # Drop all tables after tests complete
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture
def test_session(_test_engine, _test_db_tables):
    """
    Create a test database session with automatic rollback.
    Each test gets a fresh transaction that's rolled back after completion.
    """
    connection = _test_engine.connect()
    transaction = connection.begin()
    
    # Create a session that uses this connection
    session = TestSessionLocal(bind=connection)
    
    yield session
    
    # Rollback the transaction to undo all changes
    session.close()
    transaction.rollback()
    connection.close()

