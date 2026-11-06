"""UC Shop bot — ishga tushirish: python main.py"""
import json
import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config


def setup_wizard():
    """Birinchi ishga tushirishda token va admin ID so'raydi, .env yaratadi."""
    if config.BOT_TOKEN and config.ADMIN_IDS:
        return
    print("=== Birinchi sozlash ===")
    token = config.BOT_TOKEN or input("Bot token (@BotFather): ").strip()
    admins = ",".join(map(str, config.ADMIN_IDS)) or input("Admin Telegram ID (bir nechta bo'lsa vergul bilan): ").strip()
    path = os.path.join(config.HERE, ".env")
    lines = []
    if os.path.exists(path):
        lines = [l for l in open(path, encoding="utf-8").read().splitlines()
                 if not l.startswith(("BOT_TOKEN=", "ADMIN_IDS="))]
    lines += [f"BOT_TOKEN={token}", f"ADMIN_IDS={admins}"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(".env saqlandi. Qayta ishga tushirilmoqda...\n")
    os.execv(sys.executable, [sys.executable] + sys.argv)


if __name__ == "__main__":
    setup_wizard()

import core  # noqa: E402
import db  # noqa: E402
import ui  # noqa: E402
import user  # noqa: E402
import admin  # noqa: E402
from tg import TG, TGError  # noqa: E402

log = logging.getLogger("main")
_locks, _locks_guard = {}, threading.Lock()


def _user_lock(uid):
    with _locks_guard:
        return _locks.setdefault(uid, threading.Lock())


def route(u):
    if "message" in u:
        m = u["message"]
        if not m.get("from"):
            return
        uid = m["from"]["id"]
        if m["chat"]["type"] == "private" and not m.get("successful_payment") and core.is_admin(uid) and admin.wants(m):
            return admin.on_message(m)
        return user.on_message(m)
    if "callback_query" in u:
        cb = u["callback_query"]
        if (cb.get("data") or "").startswith("a:"):
            return admin.on_callback(cb)
        return user.on_callback(cb)
    if "pre_checkout_query" in u:
        return user.on_precheckout(u["pre_checkout_query"])


def safe_route(u):
    f = (u.get("message") or u.get("callback_query") or u.get("pre_checkout_query") or {}).get("from") or {}
    try:
        with _user_lock(f.get("id", 0)):
            route(u)
    except Exception:
        log.exception("update xatosi")


class Hook(BaseHTTPRequestHandler):
    """checkout.uz webhook: xabarni qabul qilmaymiz, balki to'lovni API'dan qayta tekshiramiz (xavfsiz)."""

    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            oid = str((body.get("data") or {}).get("order_id", ""))
            row = db.one("SELECT id FROM payments WHERE provider='checkout' AND ext_id=?", (oid,))
            if row:
                threading.Thread(target=user.check_checkout, args=(row["id"],), daemon=True).start()
        except Exception:
            log.exception("webhook")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ui.tg = TG(config.BOT_TOKEN)
    try:
        me = ui.api("getMe")
    except TGError as e:
        sys.exit(f"Token noto'g'ri yoki internet yo'q: {e.desc}")
    ui.BOT_USERNAME, ui.BOT_ID = me["username"], me["id"]
    try:
        ui.api("deleteWebhook")
        ui.api("setMyCommands", commands=[{"command": "start", "description": "Botni ishga tushirish"},
                                          {"command": "menu", "description": "Asosiy menyu"}])
    except TGError:
        pass
    threading.Thread(target=user.checkout_loop, daemon=True).start()
    if config.WEBHOOK_PORT:
        srv = ThreadingHTTPServer(("0.0.0.0", config.WEBHOOK_PORT), Hook)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        log.info("webhook server: port %s", config.WEBHOOK_PORT)
    log.info("@%s ishga tushdi. Adminlar: %s", ui.BOT_USERNAME, core.admin_ids())
    pool, offset = ThreadPoolExecutor(max_workers=8), None
    allowed = ["message", "callback_query", "pre_checkout_query"]
    while True:
        try:
            ups = ui.api("getUpdates", offset=offset, timeout=50, allowed_updates=allowed, _timeout=65)
        except TGError as e:
            log.warning("getUpdates: %s", e.desc)
            time.sleep(3)
            continue
        for u in ups:
            offset = u["update_id"] + 1
            pool.submit(safe_route, u)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("To'xtatildi.")
