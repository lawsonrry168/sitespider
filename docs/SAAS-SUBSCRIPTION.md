# SiteSpider 訂閱制 / SaaS 部署指南

面向**賣給終端用戶或採訂閱制**的自架多租戶架構（v1.18+）。

## 方案分級

| 方案 | 月費（示意 USD） | 單次頁數 | 每月爬取 | SERP 查詢 | AI 文案/月 |
|------|------------------|----------|----------|-----------|------------|
| **Free** | 0 | 50 | 2 | 0 | 0 |
| Starter | 49 | 200 | 8 | 0 | 0 |
| Pro | 149 | 2,000 | 40 | 100 | 15 |
| Agency | 399 | 10,000 | 200 | 500 | 60 |

方案定義見 `sitespider/plans.py`。控制台方案頁：**http://host:8765/pricing**

Free 無需 Stripe；填租戶 ID 後於定價頁點「免費開始」即可。

## 客戶分享 Portal

- 控制台 Step 3：**客戶分享連結**（需 `portal_share` 功能，Free 起可用）
- 客戶開啟：`/portal/{token}`（預設 30 天有效）
- 設定公開網址：`SITESPIDER_PUBLIC_URL=https://spider.example.com`

## Docker 一鍵部署

```bash
docker compose up -d --build
# 控制台 http://localhost:8765/
```

## 多租戶 API Key

```bash
export SITESPIDER_API_KEYS='{"sk_live_acme":{"tenant":"acme","plan":"pro","label":"Acme Ltd"}}'
```

請求標頭：`Authorization: Bearer sk_live_acme`

未設定 `SITESPIDER_API_KEYS` 時為**本機開發模式**（不強制 Key，租戶預設 `default`）。

報告路徑：`reports/{tenant_id}/{job_id}/`

## 用量與配額

- 計量檔：`.sitespider/usage.json`（按月、按租戶）
- 查詢：`GET /api/usage?tenant_id=acme`（需 API Key）
- 超限：爬取 API 回傳 **402**

## Stripe Checkout（收款連結）

```bash
export STRIPE_SECRET_KEY=sk_live_...
export STRIPE_PRICE_STARTER=price_...
export STRIPE_PRICE_PRO=price_...
export STRIPE_PRICE_AGENCY=price_...
# AI 文案加購（一次性 Checkout，Pro/Agency）
export STRIPE_PRICE_AI_BONUS=price_...
export STRIPE_AI_BONUS_PACK_SIZE=10
# 正式站建議：
export SITESPIDER_PUBLIC_HTTPS=1
```

### AI 文案加購

- 控制台 / 定價頁：`POST /api/billing/ai-bonus-checkout`（需 `STRIPE_PRICE_AI_BONUS`）
- Webhook `checkout.session.completed` 且 `metadata.purchase_type=ai_polish_pack` → 累加 `ai_polish_bonus`
- 管理後台：`POST /api/admin/tenant/{id}/ai-bonus`，body `{"extra": 10}`

1. 使用者開啟 **/pricing**，填租戶 ID，點「訂閱」
2. `POST /api/billing/checkout` → 導向 Stripe Checkout
3. 付款成功 → Webhook `checkout.session.completed` → 寫入方案 + **自動發放 API Key**（`.sitespider/api-keys.json`）
4. 成功頁：**/checkout/success** — 提示查收 Email

## Stripe Customer Portal（客戶自助）

客戶在 **控制台** 或 **/pricing** 點「管理訂閱」，需帶 **API Key**：

```bash
POST /api/billing/portal
Authorization: Bearer sk_live_...
{"tenant_id": "acme-hk"}
```

→ 導向 Stripe Portal（改方案、取消、更新信用卡）。

Stripe Dashboard → **Settings → Billing → Customer portal** 需啟用。

## 開通 Email（SMTP）

Checkout 成功後自動寄信（含完整 API Key）：

```bash
SITESPIDER_SMTP_HOST=smtp.example.com
SITESPIDER_SMTP_PORT=587
SITESPIDER_SMTP_USER=...
SITESPIDER_SMTP_PASS=...
SITESPIDER_SMTP_FROM=noreply@your-domain.com
SITESPIDER_PUBLIC_URL=https://spider.your-domain.com
```

管理員可在 `/admin` → **重寄開通信**（會輪替 Key 再寄）。

## Stripe 訂閱（Webhook）

1. Stripe Dashboard 建立 Product / Price（對應 Starter / Pro / Agency）
2. 環境變數：

```bash
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_STARTER=price_...
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_AGENCY=price_...
```

3. Webhook URL：`POST https://your-domain/api/stripe/webhook`
4. 訂閱 metadata 建議含 `tenant_id`
5. 方案寫入 `.sitespider/tenants.json`

## SERP 排名（SerpAPI）

```bash
export SERPAPI_KEY=your_key
```

Pro+ 方案產出 `serp_rank.csv`（依頁面 title 查詢 Google 前 20 名是否出現本站）。

## 通知

爬取 payload：

```json
"notify": {
  "slack_webhook": "https://hooks.slack.com/...",
  "webhook_url": "https://your-app/hooks/sitespider",
  "email_to": "client@example.com"
}
```

Email 需 SMTP：`SITESPIDER_SMTP_HOST`、`SITESPIDER_SMTP_USER`、`SITESPIDER_SMTP_PASS` 等。

## 進階匯出（依方案）

| 功能 | 檔案 | 方案 |
|------|------|------|
| WebGL 3D 內鏈圖 | `link_graph_webgl.html` | Pro+ |
| Gephi | `link_graph.gexf` | Pro+ |
| GraphML | `link_graph.graphml` | Pro+ |
| SERP 排名 | `serp_rank.csv` | Pro+（需 SerpAPI） |

## 排程（cron）

```bash
sitespider schedule -c examples/123deal-sitespider.json -o reports/scheduled
```

## 定價與商用建議

- **自架 + 訂閱**：客戶資料留在你的 VPS，適合香港／台灣顧問 agency
- **加值**：白標報告、每月 compare、Slack 通知、SERP 追蹤
- **合規**：SERP 使用第三方 API，請遵守 SerpAPI／Google 條款；勿對客戶站過度爬取

## 管理後台

```bash
export SITESPIDER_ADMIN_KEY=your-secret-admin-key
```

- 網址：**http://host:8765/admin**
- 檢視所有租戶、本月用量、輪替 API Key
- `GET /api/admin/tenants` · `POST /api/admin/tenant/{id}/rotate-key`

## 相關檔案

- `sitespider/plans.py` — 方案
- `sitespider/auth.py` — API Key
- `sitespider/usage.py` — 用量
- `sitespider/billing_stripe.py` — Stripe
- `sitespider/notifications.py` — 通知
- `docker-compose.yml` — 部署
- `sitespider/stripe_checkout.py` — Checkout Session
- `sitespider/api_keys.py` — Key 發放
- `sitespider/admin_api.py` — 管理 API
