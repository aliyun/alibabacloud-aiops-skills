# Referer Whitelist (Hotlink Protection) Rules

OSS hotlink protection restricts GET access by the request `Referer`
header via a whitelist and/or a blacklist. The OFFICIAL check order
is fixed: (1) empty-referer check, (2) BLACKLIST check, (3) whitelist
check — a referer that hits the blacklist is denied EVEN IF it also
matches the whitelist.

TRIGGER CONDITION (official "Quotas and limits" · "Trigger conditions"): OSS runs the
hotlink check ONLY for ANONYMOUS access or SIGNED-URL access to an
Object. API calls signed with an AccessKey (i.e. requests carrying an
`Authorization` header) are NOT subject to the referer rules. So a 403
attributed to referer rules never applies to a credentialed SDK/ossutil
caller — only to browser/anonymous/presigned-URL traffic.

The diagnosis script reads the real
configuration (both lists) with `GetBucketReferer` and attributes
false positives; configuration
changes stay manual (PutBucketReferer is ABSOLUTELY PROHIBITED for this
skill).

## 1. Configuration fields

| Field | Semantics |
|---|---|
| `AllowEmptyReferer` | Whether requests carrying NO Referer header are allowed |
| `RefererList` | Whitelist entries; `*` and `?` wildcards supported |
| `RefererBlacklist` | Blacklist entries (same wildcard rules); a hit DENIES the request and OUTRANKS the whitelist |
| `AllowTruncateQueryString` | When true, the referer is truncated at `?` before matching (query strings ignored) |

Hotlink protection is NOT configured only when BOTH lists are empty
(`referers=[]` AND `black_referers=[]`): every referer is allowed.
This is the OSS default and a normal configuration state, not an
error. A configured blacklist with an empty whitelist is still an
ACTIVE configuration (deny-list mode): non-blacklisted referers,
including empty referers when allowed, pass.

## 2. allow_empty_referer semantics (top false-positive cause)

Requests with NO Referer header include:

- typing / pasting the URL directly in the address bar,
- many mobile apps and WebView clients,
- privacy-stripping proxies or `Referrer-Policy: no-referrer` pages,
- downloads triggered by scripts without a referrer.

With `AllowEmptyReferer=false` AND a NON-EMPTY whitelist, ALL of the
above get 403. Official middle branch ("How it works" · empty-Referer check):
`AllowEmptyReferer=false` with an EMPTY whitelist (blacklist-only mode)
lets empty-referer requests PASS — they are denied ONLY when the
whitelist is non-empty. A user
reporting "after enabling hotlink protection I cannot open my own links
anymore" is almost always a denied-empty-referer case (deny-empty +
non-empty whitelist), not a malicious
request. Whitelisting cannot fix empty-referer clients; the only options
are `AllowEmptyReferer=true` or accepting the block.

## 3. Matching rules and the official evaluation order

Every request is evaluated in the fixed official order:

1. **Empty-referer check**: no Referer header — allowed when
   `AllowEmptyReferer=true`; when `AllowEmptyReferer=false` it is DENIED
   ONLY IF the whitelist is NON-EMPTY, and PASSES if the whitelist is
   empty (official middle branch: empty Referer NOT allowed AND whitelist
   empty -> request PASSES; empty Referer NOT allowed AND whitelist NON-EMPTY
   -> request DENIED). See section 2.
2. **Blacklist check**: the referer hits any blacklist entry -> 403,
   even if it also matches the whitelist. The blacklist OUTRANKS the
   whitelist.
3. **Whitelist check**: a matching entry allows the request; with a
   non-empty whitelist and no match -> 403. With an empty whitelist
   (blacklist-only configuration) every non-blacklisted referer is
   allowed.

Entry syntax (both lists):

- A host-only entry (no `/`) matches the
  referer's host; an entry containing `/` matches host+path. Official
  case-insensitivity applies ONLY to QueryString parameters (when
  `AllowTruncateQueryString=false`); the official doc does NOT state that
  host/scheme matching is case-insensitive, so do NOT rely on it (B-8).
- `*.example.com` covers subdomains of `example.com` but NOT other
  second-level domains, and NOT `example.com` itself if the entry is
  host-qualified. (Official gives only positive examples — `*.example.com`
  matches `http://www.example.com` / `https://help.example.com`; the
  host-only-vs-path and bare-domain-exclusion details are inferred from the
  wildcard semantics, measured 2026-09-03, not official doc text — H-1.)
