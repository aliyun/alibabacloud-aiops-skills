# Cross-Skill Diagnostic Linkage

Scenarios where CDN refresh and preload diagnosis interacts with other diagnostic capabilities.

## Scenario I: Refresh Not Effective + Cache Configuration

Primary capability: refresh-preload
Linkage: performance diagnostics (if cache TTL config needs checking after ruling out refresh issues)

Diagnostic path:
1. Query refresh task records, confirm refresh type and status
2. If directory refresh + origin 304, reference cache-rules.md to explain directory refresh mode differences
3. If refresh is normal but content persists, check cache TTL configuration

## Scenario J: Preload Not Effective + Origin Policy

Primary capability: refresh-preload
Linkage: reference cache-rules.md

Diagnostic path:
1. Query preload task records, confirm status
2. Bound origin probe: check origin Cache-Control / status code / Set-Cookie
3. Reference cache-rules.md for CDN cache priority and status code cache behavior

## Signal to Capability Mapping (Refresh and Preload Related)

| User-Observable Symptom | Primary Capability | Reference |
|------------------------|-------------------|-----------|
| Refresh not effective + directory refresh | refresh-preload | cache-rules.md |
| Refresh not effective + cache config | refresh-preload | cache-rules.md |
| Preload not effective + origin no-cache | refresh-preload | cache-rules.md |
| Content not updated + low hit rate | performance | cache-rules.md, refresh-preload |
