# WAF Attack Analysis Checklist

Use this checklist when reviewing WAF configuration, WAF alerts, SLS traffic logs, business interface documentation, and user-provided samples. It ensures coverage; it does not imply that every category can be confirmed from WAF or SLS data alone.

## Analysis principles

1. Base conclusions only on supplied logs and context. Do not assume exploitation succeeded.
2. Distinguish attack probes, suspected attacks, blocked attacks, possible false negatives, and legitimate traffic incorrectly blocked.
3. Support each conclusion with available URI, parameter, method, user agent, header, body, status, response size, time distribution, source behavior, and rule evidence.
4. State missing fields and explain how they limit the conclusion.
5. Optimize security effectiveness and business accuracy rather than simply increasing the block rate.

## Business context to capture

- Business type, primary domains, APIs, pages, and sensitive operations
- Login, payment, upload, search, administrative, mobile, mini-program, and callback flows
- Normal traffic peaks, trusted sources, office egress, partners, scanners, and approved test sources
- Current WAF mode, enabled rules, custom rules, exceptions, rate limits, BOT controls, and known incidents

## Twenty attack categories

For each category, record `covered`, `not covered`, or `unverifiable`; list the queries run, blocked and allowed samples, evidence gaps, and confidence.

1. **SQL injection**: UNION, error-based, Boolean, time-based, stacked, encoded, JSON/XML/API, ORM/HQL, and NoSQL signatures.
2. **Cross-site scripting**: reflected, stored probes, DOM probes, SVG/HTML injection, event handlers, JavaScript URIs, and encoding bypasses.
3. **Command injection and RCE**: shell metacharacters, command chaining, operating-system commands, framework exploits, and component exploits.
4. **File inclusion and path traversal**: LFI, RFI, traversal encodings, and access to password, environment, configuration, or backup files.
5. **Malicious file upload**: WebShells, extension and MIME bypasses, double extensions, polyglots, archives, and abnormal upload frequency.
6. **SSRF**: internal addresses, cloud metadata, URL parameters, redirect or DNS tricks, and dangerous protocols such as `gopher`, `file`, or `dict`.
7. **XXE and XML attacks**: DOCTYPE, ENTITY, external entity loading, file reads, and XML-based SSRF.
8. **Template and expression injection**: SSTI, SpEL, OGNL, EL, Velocity, Freemarker, Jinja2, and Twig signatures.
9. **Deserialization**: Java, PHP, and .NET object signatures, gadget-chain indicators, and suspicious encoded objects.
10. **Authentication and session attacks**: brute force, credential stuffing, password spraying, session fixation, cookie or JWT tampering, and abnormal login frequency.
11. **Access control and business logic abuse**: BOLA/IDOR, vertical privilege escalation, identifier enumeration, price or quantity tampering, and unexpected access to sensitive functions.
12. **API attacks**: parameter pollution, GraphQL introspection or depth abuse, malformed JSON, bulk scraping, token abuse, and forged callbacks.
13. **WebShell and backdoor access**: common parameters, execution functions, known management clients, encrypted patterns, and frequent small POST requests.
14. **Scanners and automated probing**: Nuclei, AWVS, AppScan, Burp Suite, sqlmap, xray, Nessus, OpenVAS, directory scanners, and anomalous user agents or status distributions.
15. **Sensitive files and directories**: version-control metadata, environment files, backups, debug pages, Swagger, Actuator, Druid, admin consoles, and test endpoints.
16. **Middleware and framework exploits**: Apache, Nginx, IIS, Tomcat, JBoss, WebLogic, Spring, Struts, ThinkPHP, Fastjson, Log4j, Shiro, WordPress, Jenkins, and version disclosure.
17. **Protocol and request anomalies**: request smuggling signals, malformed headers, Host attacks, CRLF, parameter pollution, oversized fields, mixed encoding, unexpected content types, and unusual methods.
18. **Crawler and resource abuse**: high-frequency access, bulk pagination, search abuse, verification-code abuse, message abuse, inventory scraping, and slow resource exhaustion.
19. **Application-layer CC or DDoS**: single-source bursts, distributed low-rate aggregation, hotspot URI anomalies, dynamic endpoint concentration, errors, latency, large responses, and cache bypasses.
20. **WAF bypass techniques**: URL and double encoding, Unicode, case changes, comments, whitespace, chunked transfer, nested JSON/XML, parameter-name mutation, and payloads in headers, cookies, or multipart bodies.

## False-positive review

Review blocked requests involving:

- Search, rich text, comments, tickets, code, SQL, or log fragments
- Legitimate uploads, structured JSON, long parameters, and special encodings
- Partner callbacks, internal testing, and authorized administrative operations
- Large bodies or uncommon but valid methods and content types

For each sample, record the matched rule, business purpose, impact, evidence, and the narrowest safe option: parameter, path, method, source, observation mode, or no exception.

## False-negative review

Review allowed traffic for:

- Clear attack signatures, encoded bypasses, and payloads in headers, cookies, bodies, JSON, XML, or multipart fields
- Slow, low-frequency, or distributed attacks
- Business-logic abuse and scanner behavior not correlated by existing controls

For each sample, record the suspected category, likely detection gap, severity, recommended control, validation metric, and whether identity, BOT, rate limiting, or business risk controls are required.

## Rule-tuning output

Organize recommendations into rule retention, strengthening, noise reduction, new rules, rate limiting, trusted or suspicious sources, and phased rollout. Every proposed change must include scope, priority, validation metric, observation period, rollback condition, and any application-side dependency.
