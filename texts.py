"""Standart matnlar va tugmalar. Hammasi admin paneldan o'zgartiriladi."""

# key: (admin uchun nomi, standart matn (HTML), mavjud o'zgaruvchilar)
MESSAGES = {
    "start": ("👋 Start matni",
              "👋 Assalomu alaykum, <b>{name}</b>!\n\n🎮 UC do'koniga xush kelibsiz.\n"
              "Bu yerda PUBG Mobile UC'ni qulay narxda, tez va ishonchli sotib olishingiz mumkin.\n\n"
              "Kerakli bo'limni tanlang 👇", "{name} {id} {balance}"),
    "menu": ("🏠 Asosiy menyu", "🏠 <b>Asosiy menyu</b>\nBo'limni tanlang 👇", ""),
    "admin_welcome": ("👑 Admin panel salomi", "👑 <b>Admin panel</b>\n\nKerakli bo'limni tanlang 👇", ""),
    "cancelled": ("❌ Bekor qilindi", "❌ Bekor qilindi.", ""),
    "sub_required": ("📢 Majburiy obuna", "📢 Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling, "
                     "so'ng <b>«Tekshirish»</b> tugmasini bosing:", ""),
    "sub_fail": ("⚠️ Obuna topilmadi", "❌ Siz hali hamma kanalga a'zo bo'lmadingiz!", ""),
    "banned": ("🚫 Ban xabari", "🚫 Siz botdan foydalanishdan bloklangansiz.", ""),
    "maintenance": ("🛠 Texnik ish", "🛠 Bot vaqtincha ishlamayapti. Birozdan so'ng qayta urinib ko'ring.", ""),
    "profile": ("👤 Hisobim", "👤 <b>Mening hisobim</b>\n\n🆔 ID: <code>{id}</code>\n👤 Ism: {name}\n"
                "💰 Balans: <b>{balance}</b> so'm\n🛒 Buyurtmalar: {orders} ta\n💸 Sarflangan: {spent} so'm\n"
                "👥 Takliflar: {refs} ta", "{id} {name} {balance} {orders} {spent} {refs}"),
    "buy_empty": ("🎮 UC yo'q", "😔 Hozircha sotuvda UC paketlar yo'q. Keyinroq qayta urinib ko'ring.", ""),
    "buy_choose": ("🎮 UC tanlash", "🎮 <b>UC sotib olish</b>\n\n💰 Balansingiz: <b>{balance}</b> so'm\n\n"
                   "Kerakli paketni tanlang 👇", "{balance}"),
    "ask_player": ("🆔 Player ID so'rash", "🆔 PUBG Mobile <b>Player ID</b> raqamingizni yuboring:", ""),
    "bad_player": ("⚠️ Noto'g'ri ID", "⚠️ ID noto'g'ri. Faqat raqamlardan iborat ID yuboring (5–20 xona).", ""),
    "buy_confirm": ("📋 Buyurtmani tasdiqlash", "📋 <b>Buyurtmani tasdiqlang</b>\n\n🎮 UC: <b>{uc}</b>\n"
                    "💰 Narx: <b>{price}</b> so'm\n🆔 Player ID: <code>{player}</code>\n\n"
                    "Narx balansingizdan yechiladi.", "{uc} {price} {player}"),
    "no_balance": ("❌ Balans yetarli emas", "❌ Balansingizda mablag' yetarli emas.\n\nKerak: <b>{price}</b> so'm\n"
                   "Sizda: <b>{balance}</b> so'm\n\n«Hisob to'ldirish» orqali balansni to'ldiring.", "{price} {balance}"),
    "order_created": ("✅ Buyurtma qabul qilindi", "✅ <b>Buyurtma #{id} qabul qilindi!</b>\n\n🎮 {uc} UC\n"
                      "🆔 <code>{player}</code>\n\nUC tez orada hisobingizga tashlab beriladi.", "{id} {uc} {price} {player}"),
    "order_done": ("🎉 Buyurtma bajarildi", "🎉 <b>Buyurtma #{id} bajarildi!</b>\n\n🎮 {uc} UC "
                   "<code>{player}</code> ID'ga tashlandi. Xaridingiz uchun rahmat!", "{id} {uc} {player}"),
    "order_canceled": ("❌ Buyurtma bekor qilindi", "❌ <b>Buyurtma #{id} bekor qilindi.</b>\n"
                       "💰 {price} so'm balansingizga qaytarildi.", "{id} {uc} {price}"),
    "topup_choose": ("💰 To'lov usulini tanlash", "💰 <b>Hisob to'ldirish</b>\n\nTo'lov usulini tanlang 👇", ""),
    "topup_none": ("⚠️ To'lov usuli yo'q", "⚠️ Hozircha to'lov usullari sozlanmagan. Admin bilan bog'laning.", ""),
    "ask_amount": ("💵 Summa so'rash", "💵 To'ldirish summasini so'mda yuboring.\n\n"
                   "⬇️ Minimal: <b>{min}</b> so'm\n⬆️ Maksimal: <b>{max}</b> so'm", "{min} {max}"),
    "bad_amount": ("⚠️ Noto'g'ri summa", "⚠️ Summa noto'g'ri. {min} dan {max} so'mgacha raqam yuboring.", "{min} {max}"),
    "stars_info": ("⭐ Stars to'lov", "⭐ <b>{stars} Stars</b> ≈ {amount} so'm.\nQuyidagi hisobni to'lang — "
                   "to'lov darhol balansga tushadi.", "{stars} {amount}"),
    "checkout_info": ("⚡ Checkout to'lov", "⚡ <b>To'lov yaratildi</b>\n\n💵 Summa: <b>{amount}</b> so'm\n\n"
                      "«To'lash» tugmasini bosib Click, Payme yoki karta orqali to'lang. "
                      "To'lov avtomatik tekshiriladi va balansga tushadi.", "{amount}"),
    "pay_pending": ("⏳ To'lov kutilmoqda", "⏳ To'lov hali tasdiqlanmadi. To'lagan bo'lsangiz, bir oz kuting.", ""),
    "pay_failed": ("❌ To'lov bekor", "❌ To'lov bekor qilingan yoki muddati tugagan.", ""),
    "manual_info": ("💳 Qo'lda to'lov", "💳 <b>Qo'lda to'lov</b>\n\n💳 Karta: <code>{card}</code>\n👤 Egasi: {holder}\n"
                    "💵 Summa: <b>{amount}</b> so'm\n\nTo'lovni qilib, <b>chek (screenshot)</b> yuboring 👇", "{card} {holder} {amount}"),
    "manual_sent": ("✅ Chek yuborildi", "✅ Chekingiz adminga yuborildi. Tasdiqlangach balansga tushadi.", ""),
    "manual_ok": ("✅ Chek tasdiqlandi", "✅ To'lovingiz tasdiqlandi! +{amount} so'm\n💰 Balans: {balance} so'm", "{amount} {balance}"),
    "manual_no": ("❌ Chek rad etildi", "❌ To'lovingiz rad etildi. Savol bo'lsa admin bilan bog'laning.", ""),
    "topup_ok": ("✅ Balans to'ldirildi", "✅ Balansingiz <b>{amount}</b> so'mga to'ldirildi!\n💰 Balans: <b>{balance}</b> so'm", "{amount} {balance}"),
    "ref_info": ("🎁 Referal matni", "🎁 <b>Referal tizimi</b>\n\nDo'stlaringizni taklif qiling va bonus oling!\n"
                 "💵 Har bir taklif uchun: <b>{bonus}</b> so'm\n📈 Do'stingiz to'ldirgan summadan: <b>{percent}%</b>\n\n"
                 "🔗 Sizning havolangiz:\n<code>{link}</code>\n\n👥 Takliflar: {refs} ta\n💰 Ishlangan: {earned} so'm",
                 "{bonus} {percent} {link} {refs} {earned}"),
    "ref_new": ("🎉 Yangi taklif xabari", "🎉 Havolangiz orqali yangi foydalanuvchi qo'shildi! +{bonus} so'm", "{bonus}"),
    "guides_header": ("📖 Qo'llanmalar sarlavhasi", "📖 <b>Qo'llanmalar</b>\n\nKerakli qo'llanmani tanlang 👇", ""),
    "guides_empty": ("📖 Qo'llanma yo'q", "📖 Hozircha qo'llanmalar qo'shilmagan.", ""),
    "help_header": ("🆘 Yordam sarlavhasi", "🆘 <b>Yordam</b>\n\nKerakli bo'limni tanlang 👇", ""),
    "help_empty": ("🆘 Yordam yo'q", "🆘 Hozircha yordam bo'limlari qo'shilmagan.", ""),
    "contact": ("📞 Aloqa", "📞 <b>Admin bilan aloqa</b>\n\n{admin}", "{admin}"),
    "prices_header": ("💱 Narxlar sarlavhasi", "💱 <b>UC narxlari</b>\n\n{list}", "{list}"),
}

