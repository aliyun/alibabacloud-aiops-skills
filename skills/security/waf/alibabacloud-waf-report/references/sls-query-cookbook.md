# SLS Query Cookbook for WAF Assessments

Adapt every query to the customer's indexed fields, business paths, and exact assessment interval. Thresholds are investigation starting points. Record the final query and interval in the evidence log.

## Baseline queries

### Action and rule distribution

```sql
* | select final_action, count(1) as cnt
  group by final_action order by cnt desc
```

```sql
* | select final_rule_id, final_rule_type, host, count(1) as cnt
  where final_action='block'
  group by final_rule_id, final_rule_type, host
  order by cnt desc limit 20
```

### Host and action matrix

```sql
* | select host,
    count(1) as total,
    sum(case when final_action='block' then 1 else 0 end) as blocked,
    sum(case when final_action='sigchl' then 1 else 0 end) as challenged,
    sum(case when final_action='captcha' then 1 else 0 end) as captcha
  group by host order by total desc limit 50
```

### Source concentration

```sql
* | select real_client_ip,
    count(1) as cnt,
    count(distinct(request_path)) as paths,
    count(distinct(host)) as hosts
  group by real_client_ip order by cnt desc limit 20
```

### Origin error distribution

```sql
* | select host, upstream_status, count(1) as cnt
  where upstream_status >= 400
  group by host, upstream_status order by cnt desc limit 50
```

### Hourly block pattern

```sql
* | select date_format(from_unixtime(__time__+28800),'%Y-%m-%d %H') as hour,
    count(1) as cnt
  where final_action='block'
  group by hour order by hour
```

## Twenty attack-category queries

Run both rule-hit queries and allowed-traffic signature searches where the fields are available. Treat signature searches as candidates, not proof.

### 1. SQL injection

```sql
final_action='block' AND final_rule_type='sqli'
  | select real_client_ip, host, request_path, querystring, final_rule_id limit 30
```

```sql
final_action:null AND
  (querystring:union OR querystring:select OR querystring:concat
   OR querystring:sleep OR querystring:benchmark)
  | select host, request_path, querystring, real_client_ip, upstream_status limit 30
```

### 2. Cross-site scripting

```sql
final_action='block' AND final_rule_type='xss'
  | select real_client_ip, host, request_path, querystring, final_rule_id limit 30
```

```sql
final_action:null AND
  (querystring:script OR querystring:onerror OR querystring:eval
   OR querystring:alert OR querystring:onload)
  | select host, request_path, querystring, real_client_ip, upstream_status limit 30
```

### 3. Command injection and RCE

```sql
final_action='block' AND final_rule_type IN ('code_exec','cmdi')
  | select real_client_ip, host, request_path, querystring, final_rule_id limit 30
```

### 4. File inclusion and path traversal

```sql
final_action='block' AND final_rule_type IN
  ('path_traversal','arbitrary_file_reading','lfilei')
  | select real_client_ip, host, request_path, querystring, final_rule_id limit 30
```

```sql
final_action:null AND
  (request_path:/etc/passwd OR request_path:../.. OR request_path:.env
   OR request_path:.git OR request_path:web.config)
  | select host, request_path, real_client_ip, http_user_agent, upstream_status limit 30
```

### 5. Malicious file upload

```sql
final_action='block' AND final_rule_type='arbitrary_file_uploading'
  | select real_client_ip, host, request_path, request_method, final_rule_id limit 30
```

### 6. SSRF

```sql
final_action:null AND
  (querystring:'url=http' OR querystring:'redirect=http'
   OR querystring:'callback=http' OR querystring:'target=http')
  | select host, request_path, querystring, real_client_ip, upstream_status limit 30
```

```sql
final_action:null AND querystring:http AND
  (querystring:'127.0.0.1' OR querystring:'169.254'
   OR querystring:'localhost' OR querystring:'100.100.100.200')
  | select host, request_path, querystring, real_client_ip, upstream_status limit 30
```

### 7. XXE and XML attacks

```sql
final_action='block' AND final_rule_type='xxe'
  | select real_client_ip, host, request_path, request_body, final_rule_id limit 20
```

### 8. Template and expression injection

```sql
final_action='block' AND final_rule_type='expression_injection'
  | select real_client_ip, host, request_path, querystring, final_rule_id limit 20
```

### 9. Deserialization

```sql
final_action='block' AND final_rule_type IN
  ('java_deserialization','php_deserialization','dot_net_deserialization')
  | select real_client_ip, host, request_path, request_body, final_rule_id limit 30
```

### 10. Authentication and session attacks

```sql
(request_path:*/login/token* OR request_path:*/signin* OR request_path:*/auth*)
  | select final_action, upstream_status, real_client_ip, count(1) as cnt
  group by final_action, upstream_status, real_client_ip
  order by cnt desc limit 30
```

### 11. Access control and business logic abuse

