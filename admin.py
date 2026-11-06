"""Admin panel."""
import logging
import re
import threading
import time

import checkout
import core
import db
import texts
import ui
from checkout import CheckoutError
from tg import TGError

log = logging.getLogger("admin")
EMPTY = {"inline_keyboard": []}
CANCEL = ui.ikb([ui.ab("❌ Bekor qilish", "a:cx", "danger")])


# ===================== yordamchilar =====================
def S(text, data, style=None):
    return ui.ab(text, data, style)


def ask(uid, chat, state, prompt, **data):
    ui.set_state(uid, state, **data)
    ui.say(chat, prompt, CANCEL)


def pint(text, lo=1, hi=10 ** 10):
    s = re.sub(r"[\s,._]", "", text or "")
    if s.isdigit() and lo <= int(s) <= hi:
        return int(s)
    return None


def ctx(cb):
    msg = cb.get("message") or {}
    return cb["from"]["id"], (msg.get("chat") or {}).get("id", cb["from"]["id"]), msg.get("message_id")


def show(cb, view):
    _, chat, mid = ctx(cb)
    text, markup = view
    if mid:
        ui.edit(chat, mid, text, markup)
    else:
        ui.say(chat, text, markup)


def finish_msg(cb, text):
    """Tugmali xabarni (matn yoki rasm sarlavhasi) yakuniy holatga keltiradi."""
    _, chat, mid = ctx(cb)
    try:
        ui.api("editMessageCaption", chat_id=chat, message_id=mid, caption=text, parse_mode="HTML", reply_markup=EMPTY)
    except TGError:
        try:
            ui.api("editMessageText", chat_id=chat, message_id=mid, text=text, parse_mode="HTML", reply_markup=EMPTY)
        except TGError:
            pass


def toggle_btn(key, name, view):
    on = db.get(key, "1") != "0"
    return S(("🟢 " if on else "🔴 ") + name, f"a:t:{key}:{view}", "success" if on else "danger")


def flag(key):
    return "✅ yoqilgan" if db.get(key, "1") != "0" else "⛔ o'chirilgan"


# ===================== SOZLAMALAR (generik) =====================
SETS = {
    "stars_rate": ("⭐ 1 Star narxi", "int"), "ck_key": ("🔑 Checkout.uz API kalit", "secret"),
    "man_card": ("💳 Karta raqami", "text"), "man_holder": ("👤 Karta egasi", "text"),
    "min_topup": ("⬇️ Minimal summa", "int"), "max_topup": ("⬆️ Maksimal summa", "int"),
    "ref_bonus": ("🎁 Taklif bonusi", "int"), "ref_percent": ("📈 Referal foiz", "int"),
    "admin_contact": ("📞 Aloqa matni", "text"), "orders_channel": ("📢 Buyurtmalar kanali", "chat"),
}


def pay_view():
    rate, key, card = db.geti("stars_rate"), core.checkout_key(), db.get("man_card")
    mask = (key[:4] + "…" + key[-3:]) if len(key) > 8 else ("kiritilgan" if key else "❌ kiritilmagan")
    t = ("💳 <b>To'lov tizimlari</b>\n\n"
         f"⭐ <b>Telegram Stars</b> — {flag('stars_on')}\n   1 Star = {ui.fmt(rate) + ' so`m' if rate else '❌ kiritilmagan'}\n\n"
         f"⚡ <b>Checkout.uz (avto)</b> — {flag('ck_on')}\n   API kalit: {mask}\n\n"
         f"💳 <b>Qo'lda to'lov</b> — {flag('man_on')}\n   Karta: {ui.esc(card) or '❌ kiritilmagan'}\n"
         f"   Egasi: {ui.esc(db.get('man_holder')) or '—'}\n\n"
         f"⬇️ Min: {ui.fmt(core.min_topup())} so'm   ⬆️ Max: {ui.fmt(core.max_topup())} so'm\n\n"
         "<i>Usul foydalanuvchiga faqat yoqilgan va sozlangan bo'lsa ko'rinadi.</i>")
    rows = [[S("⭐ Stars narxi", "a:s:stars_rate:pay", "primary"), toggle_btn("stars_on", "Stars", "pay")],
            [S("🔑 Checkout kalit", "a:s:ck_key:pay", "primary"), toggle_btn("ck_on", "Checkout", "pay")],
            [S("🧪 Kalitni tekshirish", "a:ckt", "success")],
            [S("💳 Karta raqami", "a:s:man_card:pay", "primary"), S("👤 Karta egasi", "a:s:man_holder:pay", "primary")],
            [toggle_btn("man_on", "Qo'lda to'lov", "pay")],
            [S("⬇️ Min summa", "a:s:min_topup:pay"), S("⬆️ Max summa", "a:s:max_topup:pay")]]
    return t, ui.ikb(*rows)


def ref_view():
    t = ("🎁 <b>Referal tizimi</b>\n\n"
         f"💵 Taklif uchun bonus: <b>{ui.fmt(db.geti('ref_bonus'))}</b> so'm\n"
         f"📈 Do'st to'ldirgan summadan foiz: <b>{db.geti('ref_percent')}%</b>\n\n"
         "<i>0 qo'ysangiz o'chadi. Bonus do'st botga kirib, majburiy obunadan o'tgach beriladi.</i>")
    return t, ui.ikb([S("💵 Bonus summasi", "a:s:ref_bonus:ref", "success"), S("📈 Foiz", "a:s:ref_percent:ref", "primary")])


def settings_view():
    t = ("⚙️ <b>Sozlamalar</b>\n\n"
         f"🤖 Bot: {flag('bot_on')}\n"
         f"📞 Aloqa: {ui.esc(db.get('admin_contact')) or '❌ kiritilmagan'}\n"
         f"📢 Buyurtmalar kanali: {ui.esc(db.get('orders_channel')) or '—'}\n"
         f"👑 Adminlar: {len(core.admin_ids())} ta")
    return t, ui.ikb([toggle_btn("bot_on", "Bot ishlashi", "set")],
                     [S("📞 Aloqa matni", "a:s:admin_contact:set", "primary")],
                     [S("📢 Buyurtmalar kanali", "a:s:orders_channel:set", "primary")],
                     [S("👑 Adminlarni boshqarish", "a:adm", "success")])


VIEWS = {"pay": pay_view, "ref": ref_view, "set": settings_view}


