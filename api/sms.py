"""
api/sms.py
Twilio SMS emergency advisory dispatch service for ThermalGuard.
Supports real Twilio REST API delivery when configured in .env or environment,
with graceful fallback/simulated mode when credentials are not yet set.
"""

import os
import re
import uuid
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.is_file():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

try:
    from twilio.rest import Client
except ImportError:
    Client = None

logger = logging.getLogger("thermalguard.sms")

def format_phone_number(phone: str, default_country: str = "+91") -> str:
    """Formats phone number to E.164 standard (+[country_code][number])."""
    if not phone:
        return ""
    stripped = re.sub(r"[^\d+]", "", str(phone).strip())
    if stripped.startswith("+"):
        return stripped
    if len(stripped) == 10:
        return f"{default_country}{stripped}"
    if len(stripped) == 12 and stripped.startswith("91"):
        return f"+{stripped}"
    return f"+{stripped}"

def get_twilio_credentials() -> Dict[str, Optional[str]]:
    """Retrieves Twilio configuration from environment."""
    return {
        "account_sid": os.getenv("TWILIO_ACCOUNT_SID"),
        "auth_token": os.getenv("TWILIO_AUTH_TOKEN"),
        "from_number": os.getenv("TWILIO_PHONE_NUMBER") or os.getenv("TWILIO_FROM_NUMBER"),
    }

def is_valid_twilio_config(creds: Dict[str, Optional[str]]) -> bool:
    """Checks if credentials are real credentials and not empty/placeholder strings."""
    sid = (creds.get("account_sid") or "").strip()
    token = (creds.get("auth_token") or "").strip()
    number = (creds.get("from_number") or "").strip()
    if not (sid and token and number):
        return False
    if "XXXX" in sid or "your_" in token or "your_" in sid or number.startswith("+12345678"):
        return False
    return True

def send_twilio_sms(to_number: str, body: str) -> Dict[str, Any]:
    """
    Sends an SMS message to a single recipient using Twilio.
    If Twilio credentials are not set or are placeholders, records a simulated dispatch.
    """
    formatted_to = format_phone_number(to_number)
    creds = get_twilio_credentials()

    account_sid = creds["account_sid"]
    auth_token = creds["auth_token"]
    from_number = creds["from_number"]

    # Live Twilio Dispatch
    if Client and is_valid_twilio_config(creds):
        try:
            client = Client(account_sid, auth_token)
            msg = client.messages.create(
                to=formatted_to,
                from_=from_number,
                body=body,
            )
            logger.info(f"Twilio SMS sent to {formatted_to}: SID={msg.sid}, Status={msg.status}")
            return {
                "success": True,
                "sid": msg.sid,
                "status": getattr(msg, "status", "sent"),
                "to": formatted_to,
                "mode": "live",
                "error": None,
            }
        except Exception as e:
            logger.error(f"Twilio SMS failed to {formatted_to}: {e}")
            return {
                "success": False,
                "sid": None,
                "status": "failed",
                "to": formatted_to,
                "mode": "live",
                "error": str(e),
            }

    # Simulated Fallback (no credentials configured)
    simulated_sid = f"SM_SIM_{uuid.uuid4().hex[:24]}"
    logger.info(f"[SIMULATED] Twilio SMS dispatched to {formatted_to}: {simulated_sid}")
    return {
        "success": True,
        "sid": simulated_sid,
        "status": "simulated",
        "to": formatted_to,
        "mode": "simulated",
        "error": None,
        "note": "Configure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER in .env for live carrier delivery.",
    }

def send_bulk_twilio_sms(recipients: List[Dict[str, Any]], body: str) -> List[Dict[str, Any]]:
    """Dispatches SMS to a list of recipients ({ 'phone': ..., 'name': ... })."""
    results = []
    for r in recipients:
        phone = r.get("phone")
        if not phone:
            continue
        res = send_twilio_sms(phone, body)
        res["facility_name"] = r.get("name") or r.get("facility_name")
        res["facility_id"] = r.get("id") or r.get("facility_id")
        results.append(res)
    return results
