#!/usr/bin/env bash
# Bazani shifrlab, `data` branch'ga yozadi (har safar bitta commit, eskilari o'chadi).
set -euo pipefail
[ -f ucshop.db ] || { echo "baza yo'q, zaxira o'tkazib yuborildi"; exit 0; }
: "${DB_PASSPHRASE:?DB_PASSPHRASE secret kiritilmagan}"

rm -f /tmp/snap.db
python3 - <<'PY'
import sqlite3
s = sqlite3.connect("ucshop.db")
d = sqlite3.connect("/tmp/snap.db")
s.backup(d)
d.close(); s.close()
PY
openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:DB_PASSPHRASE -in /tmp/snap.db -out /tmp/ucshop.db.enc

rm -rf /tmp/databr && mkdir /tmp/databr
cp /tmp/ucshop.db.enc /tmp/databr/
cd /tmp/databr
git init -q
git checkout -q -b data
git add ucshop.db.enc
git -c user.name=bot -c user.email=bot@users.noreply.github.com commit -qm "db zaxira $(date -u +%FT%TZ)"
git push -q -f "https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" data
echo "zaxira saqlandi"