# 🎮 UC Shop Bot

Telegram'da PUBG UC sotish boti. **UC'ni bot emas, admin qo'lda tashlaydi** — bot faqat buyurtma va to'lovlarni qabul qiladi.
Hamma narsa (UC paketlar, narxlar, matnlar, tugmalar, ranglar, premium emoji, to'lov tizimlari) admin paneldan boshqariladi.

## Imkoniyatlar

- 🎮 **10 ta foydalanuvchi tugmasi**: Hisob to'ldirish, UC sotib olish, Hisobim, Buyurtmalarim, To'lovlarim, UC narxlari, Referal, Qo'llanmalar, Yordam, Aloqa
- 💳 **To'lov**: Telegram Stars (avto), **checkout.uz** (avto: Click / Payme / Uzcard / Humo), qo'lda to'lov (chek + admin tasdiqlaydi)
- 📦 **UC paketlar bo'sh** — admin kiritmaguncha hech narsa yo'q (UC soni va narxini admin qo'shadi)
- 🎨 **Dizayn bo'limi**: tugma matni, rangi (🟢 yashil / 🔵 ko'k / 🔴 qizil), emoji, **premium emoji**, premium emoji paketdan avto-moslash
- 📝 **Matnlar**: har bir xabarga matn, rasm, video, GIF, **dumaloq video** qo'shish; premium emoji va formatlash saqlanadi
- 📖 Qo'llanmalar va 🆘 Yordam — qo'shish, tahrirlash, o'chirish, har biriga media
- 📡 Majburiy obuna (bir nechta kanal)
- 🎁 Referal: har bir taklif uchun bonus + do'st to'ldirgan summadan foiz
- 📢 Hammaga xabar yuborish, 👥 foydalanuvchi qidirish, balans qo'shish/ayirish, ban, 📊 statistika
- 📥 Buyurtmalar kanaliga ham xabar yuborish (ixtiyoriy)

## O'rnatish (Termux yoki VPS)

```bash
pkg install python git        # Termux; VPS'da: apt install python3 python3-pip git
git clone https://github.com/<login>/<repo>.git ucshop && cd ucshop
pip install -r requirements.txt
python main.py                # birinchi marta token va admin ID so'raydi
```

Token — [@BotFather](https://t.me/BotFather), admin ID — [@userinfobot](https://t.me/userinfobot).
Ular `.env` faylga yoziladi (**`.env` GitHub'ga yuklanmaydi** — `.gitignore`'da). Qo'lda ham yaratish mumkin: `.env.example`'ni nusxalang.

Doimiy ishlashi uchun: `nohup python main.py &` yoki `screen`/`tmux`/`systemd`.

## Admin panel

Botda `/admin` yozing. 16 ta tugma:
UC paketlar · Buyurtmalar · To'lov tizimlari · Foydalanuvchilar · Statistika · Xabar yuborish · Matnlar · **Dizayn** · Qo'llanmalar · Yordam · Majburiy obuna · Referal · Balans · Ban · Sozlamalar · Chiqish

### Birinchi sozlash tartibi
1. **UC paketlar** → ➕ → UC soni → narxi
2. **To'lov tizimlari**:
   - ⭐ Stars: «1 Star = necha so'm» kiriting (masalan 250)
   - ⚡ Checkout.uz: kassadan **API kalit** oling, kiriting, «🧪 Kalitni tekshirish» bosing
   - 💳 Qo'lda: karta raqami va egasi
3. **Majburiy obuna** (ixtiyoriy): botni kanalga admin qiling → ➕ → @kanal
4. **Sozlamalar** → Aloqa matni, buyurtmalar kanali

Sozlanmagan to'lov usuli foydalanuvchiga ko'rinmaydi.

### checkout.uz haqida
- Bot to'lovni **o'zi tekshirib turadi** (har ~12 soniyada) — webhook/server shart emas, Termux'da ham ishlaydi.
- Kassa sozlamasida **IP-whitelist** yoqilgan bo'lsa, bot ishlayotgan serverning IP'sini qo'shing (Termux'da IP o'zgarib turadi — whitelist'ni o'chirib qo'yish qulayroq).
- Ixtiyoriy webhook (VPS): `.env`ga `WEBHOOK_PORT=8080` va `WEBHOOK_PUBLIC_URL=https://domen.uz` qo'ying. Webhook faqat tekshiruvni tezlashtiradi: bot har doim to'lovni API'dan qayta tekshiradi, soxta so'rov balansni to'ldira olmaydi.
- Minimal summa 1 000, maksimal 10 000 000 so'm (checkout.uz cheklovi).

### Premium emoji
- Tugmalarda premium emoji ko'rinishi uchun **bot egasida Telegram Premium** bo'lishi kerak (yoki botda Fragment username).
- **Dizayn → 🪄 avto-moslash**: premium emoji paketining havolasini (`t.me/addemoji/...`) yuboring — har bir tugma o'z oddiy emojisiga mos premium emoji oladi. Mos kelmaganlarini «⭐ Premium emoji qo'yish» bilan qo'lda qo'ying.
- Matnlarga premium emoji qo'yish: «Matnlar» bo'limida matnni premium emoji bilan yuboring — saqlanadi.
- Telegram rang/emojini qabul qilmasa, bot o'zi oddiy tugmalarga o'tadi (xato bermaydi). Tugma ranglari Telegram'ning 2026-yil fevralidan keyingi versiyalarida ko'rinadi.

### Matn o'zgaruvchilari
`{name}` `{id}` `{balance}` `{uc}` `{price}` `{player}` ... — har bir matn kartasida ko'rsatiladi, o'chirmang.

## Xavfsizlik
- Token va API kalit repoga tushmaydi (`.env`, `ucshop.db` — `.gitignore`'da).
- Agar token yoki API kalitni biror joyda ochiq yuborgan bo'lsangiz — @BotFather orqali token'ni yangilang.
- To'lovlar bazada `UNIQUE` va atomik yangilanish bilan himoyalangan: bitta to'lov balansni ikki marta to'ldirmaydi.

## Fayllar
`main.py` (ishga tushirish) · `user.py` (foydalanuvchi) · `admin.py` (admin panel) · `core.py` · `db.py` · `ui.py` · `tg.py` · `checkout.py` · `texts.py` · `config.py`