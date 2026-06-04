# SiteSpider

**SiteSpider** 是獨立的專業 SEO 站內爬蟲，靈感來自 [Screaming Frog SEO Spider](https://www.screamingfrog.co.uk/seo-spider/) 與 SEMrush Site Audit。可爬取任意靜態或本機網站，分析連結結構、標題標籤、圖片、robots.txt、sitemap，並可選整合 Google Lighthouse。

```
  sitespider ──► 爬取 (BFS + 並行)
       │
       ├── robots.txt / sitemap.xml
       ├── 每頁：title, meta, H1–H3, 連結, 圖片
       └── 報告：HTML + CSV + JSON
```

## 安裝

```bash
cd sitespider
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 選用：Excel 匯出
pip install -e ".[excel]"

# 選用：Lighthouse
npm install
```

## PyPI 安裝

```bash
pip install sitespider
pip install "sitespider[excel]"   # 含 Excel 匯出
pip install "sitespider[yaml]"    # YAML 設定檔
pip install "sitespider[all]"     # 全部選用功能
```

> **部署**：見 [docs/DEPLOY.md](docs/DEPLOY.md)（PyPI 發布、網站 CI、HTTP 爬取）。  
> 發布：見 [docs/RELEASE.md](docs/RELEASE.md)。

## 快速開始

```bash
# 在您的網站根目錄執行（含 index.html）
cd /path/to/your-website
sitespider --mode file --root .

# HTTP 模式（需先啟動伺服器）
python3 -m http.server 8080 &
sitespider --mode http --url http://127.0.0.1:8080/

# 開啟報告
open reports/index.html
open reports/dashboard.html   # 分析圖表（推薦給客戶簡報）
```

報告設計說明見 [docs/REPORT-DESIGN.md](docs/REPORT-DESIGN.md)。  
SF 功能對照見 [docs/SF-PARITY.md](docs/SF-PARITY.md)。

## 命令列

| 指令 | 說明 |
|------|------|
| `sitespider` | 執行爬取並產生報告 |
| `sitespider list` | SF List Mode：僅爬 URL 清單 |
| `sitespider-serve` | Web 控制台（深度滑桿、即時進度） |
| `sitespider-check` | 檢查 `reports/crawl-report.json` 是否通過稽核 |

### 常用參數

```bash
sitespider \
  --mode file \
  --root /path/to/site \
  --workers 8 \
  --max-depth 5 \
  --max-pages 200 \
  -o ./my-reports \
  --fail-on-issues          # CI：有問題則 exit 1

sitespider --mode http --url https://example.com/ --lighthouse --lighthouse-max 5
sitespider --require-json-ld --thin-content-min 200
# v1.6：預設爬完後批次檢查內鏈／圖片（較快）；需即時檢查可加：
sitespider --mode http --url https://example.com/ --eager-link-check --check-images-on-fetch
sitespider export reports/crawl-report.json -o reports/   # 由 JSON 重生報告

# v1.8：JavaScript 渲染（Webflow / SPA，需 Playwright）
pip install "sitespider[browser]"
playwright install chromium
sitespider --mode http --url https://www.allurebeauty.com.hk/ --render-js --workers 2 -o reports/allure-js

# List 模式、自訂擷取、URL 清單種子
sitespider list urls.txt --url https://example.com/ -o reports/list
sitespider --urls-file urls.txt --url https://example.com/   # 清單作種子 + BFS
sitespider --custom-config examples/custom-extractions.example.json

sitespider init               # 產生 .github/workflows/sitespider.yml
sitespider --ui               # http://127.0.0.1:8765/
sitespider-check reports/crawl-report.json --lighthouse
```

## 報告輸出

| 檔案 | 內容 |
|------|------|
| `dashboard.html` | **分析圖表儀表板**（Chart.js，適合簡報） |
| `index.html` | 視覺化總覽（Internal / External / Security / Sitemap 等分頁） |
| `internal.csv` | SF Internal（含 Title Pixel Width） |
| `external.csv` / `security.csv` / `url.csv` | 外部連結、HTTPS／混合內容、URL 結構 |
| `h2.csv` / `meta_descriptions.csv` / `meta_keywords.csv` | On-Page 分頁 |
| `pagination.csv` / `directives.csv` / `structured_data.csv` | 分頁、robots、結構化資料 |
| `content.csv` / `sitemap_diff.csv` / `hreflang.csv` | 內容重複、sitemap 差異、多語 |
| `pages.csv` | 每頁完整欄位、Lighthouse、JSON-LD |
| `links.csv` | 內部／外部連結與錨文字 |
| `images.csv` | 圖片 src、alt、狀態 |
| `blocked.csv` | robots.txt 封鎖的 URL |
| `lighthouse.csv` | 效能／SEO 分數 |
| `issues.csv` | 每頁問題明細（issue、URL、深度） |
| `crawl-report.xlsx` | 多工作表 Excel（需 `[excel]`） |
| `crawl-report.json` | 完整結構化資料 |

## 專案設定檔 `sitespider.json`

在網站根目錄放置 `sitespider.json`（或複製 `sitespider.json.example`），CLI 會自動載入；命令列參數優先於設定檔。

```json
{
  "site_url": "https://www.example.com/",
  "sitemap_path_prefixes": ["cal"],
  "crawl": { "max_pages": 200, "max_depth": 5 },
  "audit": { "require_json_ld": true, "thin_content_min_words": 300 },
  "report": { "xlsx": true }
}
```

| 欄位 | 用途 |
|------|------|
| `site_url` | 正式網域（http 模式預設起始 URL） |
| `sitemap_path_prefixes` | sitemap 內 `https://…/cal/page.html` → 本機 `page.html` |
| `crawl.*` | 爬取深度、並行、Lighthouse 等 |
| `audit.*` | JSON-LD、內容過薄門檻 |
| `report.xlsx` | 自動匯出 Excel |

```bash
sitespider init --with-config          # 產生 workflow + sitespider.json
sitespider init --with-config --yaml   # 產生 sitespider.yaml
sitespider -c ./sitespider.json        # 指定設定檔
sitespider --xlsx                      # 強制匯出 Excel
sitespider compare baseline.json current.json --fail-on-new   # CI 回歸
sitespider-compare reports/main/crawl-report.json reports/crawl-report.json
sitespider report reports/allurebeauty/crawl-report.json --label "客戶網站名稱"
sitespider --client-report --client-label "客戶名稱"   # 爬取時一併產生 SEO-AUDIT-zh.md
sitespider diff-csv screamfrog-internal.csv reports/allurebeauty/internal.csv
sitespider urls reports/allurebeauty/crawl-report.json -o urls.txt
```

### 報告檔案（對照 Screaming Frog 分頁）

| 檔案 | SF 分頁 |
|------|---------|
| `internal.csv` | Internal |
| `response_codes.csv` | Response Codes |
| `page_titles.csv` | Page Titles |
| `h1.csv` | H1 |
| `canonicals.csv` | Canonicals |
| `issues.csv` | 問題彙整 |
| `SEO-AUDIT-zh.md` | 客戶繁中摘要 |

## 功能對照

| 功能 | Screaming Frog | SiteSpider |
|------|----------------|------------|
| 站內 URL 探索 | ✓ | ✓ BFS + sitemap 種子 |
| Title / Meta / H1–H3 | ✓ | ✓ |
| 內部連結圖 | ✓ | ✓ CSV + 報告 |
| 圖片 alt / 失效 | ✓ | ✓ |
| robots.txt | ✓ | ✓ |
| sitemap.xml | ✓ | ✓ |
| 並行爬取 | ✓ | ✓ `--workers` |
| Lighthouse | 外掛 | ✓ `--lighthouse` |
| Excel 匯出 | ✓ | ✓ `crawl-report.xlsx` |
| 專案設定檔 | ✗ | ✓ `sitespider.json` |
| 開放原始碼 | ✗ | ✓ |

## 偵測項目

- 缺少 / 過長 title、meta description
- H1 缺失或多個 H1
- 圖片缺少 alt、圖片 404
- 孤立頁、重複 title
- robots 封鎖、meta noindex
- 缺少 Open Graph、JSON-LD（`--require-json-ld` 啟用）
- canonical 缺失或與 URL 不一致
- 內容過薄（`--thin-content-min`，預設 300 字）
- 缺少 `html lang`、meta description 過短
- 內部連結 404
- 缺少 viewport、多段重新導向（HTTP）
- HTML 報告含深度／狀態碼／問題類型圖表
- 兩次爬取差異比對（`sitespider compare`）
- Lighthouse SEO / 效能偏低（選用）

## 專案結構

```
sitespider/
├── sitespider/           # Python 套件
│   ├── cli.py            # 命令列
│   ├── crawler.py        # 爬蟲核心
│   ├── robots.py
│   ├── sitemap.py
│   ├── lighthouse_runner.py
│   ├── report.py
│   ├── check.py          # CI 稽核
│   ├── server.py         # Web UI
│   └── ui/dashboard.html
├── tests/
├── pyproject.toml
└── package.json          # Lighthouse（選用）
```

## CI 範例

```yaml
- run: pip install -e ./sitespider
- run: |
    cd your-website
    sitespider --mode file --root . --fail-on-issues
```

## 授權

MIT

## 與 VitaPure 示範站的關係

本工具最初在 [lawsonrry168/cal](https://github.com/lawsonrry168/cal) 示範專案中開發，現已獨立為本儲存庫，可對**任意網站**使用。

另開視窗繼續開發請見 [HANDOFF.md](HANDOFF.md)。
