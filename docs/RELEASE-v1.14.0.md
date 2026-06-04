# 發布 v1.14.0 檢查清單

## 本版重點

- `priority_summary.md` 含 **7 日執行排程**
- **N-grams**（`ngrams.csv`）、**拼寫提示**（`spelling.csv`）、**內鏈圖**（`link_graph.html`）
- GEO / Priority / actions（1.13.x 累積）

## 本機驗證

```bash
cd /Users/steriod/Documents/cal/sitespider
python -m pytest -q
python -m build
python -m twine check dist/sitespider-1.14.0*
```

## 推送到 GitHub（需 workflow scope）

```bash
git push origin main
git push origin v1.14.0
```

## GitHub Release

```bash
gh release create v1.14.0 \
  --title "v1.14.0" \
  --notes-file - <<'EOF'
## 重點
- 7 日 Priority 執行排程（priority_summary.md）
- ngrams.csv、spelling.csv、link_graph.html
- GEO / priority_pages / actions 匯出

## 安裝
pip install sitespider==1.14.0
pip install "sitespider[all]"
EOF
```

## 實測建議

```bash
sitespider --config examples/123deal-sitespider.json --max-pages 40 -o reports/123deal-smoke-v114
sitespider --config examples/allurebeauty-js-sitespider.json --max-pages 25 -o reports/allurebeauty-js-smoke-v114
```

檢查：`priority_summary.md`（Day 1–7）、`link_graph.html`、`ngrams.csv`。
