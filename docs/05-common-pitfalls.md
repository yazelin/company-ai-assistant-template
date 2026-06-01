# 企業內部 AI 助理模板：常見問題與踩雷清單

## 常見坑

- 不要一開始就導入複雜向量資料庫；先確認文件品質與問題場景。
- keyword retrieval 對同義詞較弱，這是 baseline，不是最終 RAG。
- 內部文件可能含敏感資訊，接外部 LLM 前要先盤點資料分類。
- ingest 目前是 insert or replace，但正式版要處理刪除、版本與權限。
- 回答一定要回傳 sources，方便使用者判斷可信度。

## Debug 順序

1. 先確認服務有沒有啟動。
2. 再確認 endpoint / webhook URL 是否正確。
3. 檢查環境變數是否有載入。
4. 用 echo / fake provider 排除 AI 服務問題。
5. 查看完整錯誤訊息，不要只看最後一行。
6. 把問題縮到最小可重現案例。

## 問別人前準備

- repo / branch
- 啟動指令
- 完整錯誤訊息
- 你已經檢查過哪些設定
- secret 請遮掉，不要直接貼 token