```sql
final_action:null AND
  (querystring:'orderId=' OR querystring:'userId='
   OR querystring:'shopId=' OR querystring:'productId=')
  | select real_client_ip, request_path,
    count(1) as cnt, count(distinct(querystring)) as unique_queries
  group by real_client_ip, request_path
  having unique_queries > 30
  order by unique_queries desc limit 20
```

### 12. API abuse

```sql
* | select real_client_ip, request_path, count(1) as cnt
  where final_action='null'
  group by real_client_ip, request_path
  having cnt > 10000
  order by cnt desc limit 30
```

### 13. WebShell and backdoor access

```sql
final_action='block' AND
  (request_path:eval OR request_path:assert OR request_path:shell_exec)
  | select real_client_ip, host, request_path, querystring, final_rule_id limit 30
```

### 14. Scanners and automated probing

```sql
final_action='block' AND
  (http_user_agent:sqlmap OR http_user_agent:AWVS OR http_user_agent:AppScan
   OR http_user_agent:Nikto OR http_user_agent:nuclei OR http_user_agent:xray
   OR http_user_agent:gobuster OR http_user_agent:masscan)
  | select real_client_ip, host, request_path, http_user_agent limit 30
```

```sql
final_action='block' AND final_rule_type='scanner_behavior'
  | select real_client_ip, host, request_path, http_user_agent, final_rule_id limit 30
```

### 15. Sensitive files and directories

```sql
final_action:null AND
  (request_path:.git OR request_path:.env OR request_path:config.json
   OR request_path:package.json OR request_path:web.config
   OR request_path:swagger OR request_path:api-docs
   OR request_path:actuator OR request_path:druid)
  | select host, request_path, upstream_status, real_client_ip, count(1) as cnt
  group by host, request_path, upstream_status, real_client_ip
  order by cnt desc limit 30
```

### 16. Middleware and framework exploits

```sql
final_action='block' AND
  (request_path:actuator OR request_path:wp-admin OR request_path:jmxproxy
   OR request_path:druid OR request_path:nacos OR request_path:phpMyAdmin)
  | select real_client_ip, host, request_path, final_rule_id limit 30
```

### 17. Protocol and request anomalies

```sql
final_action:null AND
  (request_method:PROPFIND OR request_method:TRACE OR request_method:CONNECT
   OR request_method:PROPPATCH OR request_method:MKCOL
   OR request_method:MOVE OR request_method:LOCK)
  | select host, request_method, request_path, real_client_ip, upstream_status limit 30
```

### 18. Crawler and resource abuse

```sql
* | select real_client_ip, request_path, count(1) as cnt
  group by real_client_ip, request_path
  having cnt > 5000
  order by cnt desc limit 30
```

### 19. Application-layer CC or DDoS

```sql
* | select final_action, real_client_ip, request_path, count(1) as cnt
  where final_action IN ('sigchl','captcha')
  group by final_action, real_client_ip, request_path
  order by cnt desc limit 30
```

### 20. WAF bypass techniques

```sql
final_action:null AND
  (querystring:'%25' OR querystring:'%u00' OR request_body:'%25%25')
  | select host, request_path, querystring, real_client_ip, upstream_status limit 30
```

## BOT analysis

```sql
* | select final_action, count(1) as cnt
  where final_action IN ('sigchl','captcha')
  group by final_action
```

```sql
final_action IN ('sigchl','captcha')
  | select real_client_ip, http_user_agent, host, request_path, count(1) as cnt
  group by real_client_ip, http_user_agent, host, request_path
  order by cnt desc limit 30
```

```sql
* | select antibot_scene_id, antibot_scene_tag, count(1) as cnt
  where antibot_scene_id != 'null'
  group by antibot_scene_id, antibot_scene_tag
  order by cnt desc limit 30
```

```sql
final_action:null AND
  (http_user_agent:python-requests OR http_user_agent:curl
   OR http_user_agent:okhttp OR http_user_agent:'Go-http-client')
  | select real_client_ip, http_user_agent, host, request_path, count(1) as cnt
  group by real_client_ip, http_user_agent, host, request_path
  order by cnt desc limit 30
```

## Evidence drill-down

```sql
real_client_ip:<ip>
  | select request_path, final_action, upstream_status, count(1) as cnt
  group by request_path, final_action, upstream_status
  order by cnt desc limit 50
```

```sql
final_rule_id:<rule-id> AND real_client_ip:<ip>
  | select * limit 1
```

```sql
request_path:<path>
  | select final_action, http_user_agent, count(1) as cnt
  group by final_action, http_user_agent
  order by cnt desc limit 30
```

## Encoding note

The query string is URL-encoded in many WAF SLS configurations. Common mappings include `%2f` for `/`, `%3d` for `=`, and `%3a` for `:`. Exclude IPv4-mapped IPv6 values beginning with `::ffff:` when calculating native IPv6 coverage.
