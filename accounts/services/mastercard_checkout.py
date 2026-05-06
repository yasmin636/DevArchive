import base64
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


logger = logging.getLogger(__name__)


class MastercardCheckoutService:
    """Service MPGS Hosted Checkout (sandbox)."""

    def __init__(self, settings):
        self.gateway_url = (getattr(settings, "MASTERCARD_GATEWAY_URL", "") or "").rstrip("/")
        self.api_version = str(getattr(settings, "MASTERCARD_API_VERSION", "100"))
        self.merchant_id = getattr(settings, "MASTERCARD_MERCHANT_ID", "") or ""
        self.api_password = getattr(settings, "MASTERCARD_API_PASSWORD", "") or ""

    def is_configured(self):
        return bool(self.gateway_url and self.merchant_id and self.api_password)

    def _auth_header(self):
        raw = f"merchant.{self.merchant_id}:{self.api_password}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")

    def _request(self, method, endpoint, payload=None):
        body = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
        req = Request(
            url=f"{self.gateway_url}{endpoint}",
            data=body,
            method=method,
            headers={
                "Authorization": self._auth_header(),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(req, timeout=20) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            content = exc.read().decode("utf-8", errors="ignore")
            logger.warning("Mastercard HTTPError %s: %s", exc.code, content)
            raise RuntimeError(f"Mastercard API error {exc.code}")
        except URLError as exc:
            logger.warning("Mastercard URLError: %s", exc)
            raise RuntimeError("Mastercard API network error")

    def create_checkout_session(
        self,
        order_id,
        amount,
        currency,
        return_url,
        cancel_url,
        customer_email,
        customer_name,
    ):
        endpoint = f"/api/rest/version/{self.api_version}/merchant/{self.merchant_id}/session"
        payload = {
            "apiOperation": "INITIATE_CHECKOUT",
            "interaction": {
                "operation": "PURCHASE",
                "returnUrl": return_url,
                "cancelUrl": cancel_url,
            },
            "order": {
                "id": order_id,
                "amount": str(amount),
                "currency": currency,
                "description": "Deblocage des corrections SIGAEUD",
            },
            "customer": {
                "email": customer_email or "",
                "firstName": customer_name or "",
            },
        }
        return self._request("POST", endpoint, payload)

    def retrieve_order(self, order_id):
        endpoint = f"/api/rest/version/{self.api_version}/merchant/{self.merchant_id}/order/{order_id}"
        return self._request("GET", endpoint)
