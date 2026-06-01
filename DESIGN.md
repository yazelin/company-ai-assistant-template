# 企業內部 AI 助理模板 CI Design

> English name: Company AI Assistant Template

## 定位

**主要受眾：** 適合想先驗證內部文件問答、SOP 查詢、知識庫助理的中小企業與工程團隊。  
**核心承諾：** 先用 SQLite + keyword retrieval 做出可展示的內部文件 AI 助理，再逐步升級成 RAG。  
**痛點切入：** 先不要一開始就導入複雜向量資料庫；先用最小成本證明「公司資料接 AI」真的有用。  
**類別提示：** Docs / retrieval / ask API

## 視覺識別

- **主色：** `#f59e0b`
- **輔色：** `#14b8a6`
- **背景：** `#17120a`
- **語言策略：** 繁體中文為主，英文產品名作為輔助與 SEO。
- **風格：** dark developer-tool landing page、技術網格、明確產品 glyph、高對比 CTA。

## Landing Page CTA

主要 CTA：**取得企業 AI 助理導入清單**  
表單會帶上 repo 名稱 `company-ai-assistant-template` 與語言 `zh-Hant-TW`，方便後續分眾。

## 功能賣點

- SQLite 文件索引，適合快速 PoC
- /ask API 會回傳 answer 與 sources
- sample_docs 可直接展示內部文件問答流程
- 適合顧問訪談後快速做企業 AI PoC

## Assets

- `assets/banner.svg`：README / Open Graph / hero banner
- `assets/logo.svg`：square product mark
- `index.html`：繁中 GitHub Pages CTA landing page
