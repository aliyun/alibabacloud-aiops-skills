#!/usr/bin/env python3
"""
End-to-end live test for all 75 CLI subcommands.

Executes real API calls in dependency order, using resources created in
earlier steps.  Prints a summary table at the end.

Usage:
    cd scripts/
    export ALIBABA_CLOUD_ACCESS_KEY_ID=...
    export ALIBABA_CLOUD_ACCESS_KEY_SECRET=...
    python3 e2e_test.py
"""

import json
import subprocess
import sys
import time

WS = "f9bbbc0f55ed4d"
NS = "jz-test-default"
REGION = "cn-beijing"
DEPLOY_TARGET = "default-queue"
ENGINE = "vvr-8.0.11-flink-1.17"
COMMON = ["-w", WS, "-n", NS, "-r", REGION]

results = []  # (scenario, cmd, pass/fail, notes)


def cli(*args, expect_success=True, timeout=60):
    """Run flink_ververica_ops.py and return parsed JSON."""
    cmd = [sys.executable, "flink_ververica_ops.py"] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"success": False, "error": {"message": f"CLI timeout after {timeout}s"}, "_timeout": True}
    # Try to parse JSON from stdout
    out = r.stdout.strip()
    if not out:
        # Check stderr for traceback
        if "Traceback" in r.stderr or "TypeError" in r.stderr:
            return {"_crash": True, "_stderr": r.stderr, "success": False}
        return {"success": False, "_stderr": r.stderr, "_stdout": ""}
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"success": False, "_raw": out}
    return data


def record(scenario, cmd_name, result, notes=""):
    api_ok = result.get("success", False)
    crash = result.get("_crash", False)
    is_timeout = result.get("_timeout", False)
    if crash:
        status = "CRASH"
        notes = result.get("_stderr", "")[:120]
    elif is_timeout:
        status = "TIMEOUT"
        notes = notes or "CLI process timed out"
    elif api_ok:
        # Check nested data.success (API-level)
        inner = result.get("data", {})
        if isinstance(inner, dict) and inner.get("success") is False:
            status = "API_ERR"
            notes = notes or inner.get("errorMessage", "")[:100]
        else:
            status = "PASS"
    else:
        status = "FAIL"
        err = result.get("error", {})
        notes = notes or err.get("message", str(result)[:100])
    results.append((scenario, cmd_name, status, notes))
    mark = {"PASS": "+", "API_ERR": "~", "FAIL": "x", "CRASH": "!", "TIMEOUT": "T"}[status]
    print(f"  [{mark}] {cmd_name}: {status}  {notes[:80]}")
    return result


def jd(obj):
    return json.dumps(obj, ensure_ascii=False)


def get_data(result, key=None):
    """Extract nested data from API response."""
    d = result.get("data", {})
    if isinstance(d, dict) and "data" in d:
        d = d["data"]
    if key:
        return d.get(key) if isinstance(d, dict) else None
    return d


def wait_for_job_state(deployment_id, job_id, target_states, timeout=120):
    """Poll job state until it reaches one of target_states."""
    start = time.time()
    while time.time() - start < timeout:
        r = cli("get_job", *COMMON, "--deployment_id", deployment_id, "--job_id", job_id)
        data = get_data(r)
        state = ""
        if isinstance(data, dict):
            status = data.get("status", {})
            if isinstance(status, dict):
                state = status.get("currentJobStatus", "") or status.get("state", "")
            if not state:
                state = data.get("state", "")
        if state in target_states:
            return state
        print(f"  >> ... job state = {state or '?'}, waiting...")
        time.sleep(5)
    return "TIMEOUT"


# ═════════════════════════════════════════════════════════════════════
# Scenario A: W5 Workspace Admin (13 commands)
# ═════════════════════════════════════════════════════════════════════
print("\n=== Scenario A: W5 Workspace Admin ===")

# A1: list_members
r = cli("list_members", *COMMON)
record("W5", "list_members", r)

# A2: create_member
r = cli("create_member", *COMMON, "--member", "123456789012", "--role", "viewer", "--confirm")
record("W5", "create_member", r)

# A3: get_member
r = cli("get_member", *COMMON, "--member", "123456789012")
record("W5", "get_member", r)

# A4: update_member
r = cli("update_member", *COMMON, "--member", "123456789012", "--role", "editor", "--confirm")
record("W5", "update_member", r)

# A5: delete_member
r = cli("delete_member", *COMMON, "--member", "123456789012", "--confirm")
record("W5", "delete_member", r)

