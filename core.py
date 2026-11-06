"""Umumiy biznes mantiq: adminlar, to'lov usullari, balans, buyurtma xabari."""
import time

import config
import db
import ui

_alert_ts = {}


def admin_ids():
    ids = set(config.ADMIN_IDS) | {r["id"] for r in db.q("SELECT id FROM admins")}
    return sorted(ids)


def is_admin(uid):
    return uid in admin_ids()


def alert_admins(text, key="x", every=600):
    """Bir xil ogohlantirishni 10 daqiqada bir martadan ko'p yubormaydi."""
    if time.time() - _alert_ts.get(key, 0) < every:
        return
    _alert_ts[key] = time.time()
    for a in admin_ids():
        ui.say(a, text)


# ---------------- to'lov sozlamalari ----------------
def checkout_key():
    return db.get("ck_key") or config.CHECKOUT_API_KEY


def min_topup():
    return max(db.geti("min_topup") or 1000, 1000)


def max_topup():
    return min(db.geti("max_topup") or 10_000_000, 10_000_000)


def pay_methods():
    """Yoqilgan va sozlangan to'lov usullari."""
    m = []
    if db.get("stars_on", "1") != "0" and db.geti("stars_rate") > 0:
        m.append("stars")
    if db.get("ck_on", "1") != "0" and checkout_key():
        m.append("checkout")
    if db.get("man_on", "1") != "0" and db.get("man_card"):
        m.append("manual")
    return m


# ---------------- balans ----------------
def credit_topup(uid, amount, notify=True):
    """Balansni to'ldiradi, referal foizini beradi. Yangi balansni qaytaradi."""
    db.ex("UPDATE users SET balance=balance+?, topped=topped+? WHERE id=?", (amount, amount, uid))
    u = db.user(uid)
    pct = db.geti("ref_percent")
    if u and u["ref_by"] and pct > 0:
        bonus = amount * pct // 100
        if bonus > 0:
            db.ex("UPDATE users SET balance=balance+?, ref_earned=ref_earned+? WHERE id=?",
                  (bonus, bonus, u["ref_by"]))
            ui.say(u["ref_by"], f"🎁 Taklif qilgan do'stingiz hisobini to'ldirdi: +{ui.fmt(bonus)} so'm")
    bal = db.user(uid)["balance"]
    if notify:
        ui.send(uid, "topup_ok", amount=ui.fmt(amount), balance=ui.fmt(bal))
    return bal


# ---------------- buyurtma ----------------
def order_text(o, status=""):
    u = db.user(o["uid"]) or {}
    uname = f" @{u['username']}" if u.get("username") else ""
    return (f"🛒 <b>Buyurtma #{o['id']}</b>\n\n"
            f"👤 {ui.esc(u.get('name', ''))}{ui.esc(uname)} (<code>{o['uid']}</code>)\n"
            f"🎮 UC: <b>{o['uc']}</b>\n💰 Narx: <b>{ui.fmt(o['price'])}</b> so'm\n"
            f"🆔 Player ID: <code>{ui.esc(o['player'])}</code>"
            + (f"\n\n{status}" if status else ""))


def order_markup(oid):
    return ui.ikb([ui.btn("i_done", f"a:od:{oid}"), ui.btn("i_refund", f"a:oc:{oid}")])


def notify_order(oid):
    o = db.one("SELECT * FROM orders WHERE id=?", (oid,))
    if not o:
        return
    targets = list(admin_ids())
    ch = db.get("orders_channel")
    if ch:
        targets.append(ch)
    for t in targets:
        ui.say(t, order_text(o), order_markup(oid))


def fdate(ts):
    """Toshkent vaqti (UTC+5) bo'yicha sana."""
    return time.strftime("%d.%m %H:%M", time.gmtime((ts or 0) + 5 * 3600))
