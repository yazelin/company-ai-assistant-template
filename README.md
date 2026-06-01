![Brand banner](assets/banner.svg)

# Company AI Assistant Template

Build an internal document Q&A assistant before adding vector DB complexity.

## 繁中定位

**企業內部 AI 助理模板** 面向台灣繁中受眾。

- 主要受眾：適合想先驗證內部文件問答、SOP 查詢、知識庫助理的中小企業與工程團隊。
- 核心承諾：先用 SQLite + keyword retrieval 做出可展示的內部文件 AI 助理，再逐步升級成 RAG。
- CTA 頁：https://yazelin.github.io/company-ai-assistant-template/



## 公開教學文件

這個 repo 的教學內容直接公開，讓你可以先自己照著跑；如果需要手把手 debug、改成你的公司或個人場景，再考慮工作坊或顧問協助。

- 網頁版教學：https://yazelin.github.io/company-ai-assistant-template/tutorial.html
- Markdown 教學：[`docs/`](docs/)
- 快速開始：[`docs/01-quickstart.md`](docs/01-quickstart.md)
- 常見踩雷：[`docs/05-common-pitfalls.md`](docs/05-common-pitfalls.md)

## Who this is for

Small teams and companies that want a private AI knowledge assistant.

## Features

- FastAPI /ask endpoint
- SQLite document index
- Keyword retrieval baseline
- Provider adapter ready for LLM APIs

## Quick start

```bash
git clone https://github.com/yazelin/company-ai-assistant-template.git
cd company-ai-assistant-template
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # if present
```

See the source files and `.env.example` for the minimal runnable path.

## Learn / get help

This repo is also a CTA page for workshops and consulting:

- GitHub Pages: https://yazelin.github.io/company-ai-assistant-template/
- Contact: yaze.lin.j303@gmail.com

## License

MIT


## Brand / CTA design

- Landing page: https://yazelin.github.io/company-ai-assistant-template/
- CI spec: [DESIGN.md](DESIGN.md)
- Banner: [assets/banner.svg](assets/banner.svg)
- Logo: [assets/logo.svg](assets/logo.svg)
