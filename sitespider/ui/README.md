# SiteSpider UI

## 控制台頁（`sitespider --ui`）

| 路徑 | 檔案 | 對外名稱 |
|------|------|------|
| `/` | `dashboard.html` | 爬取中心 |
| `/workspace` | `workspace.html` | 帳號與方案 |
| `/branding` | `branding.html` | 報告品牌 |
| `/ai` | `ai.html` | AI 文案 |
| `/pricing` | `pricing.html` | 方案價格 |
| `/demo` | `demo.html` | 範例報告 |
| `/admin` | `admin.html` | 營運後台 |
| `/checkout/success` | `checkout_success.html` | 付款成功 |
| `/about` | `about.html` | 關於我們 |
| `/contact` | `contact.html` | 聯絡我們 |

共用腳本：`console-store.js`（localStorage）、`topnav.js`（頂欄）、`ai-settings.js`（AI 下拉）。

`<head>` 標準片段見 **`head-console.snippet.html`**。

維護商標與 head：

```bash
python scripts/sync-brand-assets.py      # brand-mark → favicon.svg
python scripts/sync-console-head.py      # 檢查 8 個控制台頁
python scripts/sync-console-head.py --fix  # 寫入標準 favicon / theme-color
```

## 設計系統（Washi Indigo）

| 檔案 | 角色 |
|------|------|
| `tokens.css` | 色票、字體、間距 token |
| `shell.css` | 版面、元件、按鈕、表單 |
| `theme.css` | 品牌視覺層（aurora、pipeline、卡片） |
| `comfort-display.css` | 24/27" 根字級 |
| `settings-page.css` | 設定獨立頁版面 |
| `brand-mark.svg` | **商標主檔**（頂欄、與 favicon 同圖） |
| `favicon.svg` / `apple-touch-icon.svg` | 分頁／主畫面圖示（與 brand-mark 同設計） |

詳見 [docs/DESIGN-SYSTEM.md](../../docs/DESIGN-SYSTEM.md)。

## 匯出報告（內嵌 CSS，非單獨 HTTP）

| 檔案 | 用途 |
|------|------|
| `report-pages.css` | delivery、heatmap、inspector、SEO briefs |
| `index-report.css` | Screaming Frog 風格 `index.html` |
| `analytics-theme.css` | `dashboard.html` 分析圖表匯出 |
| `link-graph.css` | 內鏈圖 |

由 `sitespider.report_theme.load_ui_css()` 讀取並內嵌至 HTML。

## 客戶 Portal

`portal.html` — 精簡 head（tokens + shell），無完整控制台 topnav。
