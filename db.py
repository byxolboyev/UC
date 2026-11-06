"""SQLite baza (thread-safe)."""
import re
import sqlite3
import threading
import time

import config
import texts

_lock = threading.RLock()
_con = sqlite3.connect(config.DB_PATH, check_same_thread=False, isolation_level=None)
_con.row_factory = sqlite3.Row
_con.execute("PRAGMA journal_mode=WAL")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, username TEXT, balance INTEGER DEFAULT 0,
  ref_by INTEGER, ref_count INTEGER DEFAULT 0, ref_earned INTEGER DEFAULT 0, ref_paid INTEGER DEFAULT 0,
  banned INTEGER DEFAULT 0, last_player TEXT DEFAULT '', spent INTEGER DEFAULT 0, topped INTEGER DEFAULT 0, joined INTEGER);
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS messages(key TEXT PRIMARY KEY, text TEXT, mtype TEXT DEFAULT '', fid TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS buttons(key TEXT PRIMARY KEY, scope TEXT, pos INTEGER, text TEXT,
  uni TEXT DEFAULT '', cid TEXT DEFAULT '', style TEXT DEFAULT 'default');
CREATE TABLE IF NOT EXISTS packages(id INTEGER PRIMARY KEY AUTOINCREMENT, uc INTEGER, price INTEGER, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER, uc INTEGER, price INTEGER,
  player TEXT, status TEXT, created INTEGER, admin_id INTEGER);
CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER, provider TEXT, amount INTEGER,
  status TEXT, ext_id TEXT, uuid TEXT, created INTEGER, paid INTEGER);
CREATE UNIQUE INDEX IF NOT EXISTS ux_pay ON payments(provider, ext_id) WHERE ext_id IS NOT NULL;
CREATE TABLE IF NOT EXISTS channels(id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT, title TEXT, link TEXT);
CREATE TABLE IF NOT EXISTS guides(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, title TEXT, text TEXT DEFAULT '',
  mtype TEXT DEFAULT '', fid TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY);
"""


def q(sql, a=()):
    with _lock:
        return [dict(r) for r in _con.execute(sql, a).fetchall()]


def one(sql, a=()):
    r = q(sql, a)
    return r[0] if r else None


def ex(sql, a=()):
    with _lock:
        return _con.execute(sql, a)


def now():
    return int(time.time())


# ---------------- sozlamalar ----------------
def get(k, default=""):
    r = one("SELECT v FROM settings WHERE k=?", (k,))
    return r["v"] if r and r["v"] is not None else default


def geti(k, default=0):
    try:
        return int(get(k, default))
    except (TypeError, ValueError):
        return default


def put(k, v):
    ex("INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))


# ---------------- foydalanuvchilar ----------------
def user(uid):
    return one("SELECT * FROM users WHERE id=?", (uid,))


def add_balance(uid, amount):
    ex("UPDATE users SET balance=balance+? WHERE id=?", (amount, uid))


def take_balance(uid, amount):
    """Atomik yechish. Yetarli bo'lmasa False."""
    return ex("UPDATE users SET balance=balance-? WHERE id=? AND balance>=?", (amount, uid, amount)).rowcount == 1


# ---------------- xabarlar ----------------
def msg(key):
    return one("SELECT * FROM messages WHERE key=?", (key,))


def set_msg(key, **f):
    cols = [c for c in f if c in ("text", "mtype", "fid")]
    if cols:
        ex(f"UPDATE messages SET {', '.join(c + '=?' for c in cols)} WHERE key=?", [f[c] for c in cols] + [key])


def reset_msg(key):
    ex("UPDATE messages SET text=?, mtype='', fid='' WHERE key=?", (texts.MESSAGES[key][1], key))


# ---------------- tugmalar ----------------
_bcache = None


def _buttons():
    global _bcache
    if _bcache is None:
        _bcache = q("SELECT * FROM buttons ORDER BY pos")
    return _bcache


def touch_buttons():
    global _bcache
    _bcache = None


def button(key):
    for b in _buttons():
        if b["key"] == key:
            return b
    return None


def buttons(scope):
    return [b for b in _buttons() if b["scope"] == scope]


def set_button(key, **f):
    cols = [c for c in f if c in ("text", "uni", "cid", "style")]
    if cols:
        ex(f"UPDATE buttons SET {', '.join(c + '=?' for c in cols)} WHERE key=?", [f[c] for c in cols] + [key])
        touch_buttons()


def reset_button(key):
    for k, scope, uni, text, style in texts.BUTTONS:
        if k == key:
            ex("UPDATE buttons SET text=?, uni=?, cid='', style=? WHERE key=?", (text, uni, style, key))
    touch_buttons()


def reset_all_buttons():
    for k, *_ in texts.BUTTONS:
        reset_button(k)


def _norm(s):
    return re.sub(r"^[^\w]+", "", s or "").strip().lower()


def find_button(text, scopes):
    n = _norm(text)
    if not n:
        return None
    for b in _buttons():
        if b["scope"] in scopes and _norm(b["text"]) == n:
            return b
    return None


# ---------------- ro'yxatlar ----------------
def packages(active_only=True):
    return q("SELECT * FROM packages" + (" WHERE active=1" if active_only else "") + " ORDER BY uc")


def channels():
    return q("SELECT * FROM channels ORDER BY id")


def guides(kind):
    return q("SELECT * FROM guides WHERE kind=? ORDER BY id", (kind,))


def seed():
    with _lock:
        _con.executescript(SCHEMA)
        for key, (_t, text, _v) in texts.MESSAGES.items():
            ex("INSERT OR IGNORE INTO messages(key,text) VALUES(?,?)", (key, text))
        for pos, (key, scope, uni, text, style) in enumerate(texts.BUTTONS):
            ex("INSERT OR IGNORE INTO buttons(key,scope,pos,text,uni,style) VALUES(?,?,?,?,?,?)",
               (key, scope, pos, text, uni, style))
    touch_buttons()


seed()
