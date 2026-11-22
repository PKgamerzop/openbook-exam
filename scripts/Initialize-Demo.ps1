# Run from any directory after the development database is migrated.
[CmdletBinding()]
param([switch]$Development)
$ErrorActionPreference = 'Stop'
if (-not $Development) { throw 'Pass -Development to initialize local demonstration data.' }
$project = Split-Path -Parent $PSScriptRoot
$directory = Join-Path $project '.local-demo'
[IO.Directory]::CreateDirectory($directory) | Out-Null
$vault = Join-Path $directory 'credential.dpapi'
if (-not (Test-Path -LiteralPath $vault)) {
    $bytes = New-Object byte[] 24
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    $secret = ConvertTo-SecureString ([Convert]::ToBase64String($bytes)) -AsPlainText -Force
    $encrypted = ConvertFrom-SecureString $secret
    $stream = [IO.File]::Open($vault, 'CreateNew', 'Write', 'None')
    try {
        $encoded = [Text.Encoding]::ASCII.GetBytes($encrypted)
        $stream.Write($encoded, 0, $encoded.Length)
    } finally { $stream.Dispose() }
}
$secret = ConvertTo-SecureString ([IO.File]::ReadAllText($vault))
$credential = [PSCredential]::new('demo_lecturer', $secret)
Push-Location (Join-Path $project 'backend')
try {
    $credential.GetNetworkCredential().Password | & '..\.venv\Scripts\python.exe' -m app.demo --development --password-stdin
    if ($LASTEXITCODE -ne 0) { throw 'Demo initialization failed.' }
    Write-Output 'The demo password is encrypted for your Windows user in .local-demo/credential.dpapi.'
} finally { Pop-Location }
