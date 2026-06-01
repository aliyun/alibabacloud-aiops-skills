# SASE API Reference

Product code: `csas` | API version: `2023-01-20` | CLI plugin mode (kebab-case)

## Parameter Format Constraints

The following format rules apply across all commands. Invalid values trigger `InvalidParameter` error (HTTP 400).
Source: `aliyun csas <command> --help`

| Parameter | Constraint | Example | Source |
|---|---|---|---|
| `--current-page` | Positive integer, 1~10000 | `1` | CLI help |
| `--page-size` | Positive integer, 1~500 (list-user-applications: 1~100) | `100` | CLI help |
| `--device-action` | Case-sensitive enum: `Locked` `Lost` `Unbound` `Unlocked` `Found` | `Locked` | CLI help |
| `--device-statuses` | Enum list: `Online` `Offline` `LongTermOffline` `Locked` `Lost` `Unbound` | `Online LongTermOffline` | CLI help |
| `--device-types` | Enum list: `Windows` `macOS` `Linux` `Android` `iOS` `Windows_Wuying` | `Windows macOS` | CLI help |
| `--device-belong` | Case-sensitive enum: `Personal` `Company` | `Company` | CLI help |
| `--sort-by` | Case-sensitive enum: `Username` `AppVersion` `UpdateTime` | `UpdateTime` | CLI help |
| `--status` (list-users) | Case-sensitive enum: `Enabled` `Disabled` | `Enabled` | CLI help |
| `--dlp-statuses` | Enum list: `Enabled` `Disabled` `Unprovisioned` `Unauthorized` | `Disabled Unprovisioned` | CLI help |
| `--pa-statuses` | Enum list: `Enabled` `Disabled` `Unprovisioned` | `Enabled` | CLI help |
| `--ia-statuses` | Enum list: `Enabled` `Disabled` `Unprovisioned` | `Disabled` | CLI help |
| `--nac-statuses` | Enum list: `Enabled` `Disabled` `Unprovisioned` | `Unprovisioned` | CLI help |
| `--sase-user-id` | From API response `SaseUserId` field | `su_2e10e16a****0566abea4ce6` | Observed |
| `--sase-user-ids` | List of SaseUserId | `su_2e10****4ce6 su_ef48****573b` | Observed |
| `--device-tag` | From API response `DeviceTag` field | `480F8E02-****-5932A5FF60BC` | Observed |
| `--device-tags` | List of DeviceTag | `480F8E02-****-60BC 24BB1571-****-86EF` | Observed |
| `--username` | String | `test001` | CLI help |
| `--fuzzy-username` | String, fuzzy match | `zhang` | CLI help |
| `--precise-username` | String, exact match | `zhangsan` | CLI help |
| `--department` | String | `Engineering` | CLI help |
| `--hostname` | String | `MacBook-Pro` | CLI help |
| `--mac` | String | `3c:06:****:79:1b` | CLI help |
| `--inner-ip` | String | `10.0.**.**` | CLI help |
| `--user-group-ids` | List | `usergroup-51bd****a540` | Observed |
| `--name` (list-user-applications) | String | `CRM` | CLI help |
| `--address` (list-user-applications) | String (IPv4/CIDR/domain) | `192.168.1.0/24` | CLI help |
| Enum list params | Space-separated values, NOT comma | `--device-types Windows macOS` | CLI help |

---

## Table of Contents

