# Static Website Hosting Configuration Playbook

Reference for interpreting the `GetBucketWebsite` evidence returned by
`scripts/static_website_diagnosis.py`: IndexDocument / ErrorDocument
semantics, common homepage / 404 rule defects, and SPA redirect patterns.

## 1. What GetBucketWebsite returns

| Field | XML element | Meaning |
|---|---|---|
| `index_file` | `IndexDocument.Suffix` | The default homepage object served when a request targets the bucket root or a directory path, e.g. `index.html` |
| (sub-dir switch) | `IndexDocument.SupportSubDir` | `true` -> a `/subdir/` request serves `subdir/index.html`; `false` (DEFAULT) -> every `/`-suffixed path serves the ROOT homepage `index.html` (official putbucketwebsite) |
| (404 rule) | `IndexDocument.Type` | Enum, ONLY effective when `SupportSubDir=true`, evaluated AFTER RoutingRule and BEFORE ErrorFile. Defines behaviour for a non-`/`-suffixed object that does NOT exist (see section 2) |
| `error_file` | `ErrorDocument.Key` | The custom 404 page object served when the requested object does not exist, e.g. `error.html` |
| (error status) | `ErrorDocument.HttpStatus` | HTTP status returned WITH the error page. Values: `200`, `404` (DEFAULT) (official putbucketwebsite) |
| `routing_rules` | `RoutingRules.RoutingRule` | Conditional redirect / mirror rules; up to 20 rules matched in `RuleNumber` order, first match wins (see section 4) |

Extraction-scope note (doc-code honesty, G-1): the diagnosis script
(`scripts/static_website_diagnosis.py` + `scripts/_oss_client.py`) currently
surfaces ONLY `index_file`, `error_file` and the `routing_rules`
prefix/redirect-type summary. It does NOT parse `SupportSubDir`, `Type`
or `HttpStatus` out of the `GetBucketWebsite` XML. The three fields are
documented here so the Agent can explain them and, when the raw XML is
available in evidence, read them directly; do NOT claim the script reports
them.

G-1 extension evaluation (2026-09-07, P2 batch): **EXEMPT — high cost, low
value.** Root cause: oss2 SDK 2.19.1 `parse_get_bucket_website()` only
extracts `IndexDocument/Suffix`, `ErrorDocument/Key` and `RoutingRules`; the
three target fields are present in the XML response but NOT surfaced as Python
attributes. Extraction would require either (a) calling the private
`_Bucket__do_bucket` method and re-parsing the raw XML, (b) issuing a
duplicate signed HTTP GET `/?website` outside oss2, or (c) monkey-patching
`oss2.xml_utils.parse_get_bucket_website` — all fragile across SDK versions
and doubling the API call count. Diagnostic value is LOW because sections 2.1
and 3 below already give the Agent complete knowledge to explain these fields
from the evidence XML or console screenshots. Decision: retain this
knowledge-layer annotation; do NOT extend the script extractor.

When the bucket has NO hosting configuration at all, OSS returns HTTP 404
with code `NoSuchWebsiteConfiguration` (measured 2026-08-27 with the oss2
SDK against a bucket that never enabled hosting). The diagnosis script maps
this to `verdict.hosting_state = "not_configured"` — a legitimate finding,
not a query failure.

## 2. IndexDocument (homepage rule) semantics

- Only takes effect AFTER static website hosting is enabled on the bucket.
- Applies to root path (`/`) and directory-style paths (`/docs/`); the
  bucket (or matching object ACL) must allow anonymous read, otherwise the
  request fails with 403 before the homepage rule can apply.
- The referenced object must:
  1. exist at the exact key (commonly the bucket root, `index.html`);
  2. carry `Content-Type: text/html` — an object uploaded as
     `application/octet-stream` renders the homepage rule correctly but the
     browser may still download it;
  3. be non-empty — a zero-byte homepage produces a blank page.
- Typical defects the diagnosis surfaces:
  - hosting enabled but `index_file` empty -> root path has no default page;
  - `index_file` names `index.html` while the actual object is
    `home.html` or lives under a prefix -> rule matches nothing.

### 2.1 SupportSubDir + Type: the three official "file 404 rules" (G-1)

`SupportSubDir` decides whether a `/subdir/` request serves the SUB-directory
homepage or falls back to the ROOT homepage. When `SupportSubDir=true`, the
`Type` enum decides what happens for a request whose URL does NOT end in `/`
(an "object request", e.g. `.../abc`) and whose object `abc` does NOT exist.
`Type` is evaluated AFTER RoutingRule and BEFORE ErrorFile. Official
putbucketwebsite + hosting-static-websites map the API enum to the console
"File 404 Rule" names as follows (assuming homepage `index.html`, request
`.../abc` where object `abc` is missing):

| `Type` | Console name | Behaviour when `abc` does not exist |
|---|---|---|
| `0` (DEFAULT) | **Redirect** (redirect-to-directory) | Check `abc/index.html`: if it exists return **302** with `Location` = the URL-encoded `/abc/`; if not, return 404 and continue to ErrorFile |
| `1` | **NoSuchKey** (return-404-directly) | Strictest: always return **404** `NoSuchKey` regardless of any directory homepage, then continue to ErrorFile |
| `2` | **Index** (return-homepage-content) | Check `abc/index.html`: if it exists return that object's CONTENT with **200** (address bar unchanged); if not, return 404 and continue to ErrorFile |

