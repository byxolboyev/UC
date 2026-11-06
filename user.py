"""Foydalanuvchi qismi."""
import logging
import math
import re
import sqlite3
import time

import checkout
import config
import core
import db
import ui
from checkout import CheckoutError
from tg import TGError

log = logging.getLogger("user")
_sub_ok = {}
FAIL = {"canceled", "cancelled", "expired", "failed", "error", "rejected"}


# ===================== ro'yxatdan o'tkazish / tekshiruvlar =====================
def ensure_user(f):
    uid = f["id"]
    name = (f.get("first_name") or "") + ((" " + f["last_name"]) if f.get("last_name") else "")
    uname = f.get("username") or ""
    u = db.user(uid)
    if u is None:
        db.ex("INSERT OR IGNORE INTO users(id,name,username,joined) VALUES(?,?,?,?)", (uid, name, uname, db.now()))
        return db.user(uid), True
    if u["name"] != name or u["username"] != uname:
        db.ex("UPDATE users SET name=?, username=? WHERE id=?", (name, uname, uid))
        u = db.user(uid)
    return u, False


def not_joined(uid, fresh=False):
    chs = db.channels()
    if not chs:
        return []
    if not fresh and time.time() - _sub_ok.get(uid, 0) < 120:
        return []
    res = []
    for ch in chs:
        try:
            m = ui.api("getChatMember", chat_id=ch["chat_id"], user_id=uid)
            st = m.get("status")
            ok = st in ("member", "administrator", "creator") or (st == "restricted" and m.get("is_member"))
        except TGError:
            ok = True  # bot kanalda admin emas -> foydalanuvchini to'smaymiz
        if not ok:
            res.append(ch)
    if not res:
        _sub_ok[uid] = time.time()
    return res


def gate(uid, chat, u=None):
    u = u or db.user(uid)
    if core.is_admin(uid):
        return True
    if u and u["banned"]:
        ui.send(chat, "banned")
        return False
    if db.get("bot_on", "1") == "0":
        ui.send(chat, "maintenance")
        return False
    miss = not_joined(uid)
    if miss:
        rows = [[ui.btn("ch_join", url=c["link"], title=c["title"])] for c in miss if c["link"]]
        rows.append([ui.btn("i_check", "u:chk")])
        ui.send(chat, "sub_required", ui.ikb(*rows))
        return False
    return True


def ref_reward(uid):
    u = db.user(uid)
    if not u or not u["ref_by"] or u["ref_paid"]:
        return
    if db.ex("UPDATE users SET ref_paid=1 WHERE id=? AND ref_paid=0", (uid,)).rowcount != 1:
        return
    bonus = db.geti("ref_bonus")
    db.ex("UPDATE users SET ref_count=ref_count+1, ref_earned=ref_earned+?, balance=balance+? WHERE id=?",
          (bonus, bonus, u["ref_by"]))
    if bonus > 0:
        ui.send(u["ref_by"], "ref_new", bonus=ui.fmt(bonus))


def send_start(uid, chat, u):
    ui.send(chat, "start", ui.user_menu(), name=ui.esc(u["name"]), id=uid, balance=ui.fmt(u["balance"]))


# ===================== menyu tugmalari =====================
def h_topup(uid, chat):
    methods = core.pay_methods()
    if not methods:
        return ui.send(chat, "topup_none")
    key = {"stars": "i_stars", "checkout": "i_checkout", "manual": "i_manual"}
    ui.send(chat, "topup_choose", ui.ikb(*[[ui.btn(key[m], f"u:t:{m}")] for m in methods]))


def h_buy(uid, chat):
    pk = db.packages()
    if not pk:
        return ui.send(chat, "buy_empty")
    btns = [ui.btn("pkg", f"u:p:{p['id']}", uc=p["uc"], price=ui.fmt(p["price"])) for p in pk]
    ui.send(chat, "buy_choose", ui.ikb(*ui.grid(btns, 2)), balance=ui.fmt(db.user(uid)["balance"]))


def h_profile(uid, chat):
    u = db.user(uid)
    cnt = db.one("SELECT COUNT(*) c FROM orders WHERE uid=?", (uid,))["c"]
    ui.send(chat, "profile", id=uid, name=ui.esc(u["name"]), balance=ui.fmt(u["balance"]), orders=cnt,
            spent=ui.fmt(u["spent"]), refs=u["ref_count"])


