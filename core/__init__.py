"""
Core modules for Amazon Price Tracker
"""
from .price_tracker import PriceTracker
from .notifications import send_mail
from .price_history import PriceHistoryManager

__all__ = ['PriceTracker', 'send_mail', 'PriceHistoryManager']
