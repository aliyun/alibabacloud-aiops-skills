$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}

# --- Step 1: Check Root Certificate Status ---
try {
    $currentDate = Get-Date
    $rootCerts = Get-ChildItem -Path Cert:\LocalMachine\Root
    $expired = $rootCerts | Where-Object { $_.NotAfter -lt $currentDate }
    $expiringSoon = $rootCerts | Where-Object { $_.NotAfter -gt $currentDate -and $_.NotAfter -lt $currentDate.AddDays(30) }
    Write-Host "Total root certificates: $($rootCerts.Count)"
    Write-Host "Expired certificates: $($expired.Count)"
    Write-Host "Expiring within 30 days: $($expiringSoon.Count)"
    if ($expired) {
        Write-Host "`nExpired root certificates:"
        $expired | Select-Object Subject, NotAfter, Thumbprint | Format-Table -AutoSize
    }
    if ($expiringSoon) {
        Write-Host "`nExpiring soon:"
        $expiringSoon | Select-Object Subject, NotAfter, Thumbprint | Format-Table -AutoSize
    }
    $criticalThumbprints = @(
        'A43489159A520F0D93D032CCAF37E7FE20A8B419',  # Microsoft Root Certificate Authority 2011
        '3B1EFD3A66EA28B16697394703A72CA340A05BD5'   # Microsoft Root Certificate Authority 2010
    )
    foreach ($tp in $criticalThumbprints) {
        $cert = $rootCerts | Where-Object { $_.Thumbprint -eq $tp }
        if ($cert) {
            Write-Host "Critical root cert [$tp]: Present, NotAfter=$($cert.NotAfter)"
        } else {
            Write-Host "Critical root cert [$tp]: MISSING"
        }
    }
} catch {
    Write-Host ("ERROR step1 root-certs: " + $_.Exception.Message)
}

# --- Step 2: Check Certificate Chain Integrity ---
try {
    $intermediateCerts = Get-ChildItem -Path Cert:\LocalMachine\CA
    $expiredCA = @($intermediateCerts | Where-Object { $_.NotAfter -lt $currentDate })
    Write-Host "Intermediate certificates: $($intermediateCerts.Count)"
    Write-Host "Expired intermediate certificates: $($expiredCA.Count)"
    if ($expiredCA.Count -gt 0 -and $expiredCA.Count -le 10) {
        $expiredCA | Select-Object Subject, Issuer, NotAfter | Format-Table -AutoSize
    }
    $personalCerts = Get-ChildItem -Path Cert:\LocalMachine\My
    foreach ($cert in $personalCerts) {
        $chain = New-Object System.Security.Cryptography.X509Certificates.X509Chain
        $chain.ChainPolicy.RevocationMode = [System.Security.Cryptography.X509Certificates.X509RevocationMode]::NoCheck
        $valid = $chain.Build($cert)
        if (-not $valid) {
            Write-Host "Certificate chain issue for: $($cert.Subject)"
            Write-Host "  Thumbprint: $($cert.Thumbprint)"
            Write-Host "  NotAfter: $($cert.NotAfter)"
            foreach ($status in $chain.ChainStatus) {
                Write-Host "  ChainStatus: $($status.StatusInformation.Trim())"
            }
        }
    }
    if (-not $personalCerts) {
        Write-Host "No certificates in LocalMachine\My store"
    }
} catch {
    Write-Host ("ERROR step2 chain-integrity: " + $_.Exception.Message)
}

# --- Step 3: Check TLS Protocol Version/Cipher Suite ---
try {
    # Protocol subkeys/values are optional: absence means OS default behavior, which is
    # itself the finding -- read the whole key (null when absent) instead of erroring.
    $protocols = @('SSL 2.0','SSL 3.0','TLS 1.0','TLS 1.1','TLS 1.2','TLS 1.3')
    foreach ($proto in $protocols) {
        $clientPath = "HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\$proto\Client"
        $serverPath = "HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\$proto\Server"
        $clientKey = Get-ItemProperty -Path $clientPath
        $serverKey = Get-ItemProperty -Path $serverPath
        Write-Host "$proto - Client: Enabled=$($clientKey.Enabled),DisabledByDefault=$($clientKey.DisabledByDefault) | Server: Enabled=$($serverKey.Enabled),DisabledByDefault=$($serverKey.DisabledByDefault)"
    }
} catch {
    Write-Host ("ERROR step3 schannel-protocols: " + $_.Exception.Message)
}
try {
    $cipherPolicyPath = 'HKLM:\SOFTWARE\Policies\Microsoft\Cryptography\Configuration\SSL\00010002'
    if (Test-Path $cipherPolicyPath) {
        $cipherPolicy = (Get-ItemProperty -Path $cipherPolicyPath).Functions
        if ($cipherPolicy) {
            Write-Host "`nCipher suite policy (group policy):"
            Write-Host $cipherPolicy
        } else {
            Write-Host "`nNo cipher suite group policy configured (using system defaults)"
        }
    } else {
        Write-Host "`nNo cipher suite group policy configured (using system defaults)"
    }
} catch {
    Write-Host ("ERROR step3 cipher-policy: " + $_.Exception.Message)
}

# --- Step 4: Check Driver Signing Root Certificate ---
try {
    $driverSignCerts = @(
        @{Thumbprint='8FBE4D070EF8AB1BCCAF2A9D5CCAE7282A2C66B3'; Name='Microsoft Code Signing PCA 2011'},
        @{Thumbprint='CDD4EEAE6000AC7F40C3802C171E30148030C072'; Name='Microsoft Root Certificate Authority 2010'}
    )
    foreach ($c in $driverSignCerts) {
        $found = Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object { $_.Thumbprint -eq $c.Thumbprint }
        if (-not $found) {
            $found = Get-ChildItem -Path Cert:\LocalMachine\CA | Where-Object { $_.Thumbprint -eq $c.Thumbprint }
        }
        if ($found) {
            Write-Host "$($c.Name) [$($c.Thumbprint)]: Present, NotAfter=$($found.NotAfter)"
        } else {
            Write-Host "$($c.Name) [$($c.Thumbprint)]: MISSING"
        }
    }
} catch {
    Write-Host ("ERROR step4 driver-sign-certs: " + $_.Exception.Message)
}
try {
    # 'Policy' value is optional; absence means no driver signing override configured
    $driverSigningKey = Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Driver Signing'
    $driverSigning = $driverSigningKey.Policy
    Write-Host "Driver Signing Policy: $driverSigning (0=None, 1=Warn, 2=Block; blank = not configured)"
} catch {
    Write-Host ("ERROR step4 driver-signing-policy: " + $_.Exception.Message)
}
