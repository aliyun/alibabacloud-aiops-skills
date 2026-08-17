# CDN Cache Rules Reference

This document is derived from Alibaba Cloud CDN official documentation, describing CDN node caching behavior.

## Cache Decision Flow (by priority, high to low)

```
Request reaches CDN node
|
+- 1. Origin forces no-cache: Pragma: no-cache / Cache-Control: no-cache / no-store / max-age=0
|     -> Not cached (unless "ignore origin no-cache" is enabled)
|
+- 2. Console cache rules (directory/extension rules, sorted by weight)
|     -> Highest weight wins, stops matching on hit
|
+- 3. Follow origin cache policy (if rule enables "prefer origin cache policy")
|     -> Cache-Control > Expires > Last-Modified > ETag
|
+- 4. Default: not cached (no console rules and no origin cache headers)
```

## Console Cache Rule Priority

- **Weight**: 1-99, higher value = higher priority
- **Same weight**: earlier creation time wins
- **Stop on match**: once a rule matches, no further matching
- **Directory rules**: path prefix match, must start with `/`
- **Extension rules**: exact suffix match, no `.`, case-sensitive, comma-separated

## Origin Cache Header Priority

| Priority | Header | Description |
|----------|--------|-------------|
| 1 (highest) | `Cache-Control: s-maxage=N` | CDN-specific TTL, preferred over max-age |
| 2 | `Cache-Control: max-age=N` | General TTL |
| 3 | `Expires` | HTTP/1.0 compatible, lower priority than Cache-Control |
| 4 | `Last-Modified` | Dynamic TTL = (now - Last-Modified) x 0.1, range [10s, 3600s] |
| 5 (lowest) | `ETag` | Default TTL = 10 seconds |

## Status Code Cache Behavior

| Status Code | Default Cache Behavior | Notes |
|-------------|----------------------|-------|
| 200, 203, 206, 300, 301, 308, 410 | Cached per console/origin rules | Default cached |
| 204, 305, 404, 405, 414, 424, 429, 500, 501, 502, 503, 504 | Default cached 1 second | Requires: no Set-Cookie, no console rules, no origin cache headers |
| 302, 307, 403 | Default not cached | Same prerequisites as above |
| 304 | Never cached | Not configurable |

**Important**: When a response contains a Set-Cookie header, no status code will be cached.

## Directory Refresh Two Modes

| Mode | Behavior | Effect |
|------|----------|--------|
| Expire | Marks cache as expired; on next origin fetch, validates with conditional headers | If origin resource unchanged, returns 304, CDN keeps old cache |
| Force Delete | Directly deletes cache files; next request forces origin fetch | Ensures latest content |

**Key conclusion**: When directory refresh uses expire mode, if the origin Last-Modified or ETag has not changed, CDN receives 304 and continues serving old cache, causing refresh-not-effective symptoms.

## Refresh and Preload Effectiveness Criteria

- **File refresh**: Exact URL match; after refresh, first request fetches from origin, subsequent requests HIT
- **Directory refresh (expire mode)**: Marks expired but validates with origin; origin 304 means old cache persists
- **Directory refresh (force mode)**: Deletes cache; next request must go to origin
- **Preload**: Pre-fetches URL content to nodes; after preload, first request is HIT
- **Partial preload failure**: 90 percent or more node success shows 100 percent complete; a few nodes may fail