def cb_set(cb, p):
    uid, chat, _ = ctx(cb)
    key, view = p[2], p[3]
    label, kind = SETS[key]
    cur = "" if kind == "secret" else (db.get(key) or "—")
    hint = "Raqam yuboring (0 = o'chirish)." if kind == "int" else "Qiymatni yuboring (- = tozalash)."
    if kind == "chat":
        hint = "Kanal @username yoki ID yuboring (bot kanalda admin bo'lishi shart). - = tozalash."
    ask(uid, chat, "a_set", f"{label}\n\nJoriy: <code>{ui.esc(cur)}</code>\n\n{hint}", key=key, view=view)


def in_set(m, uid, chat, st):
    key, view = st["key"], st["view"]
    kind = SETS[key][1]
    text = (m.get("text") or "").strip()
    if not text:
        return ui.say(chat, "⚠️ Matn yuboring.", CANCEL)
    if kind == "int":
        val = 0 if text == "-" else pint(text, 0)
        if val is None:
            return ui.say(chat, "⚠️ Faqat raqam yuboring.", CANCEL)
    elif text == "-":
        val = ""
    elif kind == "chat":
        try:
            val = ui.api("getChat", chat_id=text if not re.fullmatch(r"-?\d+", text) else int(text))["id"]
        except TGError:
            return ui.say(chat, "❌ Kanal topilmadi yoki bot unda yo'q. Qayta yuboring.", CANCEL)
    else:
        val = text
    db.put(key, val)
    if kind == "secret":
        ui.delete(chat, m["message_id"])  # kalit chatda qolmasin
    ui.clear_state(uid)
    ui.say(chat, "✅ Saqlandi.")
    ui.say(chat, *VIEWS[view]())


def cb_toggle(cb, p):
    key, view = p[2], p[3]
    db.put(key, "0" if db.get(key, "1") != "0" else "1")
    show(cb, VIEWS[view]())


def cb_ckt(cb, p):
    _, chat, _ = ctx(cb)
    key = core.checkout_key()
    if not key:
        return ui.answer(cb["id"], "❌ API kalit kiritilmagan", True)
    try:
        bal = checkout.get_balance(key)
        ui.answer(cb["id"], "✅ Kalit ishlayapti!\n" + ", ".join(f"{k.upper()}: {v}" for k, v in bal.items()), True)
    except CheckoutError as e:
        ui.answer(cb["id"], f"❌ {str(e)[:180]}\n\nKalitni va kassadagi IP-whitelist'ni tekshiring.", True)


# ===================== UC PAKETLAR =====================
def pk_list_view():
    pk = db.packages(False)
    lines = [f"{'🟢' if p['active'] else '🔴'} <b>{p['uc']} UC</b> — {ui.fmt(p['price'])} so'm" for p in pk]
    t = "📦 <b>UC paketlar</b>\n\n" + ("\n".join(lines) if pk else "Hozircha paket yo'q. Pastdagi tugma bilan qo'shing.")
    rows = ui.grid([S(f"{'🟢' if p['active'] else '🔴'} {p['uc']} UC — {ui.fmt(p['price'])}", f"a:pk:{p['id']}", "primary")
                    for p in pk], 2)
    rows.append([S("➕ Paket qo'shish", "a:pka", "success")])
    return t, ui.ikb(*rows)


def pk_card_view(pid):
    p = db.one("SELECT * FROM packages WHERE id=?", (pid,))
    if not p:
        return pk_list_view()
    t = (f"📦 <b>Paket #{pid}</b>\n\n🎮 UC: <b>{p['uc']}</b>\n💰 Narx: <b>{ui.fmt(p['price'])}</b> so'm\n"
         f"Holat: {'🟢 sotuvda' if p['active'] else '🔴 o`chirilgan'}")
    return t, ui.ikb([S("✏️ UC soni", f"a:pku:{pid}", "primary"), S("💰 Narxi", f"a:pkp:{pid}", "primary")],
                     [S("🔴 O'chirish" if p["active"] else "🟢 Yoqish", f"a:pkt:{pid}"), S("🗑 Butunlay o'chirish", f"a:pkd:{pid}", "danger")],
                     [S("⬅️ Orqaga", "a:pkl")])


def cb_pk(cb, p):
    cmd, uid, chat = p[1], *ctx(cb)[:2]
    if cmd == "pkl":
        return show(cb, pk_list_view())
    if cmd == "pka":
        return ask(uid, chat, "a_pka1", "🎮 Yangi paket: <b>UC sonini</b> yuboring (masalan 60):")
    pid = int(p[2])
    if cmd == "pk":
        return show(cb, pk_card_view(pid))
    if cmd in ("pku", "pkp"):
        field = "uc" if cmd == "pku" else "price"
        return ask(uid, chat, "a_pke", "✏️ Yangi " + ("UC sonini" if field == "uc" else "narxni (so'm)") + " yuboring:",
                   pid=pid, field=field)
    if cmd == "pkt":
        db.ex("UPDATE packages SET active=1-active WHERE id=?", (pid,))
        return show(cb, pk_card_view(pid))
    if cmd == "pkd":
        db.ex("DELETE FROM packages WHERE id=?", (pid,))
        return show(cb, pk_list_view())


def in_pka1(m, uid, chat, st):
    uc = pint(m.get("text"), 1, 10 ** 7)
    if not uc:
        return ui.say(chat, "⚠️ Musbat raqam yuboring.", CANCEL)
    ask(uid, chat, "a_pka2", f"💰 <b>{uc} UC</b> uchun narxni so'mda yuboring:", uc=uc)


def in_pka2(m, uid, chat, st):
    price = pint(m.get("text"), 1, 10 ** 10)
    if not price:
        return ui.say(chat, "⚠️ Musbat raqam yuboring.", CANCEL)
    db.ex("INSERT INTO packages(uc,price) VALUES(?,?)", (st["uc"], price))
    ui.clear_state(uid)
    ui.say(chat, "✅ Paket qo'shildi.")
    ui.say(chat, *pk_list_view())


def in_pke(m, uid, chat, st):
    v = pint(m.get("text"))
    if not v:
        return ui.say(chat, "⚠️ Musbat raqam yuboring.", CANCEL)
    db.ex(f"UPDATE packages SET {st['field']}=? WHERE id=?", (v, st["pid"]))
    ui.clear_state(uid)
    ui.say(chat, "✅ Yangilandi.")
    ui.say(chat, *pk_card_view(st["pid"]))


