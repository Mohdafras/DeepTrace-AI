param([switch]$ReuseBackend)
$ErrorActionPreference = 'Stop'
$backend = Join-Path $PSScriptRoot 'backend'
$frontend = Join-Path $PSScriptRoot 'deeptrace-ai---deepfake-image-detection-&-forensics'
$python = Join-Path $backend '.venv\Scripts\python.exe'

if (-not (Test-Path $python)) { throw 'Create backend/.venv and install backend/requirements.txt first; see README.md.' }
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) { throw 'Run npm ci in the frontend directory first; see README.md.' }
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw 'Node.js/npm is required.' }

function Test-LocalPort([int]$port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $pending = $client.ConnectAsync('127.0.0.1', $port)
        if (-not $pending.Wait(500)) { return $false }
        return $client.Connected
    } catch { return $false } finally { $client.Dispose() }
}

function Open-Terminal([string]$command) {
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
    Start-Process powershell.exe -ArgumentList @('-NoProfile', '-NoExit', '-EncodedCommand', $encoded) | Out-Null
}

if (Test-LocalPort 5173) { throw 'Port 5173 is already occupied. Use the existing frontend or stop it yourself before retrying.' }
if (Test-LocalPort 8002) {
    if (-not $ReuseBackend) { throw 'Port 8002 is occupied. If it is this project backend, rerun with -ReuseBackend; no process was stopped.' }
    $health = Invoke-RestMethod 'http://127.0.0.1:8002/api/v1/health' -TimeoutSec 10
    if (-not $health.model_loaded) { throw 'Existing backend is reachable but its model is not loaded. Inspect its terminal.' }
    Write-Host 'Reusing the backend you selected on port 8002.'
} else {
    $backendQuoted = $backend.Replace("'", "''")
    $pythonQuoted = $python.Replace("'", "''")
    Open-Terminal "Set-Location '$backendQuoted'; & '$pythonQuoted' -m uvicorn main:app --host 127.0.0.1 --port 8002 --reload"
}
$frontendQuoted = $frontend.Replace("'", "''")
Open-Terminal "Set-Location '$frontendQuoted'; npm.cmd run dev"
Write-Host 'Frontend: http://localhost:5173'
Write-Host 'Backend:  http://127.0.0.1:8002'
Write-Host 'Swagger:  http://127.0.0.1:8002/docs'
Write-Host 'Wait for the terminals to report ready. Stop each service with Ctrl+C in its terminal.'
