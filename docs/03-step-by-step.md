# 企業內部 AI 助理模板：完整操作流程

## 步驟

1. 先用 sample_docs 跑一次 ingest，建立 assistant.db。
2. 呼叫 /ask，確認 sources 有出現相關文件。
3. 把自己的 SOP / FAQ / 產品文件放進資料夾後重新 ingest。
4. 先用 AI_PROVIDER=echo 檢查檢索品質。
5. 再設定 HTTP_LLM_ENDPOINT 與 API key，讓模型根據 sources 回答。
6. 整理哪些問題答不好，決定是否升級 chunking、向量搜尋、權限控管。

## 建議紀錄

- 你使用的 Python 版本
- 啟動指令
- `.env` 裡有哪些 key 已設定；不要貼出 secret 值
- webhook / endpoint URL
- 錯誤訊息完整內容
- 你預期發生什麼、實際發生什麼

## 下一個里程碑

完成最小流程後，不要急著加功能。先找一個真實情境，讓這個 starter 解決一個很小但明確的問題。