# ===================== BUYURTMALAR / CHEKLAR =====================
def m_orders(uid, chat):
    rows = db.q("SELECT * FROM orders WHERE status='pending' ORDER BY id LIMIT 15")
    if not rows:
        return ui.say(chat, "📥 Kutilayotgan buyurtmalar yo'q ✅")
    ui.say(chat, f"📥 <b>Kutilayotgan buyurtmalar: {len(rows)} ta</b>")
    for o in rows:
        ui.say(chat, core.order_text(o), core.order_markup(o["id"]))


def cb_order(cb, p):
    uid, chat, mid = ctx(cb)
    oid = int(p[2])
    o = db.one("SELECT * FROM orders WHERE id=?", (oid,))
    if not o:
        return ui.answer(cb["id"], "Buyurtma topilmadi", True)
    if p[1] == "od":
        ok = db.ex("UPDATE orders SET status='done', admin_id=? WHERE id=? AND status='pending'", (uid, oid)).rowcount == 1
        line = "✅ <b>Bajarildi</b>"
        if ok:
            ui.send(o["uid"], "order_done", id=oid, uc=o["uc"], player=ui.esc(o["player"]))
    else:
        ok = db.ex("UPDATE orders SET status='canceled', admin_id=? WHERE id=? AND status='pending'", (uid, oid)).rowcount == 1
        line = "❌ <b>Bekor qilindi (pul qaytarildi)</b>"
        if ok:
            db.ex("UPDATE users SET balance=balance+?, spent=MAX(spent-?,0) WHERE id=?", (o["price"], o["price"], o["uid"]))
            ui.send(o["uid"], "order_canceled", id=oid, uc=o["uc"], price=ui.fmt(o["price"]))
    if not ok:
        ui.answer(cb["id"], "Bu buyurtma allaqachon ko'rib chiqilgan", True)
    else:
        ui.answer(cb["id"], "✅")
    cur = db.one("SELECT * FROM orders WHERE id=?", (oid,))
    st_line = "✅ <b>Bajarildi</b>" if cur["status"] == "done" else "❌ <b>Bekor qilindi</b>"
    ui.edit(chat, mid, core.order_text(cur, st_line), EMPTY)


def cb_proof(cb, p):
    pid = int(p[2])
    pay = db.one("SELECT * FROM payments WHERE id=? AND provider='manual'", (pid,))
    if not pay:
        return ui.answer(cb["id"], "Topilmadi", True)
    if p[1] == "pa":
        ok = db.ex("UPDATE payments SET status='paid', paid=? WHERE id=? AND status='pending'", (db.now(), pid)).rowcount == 1
        if ok:
            bal = core.credit_topup(pay["uid"], pay["amount"], notify=False)
            ui.send(pay["uid"], "manual_ok", amount=ui.fmt(pay["amount"]), balance=ui.fmt(bal))
        line = f"✅ <b>Tasdiqlandi</b> — +{ui.fmt(pay['amount'])} so'm"
    else:
        ok = db.ex("UPDATE payments SET status='rejected' WHERE id=? AND status='pending'", (pid,)).rowcount == 1
        if ok:
            ui.send(pay["uid"], "manual_no")
        line = "❌ <b>Rad etildi</b>"
    if not ok:
        return ui.answer(cb["id"], "Bu chek allaqachon ko'rib chiqilgan", True)
    ui.answer(cb["id"], "✅")
    finish_msg(cb, f"💳 To'lov cheki #{pid}\n💵 {ui.fmt(pay['amount'])} so'm\n\n{line}")


# ===================== FOYDALANUVCHILAR =====================
def m_users(uid, chat):
    n = db.one("SELECT COUNT(*) n FROM users")["n"]
    ask(uid, chat, "a_ufind", f"👥 Jami foydalanuvchilar: <b>{n}</b>\n\n🔎 Foydalanuvchi <b>ID</b> raqamini yuboring:")


def m_balance(uid, chat):
    ask(uid, chat, "a_ufind", "💰 Balansi o'zgartiriladigan foydalanuvchi <b>ID</b> raqamini yuboring:")


def m_ban(uid, chat):
    ask(uid, chat, "a_ufind", "🚫 Ban/Unban qilinadigan foydalanuvchi <b>ID</b> raqamini yuboring:")


def user_card_view(tid):
    u = db.user(tid)
    if not u:
        return "❌ Foydalanuvchi topilmadi.", None
    orders = db.one("SELECT COUNT(*) n FROM orders WHERE uid=?", (tid,))["n"]
    uname = f"@{u['username']}" if u["username"] else "—"
    t = (f"👤 <b>{ui.esc(u['name'])}</b> {ui.esc(uname)}\n🆔 <code>{tid}</code>\n"
         f"💰 Balans: <b>{ui.fmt(u['balance'])}</b> so'm\n🛒 Buyurtmalar: {orders} ta\n"
         f"💸 Sarflangan: {ui.fmt(u['spent'])} so'm\n💳 To'ldirgan: {ui.fmt(u['topped'])} so'm\n"
         f"👥 Takliflar: {u['ref_count']} ta\n📅 Qo'shilgan: {core.fdate(u['joined'])}\n"
         f"Holat: {'🚫 bloklangan' if u['banned'] else '✅ faol'}")
    return t, ui.ikb([S("➕ Balans qo'shish", f"a:ub:{tid}:+", "success"), S("➖ Balans ayirish", f"a:ub:{tid}:-", "danger")],
                     [S("✅ Unban" if u["banned"] else "🚫 Ban", f"a:ubn:{tid}", "success" if u["banned"] else "danger")],
                     [S("✉️ Xabar yuborish", f"a:um:{tid}", "primary")])


def in_ufind(m, uid, chat, st):
    tid = pint(m.get("text"))
    if not tid or not db.user(tid):
        return ui.say(chat, "❌ Bunday foydalanuvchi topilmadi. ID'ni qayta yuboring.", CANCEL)
    ui.clear_state(uid)
    ui.say(chat, *user_card_view(tid))


def cb_user(cb, p):
    uid, chat, _ = ctx(cb)
    tid = int(p[2])
    if p[1] == "ub":
        return ask(uid, chat, "a_ubal", f"💰 Summani so'mda yuboring ({'qo`shish' if p[3] == '+' else 'ayirish'}):",
                   tid=tid, sign=p[3])
    if p[1] == "um":
        return ask(uid, chat, "a_umsg", "✉️ Foydalanuvchiga yuboriladigan xabarni yuboring:", tid=tid)
    if p[1] == "ubn":
        db.ex("UPDATE users SET banned=1-banned WHERE id=?", (tid,))
        show(cb, user_card_view(tid))


