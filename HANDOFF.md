# 另一視窗繼續開發 — SiteSpider

## 儲存庫

推送完成後，在本機另開終端機或 Cursor 視窗：

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
   - [ ] 發布至 PyPI：`pip install sitespider`
   - [ ] 匯出 Screaming Frog 風格 Excel
   - [ ] 圖表：內鏈深度分佈、狀態碼圓餅圖
   - [ ] `sitespider init` 在專案內產生 GitHub Actions 範本
   - [ ] 自訂網域 / base URL 設定檔（取代寫死在 sitemap）

5. **與 cal 示範站分離**
   - SiteSpider 程式碼只在 **本 repo**
   - `cal` repo 的 `tools/seo-crawler/` 已標註遷移，勿再雙邊修改

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
