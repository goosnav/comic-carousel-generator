# Comic Carousel Generator. Run .\run.ps1 to open the GUI.
# Headless: .\run.ps1 scan1.jpg scan2.jpg --out DIR
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Write-Host "I need uv to fetch Python and the dependencies once. Install it with:"
  Write-Host '  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'
  Write-Host "then run this again."
  exit 1
}
$env:GOOSNAV_CALLER_CWD = (Get-Location).Path
$env:GOOSNAV_APP_ROOT = Join-Path $Here "app"
$env:GOOSNAV_HOST = "127.0.0.1"
$env:GOOSNAV_PORT_PREFERENCE = "0"
Set-Location (Join-Path $Here "app")
uv run --locked --managed-python --no-dev python launcher/bootstrap.py @args
