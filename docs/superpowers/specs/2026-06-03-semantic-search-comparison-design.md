# Design: company-ai-assistant Part 2 — 語意檢索升級對照組

- **Date:** 2026-06-03
- **Repo:** `company-ai-assistant-template`
- **Status:** Approved design (pending written-spec review)

## 1. 目標與動機

前半段教學的檢索是**誠實的關鍵字 baseline**(`app/search.py`:把查詢切詞、在每份文件數子字串出現次數、排序)。repo 自己的文件明說「這不是語意檢索」並列出升級路徑。

後半段新增一段**獨立課程**:用 **fastembed**(本地 ONNX embedding)+ numpy cosine 做**真正的語意檢索**當對照組,讓學員親眼看到「關鍵字找不到的改寫問句,語意檢索找得到」。這是 mcp / linebot 已驗證成功的「baseline → 升級」教學模式套到檢索場景。

非目標:不動 AI 回答層(`app/ai.py:answer`);不引入向量資料庫服務;不做 hybrid;不引 pytest。

## 2. 與前兩個 repo 的差異:這是「對照」不是「對等」

mcp / linebot 的 Part 2 證明兩版**行為相同**(parity)。這裡相反 —— 兩種檢索**本來就該不一樣**,這正是重點。所以測的是 **contrast**:
- 直接關鍵字命中的查詢(如「退費」)→ 兩版都找到同一份文件(共識,證明語意版沒退化基本能力)。
- **改寫 / 同義**的查詢(如「我想把錢拿回來」)→ 關鍵字 **0 筆**,語意 **找得到**(對照,證明升級的價值)。

## 3. 已驗證的技術事實(實測)

- **fastembed 0.8.0**;多語模型 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`(384 維,支援中文)。
- 實測對照(sample 文件 refund/hours/shipping,查詢「我想把錢拿回來」):
  - 關鍵字(現有 `search_docs` 邏輯):三份皆 0 分 → **0 筆命中**。
  - 語意(fastembed + numpy cosine):`refund.md` 0.424(top)> shipping 0.215 > hours 0.075 → **正確命中退費文件**。
  - **deterministic: True**(同輸入同向量)→ CI 可重現。
- fastembed 對該模型會印 mean-pooling 的 `UserWarning` —— 良性(mean pooling 正是 sentence-transformers paraphrase 模型的正確 pooling);結果分離度清楚,不需 pin 舊版。
- 模型約 118MB(5 檔)。首次下載慢(HF 限速),CI 需 cache fastembed 模型目錄。

## 4. 架構(兩軌 + 共用下游)

| | Part 1（現有） | Part 2（新增） |
|---|---|---|
| 檢索 | `search_docs`:關鍵字子字串計次 | `search_semantic`:fastembed embedding + numpy cosine |
| 介面 | `(query, limit) -> [{score, path, snippet}]` | **同簽章、同輸出形狀** |
| 下游回答 | `app/ai.py:answer(question, docs)` | **共用同一個** `answer` |
| 相依 | base（無第三方檢索相依） | fastembed（optional `semantic` extra） |
| 切換 | 預設 | `SEARCH_BACKEND=semantic` 讓 `/ask` 真的改用語意 |

**同介面是對照乾淨的關鍵**:`search_semantic` 回傳與 `search_docs` 完全相同的形狀,所以 `main.py` 與 `answer()` 不必改邏輯,只是換一個檢索函式。

## 5. 檔案清單

### 程式碼
- **`app/search_semantic.py`(新)**:
  - `_model()`:lazy-load fastembed `TextEmbedding`(模型名常數),快取單例。
  - `index_semantic()`:讀 `documents` 全表,對缺向量的文件 embed 並存進 `embeddings` 表。
  - `search_semantic(query, limit=5) -> [{score, path, snippet}]`:確保已索引 → embed 查詢 → 對所有存好的向量算 cosine → 取 top-k,輸出形狀同 `search_docs`(`score` 為 cosine 相似度)。
- **`app/db.py`(改)**:`conn()` 多建一張 `embeddings(path text primary key, vector text)`(vector 存 JSON 浮點陣列)。
- **`app/main.py`(改)**:讀 `SEARCH_BACKEND`(預設 `keyword`);`semantic` 時 lazy-import `app.search_semantic` 改用之(base 匯入鏈不碰 fastembed)。
- **`pyproject.toml`(改)**:`[project.optional-dependencies] semantic = ["fastembed>=0.8,<0.9"]`;`[tool.uv] package = false` 不變。
- **`uv.lock`（重產）**。

### 測試 / CI
- **`contrast_smoke_test_semantic.py`(新,semantic-only)**:用內建 sample 文件 ingest → 斷言(a)「退費」兩版都命中 refund;(b)「我想把錢拿回來」關鍵字 0 筆、語意 top=refund。非零結束於失敗。
- **`.github/workflows/ci.yml`(新)**:matrix:`keyword`(base,跑既有關鍵字路徑的最小 smoke)/ `semantic`(`--extra semantic`,**cache fastembed model dir**,跑對照測試)。

### 文件
- **`docs/08-semantic-search-upgrade.md`(新)**:關鍵字 vs 語意差異表、裝 extra、index + search 程式碼、對照 demo(關鍵字 0 / 語意命中,真實輸出)、成本(模型 ~118MB、查詢多 ~數十 ms、需先 index)、何時升級、`SEARCH_BACKEND` 切換。
- **`docs/00-overview.md`、`tutorial.html`(含 TOC 補 08)、`README.md`、`index.html`、`DESIGN.md`(改)**:兩軌化;語意檢索從「未來可升級」升格為「內建後半段」。

## 6. 錯誤處理 / 邊界

- `search_semantic` 在無 fastembed(沒裝 extra)時匯入即失敗 —— 這是預期的(僅 `SEARCH_BACKEND=semantic` 或 semantic track 才會匯入)。
- sample 文件量小,numpy cosine 全掃即可;文件量大時的 ANN 留作 docs 的「scale up」說明,不實作。
- `index_semantic` 對已存在向量的文件略過(冪等),重跑不重算。

## 7. 風險與待確認

- **CI 模型下載**:首次 ~118MB 且 HF 可能限速;以 `actions/cache` 快取模型目錄緩解,並給該 step 足夠 timeout。
- **fastembed 版本/模型飄移**:鎖 `>=0.8,<0.9`、固定模型名;contrast 測試當防線;docs 標所用版本(0.8.0)。
- **對照 demo 真實性**:已實機驗證(關鍵字 0 / 語意 refund 0.424 top、deterministic);sample 文件與查詢以驗過的那組為準寫進測試與 docs。
- **base 隔離**:fastembed 只在 `search_semantic` 頂部 import;`main.py` 預設 `keyword` 不觸發,確保 base `uv sync` 不裝 fastembed、關鍵字版可獨立跑。

## 8. 不做（YAGNI）

- 不做 hybrid(關鍵字+語意合併)。
- 不引 pytest(沿用家族 plain-python smoke script)。
- 不動 `app/ai.py` / AI 回答行為。
- 不上 sqlite-vec / 向量 DB(numpy cosine 足夠教學)。
- 不把 Part 1 關鍵字版改掉(保留為對照基準)。
