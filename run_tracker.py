import time
from typing import Optional, List
from core.price_tracker import PriceTracker
from database.db import get_db_session
from database.models import User


def _run_for_user(tracker: PriceTracker, user_id: int) -> int:
    """Run a single check-and-alert cycle for one user. Returns remaining product count."""
    try:
        notifications = tracker.get_notifications(user_id)
        to_email = notifications.get("email")
        phone_number = notifications.get("phone_number")
        products = tracker.get_all_products(user_id)

        print(f"\n=== User {user_id} ===")
        if not products:
            print("No products to track for this user.")
            return 0

        if not to_email and not phone_number:
            print("Warning: No notification settings configured for this user.")

        alerted = tracker.check_and_alert(user_id)
        if alerted:
            print(f"Sent {len(alerted)} alert(s) for user {user_id}")

        remaining = len(tracker.get_all_products(user_id))
        print(f"Remaining products for user {user_id}: {remaining}")
        return remaining
    except Exception as e:
        print(f"Error processing user {user_id}: {e}")
        return 0


def main(user_id: Optional[int] = None):
    """Run the tracker.

    - If user_id is provided: loop for that user only until all alerts sent.
    - If user_id is None: iterate through all users in DB on each cycle.
    """
    tracker = PriceTracker()

    if user_id is not None:
        print("🚀 Starting Amazon Price Tracker for a single user...")
        print("⏰ Checking prices every 2 hours. Press Ctrl+C to stop.\n")
        try:
            while True:
                remaining = _run_for_user(tracker, user_id)
                if remaining == 0:
                    print("\n✅ All alerts sent for this user. Exiting.")
                    break
                print("\n⏳ Waiting 2 hours before next check...")
                time.sleep(7200)
        except KeyboardInterrupt:
            print("\n\n⏹️  Tracking stopped by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")
        return

    # Multi-user mode
    print("🚀 Starting Amazon Price Tracker for all users...")
    print("⏰ Checking prices every 2 hours. Press Ctrl+C to stop.\n")
    try:
        while True:
            # Fetch all users
            db = get_db_session()
            try:
                users: List[User] = db.query(User).order_by(User.id.asc()).all()
            finally:
                db.close()

            if not users:
                print("❌ No users found in database. Sleeping 30 minutes before retry...")
                time.sleep(1800)
                continue

            total_remaining = 0
            for u in users:
                total_remaining += _run_for_user(tracker, u.id)

            if total_remaining == 0:
                print("\n✅ All alerts sent for all users. Exiting.")
                break

            print(f"\n⏳ Waiting 2 hours before next check... (remaining across users: {total_remaining})")
            time.sleep(7200)

    except KeyboardInterrupt:
        print("\n\n⏹️  Tracking stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run price tracker")
    parser.add_argument(
        "user_id",
        type=int,
        nargs="?",
        help="User ID to run tracking for. If omitted, runs for all users.",
    )
    args = parser.parse_args()
    main(args.user_id)
