# Related APIs

## SAS (Security Center) — Product: Sas, Version: 2018-12-03

| CLI Command | API Action | Description | Module |
|-------------|------------|-------------|--------|
| `aliyun sas describe-screen-score-thread` | DescribeScreenScoreThread | Query security score trends (currently unavailable — use DescribeSecureSuggestion Score instead) | Security Overview |
| `aliyun sas describe-vul-fix-statistics` | DescribeVulFixStatistics | Query vulnerability fix statistics | Security Overview |
| `aliyun sas get-check-risk-statistics` | GetCheckRiskStatistics | Query baseline risk statistics | Security Overview |
| `aliyun sas get-defence-count` | GetDefenceCount | Query handled alert counts | Security Overview |
| `aliyun sas describe-version-config` | DescribeVersionConfig | Query SAS edition and subscription details | Usage Info / Billing |
| `aliyun sas describe-cloud-center-instances` | DescribeCloudCenterInstances | Query host asset instances (ECS) | Usage Info / Asset Risk Trend |
| `aliyun sas list-uninstall-aegis-machines` | ListUninstallAegisMachines | Query servers without agent installed | Usage Info |
| `aliyun sas describe-secure-suggestion` | DescribeSecureSuggestion | Query security risk governance suggestions | Security Operations — Risk Governance |
| `aliyun sas describe-field-statistics` | DescribeFieldStatistics | Query server statistics (risk instance count) | Asset Risk Trend |
| `aliyun sas describe-container-field-statistics` | DescribeContainerFieldStatistics | Query container statistics | Asset Risk Trend |
| `aliyun sas get-cloud-asset-summary` | GetCloudAssetSummary | Query cloud asset summary | Asset Risk Trend |
| `aliyun sas describe-chart-data` | DescribeChartData | Query chart data for security reports | Asset Risk Trend |

## WAF (Web Application Firewall) — Product: waf-openapi, Version: 2021-10-01

| CLI Command | API Action | Description | Module |
|-------------|------------|-------------|--------|
| `aliyun waf-openapi describe-instance` | DescribeInstance | Query WAF instance details (get InstanceId) | Security Operations — Security Protection |
| `aliyun waf-openapi describe-flow-chart` | DescribeFlowChart | Query WAF traffic statistics (WafBlockSum) | Security Operations — Security Protection |

## BssOpenApi (Billing) — Product: BssOpenApi, Version: 2017-12-14

| CLI Command | API Action | Description | Module |
|-------------|------------|-------------|--------|
| `aliyun bssopenapi query-bill` | QueryBill | Query bills by billing cycle | Billing |