def in_ubal(m, uid, chat, st):
    amt = pint(m.get("text"))
    if not amt:
        return ui.say(chat, "⚠️ Musbat raqam yuboring.", CANCEL)
    tid = st["tid"]
    if st["sign"] == "+":
        db.add_balance(tid, amt)
    else:
        db.ex("UPDATE users SET balance=MAX(balance-?,0) WHERE id=?", (amt, tid))
    ui.say(tid, f"💰 Balansingiz admin tomonidan o'zgartirildi: <b>{st['sign']}{ui.fmt(amt)}</b> so'm\n"
                f"Joriy balans: <b>{ui.fmt(db.user(tid)['balance'])}</b> so'm")
    ui.clear_state(uid)
    ui.say(chat, "✅ Bajarildi.")
    ui.say(chat, *user_card_view(tid))


def in_umsg(m, uid, chat, st):
    try:
        ui.api("copyMessage", chat_id=st["tid"], from_chat_id=chat, message_id=m["message_id"])
        ui.say(chat, "✅ Yuborildi.")
    except TGError as e:
        ui.say(chat, f"❌ Yuborib bo'lmadi: {ui.esc(e.desc)}")
    ui.clear_state(uid)


# ===================== STATISTIKA =====================
def m_stats(uid, chat):
    u = db.one("SELECT COUNT(*) n, COALESCE(SUM(balance),0) b, COALESCE(SUM(banned),0) bn FROM users")
    midnight = (db.now() + 5 * 3600) // 86400 * 86400 - 5 * 3600
    today = db.one("SELECT COUNT(*) n FROM users WHERE joined>=?", (midnight,))["n"]
    o = {r["status"]: r for r in db.q("SELECT status, COUNT(*) n, COALESCE(SUM(price),0) s FROM orders GROUP BY status")}
    g = lambda s, f: o[s][f] if s in o else 0
    prov = {"stars": "⭐ Stars", "checkout": "⚡ Checkout", "manual": "💳 Qo'lda"}
    pays = db.q("SELECT provider, COUNT(*) n, COALESCE(SUM(amount),0) s FROM payments WHERE status='paid' GROUP BY provider")
    pl = "\n".join(f"   {prov.get(r['provider'], r['provider'])}: {ui.fmt(r['s'])} so'm ({r['n']} ta)" for r in pays) or "   —"
    ui.say(chat, "📊 <b>Statistika</b>\n\n"
           f"👥 Foydalanuvchilar: <b>{u['n']}</b> (bugun +{today}, bloklangan {u['bn']})\n"
           f"💰 Jami balanslar: <b>{ui.fmt(u['b'])}</b> so'm\n\n"
           f"🛒 Buyurtmalar:\n   ⏳ Kutilmoqda: {g('pending', 'n')}\n   ✅ Bajarilgan: {g('done', 'n')} ({ui.fmt(g('done', 's'))} so'm)\n"
           f"   ❌ Bekor: {g('canceled', 'n')}\n\n💳 Tushumlar:\n{pl}")


# ===================== XABAR YUBORISH =====================
def m_cast(uid, chat):
    ask(uid, chat, "a_cast", "📢 Hammaga yuboriladigan xabarni yuboring (matn, rasm, video, dumaloq video — istalgani):")


def in_cast(m, uid, chat, st):
    n = db.one("SELECT COUNT(*) n FROM users WHERE banned=0")["n"]
    ui.set_state(uid, "a_castc", src=chat, mid=m["message_id"])
    try:
        ui.api("copyMessage", chat_id=chat, from_chat_id=chat, message_id=m["message_id"])
    except TGError:
        pass
    ui.say(chat, f"👆 Shu xabar <b>{n}</b> ta foydalanuvchiga yuborilsinmi?",
           ui.ikb([S("✅ Yuborish", "a:cg", "success"), S("❌ Bekor", "a:cx", "danger")]))


def run_cast(admin, src, mid):
    ok = fail = 0
    for r in db.q("SELECT id FROM users WHERE banned=0"):
        try:
            ui.api("copyMessage", chat_id=r["id"], from_chat_id=src, message_id=mid)
            ok += 1
        except TGError:
            fail += 1
        time.sleep(0.05)
    ui.say(admin, f"📢 <b>Yuborish tugadi</b>\n✅ Yetkazildi: {ok}\n❌ Xato: {fail}")


def cb_cast(cb, p):
    uid, chat, mid = ctx(cb)
    st = ui.get_state(uid)
    if not st or st["s"] != "a_castc":
        return
    ui.clear_state(uid)
    ui.edit(chat, mid, "⏳ Yuborish boshlandi…", EMPTY)
    threading.Thread(target=run_cast, args=(uid, st["src"], st["mid"]), daemon=True).start()


def cb_cancel(cb, p):
    uid, chat, mid = ctx(cb)
    ui.clear_state(uid)
    ui.edit(chat, mid, "❌ Bekor qilindi.", EMPTY)


# ===================== MATNLAR =====================
def msgs_view():
    rows = ui.grid([S(v[0], f"a:m:{k}", "primary") for k, v in texts.MESSAGES.items()], 2)
    return ("📝 <b>Matnlar</b>\n\nBot xabarlarini tahrirlash: matn, rasm, video yoki dumaloq video qo'shish mumkin. "
            "Premium emoji va formatlash ham saqlanadi.", ui.ikb(*rows))


def msg_card_view(key):
    title, _, vars_ = texts.MESSAGES[key]
    m = db.msg(key)
    t = (f"📝 <b>{title}</b>\n\n🧩 O'zgaruvchilar: <code>{vars_ or '—'}</code>\n🖼 Media: {m['mtype'] or 'yo`q'}\n\n"
         f"<b>Joriy matn (HTML):</b>\n<pre>{ui.esc(m['text'][:900])}</pre>")
    return t, ui.ikb([S("✏️ Matnni o'zgartirish", f"a:me:{key}", "primary"), S("🖼 Media qo'shish", f"a:mm:{key}", "success")],
                     [S("🗑 Mediani olib tashlash", f"a:md:{key}", "danger"), S("👁 Ko'rish", f"a:mv:{key}", "primary")],
                     [S("♻️ Standartga qaytarish", f"a:mx:{key}", "danger")], [S("⬅️ Orqaga", "a:ml")])


