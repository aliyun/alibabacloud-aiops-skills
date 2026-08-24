"""
_constants.py — Shared constants for AK Leak Incident Response scripts
======================================================================
Internal module (prefixed with `_`). Do NOT run directly.

Single source of truth for HIGH_RISK_EVENTS, DANGEROUS_SERVICES,
SERVICE_SOURCE_PREFIXES, and DEFAULT_TIMEOUT. Imported by both the
orchestrator (ak_leak_investigation.py) and standalone scripts.
"""

# Default HTTP timeout in seconds for API calls.
DEFAULT_TIMEOUT = 60

# 15 dangerous services covered by the investigation SOP.
DANGEROUS_SERVICES = [
    "Ram", "CloudSSO", "ECS", "AasSub", "Eci", "SMS", "ECD",
    "BDRC", "RdsData", "PTS", "Alidns", "EHPC", "Dms",
    "Billing", "Instant",
]

# Alibaba Cloud AK Restrictive Protection high-risk API list (82 APIs).
# Source: https://help.aliyun.com/zh/ram/user-guide/accesskey-restrictive-protection-description
HIGH_RISK_EVENTS: dict[str, list[str]] = {
    "Ram": [
        "CreateUser", "CreateAccessKey", "AttachPolicyToUser",
        "CreateRole", "AttachPolicyToRole", "SetDefaultPolicyVersion",
        "CreateLoginProfile", "AddUserToGroup",
    ],
    "ECS": [
        "RunInstances", "CreateInstance", "CreateAutoProvisioningGroup",
        "StartInstance", "StartInstances", "RunCommand",
        "DeleteInstance", "DeleteInstances", "DeleteSnapshotGroup",
        "DeleteSnapshot", "DeleteImage", "CreateCommand", "InvokeCommand",
        # Extended monitoring — not in official 82-API list but high-risk in practice
        "CreateSecurityGroup", "AuthorizeSecurityGroup",
        "CreateImage", "ModifyInstanceAttribute",
    ],
    "AasSub": [
        "CreateSubAccount", "SetAccountStatus",
        "BindMFADevice", "ConsoleSignin", "UnbindMFADevice",
    ],
    "Eci": [
        "CreateContainerGroup", "CreateContainerGroupFromTemplate",
        "BatchCreateContainerGroups", "DeleteContainerGroup", "DeleteContainerGroups",
    ],
    "SMS": ["SendSms", "SendBatchSms", "AddSmsTemplate", "CreateSmsTemplate"],
    "ECD": [
        "StartDesktops", "CreateDesktops", "CreateDesktopGroup",
        "ModifyDesktopGroup", "RebootDesktops", "RebuildDesktops",
        "GetConnectionTicket", "ModifyDesktopSpec", "RunCommand",
        "CreateADConnectorDirectory",
    ],
    "BDRC": [
        "CreateBackupPlan", "CreateRestoreJob",
        "ModifyBackupStrategy", "CreateDownload", "DescribeDownloadBackupSetStorageInfo",
    ],
    "RdsData": [
        "ExecuteStatement", "ModifyBackupPolicy", "DeleteBackup", "DescribeBackups",
        "DeleteDBInstance", "DestroyDBInstance", "DeleteDatabase",
        "CreateAccount", "ResetAccountPassword", "ResetAccount", "GrantAccountPrivilege",
    ],
    "PTS": [
        "StartJMeterTesting", "SaveJMeterScene", "CreateJMeterScene",
        "CreateCronJob", "StartSceneTesting", "StartDebugging",
        "CreateScene", "SaveScene", "SaveOpenJMeterScene",
        "StartDebuggingJMeterScene", "StartTestingJMeterScene",
        "SavePtsScene", "CreatePtsScene", "StartDebugPtsScene", "StartPtsScene",
    ],
    "Alidns": [
        "AddDomainRecord", "DeleteDomainRecord", "UpdateDomainRecord",
        "DeleteDomain", "SetDomainRecordStatus",
        "CreateAlidnsLineRecordSet", "DeleteAlidnsLineRecordSet", "UpdateAlidnsLineRecordSet",
    ],
    "EHPC": ["CreateCluster", "AddUsers", "CreateNodes"],
    "Dms": [
        "CreateOrder", "CreateDataExportOrder", "CreateDatabaseExportOrder",
        "CreateDataCorrectOrder", "CreateDataCronClearOrder", "CreateDataImportOrder",
        "CreateFreeLockCorrectOrder", "GetDataExportDownloadURL", "GetDbExportDownloadURL",
        "CreateProcCorrectOrder",
    ],
    "Billing": ["RefundInstance"],
    "Instant": ["CreateJob", "CreatePool"],
}

# ActionTrail eventSource prefix -> service name mapping.
# Used for client-side filtering when querying ALL events.
SERVICE_SOURCE_PREFIXES: dict[str, str] = {
    "ecs": "ECS",
    "ram": "Ram",
    "eci": "Eci",
    "dysms": "SMS",
    "ecd": "ECD",
    "rds": "RdsData",
    "pts": "PTS",
    "alidns": "Alidns",
    "ehpc": "EHPC",
    "dms": "Dms",
    "billing": "Billing",
    "bss": "Billing",
    "aas": "AasSub",
    "bdrc": "BDRC",
    "instant": "Instant",
    "sts": "Ram",           # STS events often related to AK usage
    "fc": "Eci",            # FunctionCompute -> loosely map to Eci
    "cloudsso": "CloudSSO", # CloudSSO persistence events
}