- HTTP vs HTTPS in the entry matters when the entry includes the scheme
  (official, translated: "matching does NOT ignore the scheme; configuring
  http://www.aliyun.com will NOT match https://www.aliyun.com" — recommend
  adding BOTH HTTP and HTTPS versions).
- With `AllowTruncateQueryString=true` the query string is ignored for
  matching.

Size limit: the whitelist plus blacklist together must stay within
20 KB.

## 4. False-positive attribution verdicts

| Verdict | Meaning | Manual fix |
|---|---|---|
| `not_configured` | BOTH lists empty; referer rules cannot cause any 403 | none needed; look at ACL/policy instead |
| `allowed` | referer passes: not blacklisted, and whitelist matches (or whitelist empty) | 403 comes from ACL/permission, not referer |
| `denied_empty` | no Referer header + AllowEmptyReferer=false + NON-EMPTY whitelist (an empty whitelist passes empty referers) | set AllowEmptyReferer=true, or accept |
| `denied_blacklist` | the page referer HITS a blacklist entry (outranks any whitelist match) | remove/adjust the blacklist entry |
| `denied_mismatch` | referer present, not blacklisted, but the non-empty whitelist has no match | add a matching entry (wildcards supported) |

## 5. Standard template (text output only)

```xml
<RefererConfiguration>
  <AllowEmptyReferer>true</AllowEmptyReferer>
  <RefererList>
    <Referer>*.your-site.example.com</Referer>
  </RefererList>
  <RefererBlacklist>
    <Referer>*bad-site.example</Referer>
  </RefererBlacklist>
</RefererConfiguration>
```

Apply via OSS console (Permission -> Hotlink Protection) or PutBucketReferer
— manual operation. Production guidance: keep the whitelist as narrow as
possible, avoid bare `*` entries, and remember that referer headers can be
forged, so hotlink protection is a cost guard, not a security boundary.

Official production notes ("Apply to production" / "Quotas and limits"):

- **Bucket-level scope (G-10)**: referer rules take effect at the BUCKET
  level; you cannot configure different rules for individual objects or
  directories inside the bucket.
- **CDN cache bypass (G-6)**: when the bucket is accelerated by CDN, a
  hotlink request may hit the CDN edge cache and be served WITHOUT passing
  the OSS referer check. To keep the protection effective you MUST configure
  the SAME referer rules at the CDN layer (multi-layer defense). For the
  CDN-side configuration view (accelerated domain, origin type, edge cache)
  cross-refer to alibabacloud-oss-cdn-origin-config-diagnosis
  (references/bypass-detection.md · "reverse bypass").
- **Video playback (G-11)**: a browser native `<video>` tag issues BOTH a
  referer-carrying page request AND an EMPTY-referer media-data request; to
  play online video you MUST allow empty referers, otherwise playback breaks.
- **Referrer-Policy (already in section 2)**: modern browsers with
  `no-referrer` send no Referer and are treated as empty-referer requests.

## 6. SDK pitfall: version-dependent blacklist parsing

`oss2.Bucket.get_bucket_referer()` returns a `GetBucketRefererResult`
whose fields depend on the oss2 version and on what the XML actually
contains. Measured 2026-09-03 with **oss2 2.19.1**:
`xml_utils.parse_get_bucket_referer` sets `allow_empty_referer` and
`referers` unconditionally, and ALSO parses `black_referers` and
`allow_truncate_query_string` — but ONLY when the corresponding
`RefererBlacklist/Referer` / `AllowTruncateQueryString` nodes are present
in the response (they default to `[]` / `None` otherwise). OLDER oss2
surfaces exposed only `allow_empty_referer` + `referers` and silently
DROPPED `black_referers` / `allow_truncate_query_string`, so a
deny-list-configured bucket looked exactly like "hotlink protection not
configured" through such a client — and a blacklisted caller was
mis-attributed to ACL/policy. Because this behaviour is version-dependent,
the diagnosis script of this skill reads the missing fields explicitly and
evaluates the official three-step order, so a blacklist denial is never
silently lost regardless of the oss2 version in use.
