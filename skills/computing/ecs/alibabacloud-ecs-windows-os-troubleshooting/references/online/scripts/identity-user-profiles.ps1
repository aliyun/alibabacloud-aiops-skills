$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: User Profile Status Check ---

try {
    Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\*' |
        Select-Object PSChildName, ProfileImagePath, State,
            @{N='HasBak';E={Test-Path -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$($_.PSChildName).bak"}} |
        Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step1 profile-list: " + $_.Exception.Message)
}

# --- Step 2: Folder Redirection Check ---

try {
    $profileList = Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\*' |
        Where-Object { $_.ProfileImagePath -like 'C:\Users\*' }
} catch {
    Write-Host ("ERROR step2 profile-list: " + $_.Exception.Message)
}
foreach ($profile in $profileList) {
    try {
        $sid = $profile.PSChildName
        $regPath = "Registry::HKU\$sid\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        $regItem = Get-Item -Path $regPath
        if ($regItem) {
            Write-Host "--- User: $($profile.ProfileImagePath) (SID: $sid) ---"
            $names = @('Desktop', 'Personal', 'My Pictures', '{374DE290-123F-4565-9164-39C4925E467B}')
            foreach ($name in $names) {
                $raw = $regItem.GetValue($name, $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
                $expanded = if ($raw) { $raw -replace '%USERPROFILE%', $profile.ProfileImagePath } else { '(not set)' }
                Write-Host "  ${name}: $expanded"
            }
            $desktopRaw = $regItem.GetValue('Desktop', $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
            if ($desktopRaw) {
                $desktopExpanded = $desktopRaw -replace '%USERPROFILE%', $profile.ProfileImagePath
                Write-Host "  Desktop accessible: $(Test-Path -Path $desktopExpanded)"
            }
        } else {
            Write-Host "--- User: $($profile.ProfileImagePath) - Shell Folders not loaded (user not logged on) ---"
        }
    } catch {
        Write-Host ("ERROR step2 shell-folders-" + $profile.PSChildName + ": " + $_.Exception.Message)
    }
}

# --- Step 3: Custom/Default User Profile WebCache Check ---

try {
    Get-WinEvent -FilterHashtable @{LogName='Application'; Id=454} -MaxEvents 10 |
        Select-Object TimeCreated, Message |
        Format-List
} catch {
    Write-Host ("ERROR step3 webcache-events: " + $_.Exception.Message)
}
