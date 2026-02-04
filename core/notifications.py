"""
Notification functions for email and WhatsApp
"""
import smtplib
import datetime
import os
import ssl
import platform
import requests
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr

load_dotenv()
EMAIL_ID = os.getenv("EMAIL_ID")
EMAIL_PASS = os.getenv("EMAIL_PASS")
SMTP_SERVER = os.getenv("SMTP_SERVER")
try:
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
except Exception:
    SMTP_PORT = 587

# Optional WhatsApp Cloud API configuration
# WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
# WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

# Lazy import for pywhatkit to avoid display connection errors when not needed
# _pywhatkit = None

# def _get_pywhatkit():
#     """Lazy import of pywhatkit to avoid display connection errors"""
#     global _pywhatkit
#     if _pywhatkit is None:
#         try:
#             import pywhatkit
#             _pywhatkit = pywhatkit
#         except Exception as e:
#             print(f"⚠️ Warning: pywhatkit not available: {e}")
#             _pywhatkit = False  # Mark as unavailable
#     return _pywhatkit


# def _has_display():
#     """Detect if a GUI/display is available (for pywhatkit)."""
#     if platform.system() == "Linux":
#         return bool(os.getenv("DISPLAY"))
#     # On Windows/macOS assume a display is present when running interactively
#     return True


def send_mail(to_email, title, url):
    """
    Send email notification for price drop, with UTF-8 safe encoding and SMTP TLS/SSL handling.
    
    Args:
        to_email (str): Recipient email address
        title (str): Product title
        url (str): Product URL
    """
    try:
        if not EMAIL_ID or not EMAIL_PASS or not SMTP_SERVER or not SMTP_PORT:
            print("❌ Email config missing: set EMAIL_ID, EMAIL_PASS, SMTP_SERVER, SMTP_PORT")
            return False

        subject = "📉 Price Drop Alert!"
        body = f"Price of {title} has dropped!\n\nCheck it here: {url}"

        msg = MIMEMultipart()
        msg["From"] = formataddr(("PriceSnap", EMAIL_ID))
        msg["To"] = to_email
        msg["Subject"] = str(Header(subject, "utf-8"))
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Use SMTPS for port 465, otherwise STARTTLS
        if SMTP_PORT == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
                server.login(EMAIL_ID, EMAIL_PASS)
                server.sendmail(EMAIL_ID, [to_email], msg.as_string())
        else:
            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(EMAIL_ID, EMAIL_PASS)
                server.sendmail(EMAIL_ID, [to_email], msg.as_string())

        print(f"📧 Email sent for {title}")
        return True
    except Exception as e:
        print("❌ Email error:", e)
        return False


# # def _send_whatsapp_cloud(phone_number, message):
#     """Send WhatsApp message using the WhatsApp Cloud API if configured."""
#     if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
#         return None  # Not configured
#     try:
#         api_url = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
#         headers = {
#             "Authorization": f"Bearer {WHATSAPP_TOKEN}",
#             "Content-Type": "application/json",
#         }
#         payload = {
#             "messaging_product": "whatsapp",
#             "to": phone_number,
#             "type": "text",
#             "text": {"body": message, "preview_url": True},
#         }
#         resp = requests.post(api_url, headers=headers, json=payload, timeout=15)
#         if 200 <= resp.status_code < 300:
#             print("📱 WhatsApp (Cloud API) message sent")
#             return True
#         else:
#             print(f"❌ WhatsApp Cloud API error: {resp.status_code} {resp.text}")
#             return False
#     except Exception as e:
#         print("❌ WhatsApp Cloud API exception:", e)
#         return False


# # def send_whatsapp(phone_number, title, url):
#     """
#     Send WhatsApp notification for price drop.

#     Tries WhatsApp Cloud API first if configured; otherwise falls back to pywhatkit
#     which requires a GUI/browser session logged into WhatsApp Web.
#     """
#     try:
#         msg = f"📢 Price drop alert! {title}\n{url}"

#         # Try Cloud API first if configured
#         cloud_result = _send_whatsapp_cloud(phone_number, msg)
#         if cloud_result is True:
#             return True
#         if cloud_result is False:
#             return False

#         # Fallback to pywhatkit
#         pywhatkit = _get_pywhatkit()
#         if pywhatkit is False or not _has_display():
#             print("❌ WhatsApp not available (requires GUI browser or configure WHATSAPP_TOKEN + WHATSAPP_PHONE_NUMBER_ID)")
#             return False

#         now = datetime.datetime.now()
#         # Schedule 2 minutes in the future to allow WhatsApp Web to open
#         minute = now.minute + 2
#         hour = now.hour
#         if minute >= 60:
#             minute -= 60
#             hour = (hour + 1) % 24

#         pywhatkit.sendwhatmsg(phone_number, msg, hour, minute)
#         print(f"📱 WhatsApp scheduled for {title}")
#         return True
#     except Exception as e:
#         print("❌ WhatsApp error:", e)
#         return False
