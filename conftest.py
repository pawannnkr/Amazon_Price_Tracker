"""
Pytest configuration and fixtures for PriceSnap tests.
Uses PostgreSQL test database with transaction rollback for test isolation.
"""
import os
import sys
import pytest
from dotenv import load_dotenv

# Load test environment variables
load_dotenv(dotenv_path='.env.test')

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_database_url():
    """Get test database URL from environment."""
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://price_tracker_user:pass@123@localhost:5432/price_tracker_test"
    )


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
        print(f"✅ Test database connected: {test_database_url.split('@')[0]}@****")
    except Exception as e:
        print(f"⚠️  Test database connection warning: {e}")
    
    yield engine
    
    # Cleanup
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _setup_test_db_tables(test_engine):
    """Create all tables once per test session, drop after all tests complete."""
    from database.models import Base
    
    # Create tables
    Base.metadata.create_all(bind=test_engine)
    print("📦 Test database tables created")
    
    yield
    
    # Drop tables after all tests (optional cleanup)
    # Base.metadata.drop_all(bind=test_engine)
    # print("📦 Test database tables dropped")


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
    app.config["TEST_DATABASE_URL"] = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://price_tracker_user:pass@123@localhost:5432/price_tracker_test"
    )
    
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

