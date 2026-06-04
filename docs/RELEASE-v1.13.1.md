# 發布 v1.13.1 檢查清單

## 本機已完成

- [x] `pytest`（67 passed）
- [x] `git commit` + tag `v1.13.1`
- [x] `python -m build` → `dist/sitespider-1.13.1-py3-none-any.whl`（twine check PASSED）

## 推送到 GitHub（需在本機終端執行）

Cursor 內建 Git 可能因 **缺少 `workflow` scope** 無法推送 `.github/workflows/`。請在本機 Terminal：

```bash
cd /Users/steriod/Documents/cal/sitespider
git push origin main
git push origin v1.13.1
```

若仍被拒，請用含 `workflow` 權限的 PAT，或先登入 `gh auth login` 並勾選 workflow。

## 建立 GitHub Release（推送成功後）

```bash
gh release create v1.13.1 \
  --title "v1.13.1" \
  --notes-file - <<'EOF'
## 重點
- 修正 Webflow/CMS canonical（無 https:// 的網域路徑）
- SF 風格匯出、Link Score、Playwright JS、URL 檢視器（1.10–1.13 累積）

## 安裝
pip install sitespider==1.13.1
pip install "sitespider[all]"   # Excel + YAML + Playwright
EOF
```

若已設定 PyPI Trusted Publishing，**Publish release** 會觸發 `.github/workflows/publish.yml`。
