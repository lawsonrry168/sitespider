# SiteSpider 發布至 PyPI

## 首次設定（一次性）

1. 在 [pypi.org](https://pypi.org) 註冊帳號，並建立專案 **`sitespider`**（若名稱已被佔用，請改 `pyproject.toml` 的 `name`）。

2. **Trusted Publishing（建議）**
   - PyPI → Account → Publishing → Add GitHub Actions publisher
   - Owner: `lawsonrry168`，Repository: `sitespider`，Workflow: `publish.yml`，Environment: `pypi`

3. GitHub repo → **Settings → Environments** → 新增 `pypi`（與 workflow 中 `environment: pypi` 對應）。

## 每次發版

```bash
# 1. 更新版本
#    pyproject.toml 與 sitespider/__init__.py 的 __version__

pytest -q
python -m build   # 需 pip install build

# 2. 建立 GitHub Release
#    Tag: v1.3.0（與版本一致）
#    Title: v1.3.0
#    Publish release → 觸發 .github/workflows/publish.yml
```

## 本機驗證（選用）

```bash
pip install build twine
python -m build
twine check dist/*
# 測試上傳至 TestPyPI：
twine upload --repository testpypi dist/*
pip install -i https://testpypi.org/simple/ sitespider==
```

## 安裝方式（使用者）

```bash
pip install sitespider
pip install "sitespider[excel]"   # Excel
pip install "sitespider[yaml]"    # YAML 設定檔
pip install "sitespider[all]"     # 全部選用功能
```
