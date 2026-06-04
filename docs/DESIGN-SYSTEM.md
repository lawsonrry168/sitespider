# SiteSpider 設計系統 — Washi Indigo（和紙 × 藍染）

> **一句話**：藍染靛墨底 + 若竹綠 accent + 和紙淺色模式 + Outfit 標題，專業、有溫度、不沉悶。

## 風格定位：日系精緻 × 歐美 SaaS

| 面向 | 日系（採用） | 歐美 SaaS（採用） | 刻意避免 |
|------|-------------|------------------|----------|
| 色彩 | 藍染 `#0b0d12`、若竹 `#6ec9a0`、和紙 `#f5f3ef` | 單一清晰 CTA、高對比層級 | 霓虹螢光綠、純灰 admin 模板感 |
| 版面 | 留白（間）、略圓角 `13–18px` | 明確 pipeline / 卡片結構 | 過多漸層與細網格 |
| 字體 | Noto Sans TC 正文 | Outfit 標題 / IBM Plex Mono 數據 | 全大寫擠壓標籤 |

**為什麼不選純日系或純歐美？**  
純日系易偏柔和難掃讀 KPI；純歐美深色易冷硬。混合後保留顧問交付的**可信度**，又用暖色文字與竹綠 accent 帶一點生氣。

## 品牌色

| Token | 深色 | 淺色（和紙） | 用途 |
|-------|------|-------------|------|
| `--color-bg` | `#0b0d12` | `#f5f3ef` | 頁面底 |
| `--color-surface` | `#181f2b` | `#ffffff` | 卡片 |
| `--color-accent` | `#6ec9a0` | `#2a7d5a` | 主按鈕、進度、品牌字 |
| `--color-accent-2` | `#8baee8` | `#3d6db5` | 連結、次要強調 |

## 商標與 Favicon（統一圖形）

**主檔** `sitespider/ui/brand-mark.svg`：

- 藍染靛方塊（圓角 8px）+ 若竹八足蜘蛛
- 八端節點圓點＝爬取到的 URL／內鏈節點
- 淡掃描環＝站內覆蓋範圍

| 用途 | 檔案 |
|------|------|
| 頂欄商標 | `app-shell.js` → `<img src="/ui/brand-mark.svg">` |
| 分頁 favicon | `brand-mark.svg`（`favicon.svg` 由腳本同步副本） |
| 主畫面 | `apple-touch-icon.svg`（180×180） |
| 匯出分析儀表板 | `report_theme.brand_mark_inline()` 內嵌 SVG |

```html
<link rel="icon" href="/ui/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/ui/apple-touch-icon.svg">
<meta name="theme-color" content="#0b0d12">
```

## 檔案載入順序（風格重設後）

```html
<link rel="stylesheet" href="/ui/tokens.css">
<link rel="stylesheet" href="/ui/shell.css">
<link rel="stylesheet" href="/ui/theme.css">
<link rel="stylesheet" href="/ui/comfort-display.css">
<link rel="stylesheet" href="/ui/polish.css">
<link rel="stylesheet" href="/ui/ux-friendly.css">
<link rel="stylesheet" href="/ui/site-reset.css">   <!-- 單一視覺權威層 -->
<link rel="stylesheet" href="/ui/nav-back.css">
<script src="/ui/app-shell.js"></script>
<body class="app-console">
```

- **`site-reset.css`**：合併原 `site-v2` / `site-polish`，統一環境光、卡片、按鈕與報告頁；`theme.css` 不再疊加背景漸層。
- **`site-v2.css` / `site-polish.css`**：僅保留檔名相容，新專案請勿再引用。

匯出報告經 `report_theme.report_styles_bundle()` 內嵌相同 token + `site-reset`，與控制台一致。

## 爬取中心版面（`console-layout.css`）

| 區域 | 用途 |
|------|------|
| 情境列 | 三步驟 + 當步說明 + 任務下拉 + 新爬取 |
| 主欄 | 步驟 1 窄欄表單；步驟 2 進度劇場；步驟 3 左結果／右檔案 |
| 右欄 | 依步驟切換：設定（快速開始＋最近任務）／執行（即時監控）／交付（捷徑） |

僅 `dashboard.html` 載入 `console-layout.css`。

## 桌面版 GUI（`desktop-gui.css`）

寬螢幕（≥1100px）或 `?desktop=1` 時：

- **爬取中心**：三欄駕駛艙 + 可拖曳右欄 + 底部狀態列（`desktop-gui.css`）
- **其他控制台頁**：左欄導覽 + 全寬內容（`desktop-pages.css`）
- **本機啟動**：`desktop_launcher` 預設 pywebview 內嵌視窗

規格見 [DESKTOP-GUI.md](./DESKTOP-GUI.md)、[DESKTOP.md](./DESKTOP.md)。

## 報告頂欄（`report-layout.css`）

| 行 | 內容 |
|----|------|
| 第一行 | ← 返回 · ⌂ 爬取中心 · 品牌與頁名 · ↗ 檢視網站 |
| 第二行 | 「頁面」標籤 + 可橫向捲動的報告 nav |

經 `report_styles_bundle()` 內嵌至所有匯出報告；舊 HTML 無 `report-topbar-docs` 時 CSS 仍相容。

## 字級（24" / 27"）

根字級隨螢幕加寬：16px → 17px（≥1440px）→ 18px（≥1920px）。詳見 `comfort-display.css`。

## 遷移自 Obsidian Signal

舊 Signal Green `#4ade80` 已改為若竹 `#6ec9a0`。白標預設 accent 亦同步；既有 localStorage 中的 `#4ade80` 仍會沿用至使用者於 `/branding` 更新。
