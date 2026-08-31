# Prerequisites

## System Dependencies

Install the following command-line tools before using this skill:

| Tool | Purpose | macOS | Linux (Debian/Ubuntu) | Linux (RHEL/CentOS) | Windows 10/11 |
|------|---------|-------|----------------------|---------------------|---------------|
| `openssl` | TLS handshake, cert parsing, trust verification | pre-installed | `apt install openssl` | `yum install openssl` | [OpenSSL for Windows](https://slproweb.com/products/Win32OpenSSL.html) |
| `dig` / `nslookup` | DNS resolution, status diagnosis | pre-installed (`dig`) | `apt install dnsutils` | `yum install bind-utils` | pre-installed (`nslookup`) |
| `nc` / `telnet` / `Test-NetConnection` | TCP port connectivity test | pre-installed (`nc`) | `apt install netcat-openbsd` | `yum install nmap-ncat` | pre-installed PowerShell (`Test-NetConnection`) |

## Windows OpenSSL Installation

Windows does not ship with `openssl` by default. Download and install the latest Win64 OpenSSL installer from [slproweb.com](https://slproweb.com/products/Win32OpenSSL.html). Direct link for the current stable build: [Win64OpenSSL-4_0_0.exe](https://slproweb.com/download/Win64OpenSSL-4_0_0.exe).

After installation, ensure `openssl.exe` is available in your system `PATH` so that `openssl` can be invoked from the command line.

## Environment Compatibility

| Platform | Minimum Version | Notes |
|----------|----------------|-------|
| macOS | 12+ (Monterey) | Homebrew openssl 3.x supported |
| Linux | kernel 4.19+ | glibc-based distributions |
| Windows | 10 / 11 | PowerShell 5.1+ required; openssl must be installed separately |

## Python

Python 3.9+ is required only if running the helper script in `scripts/check_tls.py`. No external Python packages are needed.

## CA Certificates

The tool auto-detects the system CA bundle from common paths:

**macOS / Linux:**
- `/etc/ssl/cert.pem`
- `/etc/ssl/certs/ca-certificates.crt`
- `/etc/pki/tls/certs/ca-bundle.crt`
- `/usr/local/etc/openssl/cert.pem`

**Windows:**
- `C:\OpenSSL-Win64\certs\ca.pem` (OpenSSL for Windows)

If auto-detection fails, export the path manually:

```bash
# macOS / Linux
export SSL_CERT_FILE=/path/to/ca-bundle.crt

# Windows (PowerShell)
$env:SSL_CERT_FILE = "C:\path\to\ca-bundle.crt"
```