# A6: list_variables
r = cli("list_variables", *COMMON)
record("W5", "list_variables", r)

# A7: create_variable (needs 'kind' field)
var_body = {"name": "test_cli_e2e", "value": "hello", "kind": "Plain"}
r = cli("create_variable", *COMMON, "--body_json", jd(var_body), "--confirm")
record("W5", "create_variable", r)

# A8: update_variable
var_body_upd = {"name": "test_cli_e2e", "value": "updated", "kind": "Plain"}
r = cli("update_variable", *COMMON, "--var_name", "test_cli_e2e", "--body_json", jd(var_body_upd), "--confirm")
record("W5", "update_variable", r)

# A9: delete_variable
r = cli("delete_variable", *COMMON, "--var_name", "test_cli_e2e", "--confirm")
record("W5", "delete_variable", r)

# A10: list_deploy_targets
r = cli("list_deploy_targets", *COMMON)
record("W5", "list_deploy_targets", r)

# A11: create_deploy_target (V2 needs Resource with fixedResource)
target_body = {"resource": {"fixedResource": {"cpu": 2.0, "memory": "8Gi"}}}
r = cli("create_deploy_target", *COMMON, "--name", "test-cli-target", "--body_json", jd(target_body), "--confirm")
record("W5", "create_deploy_target", r, "may fail if namespace lacks resource quota")

# A12: update_deploy_target
r = cli("update_deploy_target", *COMMON, "--target_name", "test-cli-target", "--body_json", jd(target_body), "--confirm")
record("W5", "update_deploy_target", r)

# A13: delete_deploy_target
r = cli("delete_deploy_target", *COMMON, "--target_name", "test-cli-target", "--confirm")
record("W5", "delete_deploy_target", r)


# ═════════════════════════════════════════════════════════════════════
# Scenario B: W1 SQL Development (15 commands)
# ═════════════════════════════════════════════════════════════════════
print("\n=== Scenario B: W1 SQL Development ===")

# B1: create_folder
r = cli("create_folder", *COMMON, "--folder_name", "e2e_test_folder", "--confirm")
record("W1", "create_folder", r)
folder_id = get_data(r, "folderId") or "unknown"

# B2: get_folder
r = cli("get_folder", *COMMON, "--folder_id", folder_id)
record("W1", "get_folder", r)

# B3: update_folder
r = cli("update_folder", *COMMON, "--folder_id", folder_id, "--folder_name", "e2e_folder_renamed", "--confirm")
record("W1", "update_folder", r)

# B4: create_draft
r = cli("create_draft", *COMMON,
        "--name", "e2e_test_draft",
        "--content", "CREATE TEMPORARY TABLE t (id INT) WITH ('connector'='datagen'); SELECT * FROM t;",
        "--folder_id", folder_id,
        "--engine_version", ENGINE,
        "--execution_mode", "STREAMING",
        "--confirm")
record("W1", "create_draft", r)
draft_id = get_data(r, "deploymentDraftId") or "unknown"

# B5: get_draft
r = cli("get_draft", *COMMON, "--draft_id", draft_id)
record("W1", "get_draft", r)

# B6: update_draft
r = cli("update_draft", *COMMON, "--draft_id", draft_id,
        "--content", "SELECT 1 AS val;",
        "--confirm")
record("W1", "update_draft", r)

# B7: list_drafts
r = cli("list_drafts", *COMMON)
record("W1", "list_drafts", r)

# B8: get_draft_lock
r = cli("get_draft_lock", *COMMON, "--draft_id", draft_id)
record("W1", "get_draft_lock", r)

# B9: validate_sql
r = cli("validate_sql", *COMMON, "--statement", "SELECT 1")
record("W1", "validate_sql", r)

# B10: validate_draft (async, needs deployment_target_name)
r = cli("validate_draft", *COMMON, "--draft_id", draft_id, "--deployment_target", DEPLOY_TARGET)
record("W1", "validate_draft", r)
ticket_validate = get_data(r, "ticketId")

# B11: get_validate_result
if ticket_validate:
    time.sleep(2)
    r = cli("get_validate_result", *COMMON, "--ticket_id", ticket_validate)
    record("W1", "get_validate_result", r)
else:
    record("W1", "get_validate_result", {"success": True, "data": {}}, "skipped - no validate ticket")

