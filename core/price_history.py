"""
Price history management with database support
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from typing import List, Dict, Optional
import re
from database.db import get_db_session
from database.models import PriceHistory, Product
from core.url_utils import canonicalize_amazon_url


ASIN_REGEXES = [
    re.compile(r"/dp/([A-Z0-9]{10})", re.IGNORECASE),
    re.compile(r"/gp/product/([A-Z0-9]{10})", re.IGNORECASE),
    re.compile(r"/gp/aw/d/([A-Z0-9]{10})", re.IGNORECASE),
    re.compile(r"/product/([A-Z0-9]{10})", re.IGNORECASE),
    re.compile(r"/[^/]+/dp/([A-Z0-9]{10})", re.IGNORECASE),
]


class PriceHistoryManager:
    """Manages price history storage and retrieval from database"""
    
    def __init__(self):
        self.db = get_db_session()
    
    def __del__(self):
        """Close database session on cleanup"""
        if hasattr(self, 'db'):
            self.db.close()

    def _extract_asin(self, url: str) -> Optional[str]:
        for rx in ASIN_REGEXES:
            m = rx.search(url or "")
            if m:
                return m.group(1).upper()
        return None

    def _find_product_by_url(self, user_id: int, url: str) -> Optional[Product]:
        """
        Resolve a user's product by URL, matching against:
        - Exact stored URL
        - Canonicalized URL (https://host/dp/ASIN)
        - ASIN containment match in stored URLs
        """
        try:
            # Try exact match on provided URL
            product = (
                self.db.query(Product)
                .filter(Product.user_id == user_id, Product.url == url)
                .first()
            )
            if product:
                return product

            # Try canonical URL
            canon = canonicalize_amazon_url(url)
            if canon and canon != url:
                product = (
                    self.db.query(Product)
                    .filter(Product.user_id == user_id, Product.url == canon)
                    .first()
                )
                if product:
                    return product

            # Try ASIN match
            asin = self._extract_asin(url) or self._extract_asin(canon)
            if asin:
                product = (
                    self.db.query(Product)
                    .filter(Product.user_id == user_id, Product.url.ilike(f"%{asin}%"))
                    .first()
                )
                if product:
                    return product
            return None
        except Exception as e:
            print(f"Error resolving product by URL: {e}")
            return None
    
    def add_price_entry(self, product_id: int, price: float):
        """
        Add a price entry to history
        """
        try:
            entry = PriceHistory(
                product_id=product_id,
                price=price,
                timestamp=datetime.utcnow()
            )
            self.db.add(entry)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Error adding price entry: {e}")
    
    def get_price_history(self, user_id: int, url: str, limit: Optional[int] = None) -> Optional[List[Dict]]:
        """
        Get price history for a specific user's product
        """
        try:
            product = self._find_product_by_url(user_id, url)
            if not product:
                return None
            
            query = self.db.query(PriceHistory).filter(PriceHistory.product_id == product.id).order_by(desc(PriceHistory.timestamp))
            
            if limit:
                query = query.limit(limit)
            
            entries = query.all()
            return [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "price": e.price
                }
                for e in entries
            ]
        except Exception as e:
            print(f"Error getting price history: {e}")
            return None
    
    def get_all_history(self, user_id: int) -> Dict:
        """Get all price history for a user"""
        try:
            products = self.db.query(Product).filter(Product.user_id == user_id).all()
            history = {}
            
            for product in products:
                entries = self.db.query(PriceHistory).filter(
                    PriceHistory.product_id == product.id
                ).order_by(desc(PriceHistory.timestamp)).all()
                
                history[product.url] = {
                    "title": product.title,
                    "threshold": product.threshold,
                    "entries": [
                        {
                            "timestamp": e.timestamp.isoformat(),
                            "price": e.price
                        }
                        for e in entries
                    ]
                }
            
            return history
        except Exception as e:
            print(f"Error getting all history: {e}")
            return {}
    
    def get_product_info(self, user_id: int, url: str) -> Optional[Dict]:
        """
        Get product information including history for a user's product
        """
        try:
            product = self._find_product_by_url(user_id, url)
            if not product:
                return None
            
            entries = self.db.query(PriceHistory).filter(
                PriceHistory.product_id == product.id
            ).order_by(PriceHistory.timestamp).all()
            
            prices = [e.price for e in entries] if entries else []
            
            return {
                "url": product.url,
                "title": product.title,
                "threshold": product.threshold,
                "entries": [
                    {
                        "timestamp": e.timestamp.isoformat(),
                        "price": e.price
                    }
                    for e in entries
                ],
                "entry_count": len(entries),
                "first_entry": {
                    "timestamp": entries[0].timestamp.isoformat(),
                    "price": entries[0].price
                } if entries else None,
                "last_entry": {
                    "timestamp": entries[-1].timestamp.isoformat(),
                    "price": entries[-1].price
                } if entries else None,
                "lowest_price": min(prices) if prices else None,
                "highest_price": max(prices) if prices else None,
                "average_price": sum(prices) / len(prices) if prices else None
            }
        except Exception as e:
            print(f"Error getting product info: {e}")
            return None
    
    def get_price_statistics(self, user_id: int, url: str) -> Optional[Dict]:
        """
        Get price statistics for a user's product
        """
        try:
            product = self._find_product_by_url(user_id, url)
            if not product:
                return None
            
            entries = self.db.query(PriceHistory).filter(
                PriceHistory.product_id == product.id
            ).order_by(PriceHistory.timestamp).all()
            
            if not entries:
                return None
            
            prices = [e.price for e in entries]
            
            return {
                "url": product.url,
                "title": product.title,
                "total_entries": len(prices),
                "lowest_price": min(prices),
                "highest_price": max(prices),
                "average_price": sum(prices) / len(prices),
                "current_price": prices[-1],
                "first_price": prices[0],
                "price_change": prices[-1] - prices[0],
                "price_change_percent": ((prices[-1] - prices[0]) / prices[0] * 100) if prices[0] > 0 else 0,
                "threshold": product.threshold
            }
        except Exception as e:
            print(f"Error getting price statistics: {e}")
            return None
    
    def remove_product_history(self, user_id: int, url: str):
        """Remove price history for a user's product"""
        try:
            product = self._find_product_by_url(user_id, url)
            if product:
                # Delete all price history entries
                self.db.query(PriceHistory).filter(PriceHistory.product_id == product.id).delete()
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            print(f"Error removing product history: {e}")
            return False

    def _get_user_product(self, user_id: int, product_id: int) -> Optional[Product]:
        """Fetch a product by id ensuring it belongs to the user"""
        try:
            return (
                self.db.query(Product)
                .filter(Product.id == product_id, Product.user_id == user_id)
                .first()
            )
        except Exception as e:
            print(f"Error getting user product: {e}")
            return None

    def get_price_history_by_product_id(self, user_id: int, product_id: int, limit: Optional[int] = None) -> Optional[List[Dict]]:
        """Get price history for a user's product by product_id"""
        try:
            product = self._get_user_product(user_id, product_id)
            if not product:
                return None
            query = self.db.query(PriceHistory).filter(PriceHistory.product_id == product.id).order_by(desc(PriceHistory.timestamp))
            if limit:
                query = query.limit(limit)
            entries = query.all()
            return [
                {"timestamp": e.timestamp.isoformat(), "price": e.price}
                for e in entries
            ]
        except Exception as e:
            print(f"Error getting price history by id: {e}")
            return None

    def get_product_info_by_product_id(self, user_id: int, product_id: int) -> Optional[Dict]:
        """Get product info and full history by product_id"""
        try:
            product = self._get_user_product(user_id, product_id)
            if not product:
                return None
            entries = self.db.query(PriceHistory).filter(PriceHistory.product_id == product.id).order_by(PriceHistory.timestamp).all()
            prices = [e.price for e in entries] if entries else []
            return {
                "id": product.id,
                "url": product.url,
                "title": product.title,
                "threshold": product.threshold,
                "entries": [
                    {"timestamp": e.timestamp.isoformat(), "price": e.price}
                    for e in entries
                ],
                "entry_count": len(entries),
                "first_entry": {"timestamp": entries[0].timestamp.isoformat(), "price": entries[0].price} if entries else None,
                "last_entry": {"timestamp": entries[-1].timestamp.isoformat(), "price": entries[-1].price} if entries else None,
                "lowest_price": min(prices) if prices else None,
                "highest_price": max(prices) if prices else None,
                "average_price": sum(prices) / len(prices) if prices else None,
            }
        except Exception as e:
            print(f"Error getting product info by id: {e}")
            return None

    def get_price_statistics_by_product_id(self, user_id: int, product_id: int) -> Optional[Dict]:
        """Get price statistics by product_id"""
        try:
            product = self._get_user_product(user_id, product_id)
            if not product:
                return None
            entries = self.db.query(PriceHistory).filter(PriceHistory.product_id == product.id).order_by(PriceHistory.timestamp).all()
            if not entries:
                return None
            prices = [e.price for e in entries]
            return {
                "id": product.id,
                "url": product.url,
                "title": product.title,
                "total_entries": len(prices),
                "lowest_price": min(prices),
                "highest_price": max(prices),
                "average_price": sum(prices) / len(prices),
                "current_price": prices[-1],
                "first_price": prices[0],
                "price_change": prices[-1] - prices[0],
                "price_change_percent": ((prices[-1] - prices[0]) / prices[0] * 100) if prices[0] > 0 else 0,
                "threshold": product.threshold,
            }
        except Exception as e:
            print(f"Error getting price statistics by id: {e}")
            return None

    def remove_product_history_by_product_id(self, user_id: int, product_id: int) -> bool:
        """Remove price history entries by product_id"""
        try:
            product = self._get_user_product(user_id, product_id)
            if not product:
                return False
            self.db.query(PriceHistory).filter(PriceHistory.product_id == product.id).delete()
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            print(f"Error removing product history by id: {e}")
            return False
