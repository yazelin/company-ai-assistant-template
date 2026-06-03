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
