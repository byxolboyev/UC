"""checkout.uz API (https://checkout.uz/uz/api-docs) bilan ishlash."""
import requests

BASE = "https://checkout.uz/api/v1"


class CheckoutError(Exception):
    pass


def _post(key, path, body=None):
    try:
        r = requests.post(BASE + path, json=body or {}, timeout=25,
                          headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
    except requests.RequestException as e:
        raise CheckoutError(f"Tarmoq xatosi: {e}")
    try:
        j = r.json()
    except ValueError:
        raise CheckoutError(f"HTTP {r.status_code}: javob JSON emas")
    if j.get("status") != "success":
        raise CheckoutError(str(j.get("message") or j.get("error") or j)[:300])
    return j


def create_payment(key, amount, description="", return_url=None, webhook_url=None):
    body = {"amount": int(amount), "description": description[:200]}
    if return_url:
        body["return_url"] = return_url
    if webhook_url:
        body["webhook_url"] = webhook_url
    p = _post(key, "/create_payment", body)["payment"]
    return {"id": p["_id"], "uuid": p.get("_uuid", ""), "url": p["_url"], "status": p.get("_status")}


def status_payment(key, id=None, uuid=None):
    body = {"id": int(id)} if id else {"uuid": uuid}
    d = _post(key, "/status_payment", body)["data"]
    return {"status": (d.get("status") or "").lower(), "amount": d.get("amount")}


def get_balance(key):
    return _post(key, "/get_balance").get("balance", {})
