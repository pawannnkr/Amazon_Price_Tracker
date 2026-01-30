import os
import sys
import pytest
from dotenv import load_dotenv

# Load test environment
load_dotenv()

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fixtures for common test setup
@pytest.fixture(scope="session")
def database_url():
    """Get test database URL from environment"""
    return os.getenv("DATABASE_URL", "sqlite:///:memory:")

@pytest.fixture(scope="session")
def smtp_config():
    """Get SMTP configuration"""
    return {
        "server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "email": os.getenv("EMAIL_ID"),
        "password": os.getenv("EMAIL_PASS"),
    }

@pytest.fixture
def flask_app():
    """Create and configure test Flask app"""
    from api.app import app
    
    app.config["TESTING"] = True
    app.config["DATABASE_URL"] = "sqlite:///:memory:"
    
    with app.app_context():
        yield app

@pytest.fixture
def client(flask_app):
    """Create test client"""
    return flask_app.test_client()

@pytest.fixture
def db_session():
    """Create test database session"""
    from database.db import get_db_session, init_db
    
    # Initialize test DB
    init_db()
    session = get_db_session()
    
    yield session
    
    session.close()