def cb_msg(cb, p):
    uid, chat, _ = ctx(cb)
    cmd = p[1]
    if cmd == "ml":
        return show(cb, msgs_view())
    key = p[2]
    if key not in texts.MESSAGES:
        return
    if cmd == "m":
        return show(cb, msg_card_view(key))
    if cmd == "me":
        return ask(uid, chat, "a_me", "✏️ Yangi matnni yuboring. Formatlash va premium emoji saqlanadi.\n"
                   f"🧩 O'zgaruvchilar: <code>{texts.MESSAGES[key][2] or '—'}</code>", key=key)
    if cmd == "mm":
        return ask(uid, chat, "a_mm", "🖼 Rasm, video, GIF, dumaloq video yoki fayl yuboring.\n"
                   "Sarlavha (caption) bilan yuborsangiz, matn ham yangilanadi.", key=key)
    if cmd == "md":
        db.set_msg(key, mtype="", fid="")
        return show(cb, msg_card_view(key))
    if cmd == "mv":
        return ui.send(chat, key)
    if cmd == "mx":
        db.reset_msg(key)
        return show(cb, msg_card_view(key))


def in_me(m, uid, chat, st):
    if not (m.get("text") or m.get("caption")):
        return ui.say(chat, "⚠️ Matn yuboring.", CANCEL)
    db.set_msg(st["key"], text=ui.msg_html(m))
    mtype, fid = ui.extract_media(m)
    if mtype:
        db.set_msg(st["key"], mtype=mtype, fid=fid)
    ui.clear_state(uid)
    ui.say(chat, "✅ Matn saqlandi.")
    ui.say(chat, *msg_card_view(st["key"]))


def in_mm(m, uid, chat, st):
    mtype, fid = ui.extract_media(m)
    if not mtype:
        return ui.say(chat, "⚠️ Media yuboring (rasm/video/GIF/dumaloq video/fayl).", CANCEL)
    db.set_msg(st["key"], mtype=mtype, fid=fid)
    if m.get("caption"):
        db.set_msg(st["key"], text=ui.msg_html(m))
    ui.clear_state(uid)
    ui.say(chat, "✅ Media saqlandi.")
    ui.say(chat, *msg_card_view(st["key"]))


# ===================== DIZAYN =====================
COLORS = {"success": "🟢 yashil", "primary": "🔵 ko'k", "danger": "🔴 qizil", "default": "⚪ standart"}


def design_view():
    t = ("🎨 <b>Dizayn</b>\n\nTugma matni, rangi (yashil/ko'k/qizil), emoji va <b>premium emoji</b>ni shu yerdan o'zgartiring.\n\n"
         "🪄 <i>Avto-moslash</i>: premium emoji paketini yuborsangiz, har bir tugmaga mos emoji o'zi qo'yiladi.\n\n"
         "<i>Premium emoji tugmada ko'rinishi uchun bot egasida Telegram Premium bo'lishi kerak.</i>")
    rows = [[S(v, f"a:ds:{k}", "primary")] for k, v in texts.SCOPE_TITLES.items()]
    rows += [[S("🪄 Premium emoji paketdan avto-moslash", "a:dauto", "success")],
             [S("♻️ Hammasini standartga qaytarish", "a:dr0", "danger")]]
    return t, ui.ikb(*rows)


def _preview(key, data):
    return ui.btn(key, data, uc="60", price="12 000", title="Nomi")


def design_list_view(scope):
    bs = db.buttons(scope)
    rows = ui.grid([_preview(b["key"], f"a:db:{b['key']}") for b in bs], 2)
    rows.append([S("⬅️ Orqaga", "a:dl")])
    return f"{texts.SCOPE_TITLES[scope]}\n\nTahrirlash uchun tugmani tanlang 👇", ui.ikb(*rows)


def design_card_view(key):
    b = db.button(key)
    t = (f"🎨 <b>Tugma: {ui.esc(b['text'])}</b>\n\n🔤 Matn: <code>{ui.esc(b['text'])}</code>\n"
         f"😀 Emoji: {b['uni'] or '—'}\n⭐ Premium emoji: {'✅ qo`yilgan' if b['cid'] else '—'}\n"
         f"🎨 Rang: {COLORS.get(b['style'], b['style'])}")
    if b["scope"] == "inline" and "{" in b["text"]:
        t += "\n\n<i>{...} — o'zgaruvchilar, o'chirmang.</i>"
    rows = [[_preview(key, "a:noop")],
            [S("✏️ Matn", f"a:dt:{key}", "primary"), S("😀 Emoji", f"a:du:{key}", "primary")],
            [S("🟢 Yashil", f"a:dc:{key}:success", "success"), S("🔵 Ko'k", f"a:dc:{key}:primary", "primary"),
             S("🔴 Qizil", f"a:dc:{key}:danger", "danger")],
            [S("⚪ Standart rang", f"a:dc:{key}:default")],
            [S("⭐ Premium emoji qo'yish", f"a:dp:{key}", "success"), S("❌ Premiumni olish", f"a:dpx:{key}", "danger")],
            [S("♻️ Tiklash", f"a:dr:{key}"), S("⬅️ Orqaga", f"a:ds:{b['scope']}")]]
    return t, ui.ikb(*rows)


def _refresh_admin_kb(chat, scope):
    if scope == "admin":
        ui.say(chat, "🔄 Admin menyu yangilandi.", ui.admin_menu())


def cb_design(cb, p):
    uid, chat, _ = ctx(cb)
    cmd = p[1]
    if cmd == "dl":
        return show(cb, design_view())
    if cmd == "ds":
        return show(cb, design_list_view(p[2]))
    if cmd == "dauto":
        return ask(uid, chat, "a_dauto", "🪄 <b>Premium emoji paket</b> havolasini yuboring (masalan "
                   "<code>https://t.me/addemoji/NOM</code>) yoki paketdagi istalgan premium emojini yuboring.")
    if cmd == "dr0":
        return show(cb, ("♻️ Barcha tugmalar (matn, rang, emoji) standart holatga qaytariladi. Davom etasizmi?",
                         ui.ikb([S("✅ Ha", "a:dr1", "danger"), S("❌ Yo'q", "a:dl", "success")])))
    if cmd == "dr1":
        db.reset_all_buttons()
        show(cb, design_view())
        return _refresh_admin_kb(chat, "admin")
    key = p[2]
    b = db.button(key)
    if not b:
        return
    if cmd == "db":
        return show(cb, design_card_view(key))
    if cmd == "dt":
        return ask(uid, chat, "a_dt", f"✏️ Tugma uchun yangi matn yuboring (1–40 belgi).\nJoriy: <code>{ui.esc(b['text'])}</code>", key=key)
    if cmd == "du":
        return ask(uid, chat, "a_du", "😀 Oddiy emoji yuboring (olib tashlash uchun <code>-</code>).", key=key)
    if cmd == "dp":
        return ask(uid, chat, "a_dp", "⭐ Premium emojini yuboring (xabarda 1 ta premium emoji bo'lsin).", key=key)
    if cmd == "dpx":
        db.set_button(key, cid="")
    elif cmd == "dc":
        db.set_button(key, style=p[3])
    elif cmd == "dr":
        db.reset_button(key)
    show(cb, design_card_view(key))
    _refresh_admin_kb(chat, b["scope"])


