"""Read-only TLS probe: read the certificate the origin actually serves.

Why this exists: the L7 compliance check used to declare TLS undecidable with the
evidence line "No cloud-side API can see which certificate chain nginx or IIS
actually loaded". That claim is wrong. No cloud API is needed -- one outbound TLS
handshake to the customer's own hostname reveals the served leaf certificate, its
validity window, its SAN list and whether the chain validates. Measured on ticket
T-96DF8B18: the xiaoer opened the site, saw the certificate error and told the
customer to replace the certificate; this tool recognised the cert family and
still answered PRIMARY-CAUSE: unverified plus a generic checklist.

Discipline:
  * read-only, no credentials, no cloud API, one connection per pass, bounded timeout;
  * only the hostname the customer supplied is ever contacted;
  * a failed handshake is NOT a certificate defect -- it is reported as a reachability
    signal and never used to name a certificate root cause;
  * `ECS_TLS_PROBE=off` disables all network access;
  * `ECS_TLS_FACTS=<path>` serves recorded readings instead of probing, so offline
    replay never contacts a historical customer's domain.

The dispatcher only names a cause this run actually measured, so a defect found
here is what lets the L7 verdict become CONFIRMED instead of asserted.
"""
import datetime
import json
import os
import socket
import ssl

TIMEOUT_S = float(os.environ.get("ECS_TLS_TIMEOUT", "8"))
PROBE_ENABLED = os.environ.get("ECS_TLS_PROBE", "on").lower() != "off"
FACTS_PATH = os.environ.get("ECS_TLS_FACTS", "")

DEFECT_LABELS = {
    "expired": "the served certificate is expired",
    "not_yet_valid": "the served certificate is not valid yet",
    "hostname_mismatch": "the served certificate does not cover the requested hostname",
    "self_signed": "the served certificate is self-signed",
    "incomplete_chain": "the served certificate chain cannot be validated (missing intermediate)",
    "untrusted_issuer": "the client does not trust the issuing authority of the served certificate",
    "date_invalid": "the client reports the served certificate is outside its validity window",
    "client_reported": "the client's browser reports a certificate error for this hostname",
}

VERIFY_DEFECTS = (
    ("expired", ("certificate has expired", "expired")),
    ("not_yet_valid", ("not yet valid", "not yet active")),
    ("hostname_mismatch", ("hostname mismatch", "doesn't match", "does not match")),
    ("self_signed", ("self signed", "self-signed")),
    ("incomplete_chain", ("unable to get local issuer", "unable to verify",
                          "certificate verify failed", "unknown ca")),
)


def _facts_for(host):
    if not FACTS_PATH:
        return None
    try:
        with open(FACTS_PATH, encoding="utf-8") as handle:
            doc = json.load(handle)
    except Exception:
        return None
    hosts = doc.get("hosts") or {}
    row = hosts.get(host) or hosts.get("*") or doc.get("default")
    if not isinstance(row, dict):
        return None
    result = dict(row)
    result.setdefault("host", host)
    result["source"] = "recorded-facts"
    result["defects"] = [code for code in (result.get("defects") or [])
                         if code in DEFECT_LABELS]
    return result


def _parse_time(value):
    if not value:
        return None
    try:
        return datetime.datetime.strptime(value, "%b %d %H:%M:%S %Y %Z")
    except Exception:
        return None


def _cert_fields(cert, host):
    subject = {}
    for rdn in cert.get("subject") or ():
        for key, value in rdn:
            subject[key] = value
    san = [value for kind, value in (cert.get("subjectAltName") or ())
           if kind.lower() == "dns"]
    not_after = _parse_time(cert.get("notAfter"))
    not_before = _parse_time(cert.get("notBefore"))
    now = datetime.datetime.utcnow()
    defects = []
    if not_after and now > not_after:
        defects.append("expired")
    if not_before and now < not_before:
        defects.append("not_yet_valid")
    names = san or [subject.get("commonName", "")]
    match = any(_name_matches(host, name) for name in names if name)
    if names and not match:
        defects.append("hostname_mismatch")
    return {"subject_cn": subject.get("commonName", ""), "san": san,
            "not_before": cert.get("notBefore", ""), "not_after": cert.get("notAfter", ""),
            "days_left": (not_after - now).days if not_after else None,
            "hostname_match": bool(match), "defects": defects}


def _name_matches(host, pattern):
    host = (host or "").lower().rstrip(".")
    pattern = (pattern or "").lower().rstrip(".")
    if pattern.startswith("*."):
        suffix = pattern[2:]
        return host == suffix or (host.endswith("." + suffix)
                                  and host[:-(len(suffix) + 1)].count(".") == 0)
    return host == pattern


def _classify_verify(message):
    lowered = (message or "").lower()
    for code, needles in VERIFY_DEFECTS:
        if any(needle in lowered for needle in needles):
            return code
    return ""


def _handshake(host, port, context):
    with socket.create_connection((host, port), timeout=TIMEOUT_S) as raw:
        with context.wrap_socket(raw, server_hostname=host) as tls:
            return tls.getpeercert()