1. [list-user-devices](#1-list-user-devices)
2. [list-users](#2-list-users)
3. [list-user-applications](#3-list-user-applications)
4. [get-user-device](#4-get-user-device)
5. [get-active-idp-config](#5-get-active-idp-config)
6. [list-user-groups](#6-list-user-groups)
7. [update-user-devices-status](#7-update-user-devices-status)

---

## 1. list-user-devices

Query terminal devices with flexible filtering. Core API for device management.

```bash
aliyun csas list-user-devices --current-page 1 --page-size 100 [OPTIONS]
```

**Required parameters:**

| Parameter | Type | Description |
|---|---|---|
| `--current-page` | int | Page number, 1~10000 |
| `--page-size` | int | Items per page, 1~500 |

**Optional parameters:**

| Parameter | Type | Enum Values | Description |
|---|---|---|---|
| `--username` | string | — | Filter by username |
| `--sase-user-id` | string | — | Filter by SASE user ID (obtain from ListUsers/ListUserDevices response) |
| `--department` | string | — | Filter by department |
| `--hostname` | string | — | Filter by device hostname |
| `--device-belong` | string | `Personal`, `Company` | Device ownership |
| `--mac` | string | — | Filter by MAC address |
| `--sharing-status` | bool | `true`, `false` | Sharing enabled |
| `--device-statuses` | list | `Online`, `Offline`, `LongTermOffline`, `Locked`, `Lost`, `Unbound` | Device status |
| `--device-types` | list | `Windows`, `macOS`, `Linux`, `Android`, `iOS`, `Windows_Wuying` | OS type |
| `--app-statuses` | list | `Online`, `Offline` | Client app status |
| `--pa-statuses` | list | `Enabled`, `Disabled`, `Unprovisioned` | Private access status |
| `--ia-statuses` | list | `Enabled`, `Disabled`, `Unprovisioned` | Internet access status |
| `--dlp-statuses` | list | `Enabled`, `Disabled`, `Unprovisioned`, `Unauthorized` | DLP status |
| `--nac-statuses` | list | `Enabled`, `Disabled`, `Unprovisioned` | Network admission status |
| `--auto-login-statuses` | list | — | Auto-login status |
| `--app-versions` | list | — | Client version filter |
| `--device-tags` | list | — | Device ID filter |
| `--device-group-id` | string | — | Device group ID |
| `--inner-ip` | string | — | Internal IP address |
| `--sn-system` | string | — | System serial number |
| `--workshop` | string | — | Workspace name |
| `--sort-by` | string | `Username`, `AppVersion`, `UpdateTime` | Sort field |

**List parameter format:** `--device-types Windows macOS` (space-separated, NOT comma)

**Key response fields:**

| Field | Type | Description |
|---|---|---|
| `TotalNum` | int | Total matching devices |
| `Devices[].DeviceTag` | string | Unique device identifier |
| `Devices[].DeviceType` | string | OS type |
| `Devices[].DeviceModel` | string | Hardware model |
| `Devices[].DeviceVersion` | string | OS version |
| `Devices[].Hostname` | string | Device name |
| `Devices[].Username` | string | Owner username |
| `Devices[].SaseUserId` | string | Owner user ID |
| `Devices[].Department` | string | Owner department |
| `Devices[].InnerIP` | string | Internal IP |
| `Devices[].SrcIP` | string | Login source IP |
| `Devices[].Memory` | string | RAM (GB) |
| `Devices[].CPU` | string | CPU model |
| `Devices[].Disk` | string | Disk model |
| `Devices[].Mac` | string | MAC address |
| `Devices[].AppVersion` | string | SASE client version |
| `Devices[].DeviceBelong` | string | Personal/Company |
| `Devices[].SharingStatus` | bool | Sharing enabled |
| `Devices[].DeviceStatus` | string | Online/Offline/LongTermOffline/Locked/Lost/Unbound |
| `Devices[].AppStatus` | string | Client status (Online/Offline) |
| `Devices[].PaStatus` | string | Private access (Enabled/Disabled/Unprovisioned) |
| `Devices[].IaStatus` | string | Internet access (Enabled/Disabled/Unprovisioned) |
| `Devices[].DlpStatus` | string | DLP (Enabled/Disabled/Unprovisioned/Unauthorized) |
| `Devices[].NacStatus` | string | NAC (Enabled/Disabled/Unprovisioned) |
| `Devices[].EdrStatus` | string | EDR (Enabled/Disabled) |
| `Devices[].AutoLoginStatus` | string | Auto-login status |
| `Devices[].CreateTime` | string | Registration time |
| `Devices[].UpdateTime` | string | Last heartbeat time (activity proxy) |
| `Devices[].Workshop` | string | Workspace name |

---

## 2. list-users

Query SASE user accounts.

```bash
aliyun csas list-users --current-page 1 --page-size 100 [OPTIONS]
```

**Required parameters:**

| Parameter | Type | Description |
|---|---|---|
| `--current-page` | int | Page number, 1~10000 |
| `--page-size` | int | Items per page, 1~500 |

**Optional parameters:**

| Parameter | Type | Enum Values | Description |
|---|---|---|---|
| `--fuzzy-username` | string | — | Fuzzy match username |
| `--precise-username` | string | — | Exact match username |
| `--department` | string | — | Filter by department |
| `--status` | string | `Enabled`, `Disabled` | User status |
| `--sase-user-ids` | list | — | Filter by user IDs |

**Key response fields:**

| Field | Type | Description |
|---|---|---|
| `TotalNum` | string | Total matching users |
| `Users[].Username` | string | Login username |
| `Users[].SaseUserId` | string | Unique user identifier |
| `Users[].Department` | string | Department name |
| `Users[].Email` | string | Email address |
| `Users[].Phone` | string | Phone number |
| `Users[].Status` | string | Enabled/Disabled |
| `Users[].IdpName` | string | Identity provider name |
| `Users[].FullDepartment` | array | Full department path |

---

## 3. list-user-applications

Query private access applications authorized to a specific user.

```bash
aliyun csas list-user-applications --sase-user-id <ID> --current-page 1 --page-size 100 [OPTIONS]
```

**Required parameters:**

| Parameter | Type | Description |
|---|---|---|
| `--sase-user-id` | string | Target user ID (obtain from ListUsers response) |
| `--current-page` | int | Page number |
| `--page-size` | int | Items per page, 1~100 |

**Optional parameters:**

| Parameter | Type | Description |
|---|---|---|
| `--name` | string | Filter by application name |
| `--address` | string | Filter by application address (IPv4, CIDR, domain) |

**Key response fields:**

| Field | Type | Description |
|---|---|---|
| `TotalNum` | int | Total authorized applications |
| `Applications[].Name` | string | Application name |
| `Applications[].ApplicationId` | string | Application ID |
| `Applications[].Protocol` | string | All/TCP/UDP/HTTP/HTTPS |
| `Applications[].Action` | string | Allow/Block |
| `Applications[].Addresses` | array | Application addresses |
| `Applications[].PortRanges[].Begin` | string | Start port |
| `Applications[].PortRanges[].End` | string | End port |

---

## 4. get-user-device

Get full detail for a single device (more fields than list).

```bash
aliyun csas get-user-device --device-tag <TAG>
```

**Required parameters:**

| Parameter | Type | Description |
|---|---|---|
| `--device-tag` | string | Device identifier (obtain from ListUserDevices response) |

**Additional response fields** (beyond list-user-devices):

| Field | Type | Description |
|---|---|---|
| `Device.HistoryUsers[]` | array | Historical users of this device |
| `Device.NetInterfaceInfo[]` | array | Network interfaces (name, mac) |
| `Device.MatchDeviceGroupIds` | array | Matched device group IDs |
| `Device.SnSystem` | string | System serial number |
| `Device.SnDiskDrive` | string | Disk serial number |
| `Device.SnBaseBoard` | string | Motherboard serial number |
| `Device.JoinAdDomain` | bool | Joined AD domain |
| `Device.CityZh` / `Device.ProvinceZh` | string | Location info (Chinese) |

---

## 5. get-active-idp-config

Get the active Identity Provider configuration.

```bash
aliyun csas get-active-idp-config
```

**Parameters:** None

**Key response fields:**

| Field | Type | Description |
|---|---|---|
| `IdpConfigId` | string | IDP configuration ID |
| `Name` | string | IDP display name |
| `Type` | string | IDP type (determines custom vs third-party) |
| `Description` | string | IDP description |

---

## 6. list-user-groups

Query user groups defined in SASE.

```bash
aliyun csas list-user-groups --current-page 1 --page-size 100 [OPTIONS]
```

**Required parameters:**

| Parameter | Type | Description |
|---|---|---|
| `--current-page` | int | Page number, 1~10000 |
| `--page-size` | int | Items per page, 1~1000 |

**Optional parameters:**

| Parameter | Type | Description |
|---|---|---|
| `--name` | string | Filter by group name |
| `--attribute-value` | string | Filter by attribute value |
| `--user-group-ids` | list | Filter by group IDs |
| `--pa-policy-id` | string | Filter by private access policy ID |

**Key response fields:**

| Field | Type | Description |
|---|---|---|
| `TotalNum` | int | Total user groups |
| `UserGroups[].UserGroupId` | string | Group ID |
| `UserGroups[].Name` | string | Group name |
| `UserGroups[].Description` | string | Group description |
| `UserGroups[].Attributes[].UserGroupType` | string | username/department/email/telephone |
| `UserGroups[].Attributes[].Relation` | string | Equal/Unequal |
| `UserGroups[].Attributes[].Value` | string | Attribute value |
| `UserGroups[].CreateTime` | string | Creation time |

---

## 7. update-user-devices-status

Batch update device status. Used by cleanup-inactive.sh for locking.

```bash
aliyun csas update-user-devices-status --device-tags <TAG1> [TAG2 ...] --device-action <ACTION>
```

**Required parameters:**

| Parameter | Type | Enum Values | Description |
|---|---|---|---|
| `--device-tags` | list | — | Device identifiers (max 100 per call) |
| `--device-action` | string | `Locked`, `Lost`, `Unbound`, `Unlocked`, `Found` | Target action |

**DeviceAction details:**

| Action | Description | Constraint |
|---|---|---|
| `Locked` | Lock device | Any device |
| `Lost` | Mark as lost | Any device |
| `Unbound` | Unbind device | Only when Offline or LongTermOffline |
| `Unlocked` | Unlock device | Only when Locked |
| `Found` | Recover from lost | Only when Lost |

**Max batch size:** 100 device tags per API call.
