#!/usr/bin/env python3
"""Contrast check for the keyword -> semantic upgrade (semantic-only; needs the
`semantic` extra). Unlike mcp/linebot's parity tests, the two retrievers SHOULD
differ: on a direct keyword query both find the doc (consensus); on a paraphrase
the keyword search returns nothing but semantic finds it (the upgrade's value).
Exits non-zero on failure so CI can gate on it."""
import os, sys, tempfile
os.environ["DATABASE_URL"] = tempfile.mktemp(suffix=".db")
from app.db import conn
from app.search import search_docs
from app.search_semantic import search_semantic

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

# Consensus: a direct keyword query — both retrievers find the refund doc.
kw = search_docs("退費"); se = search_semantic("退費")
check(bool(kw) and kw[0]["path"] == "refund.md", "keyword '退費' -> refund")
check(se[0]["path"] == "refund.md", "semantic '退費' -> refund")

# Contrast: a paraphrase with no shared keywords — keyword finds nothing,
# semantic still finds the refund doc.
kw2 = search_docs("我想把錢拿回來"); se2 = search_semantic("我想把錢拿回來")
check(kw2 == [], f"keyword paraphrase -> 0 hits (got {len(kw2)})")
check(se2[0]["path"] == "refund.md", "semantic paraphrase -> refund")
check(set(se2[0]) == {"score", "path", "snippet"}, "semantic output shape matches search_docs")

if failures:
    print("FAIL:", "; ".join(failures), file=sys.stderr)
    sys.exit(1)
print("OK: keyword->semantic contrast verified (keyword 0 / semantic finds it)")