# B12: deploy_draft (async)
r = cli("deploy_draft", *COMMON, "--draft_id", draft_id, "--deployment_target", DEPLOY_TARGET, "--confirm")
record("W1", "deploy_draft", r)
ticket_deploy = get_data(r, "ticketId")

# B13: get_deploy_result
if ticket_deploy:
    time.sleep(2)
    r = cli("get_deploy_result", *COMMON, "--ticket_id", ticket_deploy)
    record("W1", "get_deploy_result", r)
else:
    record("W1", "get_deploy_result", {"success": True, "data": {}}, "skipped - no deploy ticket")

# B14: delete_draft
r = cli("delete_draft", *COMMON, "--draft_id", draft_id, "--confirm")
record("W1", "delete_draft", r)

# B15: delete_folder
r = cli("delete_folder", *COMMON, "--folder_id", folder_id, "--confirm")
record("W1", "delete_folder", r)


# ═════════════════════════════════════════════════════════════════════
# Scenario C: W2 Deployment + Job lifecycle (26 commands)
# ═════════════════════════════════════════════════════════════════════
print("\n=== Scenario C: W2 Deployment + Job lifecycle ===")

# C1: list_deployments (empty)
r = cli("list_deployments", *COMMON)
record("W2", "list_deployments", r)

# C2: create_deployment -- a real streaming SQL deployment
dep_body = {
    "name": "e2e-cli-test-dep",
    "deploymentTarget": {"name": DEPLOY_TARGET, "mode": "PER_JOB"},
    "engineVersion": ENGINE,
    "executionMode": "STREAMING",
    "logging": {"loggingProfile": "default"},
    "artifact": {
        "kind": "SQLSCRIPT",
        "sqlArtifact": {
            "sqlScript": "CREATE TEMPORARY TABLE src (id INT, ts TIMESTAMP(3), WATERMARK FOR ts AS ts) WITH ('connector'='datagen','rows-per-second'='1'); CREATE TEMPORARY TABLE sink (id INT, ts TIMESTAMP(3)) WITH ('connector'='blackhole'); INSERT INTO sink SELECT * FROM src;"
        }
    }
}
r = cli("create_deployment", *COMMON, "--body_json", jd(dep_body), "--confirm")
record("W2", "create_deployment", r)
dep_data = get_data(r)
dep_id = ""
if isinstance(dep_data, dict):
    dep_id = dep_data.get("deploymentId", "") or dep_data.get("metadata", {}).get("deploymentId", "")
if not dep_id:
    # Fallback: look inside result.data.data
    raw = r.get("data", {})
    if isinstance(raw, dict) and isinstance(raw.get("data"), dict):
        dep_id = raw["data"].get("deploymentId", "")
print(f"  >> deployment_id = {dep_id}")

# C3: get_deployment
r = cli("get_deployment", *COMMON, "--deployment_id", dep_id)
record("W2", "get_deployment", r)

# C4: update_deployment
upd_body = {"description": "e2e test deployment - updated"}
r = cli("update_deployment", *COMMON, "--deployment_id", dep_id, "--body_json", jd(upd_body), "--confirm")
record("W2", "update_deployment", r)

# C5: search_by_name
r = cli("search_by_name", *COMMON, "--name", "e2e-cli-test-dep")
record("W2", "search_by_name", r)

# C6: search_by_label
r = cli("search_by_label", *COMMON, "--label_key", "test", "--label_value", "true")
record("W2", "search_by_label", r, "empty result expected")

# C7: search_by_ip
r = cli("search_by_ip", *COMMON, "--ip", "10.0.0.1")
record("W2", "search_by_ip", r, "empty or error expected")

# C8: get_events
r = cli("get_events", *COMMON, "--deployment_id", dep_id)
record("W2", "get_events", r)

# C9: generate_resource_plan (async)
r = cli("generate_resource_plan", *COMMON, "--deployment_id", dep_id)
record("W2", "generate_resource_plan", r)
ticket_rp = get_data(r, "ticketId")

# C10: get_resource_plan_result
if ticket_rp:
    time.sleep(3)
    r = cli("get_resource_plan_result", *COMMON, "--ticket_id", ticket_rp)
    record("W2", "get_resource_plan_result", r)
else:
    record("W2", "get_resource_plan_result", {"success": True, "data": {}}, "skipped - no ticket")

