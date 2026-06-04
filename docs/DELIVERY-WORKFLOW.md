# 顧問交付流程（無 GSC 授權）

適用：客戶未提供 Search Console、或你無該站 GSC 權限（例如 123deal）。

## 1. 爬取

```bash
sitespider --config examples/123deal-sitespider.json -o reports/client-123deal-YYYYMMDD
```

設定檔**不要**含 `gsc`，或 `inspect_max: 0`。

## 2. 打包交付 ZIP

```bash
sitespider package reports/123deal-audit -o reports/123deal-delivery.zip
```

或在 Web 控制台爬取完成後按 **「下載交付 ZIP」**。

ZIP 內含：`REPORT-zh.md`、`priority_summary.md`、`dashboard.html`、主要 CSV 等。

## 3. 交付包核心檔（給客戶 / 內部）

| 優先 | 檔案 |
|------|------|
| 入口 | `REPORT-zh.md` |
| 簡報用 | `dashboard.html`（瀏覽器開啟） |
| 執行計畫 | `priority_summary.md`（含 7 日排程） |
| 明細 | `index.html` + 必要 CSV |

## 4. 說明用語（避免客戶問 GSC）

- 「本報告為**站內技術與內容稽核**，不依賴 Google 帳號。」
- 「Rich Results 以 `rich_results.csv` 為**程式解析 JSON-LD**；Google 官方判定需客戶開通 Search Console 後另測。」

## 5. 有 GSC 時（可選）

客戶驗證 GSC 並授權你後，設定：

```json
"gsc": { "site_url": "https://example.com/", "inspect_max": 15 }
```

見 `docs/GSC-RICH-RESULTS.md`。

## 6. JS 站（Webflow 等）

```bash
sitespider --config examples/allurebeauty-js-sitespider.json -o reports/client-allure-js
```
