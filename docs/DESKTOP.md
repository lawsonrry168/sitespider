# SiteSpider 本機桌面版（.app / .exe）設計說明

顧問在客戶電腦上**不需安裝 Python**、**不需開終端機打指令**，雙擊圖示即可開啟爬取中心。本文件說明架構、建置方式與限制。

---

## 產品定位

| 項目 | 說明 |
|------|------|
| 目標使用者 | SEO 顧問、代理商（本機交付、無雲端帳號亦可） |
| 核心體驗 | 與現有 `sitespider --ui` **相同 Web 控制台**，預設 **pywebview 內嵌視窗**（無則改開系統瀏覽器） |
| 非目標（v1） | App Store 上架、自動更新伺服器 |

與 Screaming Frog 類似：**本機程式 + 本機 UI**，資料留在使用者電腦。

---

## 架構（建議採用）

```
┌─────────────────────────────────────────┐
│  SiteSpider.app / SiteSpider.exe        │
│  desktop_launcher.py                    │
│    ├─ 設定 ~/Library/.../SiteSpider     │
│    ├─ 啟動 ThreadingHTTPServer :8765    │
│    └─ webbrowser.open → 爬取中心        │
└─────────────────────────────────────────┘
           │
           ▼
   系統瀏覽器（Chrome / Safari / Edge）
   http://127.0.0.1:8765/?desktop=1
```

寬螢幕會自動套用**三欄桌面 GUI**（左導覽、中工作區、右情境欄），規格見 [DESKTOP-GUI.md](./DESKTOP-GUI.md)。
```

**為何用「內建伺服器 + 瀏覽器」而非重做 UI？**

- 現有 `sitespider/ui/*.html` 已完整（爬取、交付、AI、使用說明）。
- 打包一份 Python + 靜態資源即可，開發成本最低。
- 之後若要 .app 內嵌視窗，可再加一層 Tauri / pywebview（見下方進階）。

**打包工具：PyInstaller（v1）**

- macOS：產出 `SiteSpider` 可執行檔，或改 spec 產出 `SiteSpider.app`。
- Windows：產出 `SiteSpider.exe`（主控台視窗，關閉即停服務）。

程式碼：

- `sitespider/paths.py` — 打包後定位 `ui/` 與使用者資料目錄。
- `sitespider/desktop_launcher.py` — 桌面入口。
- `packaging/sitespider-desktop.spec` — PyInstaller 設定。

---

## 使用者資料目錄

| 系統 | 路徑 |
|------|------|
| macOS | `~/Library/Application Support/SiteSpider/` |
| Windows | `%LOCALAPPDATA%\SiteSpider\` |
| 報告預設 | 上述目錄下的 `reports/` |

環境變數 `SITESPIDER_DATA_DIR` 可覆寫（進階使用者）。

---

## 建置步驟

### 1. 開發機準備

```bash
cd sitespider
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[desktop]"
```

`[desktop]` 含 `pyinstaller`、`pywebview`（內嵌視窗）。

### 2. macOS

```bash
bash scripts/build-desktop-mac.sh
# 輸出：dist/SiteSpider
./dist/SiteSpider
```

若要 **.app 圖示包**（雙擊、Dock）：編輯 `packaging/sitespider-desktop.spec`，依檔內註解改為 `COLLECT` + `BUNDLE`，並準備 `.icns`。

### 3. Windows

```powershell
.\scripts\build-desktop-win.ps1
# 輸出：dist\SiteSpider.exe
```

### 4. 開發時不打包

```bash
pip install -e ".[desktop]"
python -m sitespider.desktop_launcher
# 或
sitespider-desktop

# 強制系統瀏覽器（不用內嵌視窗）
python -m sitespider.desktop_launcher --ui browser

# 僅啟動伺服器、不開視窗
python -m sitespider.desktop_launcher --ui none
```

---

## 方案分級（建議產品包）

| 版本 | 內容 | 體積（約） |
|------|------|------------|
| **Desktop Lite** | 爬蟲 + 控制台 + Excel | ~80–120 MB |
| **Desktop Pro** | + Playwright（JS 渲染） | +300 MB（需另跑 `playwright install`） |
| **Desktop + GSC** | + Google API 憑證由使用者自行設定 | 同 Lite |

**不建議打進安裝包：**

- Node.js / Lighthouse（維持「本機已安裝 npm lighthouse」提示）。
- Playwright 瀏覽器二進位（首次啟用時下載，或安裝精靈引導）。

---

## 內嵌視窗（pywebview，已內建）

| `--ui` | 行為 |
|--------|------|
| `auto`（預設） | 已安裝 pywebview → 單一 App 視窗；否則開系統瀏覽器 |
| `webview` | 僅內嵌視窗，失敗則提示安裝 `[desktop]` |
| `browser` | 一律用 Chrome / Safari / Edge |
| `none` | 不開視窗，僅印網址 |

macOS 使用 WebKit；Windows 建議已安裝 Edge WebView2（多數 Win10+ 已內建）。

## 進階路線（v2，可選）

| 方案 | 優點 | 缺點 |
|------|------|------|
| **Tauri** | 安裝包更小 | 需 Rust，後端仍要 Python |
| **Electron** | 生態成熟 | 體積大 |

---

## 簽章與發佈

| 平台 | 建議 |
|------|------|
| macOS | Apple Developer ID + `codesign` + 公證（notarize），否則 Gatekeeper 會擋 |
| Windows | Authenticode 簽章，減少 SmartScreen 警告 |

CI 可用 GitHub Actions：`macos-latest` / `windows-latest` 各跑對應 build script，上傳 Release 附件。

---

## 已知限制（須在說明頁寫清楚）

1. 關閉終端機視窗（或 .exe 視窗）即停止服務。
2. 埠 8765 被佔用時會自動嘗試 8766…。
3. Lighthouse / Playwright / GSC 仍為**選用**，邏輯與現有 Web 版相同。
4. iCloud 同步資料夾內執行可能較慢，建議報告目錄放在本機磁碟。

---

## 相關指令對照

| 用途 | 指令 |
|------|------|
| 開發 Web 版 | `bash scripts/dev-ui.sh` |
| 桌面啟動（未打包） | `python -m sitespider.desktop_launcher` |
| 僅 CLI 爬取 | `sitespider --config …` |
| 建置 macOS | `bash scripts/build-desktop-mac.sh` |
| 建置 Windows | `.\scripts\build-desktop-win.ps1` |
