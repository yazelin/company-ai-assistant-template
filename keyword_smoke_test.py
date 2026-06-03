#!/usr/bin/env python3
"""Keyword baseline smoke (base deps, no extra). Confirms the baseline finds a
direct keyword query but returns nothing for a paraphrase — the gap Part 2 fills.
Exits non-zero on failure."""
import os, sys, tempfile
os.environ["DATABASE_URL"] = tempfile.mktemp(suffix=".db")
from app.db import conn
from app.search import search_docs

SAMPLE = {
    "refund.md": "退費政策:顧客在購買後三十天內可申請全額退款,無需任何理由。",
    "hours.md": "營業時間:週一至週五 09:00 到 18:00,例假日公休。",
    "shipping.md": "出貨說明:訂單成立後兩個工作天內寄出,提供宅配與超商取貨。",
}
c = conn()
for path, content in SAMPLE.items():
    c.execute("insert or replace into documents(path, content) values(?, ?)", (path, content))
c.commit()

failures = []
def check(cond, label):
    if not cond:
        failures.append(label)

kw = search_docs("退費")
check(bool(kw) and kw[0]["path"] == "refund.md", "keyword '退費' -> refund")
check(search_docs("我想把錢拿回來") == [], "keyword paraphrase -> 0 hits")

if failures:
    print("FAIL:", "; ".join(failures), file=sys.stderr)
    sys.exit(1)
print("OK: keyword baseline smoke passed")
