import base64
import io
from urllib.parse import quote

import qrcode


def build_upi_uri(payee_upi_id: str, payee_name: str, amount: float, note: str = "") -> str:
    """Builds a standard UPI deep link. Never includes PIN/OTP/credentials —
    those are entered by the customer inside their own UPI app, never here."""
    params = {
        "pa": payee_upi_id,
        "pn": payee_name,
        "am": f"{amount:.2f}",
        "cu": "INR",
    }
    if note:
        params["tn"] = note
    query = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    return f"upi://pay?{query}"


def generate_qr_base64(data: str) -> str:
    """Returns a base64-encoded PNG (no data: prefix) for embedding in JSON/HTML."""
    img = qrcode.make(data, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")