def probe(host, port=443):
    """Return the readings for one hostname, or None when no probe was possible."""
    if not host:
        return None
    recorded = _facts_for(host)
    if recorded is not None:
        return recorded
    if not PROBE_ENABLED:
        return None
    try:
        port = int(port or 443)
    except (TypeError, ValueError):
        port = 443
    result = {"host": host, "port": port, "source": "live", "ok": False,
              "error": "", "verify_error": "", "defects": [], "san": [],
              "subject_cn": "", "not_before": "", "not_after": "", "days_left": None,
              "hostname_match": None, "trusted": False}
    verified = ssl.create_default_context()
    try:
        cert = _handshake(host, port, verified)
        result.update(_cert_fields(cert or {}, host))
        result["ok"] = True
        result["trusted"] = True
        return result
    except ssl.SSLCertVerificationError as exc:
        result["verify_error"] = getattr(exc, "verify_message", "") or str(exc)
        code = _classify_verify(result["verify_error"])
        if code:
            result["defects"] = [code]
    except ssl.SSLError as exc:
        result["error"] = "tls handshake failed: %s" % str(exc)[:160]
        return result
    except (socket.timeout, socket.gaierror, OSError) as exc:
        result["error"] = "%s: %s" % (type(exc).__name__, str(exc)[:160])
        return result
    relaxed = ssl.create_default_context()
    relaxed.check_hostname = False
    try:
        cert = _handshake(host, port, relaxed)
        result.update(_cert_fields(cert or {}, host))
        result["ok"] = True
        result["trusted"] = True
        return result
    except ssl.SSLError:
        pass
    except (socket.timeout, socket.gaierror, OSError) as exc:
        result["error"] = "%s: %s" % (type(exc).__name__, str(exc)[:160])
        return result
    unverified = ssl.create_default_context()
    unverified.check_hostname = False
    unverified.verify_mode = ssl.CERT_NONE
    try:
        _handshake(host, port, unverified)
        result["ok"] = True
        result["served_without_validation"] = True
    except (ssl.SSLError, socket.timeout, socket.gaierror, OSError) as exc:
        result["error"] = result["error"] or "%s: %s" % (type(exc).__name__, str(exc)[:160])
    return result


def defect_summary(result):
    codes = result.get("defects") or []
    return "; ".join(DEFECT_LABELS[code] for code in codes if code in DEFECT_LABELS)


def evidence_lines(result):
    lines = []
    if result.get("not_after"):
        lines.append("Served certificate notAfter=%s notBefore=%s days_left=%s"
                     % (result["not_after"], result.get("not_before") or "-",
                        result.get("days_left")))
    if result.get("subject_cn") or result.get("san"):
        lines.append("Served certificate CN=%s SAN=%s hostname_match=%s"
                     % (result.get("subject_cn") or "-",
                        ",".join(result.get("san") or []) or "-",
                        result.get("hostname_match")))
    if result.get("verify_error"):
        if result.get("defects") == ["client_reported"]:
            lines.append("Client-reported certificate error for %s (browser dialog); the exact "
                         "defect - expiry, name coverage or chain - still needs the live "
                         "handshake reading." % result.get("host", "the hostname"))
        elif result.get("defects") == ["untrusted_issuer"]:
            lines.append("Browser code ERR_CERT_AUTHORITY_INVALID for %s: the issuer is not "
                         "trusted. Whether the leaf is self-signed, from a private CA, or served "
                         "without its intermediate still needs the live handshake reading."
                         % result.get("host", "the hostname"))
        elif result.get("defects") == ["date_invalid"]:
            lines.append("Browser code ERR_CERT_DATE_INVALID for %s: the validity window is "
                         "wrong. Whether it expired or is not valid yet still needs the live "
                         "handshake reading." % result.get("host", "the hostname"))
        else:
            lines.append("TLS verification error: %s" % result["verify_error"][:200])
    if result.get("error"):
        lines.append("Probe reachability: %s" % result["error"][:200])
    if result.get("source") == "recorded-facts":
        lines.append("Readings supplied from the recorded ticket evidence (offline replay; "
                     "no connection was made to the customer host).")
    elif result.get("source") == "live":
        lines.append("Read by a read-only outbound TLS handshake to the customer hostname; "
                     "no credential and no cloud API were used.")
    return lines


def remediation_actions(result, host):
    codes = set(result.get("defects") or [])
    actions = []
    if (codes & {"expired", "not_yet_valid", "client_reported", "date_invalid"}):
        actions.append("Replace the served certificate for %s: issue or renew it in the SSL "
                       "Certificate Service console, deploy the new certificate to the web "
                       "server (nginx/IIS/Tomcat) and reload, then re-open the site and confirm "
                       "the browser no longer reports a certificate error." % host)
    if "hostname_mismatch" in codes:
        actions.append("Re-issue the certificate for %s with that exact name in the SAN list "
                       "(a wildcard only covers one label level), then deploy and reload." % host)
    if codes & {"incomplete_chain", "self_signed", "untrusted_issuer"}:
        actions.append("Serve the full chain for %s: concatenate the leaf with the issuing "
                       "intermediate(s) in the web server certificate file and reload; a "
                       "self-signed certificate must be replaced by one from a trusted CA." % host)
    if codes:
        actions.append("After the certificate change, check the page for mixed content: any "
                       "http:// or off-site resource reference must be updated in the site code, "
                       "otherwise the browser still blocks part of the page.")
        if "client_reported" in codes:
            actions.append("The exact defect (expiry, name coverage or chain) still needs the "
                           "live handshake reading: run this check against the hostname with "
                           "probing enabled, or ask the customer to paste the browser certificate "
                           "dialog showing the expiry date and the issued-to name.")
        if codes & {"untrusted_issuer", "date_invalid"}:
            actions.append("The browser code narrows the defect but not its sub-cause: read the "
                           "served chain and validity window with a handshake to the hostname "
                           "before choosing between re-issuing and serving the full chain.")
        actions.append("Certificate issuance, renewal and deployment belong to the certificate "
                       "service owner; this tool only reads what the origin serves.")
    return actions
