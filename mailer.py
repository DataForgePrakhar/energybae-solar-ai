"""
mailer.py
Sends solar quotation email with Excel attachment via Gmail.
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

load_dotenv()

GMAIL_USER     = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def send_quotation_email(
    to_email: str,
    customer: dict,
    excel_path: str
) -> dict:
    """
    Send solar quotation email with Excel attached.
    Returns dict with success status and message.
    """

    if not GMAIL_USER or not GMAIL_PASSWORD:
        return {"success": False, "message": "Gmail credentials not configured in .env"}

    if not os.path.exists(excel_path):
        return {"success": False, "message": "Excel file not found. Please regenerate quotation."}

    # ── Build email ────────────────────────────────────────────
    msg = MIMEMultipart()
    msg["From"]    = f"Energybae Solar <{GMAIL_USER}>"
    msg["To"]      = to_email
    msg["Subject"] = f"Your Solar Quotation from Energybae – {customer.get('consumer_name', '')}"

    # ── Email body ─────────────────────────────────────────────
    body = f"""
Dear {customer.get('consumer_name', 'Customer')},

Thank you for your interest in solar energy with Energybae!

Please find your personalized solar quotation below:

━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ☀️  SOLAR QUOTATION SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Consumer No      : {customer.get('consumer_no', '—')}
  Sanctioned Load  : {customer.get('sanctioned_load', '—')}
  Avg Monthly Units: {customer.get('avg_units', '—')} kWh

  ✅ Solar Recommended : {customer.get('solar_capacity', '—')} kWp
  🔢 Number of Panels  : {customer.get('panels_required', '—')}
  💰 Yearly Savings    : ₹{customer.get('yearly_savings', '—')}
  📅 Payback Period    : {customer.get('payback_years', '—')} years

━━━━━━━━━━━━━━━━━━━━━━━━━━━

The detailed Excel quotation is attached to this email.

To learn more about our solar solutions, visit us at:
🌐 www.energybae.in

For any queries, feel free to contact us:
📞 +91 7744977420 / +91 9112233120
📧 freeenergy@energybae.in

Save Energy. Save Money. 🌿

Warm regards,
Team Energybae
Pimpri, Pune – Maharashtra
www.energybae.in
    """.strip()

    msg.attach(MIMEText(body, "plain"))

    # ── Attach Excel ───────────────────────────────────────────
    try:
        with open(excel_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            filename = os.path.basename(excel_path)
            part.add_header("Content-Disposition", f"attachment; filename={filename}")
            msg.attach(part)
    except Exception as e:
        return {"success": False, "message": f"Could not attach Excel: {str(e)}"}

    # ── Send via Gmail ─────────────────────────────────────────
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())
        return {"success": True, "message": f"Quotation sent to {to_email}"}
    except smtplib.SMTPAuthenticationError:
        return {"success": False, "message": "Gmail authentication failed. Check your App Password in .env"}
    except smtplib.SMTPException as e:
        return {"success": False, "message": f"Email sending failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {str(e)}"}