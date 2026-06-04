# SiteSpider 報告設計方向

SiteSpider 採 **三層報告**，對應不同讀者與用途：

```
  爬取完成
      │
      ├── dashboard.html     ← 分析圖表（簡報 / 客戶第一眼）
      ├── index.html         ← 表格明細（對照 Screaming Frog 分頁）
      ├── SEO-AUDIT-zh.md    ← 繁中文字摘要（Email / 提案附件）
      └── *.csv / .xlsx      ← 資料分析 / SF 比對 / 存檔
```

## 1. 分析圖表層 — `dashboard.html`

**對象**：客戶、PM、非技術 stakeholder  
**風格**：一頁式儀表板 + Chart.js 互動圖

| 區塊 | 圖表 | 用途 |
|------|------|------|
| KPI | 健康分、Indexable %、URL 數 | 30 秒掌握站點狀態 |
| 索引 | Indexability 圓環、Non-Indexable 原因 | 對照 SF Internal |
| 狀態 | HTTP 狀態碼、爬取深度 | 404 / 結構問題 |
| On-Page | 問題 Top 15、Title/Meta 長度、H1、Inlinks、字數 | 內容與連結品質 |

**開啟方式**：

```bash
open reports/allurebeauty/dashboard.html
```

> 圖表需連線載入 Chart.js CDN；離線環境可改看 `index.html` 內建 CSS 長條圖。

## 2. 明細表格層 — `index.html`

**對象**：SEO 專員、開發者  
**風格**：深色 Screaming Frog 式分頁（Internal / Canonicals / Titles / Issues / Response Codes）

適合：逐 URL 排查、複製貼上給 Webflow 管理員。

## 3. 交付與資料層

| 檔案 | 用途 |
|------|------|
| `SEO-AUDIT-zh.md` | 給客戶的繁中說明與修復步驟 |
| `internal.csv` | 與 Screaming Frog 匯出比對 |
| `sitespider diff-csv sf.csv internal.csv` | 差異分析 |
| `crawl-report.json` | CI、compare、自訂腳本 |

## 建議工作流程（以 Allure 為例）

1. 爬取：`sitespider --mode http --url https://www.allurebeauty.com.hk/ -c examples/allurebeauty-sitespider.json -o reports/allurebeauty`
2. **簡報**：開 `dashboard.html` 給客戶看圖表
3. **修復清單**：`issues.csv` + `response_codes.csv`
4. **對照 SF**：匯出 SF Internal → `sitespider diff-csv`
5. **修正後回歸**：`sitespider compare before.json after/crawl-report.json`

## 未來可擴充

- [ ] 兩次爬取並排趨勢圖（compare 資料餵入 dashboard）
- [ ] PDF 匯出（print-friendly CSS）
- [ ] Lighthouse 雷達圖（已有資料時）
- [ ] 自訂品牌色 / logo（設定檔 `report.brand`）
