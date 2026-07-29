param([string]$Destination = ".\backups")
$ErrorActionPreference = "Stop"
$workspace = (Resolve-Path ".").Path
$source = Join-Path $workspace "backend\storage\seo.sqlite3"
$targetRoot = [System.IO.Path]::GetFullPath((Join-Path $workspace $Destination))
if (-not $targetRoot.StartsWith($workspace)) { throw "O destino deve permanecer dentro do workspace." }
New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$target = Join-Path $targetRoot "seo-$stamp.sqlite3"
Copy-Item -LiteralPath $source -Destination $target
Get-FileHash -Algorithm SHA256 -LiteralPath $target | Format-List Path,Hash
