import requests
import time
import smtplib
import datetime
import os
import json
from bs4 import BeautifulSoup
import pywhatkit
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
EMAIL_ID = os.getenv("EMAIL_ID")
EMAIL_PASS = os.getenv("EMAIL_PASS")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))  # default to 587 if not set

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/113.0.0.0 Safari/537.36"
    )
}


# --- Notification Functions ---
def send_mail(to_email, title, url):
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ID, EMAIL_PASS)
        subject = "📉 Price Drop Alert!"
        body = f"Price of {title} has dropped!\n\nCheck it here: {url}"
        msg = f"Subject:{subject}\n\n{body}"
        server.sendmail(EMAIL_ID, to_email, msg)
        server.quit()
        print(f"📧 Email sent for {title}")
    except Exception as e:
        print("❌ Email error:", e)


def send_whatsapp(phone_number, title, url):
    try:
        now = datetime.datetime.now()
        msg = f"📢 Price drop alert! {title}\n{url}"
        pywhatkit.sendwhatmsg(phone_number, msg, now.hour, now.minute + 1)
        print(f"📱 WhatsApp scheduled for {title}")
    except Exception as e:
        print("❌ WhatsApp error:", e)


# --- Price Tracker ---
def get_price(url):
    try:
        page = requests.get(url, headers=HEADERS, timeout=10)
        page.raise_for_status()
        soup = BeautifulSoup(page.content, "html.parser")
        title = soup.find(id="productTitle").get_text().strip()

        price_tag = soup.find("span", class_="a-price-whole")
        if not price_tag:
            price_tag = soup.find("span", class_="a-offscreen")
        if not price_tag:
            raise ValueError("Price not found")

        price = float(price_tag.get_text().replace(",", "").replace("₹", "").strip())
        return title, price
    except Exception as e:
        print(f"❌ Error fetching price from {url}: {e}")
        return None, None


# --- Main ---
if __name__ == "__main__":
    # Load config.json
    with open("config.json", "r") as f:
        config = json.load(f)

    to_email = config["notifications"]["email"]
    phone_number = config["notifications"]["phone_number"]
    products = config["products"]

    while True:
        for product in products:
            url = product["url"]
            threshold = product["threshold"]

            title, current_price = get_price(url)
            if title and current_price:
                print(f"{title} -> ₹{current_price} (Target: ₹{threshold})")
                if current_price <= threshold:
                    send_mail(to_email, title, url)
                    send_whatsapp(phone_number, title, url)
                    products.remove(product)  # stop tracking once alert sent

        if not products:  # exit if all products alerted
            print("✅ All alerts sent. Exiting.")
            break

        time.sleep(7200)  # check every 2 hours
