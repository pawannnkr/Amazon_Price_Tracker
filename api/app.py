from flask import Flask, request, jsonify
from flask_cors import CORS
from marshmallow import ValidationError
from functools import wraps
import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.price_tracker import PriceTracker
from core.notifications import send_mail, send_whatsapp
from core.price_history import PriceHistoryManager
from api.schemas import (
    AddProductSchema,
    RemoveProductSchema,
    CheckPriceSchema,
    UpdateNotificationsSchema,
    SendNotificationSchema
)

app = Flask(__name__)
# Structured logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger("api")

# CORS configured via env; default to open during development
cors_origin = os.getenv("CORS_ORIGIN", "*")
if cors_origin == "*" or cors_origin.lower() == "any":
    CORS(app)  # Enable CORS for all routes
else:
    CORS(app, resources={r"/api/*": {"origins": cors_origin}})

# Accept both with and without trailing slashes for all routes
app.url_map.strict_slashes = False

tracker = PriceTracker()
history_manager = PriceHistoryManager()

# Initialize schemas
add_product_schema = AddProductSchema()
remove_product_schema = RemoveProductSchema()
check_price_schema = CheckPriceSchema()
update_notifications_schema = UpdateNotificationsSchema()
send_notification_schema = SendNotificationSchema()


def validate_request(schema):
    """Decorator to validate request body against a schema"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    "success": False,
                    "error": "Request must be JSON"
                }), 400
            
            try:
                # Validate and deserialize input
                data = schema.load(request.json)
                # Pass validated data to the route handler
                return f(validated_data=data, *args, **kwargs)
            except ValidationError as err:
                return jsonify({
                    "success": False,
                    "error": "Validation error",
                    "details": err.messages
                }), 400
        return decorated_function
    return decorator


def is_amazon_url(url: str) -> bool:
    """Validate the URL belongs to an Amazon domain (including amzn.in short links)."""
    try:
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        host = (parsed.netloc or '').lower()
        if not host:
            return False
        allowed = (
            host.endswith("amazon.com") or host.endswith("amazon.in") or host.endswith("amazon.co.uk")
            or host.endswith("amazon.de") or host.endswith("amazon.co.jp") or host.endswith("amazon.ca")
            or host.endswith("amazon.com.au") or host.endswith("amazon.fr") or host.endswith("amazon.it")
            or host.endswith("amazon.es") or host.endswith("amzn.in")
        )
        return allowed
    except Exception:
        return False


def require_amazon_url(field_name: str = 'url'):
    """Decorator to enforce that a given field in validated_data is an Amazon URL."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            validated = kwargs.get('validated_data') or {}
            url = validated.get(field_name)
            if not url or not is_amazon_url(url):
                return jsonify({
                    "success": False,
                    "error": "Invalid URL. Only Amazon product URLs are allowed."
                }), 400
            return f(*args, **kwargs)
        return wrapped
    return decorator


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "Amazon Price Tracker API is running"})


