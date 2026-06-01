# 企業內部 AI 助理模板：快速開始

## 前置需求

- Python 3.10+
- Git
- 可以使用終端機
- 如果要接真實 AI 或平台 token，請準備對應帳號與 API key。

## 最短路徑

1. 把 Markdown / txt 文件放進 sample_docs 或指定資料夾
2. 執行 ingest 匯入 SQLite
3. 啟動 FastAPI /ask endpoint
4. 先用 echo provider 看檢索結果，再接 LLM

## 安裝與啟動

```bash
git clone https://github.com/yazelin/company-ai-assistant-template.git
cd company-ai-assistant-template
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.ingest sample_docs
uvicorn app.main:app --reload --port 8000
```

## 健康檢查

```bash
curl http://127.0.0.1:8000/health
```

## 常用入口

- GET /health：健康檢查
- POST /ask：送出 question，回傳 answer 與 sources

## 第一次成功的標準

- 服務能啟動
- 基本 endpoint 有回應
- 範例流程能跑通
- 秘密 token 沒有 commit 到 GitHub
