#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pure interpretation of OSS real-time-log query results.

Every function here is side-effect free and takes the rows returned by
_sls_query.run_sls_query. SLS returns ALL values as strings, so the first
job is coercion; the second is turning distributions into a verdict.

Field values below are the ones measured live against a real
oss-log-<uid>-<region> / oss-log-store logstore, not guessed:
  sync_request : "cdn" = CDN origin-pull; "-" / "null" = direct client call
  sign_type    : "NotSign" = anonymous, "NormalSign" = V1 credential,
                 "NORMAL_SIGN4" = V4 credential, "UriSign" = V1 presigned
                 URL, "UriSign4" = V4 presigned URL
  access_id    : "-" / "null" = none; "STS.*" / "TMP.*" = temporary
                 credential; "LTAI*" = long-lived AccessKey
  vpc_id       : "null" / "-" = request came from outside any VPC;
                 otherwise the request originated inside a VPC
  referer      : "-" / "null" / "" = the client sent no Referer
  client_ip    : may be a private address (192.168.x.x, 10.x, 172.16-31.x)
                 when the caller reached OSS over the intranet

Severity discipline: this is a SECURITY skill, so it must be able to say
"the evidence supports a benign conclusion". Over-diagnosing normal
business traffic as an attack is a defect, not a safe default.
"""

from __future__ import annotations

# Values SLS uses for "field absent" -- they are NOT data.
_NULLISH = frozenset({"", "-", "null", "none", "NULL", "None"})

_ANONYMOUS_SIGN = frozenset({"notsign", "not_sign"})
_PRESIGNED_SIGN = frozenset({"urisign", "urisign4"})
_CREDENTIAL_SIGN = frozenset({"normalsign", "normal_sign4"})

_SCRIPTING_UA_TOKENS = ("python", "aiohttp", "curl", "wget", "java/",
                        "okhttp", "go-http-client", "scrapy", "node-fetch",
                        "axios", "httpclient", "requests/")
_BROWSER_UA_TOKENS = ("mozilla", "chrome", "safari", "edge", "firefox")

_PRIVATE_IP_PREFIXES = ("10.", "192.168.", "127.", "169.254.")


# ---------------------------------------------------------------------------
# Coercion
# ---------------------------------------------------------------------------

def is_nullish(value) -> bool:
    """True when SLS is telling us the field was absent, not that it is data."""
    return str(value if value is not None else "").strip() in _NULLISH


assert is_nullish("-") and is_nullish("null") and is_nullish("")  # normal
assert is_nullish(None)  # boundary: None
assert not is_nullish("cdn") and not is_nullish("0")  # boundary: real values, incl. "0"
assert not is_nullish("  x  ")  # boundary: padded


def to_number(value, default: float = 0.0) -> float:
    """Coerce an SLS string cell to float. Non-numeric and nullish -> default."""
    if is_nullish(value):
        return default
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


assert to_number("3") == 3.0 and to_number("0.0005") == 0.0005  # normal
assert to_number("-") == 0.0 and to_number(None) == 0.0  # invalid: nullish
assert to_number("abc") == 0.0  # invalid: non-numeric
assert to_number("abc", -1.0) == -1.0  # boundary: explicit default
assert to_number("") == 0.0  # boundary: empty string


def clean_rows(rows: list) -> list:
    """Drop the SLS transport keys and coerce numeric-looking cells.

    `__source__` / `__time__` / `__topic__` are injected by SLS into every
    result row and are not part of the requested projection; leaving them in
    makes every table the customer reads carry two junk columns.
    """
    out = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        clean = {}
        for key, value in row.items():
            name = str(key)
            if name.startswith("__") and name.endswith("__"):
                continue
            clean[name] = to_number(value) if _looks_numeric(value) else value
        if clean:
            out.append(clean)
    return out


def _looks_numeric(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, str):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    text = value.strip()
    if not text or text in _NULLISH:
        return False
    try:
        float(text)
    except ValueError:
        return False
    return True


_C = clean_rows([{"__source__": "", "__time__": "1788331244",
                  "client_ip": "1.2.3.4", "cnt": "3", "bytes_gb": "0.5"}])
assert _C == [{"client_ip": "1.2.3.4", "cnt": 3.0, "bytes_gb": 0.5}]  # normal
assert clean_rows([]) == []  # boundary: empty
assert clean_rows(None) == []  # invalid: None
assert clean_rows(["not-a-dict", {"__time__": "1"}]) == []  # invalid: junk rows dropped
assert clean_rows([{"access_id": "STS.abc"}]) == [{"access_id": "STS.abc"}]  # boundary: non-numeric kept
assert clean_rows([{"vpc_id": "551733"}]) == [{"vpc_id": 551733.0}]  # boundary: numeric-looking id coerced
assert clean_rows([{"sign_type": "-"}]) == [{"sign_type": "-"}]  # boundary: nullish stays a string


def is_private_ip(ip: str) -> bool:
    """True for RFC1918 / loopback / link-local addresses.

    A private client_ip means the caller reached OSS over the intranet, so
    it is not an external abuser and its bytes are not internet-outbound.
    """
    text = str(ip or "").strip()
    if text in _NULLISH:
        return False
    if text.startswith(_PRIVATE_IP_PREFIXES):
        return True
    if text.startswith("172."):
        parts = text.split(".")
        if len(parts) > 1 and parts[1].isdigit():
            return 16 <= int(parts[1]) <= 31
    return False


assert is_private_ip("192.168.2.212") and is_private_ip("10.0.0.1")  # normal
assert is_private_ip("172.16.0.1") and is_private_ip("172.31.255.255")  # boundary: 172 range edges
assert not is_private_ip("172.15.0.1") and not is_private_ip("172.32.0.1")  # boundary: just outside
assert not is_private_ip("47.109.130.253")  # normal: public
assert not is_private_ip("-") and not is_private_ip("")  # invalid: nullish
assert not is_private_ip(None)  # invalid: None


# ---------------------------------------------------------------------------
# Per-step interpretation
# ---------------------------------------------------------------------------

def interpret_cdn_mix(rows: list) -> dict:
    """Step 0: is the traffic CDN origin-pull or direct client access?

    If every request is sync_request=cdn the OSS-side Top IPs are CDN edge
    nodes, so all IP/UA/referer analysis must move to the CDN side.
    """
    clean = clean_rows(rows)
    total = sum(to_number(r.get("req_count") or r.get("cnt")) for r in clean)
    cdn = sum(to_number(r.get("req_count") or r.get("cnt")) for r in clean
              if str(r.get("sync_request") or "").strip().lower() == "cdn")
    if total <= 0:
        return {"verdict": "no_data", "cdn_share_pct": 0.0, "total": 0,
                "finding": "no requests matched the window, so CDN origin-pull "
                           "can be neither confirmed nor excluded"}
    share = round(cdn * 100.0 / total, 1)
    if share >= 99.0:
        verdict = "all_cdn"
        finding = ("essentially every request is CDN origin-pull "
                   "(sync_request=cdn): the OSS-side client IPs are CDN edge "
                   "nodes, not end users. Continue the investigation in the "
                   "CDN domain's own logs -- Top-IP / UA / Referer analysis "
                   "on this logstore would name the wrong actor.")
    elif share > 0:
        verdict = "mixed"
        finding = (f"{share}% of requests are CDN origin-pull and "
                   f"{round(100 - share, 1)}% are direct client calls. The "
                   "queries already exclude sync_request=cdn, so the "
                   "remaining analysis covers the direct-access part only; a "
                   "low CDN cache-hit rate also inflates origin traffic and "
                   "is worth checking on the CDN side.")
    else:
        verdict = "no_cdn"
        finding = ("no CDN origin-pull traffic in this window "
                   "(sync_request is '-' / null throughout), so all requests "
                   "come from clients directly and the OSS-side Top-IP "
                   "analysis is valid as-is.")
    return {"verdict": verdict, "cdn_share_pct": share, "total": int(total),
            "finding": finding}


assert interpret_cdn_mix([{"sync_request": "cdn", "req_count": "100"}])["verdict"] == "all_cdn"  # normal
assert interpret_cdn_mix([{"sync_request": "-", "req_count": "100"}])["verdict"] == "no_cdn"  # normal
assert interpret_cdn_mix([{"sync_request": "null", "req_count": "100"}])["verdict"] == "no_cdn"  # boundary: nullish counts as direct
_M = interpret_cdn_mix([{"sync_request": "cdn", "req_count": "30"},
                        {"sync_request": "-", "req_count": "70"}])
assert _M["verdict"] == "mixed" and _M["cdn_share_pct"] == 30.0  # normal: mixed share
assert interpret_cdn_mix([])["verdict"] == "no_data"  # invalid: empty
assert interpret_cdn_mix(None)["verdict"] == "no_data"  # invalid: None


def interpret_auth_mode(rows: list) -> dict:
    """Step 1: anonymous, presigned-URL, or credentialed access?

    This is the single most decisive split: NotSign with no access_id means
    anonymous reads (a public-read scraping or hotlinking branch), while a
    real AccessKey ID routes to the credential-leak branch.
    """
    clean = clean_rows(rows)
    total = sum(to_number(r.get("cnt")) for r in clean)
    if total <= 0:
        return {"verdict": "no_data", "anonymous_share_pct": 0.0,
                "presigned_share_pct": 0.0, "identities": [],
                "finding": "no matching requests, so the access mode cannot "
                           "be determined from this window"}
    anon = presigned = cred = 0.0
    identities = []
    for row in clean:
        count = to_number(row.get("cnt"))
        sign = str(row.get("sign_type") or "").strip().lower()
        access_id = str(row.get("access_id") or "").strip()
        if sign in _ANONYMOUS_SIGN or (is_nullish(access_id) and not sign):
            anon += count
        elif sign in _PRESIGNED_SIGN:
            presigned += count
            identities.append(access_id)
        else:
            cred += count
            if not is_nullish(access_id):
                identities.append(access_id)
    unique = sorted({i for i in identities if not is_nullish(i)})
    anon_pct = round(anon * 100.0 / total, 1)
    presigned_pct = round(presigned * 100.0 / total, 1)
    if anon_pct >= 50.0:
        verdict = "anonymous"
        finding = (f"{anon_pct}% of requests are unsigned (sign_type=NotSign "
                   "with no access_id): this is ANONYMOUS access, which is "
                   "only possible when the bucket ACL or a bucket policy "
                   "grants it. The exposure audit's effective-public verdict "
                   "is the root cause to act on.")
    elif presigned_pct >= 20.0:
        verdict = "presigned_url"
        finding = (f"{presigned_pct}% of requests use a presigned URL "
                   "(sign_type=UriSign / UriSign4): a leaked or publicly "
                   "posted signed URL lets anyone download without holding "
                   "the AccessKey. Shorten the expiry and stop sharing the "
                   "URL in public channels.")
    else:
        verdict = "credentialed"
        finding = (f"{round(cred * 100.0 / total, 1)}% of requests carry a "
                   f"credential (sign_type=NormalSign / NORMAL_SIGN4) across "
                   f"{len(unique)} distinct access id(s). Anonymous access is "
                   "NOT the vector: check whether the owner recognises every "
                   "access id below -- an unfamiliar one is a leaked "
                   "AccessKey.")
    return {"verdict": verdict, "anonymous_share_pct": anon_pct,
            "presigned_share_pct": presigned_pct,
            "credentialed_share_pct": round(cred * 100.0 / total, 1),
            "identities": unique, "finding": finding}


assert interpret_auth_mode([{"sign_type": "NotSign", "access_id": "-", "cnt": "10"}])["verdict"] == "anonymous"  # normal
assert interpret_auth_mode([{"sign_type": "NormalSign", "access_id": "LTAI5abc", "cnt": "10"}])["verdict"] == "credentialed"  # normal
assert interpret_auth_mode([{"sign_type": "UriSign4", "access_id": "LTAI5abc", "cnt": "10"}])["verdict"] == "presigned_url"  # normal
_A = interpret_auth_mode([{"sign_type": "NotSign", "access_id": "-", "cnt": "30"},
                          {"sign_type": "NormalSign", "access_id": "LTAIx", "cnt": "70"}])
assert _A["verdict"] == "credentialed" and _A["anonymous_share_pct"] == 30.0  # boundary: minority anonymous
assert interpret_auth_mode([{"sign_type": "NormalSign", "access_id": "STS.abc", "cnt": "5"}])["identities"] == ["STS.abc"]  # boundary: STS id kept
assert interpret_auth_mode([])["verdict"] == "no_data"  # invalid: empty
assert interpret_auth_mode([{"cnt": "0"}])["verdict"] == "no_data"  # invalid: zero total


def interpret_endpoint_split(rows: list) -> dict:
    """Step 1b/1c: how much of the volume is public egress vs intranet/VPC?

    Only public egress is billed as internet-outbound, and only public egress
    can be an external abuser. A dominantly internal share is the strongest
    benign signal available in this log.
    """
    clean = clean_rows(rows)
    total = sum(to_number(r.get("bytes_gb") if r.get("bytes_gb") is not None
                          else r.get("cnt")) for r in clean)
    if total <= 0:
        return {"verdict": "no_data", "internal_share_pct": 0.0,
                "finding": "no traffic in the window to split"}
    internal = 0.0
    for row in clean:
        weight = to_number(row.get("bytes_gb") if row.get("bytes_gb") is not None
                           else row.get("cnt"))
        kind = str(row.get("endpoint_type") or "").strip().lower()
        vpc = row.get("vpc_id")
        if kind == "internal" or (kind == "" and not is_nullish(vpc)):
            internal += weight
    share = round(internal * 100.0 / total, 1)
    if share >= 80.0:
        verdict = "mostly_internal"
        finding = (f"{share}% of the volume reached OSS over the intranet or "
                   "from inside a VPC. Intranet traffic is not billed as "
                   "internet-outbound and cannot come from an external "
                   "abuser, so the evidence points at the owner's own "
                   "workloads -- confirm which internal service is pulling, "
                   "rather than treating this as an attack.")
    elif share >= 30.0:
        verdict = "mixed"
        finding = (f"{share}% internal / {round(100 - share, 1)}% public. "
                   "Both a legitimate internal workload and external clients "
                   "are present, so rank the public side by bytes (step 2b) "
                   "before naming an abuser.")
    else:
        verdict = "mostly_public"
        finding = (f"{round(100 - share, 1)}% of the volume is public-internet "
                   "egress, which is what the internet-outbound bill charges "
                   "and the only part an external abuser can generate. Focus "
                   "the Top-IP analysis here.")
    return {"verdict": verdict, "internal_share_pct": share,
            "finding": finding}


assert interpret_endpoint_split([{"endpoint_type": "internal", "bytes_gb": "9"}])["verdict"] == "mostly_internal"  # normal
assert interpret_endpoint_split([{"endpoint_type": "public", "bytes_gb": "9"}])["verdict"] == "mostly_public"  # normal
# Live-measured ratio on oss-log-<uid>-cn-hangzhou: 329 public vs 110
# internal requests = 25.1% internal, which is below the 30% mixed band.
_E = interpret_endpoint_split([{"endpoint_type": "public", "bytes_gb": "0.329"},
                               {"endpoint_type": "internal", "bytes_gb": "0.110"}])
assert _E["verdict"] == "mostly_public" and _E["internal_share_pct"] == 25.1  # boundary: just under the mixed band
_E2 = interpret_endpoint_split([{"endpoint_type": "public", "bytes_gb": "5"},
                                {"endpoint_type": "internal", "bytes_gb": "5"}])
assert _E2["verdict"] == "mixed" and _E2["internal_share_pct"] == 50.0  # normal: mixed band
assert interpret_endpoint_split([{"endpoint_type": "internal", "bytes_gb": "8"},
                                 {"endpoint_type": "public", "bytes_gb": "2"}])["verdict"] == "mostly_internal"  # boundary: exactly 80%
assert interpret_endpoint_split([{"vpc_id": "551733", "cnt": "90"}])["verdict"] == "mostly_internal"  # boundary: vpc split form
assert interpret_endpoint_split([{"vpc_id": "null", "cnt": "90"}])["verdict"] == "mostly_public"  # boundary: nullish vpc = external
assert interpret_endpoint_split([])["verdict"] == "no_data"  # invalid: empty


def interpret_ip_concentration(count_rows: list, bytes_rows: list) -> dict:
    """Steps 2 + 2b: who is actually draining the bucket?

    Two rankings are read together because on real tickets they disagree:
    the IP issuing the most REQUESTS is often not the IP moving the most
    BYTES, and the bill follows bytes. Naming the count-top IP for
    containment blocks the wrong host.
    """
    counts = clean_rows(count_rows)
    bytes_ = clean_rows(bytes_rows)
    total_cnt = sum(to_number(r.get("cnt")) for r in counts)
    total_bytes = sum(to_number(r.get("bytes_gb")) for r in bytes_)
    if total_cnt <= 0 and total_bytes <= 0:
        return {"verdict": "no_data", "top_by_count": "", "top_by_bytes": "",
                "top_by_bytes_share_pct": 0.0, "ranking_diverges": False,
                "distinct_ips": 0,
                "finding": "no client-IP rows in the window"}
    top_cnt = max(counts, key=lambda r: to_number(r.get("cnt"))) if counts else {}
    top_bytes = max(bytes_, key=lambda r: to_number(r.get("bytes_gb"))) if bytes_ else {}
    top_cnt_ip = str(top_cnt.get("client_ip") or "")
    top_bytes_ip = str(top_bytes.get("client_ip") or "")
    share = round(to_number(top_bytes.get("bytes_gb")) * 100.0 / total_bytes, 1) \
        if total_bytes > 0 else 0.0
    distinct = len({str(r.get("client_ip") or "") for r in counts
                    if not is_nullish(r.get("client_ip"))})
    diverges = bool(top_cnt_ip and top_bytes_ip and top_cnt_ip != top_bytes_ip)
    external_top = top_bytes_ip and not is_private_ip(top_bytes_ip)
    if diverges:
        finding = (f"the count-top IP ({top_cnt_ip}) and the bytes-top IP "
                   f"({top_bytes_ip}) are DIFFERENT hosts. The bill follows "
                   f"bytes, so containment must target {top_bytes_ip} "
                   f"({share}% of all bytes); blocking only the count-top IP "
                   "would leave the real drain in place.")
    elif share >= 50.0 and distinct <= 5:
        finding = (f"{share}% of all bytes come from a single IP "
                   f"({top_bytes_ip}) out of only {distinct} distinct "
                   "client(s): a concentrated scripted download from fixed "
                   "hosts, the classic scraping signature.")
    elif distinct > 50:
        finding = (f"traffic is spread over {distinct} distinct client IPs "
                   f"with the top one at only {share}% of bytes. Wide "
                   "dispersion is NOT scripted scraping from a fixed host -- "
                   "cross-check the Referer step: many dispersed clients "
                   "sharing a third-party referer is hotlinking, while "
                   "dispersed clients with no referer is more likely "
                   "legitimate public distribution.")
    else:
        finding = (f"top IP {top_bytes_ip or '(none)'} accounts for {share}% "
                   f"of bytes across {distinct} distinct client(s); no single "
                   "host dominates, so rank the C-segment step (2c) before "
                   "concluding -- abuse fleets rotate addresses inside one "
                   "/24.")
    if top_bytes_ip and not external_top:
        finding += (" Note: the bytes-top client_ip is a PRIVATE address, so "
                    "this traffic came over the intranet from the owner's own "
                    "network and is not internet-outbound abuse.")
    return {
        "verdict": ("concentrated" if share >= 50.0 and distinct <= 5
                    else "dispersed" if distinct > 50 else "moderate"),
        "top_by_count": top_cnt_ip,
        "top_by_bytes": top_bytes_ip,
        "top_by_bytes_share_pct": share,
        "top_by_bytes_is_private": bool(top_bytes_ip) and not external_top,
        "ranking_diverges": diverges,
        "distinct_ips": distinct,
        "finding": finding,
    }


assert interpret_ip_concentration(
    [{"client_ip": "1.1.1.1", "cnt": "10"}],
    [{"client_ip": "1.1.1.1", "bytes_gb": "9"}])["ranking_diverges"] is False  # normal: same host
_D = interpret_ip_concentration(
    [{"client_ip": "1.1.1.1", "cnt": "12414"}],
    [{"client_ip": "2.2.2.2", "bytes_gb": "0.226"}])
assert _D["ranking_diverges"] is True and _D["top_by_bytes"] == "2.2.2.2"  # normal: the ticket-decisive divergence
assert "DIFFERENT hosts" in _D["finding"]
_C2 = interpret_ip_concentration(
    [{"client_ip": "1.1.1.1", "cnt": "100"}],
    [{"client_ip": "1.1.1.1", "bytes_gb": "9"}, {"client_ip": "2.2.2.2", "bytes_gb": "1"}])
assert _C2["verdict"] == "concentrated" and _C2["top_by_bytes_share_pct"] == 90.0  # normal: concentrated
_P = interpret_ip_concentration([], [{"client_ip": "192.168.2.212", "bytes_gb": "5"}])
assert _P["top_by_bytes_is_private"] is True and "PRIVATE address" in _P["finding"]  # boundary: intranet top
assert interpret_ip_concentration([], [])["verdict"] == "no_data"  # invalid: empty
assert interpret_ip_concentration(None, None)["verdict"] == "no_data"  # invalid: None


def interpret_referer(rows: list, owner_domains: list | None = None) -> dict:
    """Step 4: hotlinking vs direct programmatic access vs own-site traffic.

    An empty Referer is NOT automatically malicious -- native apps and
    server-side callers legitimately send none -- so it is reported as a
    signal to cross-check against the UA step, never as a conclusion.
    """
    clean = clean_rows(rows)
    total = sum(to_number(r.get("bytes_gb") if r.get("bytes_gb") is not None
                          else r.get("cnt")) for r in clean)
    if total <= 0:
        return {"verdict": "no_data", "empty_share_pct": 0.0,
                "third_party": [], "finding": "no referer rows in the window"}
    empty = 0.0
    third_party = []
    owners = [str(d).strip().lower() for d in (owner_domains or [])
              if str(d).strip()]
    for row in clean:
        weight = to_number(row.get("bytes_gb") if row.get("bytes_gb") is not None
                           else row.get("cnt"))
        referer = str(row.get("referer") or "").strip()
        if is_nullish(referer):
            empty += weight
            continue
        low = referer.lower()
        if owners and any(o in low for o in owners):
            continue
        third_party.append({"referer": referer,
                            "bytes_gb": to_number(row.get("bytes_gb")),
                            "cnt": to_number(row.get("cnt"))})
    empty_pct = round(empty * 100.0 / total, 1)
    third_party.sort(key=lambda t: t["bytes_gb"], reverse=True)
    if third_party and empty_pct < 50.0:
        verdict = "third_party"
        finding = ("traffic carries third-party Referer values "
                   f"({', '.join(t['referer'] for t in third_party[:3])}): "
                   "other sites are embedding this bucket's objects directly, "
                   "which is hotlinking / bandwidth theft. A Referer "
                   "whitelist (bucket Anti-Hotlink configuration) is the "
                   "remedy -- note there is NO acs:Referer condition key for "
                   "a bucket policy.")
    elif empty_pct >= 50.0:
        verdict = "mostly_empty"
        finding = (f"{empty_pct}% of requests send no Referer. This is NOT by "
                   "itself malicious -- native apps, server-side callers and "
                   "command-line tools legitimately send none. Cross-check "
                   "the UA step: a scripting UA with no referer means direct "
                   "programmatic downloads, while a browser UA with no "
                   "referer is unusual and worth investigating.")
    else:
        verdict = "own_or_mixed"
        finding = ("referer traffic is dominated by the owner's own domains "
                   "or is too mixed to attribute; no hotlinking signal in "
                   "this window.")
    return {"verdict": verdict, "empty_share_pct": empty_pct,
            "third_party": third_party[:10], "finding": finding}


assert interpret_referer([{"referer": "http://evil.com/", "bytes_gb": "9"}])["verdict"] == "third_party"  # normal
assert interpret_referer([{"referer": "-", "bytes_gb": "9"}])["verdict"] == "mostly_empty"  # normal
assert interpret_referer([{"referer": "http://mine.com/", "bytes_gb": "9"}],
                         ["mine.com"])["verdict"] == "own_or_mixed"  # normal: owner domain excluded
assert interpret_referer([{"referer": "http://mine.com/", "bytes_gb": "9"}])["verdict"] == "third_party"  # boundary: no owner list -> treated as third party
assert interpret_referer([])["verdict"] == "no_data"  # invalid: empty
assert interpret_referer(None, None)["verdict"] == "no_data"  # invalid: None


def classify_user_agents(rows: list) -> dict:
    """Step 3: are the clients browsers or scripts?

    The decisive combination from real tickets is a scripting UA carrying
    the owner's OWN site as referer: the business front-end was bypassed and
    the storage layer is being hit directly with the owner's credentials or
    a public grant.
    """
    clean = clean_rows(rows)
    scripting, browser, other = [], [], []
    for row in clean:
        ua = str(row.get("user_agent") or "").strip()
        entry = {"user_agent": ua, "cnt": to_number(row.get("cnt")),
                 "bytes_gb": to_number(row.get("bytes_gb"))}
        low = ua.lower()
        if is_nullish(ua):
            other.append(entry)
        elif any(t in low for t in _SCRIPTING_UA_TOKENS):
            scripting.append(entry)
        elif any(t in low for t in _BROWSER_UA_TOKENS):
            browser.append(entry)
        else:
            other.append(entry)
    total = sum(to_number(r.get("cnt")) for r in clean)
    script_cnt = sum(e["cnt"] for e in scripting)
    share = round(script_cnt * 100.0 / total, 1) if total > 0 else 0.0
    return {
        "verdict": ("scripted" if share >= 50.0 else "browser" if total > 0
                    and sum(e["cnt"] for e in browser) * 100.0 / total >= 50.0
                    else "mixed" if total > 0 else "no_data"),
        "scripting_share_pct": share,
        "scripting": sorted(scripting, key=lambda e: e["bytes_gb"],
                            reverse=True)[:10],
        "browser": sorted(browser, key=lambda e: e["bytes_gb"],
                          reverse=True)[:10],
        "other": sorted(other, key=lambda e: e["bytes_gb"], reverse=True)[:10],
    }


_U = classify_user_agents([{"user_agent": "python-requests/2.31", "cnt": "90"},
                           {"user_agent": "Mozilla/5.0", "cnt": "10"}])
assert _U["verdict"] == "scripted" and _U["scripting_share_pct"] == 90.0  # normal
assert classify_user_agents([{"user_agent": "Mozilla/5.0", "cnt": "9"}])["verdict"] == "browser"  # normal
assert classify_user_agents([{"user_agent": "-", "cnt": "9"}])["verdict"] == "mixed"  # boundary: nullish UA is neither
assert classify_user_agents([])["verdict"] == "no_data"  # invalid: empty
assert classify_user_agents([{"user_agent": "aliyun-sdk-java/0.6.53", "cnt": "5"}])["scripting_share_pct"] == 100.0  # boundary: SDK counts as scripted


def interpret_daily_trend(rows: list) -> dict:
    """Step 1d: classify the daily-volume shape into the three-pattern table
    (ported verbatim in semantics from the internal traffic-abuse playbook):

      burst     one day is 3x+ the median of the other days -- a specific
                trigger event (the link got shared / a scraper found it)
      sustained every day high and stable -- long-running business
                consumption, or a long-lived scrape that never stops
      spiky     large fluctuations with sharp peaks -- batch-pull scraping,
                the classic theft signature

    The shape NARROWS the root cause before the per-request steps are read;
    it never replaces them (auth mode / Top-IP remain the conclusion basis).
    """
    clean = clean_rows(rows)
    days = []
    for r in clean:
        weight = to_number(r.get("bytes_gb") if r.get("bytes_gb") is not None
                           else r.get("cnt"))
        day = str(r.get("day") or "").strip()
        if weight > 0:
            days.append((day, weight))
    if len(days) < 2:
        return {"verdict": "no_data", "pattern": "", "peak_day": "",
                "peak_value": 0.0, "max_min_ratio": None,
                "finding": "fewer than two non-zero days in the window -- no "
                           "trend shape to classify"}

    def _median(xs):
        xs = sorted(xs)
        n = len(xs)
        return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0

    vals = [v for _, v in days]
    peak_day, peak_val = max(days, key=lambda dv: dv[1])
    other_vals = [v for d, v in days if d != peak_day]
    other_median = _median(other_vals) if other_vals else 0.0
    ratio = (round(max(vals) / min(vals), 1) if min(vals) > 0 else None)
    if other_median > 0 and peak_val >= 3.0 * other_median:
        pattern = "burst"
        finding = (f"day {peak_day} carries {round(peak_val / other_median, 1)}x "
                   "the median of the other days -- a specific trigger event "
                   "(the bucket link got shared / a scraper found it), not a "
                   "long-running pattern. Check what changed on that day.")
    elif ratio is not None and ratio >= 3.0:
        pattern = "spiky"
        finding = ("daily volume fluctuates widely with sharp peaks "
                   f"(max/min = {ratio}x) -- the batch-pull shape, the "
                   "classic scraping signature: enumerate everything, pause, "
                   "repeat. Read the per-request steps (auth mode, Top IP by "
                   "bytes) before naming the actor.")
    else:
        pattern = "sustained"
        finding = ("volume is high and stable across every day in the "
                   "window -- either long-running business consumption or a "
                   "long-lived scrape. Cross-read the endpoint split: "
                   "internal + stable is the owner's own workload; public + "
                   "stable needs the auth-mode step to separate a signed "
                   "integration from an abuser holding a credential.")
    return {"verdict": "trend", "pattern": pattern, "peak_day": peak_day,
            "peak_value": peak_val, "max_min_ratio": ratio,
            "finding": finding}


# Three-pattern classification (cse judgment table, thresholds verbatim).
assert interpret_daily_trend(
    [{"day": "d1", "bytes_gb": "10"}, {"day": "d2", "bytes_gb": "3"},
     {"day": "d3", "bytes_gb": "3"}])["pattern"] == "burst"  # normal
assert interpret_daily_trend(
    [{"day": "d1", "bytes_gb": "10"}, {"day": "d2", "bytes_gb": "9"},
     {"day": "d3", "bytes_gb": "10"}])["pattern"] == "sustained"  # normal
assert interpret_daily_trend(
    [{"day": "d1", "bytes_gb": "10"}, {"day": "d2", "bytes_gb": "1"},
     {"day": "d3", "bytes_gb": "10"}])["pattern"] == "spiky"  # normal: two peaks
assert interpret_daily_trend(
    [{"day": "d1", "cnt": "5"}, {"day": "d2", "cnt": "7"}])["pattern"] == "sustained"  # boundary: cnt weight fallback
assert interpret_daily_trend([{"day": "d1", "bytes_gb": "5"}])["pattern"] == ""  # boundary: single day
assert interpret_daily_trend([])["verdict"] == "no_data"  # invalid: empty
assert interpret_daily_trend(None)["verdict"] == "no_data"  # invalid: None
assert interpret_daily_trend(
    [{"day": "d1", "bytes_gb": "0"}, {"day": "d2", "bytes_gb": "0"}])["verdict"] == "no_data"  # invalid: all zero


# ---------------------------------------------------------------------------
# Conclusion
# ---------------------------------------------------------------------------

_BENIGN_CONCLUSION = "normal-business-traffic"


def conclude_root_cause(cdn: dict, auth: dict, endpoint: dict,
                        ips: dict, referer: dict, ua: dict,
                        effectively_public: bool = False,
                        daily_trend: dict | None = None) -> dict:
    """Combine the per-step interpretations into ONE ranked conclusion.

    Returns {"conclusion", "severity", "evidence", "benign_possible"}.
    Severity uses the five-row feature-combination matrix, which includes an
    explicit BENIGN row: stating "this looks like normal business traffic"
    is a required capability, because over-diagnosing legitimate volume as
    an attack is itself a defect on a security skill. `daily_trend` (step 1d
    three-pattern shape) is advisory evidence only: it narrows the cause
    but never changes the conclusion ranking.
    """
    evidence = []
    for part in (cdn, auth, endpoint, ips, referer, ua, daily_trend):
        finding = (part or {}).get("finding")
        if finding:
            evidence.append(finding)

    cdn_v = (cdn or {}).get("verdict")
    auth_v = (auth or {}).get("verdict")
    endpoint_v = (endpoint or {}).get("verdict")
    ip_v = (ips or {}).get("verdict")
    ref_v = (referer or {}).get("verdict")
    ua_v = (ua or {}).get("verdict")

    if cdn_v == "all_cdn":
        return {
            "conclusion": "cdn-origin-pull",
            "severity": "medium",
            "benign_possible": True,
            "evidence": evidence,
            "statement": "The volume is CDN origin-pull, not direct client "
                         "abuse: every OSS-side client IP is a CDN edge node. "
                         "Diagnose the CDN domain's cache-hit rate instead -- "
                         "a low hit rate makes the origin fetch every object "
                         "and looks exactly like an attack on the OSS bill.",
        }
    if endpoint_v == "mostly_internal" and ip_v != "concentrated":
        return {
            "conclusion": _BENIGN_CONCLUSION,
            "severity": "low",
            "benign_possible": True,
            "evidence": evidence,
            "statement": "The evidence supports a BENIGN conclusion: the "
                         "traffic reached OSS over the intranet / from inside "
                         "a VPC and no single external host dominates. "
                         "Intranet traffic is not billed as internet-outbound "
                         "and cannot be generated by an external abuser, so "
                         "this is most likely the owner's own workload. "
                         "Confirm which internal service is pulling before "
                         "taking any containment action -- do not lock down a "
                         "bucket that is serving legitimate traffic.",
        }
    if auth_v == "anonymous" and effectively_public:
        return {
            "conclusion": "public-read-scraping",
            "severity": "high",
            "benign_possible": False,
            "evidence": evidence,
            "statement": "Anonymous (unsigned) requests are succeeding on a "
                         "bucket whose effective configuration is public: "
                         "anyone on the internet can download without a "
                         "credential. Remove the public grant itself (ACL "
                         "and any anonymous policy statement), then block the "
                         "abusive ranges from the bytes-ranked Top-IP result.",
        }
    if auth_v == "anonymous" and not effectively_public:
        return {
            "conclusion": "anonymous-attempt-blocked",
            "severity": "medium",
            "benign_possible": True,
            "evidence": evidence,
            "statement": "Requests are unsigned, but the exposure audit shows "
                         "the bucket is NOT effectively public (Block Public "
                         "Access, Requester Pays, or a private ACL with no "
                         "anonymous policy grant). Those attempts are being "
                         "rejected, so this is probing noise rather than a "
                         "successful breach -- keep the neutralizer in place "
                         "and remove the latent public grant.",
        }
    if ref_v == "third_party":
        return {
            "conclusion": "hotlinking",
            "severity": "high" if (ips or {}).get("top_by_bytes_share_pct", 0) < 50
            else "medium",
            "benign_possible": False,
            "evidence": evidence,
            "statement": "Third-party sites are embedding this bucket's "
                         "objects directly (bandwidth theft). Set a Referer "
                         "whitelist in the bucket's Anti-Hotlink "
                         "configuration -- a bucket policy cannot express "
                         "this, there is no acs:Referer condition key.",
        }
    if auth_v == "presigned_url":
        return {
            "conclusion": "signed-url-leak",
            "severity": "high",
            "benign_possible": False,
            "evidence": evidence,
            "statement": "The volume is driven by presigned URLs. A signed "
                         "URL that was posted publicly or cached by a third "
                         "party lets anyone download until it expires, and "
                         "rotating the AccessKey does NOT invalidate URLs "
                         "already issued under the old signature. Shorten the "
                         "expiry, stop publishing the URLs, and re-issue.",
        }
    if auth_v == "credentialed" and ua_v == "scripted" and ip_v == "concentrated":
        return {
            "conclusion": "ak-leak",
            "severity": "high",
            "benign_possible": False,
            "evidence": evidence,
            "statement": "A credential is being used by a scripted client "
                         "concentrated on few hosts. If the owner does not "
                         "recognise the access id, treat it as a leaked "
                         "AccessKey: disable and rotate it, then narrow the "
                         "RAM policy to the minimum object actions instead of "
                         "only rotating -- a rotated key re-leaks the same way.",
        }
    if ip_v == "concentrated" and not ips.get("top_by_bytes_is_private"):
        return {
            "conclusion": "public-read-scraping" if effectively_public
            else "bulk-download-single-source",
            "severity": "high" if effectively_public else "medium",
            "benign_possible": not effectively_public,
            "evidence": evidence,
            "statement": "One external host accounts for the majority of "
                         "bytes. Block that IP/CIDR with a Bucket Policy "
                         "Deny (see containment_policy_template) and set the "
                         "outbound-traffic alarm. If the bucket is not "
                         "effectively public this may still be a legitimate "
                         "partner or the owner's own egress -- confirm before "
                         "blocking.",
        }
    return {
        "conclusion": "inconclusive",
        "severity": "low",
        "benign_possible": True,
        "evidence": evidence,
        "statement": "The log evidence in this window does not single out an "
                     "abuse pattern: no CDN-only volume, no anonymous "
                     "success on a public bucket, no third-party referer, and "
                     "no single dominant host. Widen the window (up to the "
                     "7-day retention), or re-rank by bytes, before "
                     "concluding -- and state plainly to the customer that "
                     "no attack is evidenced rather than implying one.",
    }


assert conclude_root_cause({"verdict": "all_cdn"}, {}, {}, {}, {}, {})["conclusion"] == "cdn-origin-pull"  # normal
_B = conclude_root_cause({"verdict": "no_cdn"}, {"verdict": "credentialed"},
                         {"verdict": "mostly_internal"}, {"verdict": "dispersed"},
                         {"verdict": "own_or_mixed"}, {"verdict": "mixed"})
assert _B["conclusion"] == "normal-business-traffic" and _B["severity"] == "low"  # normal: the benign row is reachable
assert _B["benign_possible"] is True
_A2 = conclude_root_cause({"verdict": "no_cdn"}, {"verdict": "anonymous"},
                          {"verdict": "mostly_public"}, {"verdict": "concentrated"},
                          {"verdict": "mostly_empty"}, {"verdict": "scripted"},
                          effectively_public=True)
assert _A2["conclusion"] == "public-read-scraping" and _A2["severity"] == "high"  # normal
_N = conclude_root_cause({"verdict": "no_cdn"}, {"verdict": "anonymous"},
                         {"verdict": "mostly_public"}, {"verdict": "dispersed"},
                         {"verdict": "mostly_empty"}, {"verdict": "mixed"},
                         effectively_public=False)
assert _N["conclusion"] == "anonymous-attempt-blocked" and _N["benign_possible"] is True  # boundary: neutralized
_H = conclude_root_cause({"verdict": "no_cdn"}, {"verdict": "credentialed"},
                         {"verdict": "mostly_public"}, {"verdict": "concentrated"},
                         {"verdict": "own_or_mixed"}, {"verdict": "scripted"})
assert _H["conclusion"] == "ak-leak" and _H["severity"] == "high"  # normal: scripted + concentrated + credential
assert conclude_root_cause({}, {}, {}, {}, {}, {})["conclusion"] == "inconclusive"  # invalid: no evidence
assert conclude_root_cause(None, None, None, None, None, None)["severity"] == "low"  # invalid: None everywhere -> never claims high
assert all(conclude_root_cause({"verdict": v}, {}, {}, {}, {}, {})["severity"]
           in ("low", "medium", "high") for v in ("all_cdn", "mixed", "no_cdn",
                                                  "no_data", ""))  # invariant: severity always valid


# Step id (as generated by build_sls_queries) -> interpreter binding.
_COUNT_STEP = "2-top-client-ip"
_BYTES_STEP = "2b-top-client-ip-by-bytes"
_ENDPOINT_STEPS = ("1b-endpoint-split", "1c-vpc-split")


def summarize_log_evidence(plan: dict,
                           effectively_public: bool = False) -> dict:
    """Fold an executed query plan into one evidence bundle.

    Pure and total: it never raises, never calls the network, and reports
    honestly when there is nothing to interpret. A plan that did not execute
    (real-time log not enabled, permission denied, window over the scan cap)
    yields `conclusion="not_executed"` carrying the plan's own note, so the
    caller can relay the reason instead of silently dropping the leg.
    """
    plan = plan if isinstance(plan, dict) else {}
    outcome = str(plan.get("outcome") or "")
    results = [r for r in (plan.get("results") or []) if isinstance(r, dict)]
    rows_by_step = {str(r.get("step") or ""): r.get("rows") or []
                    for r in results}
    if outcome != "ok" or not results:
        return {
            "executed": bool(plan.get("executed")),
            "outcome": outcome or "not_executed",
            "conclusion": "not_executed",
            "severity": "unknown",
            "benign_possible": None,
            "statement": str(plan.get("note") or
                             "the real-time-log queries were not executed, so "
                             "no log-based conclusion is available; the "
                             "exposure audit and the query sequence in this "
                             "report remain the basis for action"),
            "steps": {},
            "empty_steps": sorted(rows_by_step),
            "evidence": [],
        }

    cdn = interpret_cdn_mix(rows_by_step.get("0-cdn-origin-check", []))
    auth = interpret_auth_mode(rows_by_step.get("1-auth-mode", []))
    endpoint_rows = []
    for step in _ENDPOINT_STEPS:
        endpoint_rows = rows_by_step.get(step) or []
        if endpoint_rows:
            break
    endpoint = interpret_endpoint_split(endpoint_rows)
    ips = interpret_ip_concentration(rows_by_step.get(_COUNT_STEP, []),
                                     rows_by_step.get(_BYTES_STEP, []))
    referer = interpret_referer(rows_by_step.get("4-referer", []))
    ua = classify_user_agents(rows_by_step.get("3-user-agent", []))
    trend = interpret_daily_trend(rows_by_step.get("1d-daily-trend", []))

    conclusion = conclude_root_cause(cdn, auth, endpoint, ips, referer, ua,
                                     effectively_public=effectively_public,
                                     daily_trend=trend)
    empty_steps = sorted(step for step, rows in rows_by_step.items()
                         if not rows)
    conclusion["executed"] = True
    conclusion["outcome"] = outcome
    conclusion["steps"] = {
        "cdn_mix": cdn, "auth_mode": auth, "endpoint_split": endpoint,
        "ip_concentration": ips, "referer": referer, "user_agent": ua,
        "daily_trend": trend,
    }
    conclusion["empty_steps"] = empty_steps
    if empty_steps:
        conclusion["statement"] += (
            f" ({len(empty_steps)} statement(s) returned no rows in this "
            f"window: {', '.join(empty_steps)} -- an empty result is evidence "
            "of absence only within the queried window, not proof that "
            "nothing happened.)")
    return conclusion


_SYNTH_OK = {
    "outcome": "ok", "executed": True, "note": "5 statement(s) executed",
    "results": [
        {"step": "0-cdn-origin-check", "rows": [{"sync_request": "-", "req_count": "439"}]},
        {"step": "1-auth-mode", "rows": [{"sign_type": "NotSign", "access_id": "-", "cnt": "400"}]},
        {"step": "1b-endpoint-split", "rows": [{"endpoint_type": "public", "bytes_gb": "9.0"}]},
        {"step": _COUNT_STEP, "rows": [{"client_ip": "47.1.1.1", "cnt": "400"}]},
        {"step": _BYTES_STEP, "rows": [{"client_ip": "47.1.1.1", "bytes_gb": "9.0"}]},
        {"step": "3-user-agent", "rows": [{"user_agent": "python-requests/2.31", "cnt": "400"}]},
        {"step": "4-referer", "rows": [{"referer": "-", "bytes_gb": "9.0"}]},
    ],
}
_S = summarize_log_evidence(_SYNTH_OK, effectively_public=True)
assert _S["conclusion"] == "public-read-scraping" and _S["severity"] == "high"  # normal: full chain
assert _S["executed"] is True and _S["steps"]["auth_mode"]["anonymous_share_pct"] == 100.0  # normal
assert _S["empty_steps"] == []  # normal: every step returned rows
assert summarize_log_evidence({"outcome": "not_enabled", "executed": False,
                               "note": "real-time log is NOT enabled",
                               "results": []})["conclusion"] == "not_executed"  # boundary: not enabled
assert "NOT enabled" in summarize_log_evidence(
    {"outcome": "not_enabled", "note": "real-time log is NOT enabled",
     "results": []})["statement"]  # boundary: the reason is relayed, not dropped
assert summarize_log_evidence({})["conclusion"] == "not_executed"  # invalid: empty plan
assert summarize_log_evidence(None)["severity"] == "unknown"  # invalid: None
assert summarize_log_evidence({"outcome": "ok", "results": [
    {"step": "1-auth-mode", "rows": []}]})["empty_steps"] == ["1-auth-mode"]  # boundary: empty step named
assert summarize_log_evidence({"outcome": "ok", "results": ["junk", None]})["conclusion"] == "not_executed"  # invalid: junk results
_PARTIAL = summarize_log_evidence({"outcome": "ok", "executed": True, "results": [
    {"step": "0-cdn-origin-check", "rows": [{"sync_request": "cdn", "req_count": "10"}]}]})
assert _PARTIAL["conclusion"] == "cdn-origin-pull"  # normal: one decisive step is enough
assert _PARTIAL["empty_steps"] == [] and "no rows" not in _PARTIAL["statement"]
