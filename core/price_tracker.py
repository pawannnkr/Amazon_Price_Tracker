"""
Core price tracking functionality with database support
"""
import requests
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime
from sqlalchemy.orm import Session
from database.db import get_db_session, init_db
from database.models import Product, PriceHistory, NotificationSettings

load_dotenv()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/113.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}


class PriceTracker:
    """Core price tracking class with database support"""
    
    def __init__(self):
        # Initialize database
        init_db()
        self.db = get_db_session()
    
    def __del__(self):
        """Close database session on cleanup"""
        if hasattr(self, 'db'):
            self.db.close()
    
    def get_price(self, url):
        """
        Fetch current price and title from Amazon product URL
        
        Args:
            url (str): Amazon product URL
            
        Returns:
            tuple: (title, price, final_url) or (None, None, None) if error
        """
        try:
            # Follow redirects to get the actual product page
            page = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
            page.raise_for_status()
            final_url = page.url  # resolved final URL after redirects
            soup = BeautifulSoup(page.content, "html.parser")
            
            # Try multiple methods to find the product title
            title = None
            title_elem = soup.find(id="productTitle")
            if title_elem:
                title = title_elem.get_text().strip()
            else:
                # Try alternative selectors
                title_elem = soup.find("h1", {"data-automation-id": "title"})
                if title_elem:
                    title = title_elem.get_text().strip()
                else:
                    # Try span with class
                    title_elem = soup.find("span", id="productTitle")
                    if title_elem:
                        title = title_elem.get_text().strip()
                    else:
                        # Try meta tag
                        meta_title = soup.find("meta", property="og:title")
                        if meta_title and meta_title.get("content"):
                            title = meta_title.get("content").strip()
            
            if not title:
                raise ValueError("Product title not found")

            # Try multiple methods to find the price
            price_tag = None
            price = None
            
            # Method 1: a-price-whole class
            price_tag = soup.find("span", class_="a-price-whole")
            if price_tag:
                price_text = price_tag.get_text().strip()
            else:
                # Method 2: a-offscreen class
                price_tag = soup.find("span", class_="a-offscreen")
                if price_tag:
                    price_text = price_tag.get_text().strip()
                else:
                    # Method 3: a-price class with a-price-whole inside
                    price_container = soup.find("span", class_="a-price")
                    if price_container:
                        price_tag = price_container.find("span", class_="a-price-whole")
                        if price_tag:
                            price_text = price_tag.get_text().strip()
                        else:
                            # Try a-offscreen inside price container
                            price_tag = price_container.find("span", class_="a-offscreen")
                            if price_tag:
                                price_text = price_tag.get_text().strip()
                            else:
                                raise ValueError("Price element not found")
                    else:
                        # Method 4: Try data-a-color="price" attribute
                        price_tag = soup.find("span", {"data-a-color": "price"})
                        if price_tag:
                            price_whole = price_tag.find("span", class_="a-price-whole")
                            if price_whole:
                                price_text = price_whole.get_text().strip()
                            else:
                                price_text = price_tag.get_text().strip()
                        else:
                            raise ValueError("Price not found on page")
            
            # Extract numeric price value from price_text
            # Clean the price text
            price_text_clean = price_text.replace(",", "").replace("₹", "").replace("$", "").replace("€", "").replace("£", "").strip()
            # Remove any non-numeric characters except decimal point
            price_match = re.search(r'[\d,]+\.?\d*', price_text_clean)
            if price_match:
                price = float(price_match.group().replace(",", ""))
            else:
                raise ValueError(f"Could not extract price from: {price_text}")

            # Save to database (price history is saved in _save_price_to_db)
            if title and price:
                # Update product if exists, price history will be saved separately
                product = self.db.query(Product).filter(Product.url == final_url).first()
                if product:
                    product.title = title
                    product.current_price = price
                    product.updated_at = datetime.utcnow()
                    # Add price history entry
                    history_entry = PriceHistory(
                        product_id=product.id,
                        price=price,
                        timestamp=datetime.utcnow()
                    )
                    self.db.add(history_entry)
                    self.db.commit()

            return title, price, final_url
        except Exception as e:
            print(f"❌ Error fetching price from {url}: {e}")
            return None, None, None
    
    
    def add_product(self, url, threshold):
        """
        Add a product to track
        
        Args:
            url (str): Amazon product URL
            threshold (float): Price threshold for alert
            
        Returns:
            dict: Product info with title and current price
        """
        title, current_price, resolved_url = self.get_price(url)
        if title and current_price:
            try:
                # Check if product already exists (use resolved/canonical URL)
                product = self.db.query(Product).filter(Product.url == resolved_url).first()
                
                if product:
                    # Update existing product
                    product.title = title
                    product.threshold = threshold
                    product.current_price = current_price
                    product.is_active = True
                    product.updated_at = datetime.utcnow()
                else:
                    # Create new product
                    product = Product(
                        url=resolved_url,
                        title=title,
                        threshold=threshold,
                        current_price=current_price,
                        is_active=True
                    )
                    self.db.add(product)
                    self.db.flush()  # Flush to get the product ID
                
                # Add price history entry
                history_entry = PriceHistory(
                    product_id=product.id,
                    price=current_price,
                    timestamp=datetime.utcnow()
                )
                self.db.add(history_entry)
                
                self.db.commit()
                self.db.refresh(product)
                
                return {
                    "id": product.id,
                    "url": product.url,
                    "title": product.title,
                    "threshold": product.threshold,
                    "current_price": product.current_price
                }
            except Exception as e:
                self.db.rollback()
                print(f"Error adding product to database: {e}")
                return None
        return None
    
    def remove_product(self, url):
        """
        Remove a product from tracking (marks as inactive)
        
        Args:
            url (str): Amazon product URL to remove
            
        Returns:
            bool: True if removed, False if not found
        """
        try:
            product = self.db.query(Product).filter(Product.url == url).first()
            if product:
                product.is_active = False
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            print(f"Error removing product: {e}")
            return False
    
    def get_all_products(self):
        """Get all active tracked products"""
        try:
            products = self.db.query(Product).filter(Product.is_active == True).all()
            return [
                {
                    "id": p.id,
                    "url": p.url,
                    "title": p.title,
                    "threshold": p.threshold,
                    "current_price": p.current_price,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None
                }
                for p in products
            ]
        except Exception as e:
            print(f"Error getting products: {e}")
            return []
    
    def update_all_prices(self):
        """Update prices for all tracked products"""
        try:
            products = self.db.query(Product).filter(Product.is_active == True).all()
            updated_products = []
            
            for product in products:
                title, current_price, _ = self.get_price(product.url)
                if title and current_price:
                    product.title = title
                    product.current_price = current_price
                    product.updated_at = datetime.utcnow()
                    updated_products.append({
                        "id": product.id,
                        "url": product.url,
                        "title": product.title,
                        "threshold": product.threshold,
                        "current_price": product.current_price
                    })
            
            self.db.commit()
            return updated_products
        except Exception as e:
            self.db.rollback()
            print(f"Error updating prices: {e}")
            return []
    
    def check_price(self, url):
        """
        Check price for a specific product
        
        Args:
            url (str): Amazon product URL
            
        Returns:
            dict: Product info with updated price
        """
        title, current_price, resolved_url = self.get_price(url)
        if title and current_price:
            try:
                product = self.db.query(Product).filter(Product.url == resolved_url).first()
                if product:
                    product.title = title
                    product.current_price = current_price
                    product.updated_at = datetime.utcnow()
                    self.db.commit()
                    self.db.refresh(product)
                    
                    return {
                        "id": product.id,
                        "url": product.url,
                        "title": product.title,
                        "threshold": product.threshold,
                        "current_price": product.current_price
                    }
                else:
                    # Return new product info if not in database
                    return {
                        "url": resolved_url,
                        "title": title,
                        "current_price": current_price
                    }
            except Exception as e:
                self.db.rollback()
                print(f"Error checking price: {e}")
                return None
        return None
    
    def update_notifications(self, email=None, phone_number=None):
        """
        Update notification settings
        
        Args:
            email (str): Email address for notifications
            phone_number (str): Phone number for WhatsApp notifications
        """
        try:
            settings = self.db.query(NotificationSettings).first()
            if not settings:
                settings = NotificationSettings(email=email or "", phone_number=phone_number or "")
                self.db.add(settings)
            else:
                if email is not None:
                    settings.email = email
                if phone_number is not None:
                    settings.phone_number = phone_number
                settings.updated_at = datetime.utcnow()
            
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Error updating notifications: {e}")
    
    def get_notifications(self):
        """Get notification settings"""
        try:
            settings = self.db.query(NotificationSettings).first()
            if settings:
                return {
                    "email": settings.email or "",
                    "phone_number": settings.phone_number or ""
                }
            return {"email": "", "phone_number": ""}
        except Exception as e:
            print(f"Error getting notifications: {e}")
            return {"email": "", "phone_number": ""}
    
    @property
    def config(self):
        """Compatibility property for backward compatibility"""
        return {
            "notifications": self.get_notifications(),
            "products": self.get_all_products()
        }
    
    def check_and_alert(self, callback=None):
        """
        Check all products and send alerts if price drops below threshold.
        This implements the main tracking logic from amazon_price.py
        
        Args:
            callback (callable): Optional callback function called for each product check.
                                Receives (title, current_price, threshold, url) as arguments.
        
        Returns:
            list: List of products that triggered alerts (were removed)
        """
        from core.notifications import send_mail, send_whatsapp
        
        notifications = self.get_notifications()
        to_email = notifications.get("email")
        phone_number = notifications.get("phone_number")
        
        products = self.db.query(Product).filter(Product.is_active == True).all()
        alerted_products = []
        
        for product in products:
            url = product.url
            threshold = product.threshold
            
            title, current_price, _ = self.get_price(url)
            if title and current_price:
                # Call callback if provided
                if callback:
                    callback(title, current_price, threshold, url)
                else:
                    print(f"{title} -> ₹{current_price} (Target: ₹{threshold})")
                
                if current_price <= threshold:
                    # Price dropped below threshold - send alerts
                    if to_email:
                        send_mail(to_email, title, url)
                    if phone_number:
                        send_whatsapp(phone_number, title, url)
                    
                    # Mark product as inactive (stop tracking once alert sent)
                    product.is_active = False
                    self.db.commit()
                    
                    alerted_products.append({
                        "url": url,
                        "title": title,
                        "price": current_price,
                        "threshold": threshold
                    })
        
        return alerted_products
