# Screaming Frog 功能對照

SiteSpider v1.16 對齊狀態（2026）。

## 已支援

| SF 分頁 / 功能 | SiteSpider |
|----------------|------------|
| Internal | `internal.csv`（含 Link Score、Outlinks） |
| All Inlinks | `all_inlinks.csv`（Follow、Link Position） |
| Link Position / Nofollow | `links.csv`、`internal.csv` 欄位 |
| Anchor Text 衝突 | `anchor_text.csv` + 稽核 |
| 產生 Sitemap | `sitemap_generated.xml` |
| 孤立頁 | `orphan_pages.csv` |
| 失效外部連結 | `broken_external.csv` |
| 圖片尺寸 | `images.csv`（width/height/loading） |
| URL 檢視器 | `inspector.html`（單頁詳情） |
| External | `external.csv` |
| Security | `security.csv` |
| URL | `url.csv` |
| Response Codes | `response_codes.csv` |
| Page Titles | `page_titles.csv` + pixel width |
| Meta Description | `meta_descriptions.csv` |
| Meta Keywords | `meta_keywords.csv` |
| H1 / H2 / H3 | `h1.csv` / `h2.csv` / `h3.csv` |
| Outlinks | `outlinks.csv`（另含 `links.csv` 全欄位版） |
| Robots.txt | `robots.csv`（規則 + 被封鎖 URL） |
| 內容重複群組 | `duplicate_content.csv`（hash 群組） |
| JavaScript | `javascript.csv`（JS 渲染、Console） |
| Rich Results（啟發式） | `rich_results.csv`（無 Google API） |
| Canonicals | `canonicals.csv` |
| Pagination | `pagination.csv` |
| Directives | `directives.csv` |
| Hreflang | `hreflang.csv` + 稽核 |
| Structured Data | `structured_data.csv` + `json_ld_rules` |
| Content | `content.csv` + duplicate hash |
| Sitemaps | `sitemap_diff.csv` |
| JavaScript | `--render-js` (Playwright) |
| List Mode | `sitespider list urls.txt` |
| Custom Extraction | `--custom-config` → `custom.csv` |
| HTTP Headers | `headers.csv` |
| AMP | `amp.csv` (rel=amphtml) |
| Console (JS) | `console.csv` |
| Screenshots (JS) | `--screenshots` |
| Lighthouse | `--lighthouse` |
| Compare / CI | `compare`, `diff-csv`, `sitespider-check` |
| N-grams | `ngrams.csv`（2/3-gram，on-page 文字） |
| 拼寫 | `spelling.csv`（預設啟發式；`sitespider[spelling]` → pyspellchecker） |
| 連結圖 | `link_graph.html`（D3 互動）· `link_graph_simple.html`（SVG） |
| Rich Results（GSC API） | `rich_results_gsc.csv`（需 GSC 憑證，見 `docs/GSC-RICH-RESULTS.md`） |
| Priority / GEO | `priority_pages.csv`, `priority_summary.md`, `geo.csv`, `actions.csv` |

## 尚未支援（需 SF 桌面或第三方）

- 完整 Hunspell 拼寫檢查
- 即時「未發布 URL」Rich Results 測試（GSC API 僅反映 Google 已索引版本）
- 全站數千節點即時力導向（目前上限約 150 節點，可調 slider）
- 完整 PageRank（目前為簡化內部 PageRank）
- 完整桌面 GUI 與單 URL 多面板詳情（僅 `index.html` + CSV）
- SERP 模式爬取
