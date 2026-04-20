"""CallMeBot WhatsApp sender.

API docs: https://www.callmebot.com/blog/free-api-whatsapp-messages/
Endpoint: GET https://api.callmebot.com/whatsapp.php?phone=...&text=...&apikey=...
"""
import logging
import requests

logger = logging.getLogger(__name__)

ENDPOINT = "https://api.callmebot.com/whatsapp.php"
TIMEOUT_SECONDS = 30


class CallMeBotError(Exception):
    pass


def send_whatsapp(phone: str, apikey: str, message: str) -> None:
    """Send `message` to `phone` via CallMeBot. Raises CallMeBotError on failure."""
    params = {"phone": phone, "text": message, "apikey": apikey}
    try:
        resp = requests.get(ENDPOINT, params=params, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as e:
        raise CallMeBotError(f"HTTP error: {e}") from e
    if resp.status_code != 200:
        raise CallMeBotError(
            f"CallMeBot returned {resp.status_code}: {resp.text[:200]}"
        )
    logger.info("WhatsApp sent: %s", message)
