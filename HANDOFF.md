# 另一視窗繼續開發 — SiteSpider

## 儲存庫（已建立）

**https://github.com/lawsonrry168/sitespider**

在本機另開終端機或 **Cursor → File → Open Folder** 選擇已 clone 的目錄：

```bash
git clone https://github.com/lawsonrry168/sitespider.git
cd sitespider
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip setuptools wheel
pip install -e ".[dev]"
```

## 建議的下一步

1. **驗證安裝**
   ```bash
   sitespider --help
   pytest -q
   ```

2. **對示範站爬取**（VitaPure 在 `lawsonrry168/cal` 的 `cal/` 目錄）
   ```bash
   git clone https://github.com/lawsonrry168/cal.git ../cal-demo
   sitespider --mode file --root ../cal-demo/cal -o reports
   open reports/index.html
   ```

3. **Web 控制台**
   ```bash
   sitespider-serve
   # http://127.0.0.1:8765/
   ```

4. **待辦功能（可選）**
   - [x] PyPI 發布流程 + [docs/RELEASE.md](docs/RELEASE.md)
   - [x] Excel、`sitespider.json` / `sitespider.yaml`、`sitespider compare`
   - [x] viewport、redirect_chain、redirects.csv、Web UI 讀設定檔
   - [ ] 手動在 PyPI 註冊套件名並完成 trusted publishing 首次設定

5. **與 cal 示範站分離**
   - SiteSpider 程式碼只在 **本 repo**
   - `cal` repo 的 `tools/seo-crawler/` 已標註遷移，勿再雙邊修改

## 推送 CI 工作流程（若尚未上傳）

本機可能有一個未推送的 commit（`.github/workflows/ci.yml`）。在終端機執行：

```bash
cd /path/to/sitespider
gh auth refresh -s workflow
git push origin main
```

若無該 commit，檔案已在工作目錄中則：

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow"
git push origin main
```

## 分支策略

```bash
git checkout -b feature/your-feature
# 開發…
pytest -q
git commit -am "feat: ..."
git push -u origin feature/your-feature
gh pr create
```

## 聯絡

GitHub Issues：https://github.com/lawsonrry168/sitespider/issues