def h_orders(uid, chat):
    rows = db.q("SELECT * FROM orders WHERE uid=? ORDER BY id DESC LIMIT 10", (uid,))
    if not rows:
        return ui.say(chat, "📦 Sizda hali buyurtmalar yo'q.")
    icon = {"pending": "⏳", "done": "✅", "canceled": "❌"}
    lines = [f"{icon.get(o['status'], '•')} <b>#{o['id']}</b> — {o['uc']} UC — {ui.fmt(o['price'])} so'm "
             f"<i>({core.fdate(o['created'])})</i>" for o in rows]
    ui.say(chat, "📦 <b>Oxirgi buyurtmalarim</b>\n\n" + "\n".join(lines))


def h_history(uid, chat):
    rows = db.q("SELECT * FROM payments WHERE uid=? ORDER BY id DESC LIMIT 10", (uid,))
    if not rows:
        return ui.say(chat, "🧾 Sizda hali to'lovlar yo'q.")
    prov = {"stars": "⭐ Stars", "checkout": "⚡ Checkout", "manual": "💳 Qo'lda"}
    icon = {"paid": "✅", "pending": "⏳"}
    lines = [f"{icon.get(p['status'], '❌')} {prov.get(p['provider'], p['provider'])} — {ui.fmt(p['amount'])} so'm "
             f"<i>({core.fdate(p['created'])})</i>" for p in rows]
    ui.say(chat, "🧾 <b>Oxirgi to'lovlarim</b>\n\n" + "\n".join(lines))


def h_prices(uid, chat):
    pk = db.packages()
    if not pk:
        return ui.send(chat, "buy_empty")
    lst = "\n".join(f"🎮 <b>{p['uc']} UC</b> — {ui.fmt(p['price'])} so'm" for p in pk)
    ui.send(chat, "prices_header", list=lst)


def h_ref(uid, chat):
    u = db.user(uid)
    ui.send(chat, "ref_info", bonus=ui.fmt(db.geti("ref_bonus")), percent=db.geti("ref_percent"),
            link=f"https://t.me/{ui.BOT_USERNAME}?start=ref_{uid}", refs=u["ref_count"], earned=ui.fmt(u["ref_earned"]))


def _guide_list(chat, kind):
    items = db.guides(kind)
    head, empty = ("guides_header", "guides_empty") if kind == "g" else ("help_header", "help_empty")
    if not items:
        return ui.send(chat, empty)
    ui.send(chat, head, ui.ikb(*[[ui.btn("item", f"u:g:{kind}:{g['id']}", title=g["title"])] for g in items]))


def h_guides(uid, chat):
    _guide_list(chat, "g")


def h_help(uid, chat):
    _guide_list(chat, "h")


def h_contact(uid, chat):
    ui.send(chat, "contact", admin=ui.esc(db.get("admin_contact")) or "Aloqa ma'lumoti hali kiritilmagan.")


MENU = {"topup": h_topup, "buy": h_buy, "profile": h_profile, "orders": h_orders, "history": h_history,
        "prices": h_prices, "ref": h_ref, "guides": h_guides, "help": h_help, "contact": h_contact}


# ===================== xabarlar =====================
def on_message(m):
    if m["chat"]["type"] != "private":
        return
    f = m["from"]
    uid, chat = f["id"], m["chat"]["id"]
    if m.get("successful_payment"):
        return on_stars_paid(m)
    u, new = ensure_user(f)
    text = m.get("text") or ""
    if text.startswith("/start"):
        return on_start(m, u, new)
    if not gate(uid, chat, u):
        return
    if text in ("/menu", "/cancel"):
        ui.clear_state(uid)
        return ui.send(chat, "menu", ui.user_menu())
    b = db.find_button(text, ("user",))
    if b:
        ui.clear_state(uid)
        return MENU[b["key"]](uid, chat)
    st = ui.get_state(uid)
    if st:
        return on_state(m, u, st)
    ui.send(chat, "menu", ui.user_menu())


def on_start(m, u, new):
    uid, chat = m["from"]["id"], m["chat"]["id"]
    parts = (m.get("text") or "").split(maxsplit=1)
    if new and len(parts) > 1 and parts[1].startswith("ref_"):
        rid = parts[1][4:]
        if rid.isdigit() and int(rid) != uid and db.user(int(rid)):
            db.ex("UPDATE users SET ref_by=? WHERE id=?", (int(rid), uid))
    ui.clear_state(uid)
    if not gate(uid, chat, u):
        return
    ref_reward(uid)
    send_start(uid, chat, db.user(uid))


