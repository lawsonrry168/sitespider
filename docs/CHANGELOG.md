# Changelog

## 1.24.0

### 控制台與設定

- **三步控制台**：站點 → 執行 → 交付；側欄即時監控與任務歷史
- **設定獨立頁**：`/workspace`（租戶／API）、`/ai`（潤飾）、`/branding`（白標）；`console-store.js` 單一 localStorage
- **共用頂欄**：`topnav.js`（控制台、工作區、白標、AI、訂閱、示範、管理）
- **Hidden 設定欄**：控制台僅保留 JS 用 DOM，不再露出表單列

### 交付與示範

- **Markdown 預覽**：`REPORT-zh.md` 等以 HTML 渲染，不再顯示原始 MD
- **交付導覽 GUI**：`REPORT-zh.html`（健康分、交付卡片、檔案對照）
- **示範** `/demo`、`GET /api/demo`、`/reports/demo/` 別名
- **Checkout 成功頁**：訂閱 vs AI 加購（`?ai_bonus=1`）
- **管理後台**：`POST /api/admin/tenant/{id}/plan` 調整方案

### 設計（Washi Indigo）

- **主題**：藍染靛底 + 若竹綠 `#6ec9a0` + 和紙淺色；取代 Obsidian Signal 螢光綠
- **統一商標**：`brand-mark.svg`（藍染方塊＋八足節點蜘蛛）→ 頂欄 / favicon / 匯出儀表板
- **維護腳本**：`scripts/sync-brand-assets.py`、`scripts/sync-console-head.py --fix`
- **24/27" 字級**：`comfort-display.css`（根字級 16→17→18px）
- **文件**：`docs/DESIGN-SYSTEM.md`、`sitespider/ui/README.md`

## 1.23.0

- **管理後台**：租戶列表顯示 AI 用量／加購；`POST /api/admin/tenant/{id}/ai-bonus` 手動發放
- **Stripe AI 加購**：`STRIPE_PRICE_AI_BONUS` 一次性 Checkout；Webhook 累加 `ai_polish_bonus`
- **控制台 / 定價頁**：Pro+ 用戶可點「加購 AI 潤飾」

## 1.22.0

- **控制台**：localStorage 記憶租戶 ID / 方案；切換方案自動套用單次頁數上限並提示
- **示範報告**：`GET /api/demo`、`/reports/demo/` 別名至 `reports/123deal-smoke/`；側欄「預覽示範報告」
- **CLI**：`sitespider share-report REPORT_DIR` 建立客戶 Portal 連結
- **AI 加購**：`ai_polish_bonus` 計量欄位、`add_ai_polish_bonus()`；用量 API 回傳有效 AI 額度
- **客戶 Portal**：manifest 含 `expires_at`；入口頁顯示連結到期日

## 1.21.0

- **設計系統**：`tokens.css` + `shell.css`；控制台三步流程（站點 → 執行 → 交付）、sidebar、健康分環形圖
- **分層匯出**：Fast（秒級可交付）→ Standard / Pro 背景匯出；UI 支援 `exporting` 狀態預覽 REPORT-zh
- **方案 / 管理 / 結帳成功** 頁面統一 topbar 與 design tokens；`docs/DESIGN-SYSTEM.md`
- **Obsidian Signal 主題**：單一 Signal Green 品牌色、Outfit 標題字、實心 Obsidian 表面、`theme.css` 視覺層
- **交付 HTML 統一主題**：`index.html`、`delivery-summary.html`、`issue_heatmap.html`、`inspector.html`、內鏈圖（D3 / 簡易 / WebGL）內嵌 Obsidian Signal CSS（`report_theme.load_ui_css`）；`/ui/*.css` 開發預覽加 `Cache-Control: no-cache`
- **控制台**：Fast 層完成後可自動開啟 `REPORT-zh.md`（進階選項，localStorage 記憶）
- **SEO / GEO 規則型簡報**：`seo-briefs.html` / `.md` / `.json`（Standard 匯出，無 API）
- **AI 潤飾（多平台）**：13 個平台完整模型清單（2026-05 更新：GPT-5.4、Claude Opus 4.8、Gemini 3.5、DeepSeek V4、Kimi K2.6 等）；控制台下拉選平台與模型
- **Inspector**：執行時載入 `ai-page-copy.json` / `ai-faq.json`，一鍵複製 Title / Meta / FAQ
- **URL 預檢**：起始 URL blur 時 `GET /api/validate-url` 顯示連線狀態
- **方案 gating**：`ai_polish` 限 Pro / Agency；Starter 控制台 AI 按鈕與交付連結會停用並提示升級
- **Free 方案**：50 頁 / 2 次爬取 / 月、客戶 Portal；本機預設 `SITESPIDER_DEFAULT_PLAN=free`
- **AI 用量**：Pro 15 次/月、Agency 60 次/月；`ai_polishes` 計量
- **客戶 Portal**：`/portal/{token}` 只讀分享；控制台「客戶分享連結」

