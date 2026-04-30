# 域名安全策略管理

## 目录

- [域名预检](#域名预检)
- [策略预检](#策略预检)
- [CC防护](#cc防护)
- [精确访问控制（ACL）](#精确访问控制acl)
- [AI智能防护](#ai智能防护)
- [全局防护策略](#全局防护策略)
- [IP黑白名单](#ip黑白名单)
- [区域封禁](#区域封禁)
- [匹配字段与匹配方法参考表](#匹配字段与匹配方法参考表)

## 域名预检

若提供了域名信息，则提前获取域名配置信息。若未提供域名，使用 AskUserQuestion 收集域名。

```bash
aliyun ddoscoo describe-domain-resource --domain '<域名>' --region cn-hangzhou #获取国内高防实例的域名配置信息
aliyun ddoscoo describe-domain-resource --domain '<域名>' --region ap-southeast-1 #获取国际高防实例的域名配置信息
```

## 策略预检

```bash
# 获取策略开关状态
aliyun ddoscoo describe-web-cc-protect-switch --domains.1 '<域名>' --region '<REGION>'

# 获取CC防护策略，其中manual代表手动策略｜clover代表智能策略
aliyun ddoscoo describe-web-cc-rules-v2 --domain '<域名>' --offset 0 --page-size 30 --region '<REGION>'

# 获取ACL防护策略
aliyun ddoscoo describe-web-precise-access-rule --domains.1 '<域名>' --region '<REGION>'

# 获取全局防护策略的规则列表（含RuleId、Action、Enabled、Description）
aliyun ddoscoo describe-l7-global-rule --domain '<域名>' --region '<REGION>'

# 获取黑白名单IP列表
aliyun ddoscoo describe-web-rules --domain '<域名>' --region '<REGION>' | python3 -c "import sys,json;d=json.load(sys.stdin)['WebRules'][0];print('BlackList:',d.get('BlackList',[]));print('WhiteList:',d.get('WhiteList',[]))"

# 获取区域封禁配置（返回每个Region的Block状态 0/1）
aliyun ddoscoo describe-web-area-block-configs --domains.1 '<域名>' --region '<REGION>'
```

`describe-web-cc-protect-switch` 返回字段说明：

| 字段                   | 说明                    | 取值                                                    |
| :--------------------- | :---------------------- | :------------------------------------------------------ |
| `AiMode`               | 智能防护模式            | `watch`（预警）、`defense`（防护）                      |
| `AiRuleEnable`         | 智能防护开关            | `0`（关闭）、`1`（开启）                                |
| `AiTemplate`           | 智能防护等级            | `level30`（宽松）、`level60`（正常）、`level90`（严格） |
| `BlackWhiteListEnable` | 黑白名单开关            | `0`（关闭）、`1`（开启）                                |
| `CcCustomRuleEnable`   | 自定义CC规则开关        | `0`（关闭）、`1`（开启）                                |
| `CcEnable`             | CC防护总开关            | `0`（关闭）、`1`（开启）                                |
| `CcGlobalSwitch`       | CC全局防护开关          | `close`（关闭）、`open`（开启）                         |
| `PreciseRuleEnable`    | 精确访问控制（ACL）开关 | `0`（关闭）、`1`（开启）                                |
| `RegionBlockEnable`    | 区域封禁开关            | `0`（关闭）、`1`（开启）                                |

> **说明：** 其中 CcEnable、CcCustomRuleEnable、CcGlobalSwitch、PreciseRuleEnable 属于 CC 防护大类，由同一个开关接口控制。CcTemplate 和 Domain 可忽略。

## CC防护

### 创建或编辑CC防护的自定义规则

**单次最多支持10条策略下发，即RuleList内最多可包含10个完整的策略。**

```bash
aliyun ddoscoo config-web-cc-rule-v2 --domain '<域名>' --rule-list '[{"action":"<block|challenge|watch>","name":"<规则名称>","ratelimit":{"interval":<统计时长>,"ttl":<处置时长>,"threshold":<阈值次数>,"target":"<统计源>","subkey":"<字段名称>"},"statistics":{"mode":"<count|distinct>","field":"<ip|header|uri>"},"condition":[{"field":"<匹配字段>","match_method":"<匹配方法>","content":"<匹配内容>","header_name":"<字段名称>"}],"status_code":{"enabled":<true|false>,"code":<状态码>,"use_ratio":<true|false>,"count_threshold":<数量阈值>}}]' --expires '<有效期秒数>' --region '<REGION>'
```

#### 参数填写指南

| 参数路径                      | 参数名       | 是否必填 | 可选值/说明                                                  |
| :---------------------------- | :----------- | :------- | :----------------------------------------------------------- |
| `--domain`                    | 域名         | **必填** | 已配置转发规则的网站域名                                     |
| `action`                      | 匹配动作     | **必填** | `block`（封禁）、`challenge`（挑战）、`watch`（观察）        |
| `name`                        | 规则名称     | **必填** | 自定义规则名称字符串，仅支持数字、字母、下划线               |
| `ratelimit.interval`          | 统计时长     | **必填** | 整数，单位：秒                                               |
| `ratelimit.ttl`               | 处置时长     | **必填** | 整数，单位：秒                                               |
| `ratelimit.threshold`         | 阈值次数     | **必填** | 整数，触发阈值（请求次数）                                   |
| `ratelimit.target`            | 统计源       | **必填** | `ip`、`header`、`session`、`cookie-name`、`query-parameter`  |
| `ratelimit.subkey`            | 字段名称     | 条件必填 | target 为 `header`/`cookie-name`/`query-parameter` 时必填    |
| `statistics`                  | 去重统计     | 可选     | 整个对象可选，默认为不去重统计                               |
| `statistics.mode`             | 去重模式     | 条件必填 | `count`（不去重）、`distinct`（去重统计）                    |
| `statistics.field`            | 统计源       | 条件必填 | `ip`、`header`、`uri`                                        |
| `condition`                   | 匹配条件     | **必填** | 数组类型，可包含多个条件，条件间为且关系                     |
| `condition[].field`           | 匹配字段     | **必填** | 见匹配字段与匹配方法参考表                                   |
| `condition[].match_method`    | 匹配方法     | **必填** | 见匹配字段与匹配方法参考表                                   |
| `condition[].content`         | 匹配内容     | **必填** | 具体匹配值                                                   |
| `condition[].header_name`     | 字段名称     | 条件必填 | field 为 `header`/`cookie-name`/`query-parameter` 时必填     |
| `status_code`                 | 状态码统计   | 可选     | 整个对象可选，默认不启用                                     |
| `status_code.enabled`         | 是否开启     | 条件必填 | `true`、`false`                                              |
| `status_code.code`            | 状态码       | 条件必填 | 整数，范围 `100`~`599`                                       |
| `status_code.use_ratio`       | 是否使用比率 | 条件必填 | `true`（按比率）、`false`（按数量）                          |
| `status_code.ratio_threshold` | 比率阈值     | 可选     | 整数，范围 `1`~`100`                                         |
| `status_code.count_threshold` | 数量阈值     | 可选     | 整数，范围 `2`~`50000`                                       |
| `--expires`                   | 有效期       | 可选     | 整数，单位：秒；`0` 表示永久生效（默认）                     |

### 删除CC防护规则

**单次最多支持10条策略下发，即RuleNames列表内最多可包含10个规则名称。**

```bash
aliyun ddoscoo delete-web-cc-rule-v2 --domain '<域名>' --rule-names '["<规则名称1>","<规则名称2>"]' --region '<REGION>'
```

### 关闭/开启CC防护

```bash
aliyun ddoscoo modify-web-cc-global-switch --domain '<域名>' --cc-global-switch '<close|open>' --region '<REGION>'
```

## 精确访问控制（ACL）

### 创建或编辑ACL防护规则

**单次最多支持10条策略下发，即Rules内最多可包含10个完整的策略。**

```bash
aliyun ddoscoo modify-web-precise-access-rule --domain '<域名>' --rules '[{"action":"<accept|block|challenge|watch>","name":"<规则名称>","condition":[{"field":"<匹配字段>","match_method":"<匹配方法>","content":"<匹配内容>","header_name":"<字段名称>"}]}]' --expires '<有效期秒数>' --region '<REGION>'
```

#### 参数填写指南

| 参数路径                   | 参数名   | 是否必填 | 可选值/说明                                                  |
| :------------------------- | :------- | :------- | :----------------------------------------------------------- |
| `--domain`                 | 域名     | **必填** | 已配置转发规则的网站域名                                     |
| `action`                   | 匹配动作 | **必填** | `accept`（放行）、`block`（封禁）、`challenge`（挑战）、`watch`（观察） |
| `name`                     | 规则名称 | **必填** | 自定义规则名称字符串                                         |
| `condition`                | 匹配条件 | **必填** | 数组类型，可包含多个条件，条件间为且关系                     |
| `condition[].field`        | 匹配字段 | **必填** | 见匹配字段与匹配方法参考表                                   |
| `condition[].match_method` | 匹配方法 | **必填** | 见匹配字段与匹配方法参考表                                   |
| `condition[].content`      | 匹配内容 | **必填** | 具体匹配值                                                   |
| `condition[].header_name`  | 字段名称 | 条件必填 | field 为 `header`/`cookie-name`/`query-parameter` 时必填     |
| `--expires`                | 有效期   | 可选     | 整数，单位：秒；仅 action 为 `block` 时生效；不传表示永久生效 |

> **与CC防护的差异：** ACL的action多了`accept`（放行），没有频率限制相关参数（`ratelimit`、`statistics`、`status_code`），是纯条件匹配型规则。

### 删除ACL防护规则

```bash
aliyun ddoscoo delete-web-precise-access-rule --domain '<域名>' --rule-names.1 '<规则名称1>' --rule-names.2 '<规则名称2>' --region '<REGION>'
```

### 关闭/开启ACL防护

```bash
aliyun ddoscoo modify-web-precise-access-switch --domain '<域名>' --config '{"PreciseRuleEnable":<0|1>}' --region '<REGION>'
```

## AI智能防护

### 关闭/开启AI智能防护

```bash
aliyun ddoscoo modify-web-ai-protect-switch --domain '<域名>' --config '{"AiRuleEnable":<0|1>}' --region '<REGION>'
```

### 设置AI智能防护模式和等级

```bash
aliyun ddoscoo modify-web-ai-protect-mode --domain '<域名>' --config '{"AiTemplate":"<level30|level60|level90>","AiMode":"<watch|defense>"}' --region '<REGION>'
```

#### 参数填写指南

| 参数路径       | 参数名       | 是否必填 | 可选值/说明                                             |
| :------------- | :----------- | :------- | :------------------------------------------------------ |
| `--domain`     | 域名         | **必填** | 已配置转发规则的网站域名                                |
| `AiRuleEnable` | 智能防护开关 | **必填** | `0`（关闭）、`1`（开启）                                |
| `AiTemplate`   | 防护等级     | **必填** | `level30`（宽松）、`level60`（正常）、`level90`（严格） |
| `AiMode`       | 防护模式     | **必填** | `watch`（预警）、`defense`（防护）                      |

> **说明：** 开关和模式/等级是两个独立接口。开关通过`modify-web-ai-protect-switch`控制，模式和等级通过`modify-web-ai-protect-mode`同时设置。查询当前状态通过策略预检中的`describe-web-cc-protect-switch`返回的`AiRuleEnable`、`AiMode`、`AiTemplate`字段获取。

## 全局防护策略

### 设置全局防护策略的开关和等级

```bash
aliyun ddoscoo config-domain-security-profile --domain '<域名>' --config '{"global_rule_enable":<0|1>,"global_rule_mode":"<weak|default|hard>"}' --region '<REGION>'
```

#### 参数填写指南

| 参数路径             | 参数名       | 是否必填 | 可选值/说明                                       |
| :------------------- | :----------- | :------- | :------------------------------------------------ |
| `--domain`           | 域名         | **必填** | 已配置转发规则的网站域名                          |
| `global_rule_enable` | 全局防护开关 | 可选     | `0`（关闭）、`1`（开启）                          |
| `global_rule_mode`   | 防护等级     | 可选     | `weak`（宽松）、`default`（正常）、`hard`（严格） |

> **说明：** Config中只需包含要修改的字段，未包含的字段保持不变。查询全局防护开关状态通过策略预检中的`describe-web-cc-protect-switch`返回的`CcGlobalSwitch`字段获取。全局防护等级无独立查询接口。

### 修改全局防护策略的规则动作和开关

**单次最多支持10条策略下发，即RuleAttr内最多可包含10个完整的策略。**

```bash
aliyun ddoscoo config-l7-global-rule --domain '<域名>' --rule-attr '[{"RuleId":"<规则ID>","Action":"<block|watch|challenge>","Enabled":<0|1>}]' --region '<REGION>'
```

#### 参数填写指南

| 参数路径   | 参数名   | 是否必填 | 可选值/说明                                           |
| :--------- | :------- | :------- | :---------------------------------------------------- |
| `--domain` | 域名     | **必填** | 已配置转发规则的网站域名                              |
| `RuleId`   | 规则ID   | **必填** | 从`describe-l7-global-rule`返回的规则ID                  |
| `Action`   | 规则动作 | **必填** | `block`（拦截）、`watch`（观察）、`challenge`（挑战） |
| `Enabled`  | 规则开关 | **必填** | `0`（关闭）、`1`（开启）                              |

## IP黑白名单

### 配置黑白名单IP

**支持IP和IP/掩码格式，黑名单和白名单各最多2000个。白名单不支持配置/0网段到/8网段。该接口为全量覆盖，需传入完整的黑白名单列表。**

```bash
aliyun ddoscoo config-web-ip-set --domain '<域名>' --black-list.1 '<IP或IP/掩码>' --black-list.2 '<IP或IP/掩码>' --white-list.1 '<IP或IP/掩码>' --white-list.2 '<IP或IP/掩码>' --region '<REGION>'
```

> **注意：** 该接口为全量覆盖模式，每次调用需传入完整的黑白名单列表。如需新增IP，应先通过策略预检中的`describe-web-rules`获取当前列表，追加后再调用本接口。

### 关闭/开启黑白名单

```bash
aliyun ddoscoo modify-web-ip-set-switch --domain '<域名>' --config '{"bwlist_enable":<0|1>}' --region '<REGION>'
```

## 区域封禁

### 设置封禁地域

**该接口为全量覆盖模式，需传入完整的封禁地域列表。不传Regions参数表示清空所有封禁地域。**

```bash
aliyun ddoscoo modify-web-area-block --domain '<域名>' --regions.1 '<地域代码1>' --regions.2 '<地域代码2>' --region '<REGION>'
```

> **注意：** 该接口为全量覆盖模式，每次调用需传入完整的封禁地域列表。如需新增地域，应先通过策略预检中的`describe-web-area-block-configs`获取当前已封禁列表（Block为1的Region），追加后再调用本接口。

#### 常用地域代码说明

| 地域代码格式   | 说明                           | 示例                                                         |
| :------------- | :----------------------------- | :----------------------------------------------------------- |
| `CN-ALL`       | 中国大陆全部                   | `CN-ALL`                                                     |
| `CN-xxxxxx`    | 中国大陆省份                   | `CN-110000`（北京）、`CN-310000`（上海）、`CN-330000`（浙江） |
| `OVERSEAS-ALL` | 海外全部                       | `OVERSEAS-ALL`                                               |
| `OVERSEAS-xx`  | 海外国家（ISO 3166-1 alpha-2） | `OVERSEAS-US`（美国）、`OVERSEAS-JP`（日本）                 |

### 关闭/开启区域封禁

```bash
aliyun ddoscoo modify-web-area-block-switch --domain '<域名>' --config '{"RegionblockEnable":<0|1>}' --region '<REGION>'
```

## 匹配字段与匹配方法参考表

> CC防护和精确访问控制（ACL）共用以下匹配字段和匹配方法。

### 匹配字段与匹配方法对应关系

| field               | 描述                          | 可用 match_method                                            |
| :------------------ | :---------------------------- | :----------------------------------------------------------- |
| `ip`                | 访问请求的来源 IP             | `belong`、`nbelong`、`ipinlist`、`ipninlist`                 |
| `uri`               | 访问请求的 URI 地址           | `contain`、`ncontain`、`equal`、`nequal`、`lless`、`lequal`、`lgreat`、`prefix`、`inlist`、`ninlist` |
| `referer`           | 访问请求的来源网址            | `contain`、`ncontain`、`equal`、`nequal`、`lless`、`lequal`、`lgreat`、`nexist`、`inlist`、`ninlist` |
| `user-agent`        | 客户端浏览器标识等信息        | `contain`、`ncontain`、`equal`、`nequal`、`lless`、`lequal`、`lgreat`、`inlist`、`ninlist` |
| `params`            | URL 地址中的参数部分          | `contain`、`ncontain`、`equal`、`nequal`、`lless`、`lequal`、`lgreat`、`inlist`、`ninlist` |
| `cookie`            | 访问请求中的 Cookie 信息      | `contain`、`ncontain`、`equal`、`nequal`、`lless`、`lequal`、`lgreat`、`nexist`、`inlist`、`ninlist` |
| `content-type`      | 响应 HTTP 内容类型            | `contain`、`ncontain`、`equal`、`nequal`、`lless`、`lequal`、`lgreat`、`inlist`、`ninlist` |
| `x-forwarded-for`   | 客户端真实 IP（XFF）          | `contain`、`ncontain`、`equal`、`nequal`、`lless`、`lequal`、`lgreat`、`nexist`、`inlist`、`ninlist` |
| `content-length`    | 访问请求包含的字节数          | `vless`、`vequal`、`vgreat`                                  |
| `post-body`         | 访问请求的内容信息            | `contain`、`ncontain`、`equal`、`nequal`、`inlist`、`ninlist` |
| `http-method`       | 访问请求方法                  | `equal`、`nequal`、`inlist`、`ninlist`                       |
| `header`            | 自定义 HTTP 头部字段          | `contain`、`ncontain`、`equal`、`nequal`、`lless`、`lequal`、`lgreat`、`nexist`、`inlist`、`ninlist` |
| `scheme`            | 访问请求协议                  | `equal`、`nequal`                                            |
| `protocol`          | HTTP 版本                     | `equal`、`nequal`、`inlist`、`ninlist`                       |
| `http2-fingerprint` | HTTP2.0 指纹                  | `equal`、`nequal`、`inlist`、`ninlist`                       |
| `ja3-fingerprint`   | JA3 指纹                      | `equal`、`nequal`、`inlist`、`ninlist`                       |
| `ja4-fingerprint`   | JA4 指纹                      | `equal`、`nequal`、`inlist`、`ninlist`                       |
| `area`              | 请求大洲/国家                 | `areainlist`                                                 |
| `uri-path`          | 请求 URI-Path                 | `contain`、`ncontain`、`equal`、`nequal`、`lless`、`lequal`、`lgreat`、`prefix`、`inlist`、`ninlist` |
| `cookie-name`       | 自定义 Cookie                 | `contain`、`ncontain`、`equal`、`nequal`、`lless`、`lequal`、`lgreat`、`prefix`、`inlist`、`ninlist` |
| `query-parameter`   | 自定义请求参数                | `contain`、`ncontain`、`equal`、`nequal`、`lless`、`lequal`、`lgreat`、`prefix`、`inlist`、`ninlist` |
| `server-port`       | 请求 Server-Port              | `vless`、`vequal`、`vgreat`                                  |

### match_method 逻辑符说明

| match_method | 说明           |
| :----------- | :------------- |
| `belong`     | 属于           |
| `nbelong`    | 不属于         |
| `ipinlist`   | IP 在列表中    |
| `ipninlist`  | IP 不在列表中  |
| `contain`    | 包含           |
| `ncontain`   | 不包含         |
| `equal`      | 等于           |
| `nequal`     | 不等于         |
| `lless`      | 长度小于       |
| `lequal`     | 长度等于       |
| `lgreat`     | 长度大于       |
| `prefix`     | 前缀匹配       |
| `inlist`     | 等于多值之一   |
| `ninlist`    | 不等于多值之一 |
| `nexist`     | 不存在         |
| `vless`      | 值小于         |
| `vequal`     | 值等于         |
| `vgreat`     | 值大于         |
| `areainlist` | 区域封禁选择   |
