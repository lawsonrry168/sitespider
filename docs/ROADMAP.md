# SiteSpider 產品路線圖與進度

最後更新：2026-06（程式標記 **v1.24.0**）。

## 總體進度（顧問交付視角）

| 模組 | 完成度 | 說明 |
|------|--------|------|
| 核心爬蟲（HTTP + robots + sitemap） | **95%** | 並行、排除路徑、canonical 修復 |
| JS 渲染（Playwright） | **90%** | Allure 類 Webflow 站已驗證 |
| SF 風格 CSV 匯出 | **~85%** | 主要分頁已對齊 `docs/SF-PARITY.md` |
| 稽核與 Issues | **90%** | 錨文字、圖片、hreflang、重複內容等 |
| 報告 UI（index / dashboard / inspector） | **90%** | Washi Indigo + report-polish 交付導覽 |
| 商業優先級（Priority + 7 日排程） | **90%** | Money Page 加權、`priority_summary.md` |
| GEO（geo.csv、llms 檢查） | **80%** | 分數與 llms.txt HTTP 檢查 |
| 顧問交付（REPORT-zh + ZIP） | **95%** | ZIP 含 `README-客戶.txt`、交付清單 API |
| Web 控制台（`sitespider --ui`） | **95%** | 比對、排程 wizard、toast、方案 gating |
| SaaS / Stripe | **85%** | 方案防篡改、伺服器端 branding、多站儀表板 |
| GSC Rich Results API | **70%** | 可選；需客戶 Search Console 授權 |
| 與 SF 桌面完全等價 | **~50%** | 無即時 SERP 抓取 |

**一句話**：已可作為 **Screaming Frog 的 CLI/顧問替代品（站內爬取 + 報告 + 優先順序）**；SaaS 與 Agency 多站儀表板已落地。

---

## v1.24 新增（2026-06）

### SaaS 與安全
- [x] **方案防篡改**：`plan_resolve.py` — Stripe / API Key / tenants.json 存在時忽略 client `plan_id`
- [x] **白標 gating**：Starter `branding_lite`（署名）、Agency `white_label`（完整品牌）
- [x] **伺服器端 branding**：`POST/GET /api/branding` + `.sitespider/branding.json`

### 控制台 UX
- [x] **Toast / inline banner** 取代 `alert()`（dashboard、pricing、admin、workspace）
- [x] **歷史任務比對**：`POST /api/compare` → `compare-report.html`
- [x] **交付清單**：`GET /api/job/{id}/delivery-checklist`
- [x] **排程 wizard**：`GET /api/schedule/wizard` + 側欄複製 cron
- [x] **Agency 多站儀表板**：`/sites` + `/api/sites-dashboard`

### 方案差異化
- [x] **Starter**：每月 1 次 AI 文案 + 報告署名（`branding_lite`）

---

## 版本與 Git 狀態

| 項目 | 狀態 |
|------|------|
| 程式版本 | **1.24.0**（`pyproject.toml`） |
| 待辦 | 即時 SERP、Playwright E2E、index 離線 Chart 內嵌 |

---

## Phase 3（建議下一步）

### P3-A 品質
- [ ] Playwright E2E：dashboard 爬取 smoke
- [ ] analytics_dashboard 內嵌 Chart.js（離線交付）

### P3-B SF 進階（低優先）
- [ ] 即時 SERP 排名抓取
- [ ] Gephi 匯出 UI 入口

### P3-C 協作
- [ ] 報告內嵌 compare diff 區塊
- [ ] AI polish 寫回 REPORT MD 閉環

---

## 模組架構（維護用）

```
sitespider/
  plan_resolve.py       # 方案解析（防篡改）
  tenant_branding.py    # 伺服器端白標
  schedule_wizard.py    # cron 指令產生
  sites_dashboard.py    # Agency 多站彙整
  server.py             # Web 控制台 API
  ui/dashboard.html     # 爬取中心
  ui/sites.html         # 多站儀表板
```
