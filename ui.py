"""Umumiy yordamchilar: tugmalar, xabar yuborish, holatlar."""
import html
import logging

import db
from tg import TGError, to_html

log = logging.getLogger("ui")

tg = None            # main.py o'rnatadi
BOT_USERNAME = ""
BOT_ID = 0
STYLES = ("success", "primary", "danger")

# ---------------- holatlar (xotirada) ----------------
_STATES = {}


def set_state(uid, name, **data):
    _STATES[uid] = {"s": name, **data}


def get_state(uid):
    return _STATES.get(uid)


def clear_state(uid):
    _STATES.pop(uid, None)


# ---------------- format ----------------
def fmt(n):
    try:
        return f"{int(n):,}".replace(",", " ")
    except (TypeError, ValueError):
        return str(n)


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=False)


def render(text, v):
    for k, val in v.items():
        text = text.replace("{" + k + "}", str(val))
    return text


# ---------------- API ----------------
def api(method, **kw):
    return tg.call(method, **kw)


def say(chat, text, markup=None, **kw):
    """Oddiy matn yuborish; xato bo'lsa None qaytaradi (masalan, bot bloklangan)."""
    try:
        return tg.call("sendMessage", chat_id=chat, text=text or "—", parse_mode="HTML", reply_markup=markup,
                       link_preview_options={"is_disabled": True}, **kw)
    except TGError as e:
        log.warning("sendMessage %s: %s", chat, e.desc)
        return None


def answer(cbid, text=None, alert=False):
    try:
        tg.call("answerCallbackQuery", callback_query_id=cbid, text=text, show_alert=alert or None)
    except TGError:
        pass


def edit(chat, mid, text, markup=None):
    """Xabarni tahrirlaydi. Muvaffaqiyatsiz bo'lsa yangi xabar yuboradi."""
    try:
        tg.call("editMessageText", chat_id=chat, message_id=mid, text=text, parse_mode="HTML",
                reply_markup=markup, link_preview_options={"is_disabled": True})
        return True
    except TGError as e:
        if "not modified" in e.desc.lower():
            return True
        say(chat, text, markup)
        return False


def delete(chat, mid):
    try:
        tg.call("deleteMessage", chat_id=chat, message_id=mid)
    except TGError:
        pass


# ---------------- tugmalar ----------------
def btn(key, data=None, url=None, **v):
    """Bazadagi (admin tahrirlaydigan) tugmadan Telegram tugmasini yasaydi."""
    b = db.button(key) or {"text": key, "uni": "", "cid": "", "style": "default"}
    text = render(b["text"] or "", v)
    label = text if b["cid"] else f"{b['uni']} {text}".strip()
    d = {"text": label or "·"}
    if data is not None:
        d["callback_data"] = data
    if url:
        d["url"] = url
    if b["style"] in STYLES:
        d["style"] = b["style"]
    if b["cid"]:
        d["icon_custom_emoji_id"] = b["cid"]
    return d


def ab(text, data=None, style=None, url=None):
    """Admin ichki tugmalari (dizaynda tahrirlanmaydi)."""
    d = {"text": text}
    if data is not None:
        d["callback_data"] = data
    if url:
        d["url"] = url
    if style:
        d["style"] = style
    return d


def ikb(*rows):
    return {"inline_keyboard": [list(r) for r in rows if r]}


def grid(items, per=2):
    return [items[i:i + per] for i in range(0, len(items), per)]


def reply_menu(scope, per=2):
    keys = [b["key"] for b in db.buttons(scope)]
    rows = grid([btn(k) for k in keys], per)
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


def user_menu():
    return reply_menu("user")


def admin_menu():
    return reply_menu("admin")


# ---------------- media ----------------
_MEDIA = {"photo": ("sendPhoto", "photo"), "video": ("sendVideo", "video"),
          "animation": ("sendAnimation", "animation"), "document": ("sendDocument", "document")}


def extract_media(m):
    if m.get("photo"):
        return "photo", m["photo"][-1]["file_id"]
    for k in ("video", "animation", "video_note", "document"):
        if m.get(k):
            return k, m[k]["file_id"]
    return "", ""


def msg_html(m):
    return to_html(m.get("text") or m.get("caption") or "", m.get("entities") or m.get("caption_entities"))


def send_media(chat, text, mtype="", fid="", markup=None):
    try:
        if mtype == "video_note" and fid:
            tg.call("sendVideoNote", chat_id=chat, video_note=fid)
        elif mtype in _MEDIA and fid:
            method, field = _MEDIA[mtype]
            if len(text or "") <= 1000:
                return tg.call(method, chat_id=chat, **{field: fid}, caption=text or None,
                               parse_mode="HTML", reply_markup=markup)
            tg.call(method, chat_id=chat, **{field: fid})
    except TGError as e:
        log.warning("media %s: %s", chat, e.desc)
        if e.code == 403:
            return None
    return say(chat, text, markup)


def send(chat, key, markup=None, **v):
    """Admin tahrirlaydigan xabarni (matn + media) yuboradi."""
    m = db.msg(key) or {"text": key, "mtype": "", "fid": ""}
    return send_media(chat, render(m["text"], v), m["mtype"], m["fid"], markup)
