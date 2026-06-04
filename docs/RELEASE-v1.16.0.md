# Release v1.16.0

## 摘要

顧問交付完整版：Web 控制台、REPORT-zh、交付 ZIP（含客戶一頁說明）、可選 GSC、SF 擴充與 Phase 2 工具。

## 新功能

- `sitespider --ui` Web 控制台
- `sitespider package` 交付 ZIP（含 `README-客戶.txt`）
- `sitespider multi-compare` 多站 HTML 儀表板
- `sitespider compare … --changed-urls-only` 增量比對
- `serp_snippets.csv`、`link_graph_full.html`（≥80 頁時產生）
- 拼寫：`pyspellchecker` 或 `HUNSPELL_DICT` + Hunspell
- 可選 GSC URL Inspection → `rich_results_gsc.csv`

## 發版步驟

```bash
cd /path/to/sitespider
pytest -q
git add -A
git commit -m "$(cat <<'EOF'
Release v1.16.0: delivery console, Phase 2 tools, SF exports.

EOF
)"
git tag -a v1.16.0 -m "v1.16.0"
git push origin main
git push origin v1.16.0
```

若 push 因 workflow 失敗，請用含 `workflow` scope 的 token 重新授權，或：

```bash
gh auth refresh -s workflow
```

## 123deal 交付（無 GSC）

```bash
sitespider --config examples/123deal-sitespider.json
sitespider-package reports/<job-dir>
```
