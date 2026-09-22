# FEATURE_ROADMAP — Implementation Status

SiteSpider v1.25.0 wires Phase 1–4 roadmap modules into the crawl pipeline, CLI, report exports, and optional integrations. This document reflects **honest** shipped status as of the roadmap integration branch.

## Phase 1 — Core crawl enrichment

| Module | Status | Notes |
|--------|--------|-------|
| `PageResult` fields | **Done** | `body_text`, `heading_sequence`, `form_actions`, `raw_html`, `tracking`, readability/GA4/backlink/security fields |
| Fragment check | **Done** | Playwright: real `<a href>` list passed to `check_fragments_on_page`. HTTP: BeautifulSoup `id`/`name` fallback |
| Tracking footprint | **Done** | `audit_html_tracking` + `apply_page_tracking` during `_parse_html`; post-crawl site/locale audits |
| Heading hierarchy | **Done** | DOM-order `heading_sequence` + `audit_heading_hierarchy` |
| URL quality | **Done** | `audit_url_quality` in roadmap runner |
| Insecure forms | **Done** | `audit_insecure_forms` |
| Security headers | **Done** | Default on; `audit_security_headers` + `security_score` |

## Phase 2 — Content & similarity

| Module | Status | Notes |
|--------|--------|-------|
| Near duplicates | **Done** | `similarity.audit_near_duplicates` — **shingle Jaccard/cosine + SimHash**, not sklearn |
| Readability | **Done** | English Flesch / Chinese sentence-length heuristic |
| Keyword density | **Done** | Top terms + `keyword_stuffing` issue |
| Directory tree | **Done** | `directory_tree.html` when `export_directory_tree` (default true) |
| Image sitemap | **Done** | `export_image_sitemap_xml` when `--image-sitemap` |

## Phase 3 — External APIs (optional deps)

| Module | Status | Notes |
|--------|--------|-------|
| GA4 Data API | **Done** | `pip install "sitespider[analytics]"`; `--ga4-property-id`, `--ga4-credentials`, `--ga4-date-range` |
| Backlinks (Ahrefs/Moz) | **Done** | `--backlink-provider` + `--backlink-api-key` |
| CrUX API | **Done** | `--crux-api-key`; origin-level CWV |
| Grammar (LanguageTool) | **Done** | `--grammar-check` + `--grammar-api-url`; issue `grammar_error` |
| AMP validate | **Done** | `--audit-amp` |
| a11y (axe-core) | **Done** | `--a11y-audit` during Playwright render; violations → `accessibility.csv` |

## Phase 4 — Delivery & integrations

| Module | Status | Notes |
|--------|--------|-------|
| Looker bundle | **Done** | `looker/pages.json` + schema — **JSON dump for manual upload, not a Looker Community Connector** |
| Google Sheets | **Done** | `--export-sheets` + `--sheets-id` + optional `--sheets-credentials`; `pip install "sitespider[sheets]"` |
| Tracking bundle | **Done** | `tracking.csv`, `tracking-events.csv`, `tracking-audit.html` |
| Robots test API | **Done** | `GET/POST /api/robots/test` — **test API only, not a full robots editor UI** |
| Roadmap runner | **Done** | `run_roadmap_audits` + `export_roadmap_reports` from `post_crawl` / report tiers |

## CLI flags (summary)

Roadmap options are exposed on `sitespider` CLI and mapped into `CrawlConfig`: near-duplicate threshold, security/readability/keyword/tracking toggles, GA4/backlink/CrUX/grammar/AMP/a11y, Looker/Sheets/directory tree/image sitemap, Playwright cookies/JS/auth, `--user-agent-preset`, `--no-check-fragments`.

## Known limitations

- **Similarity** uses in-house shingles/SimHash, not scikit-learn TF-IDF.
- **Looker** export is static JSON; no live connector in Looker Studio.
- **Robots** server endpoint validates rules; no visual editor.
- **GA4 / Sheets / analytics** require Google credentials and optional packages; failures append to `report.errors` without aborting the crawl.
- **a11y** runs only when Playwright render path is used with `--a11y-audit`.
- **analytics_dashboard.html** is produced by `report_analytics` (`dashboard.html` in standard tier); roadmap export does **not** duplicate it.

## Report artifacts

When enabled and data exists: `near_duplicates.csv`, `readability.csv`, `keyword_density.csv`, `accessibility.csv`, `analytics.csv`, `backlinks.csv`, `crux.csv`, `grammar.csv`, `directory_tree.html`, tracking bundle, `looker/pages.json`.
