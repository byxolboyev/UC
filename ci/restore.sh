#!/usr/bin/env bash
# `data` branch'dagi shifrlangan zaxiradan bazani tiklaydi.
# Xato bo'lsa ishni TO'XTATADI: bo'sh baza bilan boshlab, yaxshi zaxira ustiga yozib yubormaslik uchun.
set -euo pipefail
: "${DB_PASSPHRASE:?DB_PASSPHRASE secret kiritilmagan}"

set +e
git ls-remote --exit-code --heads origin data >/dev/null 2>&1
rc=$?
set -e
if [ "$rc" -eq 2 ]; then
  echo "Zaxira topilmadi — yangi baza yaratiladi (birinchi ishga tushirish)."
  exit 0
fi
[ "$rc" -eq 0 ] || { echo "Git bilan bog'lanib bo'lmadi (kod $rc)"; exit 1; }

git fetch -q origin +data:refs/remotes/origin/data
git show origin/data:ucshop.db.enc > /tmp/ucshop.db.enc
openssl enc -d -aes-256-cbc -pbkdf2 -pass env:DB_PASSPHRASE -in /tmp/ucshop.db.enc -out ucshop.db
echo "Baza tiklandi."