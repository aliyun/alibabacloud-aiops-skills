#!/usr/bin/env python3
"""
Certificate Chain Completeness Checker and Fixer

Checks local PEM certificate bundles and fetches missing intermediate certificates.

Usage:
    # Check a local PEM file
    python3 fix_certchain.py --file cert.pem

    # Auto-fix a local PEM file
    python3 fix_certchain.py --file cert.pem --fix --output complete_chain.pem
"""

import argparse
import http.client
import ipaddress
import os
import re
import socket
import ssl
import subprocess
import sys
import tempfile
import urllib.parse
from typing import Optional

MAX_CERTIFICATE_DOWNLOAD_BYTES = 1024 * 1024


def run_openssl(args, stdin_data=None):
    """Run an openssl command and return (stdout, stderr, returncode)."""
    proc = subprocess.run(
        ["openssl"] + args,
        input=stdin_data,
        capture_output=True,
        timeout=30,
    )
    return proc.stdout, proc.stderr, proc.returncode


def split_pem_certs(pem_data):
    """Split a PEM bundle into individual certificate strings."""
    pattern = r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----"
    return re.findall(pattern, pem_data, re.DOTALL)


def get_cert_field(cert_pem, field):
    """Get a field (subject/issuer) from a PEM certificate."""
    stdout, _, rc = run_openssl(
        ["x509", "-noout", f"-{field}", "-nameopt", "utf8,sep_comma_plus_space"],
        stdin_data=cert_pem.encode(),
    )
    if rc != 0:
        return "unknown"
    return stdout.decode().strip()


def extract_cn(field_str):
    """Extract CN from a subject/issuer string."""
    match = re.search(r"CN\s*=\s*([^,/]+)", field_str)
    return match.group(1).strip() if match else field_str


def get_cert_subject_cn(cert_pem):
    return extract_cn(get_cert_field(cert_pem, "subject"))


def get_cert_issuer_cn(cert_pem):
    return extract_cn(get_cert_field(cert_pem, "issuer"))


def is_self_signed(cert_pem):
    """Check if a certificate is self-signed (root CA)."""
    subject = get_cert_field(cert_pem, "subject").replace("subject=", "").strip()
    issuer = get_cert_field(cert_pem, "issuer").replace("issuer=", "").strip()
    return subject == issuer


def is_known_root_issuer(issuer_cn):
    """Check if an issuer CN is a well-known root CA."""
    return issuer_cn.lower() in KNOWN_ROOT_ISSUERS


def get_aia_url(cert_pem):
    """Extract the CA Issuers URL from the AIA extension of a certificate."""
    stdout, _, rc = run_openssl(
        ["x509", "-noout", "-ext", "authorityInfoAccess"],
        stdin_data=cert_pem.encode(),
    )
    if rc != 0:
        return None
    output = stdout.decode()
    match = re.search(r"CA\s+Issuers\s+-\s+URI:(\S+)", output)
    if match:
        return match.group(1).strip()
    return None


