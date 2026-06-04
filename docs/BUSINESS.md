# SiteSpider 商業定位與產品策略

## 定位

**Client-Ready SEO / GEO Delivery for Agencies**

不是通用大規模反封鎖爬蟲平台（Bright Data / Oxylabs），也不是任意 URL → Markdown 的 LLM 基建（Firecrawl）。

SiteSpider = **Screaming Frog 顧問交付版 + 多平台 AI 文案 + 輕量 SaaS**。

## 方案（2026-05）

| 方案 | 月費 | 單次頁數 | 每月爬取 | AI 文案/月 |
|------|------|----------|----------|------------|
| **Free** | $0 | 50 | 2 | 0 |
| Starter | $49 | 200 | 8 | **1** |
| **Pro** | $149 | 2,000 | 40 | 15 |
| Agency | $399 | 10,000 | 200 | 60 |

- Free：獲客試用，含 **客戶分享 Portal**
- Starter：報告署名 + 每月 1 次 AI 文案試用
- Pro+：完整 AI、SERP、GSC、排程；Agency 含完整白標與多站儀表板

本機未設定 `SITESPIDER_API_KEYS` 時，預設方案為 `SITESPIDER_DEFAULT_PLAN`（預設 `free`）。

## 收入模式（Hybrid）

1. **Freemium + 訂閱** — Free → Stripe 升級 Starter/Pro/Agency  
2. **用量計費** — 爬取次數、頁數上限；AI 按次計量（`ai_polishes` / 月）  
3. **加值** — AI 加購包（Stripe 一次性 `STRIPE_PRICE_AI_BONUS`）、管理後台手動發放、Enterprise SLA  

**刻意不做**：自建 Proxy 池（站內稽核以客戶授權網域為主）。

## 客戶 Portal

顧問在 Step 3 點 **「客戶分享連結」** → `POST /api/job/{id}/share` → 客戶開啟 `/portal/{token}`（只讀 HTML/MD，30 天有效）。

## 競爭差異

| 對手 | SiteSpider 策略 |
|------|------------------|
| Screaming Frog | 自動化交付、中文 REPORT、AI、無桌面授權 |
| Firecrawl | 垂直 SEO 報告 + llms.txt，非通用 crawl |
| Apify | SEO 產業 Preset，非通用 Actor 市場 |

## 相關文件

- [SAAS-SUBSCRIPTION.md](SAAS-SUBSCRIPTION.md) — 部署與 Stripe  
- [DESIGN-SYSTEM.md](DESIGN-SYSTEM.md) — Washi Indigo UI  
- [sitespider/ui/README.md](../sitespider/ui/README.md) — 控制台頁與 CSS 對照  
- [ROADMAP.md](ROADMAP.md) — 功能進度  
