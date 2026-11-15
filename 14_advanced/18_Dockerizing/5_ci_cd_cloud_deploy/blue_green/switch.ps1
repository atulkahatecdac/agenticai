# Usage: .\switch.ps1 green   |   .\switch.ps1 blue
param([Parameter(Mandatory)][ValidateSet("blue", "green")][string]$Color)
Set-Location $PSScriptRoot
# 1. Never switch to a version that is not ready.
docker compose exec -T $Color python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/ready', timeout=2)"
if ($LASTEXITCODE -ne 0) { Write-Error "$Color is not ready - staying where we are"; exit 1 }
# 2. Point the upstream at the new colour and reload nginx (graceful).
Set-Content -Path active.conf -Value "upstream live { server ${Color}:8000; }" -NoNewline
docker compose exec -T proxy nginx -s reload
Write-Host "Live traffic -> $Color"
