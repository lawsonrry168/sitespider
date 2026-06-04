# 範例設定檔

| 檔案 | 站點 | 模式 | GSC | 用途 |
|------|------|------|-----|------|
| `123deal-sitespider.json` | 123deal.com.hk | HTTP | **關閉** | 顧問稽核（無客戶 Search Console） |
| `allurebeauty-sitespider.json` | Allure | HTTP | 可選 | 靜態爬取 |
| `allurebeauty-js-sitespider.json` | Allure | HTTP + **JS** | 可選 | Webflow / 動態站 |

## 使用

```bash
sitespider --config examples/123deal-sitespider.json -o reports/123deal-audit
sitespider package reports/123deal-audit
```

Web 控制台：`sitespider --ui` → 選範例 → 載入範例。

內建**範例報告**（`/demo`）來自 `reports/123deal-smoke/`，重新產生：

```bash
./scripts/regen-demo-report.sh
```

## GSC

僅在**你擁有**該站 Search Console 資源時，於 JSON 加入：

```json
"gsc": { "site_url": "https://example.com/", "inspect_max": 10 }
```

見 `docs/GSC-RICH-RESULTS.md`。
