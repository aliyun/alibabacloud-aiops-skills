"""Outside-in verification of a domain's live HTTPS view.

This module never touches the cloud APIs and never runs inside the customer
instance. It plays the role of the visitor: it resolves the domain through
the system resolver, opens a TLS connection to port 443 with full
certificate verification ON, and reports exactly what the public internet
sees. That is the same first move a support engineer makes before asking
for any authorization: compare the served certificate and the resolved
address with what the customer believes is true.

Every routine here is information-only:

    * DNS resolution is a read; nothing is registered or changed.
    * The browser-grade verdict always comes from a fully verified handshake.
    * When that handshake rejects the certificate, a follow-up unverified
      handshake only reads the served certificate (subject/SAN/fingerprint)
      so the report can name it; it never changes the verdict.
    * A public DoH cross-check runs beside the system resolver, so a
      split-horizon answer or a TLS-inspecting proxy cannot pass itself off
      as the origin. When the two views differ, both are probed and reported.
    * All socket operations carry explicit timeouts, and any environment
      restriction (blocked egress, no resolver) degrades to a named
      ``blocked`` result instead of fabricating a certificate view.

Result dictionaries always carry a ``verdict`` key. The entry script maps
verdicts onto the triage branches; nothing in this module interprets them.
"""

import datetime
import hashlib
import json
import os
import re
import socket
import ssl
import tempfile
import threading
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from _constants import (
    DEFAULT_TLS_PORT,
    DNS_RESOLVE_TIMEOUT_SECONDS,
    EXPIRING_SOON_DAYS,
    TLS_CONNECT_TIMEOUT_SECONDS,
)

# Public DoH endpoints used only as a cross-check on the system resolver.
# Alibaba public DNS first (same ecosystem as the product), Google as fallback.
PUBLIC_DNS_ENDPOINTS = (
    "https://dns.alidns.com/resolve?name={0}&type=A",
    "https://dns.google/resolve?name={0}&type=A",
)
PUBLIC_DNS_TIMEOUT_SECONDS = 6

_MONTH_ABBREVIATIONS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_LEGACY_DATE_RE = re.compile(
    r"^([A-Za-z]{3,9})\s+(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})\s+(\d{4})\s*(?:GMT|UTC)?$",
    re.IGNORECASE)