## 1.20.0

- **Checkout 後自動 Email**：Webhook 開通時寄送 API Key + 使用說明（需 SMTP）
- **Stripe Customer Portal**：`POST /api/billing/portal`（控制台 / 方案頁「管理訂閱」）
- 管理後台：**重寄開通信**（輪替 Key 並寄信）

## 1.19.0

- **Stripe Checkout**：`/pricing` 一鍵訂閱、`POST /api/billing/checkout`
- 付款成功 Webhook 自動發放 **API Key**（`.sitespider/api-keys.json`）
- **管理後台** `/admin`：租戶列表、用量、輪替 Key（`SITESPIDER_ADMIN_KEY`）

## 1.18.0

- **訂閱 SaaS**：Starter / Pro / Agency 方案、用量配額、API Key 多租戶
- **Stripe Webhook** → 租戶方案同步（`billing_stripe.py`）
- **SERP 排名**：`serp_rank.csv`（SerpAPI，`SERPAPI_KEY`）
- **WebGL 內鏈圖**、**GEXF / GraphML**（Gephi）
- **通知**：Slack / Webhook / SMTP
- **Docker**、`/pricing`、 `GET /api/plans`、`GET /api/usage`

## 1.17.0

- **控制台**：任務歷史、localStorage 記住設定、煙霧/全站預設、白標欄位、自訂擷取勾選
- **交付**：`issue_heatmap.html`、`delivery-summary.html`、可選 `delivery-summary.pdf`（`sitespider[pdf]`）
- **CLI**：`sitespider schedule` 排程爬取+比對、`sitespider multi-compare`
- 每次爬取存 `crawl-config.snapshot.json`；修復 `/api/job` 不再回傳巨大 JSON

## 1.16.0

- **Phase 2**：ZIP 內附 `README-客戶.txt`；`sitespider multi-compare` 多站儀表板；`compare --changed-urls-only` 增量比對
- **SF 進階（部分）**：`serp_snippets.csv`（標題／描述像素寬度）；`link_graph_full.html`（最多 500 節點）；可選 Hunspell（`HUNSPELL_DICT`）
- **Web 控制台**（`sitespider --ui`）：設定檔上傳／範例載入、GSC 開關、交付檔案一鍵開啟、本機報告路徑複製
- 每次爬取產生 **`REPORT-zh.md`** 交付導覽（無 GSC 流程說明、檔案對照、閱讀順序）
- `docs/DELIVERY-WORKFLOW.md` 顧問交付流程
- 拼寫：`pip install "sitespider[spelling]"` 啟用 **pyspellchecker**（`spelling.csv` 含 `Engine` 欄）
- GSC：**Search Console URL Inspection API** → `rich_results_gsc.csv`（`--gsc-inspect-max`，需 `sitespider[gsc]`）
- 內鏈圖：`link_graph.html` 改為 **D3 互動**力導向；`link_graph_simple.html` 保留簡易 SVG

## 1.15.0

- SF 對齊：`h3.csv`、`outlinks.csv`、`robots.csv`、`duplicate_content.csv`、`javascript.csv`
- `rich_results.csv`：依 JSON-LD @type 與 URL 路徑的 Rich Results 啟發式檢查

## 1.14.0

- `priority_summary.md`：7 日執行排程（Day 1–7，依問題分佈與 Money Page）
- 匯出 `ngrams.csv`（2/3-gram，title / H1 / meta）
- 匯出 `spelling.csv`（英文拼寫啟發式標記，無外部字典）
- `link_graph.html`：Top 頁內鏈視覺化（Link Score 節點大小）
- v1.13.x 累積：GEO、`geo.csv`、`actions.csv`、商業導向 `priority_pages.csv`

## 1.13.1

- 修正 Webflow/CMS canonical：`www.example.com/path`（無 `https://`）不再被錯誤合併成雙重網域路徑
- Allure JS 範例：`domcontentloaded`、`exclude_paths: ["/404"]`

## 1.13.0

- 圖片 `width` / `height` / `loading` 解析與 `images.csv` 欄位
- 稽核：`image_missing_dimensions`、`image_oversized`
- 匯出：`orphan_pages.csv`、`broken_external.csv`
- Web 控制台：完整問題標籤（`ISSUE_LABELS`）、Top 20 問題摘要

## 1.12.0

- 錨文字稽核（重複、空白、非描述性）與 `anchor_text.csv`
- 爬取後產生 `sitemap_generated.xml`
- URL 檢視器：內鏈來源表格（錨文字、Follow、版位）

## 1.11.0

- `nofollow` 與 Link Position（Navigation / Footer / …）
- Link Score 僅計 follow 內鏈
- `all_inlinks.csv` 增 Follow、Link Position 欄位

## 1.10.0

- 內部 PageRank（Link Score）、`all_inlinks.csv`
- `inspector.html` 單頁檢視器
- Web 控制台：JS 渲染、設定檔、排除路徑