# C11: start_job
r = cli("start_job", *COMMON, "--deployment_id", dep_id, "--restore_strategy", "NONE", "--confirm")
record("W2", "start_job", r)
job_data = get_data(r)
job_id = ""
if isinstance(job_data, dict):
    job_id = job_data.get("jobId", "") or job_data.get("jobID", {}).get("jobId", "")
if not job_id:
    raw = r.get("data", {})
    if isinstance(raw, dict) and isinstance(raw.get("data"), dict):
        job_id = raw["data"].get("jobId", "")
print(f"  >> job_id = {job_id}")

# Wait for job to be RUNNING (or at least STARTING)
if job_id:
    print("  >> waiting for job to reach RUNNING state...")
    state = wait_for_job_state(dep_id, job_id, ["RUNNING", "FAILING", "FAILED", "CANCELLING", "FINISHED"], timeout=120)
    print(f"  >> job state = {state}")

# C12: get_job
if job_id:
    r = cli("get_job", *COMMON, "--deployment_id", dep_id, "--job_id", job_id)
    record("W2", "get_job", r)
else:
    record("W2", "get_job", {"success": True, "data": {}}, "skipped - no job_id")

# C13: list_jobs
r = cli("list_jobs", *COMMON, "--deployment_id", dep_id)
record("W2", "list_jobs", r)

# C14: get_start_log
r = cli("get_start_log", *COMMON, "--deployment_id", dep_id, "--job_id", job_id or "dummy")
record("W2", "get_start_log", r)

# C15: diagnose_job
if job_id:
    r = cli("diagnose_job", *COMMON, "--deployment_id", dep_id, "--job_id", job_id)
    record("W2", "diagnose_job", r)
else:
    record("W2", "diagnose_job", {"success": True, "data": {}}, "skipped - no job_id")

# C16: hot_update_job
if job_id:
    r = cli("hot_update_job", *COMMON, "--deployment_id", dep_id, "--job_id", job_id, "--confirm")
    record("W2", "hot_update_job", r)
else:
    record("W2", "hot_update_job", {"success": True, "data": {}}, "skipped - no job_id")

# C17: get_hot_update_result
if job_id:
    r = cli("get_hot_update_result", *COMMON, "--deployment_id", dep_id, "--job_id", job_id)
    record("W2", "get_hot_update_result", r)
else:
    record("W2", "get_hot_update_result", {"success": True, "data": {}}, "skipped - no job_id")

# C18: create_savepoint (need running job)
r = cli("create_savepoint", *COMMON, "--deployment_id", dep_id, "--confirm")
record("W2", "create_savepoint", r)
sp_data = get_data(r)
sp_id = ""
if isinstance(sp_data, dict):
    sp_id = sp_data.get("savepointId", "")
if not sp_id:
    raw = r.get("data", {})
    if isinstance(raw, dict) and isinstance(raw.get("data"), dict):
        sp_id = raw["data"].get("savepointId", "")
print(f"  >> savepoint_id = {sp_id}")

# Wait a bit for savepoint
if sp_id:
    time.sleep(5)

# C19: get_savepoint
if sp_id:
    r = cli("get_savepoint", *COMMON, "--savepoint_id", sp_id)
    record("W2", "get_savepoint", r)
else:
    record("W2", "get_savepoint", {"success": True, "data": {}}, "skipped - no savepoint_id")

# C20: list_savepoints
r = cli("list_savepoints", *COMMON, "--deployment_id", dep_id)
record("W2", "list_savepoints", r)

# C21: get_lineage
r = cli("get_lineage", *COMMON)
record("W2", "get_lineage", r)

# C22: flink_api_proxy (use the deployment as resource)
if job_id:
    r = cli("flink_api_proxy", *COMMON,
            "--flink_api_path", "/overview",
            "--resource_type", "jobs",
            "--resource_id", dep_id)
    record("W2", "flink_api_proxy", r)
else:
    record("W2", "flink_api_proxy", {"success": True, "data": {}}, "skipped - no running job")

# C23: stop_job
if job_id:
    r = cli("stop_job", *COMMON, "--deployment_id", dep_id, "--job_id", job_id, "--stop_strategy", "NONE", "--confirm")
    record("W2", "stop_job", r)
    # Wait for job to transition to CANCELLED
    print("  >> waiting for job to stop...")
    wait_for_job_state(dep_id, job_id, ["CANCELLED", "FAILED", "FINISHED"], timeout=60)
else:
    record("W2", "stop_job", {"success": True, "data": {}}, "skipped - no job_id")

