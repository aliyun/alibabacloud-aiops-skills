# Acceptance Criteria: alibabacloud-csas-user-device-ops

**Scenario**: SASE User & Device Operations
**Purpose**: Skill testing acceptance criteria — correct and incorrect patterns

---

## 1. CLI Command Format

All commands MUST use plugin mode (kebab-case), NOT PascalCase API format.

#### CORRECT
```bash
aliyun csas list-user-devices --current-page 1 --page-size 100
aliyun csas list-users --current-page 1 --page-size 100
aliyun csas get-user-device --device-tag abc123
aliyun csas update-user-devices-status --device-action Locked --device-tags tag1
```

#### INCORRECT
```bash
# WRONG: PascalCase API format
aliyun csas ListUserDevices --CurrentPage 1 --PageSize 100
aliyun csas GetUserDevice --DeviceTag abc123
aliyun csas UpdateUserDevicesStatus --DeviceAction Lock --DeviceTags.1 tag1
```

---

## 2. Parameter Names (kebab-case)

All parameter names use kebab-case with `--` prefix.

#### CORRECT
```bash
--current-page 1
--page-size 100
--device-types Windows macOS
--device-statuses Online Offline
--sase-user-id su_xxx
--device-belong Company
--dlp-statuses Disabled
--sort-by UpdateTime
```

#### INCORRECT
```bash
# WRONG: PascalCase or camelCase params
--CurrentPage 1
--PageSize 100
--DeviceTypes Windows
--SaseUserId su_xxx
--DeviceBelong Company
```

---

## 3. List Parameter Format

List parameters use SPACE-separated values, NOT comma-separated or RepeatList format.

#### CORRECT
```bash
aliyun csas list-user-devices --device-types Windows macOS Linux
aliyun csas list-user-devices --device-statuses Online Offline
aliyun csas update-user-devices-status --device-tags tag1 tag2 tag3
```

#### INCORRECT
```bash
# WRONG: comma-separated
aliyun csas list-user-devices --device-types Windows,macOS,Linux

# WRONG: RepeatList format (old API style)
aliyun csas list-user-devices --DeviceTypes.1 Windows --DeviceTypes.2 macOS

# WRONG: JSON array
aliyun csas list-user-devices --device-types '["Windows","macOS"]'
```

---

## 4. DeviceAction Enum Values

The `--device-action` parameter uses specific enum values per the plugin mode API.

#### CORRECT
```bash
aliyun csas update-user-devices-status --device-action Locked --device-tags tag1
aliyun csas update-user-devices-status --device-action Unlocked --device-tags tag1
aliyun csas update-user-devices-status --device-action Lost --device-tags tag1
aliyun csas update-user-devices-status --device-action Found --device-tags tag1
aliyun csas update-user-devices-status --device-action Unbound --device-tags tag1
```

#### INCORRECT
```bash
# WRONG: old enum values
aliyun csas update-user-devices-status --device-action Lock --device-tags tag1
aliyun csas update-user-devices-status --device-action Unlock --device-tags tag1

# WRONG: lowercase
aliyun csas update-user-devices-status --device-action locked --device-tags tag1
```

---

## 5. DeviceStatuses Enum Values

Full set of valid device status values:

#### CORRECT
```bash
# All valid values:
--device-statuses Online
--device-statuses Offline
--device-statuses LongTermOffline
--device-statuses Locked
--device-statuses Lost
--device-statuses Unbound
```

#### INCORRECT
```bash
# WRONG: old/abbreviated names
--device-statuses LongOffline    # Should be LongTermOffline
--device-statuses long_offline   # Wrong format
```

---

## 6. DeviceTypes Enum Values

#### CORRECT
```bash
--device-types Windows
--device-types macOS
--device-types Linux
--device-types Android
--device-types iOS
--device-types Windows_Wuying
```

#### INCORRECT
```bash
# WRONG: wrong casing or names
--device-types windows      # Should be Windows
--device-types MacOS        # Should be macOS
--device-types ios          # Should be iOS
--device-types Wuying       # Should be Windows_Wuying
```

---

## 7. Pagination with --pager

Use `--pager` for automatic full-result pagination.

#### CORRECT
```bash
# Auto-paginate all results
aliyun csas list-user-devices --current-page 1 --page-size 500 --pager

# Still need --current-page and --page-size even with --pager
aliyun csas list-users --current-page 1 --page-size 100 --pager
```

#### INCORRECT
```bash
# WRONG: --pager without required params
aliyun csas list-user-devices --pager

# WRONG: assuming --pager removes need for pagination params
aliyun csas list-users --pager
```

---

## 8. Script Parameters

Scripts use their own parameter format (not CLI format).

#### CORRECT
```bash
bash scripts/inactive-analysis.sh --days 30 --scope devices
bash scripts/cleanup-inactive.sh --days 90 --dry-run
bash scripts/cleanup-inactive.sh --days 90 --yes
bash scripts/validate-cli.sh --check-permission
```

#### INCORRECT
```bash
# WRONG: mixing CLI and script formats
bash scripts/cleanup-inactive.sh --days 90 --device-action Locked
bash scripts/inactive-analysis.sh --current-page 1

# WRONG: missing required --days for cleanup
bash scripts/cleanup-inactive.sh --yes
```

---

## 9. Capability Boundary

This skill does NOT perform irreversible operations.

#### CORRECT behavior
- Lock inactive devices → `cleanup-inactive.sh`
- Analyze inactive users/devices → `inactive-analysis.sh`
- Guide user to console for deletion

#### INCORRECT behavior
- Calling `aliyun csas delete-user-devices` (NOT supported by this skill)
- Calling `aliyun csas delete-client-user` (NOT supported by this skill)
- Calling `aliyun csas update-users-status` to freeze users (NOT supported)
