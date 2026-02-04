"""
Unit tests for database models.
Tests CRUD operations and model validation using PostgreSQL test database.
"""
import pytest
from datetime import datetime


class TestUserModel:
    """Tests for User model."""
    
    def test_create_user(self, db_session):
        """Test creating a new user."""
        from database.models import User
        
        user = User(
            email="new_test@example.com",
            name="Test User"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "new_test@example.com"
        assert user.name == "Test User"
        assert user.created_at is not None
    
    def test_user_email_unique(self, db_session):
        """Test that email must be unique."""
        from database.models import User
        
        user1 = User(email="unique_test@example.com", name="User 1")
        db_session.add(user1)
        db_session.commit()
        
        # Try to create another user with same email
        user2 = User(email="unique_test@example.com", name="User 2")
        db_session.add(user2)
        
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()
        
        db_session.rollback()
    
    def test_user_email_required(self, db_session):
        """Test that email is required."""
        from database.models import User
        
        user = User(email=None, name="No Email User")
        db_session.add(user)
        
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()
        
        db_session.rollback()
    
    def test_user_repr(self, db_session):
        """Test user string representation."""
        from database.models import User
        
        user = User(email="repr_test@example.com", name="Repr Test")
        db_session.add(user)
        db_session.commit()
        
        assert "User" in repr(user)
        assert "repr_test@example.com" in repr(user)


class TestProductModel:
    """Tests for Product model."""
    
    def test_create_product(self, db_session, sample_user):
        """Test creating a new product."""
        from database.models import Product
        
        product = Product(
            user_id=sample_user.id,
            url="https://www.amazon.in/dp/B0000000001",
            title="Test Product",
            threshold=2999.0,
            current_price=3499.0,
            is_active=True
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)
        
        assert product.id is not None
        assert product.user_id == sample_user.id
        assert product.url == "https://www.amazon.in/dp/B0000000001"
        assert product.threshold == 2999.0
        assert product.is_active is True
    
    def test_product_default_values(self, db_session, sample_user):
        """Test product default values."""
        from database.models import Product
        
        product = Product(
            user_id=sample_user.id,
            url="https://www.amazon.in/dp/B0000000002",
            threshold=1999.0
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)
        
        assert product.is_active is True  # Default value
        assert product.current_price is None  # No initial price
        assert product.title is None
        assert product.created_at is not None
    
    def test_product_url_indexed(self, db_session, sample_user):
        """Test that product URL is indexed."""
        from database.models import Product
        
        # Create product with URL
        product = Product(
            user_id=sample_user.id,
            url="https://www.amazon.in/dp/B0000000003",
            threshold=999.0
        )
        db_session.add(product)
        db_session.commit()
        
        # Query by URL should work
        found = db_session.query(Product).filter(
            Product.url == "https://www.amazon.in/dp/B0000000003"
        ).first()
        
        assert found is not None
        assert found.id == product.id


class TestPriceHistoryModel:
    """Tests for PriceHistory model."""
    
    def test_create_price_history(self, db_session, sample_product):
        """Test creating price history entry."""
        from database.models import PriceHistory
        
        history = PriceHistory(
            product_id=sample_product.id,
            price=4999.0
        )
        db_session.add(history)
        db_session.commit()
        db_session.refresh(history)
        
        assert history.id is not None
        assert history.product_id == sample_product.id
        assert history.price == 4999.0
        assert history.timestamp is not None
    
    def test_price_history_ordering(self, db_session, sample_product):
        """Test that price history is ordered by timestamp."""
        from database.models import PriceHistory
        from datetime import datetime, timedelta
        
        # Create multiple entries
        timestamps = [
            datetime.utcnow() - timedelta(days=3),
            datetime.utcnow() - timedelta(days=2),
            datetime.utcnow() - timedelta(days=1),
            datetime.utcnow()
        ]
        
        for i, ts in enumerate(timestamps):
            entry = PriceHistory(
                product_id=sample_product.id,
                price=5000.0 - (i * 100),
                timestamp=ts
            )
            db_session.add(entry)
        
        db_session.commit()
        
        # Query should return in chronological order
        history = db_session.query(PriceHistory).filter(
            PriceHistory.product_id == sample_product.id
        ).order_by(PriceHistory.timestamp.asc()).all()
        
        assert len(history) == 4
        # Oldest price should be highest (5000 - 0 = 5000)
        assert history[0].price == 5000.0 - (0 * 100)


class TestNotificationSettingsModel:
    """Tests for NotificationSettings model."""
    
    def test_create_notification_settings(self, db_session, sample_user):
        """Test creating notification settings."""
        from database.models import NotificationSettings
        
        settings = NotificationSettings(
            user_id=sample_user.id,
            email="notifications@example.com",
            phone_number="+919876543210"
        )
        db_session.add(settings)
        db_session.commit()
        db_session.refresh(settings)
        
        assert settings.id is not None
        assert settings.user_id == sample_user.id
        assert settings.email == "notifications@example.com"
        assert settings.phone_number == "+919876543210"
    
    def test_notification_settings_one_to_one(self, db_session, sample_user):
        """Test that user can have only one notification setting."""
        from database.models import NotificationSettings
        
        # Create first settings
        settings1 = NotificationSettings(
            user_id=sample_user.id,
            email="first@example.com"
        )
        db_session.add(settings1)
        db_session.commit()
        
        # Try to create second settings for same user
        settings2 = NotificationSettings(
            user_id=sample_user.id,
            email="second@example.com"
        )
        db_session.add(settings2)
        
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()
        
        db_session.rollback()


class TestModelRelationships:
    """Tests for model relationships."""
    
    def test_user_products_relationship(self, db_session, sample_product):
        """Test User -> Products relationship."""
        from database.models import User
        
        user = db_session.query(User).filter(User.id == sample_product.user_id).first()
        
        assert user is not None
        assert len(user.products) >= 1
        assert sample_product in user.products
    
    def test_product_user_relationship(self, db_session, sample_product):
        """Test Product -> User relationship."""
        from database.models import User
        
        user = db_session.query(User).filter(User.id == sample_product.user_id).first()
        
        assert sample_product.user == user
    
    def test_product_price_history_relationship(self, db_session, sample_product, sample_price_history):
        """Test Product -> PriceHistory relationship."""
        from database.models import Product
        
        product = db_session.query(Product).filter(Product.id == sample_product.id).first()
        
        assert len(product.price_history) >= 1
        assert all(h.product_id == product.id for h in product.price_history)
    
    def test_cascade_delete_user(self, db_session, sample_user):
        """Test that deleting user cascades to products and price history."""
        from database.models import User
        
        # Create a product with history for this user
        product = Product(
            user_id=sample_user.id,
            url="https://www.amazon.in/dp/B0000000004",
            threshold=1999.0
        )
        db_session.add(product)
        db_session.commit()
        
        # Add price history
        from database.models import PriceHistory
        history = PriceHistory(product_id=product.id, price=2499.0)
        db_session.add(history)
        db_session.commit()
        
        product_id = product.id
        history_id = history.id
        
        # Delete user
        db_session.delete(sample_user)
        db_session.commit()
        
        # Product and history should be deleted
        product = db_session.query(Product).filter(Product.id == product_id).first()
        history = db_session.query(PriceHistory).filter(PriceHistory.id == history_id).first()
        
        assert product is None
        assert history is None

