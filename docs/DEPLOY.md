# SiteSpider 部署指南

SiteSpider 是**命令列工具**，不是需要常駐的 Web 服務。部署通常指下列三種情境之一。

---

## 情境 A：發布工具到 PyPI（讓他人 `pip install`）

### 一次性設定

1. 註冊 [pypi.org](https://pypi.org) 帳號。
2. 確認套件名 `sitespider` 可用（若被佔用，修改 `pyproject.toml` 的 `name`）。
3. **Trusted Publishing（建議，免 API token）**
   - PyPI → **Account settings** → **Publishing** → **Add a new pending publisher**
   - PyPI project name: `sitespider`
   - Owner: `lawsonrry168`
   - Repository: `sitespider`
   - Workflow filename: `publish.yml`
   - Environment name: `pypi`
4. GitHub 儲存庫 `lawsonrry168/sitespider` → **Settings** → **Environments** → **New environment** → 名稱填 `pypi`。

### 每次發版

```bash
cd sitespider
# 1. 更新版本號（兩處一致）
#    pyproject.toml → version = "1.3.0"
#    sitespider/__init__.py → __version__ = "1.3.0"

pytest -q
git add -A && git commit -m "chore: release v1.3.0"
git push origin main

# 2. 在 GitHub 建立 Release
#    Tag: v1.3.0  （建議與版本號一致，可帶 v 前綴）
#    Publish release
#    → 自動執行 .github/workflows/publish.yml → 上傳 PyPI
```

### 驗證安裝

```bash
pip install sitespider
sitespider --help
```

詳見 [RELEASE.md](./RELEASE.md)。

---

## 情境 B：在你的「網站專案」裡跑 SEO CI（最常見）

目標：每次 push / PR 自動爬取靜態站或 build 產物，有 SEO 問題就讓 CI 失敗。

### 步驟 1：在網站 repo 加入設定

在**網站根目錄**（有 `index.html` 或 build 輸出的地方）：

```bash
# 於網站專案目錄
sitespider init --with-config --site-url https://你的網域/
# 或 YAML：sitespider init --with-config --yaml
```

編輯 `sitespider.json`，例如 VitaPure / cal 子目錄：

```json
{
  "site_url": "https://你的使用者名.github.io/cal/",
  "sitemap_path_prefixes": ["cal"],
  "mode": "file",
  "output": "reports",
  "audit": { "thin_content_min_words": 300 }
}
```

`sitemap_path_prefixes` 用於 sitemap 裡是 `https://…/cal/page.html`、本機卻是 `page.html` 的情況。

### 步驟 2：GitHub Actions

**方式 1 — 從 PyPI 安裝（SiteSpider 已發布後）：**

`.github/workflows/seo.yml`：

```yaml
name: SEO Audit

on:
  push:
    branches: [main]
  pull_request:

jobs:
  seo:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install SiteSpider
        run: pip install "sitespider[excel]"

      - name: Crawl site
        run: |
          sitespider --mode file --root . \
            -o reports \
            --fail-on-issues

      - name: Upload reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: seo-reports
          path: reports/
```

若 HTML 在子目錄（例如 `cal/`）：

```yaml
      - run: sitespider --mode file --root cal -o reports --fail-on-issues
```

**方式 2 — 尚未發布 PyPI，用 git submodule / path：**

```yaml
      - name: Install SiteSpider
        run: pip install -e ./tools/sitespider
```

### 步驟 3：PR 回歸比對（選用）

保留 main 分支上一份基準報告，或從 artifact 下載後比對：

```yaml
      - name: Compare with baseline
        run: |
          sitespider compare path/to/baseline/crawl-report.json reports/crawl-report.json --fail-on-new
```

### 步驟 4：本機先跑通

```bash
cd /path/to/your-website
pip install -e /path/to/sitespider   # 或 pip install sitespider
sitespider --mode file --root . -o reports
open reports/index.html
sitespider-check reports/crawl-report.json
```

---

## 情境 C：爬取「已上線」的 HTTP 網站

適用：staging / production URL、需檢查真實重新導向與 HTTP 狀態碼。

```bash
# 本機先確認網站可連
sitespider --mode http \
  --url https://example.com/ \
  -o reports \
  --max-pages 200 \
  --max-depth 5

# Lighthouse（需 Node + npm install lighthouse）
sitespider --mode http --url https://example.com/ --lighthouse --lighthouse-max 10
```

CI 範例（爬遠端，不 build 靜態檔）：

```yaml
      - run: |
          sitespider --mode http --url https://example.com/ \
            -o reports --fail-on-issues --max-pages 100
```

注意：請遵守目標站 `robots.txt`，勿對他人網站過度並行爬取。

---

## 情境 D：Web 控制台（僅本機／內網）

`sitespider-serve` **不建議**暴露到公網（無認證、可觸發任意路徑爬取）。

```bash
cd /path/to/your-website
sitespider --ui
# 或
sitespider-serve --host 127.0.0.1 --port 8765
# 瀏覽器開 http://127.0.0.1:8765/
```

內網若必須使用：請加反向代理 + 認證（nginx Basic Auth、VPN 等）。

---

## 建議部署順序（Checklist）

| 順序 | 動作 | 完成 |
|------|------|------|
| 1 | 本機 `pytest -q`、`sitespider --mode file --root <網站> -o reports` | ☐ |
| 2 | 網站 repo 加入 `sitespider.json` + `sitespider init` 的 workflow | ☐ |
| 3 | Push 後確認 Actions 綠燈、下載 `seo-reports` artifact | ☐ |
| 4 | （選用）PyPI trusted publishing + Release `v1.3.0` | ☐ |
| 5 | 網站 CI 改為 `pip install sitespider` | ☐ |

---

## 與 Screaming Frog 匯出比對

1. 在 Screaming Frog：**Bulk Export → Internal → Export**，存成 `screaming-frog-internal.csv`。
2. SiteSpider 爬取後會產生 `internal.csv`（欄位與 SF Internal 對齊）。
3. 比對差異：

```bash
sitespider diff-csv screaming-frog-internal.csv reports/allurebeauty/internal.csv -o reports/allurebeauty
# 或
sitespider-diff-csv sf.csv reports/allurebeauty/internal.csv
```

輸出：

- `diff-only-screaming-frog.csv` — 僅 SF 抓到的 URL
- `diff-only-sitespider.csv` — 僅 SiteSpider 抓到的 URL
- `diff-sf-comparison.md` — 摘要與欄位不一致說明

## 常見問題

**Q：和 Vercel / GitHub Pages 部署有關係嗎？**  
A：SiteSpider 不部署到你的 Pages。它是 **build 或 push 之後在 CI 裡檢查 HTML**，或本機檢查。靜態站照常 `git push` → Pages 發布；SEO 檢查在 Actions 平行執行。

**Q：`--fail-on-issues` 失敗怎麼辦？**  
A：開 `reports/index.html` 或 `issues.csv`，依問題類型修改 title、meta、canonical 等後再 push。

**Q：cal 示範站路徑？**  
A：`sitespider --mode file --root cal -o reports`，`sitespider.json` 內設 `sitemap_path_prefixes: ["cal"]` 與正確 `site_url`。
