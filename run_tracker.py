import time
from core.price_tracker import PriceTracker

def main():
    """Main tracking loop - matches the logic from amazon_price.py"""
    tracker = PriceTracker()
    
    # Get notification settings
    to_email = tracker.config["notifications"].get("email")
    phone_number = tracker.config["notifications"].get("phone_number")
    products = tracker.config["products"]
    
    if not products:
        print("❌ No products to track. Please add products to config.json")
        return
    
    if not to_email and not phone_number:
        print("⚠️ Warning: No notification settings configured.")
        print("   Please set email or phone_number in config.json")
    
    print("🚀 Starting Amazon Price Tracker...")
    print(f"📦 Tracking {len(products)} product(s)")
    print("⏰ Checking prices every 2 hours")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Check all products and send alerts if needed
            alerted = tracker.check_and_alert()
            
            if alerted:
                print(f"\n✅ Sent {len(alerted)} alert(s)")
            
            # Reload products (some may have been removed after alerts)
            products = tracker.get_all_products()
            
            if not products:  # exit if all products alerted
                print("\n✅ All alerts sent. Exiting.")
                break
            
            # Wait 2 hours before next check
            print(f"\n⏳ Waiting 2 hours before next check... ({len(products)} product(s) remaining)")
            time.sleep(7200)  # check every 2 hours
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Tracking stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
