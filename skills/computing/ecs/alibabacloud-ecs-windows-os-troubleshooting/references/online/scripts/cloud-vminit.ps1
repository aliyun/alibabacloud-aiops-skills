$ProgressPreference = 'SilentlyContinue'

$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: vminit Service Status Check ---
# Win32_Service.PathName contains both exe path and command-line arguments; must parse before Test-Path
try {
    $svc = Get-CimInstance -ClassName Win32_Service -Filter "Name='vminit'"
    if ($svc) {
        $rawPath = $svc.PathName
        # Strip surrounding quotes or trailing arguments to extract the pure .exe path
        if     ($rawPath -match '^"([^"]+)"')   { $exePath = $Matches[1] }
        elseif ($rawPath -match '^(\S+\.exe)')   { $exePath = $Matches[1] }
        else                                       { $exePath = $rawPath }
        [PSCustomObject]@{
            Name      = $svc.Name
            State     = $svc.State
            StartMode = $svc.StartMode
            PathName  = $rawPath
            ExePath   = $exePath
            Exists    = if ($exePath) { Test-Path -LiteralPath $exePath } else { $false }
        } | Format-List
    } else {
        Write-Host 'vminit service not found via Win32_Service'
    }
} catch {
    Write-Host ("ERROR step1 vminit-service: " + $_.Exception.Message)
}

# --- Step 2: vminit Initialization Log Check ---
try {
    $logPath = "$env:ProgramData\aliyun\vminit\log"
    $latestLog = Get-ChildItem $logPath -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latestLog) {
      Write-Host "LogFile: $($latestLog.FullName)"
      Get-Content $latestLog.FullName
    } else {
      Write-Host 'No vminit log file found'
    }
} catch {
    Write-Host ("ERROR step2 vminit-log: " + $_.Exception.Message)
}

# --- Step 3: user-data Interface Check ---
try {
  $resp = Invoke-WebRequest -Uri 'http://100.100.100.200/latest/user-data' -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
  Write-Host "HTTP Status: $($resp.StatusCode)"
  Write-Host "Content-Length: $($resp.Content.Length)"
  Write-Host '--- Content (first 500 chars) ---'
  $resp.Content.Substring(0, [Math]::Min(500, $resp.Content.Length))
} catch {
  Write-Host "ERROR step3 user-data: $($_.Exception.Message)"
}