def _after_design(chat, key):
    ui.say(chat, "✅ Saqlandi.")
    ui.say(chat, *design_card_view(key))
    _refresh_admin_kb(chat, db.button(key)["scope"])


def in_dt(m, uid, chat, st):
    text = (m.get("text") or "").strip()
    b = db.button(st["key"])
    if not 1 <= len(text) <= 40:
        return ui.say(chat, "⚠️ Matn 1–40 belgi bo'lsin.", CANCEL)
    if b["scope"] in ("user", "admin") and any(
            x["key"] != b["key"] and db._norm(x["text"]) == db._norm(text) for x in db.buttons(b["scope"])):
        return ui.say(chat, "⚠️ Bu nom boshqa tugmada ishlatilgan. Boshqa nom yuboring.", CANCEL)
    db.set_button(st["key"], text=text)
    ui.clear_state(uid)
    _after_design(chat, st["key"])


def in_du(m, uid, chat, st):
    text = (m.get("text") or "").strip()
    if not text or len(text) > 12:
        return ui.say(chat, "⚠️ Bitta emoji yuboring (yoki <code>-</code>).", CANCEL)
    db.set_button(st["key"], uni="" if text == "-" else text)
    ui.clear_state(uid)
    _after_design(chat, st["key"])


def in_dp(m, uid, chat, st):
    cid = next((e["custom_emoji_id"] for e in (m.get("entities") or []) if e["type"] == "custom_emoji"), None)
    if not cid and (m.get("text") or "").strip().isdigit() and len(m["text"].strip()) > 10:
        cid = m["text"].strip()
    if not cid:
        return ui.say(chat, "⚠️ Xabarda premium emoji topilmadi. Premium emoji yuboring.", CANCEL)
    db.set_button(st["key"], cid=cid)
    ui.clear_state(uid)
    _after_design(chat, st["key"])


def _pack_name(m):
    text = (m.get("text") or "").strip()
    mo = re.search(r"(?:addemoji|addstickers)/([A-Za-z0-9_]+)", text)
    if mo:
        return mo.group(1)
    for e in m.get("entities") or []:
        if e["type"] == "custom_emoji":
            stk = ui.api("getCustomEmojiStickers", custom_emoji_ids=[e["custom_emoji_id"]])
            if stk and stk[0].get("set_name"):
                return stk[0]["set_name"]
    return text if re.fullmatch(r"[A-Za-z0-9_]{3,64}", text) else None


def _ne(s):
    return (s or "").replace("️", "").strip()


def in_dauto(m, uid, chat, st):
    try:
        name = _pack_name(m)
        if not name:
            return ui.say(chat, "⚠️ Paket havolasi yoki premium emoji topilmadi. Qayta yuboring.", CANCEL)
        stickers = ui.api("getStickerSet", name=name).get("stickers", [])
    except TGError as e:
        return ui.say(chat, f"❌ Paketni olib bo'lmadi: {ui.esc(e.desc)}", CANCEL)
    mp = {}
    for s in stickers:
        if s.get("custom_emoji_id"):
            mp.setdefault(_ne(s.get("emoji")), s["custom_emoji_id"])
    done, miss = 0, []
    for b in db._buttons():
        cid = mp.get(_ne(b["uni"]))
        if cid:
            db.set_button(b["key"], cid=cid)
            done += 1
        else:
            miss.append(b["text"])
    ui.clear_state(uid)
    t = f"🪄 <b>{done}</b> ta tugmaga premium emoji qo'yildi (paketda {len(mp)} xil emoji)."
    if miss:
        t += "\n\nMos emoji topilmaganlar (qo'lda qo'yish mumkin):\n" + ", ".join(ui.esc(x) for x in miss[:25])
    ui.say(chat, t)
    ui.say(chat, *design_view())
    _refresh_admin_kb(chat, "admin")


# ===================== QO'LLANMA / YORDAM =====================
KIND = {"g": ("📖 Qo'llanmalar", "qo'llanma"), "h": ("🆘 Yordam bo'limlari", "bo'lim")}


def guides_view(k):
    items = db.guides(k)
    t = f"<b>{KIND[k][0]}</b>\n\n" + ("\n".join(f"• {ui.esc(g['title'])}" for g in items) if items else "Hozircha bo'sh.")
    rows = [[S(g["title"], f"a:g:{k}:{g['id']}", "primary")] for g in items]
    rows.append([S("➕ Qo'shish", f"a:ga:{k}", "success")])
    return t, ui.ikb(*rows)


def guide_card_view(k, gid):
    g = db.one("SELECT * FROM guides WHERE id=? AND kind=?", (gid, k))
    if not g:
        return guides_view(k)
    t = (f"📄 <b>{ui.esc(g['title'])}</b>\n\n🖼 Media: {g['mtype'] or 'yo`q'}\n"
         f"📝 Matn: {len(g['text'])} belgi")
    return t, ui.ikb([S("✏️ Sarlavha", f"a:gt:{k}:{gid}", "primary"), S("✏️ Matn/Media", f"a:gc:{k}:{gid}", "primary")],
                     [S("👁 Ko'rish", f"a:gv:{k}:{gid}", "success"), S("🗑 O'chirish", f"a:gd:{k}:{gid}", "danger")],
                     [S("⬅️ Orqaga", f"a:gl:{k}")])