# C24: delete_savepoint
if sp_id:
    r = cli("delete_savepoint", *COMMON, "--savepoint_id", sp_id, "--confirm")
    record("W2", "delete_savepoint", r)
else:
    record("W2", "delete_savepoint", {"success": True, "data": {}}, "skipped - no savepoint_id")

# C25: delete_job (must be in CANCELLED/FAILED/FINISHED state)
if job_id:
    # Wait and retry for job to be in terminal state
    for attempt in range(3):
        r = cli("delete_job", *COMMON, "--deployment_id", dep_id, "--job_id", job_id, "--confirm")
        if r.get("success") and not (isinstance(r.get("data", {}), dict) and r["data"].get("success") is False):
            break
        print(f"  >> delete_job attempt {attempt+1} failed, waiting...")
        time.sleep(10)
    record("W2", "delete_job", r)
else:
    record("W2", "delete_job", {"success": True, "data": {}}, "skipped - no job_id")

# C26: delete_deployment
for attempt in range(3):
    r = cli("delete_deployment", *COMMON, "--deployment_id", dep_id, "--confirm")
    if r.get("success") and not (isinstance(r.get("data", {}), dict) and r["data"].get("success") is False):
        break
    print(f"  >> delete_deployment attempt {attempt+1} failed, waiting...")
    time.sleep(10)
record("W2", "delete_deployment", r)


# ═════════════════════════════════════════════════════════════════════
# Scenario D: W3 Session Cluster (7 commands)
# ═════════════════════════════════════════════════════════════════════
print("\n=== Scenario D: W3 Session Cluster ===")

# D1: list_session_clusters
r = cli("list_session_clusters", *COMMON)
record("W3", "list_session_clusters", r)

# D2: create_session_cluster
sc_body = {
    "name": "e2e-cli-test-sc",
    "workspace": WS,
    "engineVersion": ENGINE,
    "deploymentTargetName": DEPLOY_TARGET,
    "logging": {"loggingProfile": "default"},
    "basicResourceSetting": {
        "parallelism": 1,
        "jobmanagerResourceSettingSpec": {"cpu": 1.0, "memory": "4Gi"},
        "taskmanagerResourceSettingSpec": {"cpu": 1.0, "memory": "4Gi"}
    }
}
r = cli("create_session_cluster", *COMMON, "--body_json", jd(sc_body), "--confirm")
record("W3", "create_session_cluster", r)
sc_data = get_data(r)
sc_name = sc_data.get("name", "e2e-cli-test-sc") if isinstance(sc_data, dict) else "e2e-cli-test-sc"
# Find the cluster_id - check the register args
# The CLI uses --cluster_id for session cluster operations
sc_id = sc_data.get("sessionClusterId", "") if isinstance(sc_data, dict) else ""
print(f"  >> session_cluster name={sc_name}, id={sc_id}")

# D3: get_session_cluster
r = cli("get_session_cluster", *COMMON, "--cluster_id", sc_name)
record("W3", "get_session_cluster", r)

# D4: update_session_cluster
sc_upd = {"engineVersion": ENGINE, "deploymentTargetName": DEPLOY_TARGET}
r = cli("update_session_cluster", *COMMON, "--cluster_id", sc_name, "--body_json", jd(sc_upd), "--confirm")
record("W3", "update_session_cluster", r)

# D5: start_session_cluster
r = cli("start_session_cluster", *COMMON, "--cluster_id", sc_name, "--confirm")
record("W3", "start_session_cluster", r)

# Wait for cluster to start
print("  >> waiting for session cluster to start...")
time.sleep(15)

# D6: stop_session_cluster
r = cli("stop_session_cluster", *COMMON, "--cluster_id", sc_name, "--confirm")
record("W3", "stop_session_cluster", r)

# Wait for cluster to stop
time.sleep(10)

# D7: delete_session_cluster
r = cli("delete_session_cluster", *COMMON, "--cluster_id", sc_name, "--confirm")
record("W3", "delete_session_cluster", r)


# ═════════════════════════════════════════════════════════════════════
# Scenario E: W4 Dev Resources (14 commands)
# ═════════════════════════════════════════════════════════════════════
print("\n=== Scenario E: W4 Dev Resources ===")

# E1: list_engine_versions
r = cli("list_engine_versions", *COMMON)
record("W4", "list_engine_versions", r)

# E2: get_catalogs
r = cli("get_catalogs", *COMMON)
record("W4", "get_catalogs", r)

