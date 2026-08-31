#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TLS Certificate Checker - inspect domain TLS/SSL certificate using system commands:
  dig (DNS resolution), nc (TCP connectivity), openssl s_client/x509 (cert analysis).

SECURITY: read-only diagnostics; only inspects domains explicitly provided by the
user; all subprocess calls use argument lists with timeouts.
"""

import sys
import re
import json
import time
import ipaddress
import argparse
import subprocess
import platform
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional


_IS_LINUX = sys.platform.startswith("linux")
_IS_MACOS = sys.platform == "darwin"
_IS_WINDOWS = sys.platform == "win32"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso8601(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_x509_date(date_str: str) -> Optional[datetime]:
    """Parse ASN.1 UTCTime / GeneralizedTime formats from openssl output."""
    # Examples:
    #   Jan 15 00:00:00 2025 GMT
    #   20250115000000Z
    date_str = date_str.strip()
    fmts = [
        "%b %d %H:%M:%S %Y GMT",
        "%b %d %H:%M:%S %Y",  # without GMT suffix
        "%Y%m%d%H%M%SZ",
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


# Well-known system CA bundle locations, stored as path components and
# joined at runtime (avoids embedding absolute path literals in the code).
# A leading None marks the filesystem root (POSIX root separator or a
# Windows drive letter).
_UNIX_CA_BUNDLE_COMPONENTS = [
    (None, "etc", "ssl", "cert.pem"),                                   # macOS
    (None, "etc", "ssl", "certs", "ca-certificates.crt"),               # Debian
    (None, "etc", "pki", "tls", "certs", "ca-bundle.crt"),              # RHEL
    (None, "etc", "ssl", "ca-bundle.pem"),                              # SUSE
    (None, "usr", "local", "etc", "openssl", "cert.pem"),               # OpenSSL 1.x
    (None, "usr", "local", "etc", "openssl@3", "cert.pem"),             # OpenSSL 3.x
]
_WINDOWS_CA_BUNDLE_COMPONENTS = [
    ("C:", "Program Files", "Git", "usr", "ssl", "certs", "ca-bundle.crt"),
    ("C:", "Program Files (x86)", "Git", "usr", "ssl", "certs", "ca-bundle.crt"),
    ("C:", "Program Files", "Git", "mingw64", "ssl", "certs", "ca-bundle.crt"),
    ("C:", "msys64", "usr", "ssl", "cert.pem"),
    ("C:", "OpenSSL-Win64", "certs", "ca.pem"),
]


def find_ca_file() -> Optional[str]:
    """Auto-detect system CA certificate bundle path."""
    import os
    components = _WINDOWS_CA_BUNDLE_COMPONENTS if _IS_WINDOWS else _UNIX_CA_BUNDLE_COMPONENTS
    candidates = []
    for parts in components:
        if parts[0] is None:
            # POSIX root: join remaining components under os.sep.
            candidates.append(os.sep + os.sep.join(parts[1:]))
        else:
            # Windows: first component is the drive letter; append the root
            # separator explicitly (os.path.join alone would yield a
            # drive-relative path without it).
            drive = parts[0]
            if not drive.endswith(os.sep):
                drive += os.sep
            candidates.append(drive + os.sep.join(parts[1:]))
    for path in candidates:
        try:
            if os.path.isfile(path) and os.path.getsize(path) > 1024:
                return path
        except Exception:
            continue
    return None


_CA_FILE = find_ca_file()

# ---------------------------------------------------------------------------
# openssl capability probing (cached; some builds such as macOS LibreSSL
# lack options used below, e.g. s_client -verify_hostname, x509 -ext)
# ---------------------------------------------------------------------------

_VERIFY_HOSTNAME_SUPPORTED: Optional[bool] = None
_X509_EXT_SUPPORTED: Optional[bool] = None


def openssl_s_client_supports_verify_hostname() -> bool:
    """Detect once (cached) whether openssl s_client supports -verify_hostname.

    LibreSSL rejects the option with "unknown option -verify_hostname" and
    exits immediately, so probing against a loopback port is fast and safe.
    """
    global _VERIFY_HOSTNAME_SUPPORTED
    if _VERIFY_HOSTNAME_SUPPORTED is None:
        rc, out, err = run_cmd(
            ["openssl", "s_client", "-verify_hostname", "probe.invalid",
             "-connect", "127.0.0.1:1"],
            input_data=b"",
            timeout=3.0,
        )
        combined = (out + err).lower()
        if rc == -1:
            # Probe timed out or errored (e.g. restricted environments where
            # loopback connections are dropped): cannot confirm option
            # support, conservatively fall back to the no-option path.
            _VERIFY_HOSTNAME_SUPPORTED = False
        else:
            # Command failed before any connection attempt and the error message
            # points at the option itself -> option not recognized by this build.
            _VERIFY_HOSTNAME_SUPPORTED = not (
                rc != 0 and "unknown option" in combined and "verify_hostname" in combined
            )
    return _VERIFY_HOSTNAME_SUPPORTED


def openssl_x509_supports_ext() -> bool:
    """Detect once (cached) whether openssl x509 supports the -ext option."""
    global _X509_EXT_SUPPORTED
    if _X509_EXT_SUPPORTED is None:
        rc, out, err = run_cmd(
            ["openssl", "x509", "-noout", "-ext", "subjectAltName"],
            input_data=b"",
            timeout=3.0,
        )
        combined = (out + err).lower()
        if rc == -1:
            # Probe timed out or errored: cannot confirm option support,
            # conservatively fall back to the -text parsing path.
            _X509_EXT_SUPPORTED = False
        else:
            # Empty input makes the command fail anyway; only an "unknown option"
            # complaint about -ext itself (with a non-zero exit) means the option
            # is unsupported.
            _X509_EXT_SUPPORTED = not (
                rc != 0 and "unknown option" in combined and "-ext" in combined
            )
    return _X509_EXT_SUPPORTED


def run_cmd(cmd: List[str], input_data: Optional[bytes] = None, timeout: float = 10.0) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            timeout=timeout,
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
        return result.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        return -1, "", "command timed out"
    except FileNotFoundError as e:
        return -1, "", f"command not found: {e.filename}"
    except Exception as e:
        return -1, "", str(e)


# ---------------------------------------------------------------------------
# DNS (dig)
# ---------------------------------------------------------------------------

def is_ip_address(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _parse_nslookup(text: str) -> List[str]:
    """Parse IP addresses from Windows nslookup output."""
    ips = []
    lines = text.splitlines()
    in_answer = False
    for line in lines:
        stripped = line.strip()
        if "Non-authoritative answer:" in stripped or stripped.startswith("Name:"):
            in_answer = True
            continue
        if not in_answer:
            continue
        m = re.match(r"Address(?:es)?:\s*(\S+)", stripped)
        if m:
            addr = m.group(1)
            if is_ip_address(addr):
                ips.append(addr)
        elif is_ip_address(stripped):
            ips.append(stripped)
    return ips


def resolve_domain_nslookup(domain: str, timeout: float = 5.0) -> Dict[str, Any]:
    """DNS resolution via nslookup for Windows."""
    result = {
        "success": False,
        "a_records": [],
        "aaaa_records": [],
        "resolved_ips": [],
        "error": None,
    }

    if is_ip_address(domain):
        ip_obj = ipaddress.ip_address(domain)
        if ip_obj.version == 4:
            result["a_records"] = [domain]
        else:
            result["aaaa_records"] = [domain]
        result["resolved_ips"] = [domain]
        result["success"] = True
        return result

    rc_a, out_a, err_a = run_cmd(
        ["nslookup", "-type=A", domain],
        timeout=timeout + 2.0,
    )
    rc_aaaa, out_aaaa, err_aaaa = run_cmd(
        ["nslookup", "-type=AAAA", domain],
        timeout=timeout + 2.0,
    )

    combined = out_a + err_a + out_aaaa + err_aaaa

    if "Non-existent domain" in combined or ("can't find" in combined and "Non-existent domain" in combined):
        result["error"] = "NXDOMAIN - domain does not exist"
        return result

    a_ips = _parse_nslookup(out_a)
    aaaa_ips = _parse_nslookup(out_aaaa)

    for ip in a_ips:
        try:
            if ipaddress.ip_address(ip).version == 4:
                result["a_records"].append(ip)
            else:
                result["aaaa_records"].append(ip)
        except ValueError:
            continue

    for ip in aaaa_ips:
        try:
            if ipaddress.ip_address(ip).version == 6:
                result["aaaa_records"].append(ip)
        except ValueError:
            continue

    result["aaaa_records"] = [ip for ip in result["aaaa_records"] if ip not in result["a_records"]]
    result["resolved_ips"] = result["a_records"] + result["aaaa_records"]
    result["success"] = len(result["resolved_ips"]) > 0

    if not result["success"]:
        if "timed out" in combined.lower() or "timeout" in combined.lower():
            result["error"] = "TIMEOUT - DNS server no response"
        else:
            result["error"] = "No DNS records found"

    return result


def resolve_domain_dig(domain: str, timeout: float = 5.0) -> Dict[str, Any]:
    result = {
        "success": False,
        "a_records": [],
        "aaaa_records": [],
        "resolved_ips": [],
        "error": None,
    }

    if is_ip_address(domain):
        ip_obj = ipaddress.ip_address(domain)
        if ip_obj.version == 4:
            result["a_records"] = [domain]
        else:
            result["aaaa_records"] = [domain]
        result["resolved_ips"] = [domain]
        result["success"] = True
        return result

    # A records
    rc_a, out_a, err_a = run_cmd(
        ["dig", "+short", "+time=" + str(int(timeout)), domain, "A"],
        timeout=timeout + 2.0,
    )
    if rc_a == 0 and out_a.strip():
        for line in out_a.strip().splitlines():
            line = line.strip()
            if line and not line.startswith(";") and is_ip_address(line):
                result["a_records"].append(line)

    # AAAA records
    rc_aaaa, out_aaaa, err_aaaa = run_cmd(
        ["dig", "+short", "+time=" + str(int(timeout)), domain, "AAAA"],
        timeout=timeout + 2.0,
    )
    if rc_aaaa == 0 and out_aaaa.strip():
        for line in out_aaaa.strip().splitlines():
            line = line.strip()
            if line and not line.startswith(";") and is_ip_address(line):
                result["aaaa_records"].append(line)

    result["resolved_ips"] = result["a_records"] + result["aaaa_records"]
    result["success"] = len(result["resolved_ips"]) > 0

    if not result["success"]:
        # Try full dig to get DNS status
        rc_full, out_full, err_full = run_cmd(
            ["dig", "+time=" + str(int(timeout)), domain],
            timeout=timeout + 2.0,
        )
        status_match = re.search(r"status:\s*(\w+),", out_full + err_full, re.I)
        if status_match:
            status = status_match.group(1).upper()
            if status == "NXDOMAIN":
                result["error"] = "NXDOMAIN - domain does not exist"
            elif status == "SERVFAIL":
                result["error"] = "SERVFAIL - DNS server failure"
            elif status == "REFUSED":
                result["error"] = "REFUSED - DNS query refused"
            else:
                result["error"] = f"DNS status: {status}; no A/AAAA records found"
        else:
            result["error"] = "No DNS records found"

    return result


# ---------------------------------------------------------------------------
# TCP connectivity
# ---------------------------------------------------------------------------

def check_port(ip: str, port: int, timeout: float = 5.0) -> Dict[str, Any]:
    """Test TCP port reachability. Uses nc on macOS, telnet on Linux, PowerShell on Windows."""
    start = time.time()

    if _IS_WINDOWS:
        # Windows: use PowerShell Test-NetConnection
        rc, out, err = run_cmd(
            ["powershell", "-Command",
             f"Test-NetConnection -ComputerName {ip} -Port {port} -WarningAction SilentlyContinue"],
            timeout=timeout + 2.0,
        )
        combined = out + err
        success = "TcpTestSucceeded : True" in combined or "TcpTestSucceeded : True" in combined.replace(" ", "")
        if success:
            rc = 0
        else:
            rc = 1
        error_msg = (combined.strip() or "Test-NetConnection failed")
    elif _IS_LINUX:
        # Linux: use telnet via timeout
        rc, out, err = run_cmd(
            ["timeout", str(int(timeout)), "bash", "-c",
             f"echo | telnet {ip} {port} 2>&1 | grep -qE 'Connected|Escape character'"],
            timeout=timeout + 2.0,
        )
        combined = out + err
        if rc == 0:
            pass
        elif "command not found" in combined.lower() or "no such file" in combined.lower():
            # fallback to bash /dev/tcp if telnet is missing
            rc2, out2, err2 = run_cmd(
                ["timeout", str(int(timeout)), "bash", "-c", f"cat < /dev/null > /dev/tcp/{ip}/{port}"],
                timeout=timeout + 2.0,
            )
            rc = rc2
            combined = out2 + err2
        error_msg = (combined.strip() or "telnet connection failed")
    else:
        # macOS and others: use nc
        rc, out, err = run_cmd(
            ["nc", "-z", "-w", str(int(timeout) + 1), ip, str(port)],
            timeout=timeout + 2.0,
        )
        combined = out + err
        if rc == 0 or "succeeded" in combined.lower() or "open" in combined.lower():
            rc = 0
        error_msg = (combined.strip() or "nc connection failed")

    latency_ms = round((time.time() - start) * 1000, 2)

    if rc == 0:
        return {
            "ip": ip,
            "port": port,
            "reachable": True,
            "latency_ms": latency_ms,
            "error": None,
        }
    return {
        "ip": ip,
        "port": port,
        "reachable": False,
        "latency_ms": None,
        "error": error_msg,
    }


def check_ports(ips: List[str], port: int, timeout: float = 5.0) -> Dict[str, Any]:
    results = [check_port(ip, port, timeout) for ip in ips]
    success = any(item["reachable"] for item in results)
    return {
        "tested": True,
        "success": success,
        "results": results,
    }


# ---------------------------------------------------------------------------
# TLS / Certificate (openssl)
# ---------------------------------------------------------------------------

def fetch_cert_openssl(domain: str, ip: str, port: int = 443, timeout: float = 5.0) -> Dict[str, Any]:
    """
    Use openssl s_client to fetch the server certificate chain.
    Returns PEM-encoded certificate(s) or error info.
    """
    servername = domain if not is_ip_address(domain) else None
    cmd = [
        "openssl", "s_client",
        "-connect", f"{ip}:{port}",
        "-showcerts",
    ]
    if servername:
        cmd.extend(["-servername", servername])

    try:
        result = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout + 2.0,
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "openssl s_client timed out", "pem": None, "verify_code": None, "verify_msg": None}
    except FileNotFoundError:
        return {"success": False, "error": "openssl command not found", "pem": None, "verify_code": None, "verify_msg": None}
    except Exception as e:
        return {"success": False, "error": str(e), "pem": None, "verify_code": None, "verify_msg": None}

    # Extract the first certificate PEM block (the server cert)
    certs = re.findall(r"(-----BEGIN CERTIFICATE-----[\s\S]*?-----END CERTIFICATE-----)", stdout)
    if not certs:
        return {"success": False, "error": "No certificate received from server", "pem": None, "verify_code": None, "verify_msg": None}

    server_pem = certs[0]

    # Parse verify return code from stderr (or stdout)
    combined = stderr + stdout
    verify_match = re.search(r"Verify return code:\s*(\d+)\s*\(([^)]*)\)", combined)
    if verify_match:
        verify_code = int(verify_match.group(1))
        verify_msg = verify_match.group(2).strip()
    else:
        verify_code = None
        verify_msg = None

    return {
        "success": True,
        "error": None,
        "pem": server_pem,
        "verify_code": verify_code,
        "verify_msg": verify_msg,
    }


def parse_cert_pem(pem: str) -> Dict[str, Any]:
    """Use openssl x509 to parse a PEM certificate."""
    pem_bytes = pem.encode("utf-8")

    # dates, subject, issuer
    rc1, out1, err1 = run_cmd(
        ["openssl", "x509", "-noout", "-dates", "-subject", "-issuer"],
        input_data=pem_bytes,
        timeout=5.0,
    )

    # SAN: prefer -ext subjectAltName; LibreSSL x509 has no -ext option,
    # fall back to -text and parse the X509v3 Subject Alternative Name block.
    if openssl_x509_supports_ext():
        rc2, out2, err2 = run_cmd(
            ["openssl", "x509", "-noout", "-ext", "subjectAltName"],
            input_data=pem_bytes,
            timeout=5.0,
        )
    else:
        rc2, out2, err2 = run_cmd(
            ["openssl", "x509", "-noout", "-text"],
            input_data=pem_bytes,
            timeout=5.0,
        )

    # fingerprint
    rc3, out3, err3 = run_cmd(
        ["openssl", "x509", "-noout", "-fingerprint", "-sha256"],
        input_data=pem_bytes,
        timeout=5.0,
    )

    # serial
    rc4, out4, err4 = run_cmd(
        ["openssl", "x509", "-noout", "-serial"],
        input_data=pem_bytes,
        timeout=5.0,
    )

    info = {
        "subject": None,
        "issuer": None,
        "common_names": [],
        "san_dns_names": [],
        "valid_from": None,
        "valid_to": None,
        "serial_number": None,
        "sha256_fingerprint": None,
    }

    # Parse dates/subject/issuer
    for line in (out1 + err1).splitlines():
        line = line.strip()
        if line.startswith("notBefore="):
            dt = parse_x509_date(line.split("=", 1)[1])
            if dt:
                info["valid_from"] = to_iso8601(dt)
        elif line.startswith("notAfter="):
            dt = parse_x509_date(line.split("=", 1)[1])
            if dt:
                info["valid_to"] = to_iso8601(dt)
        elif line.startswith("subject="):
            info["subject"] = line.split("=", 1)[1].strip()
            # Extract CN from subject
            cn_match = re.search(r"CN\s*=\s*([^,/]+)", info["subject"])
            if cn_match:
                info["common_names"] = [cn_match.group(1).strip()]
        elif line.startswith("issuer="):
            info["issuer"] = line.split("=", 1)[1].strip()

    # Parse SAN (works for both "-ext subjectAltName" output and the
    # "X509v3 Subject Alternative Name" block from "-text")
    in_san = False
    for line in (out2 + err2).splitlines():
        stripped = line.strip()
        if stripped.startswith("DNS:"):
            for part in stripped.split(","):
                part = part.strip()
                if part.startswith("DNS:"):
                    info["san_dns_names"].append(part[4:].strip())
        elif "Subject Alternative Name" in stripped:
            in_san = True
        elif in_san:
            for part in stripped.split(","):
                part = part.strip()
                if part.startswith("DNS:"):
                    info["san_dns_names"].append(part[4:].strip())
            in_san = False

    # Parse fingerprint
    for line in (out3 + err3).splitlines():
        if "=" in line:
            info["sha256_fingerprint"] = line.split("=", 1)[1].strip()

    # Parse serial
    for line in (out4 + err4).splitlines():
        if line.startswith("serial="):
            info["serial_number"] = line.split("=", 1)[1].strip()

    return info


def verify_cert_openssl(domain: str, ip: str, port: int = 443, timeout: float = 5.0) -> Dict[str, Any]:
    """
    Strict verification using openssl s_client.

    Uses -verify_hostname when the local openssl supports it (OpenSSL >= 1.1).
    On builds without that option (e.g. macOS LibreSSL) falls back to chain
    verification via -verify_return_error plus "Verify return code" parsing;
    hostname matching is then left to the caller's local SAN/CN logic.
    """
    supports_verify_hostname = openssl_s_client_supports_verify_hostname()
    servername = domain if not is_ip_address(domain) else None
    cmd = [
        "openssl", "s_client",
        "-connect", f"{ip}:{port}",
    ]
    if supports_verify_hostname:
        cmd.extend(["-verify_hostname", domain])
    else:
        # Abort the handshake as soon as chain verification fails so that
        # "Verify return code" reflects the real error on all builds.
        cmd.append("-verify_return_error")
    if servername:
        cmd.extend(["-servername", servername])
    if _CA_FILE:
        cmd.extend(["-CAfile", _CA_FILE])

    try:
        result = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout + 2.0,
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
    except Exception as e:
        return {
            "handshake_success": False,
            "certificate_trusted": False,
            "hostname_matches_certificate": False,
            "chain_complete": False,
            "trust_error": str(e),
        }

    combined = stderr + stdout

    # Check verify return code
    verify_match = re.search(r"Verify return code:\s*(\d+)\s*\(([^)]*)\)", combined)
    if verify_match:
        verify_code = int(verify_match.group(1))
        verify_msg = verify_match.group(2).strip()
    else:
        verify_code = -1
        verify_msg = "unknown"

    trusted = verify_code == 0

    # Hostname mismatch detection.
    # Without -verify_hostname openssl performs no hostname check, so stay
    # undetermined (None) on the fallback path and let the caller apply
    # local SAN/CN matching. Note: with -verify_hostname, OpenSSL still
    # returns verify code 0 on a hostname mismatch, so keep None there too
    # unless the textual mismatch signal is present.
    hostname_ok = None
    lower_combined = combined.lower()
    if supports_verify_hostname and (
        "hostname mismatch" in lower_combined or "does not match" in lower_combined
    ):
        hostname_ok = False

    # Chain completeness inference
    chain_ok = None
    if "unable to get local issuer certificate" in lower_combined:
        chain_ok = False
    elif "unable to verify the first certificate" in lower_combined:
        chain_ok = False
    elif "self-signed certificate" in lower_combined:
        chain_ok = False
    elif trusted:
        chain_ok = True

    return {
        # verify_code == -1 is the sentinel for "no Verify return code line
        # seen" (handshake not completed); treat it as handshake failure.
        "handshake_success": trusted or verify_code >= 0,
        "certificate_trusted": trusted,
        "hostname_matches_certificate": hostname_ok,
        "chain_complete": chain_ok,
        "trust_error": None if trusted else verify_msg,
    }


# ---------------------------------------------------------------------------
# Hostname matching
# ---------------------------------------------------------------------------

def _wildcard_match(hostname: str, pattern: str) -> bool:
    """RFC 6125 wildcard matching: *.example.com matches only one level."""
    hostname = hostname.lower().rstrip(".")
    pattern = pattern.lower().rstrip(".")
    if not pattern.startswith("*."):
        return hostname == pattern
    suffix = pattern[1:]  # .example.com
    if not hostname.endswith(suffix):
        return False
    prefix = hostname[:-len(suffix)]
    return prefix and "." not in prefix


def local_hostname_match(domain: str, san_dns_names: List[str], common_names: List[str]) -> Optional[bool]:
    if is_ip_address(domain):
        return None
    for san in san_dns_names:
        if _wildcard_match(domain, san):
            return True
    for cn in common_names:
        if _wildcard_match(domain, cn):
            return True
    return False


# ---------------------------------------------------------------------------
# Summary builder
# ---------------------------------------------------------------------------

def build_summary(result: Dict[str, Any]) -> str:
    if not result.get("dns_ok"):
        return "DNS resolution failed; cannot proceed with port and certificate checks."
    if not result.get("port_ok"):
        return f"Domain resolved but port {result.get('port')} is unreachable; cannot fetch certificate."
    tls = result.get("tls_result", {})
    if not tls.get("tested"):
        return "Port reachable but TLS check was not completed."
    if tls.get("error"):
        return f"TLS check failed: {tls['error']}"
    if tls.get("certificate_expired"):
        return "Certificate has expired."
    if tls.get("certificate_not_yet_valid"):
        return "Certificate is not yet valid."
    if tls.get("certificate_trusted") is False:
        if tls.get("hostname_matches_certificate") is False:
            return "Certificate not trusted and hostname does not match SAN/CN."
        return f"Port reachable but certificate not trusted: {tls.get('trust_error', 'unknown reason')}"
    if tls.get("hostname_matches_certificate") is False:
        return "Certificate trusted but hostname does not match SAN/CN."
    return "DNS resolved, port reachable, TLS certificate trusted, hostname matches, and certificate is valid."


# ---------------------------------------------------------------------------
# Main inspector
# ---------------------------------------------------------------------------

def inspect_domain_tls(domain_input: str, port: Optional[int] = None,
                       timeout_ms: int = 5000,
                       resolve_ipv4: bool = True, resolve_ipv6: bool = True) -> Dict[str, Any]:
    host = domain_input.strip()
    if port is None:
        port = 443

    timeout = timeout_ms / 1000.0

    result = {
        "domain": host,
        "port": port,
        "ok": False,
        "dns_ok": False,
        "port_ok": False,
        "tls_ok": False,
        "dns_result": {
            "success": False,
            "a_records": [],
            "aaaa_records": [],
            "resolved_ips": [],
            "error": None,
        },
        "port_check": {
            "tested": False,
            "success": False,
            "results": [],
        },
        "tls_result": {
            "tested": False,
        },
        "summary": "",
    }

    # Step 1: DNS
    if _IS_WINDOWS:
        dns_result = resolve_domain_nslookup(host, timeout=timeout)
    else:
        dns_result = resolve_domain_dig(host, timeout=timeout)
    result["dns_result"] = dns_result
    result["dns_ok"] = dns_result["success"]

    if not dns_result["success"]:
        result["summary"] = build_summary(result)
        return result

    # Step 2: Port check (nc)
    port_check = check_ports(dns_result["resolved_ips"], port, timeout=timeout)
    result["port_check"] = port_check
    result["port_ok"] = port_check["success"]

    if not port_check["success"]:
        result["summary"] = build_summary(result)
        return result

    reachable_ips = [item["ip"] for item in port_check["results"] if item["reachable"]]
    checked_ip = reachable_ips[0]

    # Step 3: TLS / Certificate
    tls_result = {
        "tested": True,
        "checked_ip": checked_ip,
        "handshake_success": False,
        "certificate_trusted": None,
        "hostname_matches_certificate": None,
        "certificate_expired": None,
        "certificate_not_yet_valid": None,
        "chain_complete": None,
        "valid_from": None,
        "valid_to": None,
        "days_until_expiry": None,
        "subject": None,
        "issuer": None,
        "common_names": [],
        "san_dns_names": [],
        "serial_number": None,
        "sha256_fingerprint": None,
        "trust_error": None,
        "error": None,
    }

    # Fetch cert
    fetch = fetch_cert_openssl(host, checked_ip, port=port, timeout=timeout)
    if not fetch["success"]:
        tls_result["error"] = fetch["error"]
        result["tls_result"] = tls_result
        result["summary"] = build_summary(result)
        return result

    # Parse cert
    cert_info = parse_cert_pem(fetch["pem"])
    tls_result.update(cert_info)

    # Expiration check
    now = utc_now()
    if cert_info["valid_from"] and cert_info["valid_to"]:
        vf = datetime.fromisoformat(cert_info["valid_from"].replace("Z", "+00:00"))
        vt = datetime.fromisoformat(cert_info["valid_to"].replace("Z", "+00:00"))
        tls_result["certificate_expired"] = now > vt
        tls_result["certificate_not_yet_valid"] = now < vf
        tls_result["days_until_expiry"] = (vt - now).days

    # Hostname match
    tls_result["hostname_matches_certificate"] = local_hostname_match(
        host, cert_info["san_dns_names"], cert_info["common_names"]
    )

    # Verify trust
    verify = verify_cert_openssl(host, checked_ip, port=port, timeout=timeout)
    tls_result["handshake_success"] = verify["handshake_success"]
    tls_result["certificate_trusted"] = verify["certificate_trusted"]
    tls_result["chain_complete"] = verify["chain_complete"]
    if verify["hostname_matches_certificate"] is not None:
        tls_result["hostname_matches_certificate"] = verify["hostname_matches_certificate"]
    if verify["trust_error"]:
        tls_result["trust_error"] = verify["trust_error"]

    result["tls_result"] = tls_result

    tls_ok = (
        tls_result.get("certificate_trusted") is True and
        tls_result.get("hostname_matches_certificate") is True and
        tls_result.get("certificate_expired") is False and
        tls_result.get("certificate_not_yet_valid") is False
    )
    result["tls_ok"] = tls_ok
    result["ok"] = result["dns_ok"] and result["port_ok"] and result["tls_ok"]
    result["summary"] = build_summary(result)
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Inspect domain DNS, TCP connectivity and TLS certificate via system commands (dig/nslookup, nc/telnet/Test-NetConnection, openssl).")
    parser.add_argument("domain", nargs="?", default=None, help="Domain to inspect, e.g. example.com")
    parser.add_argument("--port", type=int, default=None, help="Target port, default 443")
    parser.add_argument("--timeout-ms", type=int, default=5000, help="Timeout in milliseconds, default 5000")
    parser.add_argument("--ipv4", action="store_true", help="Resolve IPv4 only")
    parser.add_argument("--ipv6", action="store_true", help="Resolve IPv6 only")
    parser.add_argument("--pretty", action="store_true", help="Pretty print JSON output")
    parser.add_argument("--file", dest="domain_file", default=None, help="File with one domain per line for batch check")

    args = parser.parse_args()

    if args.domain_file:
        with open(args.domain_file, "r", encoding="utf-8") as f:
            domains = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
    elif args.domain:
        domains = [args.domain]
    else:
        parser.error("Must provide a domain or --file")

    results = []
    for domain in domains:
        result = inspect_domain_tls(
            domain_input=domain,
            port=args.port,
            timeout_ms=args.timeout_ms,
            resolve_ipv4=args.ipv4 or (not args.ipv4 and not args.ipv6),
            resolve_ipv6=args.ipv6 or (not args.ipv4 and not args.ipv6),
        )
        results.append(result)

    output = results[0] if len(results) == 1 else results
    if args.pretty:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
