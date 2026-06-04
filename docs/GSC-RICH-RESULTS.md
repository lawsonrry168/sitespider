# Google Search Console — Rich Results API

SiteSpider 使用 **Search Console URL Inspection API** 取得與 SF「Rich Results」類似的 Google 端驗證結果。

## 重要：不是 AI Studio API Key

- **Google AI Studio / Gemini API Key** 無法用於此功能。
- 需要 **Search Console 已驗證網站** + **OAuth 服務帳戶** 或 **Application Default Credentials**。

## 安裝

```bash
pip install "sitespider[gsc]"
```

## 憑證設定（二擇一）

### A. OAuth 用戶端（你目前的 `client_secret_*.json`）

1. GCP → 憑證 → **OAuth 用戶端 ID** → 類型「電腦版應用程式」或「桌面」。
2. 下載 JSON，放在本機（**勿 commit**），例如 iCloud 或 `.secrets/`。
3. 在專案目錄：

```bash
source scripts/gsc-env.sh   # 已指向你的 client_secret 路徑
pip install "sitespider[gsc]"
```

4. **第一次**執行含 `--gsc-inspect-max` 的爬取時會開瀏覽器，用**有 GSC 權限的 Google 帳號**登入授權。
5. Token 快取於 `~/.config/sitespider/gsc-oauth-token.json`（可改 `GSC_OAUTH_TOKEN_PATH`）。

### B. 服務帳戶 JSON

1. 建立服務帳戶並下載 JSON。
2. 在 Search Console → 使用者與權限 → 加入服務帳戶 **email**。
3. `export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"`

## 設定檔

```json
{
  "site_url": "https://www.example.com/",
  "mode": "http",
  "gsc": {
    "site_url": "https://www.example.com/",
    "inspect_max": 15
  }
}
```

`gsc.site_url` 須與 GSC 資源一致（URL 前綴須有尾隨 `/`，網域資源用 `sc-domain:example.com`）。

## CLI

```bash
sitespider --mode http --url https://www.example.com/ \
  --gsc-site-url "https://www.example.com/" \
  --gsc-inspect-max 10 \
  -o reports/example-gsc
```

## 產出

- `rich_results.csv` — 本機啟發式（JSON-LD @type）
- `rich_results_gsc.csv` — 合併 GSC API 的 Verdict / Issues（僅已檢查的 URL）

## 配額與限制

- API **逐 URL** 檢查，預設每次請求間隔 1 秒。
- 回傳的是 Google **目前已索引版本** 的狀態，非即時「測試未發布程式碼」。
- 建議 `inspect_max` 設 10–30，避免耗盡每日配額。