def cb_guide(cb, p):
    uid, chat, _ = ctx(cb)
    cmd, k = p[1], p[2]
    if k not in KIND:
        return
    if cmd == "gl":
        return show(cb, guides_view(k))
    if cmd == "ga":
        return ask(uid, chat, "a_ga1", f"➕ Yangi {KIND[k][1]} <b>sarlavhasini</b> yuboring (tugma nomi bo'ladi):", k=k)
    gid = int(p[3])
    if cmd == "g":
        return show(cb, guide_card_view(k, gid))
    g = db.one("SELECT * FROM guides WHERE id=? AND kind=?", (gid, k))
    if not g:
        return show(cb, guides_view(k))
    if cmd == "gt":
        return ask(uid, chat, "a_gt", "✏️ Yangi sarlavhani yuboring:", k=k, gid=gid)
    if cmd == "gc":
        return ask(uid, chat, "a_gc", "✏️ Yangi mazmunni yuboring (matn, rasm, video, dumaloq video...):", k=k, gid=gid)
    if cmd == "gv":
        return ui.send_media(chat, g["text"], g["mtype"], g["fid"])
    if cmd == "gd":
        db.ex("DELETE FROM guides WHERE id=?", (gid,))
        return show(cb, guides_view(k))


def in_ga1(m, uid, chat, st):
    title = (m.get("text") or "").strip()
    if not 1 <= len(title) <= 50:
        return ui.say(chat, "⚠️ Sarlavha 1–50 belgi bo'lsin.", CANCEL)
    ask(uid, chat, "a_ga2", "📝 Endi mazmunni yuboring: matn, rasm, video yoki dumaloq video (istalgani, sarlavha bilan ham bo'ladi):",
        k=st["k"], title=title)


def in_ga2(m, uid, chat, st):
    mtype, fid = ui.extract_media(m)
    text = ui.msg_html(m)
    if not (text or mtype):
        return ui.say(chat, "⚠️ Matn yoki media yuboring.", CANCEL)
    db.ex("INSERT INTO guides(kind,title,text,mtype,fid) VALUES(?,?,?,?,?)", (st["k"], st["title"], text, mtype, fid))
    ui.clear_state(uid)
    ui.say(chat, "✅ Qo'shildi.")
    ui.say(chat, *guides_view(st["k"]))


def in_gt(m, uid, chat, st):
    title = (m.get("text") or "").strip()
    if not 1 <= len(title) <= 50:
        return ui.say(chat, "⚠️ Sarlavha 1–50 belgi bo'lsin.", CANCEL)
    db.ex("UPDATE guides SET title=? WHERE id=?", (title, st["gid"]))
    ui.clear_state(uid)
    ui.say(chat, "✅ Yangilandi.")
    ui.say(chat, *guide_card_view(st["k"], st["gid"]))


def in_gc(m, uid, chat, st):
    mtype, fid = ui.extract_media(m)
    text = ui.msg_html(m)
    if not (text or mtype):
        return ui.say(chat, "⚠️ Matn yoki media yuboring.", CANCEL)
    db.ex("UPDATE guides SET text=?, mtype=?, fid=? WHERE id=?", (text, mtype, fid, st["gid"]))
    ui.clear_state(uid)
    ui.say(chat, "✅ Yangilandi.")
    ui.say(chat, *guide_card_view(st["k"], st["gid"]))


# ===================== MAJBURIY OBUNA =====================
def ch_view():
    chs = db.channels()
    t = ("📡 <b>Majburiy obuna kanallari</b>\n\n"
         + ("\n".join(f"• {ui.esc(c['title'])} — <code>{c['chat_id']}</code>" for c in chs) if chs else "Hozircha kanal yo'q.")
         + "\n\n<i>Bot kanalda admin bo'lishi shart.</i>")
    rows = [[S(f"🗑 {c['title']}", f"a:chd:{c['id']}", "danger")] for c in chs]
    rows.append([S("➕ Kanal qo'shish", "a:cha", "success")])
    return t, ui.ikb(*rows)


def cb_channel(cb, p):
    uid, chat, _ = ctx(cb)
    if p[1] == "cha":
        return ask(uid, chat, "a_cha", "📡 Kanal <b>@username</b> yoki ID'sini yuboring, yoki kanaldan biror xabarni forward qiling.")
    if p[1] == "chd":
        db.ex("DELETE FROM channels WHERE id=?", (int(p[2]),))
        show(cb, ch_view())


def _chat_ref(m):
    fo = m.get("forward_origin") or {}
    if fo.get("type") == "channel":
        return fo["chat"]["id"]
    if m.get("forward_from_chat"):
        return m["forward_from_chat"]["id"]
    t = (m.get("text") or "").strip()
    mo = re.match(r"https?://t\.me/([A-Za-z0-9_]{4,})/?$", t)
    if mo:
        return "@" + mo.group(1)
    if re.fullmatch(r"-?\d+", t):
        return int(t)
    return t if t.startswith("@") else None


def in_cha(m, uid, chat, st):
    ref = _chat_ref(m)
    if ref is None:
        return ui.say(chat, "⚠️ Kanalni aniqlab bo'lmadi. @username, ID yoki forward yuboring.", CANCEL)
    try:
        c = ui.api("getChat", chat_id=ref)
        me = ui.api("getChatMember", chat_id=c["id"], user_id=ui.BOT_ID)
    except TGError as e:
        return ui.say(chat, f"❌ Kanal topilmadi yoki bot unda yo'q: {ui.esc(e.desc)}", CANCEL)
    if me.get("status") not in ("administrator", "creator"):
        return ui.say(chat, "❌ Avval botni kanalga <b>admin</b> qiling, so'ng qayta yuboring.", CANCEL)
    link = f"https://t.me/{c['username']}" if c.get("username") else ""
    if not link:
        try:
            link = ui.api("exportChatInviteLink", chat_id=c["id"])
        except TGError:
            return ask(uid, chat, "a_chl", "🔗 Kanal yopiq. Taklif havolasini (https://t.me/+...) yuboring:",
                       cid=c["id"], title=c.get("title", ""))
    db.ex("INSERT INTO channels(chat_id,title,link) VALUES(?,?,?)", (str(c["id"]), c.get("title", ""), link))
    ui.clear_state(uid)
    ui.say(chat, "✅ Kanal qo'shildi.")
    ui.say(chat, *ch_view())


def in_chl(m, uid, chat, st):
    link = (m.get("text") or "").strip()
    if not link.startswith("https://t.me/"):
        return ui.say(chat, "⚠️ Havola https://t.me/ bilan boshlansin.", CANCEL)
    db.ex("INSERT INTO channels(chat_id,title,link) VALUES(?,?,?)", (str(st["cid"]), st["title"], link))
    ui.clear_state(uid)
    ui.say(chat, "✅ Kanal qo'shildi.")
    ui.say(chat, *ch_view())


