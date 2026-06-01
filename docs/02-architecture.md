# 企業內部 AI 助理模板：架構說明

## 核心檔案

- app/ingest.py：讀取 .md / .txt 並寫入 SQLite documents table
- app/search.py：最小 keyword retrieval baseline
- app/ai.py：把檢索片段組成 context，再交給 echo 或 HTTP LLM
- app/main.py：提供 /ask API
- sample_docs/：示範用內部文件

## 資料流

1. 使用者或 client 發出請求。
2. FastAPI / stdio 入口接收資料。
3. handler 解析訊息與設定。
4. adapter / tool / search 層執行實際工作。
5. 回傳最小可理解的結果。

## 設計原則

- 先讓流程可跑，再做漂亮抽象。
- token 與 secrets 全部放在環境變數。
- 每一層保持可以替換：入口、AI provider、資料來源、部署方式。
- 範例程式刻意保持小，方便你看懂後改成自己的版本。
