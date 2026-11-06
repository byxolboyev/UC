"""Telegram Bot API uchun yengil klient (faqat requests kerak)."""
import html
import json
import logging
import time

import requests

log = logging.getLogger("tg")


class TGError(Exception):
    def __init__(self, desc, code=0, params=None):
        super().__init__(desc)
        self.desc, self.code, self.params = desc, code, params or {}


_FANCY_HINT = ("button", "style", "icon", "emoji")


def strip_fancy(markup):
    """Rang va premium emojini olib tashlaydi (eski klient/akkaunt uchun zaxira)."""
    def clean(b):
        return {k: v for k, v in b.items() if k not in ("style", "icon_custom_emoji_id")}
    if isinstance(markup, dict):
        if "inline_keyboard" in markup:
            return {"inline_keyboard": [[clean(b) for b in r] for r in markup["inline_keyboard"]]}
        if "keyboard" in markup:
            m = dict(markup)
            m["keyboard"] = [[clean(b) for b in r] for r in markup["keyboard"]]
            return m
    return markup


class TG:
    def __init__(self, token):
        self.base = f"https://api.telegram.org/bot{token}/"
        self.s = requests.Session()

    def call(self, method, _timeout=30, **p):
        stripped = parse_off = False
        for attempt in range(5):
            data = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
                    for k, v in p.items() if v is not None}
            try:
                j = self.s.post(self.base + method, data=data, timeout=_timeout).json()
            except requests.RequestException as e:
                if attempt >= 3:
                    raise TGError(f"network: {e}")
                time.sleep(1 + attempt)
                continue
            except ValueError:
                raise TGError("bad json from telegram")
            if j.get("ok"):
                return j["result"]
            desc, code, prm = j.get("description", ""), j.get("error_code", 0), j.get("parameters", {})
            low = desc.lower()
            if code == 429:
                time.sleep(prm.get("retry_after", 1) + 0.5)
                continue
            if code == 400 and p.get("reply_markup") and not stripped \
                    and any(h in low for h in _FANCY_HINT) and "not modified" not in low:
                log.warning("rang/emoji qabul qilinmadi (%s) -> oddiy tugmalar", desc)
                p["reply_markup"] = strip_fancy(p["reply_markup"])
                stripped = True
                continue
            if code == 400 and "parse entities" in low and p.get("parse_mode") and not parse_off:
                p.pop("parse_mode")
                parse_off = True
                continue
            raise TGError(desc, code, prm)
        raise TGError("too many retries")


_TAGS = {
    "bold": ("<b>", "</b>"), "italic": ("<i>", "</i>"), "underline": ("<u>", "</u>"),
    "strikethrough": ("<s>", "</s>"), "spoiler": ("<tg-spoiler>", "</tg-spoiler>"),
    "code": ("<code>", "</code>"), "pre": ("<pre>", "</pre>"),
    "blockquote": ("<blockquote>", "</blockquote>"),
    "expandable_blockquote": ("<blockquote expandable>", "</blockquote>"),
}


def to_html(text, entities=None):
    """Telegram entity'larini (premium emoji ham) HTML'ga aylantiradi."""
    if not text:
        return ""
    opens, closes = {}, {}
    for i, e in enumerate(entities or []):
        t = e.get("type")
        if t in _TAGS:
            a, b = _TAGS[t]
        elif t == "text_link":
            a, b = f'<a href="{html.escape(e["url"], quote=True)}">', "</a>"
        elif t == "custom_emoji":
            a, b = f'<tg-emoji emoji-id="{e["custom_emoji_id"]}">', "</tg-emoji>"
        else:
            continue
        s, ln = e["offset"], e["length"]
        opens.setdefault(s, []).append((-ln, i, a))
        closes.setdefault(s + ln, []).append((ln, -i, b))
    out, pos = [], 0

    def flush(p):
        for _, _, b in sorted(closes.get(p, [])):
            out.append(b)
        for _, _, a in sorted(opens.get(p, [])):
            out.append(a)

    for ch in text:
        flush(pos)
        out.append(html.escape(ch, quote=False))
        pos += 2 if ord(ch) > 0xFFFF else 1
    for _, _, b in sorted(closes.get(pos, [])):
        out.append(b)
    return "".join(out)
