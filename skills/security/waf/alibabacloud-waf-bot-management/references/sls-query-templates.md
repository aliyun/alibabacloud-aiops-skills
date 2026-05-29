# SLS Query Templates Library

## Usage Instructions

The following queries are based on Alibaba Cloud WAF SLS Log Service. Before using, please confirm:
1. WAF Log Service is enabled (`DescribeUserWafLogStatus`)
2. Bot collection fields have been added to the logs and index is enabled
3. Replace `{domain}` with the actual protected domain name, and `{time_range}` with the query time range

Key fields in SLS logs include: real_client_ip (real IP), matched_host (matched domain), request_path (request path), user_agent, final_action (final action), bot_action (bot action), bot_rule_id (matched rule ID), bot_rule_label (matched rule label).

---

## 1. Traffic Overview

### Access/Block Traffic Trend

```sql
* and matched_host: "{domain}"
| select date_format(__time__, '%Y-%m-%d %H:%i') as time,
  count(*) as total,
  sum(case when final_action = 'block' then 1 else 0 end) as blocked,
  sum(case when bot_action != '' then 1 else 0 end) as bot_hit
group by time
order by time
```

### Bot Category Traffic Trend

```sql
* and matched_host: "{domain}" and bot_action != ''
| select date_format(__time__, '%Y-%m-%d %H:%i') as time,
  bot_rule_label,
  count(*) as cnt
group by time, bot_rule_label
order by time
```

### Action Distribution

```sql
* and matched_host: "{domain}"
| select bot_action, count(*) as cnt
group by bot_action
order by cnt desc
```

---

## 2. Attack Source Analysis

### Top Attacking IPs

```sql
* and matched_host: "{domain}" and final_action = 'block'
| select real_client_ip, count(*) as cnt
group by real_client_ip
order by cnt desc
limit 20
```

### Top Attacking User-Agents

```sql
* and matched_host: "{domain}" and final_action = 'block'
| select user_agent, count(*) as cnt
group by user_agent
order by cnt desc
limit 20
```

### Top Matched Rule Distribution

```sql
* and matched_host: "{domain}" and bot_rule_label != ''
| select bot_rule_label, count(*) as cnt
group by bot_rule_label
order by cnt desc
limit 20
```

### Top Attacked Paths

```sql
* and matched_host: "{domain}" and final_action = 'block'
| select request_path, count(*) as cnt
group by request_path
order by cnt desc
limit 20
```

---

## 3. Scalper/Volume-Boosting Behavior Detection

### Single Device with Multiple Account Switching

```sql
* and matched_host: "{domain}"
| select umid, count(distinct account) as account_cnt
group by umid
having account_cnt > 5
order by account_cnt desc
```

### Single Account with Multiple Device Switching

```sql
* and matched_host: "{domain}"
| select account, count(distinct umid) as device_cnt
group by account
having device_cnt > 5
order by device_cnt desc
```

### Single Account with Multiple IP Switching

```sql
* and matched_host: "{domain}"
| select account, count(distinct real_client_ip) as ip_cnt
group by account
having ip_cnt > 5
order by ip_cnt desc
```

### Abnormally High-Frequency IPs

```sql
* and matched_host: "{domain}"
| select real_client_ip, count(*) as cnt
group by real_client_ip
having cnt > 100
order by cnt desc
limit 50
```

### Abnormally High-Frequency Devices

```sql
* and matched_host: "{domain}" and umid != ''
| select umid, count(*) as cnt
group by umid
having cnt > 100
order by cnt desc
limit 50
```

---

## 4. SMS Volume-Boosting Detection

### SMS API Call Statistics

```sql
* and matched_host: "{domain}" and request_path: "/api/sms*"
| select real_client_ip, count(*) as cnt
group by real_client_ip
order by cnt desc
limit 20
```

### SMS API User-Agent Distribution

