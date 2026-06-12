# DefenseScene / DefenseType Enum Reference

## WAF 3.0 — DefenseScene Values

### DefenseType = `template` (Template Level)

| DefenseScene | Description |
|---|---|
| `waf_group` | Basic Protection - Regular Expression Rules |
| `waf_base` | Web Core Protection (new version) |
| `waf_base_compliance` | Basic Protection - Protocol Compliance Rules |
| `waf_base_sema` | Basic Protection - Semantic Rules |
| `cc` | CC Protection |
| `antiscan_dirscan` | Scan Protection - Directory Traversal Blocking |
| `antiscan_highfreq` | Scan Protection - High Frequency Scan Blocking |
| `antiscan_scantools` | Scan Protection - Scan Tool Blocking |
| `ip_blacklist` | IP Blacklist |
| `custom_acl` | Custom Rules (ACL) |
| `region_block` | Region Blocking |
| `tamperproof` | Web Page Anti-Tampering |
| `dlp` | Information Leak Prevention |
| `custom_response_block` | Custom Response (block page) |
| `spike_throttle` | Spike Throttling |

### DefenseType = `resource` (Resource Level)

| DefenseScene | Description |
|---|---|
| `account_identifier` | Account Identifier Extraction |
| `custom_response` | Custom Response (new version) |
| `waf_codec` | Decoding Settings |

### DefenseType = `global` (Global Level)

| DefenseScene | Description |
|---|---|
| `regular_custom` | Custom Regular Expression |
| `address_book` | Address Book |
| `custom_response` | Custom Response (new version, global scope) |

> Note: `custom_response` appears in both `resource` and `global` DefenseType scopes.

---

## WAF 2.0 — DefenseType Values

Used with `DescribeProtectionModuleRules` API (version `2019-09-10`).

| DefenseType | Description |
|---|---|
| `waf-codec` | Rule Engine Decoding Settings |
| `tamperproof` | Website Anti-Tampering Rules |
| `dlp` | Sensitive Information Leak Prevention Rules |
| `ng_account` | Account Security Rules |
| `bot_crawler` | Legitimate Crawler Rules |
| `bot_intelligence` | Crawler Threat Intelligence Rules |
| `antifraud` | Data Risk Control Protection Requests |
| `antifraud_js` | Data Risk Control JS Injection Page Config |
| `bot_algorithm` | Intelligent Algorithm Rules |
| `bot_wxbb_pkg` | App Protection - Version Protection Rules |
| `bot_wxbb` | App Protection - Path Protection Rules |
| `ac_blacklist` | IP Blacklist Rules |
| `ac_highfreq` | High Frequency Web Attack Auto-Block Rules |
| `ac_dirscan` | Directory Scan Protection Rules |
| `ac_custom` | Custom Protection Policy Rules |
| `whitelist` | Whitelist Rules |