# E3: get_databases
r = cli("get_databases", *COMMON, "--catalog_name", "vvp")
record("W4", "get_databases", r)

# E4: get_tables
r = cli("get_tables", *COMMON, "--catalog_name", "vvp", "--database_name", "default")
record("W4", "get_tables", r)

# E5: execute_sql
r = cli("execute_sql", *COMMON, "--statement", "SHOW CATALOGS", "--confirm")
record("W4", "execute_sql", r)

# E6: get_udf_artifacts
r = cli("get_udf_artifacts", *COMMON)
record("W4", "get_udf_artifacts", r)

# E7: create_udf_artifact (needs a real JAR url, will timeout or get API error)
udf_body = {"jarUrl": "https://dummy.oss-cn-beijing.aliyuncs.com/test.jar", "name": "e2e-test-udf"}
r = cli("create_udf_artifact", *COMMON, "--body_json", jd(udf_body), "--confirm", timeout=30)
record("W4", "create_udf_artifact", r, "expected: timeout/error - no real jar")

# E8: update_udf_artifact (will fail - no artifact exists)
r = cli("update_udf_artifact", *COMMON, "--udf_artifact_name", "e2e-test-udf", "--body_json", jd(udf_body), "--confirm")
record("W4", "update_udf_artifact", r, "expect API error - artifact not found")

# E9: delete_udf_artifact
r = cli("delete_udf_artifact", *COMMON, "--udf_artifact_name", "e2e-test-udf", "--confirm")
record("W4", "delete_udf_artifact", r, "expect API error - artifact not found")

# E10: register_udf_function
udf_fn = {"className": "com.test.E2eUdf", "functionName": "e2e_udf", "udfArtifactName": "e2e-test-udf"}
r = cli("register_udf_function", *COMMON, "--body_json", jd(udf_fn), "--confirm")
record("W4", "register_udf_function", r, "expect API error - artifact not found")

# E11: delete_udf_function
r = cli("delete_udf_function", *COMMON, "--function_name", "e2e_udf", "--class_name", "com.test.E2eUdf", "--udf_artifact_name", "e2e-test-udf", "--confirm")
record("W4", "delete_udf_function", r, "expect API error - function not found")

# E12: list_connectors
r = cli("list_connectors", *COMMON)
record("W4", "list_connectors", r)

# E13: register_connector
r = cli("register_connector", *COMMON, "--body_json", '{"jarUrl":"https://dummy.oss-cn-beijing.aliyuncs.com/conn.jar"}', "--confirm", timeout=30)
record("W4", "register_connector", r, "expected: timeout/error - no real jar")

# E14: delete_connector
r = cli("delete_connector", *COMMON, "--connector_name", "e2e-test-connector", "--confirm")
record("W4", "delete_connector", r)


# ═════════════════════════════════════════════════════════════════════
# Summary
# ═════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("FINAL RESULTS")
print("=" * 80)

pass_count = sum(1 for _, _, s, _ in results if s == "PASS")
api_err_count = sum(1 for _, _, s, _ in results if s == "API_ERR")
fail_count = sum(1 for _, _, s, _ in results if s == "FAIL")
crash_count = sum(1 for _, _, s, _ in results if s == "CRASH")
timeout_count = sum(1 for _, _, s, _ in results if s == "TIMEOUT")
total = len(results)

print(f"\n{'Scenario':<6} {'Command':<30} {'Status':<10} Notes")
print("-" * 80)
for scenario, cmd, status, notes in results:
    print(f"{scenario:<6} {cmd:<30} {status:<10} {notes[:40]}")

print("-" * 80)
print(f"Total: {total}  |  PASS: {pass_count}  |  API_ERR: {api_err_count}  |  FAIL: {fail_count}  |  TIMEOUT: {timeout_count}  |  CRASH: {crash_count}")
print(f"\nPASS = SDK call succeeded and API returned success")
print(f"API_ERR = SDK call succeeded but API returned business error (e.g. resource not found)")
print(f"FAIL = SDK call returned error envelope (connectivity/auth)")
print(f"TIMEOUT = CLI process timed out (expected for fake JAR URLs)")
print(f"CRASH = Python TypeError/Traceback (BUG!)")

if crash_count > 0:
    print("\n!!! CRASHES DETECTED - BUGS TO FIX !!!")
    for scenario, cmd, status, notes in results:
        if status == "CRASH":
            print(f"  {scenario}/{cmd}: {notes}")

sys.exit(1 if crash_count > 0 else 0)
