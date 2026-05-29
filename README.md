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

# 選用：Lighthouse
npm install
```

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
```

## 命令列

| 指令 | 說明 |
|------|------|
| `sitespider` | 執行爬取並產生報告 |
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
sitespider --ui               # http://127.0.0.1:8765/
sitespider-check reports/crawl-report.json --lighthouse
```

## 報告輸出

| 檔案 | 內容 |
|------|------|
| `index.html` | 視覺化總覽 |
| `pages.csv` | 每頁 SEO 欄位、Lighthouse、JSON-LD 類型 |
| `links.csv` | 內部／外部連結與錨文字 |
| `images.csv` | 圖片 src、alt、狀態 |
| `blocked.csv` | robots.txt 封鎖的 URL |
| `lighthouse.csv` | 效能／SEO 分數 |
| `crawl-report.json` | 完整結構化資料 |

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
| 開放原始碼 | ✗ | ✓ |

## 偵測項目

- 缺少 / 過長 title、meta description
- H1 缺失或多個 H1
- 圖片缺少 alt、圖片 404
- 孤立頁、重複 title
- robots 封鎖、meta noindex
- 缺少 Open Graph、JSON-LD
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
