# 企業內部 AI 助理模板：常見問題與踩雷清單

下面每一條都是這個 repo 真的會踩到的坑，附上「真實症狀 / 錯誤訊息」和「怎麼修」。錯誤訊息都是本機實際跑出來貼上的。

## 坑 1：忘了先 ingest，查詢永遠是空的

`assistant.db` 不在 repo 裡（被 `.gitignore` 忽略），是你 ingest 時才產生的。沒跑 ingest 就查，`sources` 一定是空陣列。

真實症狀（對一個從沒 ingest 過的 DB 做檢索）：

```text
search result on never-ingested db: []
```

對應到 API 就是：

```json
{"answer":"Echo answer. Retrieved context:\nNo matching docs.","sources":[]}
```

注意：這不會報錯。`app/db.py` 的 `conn()` 會 `create table if not exists`，所以 DB 自動被建出來、只是裡面沒有任何文件。很多人以為「服務有回 200 就 OK」，其實是空庫。

修法：先跑 `python -m app.ingest sample_docs`，確認印出 `ingested ...`，再查。

## 坑 2：改了文件卻沒重新 ingest

`/ask` 讀的是 SQLite，不是直接讀檔案。你在 `sample_docs/` 改了內容、加了新檔，但沒重新 ingest，查到的還是舊資料。

症狀：你明明加了 `refund-policy.md`，問退費相關問題卻還是 `"sources":[]`。

修法：每次動 `sample_docs/` 之後都重跑 `python -m app.ingest sample_docs`（`insert or replace`，重跑安全，不會重複）。

## 坑 3：DATABASE_URL 指到別的路徑，ingest 和查詢用了不同的 DB

`app/db.py` 讀 `DATABASE_URL`（預設 `assistant.db`，相對於你「執行指令時所在的目錄」）。如果你 ingest 時在某個資料夾、起 uvicorn 時在另一個資料夾，或 `.env` 改了 `DATABASE_URL`，兩邊就會操作到不同的 `.db` 檔，於是「明明 ingest 成功了，查還是空的」。

修法：固定在 repo 根目錄執行所有指令；ingest 和 uvicorn 用同一個 `.env` / 同一個 `DATABASE_URL`。

## 坑 4：把 AI_PROVIDER 設成 http 但金鑰沒填

`.env` 改成 `AI_PROVIDER=http` 卻把 `HTTP_LLM_API_KEY` 留空時，`app/ai.py` 會送出 `Authorization: Bearer `（後面空白），httpx 直接擋下來：

真實錯誤：

```text
LocalProtocolError: Illegal header value b'Bearer '
```

`/ask` 會回 500。修法：把 `HTTP_LLM_API_KEY` 填上有效金鑰，或先把 `AI_PROVIDER` 改回 `echo` 排除 LLM 問題。

## 坑 5：金鑰 / endpoint 設錯（401 等）

金鑰填了但無效、或 endpoint 指錯，會在 `r.raise_for_status()` 丟出帶 HTTP 狀態碼的錯誤：

真實錯誤（用一個無效金鑰打 OpenAI）：

```text
HTTPStatusError: Client error '401 Unauthorized' for url 'https://api.openai.com/v1/chat/completions'
```

修法：401 = 金鑰錯或過期；404 / 連線錯誤 = `HTTP_LLM_ENDPOINT` 填錯。先用 `curl` 直接打那個 endpoint 確認金鑰可用，再回來測 `/ask`。

## 坑 6：request body 少欄位（422），不是壞掉

少帶 `question` 欄位時 FastAPI 回 422：

```json
{"detail":[{"type":"missing","loc":["body","question"],"msg":"Field required","input":{}}]}
```

這是正常的輸入驗證。修正 JSON 帶上 `question` 即可。

## 坑 7：以為 echo 就是 AI

`echo` provider 不呼叫任何模型，只把檢索 context 原樣回傳（answer 開頭固定是 `Echo answer.`）。它是用來「單獨驗證檢索」的，不是 LLM 回答。要真的讓模型回答，照 `03-step-by-step.md` 把 provider 換成 `http`。

## Debug 順序（這個 repo 專用）

1. `curl /health` 回 `{"ok":true}` 嗎？沒有的話服務根本沒起來，看 uvicorn 終端機的錯誤。
2. 跑過 `ingest` 了嗎？`ingested ...` 有印出來嗎？`assistant.db` 存在嗎？
3. 有命中的問題 `sources` 非空嗎？空的話多半是坑 1 / 2 / 3。
4. answer 開頭是 `Echo answer.`？那是 echo provider，先確認你要不要的就是這個。
5. 接了 `http` provider 才出錯？把 `AI_PROVIDER` 改回 `echo`，先確認檢索沒問題，再單獨修 LLM 設定。
6. 看完整錯誤訊息（uvicorn 終端機的 traceback），不要只看 `/ask` 回的那一行。

## 問別人前準備

- repo / branch、你用的 Python 版本
- 你實際打的指令（ingest 指令、curl 指令）
- `AI_PROVIDER` 是 echo 還是 http（**不要貼出 API key 本身**）
- uvicorn 終端機的完整錯誤訊息
- 你預期看到什麼、實際看到什麼
