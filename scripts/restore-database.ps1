param(
  [Parameter(Mandatory = $true)][string]$Backup,
  [switch]$ConfirmRestore
)
$ErrorActionPreference = "Stop"
if (-not $ConfirmRestore) { throw "Recuperação cancelada. Execute novamente com -ConfirmRestore." }
$workspace = (Resolve-Path ".").Path
$backupPath = (Resolve-Path -LiteralPath $Backup).Path
if (-not $backupPath.StartsWith($workspace)) { throw "O backup deve estar dentro do workspace." }
$database = Join-Path $workspace "backend\storage\seo.sqlite3"
$safety = "$database.before-restore-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
if (Test-Path -LiteralPath $database) { Copy-Item -LiteralPath $database -Destination $safety }
Copy-Item -LiteralPath $backupPath -Destination $database -Force
Write-Output "Base recuperada. Cópia de segurança anterior: $safety"