Key distinction the Agent must not blur: `Type=0` (Redirect) changes the
browser address bar via a 302 to the trailing-slash directory, whereas
`Type=2` (Index) keeps the address bar and returns the homepage body inline
with 200. `Type=1` (NoSuchKey) never serves a directory homepage.

## 3. ErrorDocument (404 page rule) semantics

- Optional. When unset, OSS returns the raw XML error body
  (`<Error><Code>NoSuchKey>...`) on missing pages.
- The error page object itself must be anonymously readable and ideally
  `text/html`; otherwise the visitor sees the raw XML again.
- OSS returns the ErrorDocument for 404-class object misses only; it does
  not intercept 403 (permission) responses.
- `ErrorDocument.HttpStatus` (values `200` / `404`, DEFAULT `404`) sets the
  status code returned WITH the error page. The default `404` is correct for
  a genuine "page not found"; `200` is used deliberately for the SPA fallback
  (section 4) so the browser treats the returned `index.html` as a normal
  navigation and the client-side router takes over instead of showing an
  error. Choosing `200` on a non-SPA site hides real 404s from crawlers and
  monitoring, so it is a trade-off, not a default recommendation.

## 4. SPA (single-page application) redirect patterns

Static hosting of SPAs (Vue / React router in history mode) needs routing
rules so that unknown paths fall back to the app shell instead of 404:

- **Official simplest approach (hosting-static-websites, RECOMMENDED, G-4)**:
  you do NOT need any RoutingRule at all. Set Default Homepage to
  `index.html`, keep Sub-directory Homepage **Not Enabled**
  (`SupportSubDir=false`), set Default 404 Page to
  **`index.html`** (the key move: every unmatched route returns the app
  shell), and set Error Document Response Code to **200** (`HttpStatus=200`,
  so the router sees a normal navigation). Official wording (translated):
  "set the Default 404 Page to index.html (the key configuration: makes every
  route redirect to the application entry); select 200 for the Error Document
  Response Code".
  This is the lowest-risk SPA config and should be suggested first.
- **Redirect-style fallback**: a RoutingRule matching all keys (empty
  prefix) with redirect target `/index.html` — every unknown path lands on
  the SPA entry, and the client-side router takes over.
- **Mirror / key-substitution style**: `ReplaceKeyWith` rewrite
  (e.g. prefix `app/` -> `app/index.html`) for directory-shaped apps.
- The diagnosis script lists each routing rule's prefix and redirect type in
  `website.routing_rules` so the Agent can verify whether a fallback rule
  exists at all.

### 4.1 RoutingRule field reference (official putbucketwebsite, G-4)

Up to **20** RoutingRules, matched in ascending `RuleNumber` order; the first
matching rule executes and the rest are skipped. A rule matches only when ALL
of its `Condition` nodes are satisfied.

- `Condition`:
  - `KeyPrefixEquals` — object key must start with this prefix.
  - `KeySuffixEquals` — object key must end with this suffix (empty default =
    no suffix match).
  - `HttpErrorCodeReturnedEquals` — rule matches only when the request returns
    this status. **MUST be `404` when the redirect is a Mirror (mirror
    back-to-origin) rule.**
  - `IncludeHeader` (up to 10) — match on a request header `Key` + `Equals`.
- `Redirect`:
  - `RedirectType` — `Mirror` (mirror back-to-origin, supported on public + finance cloud),
    `External` (returns a 3xx to another address), or `AliCDN` (like External
    but adds a header Alibaba Cloud CDN consumes to fetch on the user's behalf
    instead of returning the 3xx).
  - `HttpRedirectCode` — `301` (DEFAULT) / `302` / `307`; only for
    `External` / `AliCDN`.
  - `Protocol` (`http` / `https`) and `HostName` — only for `External` /
    `AliCDN`.
  - `ReplaceKeyPrefixWith` / `EnableReplacePrefix` (default false) /
    `ReplaceKeyWith` (supports the `${key}` variable, e.g.
    `prefix/${key}.suffix`). Only ONE of `ReplaceKeyWith` or
    `ReplaceKeyPrefixWith` may be present; `EnableReplacePrefix=true` is not
    allowed together with a non-empty `ReplaceKeyWith`.
  - `PassQueryString` (default false) — carry the request query string into
    the redirect Location or the mirror back-to-origin request.
  - Mirror-only: `MirrorURL` (must start `http://`/`https://` and end `/`;
    REQUIRED for `Mirror`), `MirrorPassQueryString` (overrides
    `PassQueryString`), `MirrorFollowRedirect` (default true, follows up to 10
    source 3xx hops), `MirrorCheckMd5` (default false), and `MirrorHeaders`
    (`PassAll` / `Pass` / `Remove` / `Set` key-value, each list up to 10).

All of the above configurations are WRITE operations (`PutBucketWebsite`)
and therefore OUT OF SCOPE for this skill: it only reads and explains them.
Guide the user to the OSS console (Bucket -> Data Management -> Static
Pages) for any change.

## 5. Checklist used when interpreting the report

1. `hosting_state == not_configured` -> nothing to tune yet; enable hosting
   first (manual), then re-run the diagnosis.
2. `index_file` present but homepage blank/download -> verify object
   existence, Content-Type, and anonymous readability (probe evidence).
3. `error_file` absent -> advisory only: recommend adding a custom 404 page.
4. Routing rules absent for an SPA -> advisory: explain the fallback
   pattern above (manual configuration).
