# 企業內部 AI 助理模板：帶你走一遍

`01-quickstart.md` 讓服務跑起來。這份文件帶你做兩件真正有價值的事：

1. 把「你自己的文件」加進去，證明它真的被檢索到（含真實 before / after）。
2. 從 `echo` 換成真實的 HTTP LLM provider。

下面的輸出都是本機真的跑出來貼上的。假設你已照 quickstart 跑過 ingest、服務在 `127.0.0.1:8000`。

## 第一部分：加一份自己的文件，看它被檢索到

### Before：先問一個目前文件裡沒有的主題

目前 `sample_docs/` 只有 `overview.md`，沒有任何退費相關內容。先問：

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"refund window thirty days"}'
```

真實輸出：

```json
{"answer":"Echo answer. Retrieved context:\nNo matching docs.","sources":[]}
```

`sources` 是空的 —— 因為沒有任何文件含這些關鍵字。這是我們等下要改變的「之前」狀態。

### 動作：新增一份文件

在 `sample_docs/` 新增 `refund-policy.md`，內容：

```markdown
# Refund Policy

Customers may request a refund within a thirty day window after purchase.
Approved refunds are returned to the original payment method.
```

### 重新 ingest

關鍵：**改完文件一定要重新 ingest**，否則 SQLite 裡還是舊的內容。

```bash
python -m app.ingest sample_docs
```

真實輸出（現在多了一行新檔案）：

```text
ingested sample_docs/overview.md
ingested sample_docs/refund-policy.md
```

`ingest.py` 用 `insert or replace`，所以舊檔不會重複、新檔會被加進去。

### After：問同一個問題

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"refund window thirty days"}'
```

真實輸出：

```json
{
  "answer": "Echo answer. Retrieved context:\n[sample_docs/refund-policy.md]\n# Refund Policy\n\nCustomers may request a refund within a thirty day window after purchase.\nApproved refunds are returned to the original payment method.\n",
  "sources": [
    {
      "score": 5,
      "path": "sample_docs/refund-policy.md",
      "snippet": "# Refund Policy\n\nCustomers may request a refund within a thirty day window after purchase.\nApproved refunds are returned to the original payment method.\n"
    }
  ]
}
```

差別很清楚：同一個問題，`sources` 從 `[]` 變成命中 `sample_docs/refund-policy.md`，`score` 是 5（query 裡 `refund` / `window` / `thirty` / `day(s)` 等關鍵字計次的總和）。**這就是「加文件 → 重新 ingest → 被檢索到」的完整證明。** 你自己的 SOP / FAQ / 產品文件也是一樣流程。

> 提醒：這個 starter 的檢索是「關鍵字 / 子字串計次」（看 `app/search.py`），不是語意檢索。所以「退費」這個中文詞不會自動對應到英文 `refund`，同義詞、換句話說也命中不到。這是個誠實的 keyword retrieval baseline，要升級成語意檢索請看本文最後的「升級路徑」。

## 第二部分：從 echo 換成真實的 HTTP LLM

目前 `answer` 開頭都是 `Echo answer.`，因為 `AI_PROVIDER=echo`，`app/ai.py` 只是把檢索 context 原樣回傳、沒呼叫任何模型。要讓模型「根據 sources 回答」，改 `.env`。

### 改之前（`.env`）

```env
AI_PROVIDER=echo
HTTP_LLM_ENDPOINT=https://api.openai.com/v1/chat/completions
HTTP_LLM_API_KEY=
MODEL_NAME=gpt-4o-mini
```

### 改成這樣

```env
AI_PROVIDER=http
HTTP_LLM_ENDPOINT=https://api.openai.com/v1/chat/completions
HTTP_LLM_API_KEY=sk-你的金鑰
MODEL_NAME=gpt-4o-mini
```

`app/ai.py` 的邏輯是：只要 `AI_PROVIDER` 不是 `echo`，就會用 `httpx` 對 `HTTP_LLM_ENDPOINT` 發一個 OpenAI 相容的 chat completions 請求，把檢索到的片段塞進 system / user prompt，再回傳 `choices[0].message.content`。

endpoint 不限 OpenAI——任何 OpenAI 相容介面都行（自架 vLLM、Ollama 的 OpenAI 相容層、Groq、Together 等），改 `HTTP_LLM_ENDPOINT` 與 `MODEL_NAME` 即可。

> 這一步需要你自己的金鑰才能真的拿到模型回應，所以這裡不貼造假的 LLM 回應。**設好你的 `HTTP_LLM_API_KEY` 後**，重啟 `uvicorn`，再打同一個 `/ask`，你會看到 `answer` 不再是 `Echo answer....`，而是模型根據 `sources` 寫出來的自然語言回答；`sources` 欄位仍然照舊回傳，方便你核對答案出處。
>
> 如果金鑰沒設好或無效，`app/ai.py` 會在 `r.raise_for_status()` 丟出例外，`/ask` 回 500。常見錯誤訊息與排查見 `05-common-pitfalls.md`。

## 動手練習：在 /ask 回應多加一個 source_count 欄位

目標：讓 `/ask` 除了 `answer` / `sources`，再回一個「命中幾份文件」的數字，前端就不用自己算 `sources.length`。這個練習我實際做過、驗證有效，下面是真實結果。

### 改 `app/main.py`

改之前：

```python
@app.post("/ask")
async def ask(req:AskRequest):
    docs=search_docs(req.question); return {"answer":await answer(req.question,docs),"sources":docs}
```

改成（在回傳的 dict 多一個 `source_count`）：

```python
@app.post("/ask")
async def ask(req:AskRequest):
    docs=search_docs(req.question); return {"answer":await answer(req.question,docs),"sources":docs,"source_count":len(docs)}
```

存檔。如果你 uvicorn 是用 `--reload` 起的，它會自動重載；沒有的話請 Ctrl+C 重啟。

### 驗證（真實輸出）

有命中的問題：

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"refund window thirty days"}'
```

```json
{"answer":"Echo answer. Retrieved context:\n[sample_docs/refund-policy.md]\n# Refund Policy\n\nCustomers may request a refund within a thirty day window after purchase.\nApproved refunds are returned to the original payment method.\n","sources":[{"score":5,"path":"sample_docs/refund-policy.md","snippet":"# Refund Policy\n\nCustomers may request a refund within a thirty day window after purchase.\nApproved refunds are returned to the original payment method.\n"}],"source_count":1}
```

沒命中的問題：

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"zzz unrelated"}'
```

```json
{"answer":"Echo answer. Retrieved context:\nNo matching docs.","sources":[],"source_count":0}
```

成功的話你會看到：回應尾巴多了 `"source_count":1`（命中一份）和 `"source_count":0`（沒命中）。一個三個字的修改就讓 API 多回一個有用的欄位——這就是這個 starter 刻意保持小的好處：你看得懂，就改得動。

## 升級路徑（做完上面再想這些）

- 檢索：keyword 計次 → chunking（把長文切段）→ embedding 向量檢索 → hybrid（關鍵字 + 向量）。這是「baseline → RAG」真正的那一段。
- 中文 / 同義詞：keyword baseline 不處理同義詞與跨語言，要嘛在 ingest 時做正規化，要嘛直接上 embedding。
- 權限：目前任何人打 `/ask` 都能讀全部文件；正式版要加登入與依部門 / 文件分群的權限。
- 資料治理：`insert or replace` 不處理「刪除」與「版本」，正式版要補。

想把這些落地到你公司的真實情境，可看 `06-customize-for-your-use-case.md` 與 `07-workshop-and-consulting.md`。
