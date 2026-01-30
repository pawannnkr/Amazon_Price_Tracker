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
from core.notifications import send_mail
from core.price_history import PriceHistoryManager
from api.schemas import (
    AddProductSchema,
    RemoveProductSchema,
    CheckPriceSchema,
    UpdateNotificationsSchema,
    SendNotificationSchema
)
from database.db import get_db_session
from database.models import User

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


# Users API
@app.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user: { email: str, name?: str }"""
    try:
        if not request.is_json:
            return jsonify({"success": False, "error": "Request must be JSON"}), 400
        data = request.json or {}
        email = (data.get('email') or '').strip()
        name = (data.get('name') or '').strip() or None
        if not email:
            return jsonify({"success": False, "error": "'email' is required"}), 400
        # Basic email format check
        if '@' not in email or '.' not in email.split('@')[-1]:
            return jsonify({"success": False, "error": "Invalid email format"}), 400
        db = get_db_session()
        try:
            # Check uniqueness
            if db.query(User).filter(User.email == email).first():
                return jsonify({"success": False, "error": "Email already exists"}), 409
            user = User(email=email, name=name)
            db.add(user)
            db.commit()
            db.refresh(user)
            return jsonify({
                "success": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
            }), 201
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/users', methods=['GET'])
def list_users():
    """List users, optionally filter by exact email: /api/users?email=..."""
    try:
        email = request.args.get('email')
        db = get_db_session()
        try:
            q = db.query(User)
            if email:
                q = q.filter(User.email == email)
            users = q.order_by(User.id.asc()).all()
            return jsonify({
                "success": True,
                "users": [
                    {
                        "id": u.id,
                        "email": u.email,
                        "name": u.name,
                        "created_at": u.created_at.isoformat() if u.created_at else None
                    }
                    for u in users
                ],
                "count": len(users)
            })
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id: int):
    """Get a single user by id"""
    try:
        db = get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({"success": False, "error": "User not found"}), 404
            return jsonify({
                "success": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
            })
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id: int):
    """Delete a user and cascade their data (products, price history, notifications)"""
    try:
        db = get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return jsonify({"success": False, "error": "User not found"}), 404
            db.delete(user)
            db.commit()
            return jsonify({"success": True, "message": "User deleted"})
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/products', methods=['GET'])
def get_products():
    """Get all tracked products for a user"""
    try:
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify({"success": False, "error": "Missing 'user_id' query parameter"}), 400
        products = tracker.get_all_products(user_id)
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
        user_id = validated_data['user_id']
        url = validated_data['url']
        threshold = validated_data['threshold']
        
        product = tracker.add_product(user_id, url, threshold)
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


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
#@validate_request(remove_product_schema)
#@require_amazon_url()
def remove_product(product_id):
    """
    Remove a product from tracking for a user
    
    Query Parameter:
        user_id (int): Required user ID
    """
    try:
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify({"success": False, "error": "Missing 'user_id' query parameter"}), 400
        if tracker.remove_product(user_id, product_id):
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
        user_id = validated_data['user_id']
        url = validated_data['url']
        
        product = tracker.check_price(user_id, url)
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
    """Update prices for all tracked products for a user"""
    try:
        user_id = request.args.get('user_id', type=int) or (request.json or {}).get('user_id')
        if not user_id:
            return jsonify({"success": False, "error": "Missing 'user_id' parameter"}), 400
        products = tracker.update_all_prices(int(user_id))
        return jsonify({
            "success": True,
            "message": f"Updated {len(products)} products",
            "products": products
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    """Get notification settings for a user"""
    try:
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify({"success": False, "error": "Missing 'user_id' query parameter"}), 400
        notifications = tracker.get_notifications(user_id)
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
        user_id = validated_data['user_id']
        email = validated_data.get('email')
        phone_number = validated_data.get('phone_number')
        
        tracker.update_notifications(user_id=user_id, email=email, phone_number=phone_number)
        return jsonify({
            "success": True,
            "message": "Notification settings updated",
            "notifications": tracker.get_notifications(user_id)
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
        user_id = validated_data['user_id']
        title = validated_data['title']
        url = validated_data['url']
        
        notifications = tracker.get_notifications(user_id)
        email = notifications.get("email")
        # phone_number = notifications.get("phone_number")
        
        results = {
            "email_sent": False,
            # "whatsapp_sent": False
        }
        
        if email:
            results["email_sent"] = send_mail(email, title, url)
        
        # if phone_number:
        #     results["whatsapp_sent"] = send_whatsapp(phone_number, title, url)
        
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
    Check all products for a user and send alerts if prices drop below threshold.
    """
    try:
        user_id = request.args.get('user_id', type=int) or (request.json or {}).get('user_id')
        if not user_id:
            return jsonify({"success": False, "error": "Missing 'user_id' parameter"}), 400
        alerted = tracker.check_and_alert(int(user_id))
        
        return jsonify({
            "success": True,
            "message": f"Checked all products. {len(alerted)} alert(s) sent.",
            "alerted_products": alerted,
            "remaining_products": len(tracker.get_all_products(int(user_id)))
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
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify({"success": False, "error": "Missing 'user_id' query parameter"}), 400
        limit = request.args.get('limit', type=int)
        all_history = history_manager.get_all_history(user_id)
        
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


@app.route('/api/history/by-id', methods=['GET'])
def get_product_history_by_id():
    """
    Get price history for a specific product via product_id
    
    Query Parameters:
        user_id (int, required)
        product_id (int, required)
        limit (int, optional): Maximum number of entries to return
        stats (bool, optional): Include statistics (default: false)
    """
    try:
        user_id = request.args.get('user_id', type=int)
        product_id = request.args.get('product_id', type=int)
        if not user_id:
            return jsonify({"success": False, "error": "Missing 'user_id' query parameter"}), 400
        if not product_id:
            return jsonify({"success": False, "error": "Missing 'product_id' query parameter"}), 400

        limit = request.args.get('limit', type=int)
        include_stats = request.args.get('stats', 'false').lower() == 'true'

        if include_stats:
            stats = history_manager.get_price_statistics_by_product_id(user_id, product_id)
            if stats:
                return jsonify({"success": True, "statistics": stats})
            else:
                return jsonify({"success": False, "error": "Product history not found"}), 404
        else:
            history = history_manager.get_price_history_by_product_id(user_id, product_id, limit=limit)
            if history is not None:
                product_info = history_manager.get_product_info_by_product_id(user_id, product_id)
                return jsonify({
                    "success": True,
                    "product_id": product_id,
                    "title": product_info["title"] if product_info else None,
                    "threshold": product_info["threshold"] if product_info else None,
                    "entries": history,
                    "entry_count": len(history)
                })
            else:
                return jsonify({"success": False, "error": "Product history not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/history/stats/by-id', methods=['GET'])
def get_product_stats_by_id():
    """Get price statistics for a specific product via product_id"""
    try:
        user_id = request.args.get('user_id', type=int)
        product_id = request.args.get('product_id', type=int)
        if not user_id:
            return jsonify({"success": False, "error": "Missing 'user_id' query parameter"}), 400
        if not product_id:
            return jsonify({"success": False, "error": "Missing 'product_id' query parameter"}), 400

        stats = history_manager.get_price_statistics_by_product_id(user_id, product_id)
        if stats:
            return jsonify({"success": True, "statistics": stats})
        else:
            return jsonify({"success": False, "error": "Product history not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/history/<int:product_id>', methods=['GET'])
def get_product_history_by_path(product_id: int):
    """
    Get price history for a specific product by product_id
    
    Query Parameters:
        user_id (int, required)
        limit (int, optional)
        stats (bool, optional)
    """
    try:
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify({"success": False, "error": "Missing 'user_id' query parameter"}), 400
        
        limit = request.args.get('limit', type=int)
        include_stats = request.args.get('stats', 'false').lower() == 'true'
        
        if include_stats:
            stats = history_manager.get_price_statistics_by_product_id(user_id, product_id)
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
            history = history_manager.get_price_history_by_product_id(user_id, product_id, limit=limit)
            if history is not None:
                product_info = history_manager.get_product_info_by_product_id(user_id, product_id)
                return jsonify({
                    "success": True,
                    "product_id": product_id,
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


@app.route('/api/history/<int:product_id>/stats', methods=['GET'])
def get_product_stats_by_path(product_id: int):
    """
    Get price statistics for a specific product by product_id
    """
    try:
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify({"success": False, "error": "Missing 'user_id' query parameter"}), 400
        
        stats = history_manager.get_price_statistics_by_product_id(user_id, product_id)
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


@app.route('/api/history/<int:product_id>', methods=['DELETE'])
def delete_product_history_by_id(product_id: int):
    """
    Delete price history for a specific product by product_id
    """
    try:
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify({"success": False, "error": "Missing 'user_id' query parameter"}), 400
        
        if history_manager.remove_product_history_by_product_id(user_id, product_id):
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
