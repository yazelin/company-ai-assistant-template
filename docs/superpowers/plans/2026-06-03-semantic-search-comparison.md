# Semantic-Search Comparison Second-Half Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a second course track that upgrades the keyword-baseline retrieval to real semantic retrieval (fastembed + numpy cosine), as a contrast lesson, with the same retrieval interface.

**Architecture:** Keep `app/search.py` (keyword) unchanged. Add `app/search_semantic.py` with the same `(query, limit) -> [{score, path, snippet}]` interface, ranking by embedding cosine similarity. fastembed is an optional `semantic` extra; `app/main.py` picks the backend via `SEARCH_BACKEND` (lazy-imports the semantic module). A contrast smoke test proves keyword returns 0 on a paraphrase while semantic finds the doc.

**Tech Stack:** Python 3.10+, uv, fastembed 0.8.x (optional extra), numpy, SQLite, GitHub Actions. No pytest — plain-python smoke scripts (family style).

---

## Preconditions / verified facts

Scratch-verified end-to-end (fastembed 0.8.0, model `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 384-dim):
- Storing each doc embedding as a JSON float array in a SQLite `embeddings(path, vector)` table, loading it back, and computing numpy cosine works.
- `index_semantic()` is idempotent (skips docs that already have an embedding).
- Contrast holds with the sample docs below: query `退費` → both keyword and semantic top = `refund.md` (consensus); query `我想把錢拿回來` → keyword **0 hits**, semantic top = `refund.md` (0.424). Deterministic across runs.
- `search_semantic` output shape `{score, path, snippet}` matches `search_docs`.
- fastembed prints a benign mean-pooling `UserWarning` for this model — ignore.
- Model is ~118MB; first download is slow (HF rate-limits unauthenticated) → CI caches `~/.cache/fastembed`.
- `app/db.py` and `app/search*.py` read `DATABASE_URL`/config at import, so tests set env BEFORE importing app modules.

**Working dir:** `/home/ct/company-ai-assistant-template`. Branch `feat/semantic-search-comparison-track` (not main).

**Sample docs fixture** (used verbatim by both smoke tests):
```python
SAMPLE = {
    "refund.md": "退費政策:顧客在購買後三十天內可申請全額退款,無需任何理由。",
    "hours.md": "營業時間:週一至週五 09:00 到 18:00,例假日公休。",
    "shipping.md": "出貨說明:訂單成立後兩個工作天內寄出,提供宅配與超商取貨。",
}
```

---

## File structure

| File | Responsibility |
|---|---|
| `pyproject.toml` (modify) | `semantic` optional extra |
| `app/db.py` (modify) | add `embeddings` table |
| `app/search_semantic.py` (create) | `_model` / `index_semantic` / `search_semantic` |
| `app/main.py` (modify) | `SEARCH_BACKEND` switch (lazy import) |
| `keyword_smoke_test.py` (create) | base-deps baseline smoke (keyword track) |
| `contrast_smoke_test_semantic.py` (create) | keyword-vs-semantic contrast (semantic track) |
| `.github/workflows/ci.yml` (create) | matrix: keyword + semantic (with model cache) |
| `docs/08-semantic-search-upgrade.md` (create) | the lesson |
| `docs/00-overview.md`, `tutorial.html`, `README.md`, `index.html`, `DESIGN.md` (modify) | two-track framing |

---

## Task 1: Add the semantic optional extra

**Files:** Modify `pyproject.toml`; regenerate `uv.lock`.

- [ ] **Step 1: Edit `pyproject.toml`** — add after the `dependencies = [...]` array (keep `[tool.uv] package = false`; do NOT add fastembed to required deps):

```toml
[project.optional-dependencies]
semantic = ["fastembed>=0.8,<0.9"]
```

- [ ] **Step 2: Regenerate lock + confirm base excludes fastembed.**

Run: `uv lock && uv sync && uv run python -c "import importlib.util as u; print('fastembed:', u.find_spec('fastembed') is not None)"`
Expected: `fastembed: False`.

- [ ] **Step 3: Confirm the extra installs fastembed 0.8.x.**

Run: `uv sync --extra semantic && uv run python -c "import fastembed; print(fastembed.__version__)"`
Expected: `0.8.x`.

- [ ] **Step 4: Restore base env.**

Run: `uv sync`

- [ ] **Step 5: Commit.**

```bash
git add pyproject.toml uv.lock
git commit -m "build: add optional semantic extra (fastembed)"
```

---

## Task 2: Add the embeddings table to db.py

**Files:** Modify `app/db.py`.

- [ ] **Step 1: Replace the entire `app/db.py` with:**

```python
import os, sqlite3
from dotenv import load_dotenv
load_dotenv(); DB=os.getenv("DATABASE_URL","assistant.db")
def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    c.execute("create table if not exists documents(id integer primary key,path text unique,content text)")
    c.execute("create table if not exists embeddings(path text primary key,vector text)")
    return c
```

- [ ] **Step 2: Verify Part 1 still works (the new table is additive).**

Run: `uv sync && PYTHONPATH=. uv run python -c "
import os, tempfile; os.environ['DATABASE_URL']=tempfile.mktemp(suffix='.db')
from app.db import conn
from app.search import search_docs
c=conn(); c.execute(\"insert into documents(path,content) values('refund.md','退費政策:三十天內可全額退款')\"); c.commit()
print('keyword 退費:', search_docs('退費')[0]['path'])
"`
Expected: `keyword 退費: refund.md` (documents + embeddings tables both create cleanly; keyword path unaffected).

- [ ] **Step 3: Commit.**

```bash
git add app/db.py
git commit -m "feat: add embeddings table for semantic retrieval"
```

---

## Task 3: Semantic retrieval + contrast/keyword smoke tests

**Files:** Create `app/search_semantic.py`, `keyword_smoke_test.py`, `contrast_smoke_test_semantic.py`.

- [ ] **Step 1: Create `keyword_smoke_test.py`** (base-deps baseline smoke — runs WITHOUT the extra):

```python
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
```

- [ ] **Step 2: Run the keyword smoke — must pass on base deps.**

Run: `uv sync && PYTHONPATH=. uv run python keyword_smoke_test.py`
Expected: `OK: keyword baseline smoke passed`, exit 0.

- [ ] **Step 3: Write the contrast test (this is the Part-2 test).** Create `contrast_smoke_test_semantic.py`:

```python
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
```

- [ ] **Step 4: Run it to verify it FAILS (search_semantic doesn't exist yet).**

Run: `uv sync --extra semantic && PYTHONPATH=. uv run python contrast_smoke_test_semantic.py; echo "exit=$?"`
Expected: non-zero exit — `ModuleNotFoundError: No module named 'app.search_semantic'`.

- [ ] **Step 5: Create `app/search_semantic.py`:**

```python
"""Semantic retrieval — the Part 2 upgrade to app/search.py's keyword baseline.

Same interface as search_docs: (query, limit) -> [{score, path, snippet}], but
ranks by embedding cosine similarity (fastembed, local, no API key) instead of
keyword counts. Requires the `semantic` extra: uv sync --extra semantic."""
import json
import numpy as np
from fastembed import TextEmbedding
from .db import conn

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_model_cache = None


def _model():
    global _model_cache
    if _model_cache is None:
        _model_cache = TextEmbedding(model_name=MODEL_NAME)
    return _model_cache


def index_semantic():
    """Embed and store any documents that lack an embedding. Idempotent."""
    c = conn()
    done = {r["path"] for r in c.execute("select path from embeddings")}
    rows = [r for r in c.execute("select path, content from documents") if r["path"] not in done]
    if not rows:
        return 0
    vectors = list(_model().embed([r["content"] for r in rows]))
    for r, v in zip(rows, vectors):
        c.execute("insert or replace into embeddings(path, vector) values(?, ?)",
                  (r["path"], json.dumps([float(x) for x in v])))
    c.commit()
    return len(rows)


def _cosine(a, b):
    a = np.array(a); b = np.array(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def search_semantic(query, limit=5):
    index_semantic()
    c = conn()
    qv = list(_model().embed([query]))[0]
    contents = {r["path"]: r["content"] for r in c.execute("select path, content from documents")}
    scored = []
    for r in c.execute("select path, vector from embeddings"):
        scored.append((_cosine(qv, json.loads(r["vector"])), r["path"], contents[r["path"]][:1200]))
    scored.sort(reverse=True)
    return [{"score": s, "path": p, "snippet": sn} for s, p, sn in scored[:limit]]
```

- [ ] **Step 6: Run the contrast test to verify it PASSES.**

Run: `PYTHONPATH=. uv run python contrast_smoke_test_semantic.py`
Expected: `OK: keyword->semantic contrast verified (keyword 0 / semantic finds it)`, exit 0. (Benign mean-pooling UserWarning may print; first run downloads the model.)

- [ ] **Step 7: Confirm the keyword smoke still passes on base deps (no regression).**

Run: `uv sync && PYTHONPATH=. uv run python keyword_smoke_test.py`
Expected: `OK: keyword baseline smoke passed`.

- [ ] **Step 8: Commit.**

```bash
git add app/search_semantic.py keyword_smoke_test.py contrast_smoke_test_semantic.py
git commit -m "feat: semantic retrieval (fastembed + cosine) with keyword/contrast smoke tests"
```

---

## Task 4: Wire the SEARCH_BACKEND switch into main.py

**Files:** Modify `app/main.py`.

- [ ] **Step 1: Replace the entire `app/main.py` with:**

```python
import os
from fastapi import FastAPI
from pydantic import BaseModel
from .search import search_docs
from .ai import answer
app=FastAPI(title="Company AI Assistant Template")
class AskRequest(BaseModel): question:str
def _retrieve(query):
    # SEARCH_BACKEND=semantic uses the Part 2 embedding retrieval (needs the
    # `semantic` extra); the default keeps the zero-extra keyword baseline so
    # the base import chain never touches fastembed.
    if os.getenv("SEARCH_BACKEND","keyword")=="semantic":
        from .search_semantic import search_semantic
        return search_semantic(query)
    return search_docs(query)
@app.get("/health")
def health(): return {"ok":True}
@app.post("/ask")
async def ask(req:AskRequest):
    docs=_retrieve(req.question); return {"answer":await answer(req.question,docs),"sources":docs}
```

- [ ] **Step 2: Verify base import works without fastembed (default keyword backend).**

Run: `uv sync && PYTHONPATH=. uv run python -c "import app.main; print('app.main imports on base deps: OK')"`
Expected: `app.main imports on base deps: OK` (no fastembed needed because the import is lazy and the default backend is keyword).

- [ ] **Step 3: Verify /ask works end-to-end in keyword mode (TestClient, base deps).**

Run: `PYTHONPATH=. uv run python -c "
import os, tempfile; os.environ['DATABASE_URL']=tempfile.mktemp(suffix='.db'); os.environ['AI_PROVIDER']='echo'
from app.db import conn
c=conn(); c.execute(\"insert into documents(path,content) values('refund.md','退費政策:三十天內可全額退款')\"); c.commit()
from starlette.testclient import TestClient; from app.main import app
r=TestClient(app).post('/ask', json={'question':'退費'})
print('status', r.status_code, '| sources[0]', r.json()['sources'][0]['path'])
"`
Expected: `status 200 | sources[0] refund.md`.

- [ ] **Step 4: Commit.**

```bash
git add app/main.py
git commit -m "feat: SEARCH_BACKEND switch to use semantic retrieval in /ask"
```

---

## Task 5: CI matrix (keyword + semantic, with model cache)

**Files:** Create `.github/workflows/ci.yml`.

- [ ] **Step 1: Create `.github/workflows/ci.yml`:**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  smoke-test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        track: [keyword, semantic]
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5

      # keyword track: base deps, keyword baseline
      - name: Sync (keyword)
        if: matrix.track == 'keyword'
        run: uv sync
      - name: Keyword baseline smoke
        if: matrix.track == 'keyword'
        run: PYTHONPATH=. uv run python keyword_smoke_test.py

      # semantic track: cache the embedding model, install the extra, run contrast
      - name: Cache fastembed model
        if: matrix.track == 'semantic'
        uses: actions/cache@v4
        with:
          path: ~/.cache/fastembed
          key: fastembed-paraphrase-multilingual-minilm-l12-v2
      - name: Sync with semantic extra
        if: matrix.track == 'semantic'
        run: uv sync --extra semantic
      - name: Keyword -> semantic contrast
        if: matrix.track == 'semantic'
        run: PYTHONPATH=. uv run python contrast_smoke_test_semantic.py
```

- [ ] **Step 2: Validate YAML.**

Run: `uv run --with pyyaml python -c "import yaml; d=yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok', d['jobs']['smoke-test']['strategy']['matrix']['track'])"`
Expected: `yaml ok ['keyword', 'semantic']`.

- [ ] **Step 3: Locally simulate both tracks.**

Run:
```bash
uv sync && PYTHONPATH=. uv run python keyword_smoke_test.py
uv sync --extra semantic && PYTHONPATH=. uv run python contrast_smoke_test_semantic.py
uv sync
```
Expected: two `OK:` lines.

- [ ] **Step 4: Commit.**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: matrix runs keyword + semantic tracks (semantic caches the model)"
```

---

## Task 6: Write the lesson `docs/08-semantic-search-upgrade.md`

**Files:** Create `docs/08-semantic-search-upgrade.md`.

- [ ] **Step 1: Create the file** with this content (Traditional Chinese; no emoji):

````markdown
# 企業 AI 助理入門模板：升級成語意檢索(對照組)

前半段(`01`/`03`)你已經用**關鍵字計次**做出最小的文件助理 —— 把查詢切詞、在每份文件數出現次數、排序。它誠實、好懂,但有個天花板:**換句話說就找不到**。這一段是課程後半:把同樣的檢索換成**真正的語意檢索**(embedding + 餘弦相似度),親眼看到差別。

獨立的一課 —— 先跑過前半段、撞到關鍵字的天花板,再回來看這段最有感。

## 先講結論:差在哪

| 面向 | 關鍵字(`app/search.py`) | 語意(`app/search_semantic.py`) |
|---|---|---|
| 比對方式 | 子字串出現次數 | embedding 餘弦相似度 |
| 換句話說 | 找不到(0 筆) | 找得到 |
| 介面 | `(query, limit) -> [{score, path, snippet}]` | **同簽章、同輸出形狀** |
| 相依 | 無第三方 | fastembed(optional `semantic` extra) |
| 成本 | 幾乎 0 | 模型 ~118MB、查詢多幾十毫秒、需先 index |

核心訊息:**升級換掉的是「怎麼比對」,不是「你的資料或回答邏輯」** —— `search_semantic` 回傳形狀跟 `search_docs` 完全一樣,所以 `/ask` 與 AI 回答層(`app/ai.py`)一行都不用改。

## 步驟 1:裝 fastembed

```bash
uv sync --extra semantic
```

成功的話 `uv run python -c "import fastembed; print(fastembed.__version__)"` 會印出 `0.8.x`。fastembed 是本地 ONNX embedding,**不需要 API key**,模型(`paraphrase-multilingual-MiniLM-L12-v2`,支援中文)第一次用會自動下載(~118MB)。

## 步驟 2:看 `app/search_semantic.py`

兩個動作:先把文件 embed 存起來(`index_semantic`),查詢時 embed 問句、算餘弦取 top-k:

```python
from fastembed import TextEmbedding
import numpy as np

emb = TextEmbedding(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

def cosine(a, b):
    a = np.array(a); b = np.array(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))
```

向量存在 SQLite 的 `embeddings` 表(JSON 浮點陣列);`index_semantic` 對已索引的文件略過(冪等),所以重跑不重算。

## 步驟 3:跑對照測試

跟 mcp / linebot 那兩課不同:那兩課證明兩種寫法**行為相同**;這課的兩種檢索**本來就該不一樣** —— 這正是重點。所以測的是**對照**:

```bash
uv sync --extra semantic
PYTHONPATH=. uv run python contrast_smoke_test_semantic.py
```

它用三份 sample 文件(退費 / 營業時間 / 出貨)斷言:

- **直接關鍵字查**「退費」→ 關鍵字版與語意版**都**命中 `refund.md`(共識,語意版沒退化基本能力)。
- **改寫查**「我想把錢拿回來」→ 關鍵字版 **0 筆**、語意版仍命中 `refund.md`(對照,升級的價值)。

成功會看到 `OK: keyword->semantic contrast verified (keyword 0 / semantic finds it)`。這就是語意檢索真正贏關鍵字的地方:使用者不會剛好用你文件裡的詞。

## 步驟 4:在真 app 切換

`/ask` 用 `SEARCH_BACKEND` 切換,預設 `keyword`、設 `semantic` 就改用語意版:

```bash
uv sync --extra semantic
SEARCH_BACKEND=semantic uv run uvicorn app.main:app
```

下游 AI 回答完全不變 —— 只是餵給它的「找到的文件」品質變好。

## 何時升級

- **關鍵字**(前半段):文件少、查詢用詞固定、極簡或不想帶模型相依、要零成本。
- **語意**(這一段):使用者會換句話說、同義詞多、跨語言、FAQ 命中率要高 —— 多帶一個本地模型,換到「懂意思」的檢索。

下一步若要再進階:chunking(長文切段再 embed)、hybrid(關鍵字 + 語意合併)、或文件量大時換向量索引(如 sqlite-vec)。本課把最小可動的語意檢索做到能跑、能對照,先把概念站穩。
````

- [ ] **Step 2: Verify the doc's commands work.**

Run: `uv sync --extra semantic && PYTHONPATH=. uv run python contrast_smoke_test_semantic.py && uv run python -c "import fastembed; print(fastembed.__version__)"`
Expected: the contrast OK line + `0.8.x`. If any quoted behavior differs, fix the doc.
Also: `grep -nP "[\x{1F000}-\x{1FAFF}\x{2600}-\x{27BF}\x{2B00}-\x{2BFF}]" docs/08-semantic-search-upgrade.md || echo "no emoji"` → `no emoji`.

- [ ] **Step 3: Commit.**

```bash
git add docs/08-semantic-search-upgrade.md
git commit -m "docs: add semantic-search upgrade second-half lesson (08)"
```

---

## Task 7: Reframe `docs/00-overview.md` as two tracks

**Files:** Modify `docs/00-overview.md`.

- [ ] **Step 1: Read it:** `cat docs/00-overview.md`.

- [ ] **Step 2: Insert this section after the first intro paragraph (before the next `##`), verbatim:**

```markdown
## 兩軌:先關鍵字、再語意

這份教材分兩段:

- **前半段(`01`、`03`)** — 用關鍵字計次做出最小文件助理,看懂檢索 → 組 context → 問 AI 的整條流程。
- **後半段(`08`)** — 把檢索升級成**語意檢索**(fastembed embedding + 餘弦)當對照組,體會「換句話說也找得到」,而 AI 回答層一行都不用改。

先用關鍵字撞到天花板,再換語意 —— 你會清楚知道升級換掉的是「怎麼比對」,不是你的資料或回答邏輯。
```

- [ ] **Step 3:** If the file lists the doc series, add an entry for `08-semantic-search-upgrade.md` (`把檢索升級成語意檢索的對照組`) in the existing list's style. If no such list, skip.

- [ ] **Step 4: Verify no emoji.**

Run: `grep -nP "[\x{1F000}-\x{1FAFF}\x{2600}-\x{27BF}\x{2B00}-\x{2BFF}]" docs/00-overview.md || echo "no emoji"`
Expected: `no emoji`.

- [ ] **Step 5: Commit.**

```bash
git add docs/00-overview.md
git commit -m "docs: reframe overview as two tracks (keyword + semantic)"
```

---

## Task 8: Mirror Part 2 into `tutorial.html` + TOC

**Files:** Modify `tutorial.html`.

- [ ] **Step 1: Read it:** `cat tutorial.html` — study `<section>`/`<h2>`/`<h3>`/`<pre><code>`/`<table>` conventions, the header TOC (`docs/NN-...` anchor links), and where `<main>` ends.

- [ ] **Step 2: Add an `08` TOC anchor.** After the last TOC anchor (the `07-...` link), add, matching the existing format:
`<a href='docs/08-semantic-search-upgrade.md'>08-semantic-search-upgrade</a>`

- [ ] **Step 3: Append a Part 2 `<section>`** inside `<main>` (after the last section, before `</main>`), mirroring `docs/08`. Use the file's element conventions. Include, matching docs/08 verbatim: the differences table (關鍵字 vs 語意), `uv sync --extra semantic`, the cosine snippet, the contrast command `PYTHONPATH=. uv run python contrast_smoke_test_semantic.py` + the consensus/contrast explanation (退費 both find / 我想把錢拿回來 keyword 0, semantic finds), and the `SEARCH_BACKEND=semantic uv run uvicorn app.main:app` switch. No fabricated output.

- [ ] **Step 4: Verify.**

Run:
```bash
uv run python -c "import html.parser; html.parser.HTMLParser().feed(open('tutorial.html').read()); print('html ok')"
grep -nP "[\x{1F000}-\x{1FAFF}\x{2600}-\x{27BF}\x{2B00}-\x{2BFF}]" tutorial.html || echo "no emoji"
tail -c 40 tutorial.html
```
Expected: `html ok`, `no emoji`, ends with `</body></html>`. New section inside `<main>`.

- [ ] **Step 5: Commit.**

```bash
git add tutorial.html
git commit -m "docs: mirror semantic Part 2 into tutorial.html + TOC"
```

---

## Task 9: Surface the two-track structure in README / index / DESIGN

**Files:** Modify `README.md`, `index.html`, `DESIGN.md`.

- [ ] **Step 1: Read all three** to find insertion points: `cat README.md DESIGN.md`; for index.html the features card.

- [ ] **Step 2: `README.md`** — add to the Features/功能 list (match existing style):

```markdown
- 語意檢索升級版(optional `semantic` extra)— 見 `docs/08-semantic-search-upgrade.md`
```

After the existing quick-start / run instructions, add:

````markdown
### 後半段:語意檢索版(對照組)

```bash
uv sync --extra semantic
PYTHONPATH=. uv run python contrast_smoke_test_semantic.py   # 關鍵字 0 / 語意找得到
SEARCH_BACKEND=semantic uv run uvicorn app.main:app          # /ask 改用語意檢索
```
````

If README has a docs/ link list, add `- 後半段(語意檢索對照組):docs/08-semantic-search-upgrade.md`.

- [ ] **Step 3: `DESIGN.md`** — in the 功能賣點/features list, add (match style):

```markdown
- 內建語意檢索對照組(後半段 `docs/08`):同介面把關鍵字檢索升級成 fastembed 語意檢索,免 API key
```

(If DESIGN.md already mentions "升級檢索 / embedding" as a future direction in a way that's now redundant, point it at the built-in docs/08 instead.)

- [ ] **Step 4: `index.html`** — in the features card `<ul>`, add one `<li>` matching sibling structure:

```html
<li><span>後半段把關鍵字檢索升級成語意檢索(對照組),免 API key 的本地 embedding</span></li>
```

- [ ] **Step 5: Verify.**

Run:
```bash
uv run python -c "import html.parser; html.parser.HTMLParser().feed(open('index.html').read()); print('index ok')"
test -f docs/08-semantic-search-upgrade.md && echo "link target exists"
grep -nP "[\x{1F000}-\x{1FAFF}\x{2600}-\x{27BF}\x{2B00}-\x{2BFF}]" README.md DESIGN.md index.html || echo "no emoji"
```
Expected: `index ok`, `link target exists`, `no emoji`.

- [ ] **Step 6: Commit.**

```bash
git add README.md index.html DESIGN.md
git commit -m "docs: surface the semantic-search second-half track in README/index/DESIGN"
```

---

## Final verification (after all tasks)

- [ ] **Both tracks green:**

```bash
uv sync && PYTHONPATH=. uv run python keyword_smoke_test.py
uv sync --extra semantic && PYTHONPATH=. uv run python contrast_smoke_test_semantic.py
uv sync
```
Expected: two `OK:` lines.

- [ ] **Base isolation:** `uv sync && PYTHONPATH=. uv run python -c "import app.main; import importlib.util as u; print('fastembed present:', u.find_spec('fastembed') is not None)"` → `fastembed present: False` and no import error.

- [ ] **No emoji drift:** `grep -rnP "[\x{1F000}-\x{1FAFF}\x{2600}-\x{27BF}\x{2B00}-\x{2BFF}]" docs/ README.md DESIGN.md tutorial.html index.html || echo "clean"`.

---

## Self-review notes (author)

- **Spec coverage:** §4 two-track → Tasks 3/4/6/7; §3 verified facts → Tasks 1/3 (scratch-proven); §5 files → Tasks 1-9; contrast (not parity) test → Task 3; SEARCH_BACKEND switch → Task 4; optional `semantic` extra → Task 1; CI matrix + model cache → Task 5; docs → Tasks 6-9.
- **Placeholder scan:** all code blocks complete and scratch-verified (db JSON-vector storage, idempotent index, numpy cosine, contrast, output-shape parity); doc tasks give exact insert blocks; tutorial/overview/README tasks read the file first because they adapt to existing structure, but the content to insert is fully specified.
- **Name consistency:** `search_docs` / `search_semantic` / `index_semantic` / `_model` / `_cosine` / `MODEL_NAME` / `embeddings` table / env `SEARCH_BACKEND`, `DATABASE_URL` / extra `semantic` / tests `keyword_smoke_test.py`, `contrast_smoke_test_semantic.py` — consistent across tasks.