# (key, scope, unicode emoji, matn, rang)  rang: success=yashil, primary=ko'k, danger=qizil, default
BUTTONS = [
    # ---- foydalanuvchi menyusi (10 ta) ----
    ("topup", "user", "💰", "Hisob to'ldirish", "success"),
    ("buy", "user", "🎮", "UC sotib olish", "success"),
    ("profile", "user", "👤", "Mening hisobim", "primary"),
    ("orders", "user", "📦", "Buyurtmalarim", "primary"),
    ("history", "user", "🧾", "To'lovlarim", "primary"),
    ("prices", "user", "💱", "UC narxlari", "primary"),
    ("ref", "user", "🎁", "Referal", "primary"),
    ("guides", "user", "📖", "Qo'llanmalar", "danger"),
    ("help", "user", "🆘", "Yordam", "danger"),
    ("contact", "user", "📞", "Aloqa", "danger"),
    # ---- admin menyusi ----
    ("a_uc", "admin", "📦", "UC paketlar", "success"),
    ("a_orders", "admin", "📥", "Buyurtmalar", "success"),
    ("a_pay", "admin", "💳", "To'lov tizimlari", "primary"),
    ("a_users", "admin", "👥", "Foydalanuvchilar", "primary"),
    ("a_stats", "admin", "📊", "Statistika", "primary"),
    ("a_cast", "admin", "📢", "Xabar yuborish", "primary"),
    ("a_msgs", "admin", "📝", "Matnlar", "primary"),
    ("a_design", "admin", "🎨", "Dizayn", "success"),
    ("a_guides", "admin", "📖", "Qo'llanmalar", "primary"),
    ("a_help", "admin", "🆘", "Yordam", "primary"),
    ("a_channels", "admin", "📡", "Majburiy obuna", "primary"),
    ("a_ref", "admin", "🎁", "Referal sozlash", "primary"),
    ("a_balance", "admin", "💰", "Balans boshqarish", "success"),
    ("a_ban", "admin", "🚫", "Ban / Unban", "danger"),
    ("a_settings", "admin", "⚙️", "Sozlamalar", "primary"),
    ("a_exit", "admin", "🏠", "Chiqish", "danger"),
    # ---- inline tugmalar ----
    ("pkg", "inline", "🎮", "{uc} UC — {price} so'm", "primary"),
    ("item", "inline", "📄", "{title}", "primary"),
    ("ch_join", "inline", "📢", "{title}", "primary"),
    ("i_check", "inline", "✅", "Tekshirish", "success"),
    ("i_confirm", "inline", "✅", "Tasdiqlash", "success"),
    ("i_cancel", "inline", "❌", "Bekor qilish", "danger"),
    ("i_stars", "inline", "⭐", "Telegram Stars", "primary"),
    ("i_checkout", "inline", "⚡", "Avto to'lov (Click/Payme/Karta)", "success"),
    ("i_manual", "inline", "💳", "Qo'lda to'lov", "danger"),
    ("i_pay", "inline", "💳", "To'lash", "success"),
    ("i_paycheck", "inline", "🔄", "To'lovni tekshirish", "primary"),
    ("i_done", "inline", "✅", "Bajarildi", "success"),
    ("i_refund", "inline", "❌", "Bekor qilish", "danger"),
    ("i_approve", "inline", "✅", "Tasdiqlash", "success"),
    ("i_reject", "inline", "❌", "Rad etish", "danger"),
]

SCOPE_TITLES = {"user": "👤 Foydalanuvchi menyusi", "admin": "👑 Admin menyusi", "inline": "🔘 Inline tugmalar"}
