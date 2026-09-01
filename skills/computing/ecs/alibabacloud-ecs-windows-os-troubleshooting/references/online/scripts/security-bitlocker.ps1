$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Check BitLocker Encryption Status ---
try {
    $bdeService = Get-Service -Name BDESVC
    Write-Host "BitLocker Service (BDESVC): Status=$($bdeService.Status), StartType=$($bdeService.StartType)"
} catch {
    Write-Host "BitLocker Service (BDESVC): Not installed"
}
try {
    $volumes = Get-CimInstance -Namespace 'Root\CIMV2\Security\MicrosoftVolumeEncryption' -ClassName 'Win32_EncryptableVolume'
    foreach ($vol in $volumes) {
        Write-Host "`nVolume: $($vol.DriveLetter)"
        Write-Host "  ProtectionStatus: $($vol.ProtectionStatus) (0=Off, 1=On, 2=Unknown)"
        Write-Host "  ConversionStatus: $($vol.ConversionStatus) (0=FullyDecrypted, 1=FullyEncrypted, 2=EncryptionInProgress, 3=DecryptionInProgress, 4=EncryptionPaused, 5=DecryptionPaused)"
        Write-Host "  EncryptionMethod: $($vol.EncryptionMethod)"
    }
} catch {
    Write-Host ("ERROR step1 encryptable-volume-wmi: " + $_.Exception.Message)
    Write-Host "BitLocker feature may not be installed on this edition"
}

# --- Step 2: Check Recovery Key Status ---
try {
    $volumes = Get-CimInstance -Namespace 'Root\CIMV2\Security\MicrosoftVolumeEncryption' -ClassName 'Win32_EncryptableVolume'
    foreach ($vol in $volumes) {
        if ($vol.ProtectionStatus -eq 1) {
            Write-Host "Volume $($vol.DriveLetter) is BitLocker encrypted"
            $protectors = $vol | Invoke-CimMethod -MethodName 'GetKeyProtectors'
            if ($protectors -and $protectors.VolumeKeyProtectorID) {
                Write-Host "  Key Protectors count: $($protectors.VolumeKeyProtectorID.Count)"
                foreach ($id in $protectors.VolumeKeyProtectorID) {
                    $type = $null
                    try {
                        $kpResult = $vol | Invoke-CimMethod -MethodName 'GetKeyProtectorType' -Arguments @{VolumeKeyProtectorID=$id}
                        $type = $kpResult.KeyProtectorType
                    } catch {
                        Write-Host ("ERROR step2 key-protector-type($id): " + $_.Exception.Message)
                    }
                    $typeNames = @{0='Unknown';1='TPM';2='ExternalKey';3='NumericalPassword';4='TPMAndPIN';5='TPMAndStartupKey';6='TPMAndPINAndStartupKey';7='PublicKey';8='Passphrase';9='TPMCertificate';10='CryptoAPI_NextGen'}
                    $typeName = if ($null -ne $type -and $typeNames.ContainsKey([int]$type)) { $typeNames[[int]$type] } else { "Type_$type" }
                    Write-Host "  Protector: ID=$id, Type=$typeName"
                }
            } else {
                Write-Host "  WARNING: No key protectors found"
            }
        }
    }
} catch {
    Write-Host ("ERROR step2 key-protectors: " + $_.Exception.Message)
}
try {
    # Check BitLocker related events
    # NOTE: filter ProviderName in FilterHashtable -- pulling the latest N entries of the
    # whole System log and filtering afterwards almost always returns nothing.
    Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-BitLocker-Driver'; Level=1,2,3; StartTime=(Get-Date).AddDays(-30)} -MaxEvents 20 |
        Select-Object TimeCreated, Id, LevelDisplayName, Message | Format-Table -AutoSize
} catch {
    Write-Host ("ERROR step2 bitlocker-events: " + $_.Exception.Message)
}