def resolve_public_certificate_url(url):
    """Parse an AIA URL and resolve it once to public IP addresses."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return None
        if not parsed.hostname or parsed.username or parsed.password:
            return None
        if parsed.port not in {None, 80, 443}:
            return None

        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            addresses = [ipaddress.ip_address(parsed.hostname)]
        except ValueError:
            addresses = list({
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(
                    parsed.hostname,
                    port,
                    type=socket.SOCK_STREAM,
                )
            })

        if not addresses or not all(address.is_global for address in addresses):
            return None
        return parsed, port, addresses
    except (OSError, ValueError):
        return None


def is_safe_certificate_url(url):
    """Return whether an AIA URL resolves only to public HTTP(S) endpoints."""
    return resolve_public_certificate_url(url) is not None


def fetch_certificate(url):
    """Download a certificate from a DNS-pinned public AIA URL."""
    resolved = resolve_public_certificate_url(url)
    if not resolved:
        print(f"  [WARN] Rejected unsafe certificate URL: {url}", file=sys.stderr)
        return None

    parsed, port, addresses = resolved
    request_target = urllib.parse.urlunparse(
        ("", "", parsed.path or "/", parsed.params, parsed.query, "")
    )
    host_header = parsed.hostname
    if parsed.port and parsed.port != (443 if parsed.scheme == "https" else 80):
        host_header = f"{host_header}:{parsed.port}"

    last_error = None
    for address in addresses:
        connection = None
        try:
            if parsed.scheme == "https":
                raw_socket = socket.create_connection((str(address), port), timeout=15)
                tls_socket = ssl.create_default_context().wrap_socket(
                    raw_socket,
                    server_hostname=parsed.hostname,
                )
                connection = http.client.HTTPConnection(str(address), port, timeout=15)
                connection.sock = tls_socket
            else:
                connection = http.client.HTTPConnection(str(address), port, timeout=15)

            connection.request(
                "GET",
                request_target,
                headers={
                    "Host": host_header,
                    "User-Agent": "WAF-CertChainFixer/1.0",
                    "Accept": "application/pkix-cert, application/x-pem-file, */*",
                },
            )
            response = connection.getresponse()
            if response.status != 200:
                raise ValueError(f"HTTP {response.status}; redirects are not allowed")
            data = response.read(MAX_CERTIFICATE_DOWNLOAD_BYTES + 1)
            if len(data) > MAX_CERTIFICATE_DOWNLOAD_BYTES:
                raise ValueError("certificate response exceeds 1 MiB")

            if b"BEGIN CERTIFICATE" in data:
                return data.decode()

            stdout, _, rc = run_openssl(
                ["x509", "-inform", "DER", "-outform", "PEM"],
                stdin_data=data,
            )
            if rc == 0 and b"BEGIN CERTIFICATE" in stdout:
                return stdout.decode()
            raise ValueError("response is not a PEM or DER X.509 certificate")
        except Exception as exc:
            last_error = exc
        finally:
            if connection:
                connection.close()

    print(f"  [WARN] Failed to fetch {url}: {last_error}", file=sys.stderr)
    return None


def probe_remote_certs(domain, ip=None, port=443):
    """Connect to a remote server and retrieve the certificate chain."""
    target = ip or domain
    try:
        cmd = ["s_client", "-connect", f"{target}:{port}", "-servername", domain, "-showcerts"]
        proc = subprocess.run(
            ["openssl"] + cmd,
            input=b"\n",
            capture_output=True,
            timeout=15,
        )
        output = proc.stdout.decode(errors="replace")
        return split_pem_certs(output)
    except Exception as e:
        print(f"[ERROR] Failed to connect to {target}:{port}: {e}", file=sys.stderr)
        return []


def verify_chain_with_openssl(certs):
    """Cryptographically verify a PEM chain against roots or system trust."""
    if not certs:
        return False, "No certificates supplied"

    with tempfile.TemporaryDirectory() as temp_dir:
        leaf_path = os.path.join(temp_dir, "leaf.pem")
        with open(leaf_path, "w") as f:
            f.write(certs[0].strip() + "\n")

        intermediates = []
        roots = []
        for cert in certs[1:]:
            if is_self_signed(cert):
                roots.append(cert)
            else:
                intermediates.append(cert)

        args = ["verify"]
        if roots:
            root_path = os.path.join(temp_dir, "roots.pem")
            with open(root_path, "w") as f:
                f.write("\n".join(cert.strip() for cert in roots) + "\n")
            args.extend(["-CAfile", root_path])

        if intermediates:
            intermediate_path = os.path.join(temp_dir, "intermediates.pem")
            with open(intermediate_path, "w") as f:
                f.write("\n".join(cert.strip() for cert in intermediates) + "\n")
            args.extend(["-untrusted", intermediate_path])

        args.append(leaf_path)
        stdout, stderr, rc = run_openssl(args)
        detail = (stdout + stderr).decode(errors="replace").strip()
        return rc == 0, detail


def check_chain(certs):
    """
    Analyze a certificate chain and report completeness.
    A chain is complete only when its subject/issuer order has no gaps and
    OpenSSL verifies signatures, CA constraints, validity, and trust.
    """
    result = {
        "total_certs": len(certs),
        "is_complete": False,
        "missing_intermediates": [],
        "chain_details": [],
        "server_cert": None,
        "has_root": False,
        "cryptographically_verified": False,
        "verification_error": None,
    }

    if not certs:
        result["verification_error"] = "No certificates supplied"
        return result

    result["server_cert"] = certs[0]

    for i, cert in enumerate(certs):
        detail = {
            "index": i,
            "subject_cn": get_cert_subject_cn(cert),
            "issuer_cn": get_cert_issuer_cn(cert),
            "is_self_signed": is_self_signed(cert),
        }
        result["chain_details"].append(detail)
        if detail["is_self_signed"]:
            result["has_root"] = True

    # Check chain linkage: each cert's issuer should match the next cert's subject
    for i in range(len(certs) - 1):
        issuer_cn = get_cert_issuer_cn(certs[i])
        next_subject_cn = get_cert_subject_cn(certs[i + 1])
        if issuer_cn.lower() != next_subject_cn.lower():
            result["missing_intermediates"].append({
                "after_index": i,
                "expected_issuer": issuer_cn,
                "found_subject": next_subject_cn,
            })

    verified, verification_detail = verify_chain_with_openssl(certs)
    result["cryptographically_verified"] = verified
    if not verified:
        result["verification_error"] = verification_detail or "OpenSSL verification failed"
        if len(certs) == 1 and not is_self_signed(certs[0]):
            result["missing_intermediates"].append({
                "after_index": 0,
                "expected_issuer": get_cert_issuer_cn(certs[0]),
                "found_subject": None,
            })

    result["is_complete"] = (
        len(result["missing_intermediates"]) == 0 and verified
    )
    return result


def fix_chain(certs):
    """
    Attempt to fix an incomplete certificate chain by fetching missing intermediates.
    Returns (complete_chain_pem, fetched_certs_info).
    """
    fixed_certs = list(certs)
    fetched_info = []
    max_iterations = 5

    for _ in range(max_iterations):
        analysis = check_chain(fixed_certs)
        if analysis["is_complete"]:
            break

        last_cert = fixed_certs[-1]
        if is_self_signed(last_cert):
            break

        issuer_cn = get_cert_issuer_cn(last_cert)

        # Fetch the issuer advertised by the certificate's validated AIA URL.
        # OpenSSL verification, not a static root-name list, decides completion.
        # Strategy 1: AIA URL from the last certificate
        aia_url = get_aia_url(last_cert)
        if aia_url:
            print(f"  Fetching intermediate from AIA: {aia_url}", file=sys.stderr)
            intermediate_pem = fetch_certificate(aia_url)
            if intermediate_pem:
                intermediate_certs = split_pem_certs(intermediate_pem)
                if intermediate_certs:
                    fetched_info.append({
                        "source": "AIA",
                        "url": aia_url,
                        "subject_cn": get_cert_subject_cn(intermediate_certs[0]),
                    })
                    fixed_certs.extend(intermediate_certs)
                    continue

        print(
            f"  [WARN] Cannot safely fetch intermediate for issuer: {issuer_cn}; "
            "use the issuer's official CA repository.",
            file=sys.stderr,
        )
        break

    complete_pem = "\n".join(c.strip() for c in fixed_certs)
    return complete_pem, fetched_info


def print_report(analysis):
    """Print a human-readable chain analysis report."""
    print(f"\n{'=' * 60}")
    print(f"  Certificate Chain Analysis")
    print(f"{'=' * 60}")
    print(f"  Total certificates in chain: {analysis['total_certs']}")
    print(f"  Chain status: {'COMPLETE' if analysis['is_complete'] else 'INCOMPLETE'}")
    print(f"  Contains root CA: {'Yes' if analysis['has_root'] else 'No (normal - browsers have roots built-in)'}")

    print(f"\n  Chain details:")
    for detail in analysis["chain_details"]:
        if detail["index"] == 0:
            role = "Server"
        elif detail["is_self_signed"]:
            role = "Root CA"
        else:
            role = "Intermediate"
        print(f"    [{detail['index']}] ({role})")
        print(f"        Subject: {detail['subject_cn']}")
        print(f"        Issuer:  {detail['issuer_cn']}")

    if analysis["missing_intermediates"]:
        print(f"\n  Missing intermediates:")
        for gap in analysis["missing_intermediates"]:
            if gap["found_subject"]:
                print(f"    After cert [{gap['after_index']}]: expected issuer '{gap['expected_issuer']}' "
                      f"but found '{gap['found_subject']}'")
            else:
                print(f"    After cert [{gap['after_index']}]: chain ends but issuer "
                      f"'{gap['expected_issuer']}' is not present")

    print(f"{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Check and fix SSL certificate chain completeness"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    # Legacy compatibility only: keep accepting remote-probe flags, but do not
    # advertise them as part of this Skill's supported interface.
    group.add_argument("--domain", help=argparse.SUPPRESS)
    group.add_argument("--file", help="Local PEM file to check")

    parser.add_argument("--ip", help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=443, help=argparse.SUPPRESS)
    parser.add_argument("--fix", action="store_true", help="Auto-fetch missing intermediates")
    parser.add_argument("--output", "-o", help="Output file for complete chain PEM")
    parser.add_argument("--json", action="store_true", help="Output analysis as JSON")

    args = parser.parse_args()

    if args.file and args.output:
        input_path = os.path.realpath(os.path.abspath(args.file))
        output_path = os.path.realpath(os.path.abspath(args.output))
        same_file = input_path == output_path
        if os.path.exists(input_path) and os.path.exists(output_path):
            same_file = same_file or os.path.samefile(input_path, output_path)
        if same_file:
            parser.error("--output must differ from --file to avoid overwriting input")

    # Load certificates
    if args.domain:
        print(f"Probing {args.domain}" + (f" via {args.ip}" if args.ip else "") + f":{args.port} ...", file=sys.stderr)
        certs = probe_remote_certs(args.domain, args.ip, args.port)
        if not certs:
            print("[ERROR] No certificates retrieved from remote server.", file=sys.stderr)
            sys.exit(1)
    else:
        with open(args.file, "r") as f:
            pem_data = f.read()
        certs = split_pem_certs(pem_data)
        if not certs:
            print("[ERROR] No certificates found in file.", file=sys.stderr)
            sys.exit(1)

    # Analyze chain
    analysis = check_chain(certs)

    def json_analysis(value):
        return {k: v for k, v in value.items() if k != "server_cert"}

    if not args.fix:
        if args.json:
            import json
            print(json.dumps(json_analysis(analysis), indent=2, ensure_ascii=False))
        else:
            print_report(analysis)
        sys.exit(0 if analysis["is_complete"] else 1)

    if not args.json:
        print_report(analysis)

    fetched = []
    if analysis["is_complete"]:
        complete_pem = "\n".join(c.strip() for c in certs)
        final_analysis = analysis
    else:
        print("Attempting to fetch missing intermediates...", file=sys.stderr)
        complete_pem, fetched = fix_chain(certs)
        final_analysis = check_chain(split_pem_certs(complete_pem))

    output_path = None
    if final_analysis["is_complete"] and args.output:
        with open(args.output, "w") as f:
            f.write(complete_pem + "\n")
        output_path = args.output
        print(f"Complete chain written to: {args.output}", file=sys.stderr)

    if args.json:
        import json
        payload = {
            "initial_analysis": json_analysis(analysis),
            "final_analysis": json_analysis(final_analysis),
            "fetched": fetched,
            "output": output_path,
        }
        if not args.output and final_analysis["is_complete"]:
            payload["pem"] = complete_pem
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        if fetched:
            print(f"\n  Fetched {len(fetched)} intermediate(s):", file=sys.stderr)
            for info in fetched:
                print(f"    - {info['subject_cn']} (from {info['source']}: {info['url']})", file=sys.stderr)
        print_report(final_analysis)
        if not args.output and final_analysis["is_complete"]:
            print(complete_pem)

    if final_analysis["is_complete"]:
        print("[OK] Certificate chain is now complete.", file=sys.stderr)
        sys.exit(0)

    print("[WARN] Chain still incomplete. Manual intervention may be required.", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
