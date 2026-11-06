"""Sozlamalar. Qiymatlar .env fayldan yoki muhit o'zgaruvchilaridan olinadi."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def _load_env():
    path = os.path.join(HERE, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()]
DB_PATH = os.getenv("DB_PATH", os.path.join(HERE, "ucshop.db"))

# Ixtiyoriy: checkout.uz kalitini admin paneldan ham kiritish mumkin
CHECKOUT_API_KEY = os.getenv("CHECKOUT_API_KEY", "").strip()

# Ixtiyoriy: webhook (server/VPS uchun). 0 bo'lsa faqat avtomatik tekshiruv (polling) ishlaydi.
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "0") or 0)
WEBHOOK_PUBLIC_URL = os.getenv("WEBHOOK_PUBLIC_URL", "").strip()
