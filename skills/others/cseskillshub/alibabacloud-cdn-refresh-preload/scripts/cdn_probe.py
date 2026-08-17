#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cdn_probe.py — Local probe script for CDN diagnostics (READ-ONLY)
=================================================================
Executes diagnostic commands locally via subprocess as an argv list.

Security model (command-injection hardened; the skill is declared read-only):
  1. No shell: the input string is parsed with shlex.split() and executed as
     a subprocess argv list with shell=False; shell features (pipes, command
     chaining, substitution) are never available to the input.
  2. Raw-input pre-check: any input containing shell metacharacters
     (; | & $ ` > < newline) is rejected before parsing.
  3. Binary whitelist: only curl / dig / openssl may be executed; every
     other binary is refused with a clear error and a fix hint.
  4. curl is restricted to read-only GET/HEAD requests: body/upload/output
     flags (-d/--data*, -F/--form*, -T/--upload-file, -o/--output, -O, -J,
     -K/--config, -C, -D/--dump-header, -b/--cookie) are rejected, URL
     positionals are restricted to http:// and https:// schemes, and
     -X/--request accepts only GET/HEAD (default curl behavior without -X
     is GET, or HEAD with -I).
  5. dig is passed through (DNS lookup only). openssl is restricted to the
     `s_client` subcommand (read-only TLS handshake inspection, e.g.
     `openssl s_client -connect host:443`); file-writing flags
     (-out/-keyout/-sess_out/-export) are rejected, and every other openssl
     subcommand (genrsa/req/x509/...) is refused.

Exit codes:
  0    success
  1    runtime error
  2    rejected by security policy
  124  timeout
  127  binary not found on PATH

Usage:
  python3 cdn_probe.py "<command>"
  python3 cdn_probe.py "curl -ksI https://example.com"
  python3 cdn_probe.py "dig example.com +short"
"""

import json
import re
import shlex
import subprocess
import sys

# ------------------------------ policy constants ----------------------------

ALLOWED_BINARIES = {"curl", "dig", "openssl"}

# openssl subcommands allowed (read-only diagnostics only).
OPENSSL_ALLOWED_SUBCMDS = {"s_client"}

# openssl flags that write local files.
OPENSSL_WRITE_FLAGS = {"-out", "-keyout", "-sess_out", "-export"}

# Shell metacharacters that must never appear in a probe command.
FORBIDDEN_CHARS = set(";|&$`><\n\r")

# curl flags that perform writes (request body, upload, local file output)
# or can smuggle arbitrary options (-K reads a config file).
CURL_WRITE_FLAGS = {
    "-d", "--data", "--data-raw", "--data-binary", "--data-urlencode",
    "--data-ascii",
    "-F", "--form", "--form-string", "--form-escape",
    "-T", "--upload-file",
    "-o", "--output", "-O", "--remote-name",
    "-J", "--remote-header-name",
    "-K", "--config",
    "-C", "--continue-at",
    "-D", "--dump-header",  # dumps response headers into a local file (write primitive)
    "-b", "--cookie",  # @file form reads arbitrary local files (info-leak primitive)
}

# Positional (URL) arguments to curl must use one of these schemes;
# file://, ftp://, dict://, gopher:// ... are all refused.
_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")
ALLOWED_URL_SCHEMES = {"http", "https"}

# curl read-only flags that take a following value.
CURL_VALUE_FLAGS = {
    "-H", "--header",
    "-A", "--user-agent",
    "-e", "--referer",
    "-w", "--write-out",
    "-m", "--max-time",
    "--connect-timeout",
    "--resolve",
    "--url",
    "-x", "--proxy",
    "-U", "--proxy-user",
    "--retry", "--retry-delay", "--retry-max-time",
    "--cacert", "--capath", "--ciphers",
}

# curl boolean (no-value) read-only flags.
CURL_BOOL_FLAGS = {
    "-s", "--silent", "-S", "--show-error",
    "-k", "--insecure",
    "-I", "--head",
    "-i", "--include",
    "-v", "--verbose",
    "-L", "--location",
    "--compressed",
    "-N", "--no-buffer",
    "-g", "--globoff",
    "-f", "--fail",
    "-4", "--ipv4", "-6", "--ipv6",
    "--http1.1", "--http2",
    "--tlsv1.2", "--tlsv1.3",
    "--no-progress-meter", "-#", "--progress-bar",
    "--raw", "--tcp-nodelay", "--path-as-is",
}

ALLOW_HINT = ("Only read-only diagnostics are permitted: "
              "curl (GET/HEAD only), dig, openssl.")
CURL_FLAG_HINT = ("Use read-only probes such as 'curl -ksI <url>' with common "
                  "read-only flags (-s -S -k -I -i -H -A -w --max-time --resolve ...).")


class ProbeError(Exception):
    """Raised when a probe command violates the security policy."""

    def __init__(self, reason, hint=""):
        super().__init__(reason)
        self.reason = reason
        self.hint = hint


# ------------------------------ validation ----------------------------------

def _validate_curl_method(method):
    if method.upper() not in ("GET", "HEAD"):
        raise ProbeError(
            f"curl method '{method or '<missing>'}' is not allowed (-X/--request)",
            "Only read-only requests are permitted: -X GET or -X HEAD "
            "(or omit -X entirely; default is GET, -I implies HEAD).",
        )


def _reject_write_flag(tok):
    raise ProbeError(
        f"curl flag '{tok}' performs a write/upload and is not allowed",
        CURL_FLAG_HINT,
    )


def _reject_unknown_flag(tok):
    raise ProbeError(f"unknown curl flag '{tok}'", CURL_FLAG_HINT)


def _validate_url_scheme(tok):
    """Positional/URL arguments may only use http:// or https:// schemes."""
    m = _SCHEME_RE.match(tok)
    if m:
        scheme = m.group(0)[:-1].lower()
        if scheme not in ALLOWED_URL_SCHEMES:
            raise ProbeError(
                f"URL scheme '{scheme}://' is not allowed",
                "Only http:// and https:// URLs are permitted for probes.",
            )


def _validate_curl(argv):
    """Ensure the curl invocation is a read-only GET/HEAD request."""
    args = argv[1:]
    i = 0
    while i < len(args):
        tok = args[i]
        if not tok.startswith("-"):
            _validate_url_scheme(tok)  # URL / positional argument
            i += 1
            continue

        # --- method restriction: -X / --request => GET or HEAD only ---
        if tok in ("-X", "--request"):
            method = args[i + 1] if i + 1 < len(args) else ""
            _validate_curl_method(method)
            i += 2
            continue
        if tok.startswith("--request="):
            _validate_curl_method(tok.split("=", 1)[1])
            i += 1
            continue
        if tok.startswith("-X") and len(tok) > 2:  # combined form, e.g. -XGET
            _validate_curl_method(tok[2:])
            i += 1
            continue

        # --- explicit write/upload flags ---
        if tok in CURL_WRITE_FLAGS or tok.startswith("--data") or tok.startswith("--form"):
            _reject_write_flag(tok)

        # --- long flags ---
        if tok.startswith("--"):
            if "=" in tok:
                flag = tok.split("=", 1)[0]
                if flag in CURL_WRITE_FLAGS or flag.startswith("--data") or flag.startswith("--form"):
                    _reject_write_flag(flag)
                if flag not in CURL_VALUE_FLAGS:
                    _reject_unknown_flag(flag)
                i += 1
                continue
            if tok in CURL_VALUE_FLAGS:
                if tok == "--url" and i + 1 < len(args):
                    _validate_url_scheme(args[i + 1])
                i += 2
                continue
            if tok in CURL_BOOL_FLAGS:
                i += 1
                continue
            _reject_unknown_flag(tok)

        # --- combined short flags, e.g. -ksI ---
        if len(tok) > 2:
            chars = tok[1:]
            consumes_value = False
            for idx, ch in enumerate(chars):
                flag = "-" + ch
                is_last = idx == len(chars) - 1
                if flag in CURL_WRITE_FLAGS:
                    _reject_write_flag(flag)
                if flag in CURL_VALUE_FLAGS:
                    if not is_last:
                        raise ProbeError(
                            f"curl flag '{flag}' requires a value and cannot be combined here",
                            CURL_FLAG_HINT,
                        )
                    consumes_value = True
                elif flag not in CURL_BOOL_FLAGS:
                    _reject_unknown_flag(flag)
            i += 2 if consumes_value else 1
            continue

        # --- single short flag ---
        if tok in CURL_WRITE_FLAGS:
            _reject_write_flag(tok)
        if tok in CURL_VALUE_FLAGS:
            i += 2
            continue
        if tok in CURL_BOOL_FLAGS:
            i += 1
            continue
        _reject_unknown_flag(tok)


def _validate_openssl(argv):
    """Restrict openssl to the read-only s_client subcommand."""
    subcmd = argv[1] if len(argv) > 1 else "<missing>"
    if subcmd not in OPENSSL_ALLOWED_SUBCMDS:
        raise ProbeError(
            f"openssl subcommand '{subcmd}' is not allowed",
            "Only 'openssl s_client' (read-only TLS inspection) is permitted.",
        )
    for tok in argv[2:]:
        flag = tok.split("=", 1)[0] if "=" in tok else tok
        if flag in OPENSSL_WRITE_FLAGS:
            raise ProbeError(
                f"openssl flag '{tok}' writes files and is not allowed",
                "Use read-only inspection, e.g. 'openssl s_client -connect host:443'.",
            )


def validate_command(raw):
    """Validate the raw command string; return the argv list if allowed.

    Raises ProbeError with a human-readable reason and fix hint otherwise.
    """
    if not raw or not raw.strip():
        raise ProbeError(
            "empty command",
            "Provide one probe command, e.g. 'curl -ksI https://example.com'.",
        )

    # Pre-check: refuse any shell metacharacter outright.
    bad = FORBIDDEN_CHARS & set(raw)
    if bad:
        shown = ", ".join(repr(c) for c in sorted(bad))
        raise ProbeError(
            f"shell metacharacters not allowed in probe input: {shown}",
            "This probe runs commands without a shell; "
            "use a single plain curl/dig/openssl command.",
        )

    try:
        argv = shlex.split(raw)
    except ValueError as e:
        raise ProbeError(
            f"unparseable command: {e}",
            "Check quoting; use a single plain curl/dig/openssl command.",
        )
    if not argv:
        raise ProbeError(
            "empty command",
            "Provide one probe command, e.g. 'curl -ksI https://example.com'.",
        )

    # Only bare command names are accepted: reject any path form to rule out
    # /tmp/evil/curl and symlink bypasses.
    if "/" in argv[0] or "\\" in argv[0]:
        raise ProbeError(
            f"binary path '{argv[0]}' is not allowed",
            "Only bare command names are supported: curl, dig, openssl.",
        )

    binary = argv[0]
    if binary not in ALLOWED_BINARIES:
        raise ProbeError(f"binary '{binary}' is not allowed", ALLOW_HINT)

    if binary == "curl":
        _validate_curl(argv)
    elif binary == "openssl":
        _validate_openssl(argv)
    # dig: passed through (DNS lookup only).
    return argv


# ------------------------------ execution -----------------------------------

def local_exec(argv, timeout=60):
    """Execute a validated argv list locally (argv list, never a shell)."""
    try:
        result = subprocess.run(
            argv, shell=False, capture_output=True, text=True, timeout=timeout,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"Command timed out after {timeout}s", "exit_code": 124}
    except FileNotFoundError:
        return {"stdout": "", "stderr": f"binary '{argv[0]}' not found on PATH", "exit_code": 127}
    except Exception as e:
        return {"error": str(e), "exit_code": -1}


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 cdn_probe.py \"<command>\"", file=sys.stderr)
        print("Example: python3 cdn_probe.py \"curl -ksI https://example.com\"", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]
    try:
        timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    except ValueError:
        print("Error: timeout must be an integer (seconds)", file=sys.stderr)
        sys.exit(1)
    if timeout <= 0:
        print("Error: timeout must be a positive integer (seconds)", file=sys.stderr)
        sys.exit(1)

    try:
        argv = validate_command(command)
    except ProbeError as e:
        print(f"Rejected: {e.reason}", file=sys.stderr)
        if e.hint:
            print(f"Hint: {e.hint}", file=sys.stderr)
        sys.exit(2)

    result = local_exec(argv, timeout)

    # Output results
    if result.get("stdout"):
        print(result["stdout"], end="")
    if result.get("stderr"):
        print(result["stderr"], end="", file=sys.stderr)

    exit_code = result.get("exit_code", -1)
    if "error" in result and not result.get("stdout"):
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
