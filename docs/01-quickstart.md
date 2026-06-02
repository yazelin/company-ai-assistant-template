# 企業內部 AI 助理模板：快速開始

這份文件帶你從 clone 到「打 /ask 拿到答案」走完一遍。每一步都附上「實際指令 → 真實輸出 → 成功的話你會看到」。輸出都是本機真的跑出來貼上的。

## 前置需求

- Python 3.10+（本文用 3.12.3 驗證）
- Git
- 可以使用終端機（會用到 `curl`）
- 之後若要接真實 LLM，再準備 OpenAI 相容的 endpoint 與 API key。第一輪用內建 `echo` provider，不需要任何金鑰。

## 這個 starter 在做什麼（一句話）

把 `sample_docs/` 裡的 `.md` / `.txt` 索引進一個 SQLite 檔（`assistant.db`），然後 `POST /ask` 時用「關鍵字計次」找出最相關的片段，組成 context 回給你。

注意：`assistant.db` 沒有放進 repo（已被 `.gitignore` 忽略）。**它是你第一步 ingest 時自己產生的**，所以下面第 5 步如果沒跑，後面查詢一定是空的。

## 步驟 1：安裝

```bash
git clone https://github.com/yazelin/company-ai-assistant-template.git
cd company-ai-assistant-template
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env.example` 預設就是 `AI_PROVIDER=echo`，所以複製過去即可，先不用改。

成功的話你會看到 `pip` 安裝完 fastapi / uvicorn / httpx / python-dotenv，沒有紅色錯誤。

## 步驟 2：把文件索引進 SQLite（這一步會「生出」assistant.db）

```bash
python -m app.ingest sample_docs
```

真實輸出：

```text
ingested sample_docs/overview.md
```

成功的話你會看到：印出 `ingested ...` 一行（每個被收進去的檔案一行），而且資料夾下多出一個 `assistant.db` 檔：

```text
assistant.db  12.0K
```

如果你跳過這一步，後面查詢的 `sources` 會永遠是空的（見 `05-common-pitfalls.md`）。

## 步驟 3：啟動服務

```bash
uvicorn app.main:app --reload --port 8000
```

成功的話終端機會停在這幾行（服務常駐，不會跳回提示字元）：

```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

請另開一個終端機做下面的測試（這個視窗讓它繼續跑）。

## 步驟 4：健康檢查

```bash
curl http://127.0.0.1:8000/health
```

真實輸出：

```json
{"ok":true}
```

## 步驟 5：問一個有命中的問題

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What documents does this assistant index?"}'
```

真實輸出（為了好讀有換行；實際是一行）：

```json
{
  "answer": "Echo answer. Retrieved context:\n[sample_docs/overview.md]\n# Company AI Assistant Template\n\nIndexes internal Markdown/text documents and answers with retrieved context.\n",
  "sources": [
    {
      "score": 2,
      "path": "sample_docs/overview.md",
      "snippet": "# Company AI Assistant Template\n\nIndexes internal Markdown/text documents and answers with retrieved context.\n"
    }
  ]
}
```

成功的話你會看到：`sources` 陣列裡有東西，`path` 指到 `sample_docs/overview.md`，`score` 是命中的關鍵字計次。`answer` 開頭是 `Echo answer.` —— 因為現在是 `echo` provider，它只是把檢索到的 context 原樣回給你，**還沒有真的呼叫 LLM**。這是預期行為。

## 步驟 6：問一個沒命中的問題

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"zzzzzz nonexistent topic"}'
```

真實輸出：

```json
{"answer":"Echo answer. Retrieved context:\nNo matching docs.","sources":[]}
```

成功的話你會看到：`sources` 是空陣列 `[]`，answer 是 `No matching docs.`。代表檢索正常運作、只是這個問題在你目前的文件裡找不到關鍵字。

## 看看錯誤長什麼樣（之後 debug 會用到）

打一個不存在的路徑（404）：

```bash
curl http://127.0.0.1:8000/asdf
```

```json
{"detail":"Not Found"}
```

打 `/ask` 但忘了帶 `question` 欄位（FastAPI 的 422 驗證錯誤）：

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" -d '{}'
```

```json
{"detail":[{"type":"missing","loc":["body","question"],"msg":"Field required","input":{}}]}
```

看到 422 + `"msg":"Field required"` 不是壞掉，是 request body 少了必填欄位。修正 JSON 即可。

## 整體 OK 的判斷標準

跑完上面六步，只要：

- `GET /health` 回 `{"ok":true}`
- `POST /ask` 有命中的問題回得到非空 `sources`
- 沒命中的問題回 `"sources":[]`（而不是整個 500）

就代表這個 starter 在你機器上完整跑通了。下一步請看 `03-step-by-step.md`，把你自己的文件加進去並換成真實 LLM。
