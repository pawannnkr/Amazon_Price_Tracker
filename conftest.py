"""
Pytest configuration and fixtures for PriceSnap tests.
Uses PostgreSQL test database with transaction rollback for test isolation.

Database credentials can be set via environment variables or .env.test file:
- TEST_DB_USER: PostgreSQL username (default: testuser)
- TEST_DB_PASS: PostgreSQL password (default: testpass)
- TEST_DB_NAME: PostgreSQL database name (default: pricesnapdb)
- TEST_DATABASE_URL: Full database URL (overrides individual settings)

For CI/CD, set these as GitHub Secrets to avoid exposing credentials.
"""
import os
import sys
import pytest
from dotenv import load_dotenv

# Load test environment variables from .env.test if exists
load_dotenv(dotenv_path='.env.test')

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Database Configuration
# ============================================================================

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


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_database_url():
    """Get test database URL from environment."""
    return get_test_database_url()


@pytest.fixture(scope="session")
def test_engine(test_database_url):
    """Create session-scoped test engine."""
    from sqlalchemy import create_engine
    from sqlalchemy.pool import QueuePool
    
    engine = create_engine(
        test_database_url,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False
    )
    
    # Verify connection
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_name = test_database_url.split('/')[-1]
        print(f"✅ Test database connected: {db_name}")
    except Exception as e:
        print(f"⚠️  Test database connection warning: {e}")
    
    yield engine
    
    # Cleanup
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _setup_test_db_tables(test_engine):
    """
    Verify database tables exist (tables should be created once via setup_test_database.py).
    This fixture just verifies connection and table existence without creating/dropping.
    """
    from database.models import Base
    from sqlalchemy import inspect
    
    # Verify tables exist
    inspector = inspect(test_engine)
    existing_tables = inspector.get_table_names()
    
    # Check if our required tables exist
    required_tables = ['users', 'products', 'price_history', 'notification_settings']
    missing_tables = [t for t in required_tables if t not in existing_tables]
    
    if missing_tables:
        print(f"📦 Creating missing tables: {', '.join(missing_tables)}")
        Base.metadata.create_all(bind=test_engine)
        print("✅ Tables created successfully!")
    else:
        print("✅ All test database tables already exist")
    
    yield
    
    # Tables are NOT dropped - they persist for subsequent test runs
    print("✅ Test session complete - tables preserved for next run")


@pytest.fixture
def db_session(test_engine):
    """
    Create a test database session with automatic rollback.
    Each test gets a fresh transaction that's rolled back after completion.
    This ensures complete test isolation.
    """
    from sqlalchemy.orm import sessionmaker
    
    # Create a new session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = SessionLocal()
    
    # Begin a nested transaction
    transaction = session.begin_nested()
    
    yield session
    
    # Rollback to undo all changes made during the test
    session.close()
    transaction.rollback()


@pytest.fixture
def clean_db_session(db_session):
    """
    Database session that ensures complete cleanup after each test.
    Rolls back any changes made during the test.
    """
    yield db_session
    # Explicit rollback to ensure clean state
    db_session.rollback()


# ============================================================================
# Application Fixtures
# ============================================================================

@pytest.fixture
def flask_app():
    """Create and configure test Flask application."""
    from api.app import app
    
    app.config["TESTING"] = True
    app.config["DEBUG"] = False
    
    # Use test database URL
    app.config["TEST_DATABASE_URL"] = get_test_database_url()
    
    yield app


@pytest.fixture
def client(flask_app):
    """Create test client for Flask app."""
    return flask_app.test_client()


@pytest.fixture
def app_client(flask_app):
    """Create test client with app context."""
    with flask_app.test_client() as test_client:
        with flask_app.app_context():
            yield test_client


# ============================================================================
# Data Fixtures
# ============================================================================

@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    from database.models import User
    
    user = User(
        email="test_user@example.com",
        name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    yield user
    
    # Cleanup - user will be rolled back by db_session fixture


@pytest.fixture
def sample_product(db_session, sample_user):
    """Create a sample product for testing."""
    from database.models import Product
    
    product = Product(
        user_id=sample_user.id,
        url="https://www.amazon.in/dp/B08XYZ1234",
        title="Test Product",
        threshold=5000.0,
        current_price=5500.0,
        is_active=True
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    
    yield product


@pytest.fixture
def sample_price_history(db_session, sample_product):
    """Create sample price history entries."""
    from database.models import PriceHistory
    from datetime import datetime, timedelta
    
    prices = [5500.0, 5200.0, 4800.0, 5000.0, 4900.0]
    history_entries = []
    
    for i, price in enumerate(prices):
        entry = PriceHistory(
            product_id=sample_product.id,
            price=price,
            timestamp=datetime.utcnow() - timedelta(days=len(prices) - i)
        )
        db_session.add(entry)
        history_entries.append(entry)
    
    db_session.commit()
    
    yield history_entries


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def smtp_config():
    """Get SMTP configuration for testing notifications."""
    return {
        "server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "email": os.getenv("EMAIL_ID"),
        "password": os.getenv("EMAIL_PASS"),
    }


@pytest.fixture
def cors_config():
    """Get CORS configuration for testing."""
    return {
        "origin": os.getenv("CORS_ORIGIN", "*")
    }


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def api_headers():
    """Default API headers for testing."""
    return {
        "Content-Type": "application/json"
    }


@pytest.fixture
def auth_token():
    """Generate auth token for testing (placeholder)."""
    # In real implementation, this would generate a JWT or similar
    return "test_auth_token_placeholder"

