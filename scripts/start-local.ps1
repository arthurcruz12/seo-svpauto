$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

$storage = Join-Path $root "backend\storage"
New-Item -ItemType Directory -Force -Path $storage | Out-Null

$python = Join-Path $root "backend\.venv\Scripts\python.exe"
$npm = "npm.cmd"

if (-not (Test-Path $python)) {
  throw "Ambiente Python não encontrado em backend\.venv. Instale as dependências do backend primeiro."
}

if (-not (Test-Path (Join-Path $root "node_modules"))) {
  throw "Dependências do frontend não encontradas. Execute npm install primeiro."
}

if (-not (Test-Path (Join-Path $root "dist\index.html"))) {
  Write-Host "Build de produção não encontrado. A criar dist..."
  & $npm run build
}

$env:SEO_EXPOSE_DEV_MFA = "1"

$apiOut = Join-Path $storage "api.out.log"
$apiErr = Join-Path $storage "api.err.log"
$webOut = Join-Path $storage "frontend.out.log"
$webErr = Join-Path $storage "frontend.err.log"

function Start-SeoCommand {
  param(
    [string]$Command
  )

  $process = New-Object System.Diagnostics.Process
  $process.StartInfo = New-Object System.Diagnostics.ProcessStartInfo
  $process.StartInfo.FileName = "cmd.exe"
  $process.StartInfo.Arguments = "/d /s /c `"$Command`""
  $process.StartInfo.WorkingDirectory = $root
  $process.StartInfo.UseShellExecute = $false
  $process.StartInfo.CreateNoWindow = $true

  $started = $process.Start()
  if (-not $started) {
    throw "Não foi possível iniciar: $Command"
  }
  return $process.Id
}

$apiCommand = "set SEO_EXPOSE_DEV_MFA=1 && `"$python`" -m uvicorn backend.app.server:app --host 127.0.0.1 --port 8000 > `"$apiOut`" 2> `"$apiErr`""
$webCommand = "npm.cmd run preview -- --host 127.0.0.1 --port 5173 > `"$webOut`" 2> `"$webErr`""

$apiPid = Start-SeoCommand -Command $apiCommand
$webPid = Start-SeoCommand -Command $webCommand

Start-Sleep -Seconds 4

$apiOk = Test-NetConnection 127.0.0.1 -Port 8000 -InformationLevel Quiet
$webOk = Test-NetConnection 127.0.0.1 -Port 5173 -InformationLevel Quiet

Write-Host ""
Write-Host "SEO local"
Write-Host "API PID: $apiPid"
Write-Host "Web PID: $webPid"
Write-Host "API: http://127.0.0.1:8000/health"
Write-Host "Web: http://127.0.0.1:5173/"

if (-not $apiOk) {
  Write-Warning "A API não respondeu na porta 8000. Verifique backend\storage\api.err.log"
}

if (-not $webOk) {
  Write-Warning "O frontend não respondeu na porta 5173. Verifique backend\storage\frontend.err.log"
}