def _parse_cert_date(text: Optional[str]) -> Optional[datetime.datetime]:
    """Parse one ssl peer-certificate date into an aware UTC datetime.

    Python spells these ISO 8601 UTC on recent interpreters and
    ``Mon DD HH:MM:SS YYYY GMT`` on older ones; ``strptime`` with ``%b``
    would resolve the month through the machine locale, so both spellings
    are handled here explicitly and an unparsable value returns ``None``
    rather than being guessed.
    """
    raw = (text or "").strip()
    if not raw:
        return None
    candidate = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.datetime.fromisoformat(candidate)
    except ValueError:
        parsed = None
    if parsed is not None:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed.astimezone(datetime.timezone.utc)
    match = _LEGACY_DATE_RE.match(raw)
    if not match:
        return None
    month = _MONTH_ABBREVIATIONS.get(match.group(1)[:3].lower())
    if month is None:
        return None
    try:
        return datetime.datetime(
            int(match.group(6)), month, int(match.group(2)),
            int(match.group(3)), int(match.group(4)), int(match.group(5)),
            tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


def _call_with_timeout(func, args, timeout, on_timeout=None):
    """Run ``func(*args)`` in a daemon worker and return a fixed value when
    the worker outlives ``timeout`` seconds. The daemon worker can never
    block the interpreter from exiting."""
    box: Dict[str, Any] = {}
    event = threading.Event()

    def runner():
        try:
            box["value"] = func(*args)
        except BaseException as exc:  # surfaced by the caller below
            box["error"] = exc
        finally:
            event.set()

    worker = threading.Thread(target=runner, daemon=True)
    worker.start()
    if event.wait(timeout):
        if "error" in box:
            raise box["error"]
        return box.get("value")
    return on_timeout


def resolve_domain(domain: str) -> Dict[str, Any]:
    """Resolve ``domain`` to its address list through the system resolver."""
    def _lookup():
        infos = socket.getaddrinfo(domain, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        return sorted({info[4][0] for info in infos})

    try:
        addresses = _call_with_timeout(
            _lookup, (), DNS_RESOLVE_TIMEOUT_SECONDS, on_timeout="TIMEOUT")
    except socket.gaierror as exc:
        return {"verdict": "dns-failed", "detail": str(exc), "addresses": []}
    except OSError as exc:
        return {"verdict": "dns-error", "detail": str(exc), "addresses": []}
    if addresses == "TIMEOUT":
        return {"verdict": "blocked",
                "detail": "resolver gave no answer within the time budget",
                "addresses": []}
    if not addresses:
        return {"verdict": "dns-empty", "detail": "no records returned",
                "addresses": []}
    return {"verdict": "resolved", "detail": "", "addresses": list(addresses)}


def resolve_domain_public(domain: str) -> Dict[str, Any]:
    """Resolve ``domain`` through public DoH as a cross-check on the system resolver.

    Split-horizon DNS and TLS-inspecting proxies commonly answer for the
    customer domain locally; the public answer is what a visitor sees.
    Best-effort by design: an unreachable DoH endpoint returns
    ``unavailable`` and the caller keeps the system-resolver view.
    """
    query = urllib.parse.quote(domain, safe="")
    detail = ""
    for template in PUBLIC_DNS_ENDPOINTS:
        url = template.format(query)
        source = url.split("?", 1)[0]
        request = urllib.request.Request(
            url, headers={"Accept": "application/dns-json"})
        try:
            with urllib.request.urlopen(
                    request, timeout=PUBLIC_DNS_TIMEOUT_SECONDS) as response:
                doc = json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError) as exc:
            detail = "{0}: {1}".format(source, str(exc)[:120])
            continue
        if not isinstance(doc, dict):
            detail = "{0}: non-JSON answer".format(source)
            continue
        status = doc.get("Status")
        if status not in (0, "0", None):
            detail = "{0}: dns status {1}".format(source, status)
            continue
        answers = set()
        for row in doc.get("Answer") or []:
            if not isinstance(row, dict):
                continue
            try:
                record_type = int(row.get("type", 0) or 0)
            except (TypeError, ValueError):
                continue
            if record_type == 1 and row.get("data"):
                answers.add(str(row["data"]))
        answers = sorted(answers)
        if not answers:
            return {"verdict": "dns-empty", "detail": "",
                    "addresses": [], "source": source}
        return {"verdict": "resolved", "detail": "",
                "addresses": answers, "source": source}
    return {"verdict": "unavailable", "detail": detail,
            "addresses": [], "source": ""}


def _decode_der(der: bytes) -> Dict[str, Any]:
    """Subject/issuer/SAN/validity of a DER certificate, via the stdlib decoder.

    ``ssl.getpeercert()`` exposes these fields only after a *verified*
    handshake. A rejected certificate still has to be named in the report,
    so its DER bytes are decoded here instead of shelling out to openssl
    (whose flags differ between LibreSSL and OpenSSL).
    """
    if not der:
        return {}
    descriptor = -1
    path = ""
    try:
        descriptor, path = tempfile.mkstemp(suffix=".pem")
        with os.fdopen(descriptor, "w") as handle:
            descriptor = -1
            handle.write(ssl.DER_cert_to_PEM_cert(der))
        cert = ssl._ssl._test_decode_cert(path)
    except (OSError, ValueError, AttributeError):
        return {}
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass
    info = _basic_info(cert)
    info["not_before"] = cert.get("notBefore", "")
    info["not_after"] = cert.get("notAfter", "")
    return info


def _served_certificate(
    domain: str,
    port: int,
    timeout: int,
    address: Optional[str] = None,
) -> Dict[str, Any]:
    """Read what the server actually serves, without trusting it.

    Verification is disabled only for this reporting pass; the verdict still
    comes from the verified handshake in ``probe_https``. This is how an
    expired or wrong-name certificate gets named instead of merely rejected.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    connection: Optional[socket.socket] = None
    tls_socket: Optional[ssl.SSLSocket] = None
    try:
        connection = socket.create_connection(
            (address or domain, port), timeout)
        connection.settimeout(timeout)
        tls_socket = context.wrap_socket(connection, server_hostname=domain)
        connection = None
        der = tls_socket.getpeercert(binary_form=True) or b""
        info = _decode_der(der)
        if der:
            info["fingerprint_sha256"] = hashlib.sha256(der).hexdigest()
        info["protocol"] = tls_socket.version() or ""
        return info
    except (OSError, ssl.SSLError, ValueError):
        return {}
    finally:
        for handle in (tls_socket, connection):
            if handle is not None:
                try:
                    handle.close()
                except OSError:
                    pass


def _date_info(cert: Dict[str, Any], now: datetime.datetime) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "not_before": cert.get("notBefore", ""),
        "not_after": cert.get("notAfter", ""),
        "days_left": None,
    }
    end = _parse_cert_date(str(cert.get("notAfter", "")))
    start = _parse_cert_date(str(cert.get("notBefore", "")))
    if end is None:
        out["window"] = "unparsable"
        return out
    out["days_left"] = (end - now).days
    if now > end:
        out["window"] = "expired"
    elif start is not None and now < start:
        out["window"] = "not-yet-valid"
    elif out["days_left"] <= EXPIRING_SOON_DAYS:
        out["window"] = "expiring-soon"
    else:
        out["window"] = "valid"
    return out


def _basic_info(cert: Dict[str, Any]) -> Dict[str, Any]:
    def _first_entry(name):
        rows = cert.get(name) or []
        if not rows:
            return ""
        entry: Any = rows[0]
        while isinstance(entry, (list, tuple)) and entry:
            entry = entry[-1]
        return str(entry)

    sans = sorted(
        str(value) for kind, value in (cert.get("subjectAltName") or [])
        if kind.lower() == "dns"
    )
    return {
        "subject": _first_entry("subject"),
        "issuer": _first_entry("issuer"),
        "san_dns": sans,
    }


def probe_https(
    domain: str,
    port: int = DEFAULT_TLS_PORT,
    timeout: int = TLS_CONNECT_TIMEOUT_SECONDS,
    address: Optional[str] = None,
) -> Dict[str, Any]:
    """Return the outside-in HTTPS view of ``domain``:port.

    Verification is deliberately left ON, so the returned verdict mirrors
    what a browser shows: a certificate the browser rejects is exactly the
    certificate the customer needs explained. ``address`` pins the TCP
    destination (public-DNS answer) while SNI and name checks stay on
    ``domain``; that is how a polluted local resolver is bypassed.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    result: Dict[str, Any] = {
        "target": "{0}:{1}".format(domain, port),
        "address": address or "",
        "verdict": "unknown",
        "detail": "",
        "error_code": "",
    }
    context = ssl.create_default_context()
    connection: Optional[socket.socket] = None
    tls_socket: Optional[ssl.SSLSocket] = None
    try:
        try:
            raw = _call_with_timeout(
                socket.create_connection,
                ((address or domain, port),), timeout + 5,
                on_timeout="TIMEOUT")
        except socket.timeout:
            raw = "TIMEOUT"
        if raw == "TIMEOUT":
            result["verdict"] = "connect-timeout"
            result["detail"] = (
                "no TCP answer on {0} within the time budget: the address may "
                "not belong to the instance, the security group may reject "
                "the source, or egress from this probe host is blocked"
                .format(port))
            return result
        connection = raw
        connection.settimeout(timeout)
        tls_socket = context.wrap_socket(connection, server_hostname=domain)
        connection = None
        try:
            tls_socket.settimeout(timeout)
            tls_socket.do_handshake()
        except socket.timeout:
            result["verdict"] = "handshake-timeout"
            result["detail"] = "TCP opened but the TLS handshake stalled"
            return result
        cert = tls_socket.getpeercert() or {}
        result.update(_basic_info(cert))
        result.update(_date_info(cert, now))
        der = tls_socket.getpeercert(binary_form=True) or b""
        if der:
            result["fingerprint_sha256"] = hashlib.sha256(der).hexdigest()
        result["certificate_verified"] = True
        result["protocol"] = tls_socket.version() or ""
        window = result.get("window")
        if window in ("expired", "not-yet-valid"):
            result["verdict"] = "cert-window-invalid"
            result["error_code"] = "err_cert_date_invalid"
        elif window == "expiring-soon":
            result["verdict"] = "cert-expiring-soon"
        elif window == "valid":
            result["verdict"] = "valid"
        else:
            result["verdict"] = "cert-window-unparsable"
            result["detail"] = (
                "the handshake verified, but the served validity dates were not "
                "readable: report them as not returned instead of assuming a "
                "window")
        return result
    except ssl.SSLCertVerificationError as exc:
        message = (exc.verify_message or str(exc)).lower()
        result["verdict"] = "cert-verify-failed"
        result["certificate_verified"] = False
        result["detail"] = str(exc.verify_message or exc)
        if "expired" in message:
            result["error_code"] = "err_cert_date_invalid"
        elif "hostname mismatch" in message:
            result["error_code"] = ""
            result["verdict"] = "cert-name-mismatch"
        served = _served_certificate(domain, port, timeout, address)
        if served:
            result["served"] = served
            for key in ("subject", "issuer", "san_dns", "not_before",
                        "not_after", "fingerprint_sha256"):
                if served.get(key):
                    result[key] = served[key]
            if served.get("not_after"):
                result.update(_date_info(
                    {"notBefore": served.get("not_before", ""),
                     "notAfter": served.get("not_after", "")}, now))
        return result
    except ssl.SSLError as exc:
        text = str(exc)
        if "WRONG_VERSION_NUMBER" in text or "ALERT" in text.upper():
            result["verdict"] = "non-tls-response"
            result["detail"] = (
                "port answered, but not with TLS: something else listens "
                "there, or a transparent middlebox replies in plain HTTP "
                "(a plain HTTP answer is what ticket T-BF6A05D6 saw)")
            return result
        result["verdict"] = "handshake-failed"
        result["error_code"] = "err_connection_closed"
        result["detail"] = text
        return result
    except ConnectionResetError as exc:
        result["verdict"] = "connection-reset"
        result["error_code"] = "err_connection_closed"
        result["detail"] = str(exc)
        return result
    except ConnectionRefusedError as exc:
        result["verdict"] = "connection-refused"
        result["error_code"] = "err_connection_closed"
        result["detail"] = str(exc)
        return result
    except socket.timeout:
        result["verdict"] = "connect-timeout"
        result["detail"] = "no answer within the time budget"
        return result
    except socket.gaierror as exc:
        result["verdict"] = "dns-failed"
        result["detail"] = str(exc)
        return result
    except OSError as exc:
        result["verdict"] = "blocked"
        result["detail"] = (
            "environment restriction on the probe host: {0}".format(exc))
        return result
    finally:
        for handle in (tls_socket, connection):
            if handle is not None:
                try:
                    handle.close()
                except OSError:
                    pass


def summarize_endpoint_ip(domain: str, cidr: str) -> Dict[str, Any]:
    """Resolve ``domain`` and report whether the answers fall inside ``cidr``.

    Used for the ownership check on Let's Encrypt edge addresses; pure DNS
    plus arithmetic, no connection is made.
    """
    import ipaddress

    resolved = resolve_domain(domain)
    network = ipaddress.ip_network(cidr)
    inside: List[str] = []
    outside: List[str] = []
    for raw_address in resolved.get("addresses", []):
        try:
            address = ipaddress.ip_address(raw_address)
        except ValueError:
            continue
        if address.version == 4 and address in network:
            inside.append(raw_address)
        else:
            outside.append(raw_address)
    return {
        "domain": domain,
        "dns_verdict": resolved.get("verdict", ""),
        "addresses": resolved.get("addresses", []),
        "in_cidr": inside,
        "out_of_cidr": outside,
        "cidr": cidr,
    }


# Boundary self-tests executed on import (inline, no test framework).
_NOW_STUB = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
assert _parse_cert_date("Jan  1 00:00:00 2026 GMT") == _NOW_STUB
assert _parse_cert_date("Feb 28 23:59:59 2026") == datetime.datetime(
    2026, 2, 28, 23, 59, 59, tzinfo=datetime.timezone.utc)
assert _parse_cert_date("2026-01-01 00:00:00") == _NOW_STUB
assert _parse_cert_date("2026-01-01T00:00:00+00:00") == _NOW_STUB
assert _parse_cert_date("2026-01-01T08:00:00+08:00") == _NOW_STUB
assert _parse_cert_date("not a date") is None
assert _parse_cert_date("") is None
assert _parse_cert_date(None) is None
assert _parse_cert_date("Xyz 01 00:00:00 2026 GMT") is None
_window = _date_info({"notBefore": "Jan 01 00:00:00 2020 GMT",
                      "notAfter": "Jan 01 00:00:00 2021 GMT"}, _NOW_STUB)
assert _window["window"] == "expired", _window
_iso_expired = _date_info({"notBefore": "2020-01-01 00:00:00",
                           "notAfter": "2021-01-01 00:00:00"}, _NOW_STUB)
assert _iso_expired["window"] == "expired", _iso_expired
_future = _date_info({"notBefore": "Jan 01 00:00:00 2030 GMT",
                      "notAfter": "Jan 01 00:00:00 2031 GMT"}, _NOW_STUB)
assert _future["window"] == "not-yet-valid", _future
_blank = _date_info({"notBefore": "", "notAfter": ""}, _NOW_STUB)
assert _blank["window"] == "unparsable" and _blank["days_left"] is None, _blank
assert _call_with_timeout(lambda value: value, ("x",), 5) == "x"
assert _call_with_timeout(lambda: None, (), 5, on_timeout="sentinel") is None


def _raise_soon():
    raise socket.gaierror("boom")


try:
    _call_with_timeout(_raise_soon, (), 5)
    raise AssertionError("worker errors must re-raise, not be swallowed")
except socket.gaierror:
    pass