# ===================== ADMINLAR =====================
def adm_view():
    import config
    rows_db = db.q("SELECT id FROM admins")
    t = ("👑 <b>Adminlar</b>\n\n" + "\n".join(f"• <code>{a}</code> (asosiy)" for a in config.ADMIN_IDS)
         + ("\n" if config.ADMIN_IDS and rows_db else "") + "\n".join(f"• <code>{r['id']}</code>" for r in rows_db))
    rows = [[S(f"🗑 {r['id']}", f"a:admd:{r['id']}", "danger")] for r in rows_db]
    rows.append([S("➕ Admin qo'shish", "a:adma", "success"), S("⬅️ Orqaga", "a:ads")])
    return t, ui.ikb(*rows)


def cb_adm(cb, p):
    uid, chat, _ = ctx(cb)
    if p[1] == "adm":
        return show(cb, adm_view())
    if p[1] == "ads":
        return show(cb, settings_view())
    if p[1] == "adma":
        return ask(uid, chat, "a_adma", "👑 Yangi admin <b>ID</b> raqamini yuboring:")
    if p[1] == "admd":
        db.ex("DELETE FROM admins WHERE id=?", (int(p[2]),))
        show(cb, adm_view())


def in_adma(m, uid, chat, st):
    aid = pint(m.get("text"))
    if not aid:
        return ui.say(chat, "⚠️ ID raqam bo'lishi kerak.", CANCEL)
    db.ex("INSERT OR IGNORE INTO admins(id) VALUES(?)", (aid,))
    ui.clear_state(uid)
    ui.say(chat, "✅ Admin qo'shildi.")
    ui.say(chat, *adm_view())


# ===================== MENYU / YO'NALTIRISH =====================
def _say_view(fn):
    return lambda uid, chat: ui.say(chat, *fn())


def m_exit(uid, chat):
    ui.clear_state(uid)
    ui.send(chat, "menu", ui.user_menu())


MENU = {"a_uc": _say_view(pk_list_view), "a_orders": m_orders, "a_pay": _say_view(pay_view), "a_users": m_users,
        "a_stats": m_stats, "a_cast": m_cast, "a_msgs": _say_view(msgs_view), "a_design": _say_view(design_view),
        "a_guides": _say_view(lambda: guides_view("g")), "a_help": _say_view(lambda: guides_view("h")),
        "a_channels": _say_view(ch_view), "a_ref": _say_view(ref_view), "a_balance": m_balance, "a_ban": m_ban,
        "a_settings": _say_view(settings_view), "a_exit": m_exit}

INPUTS = {"a_set": in_set, "a_pka1": in_pka1, "a_pka2": in_pka2, "a_pke": in_pke, "a_ufind": in_ufind,
          "a_ubal": in_ubal, "a_umsg": in_umsg, "a_cast": in_cast, "a_me": in_me, "a_mm": in_mm, "a_dt": in_dt,
          "a_du": in_du, "a_dp": in_dp, "a_dauto": in_dauto, "a_ga1": in_ga1, "a_ga2": in_ga2, "a_gt": in_gt,
          "a_gc": in_gc, "a_cha": in_cha, "a_chl": in_chl, "a_adma": in_adma}

CB = {"s": cb_set, "t": cb_toggle, "ckt": cb_ckt, "od": cb_order, "oc": cb_order, "pa": cb_proof, "px": cb_proof,
      "ub": cb_user, "um": cb_user, "ubn": cb_user, "cg": cb_cast, "cx": cb_cancel,
      "ml": cb_msg, "m": cb_msg, "me": cb_msg, "mm": cb_msg, "md": cb_msg, "mv": cb_msg, "mx": cb_msg,
      "dl": cb_design, "ds": cb_design, "db": cb_design, "dt": cb_design, "du": cb_design, "dp": cb_design,
      "dpx": cb_design, "dc": cb_design, "dr": cb_design, "dr0": cb_design, "dr1": cb_design, "dauto": cb_design,
      "gl": cb_guide, "ga": cb_guide, "g": cb_guide, "gt": cb_guide, "gc": cb_guide, "gv": cb_guide, "gd": cb_guide,
      "cha": cb_channel, "chd": cb_channel, "adm": cb_adm, "ads": cb_adm, "adma": cb_adm, "admd": cb_adm}
for _k in ("pkl", "pka", "pk", "pku", "pkp", "pkt", "pkd"):
    CB[_k] = cb_pk
OWN_ANSWER = {"od", "oc", "pa", "px", "ckt"}


def wants(m):
    uid = m["from"]["id"]
    t = m.get("text") or ""
    st = ui.get_state(uid)
    if st and st["s"].startswith("a_"):
        if t.startswith("/") and t != "/admin":
            ui.clear_state(uid)
            return False
        return True
    return t == "/admin" or bool(db.find_button(t, ("admin",)))


def on_message(m):
    uid, chat = m["from"]["id"], m["chat"]["id"]
    t = m.get("text") or ""
    if t == "/admin":
        ui.clear_state(uid)
        return ui.send(chat, "admin_welcome", ui.admin_menu())
    b = db.find_button(t, ("admin",))
    if b and not (ui.get_state(uid) or {}).get("s", "").startswith("a_dt"):
        ui.clear_state(uid)
        return MENU[b["key"]](uid, chat)
    st = ui.get_state(uid)
    fn = INPUTS.get(st["s"]) if st else None
    if fn:
        fn(m, uid, chat, st)


def on_callback(cb):
    uid = cb["from"]["id"]
    if not core.is_admin(uid):
        return ui.answer(cb["id"], "⛔ Ruxsat yo'q", True)
    p = (cb.get("data") or "").split(":")
    cmd = p[1] if len(p) > 1 else ""
    if cmd == "noop":
        return ui.answer(cb["id"])
    h = CB.get(cmd)
    if not h:
        return ui.answer(cb["id"])
    if cmd not in OWN_ANSWER:
        ui.answer(cb["id"])
    try:
        h(cb, p)
    except TGError as e:
        log.warning("admin cb %s: %s", cmd, e.desc)
    except Exception:
        log.exception("admin cb %s", cmd)
        ui.say(cb["from"]["id"], "⚠️ Xatolik yuz berdi. Qayta urinib ko'ring.")