```sql
* and matched_host: "{domain}" and request_path: "/api/sms*"
| select user_agent, count(*) as cnt
group by user_agent
order by cnt desc
limit 20
```

### SMS API Source Region Distribution

```sql
* and matched_host: "{domain}" and request_path: "/api/sms*"
| select province, count(*) as cnt
group by province
order by cnt desc
```

---

## 5. API Endpoint Analysis

### API Call Volume Trend

```sql
* and matched_host: "{domain}" and request_path: "/api/*"
| select date_format(__time__, '%Y-%m-%d %H:%i') as time,
  count(*) as total
group by time
order by time
```

### Top API Endpoints by Call Volume

```sql
* and matched_host: "{domain}" and request_path: "/api/*"
| select request_path, count(*) as cnt
group by request_path
order by cnt desc
limit 20
```

### API Call User-Agent Distribution

```sql
* and matched_host: "{domain}" and request_path: "/api/*"
| select user_agent, count(*) as cnt
group by user_agent
order by cnt desc
limit 20
```

### Unauthenticated API Calls (Potential Abuse)

```sql
* and matched_host: "{domain}" and request_path: "/api/*" not Authorization not Bearer
| select real_client_ip, request_path, count(*) as cnt
group by real_client_ip, request_path
order by cnt desc
limit 50
```

---

## 6. Protection Effectiveness Evaluation

### Block Rate Calculation

```sql
* and matched_host: "{domain}"
| select
  count(*) as total,
  sum(case when final_action = 'block' or bot_action = 'block' or bot_action = 'captcha' or bot_action = 'captcha_strict' or bot_action = 'js' then 1 else 0 end) as intercepted,
  round(sum(case when final_action = 'block' or bot_action = 'block' or bot_action = 'captcha' or bot_action = 'captcha_strict' or bot_action = 'js' then 1 else 0 end) * 100.0 / count(*), 2) as intercept_rate
```

### Rule Hit Efficiency

```sql
* and matched_host: "{domain}" and bot_rule_label != ''
| select bot_rule_label,
  count(*) as total_hits,
  sum(case when bot_action = 'block' then 1 else 0 end) as blocked,
  sum(case when bot_action = 'captcha' then 1 else 0 end) as captcha_challenged,
  sum(case when bot_action = 'monitor' then 1 else 0 end) as observed
group by bot_rule_label
order by total_hits desc
```

### False Positive Investigation - Blocked Legitimate User-Agents

```sql
* and matched_host: "{domain}" and final_action = 'block'
| select user_agent, real_client_ip, request_path, bot_rule_label
order by __time__ desc
limit 100
```

---

## 7. Bot Management Dashboard Metrics

### Comprehensive Metrics Dashboard

```sql
* and matched_host: "{domain}"
| select
  count(*) as total_requests,
  sum(case when bot_action != '' then 1 else 0 end) as bot_requests,
  sum(case when final_action = 'block' then 1 else 0 end) as blocked_requests,
  count(distinct real_client_ip) as unique_ips,
  count(distinct umid) as unique_devices,
  round(sum(case when final_action = 'block' then 1 else 0 end) * 100.0 / count(*), 2) as block_rate
```

### Hourly Traffic Trend

```sql
* and matched_host: "{domain}"
| select date_trunc('hour', __time__) as hour,
  count(*) as total,
  sum(case when bot_action != '' then 1 else 0 end) as bot_hit,
  sum(case when final_action = 'block' then 1 else 0 end) as blocked
group by hour
order by hour
```

### Daily Management Trend (for Weekly/Monthly Reports)

```sql
* and matched_host: "{domain}"
| select date_trunc('day', __time__) as day,
  count(*) as total,
  sum(case when final_action = 'block' then 1 else 0 end) as blocked,
  count(distinct case when bot_action != '' then real_client_ip end) as bot_ips,
  round(sum(case when final_action = 'block' then 1 else 0 end) * 100.0 / count(*), 2) as block_rate
group by day
order by day
```