def parse_amount(text):
    s = re.sub(r"[\s,._]", "", text or "")
    return int(s) if s.isdigit() and len(s) < 12 else None


def on_state(m, u, st):
    uid, chat = m["from"]["id"], m["chat"]["id"]
    s, text = st["s"], (m.get("text") or "").strip()
    if s == "player":
        if not (text.isdigit() and 5 <= len(text) <= 20):
            return ui.send(chat, "bad_player")
        return ask_confirm(uid, chat, st["pkg"], text)
    if s == "amount":
        amt = parse_amount(text)
        lo, hi = core.min_topup(), core.max_topup()
        if amt is None or not lo <= amt <= hi:
            return ui.send(chat, "bad_amount", min=ui.fmt(lo), max=ui.fmt(hi))
        return pay_start(uid, chat, st["method"], amt)
    if s == "proof":
        mtype, _ = ui.extract_media(m)
        if mtype not in ("photo", "document"):
            return ui.say(chat, "📸 Iltimos, to'lov chekini rasm (screenshot) ko'rinishida yuboring.")
        return submit_proof(m, uid, chat, st["amount"])
    ui.clear_state(uid)


# ===================== UC sotib olish =====================
def ask_confirm(uid, chat, pkg_id, player):
    p = db.one("SELECT * FROM packages WHERE id=? AND active=1", (pkg_id,))
    if not p:
        ui.clear_state(uid)
        return ui.say(chat, "❌ Bu paket hozir mavjud emas.")
    ui.set_state(uid, "confirm", pkg=pkg_id, player=player)
    ui.send(chat, "buy_confirm", ui.ikb([ui.btn("i_confirm", "u:ok"), ui.btn("i_cancel", "u:x")]),
            uc=p["uc"], price=ui.fmt(p["price"]), player=ui.esc(player))


def create_order(uid, chat, pkg_id, player):
    p = db.one("SELECT * FROM packages WHERE id=? AND active=1", (pkg_id,))
    if not p:
        return ui.say(chat, "❌ Bu paket hozir mavjud emas.")
    if not db.take_balance(uid, p["price"]):
        return ui.send(chat, "no_balance", ui.user_menu(), price=ui.fmt(p["price"]),
                       balance=ui.fmt(db.user(uid)["balance"]))
    try:
        oid = db.ex("INSERT INTO orders(uid,uc,price,player,status,created) VALUES(?,?,?,?,'pending',?)",
                    (uid, p["uc"], p["price"], player, db.now())).lastrowid
    except Exception:
        db.add_balance(uid, p["price"])
        log.exception("order insert")
        return ui.say(chat, "❌ Xatolik yuz berdi, pulingiz qaytarildi. Qayta urinib ko'ring.")
    db.ex("UPDATE users SET last_player=?, spent=spent+? WHERE id=?", (player, p["price"], uid))
    ui.send(chat, "order_created", ui.user_menu(), id=oid, uc=p["uc"], price=ui.fmt(p["price"]), player=ui.esc(player))
    core.notify_order(oid)


# ===================== hisob to'ldirish =====================
def pay_start(uid, chat, method, amount):
    ui.clear_state(uid)
    if method not in core.pay_methods():
        return ui.send(chat, "topup_none", ui.user_menu())
    if method == "stars":
        rate = db.geti("stars_rate")
        stars = math.ceil(amount / rate)
        total = stars * rate
        ui.send(chat, "stars_info", ui.user_menu(), stars=stars, amount=ui.fmt(total))
        try:
            ui.api("sendInvoice", chat_id=chat, title="Hisob to'ldirish",
                   description=f"Balansni {ui.fmt(total)} so'mga to'ldirish", payload=f"top:{uid}:{rate}",
                   currency="XTR", prices=[{"label": "Balans", "amount": stars}])
        except TGError as e:
            log.warning("invoice: %s", e.desc)
            ui.say(chat, "❌ Hisob yaratib bo'lmadi. Summani o'zgartirib qayta urinib ko'ring.")
    elif method == "checkout":
        start_checkout(uid, chat, amount)
    else:
        ui.set_state(uid, "proof", amount=amount)
        ui.send(chat, "manual_info", ui.ikb([ui.btn("i_cancel", "u:x")]), card=ui.esc(db.get("man_card")),
                holder=ui.esc(db.get("man_holder")) or "—", amount=ui.fmt(amount))


