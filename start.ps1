param(
    [int]$Port = 8000,
    [string]$HostAddress = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$env:PYTHONIOENCODING = "utf-8"
Write-Host "项目目录: $projectRoot"
Write-Host "访问地址: http://${HostAddress}:$Port"

python -m uvicorn app:app --host $HostAddress --port $Port