@app.route('/api/products', methods=['GET'])
def get_products():
    """Get all tracked products"""
    try:
        products = tracker.get_all_products()
        return jsonify({
            "success": True,
            "products": products,
            "count": len(products)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/products', methods=['POST'])
@validate_request(add_product_schema)
@require_amazon_url()
def add_product(validated_data):
    """
    Add a new product to track
    
    Request Body:
    {
        "url": "https://www.amazon.in/dp/B08XYZ1234",  # Required: Amazon product URL
        "threshold": 5000.0                            # Required: Price threshold in ₹
    }
    """
    try:
        url = validated_data['url']
        threshold = validated_data['threshold']
        
        product = tracker.add_product(url, threshold)
        if product:
            return jsonify({
                "success": True,
                "message": "Product added successfully",
                "product": product
            }), 201
        else:
            return jsonify({
                "success": False,
                "error": "Failed to fetch product information"
            }), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/products', methods=['DELETE'])
@validate_request(remove_product_schema)
@require_amazon_url()
def remove_product(validated_data):
    """
    Remove a product from tracking
    
    Request Body:
    {
        "url": "https://www.amazon.in/dp/B08XYZ1234"  # Required: Amazon product URL to remove
    }
    """
    try:
        url = validated_data['url']
        
        if tracker.remove_product(url):
            return jsonify({
                "success": True,
                "message": "Product removed successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Product not found"
            }), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/products/check', methods=['POST'])
@validate_request(check_price_schema)
@require_amazon_url()
def check_price(validated_data):
    """
    Check price for a specific product URL
    
    Request Body:
    {
        "url": "https://www.amazon.in/dp/B08XYZ1234"  # Required: Amazon product URL to check
    }
    """
    try:
        url = validated_data['url']
        
        product = tracker.check_price(url)
        if product:
            return jsonify({
                "success": True,
                "product": product
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to fetch product information"
            }), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/products/update-all', methods=['POST'])
def update_all_prices():
    """Update prices for all tracked products"""
    try:
        products = tracker.update_all_prices()
        return jsonify({
            "success": True,
            "message": f"Updated {len(products)} products",
            "products": products
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    """Get notification settings"""
    try:
        notifications = tracker.get_notifications()
        return jsonify({
            "success": True,
            "notifications": notifications
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/notifications', methods=['PUT'])
@validate_request(update_notifications_schema)
def update_notifications(validated_data):
    """
    Update notification settings
    
    Request Body (both fields optional):
    {
        "email": "user@example.com",           # Optional: Email address for notifications
        "phone_number": "+919876543210"        # Optional: Phone number in international format
    }
    """
    try:
        email = validated_data.get('email')
        phone_number = validated_data.get('phone_number')
        
        tracker.update_notifications(email=email, phone_number=phone_number)
        return jsonify({
            "success": True,
            "message": "Notification settings updated",
            "notifications": tracker.get_notifications()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/notify', methods=['POST'])
@app.route('/api/notifications/send', methods=['POST'])
@validate_request(send_notification_schema)
@require_amazon_url()
def send_notification(validated_data):
    """
    Send notification for a product manually
    
    """
    try:
        title = validated_data['title']
        url = validated_data['url']
        
        notifications = tracker.get_notifications()
        email = notifications.get("email")
        phone_number = notifications.get("phone_number")
        
        results = {
            "email_sent": False,
            "whatsapp_sent": False
        }
        
        if email:
            results["email_sent"] = send_mail(email, title, url)
        
        if phone_number:
            results["whatsapp_sent"] = send_whatsapp(phone_number, title, url)
        
        return jsonify({
            "success": True,
            "message": "Notifications sent",
            "results": results
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/track/check', methods=['POST'])
def check_and_alert():
    """
    Check all products and send alerts if prices drop below threshold.
    This applies the main logic from amazon_price.py
    """
    try:
        alerted = tracker.check_and_alert()
        
        return jsonify({
            "success": True,
            "message": f"Checked all products. {len(alerted)} alert(s) sent.",
            "alerted_products": alerted,
            "remaining_products": len(tracker.get_all_products())
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/history', methods=['GET'])
def get_all_history():
    """
    Get price history for all products
    
    Query Parameters:
        limit (int, optional): Maximum number of entries per product to return
    """
    try:
        limit = request.args.get('limit', type=int)
        all_history = history_manager.get_all_history()
        
        # Apply limit if specified
        if limit:
            for url in all_history:
                entries = all_history[url].get("entries", [])
                all_history[url]["entries"] = entries[:limit]
        
        return jsonify({
            "success": True,
            "history": all_history
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/history/by-url', methods=['GET'])
def get_product_history_by_query():
    """
    Get price history for a specific product via query parameter
    
    Query Parameters:
        url (str, required): The product URL (unencoded)
        limit (int, optional): Maximum number of entries to return
        stats (bool, optional): Include statistics (default: false)
    """
    try:
        import urllib.parse
        url = request.args.get('url')
        if not url:
            return jsonify({"success": False, "error": "Missing 'url' query parameter"}), 400
        url = urllib.parse.unquote(url)
        if not is_amazon_url(url):
            return jsonify({"success": False, "error": "Invalid URL. Only Amazon product URLs are allowed."}), 400

        limit = request.args.get('limit', type=int)
        include_stats = request.args.get('stats', 'false').lower() == 'true'

        if include_stats:
            stats = history_manager.get_price_statistics(url)
            if stats:
                return jsonify({"success": True, "statistics": stats})
            else:
                return jsonify({"success": False, "error": "Product history not found"}), 404
        else:
            history = history_manager.get_price_history(url, limit=limit)
            if history is not None:
                product_info = history_manager.get_product_info(url)
                return jsonify({
                    "success": True,
                    "url": url,
                    "title": product_info["title"] if product_info else None,
                    "threshold": product_info["threshold"] if product_info else None,
                    "entries": history,
                    "entry_count": len(history)
                })
            else:
                return jsonify({"success": False, "error": "Product history not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/history/stats/by-url', methods=['GET'])
def get_product_stats_by_query():
    """Get price statistics for a specific product via query parameter"""
    try:
        import urllib.parse
        url = request.args.get('url')
        if not url:
            return jsonify({"success": False, "error": "Missing 'url' query parameter"}), 400
        url = urllib.parse.unquote(url)
        if not is_amazon_url(url):
            return jsonify({"success": False, "error": "Invalid URL. Only Amazon product URLs are allowed."}), 400

        stats = history_manager.get_price_statistics(url)
        if stats:
            return jsonify({"success": True, "statistics": stats})
        else:
            return jsonify({"success": False, "error": "Product history not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/history/<path:url>', methods=['GET'])
def get_product_history(url):
    """
    Get price history for a specific product
    
    Query Parameters:
        limit (int, optional): Maximum number of entries to return
        stats (bool, optional): Include statistics (default: false)
    """
    try:
        import urllib.parse
        url = urllib.parse.unquote(url)
        
        limit = request.args.get('limit', type=int)
        include_stats = request.args.get('stats', 'false').lower() == 'true'
        
        if include_stats:
            # Return with statistics
            stats = history_manager.get_price_statistics(url)
            if stats:
                return jsonify({
                    "success": True,
                    "statistics": stats
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Product history not found"
                }), 404
        else:
            # Return just history entries
            history = history_manager.get_price_history(url, limit=limit)
            if history is not None:
                product_info = history_manager.get_product_info(url)
                return jsonify({
                    "success": True,
                    "url": url,
                    "title": product_info["title"] if product_info else None,
                    "threshold": product_info["threshold"] if product_info else None,
                    "entries": history,
                    "entry_count": len(history)
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Product history not found"
                }), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/history/<path:url>/stats', methods=['GET'])
def get_product_stats(url):
    """
    Get price statistics for a specific product
    """
    try:
        import urllib.parse
        url = urllib.parse.unquote(url)
        
        stats = history_manager.get_price_statistics(url)
        if stats:
            return jsonify({
                "success": True,
                "statistics": stats
            })
        else:
            return jsonify({
                "success": False,
                "error": "Product history not found"
            }), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/history/<path:url>', methods=['DELETE'])
def delete_product_history(url):
    """
    Delete price history for a specific product
    """
    try:
        import urllib.parse
        url = urllib.parse.unquote(url)
        
        if history_manager.remove_product_history(url):
            return jsonify({
                "success": True,
                "message": "Price history deleted successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Product history not found"
            }), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=5000, debug=True)