def start_checkout(uid, chat, amount):
    wh = f"{config.WEBHOOK_PUBLIC_URL.rstrip('/')}/checkout" if config.WEBHOOK_PUBLIC_URL else None
    try:
        r = checkout.create_payment(core.checkout_key(), amount, f"Hisob to'ldirish (ID {uid})",
                                    return_url=f"https://t.me/{ui.BOT_USERNAME}", webhook_url=wh)
    except CheckoutError as e:
        log.warning("checkout create: %s", e)
        core.alert_admins(f"⚠️ <b>Checkout.uz xatosi</b>\n<code>{ui.esc(e)}</code>\n\n"
                          "API kalit to'g'riligini va kassada IP-whitelist sozlamasini tekshiring.", "ckerr")
        return ui.say(chat, "❌ To'lovni yaratib bo'lmadi. Birozdan so'ng qayta urinib ko'ring yoki boshqa usulni tanlang.")
    pid = db.ex("INSERT INTO payments(uid,provider,amount,status,ext_id,uuid,created) VALUES(?,?,?,?,?,?,?)",
                (uid, "checkout", amount, "pending", str(r["id"]), r["uuid"], db.now())).lastrowid
    ui.send(chat, "checkout_info", ui.ikb([ui.btn("i_pay", url=r["url"])], [ui.btn("i_paycheck", f"u:pc:{pid}")]),
            amount=ui.fmt(amount))


def check_checkout(pid):
    """'paid' | 'pending' | 'failed' | 'error'"""
    p = db.one("SELECT * FROM payments WHERE id=? AND provider='checkout'", (pid,))
    if not p:
        return "failed"
    if p["status"] == "paid":
        return "paid"
    if p["status"] != "pending":
        return "failed"
    key = core.checkout_key()
    if not key:
        return "error"
    try:
        st = checkout.status_payment(key, id=p["ext_id"])["status"]
    except CheckoutError as e:
        log.warning("checkout status: %s", e)
        return "error"
    if st == "paid":
        if db.ex("UPDATE payments SET status='paid', paid=? WHERE id=? AND status='pending'", (db.now(), pid)).rowcount == 1:
            core.credit_topup(p["uid"], p["amount"])
        return "paid"
    if st in FAIL:
        db.ex("UPDATE payments SET status='failed' WHERE id=? AND status='pending'", (pid,))
        return "failed"
    return "pending"


def checkout_loop():
    """Kutilayotgan checkout.uz to'lovlarini avtomatik tekshirib turadi."""
    while True:
        try:
            for p in db.q("SELECT id, created FROM payments WHERE provider='checkout' AND status='pending'"):
                if db.now() - p["created"] > 3 * 3600:
                    db.ex("UPDATE payments SET status='expired' WHERE id=? AND status='pending'", (p["id"],))
                    continue
                check_checkout(p["id"])
                time.sleep(0.4)
        except Exception:
            log.exception("checkout_loop")
        time.sleep(12)


def submit_proof(m, uid, chat, amount):
    pid = db.ex("INSERT INTO payments(uid,provider,amount,status,created) VALUES(?,?,?,?,?)",
                (uid, "manual", amount, "pending", db.now())).lastrowid
    u = db.user(uid)
    cap = (f"💳 <b>To'lov cheki #{pid}</b>\n👤 {ui.esc(u['name'])} (<code>{uid}</code>)\n"
           f"💵 Summa: <b>{ui.fmt(amount)}</b> so'm")
    markup = ui.ikb([ui.btn("i_approve", f"a:pa:{pid}"), ui.btn("i_reject", f"a:px:{pid}")])
    sent = 0
    for a in core.admin_ids():
        try:
            ui.api("copyMessage", chat_id=a, from_chat_id=chat, message_id=m["message_id"], caption=cap,
                   parse_mode="HTML", reply_markup=markup)
            sent += 1
        except TGError as e:
            log.warning("proof copy %s: %s", a, e.desc)
    ui.clear_state(uid)
    ui.send(chat, "manual_sent", ui.user_menu())


# ===================== Stars =====================
def on_precheckout(pq):
    u = db.user(pq["from"]["id"])
    ok = not (u and u["banned"])
    try:
        ui.api("answerPreCheckoutQuery", pre_checkout_query_id=pq["id"], ok=ok,
               error_message=None if ok else "Siz bloklangansiz")
    except TGError as e:
        log.warning("precheckout: %s", e.desc)


