# 建置 Windows 本機版 SiteSpider.exe
# 用法（PowerShell）：.\scripts\build-desktop-win.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    Write-Error "請先建立虛擬環境：python -m venv .venv ; .venv\Scripts\pip install -e '.[desktop]'"
}

& $Py -m pip install -q -e ".[desktop]"
& $Py -m PyInstaller --noconfirm --clean packaging\sitespider-desktop.spec

$Out = Join-Path $Root "dist\SiteSpider.exe"
if (Test-Path $Out) {
    Write-Host ""
    Write-Host "建置完成：$Out"
    Write-Host "報告預設：%LOCALAPPDATA%\SiteSpider\reports\"
} else {
    Write-Error "找不到 dist\SiteSpider.exe"
}