def on_stars_paid(m):
    sp, uid = m["successful_payment"], m["from"]["id"]
    parts = (sp.get("invoice_payload") or "").split(":")
    if sp.get("currency") != "XTR" or len(parts) != 3 or parts[0] != "top" or not parts[2].isdigit():
        return
    amount = sp["total_amount"] * int(parts[2])
    ensure_user(m["from"])
    try:
        db.ex("INSERT INTO payments(uid,provider,amount,status,ext_id,created,paid) VALUES(?,?,?,?,?,?,?)",
              (uid, "stars", amount, "paid", sp["telegram_payment_charge_id"], db.now(), db.now()))
    except sqlite3.IntegrityError:
        return  # takroriy xabar
    core.credit_topup(uid, amount)


# ===================== callback =====================
def on_callback(cb):
    f, cid = cb["from"], cb["id"]
    uid, data = f["id"], cb.get("data") or ""
    msg = cb.get("message") or {}
    chat = (msg.get("chat") or {}).get("id", uid)
    mid = msg.get("message_id")
    u, _ = ensure_user(f)
    p = data.split(":")
    cmd = p[1] if len(p) > 1 else ""

    if cmd == "noop":
        return ui.answer(cid)
    if cmd == "chk":
        if u["banned"] and not core.is_admin(uid):
            return ui.answer(cid)
        if not core.is_admin(uid) and not_joined(uid, fresh=True):
            return ui.answer(cid, db_text("sub_fail"), True)
        ui.answer(cid)
        ref_reward(uid)
        if mid:
            ui.delete(chat, mid)
        return send_start(uid, chat, db.user(uid))
    if not gate(uid, chat, u):
        return ui.answer(cid)

    if cmd == "x":
        ui.clear_state(uid)
        ui.answer(cid)
        return ui.send(chat, "cancelled", ui.user_menu())
    if cmd in ("p", "lp"):
        pkg = int(p[2])
        if not db.one("SELECT 1 FROM packages WHERE id=? AND active=1", (pkg,)):
            return ui.answer(cid, "❌ Paket mavjud emas", True)
        ui.answer(cid)
        if cmd == "lp" and u["last_player"]:
            return ask_confirm(uid, chat, pkg, u["last_player"])
        ui.set_state(uid, "player", pkg=pkg)
        rows = []
        if u["last_player"]:
            rows.append([ui.ab(f"🆔 {u['last_player']}", f"u:lp:{pkg}", "primary")])
        rows.append([ui.btn("i_cancel", "u:x")])
        return ui.send(chat, "ask_player", ui.ikb(*rows))
    if cmd == "ok":
        st = ui.get_state(uid)
        if not st or st["s"] != "confirm":
            return ui.answer(cid, "⌛ Muddati o'tgan, qaytadan boshlang", True)
        ui.clear_state(uid)
        ui.answer(cid)
        if mid:
            ui.delete(chat, mid)
        return create_order(uid, chat, st["pkg"], st["player"])
    if cmd == "t":
        method = p[2]
        if method not in core.pay_methods():
            return ui.answer(cid, "⚠️ Bu usul hozir mavjud emas", True)
        ui.answer(cid)
        ui.set_state(uid, "amount", method=method)
        return ui.send(chat, "ask_amount", ui.ikb([ui.btn("i_cancel", "u:x")]),
                       min=ui.fmt(core.min_topup()), max=ui.fmt(core.max_topup()))
    if cmd == "pc":
        row = db.one("SELECT uid FROM payments WHERE id=?", (int(p[2]),))
        if not row or row["uid"] != uid:
            return ui.answer(cid)
        st = check_checkout(int(p[2]))
        if st == "paid":
            return ui.answer(cid, "✅ To'lov qabul qilindi!", True)
        if st == "failed":
            return ui.answer(cid, db_text("pay_failed"), True)
        return ui.answer(cid, db_text("pay_pending"), True)
    if cmd == "g":
        g = db.one("SELECT * FROM guides WHERE id=? AND kind=?", (int(p[3]), p[2]))
        ui.answer(cid)
        if g:
            ui.send_media(chat, g["text"], g["mtype"], g["fid"])
        return
    ui.answer(cid)


def db_text(key):
    """Callback ogohlantirishi uchun oddiy matn (HTML teglarsiz)."""
    return re.sub(r"<[^>]+>", "", db.msg(key)["text"])[:190]
