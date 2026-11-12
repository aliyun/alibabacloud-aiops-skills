"""Validated patrol configuration changes and report polling."""

from copy import deepcopy
from datetime import date
import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .common import (
    OpsError, add_body_arguments, positive_number, positive_seconds,
    validate_object, validate_string,
)


_COMMAND_SPECS = {
    "get_patrol_config": ("GetPatrolConfig", "Query patrol configuration."),
    "update_patrol_config": ("UpdatePatrolConfig", "Preview or update explicit patrol configuration fields, with read-back verification."),
    "trigger_patrol": ("TriggerPatrol", "Trigger one patrol within an explicit scope, with optional bounded wait."),
    "list_patrol_reports": ("ListPatrolReports", "Page through reports by time, status, scope, and trigger type."),
    "get_patrol_report_detail": ("GetPatrolReportDetail", "Read report detail by report ID or server-timezone date."),
    "wait_patrol_report": (None, "Read-only wait for an existing report; never re-triggers."),
}
COMMANDS = {name: action for name, (action, _) in _COMMAND_SPECS.items()}
SCOPE_TYPES = {"ALL", "TAGS", "DEPLOYMENTS"}
FILTER_STATUSES = {"PENDING", "IN_PROGRESS", "COMPLETED", "FAILED"}
RESPONSE_STATUSES = FILTER_STATUSES | {"COMPLETING"}
_QUERY_FIELDS = {
    "start_date": "startDate", "end_date": "endDate", "scope_type": "scopeType",
    "trigger_type": "triggerType", "report_id": "reportId", "date": "date",
    "timezone": "timezone", "status": "status", "page": "page", "size": "size",
}


def _invalid(message):
    raise OpsError("ValidationError", message)


def _enum(value, name, choices):
    if not isinstance(value, str) or value not in choices:
        _invalid(f"{name} must be one of: {', '.join(sorted(choices))}.")


def _integer(value, name, minimum=None, maximum=None):
    if type(value) is not int:
        _invalid(f"{name} must be an integer.")
    if minimum is not None and value < minimum:
        _invalid(f"{name} must be greater than or equal to {minimum}.")
    if maximum is not None and value > maximum:
        _invalid(f"{name} must be less than or equal to {maximum}.")


def _timezone(value):
    validate_string(value, "timezone")
    try:
        ZoneInfo(value)
    except (ValueError, ZoneInfoNotFoundError):
        _invalid("timezone must be a valid IANA timezone name.")


def _scope_config(config):
    validate_object(config, "scopeConfig", {"deploymentIds", "tags"})
    if "deploymentIds" in config:
        ids = config["deploymentIds"]
        if not isinstance(ids, list) or not ids:
            _invalid("scopeConfig.deploymentIds must be a non-empty array of strings.")
        for value in ids:
            validate_string(value, "scopeConfig.deploymentIds[]")
    if "tags" in config:
        tags = config["tags"]
        if not isinstance(tags, dict) or not tags:
            _invalid("scopeConfig.tags must be a non-empty tag map.")
        for key, values in tags.items():
            validate_string(key, "scopeConfig.tags key")
            if not isinstance(values, list) or not values:
                _invalid("scopeConfig.tags values must be non-empty arrays of strings.")
            for value in values:
                validate_string(value, "scopeConfig.tags[][]")


def _scope_matches(scope_type, config):
    _enum(scope_type, "scopeType", SCOPE_TYPES)
    config = {} if config is None else config
    _scope_config(config)
    expected = {"ALL": set(), "TAGS": {"tags"}, "DEPLOYMENTS": {"deploymentIds"}}
    if set(config) != expected[scope_type]:
        _invalid(f"scopeConfig does not match scopeType={scope_type}.")


def validate_patrol_request(command, body=None, parameters=None, confirm=False,
                            timeout=300, poll_interval=5):
    """Reject invalid inputs before constructing the SDK or making requests."""
    if command not in COMMANDS:
        _invalid("Unsupported patrol command.")
    if type(confirm) is not bool:
        _invalid("confirm must be a boolean.")
    positive_number(timeout, "timeout")
    positive_number(poll_interval, "poll_interval")
    if parameters is not None and not isinstance(parameters, dict):
        _invalid("parameters must be a JSON object.")
    if command in {"update_patrol_config", "trigger_patrol"}:
        if parameters:
            _invalid("This patrol command does not support query parameters.")
        allowed = {"scopeType", "scopeConfig"}
        if command == "update_patrol_config":
            allowed |= {"cron", "enabled", "timezone"}
        validate_object(body, "body", allowed)
        if not body:
            _invalid("body must not be empty.")
        if "scopeType" in body:
            _enum(body["scopeType"], "scopeType", SCOPE_TYPES)
        if "scopeConfig" in body:
            _scope_config(body["scopeConfig"])
        if "enabled" in body and type(body["enabled"]) is not bool:
            _invalid("enabled must be a boolean.")
        if "cron" in body:
            validate_string(body["cron"], "cron")
        if "timezone" in body:
            _timezone(body["timezone"])
        if command == "trigger_patrol":
            if "scopeType" not in body:
                _invalid("Triggering a patrol requires an explicit scopeType.")
            _scope_matches(body["scopeType"], body.get("scopeConfig"))
            if not confirm:
                raise OpsError("ConfirmationRequired", "Triggering a patrol requires an explicit --confirm.")
        elif "scopeType" in body and "scopeConfig" in body:
            _scope_matches(body["scopeType"], body["scopeConfig"])
        return
    if body is not None:
        _invalid("This read-only patrol command does not support body.")
    values = {} if parameters is None else parameters
    if command == "get_patrol_config":
        validate_object(values, "parameters", set())
    elif command == "list_patrol_reports":
        validate_object(values, "parameters", {"startDate", "endDate", "status", "scopeType",
                                        "triggerType", "page", "size"})
        for key in ("startDate", "endDate"):
            if key in values:
                _integer(values[key], key)
        if "startDate" in values and "endDate" in values and values["startDate"] > values["endDate"]:
            _invalid("startDate must not be later than endDate.")
        for key, choices in (("status", FILTER_STATUSES), ("scopeType", SCOPE_TYPES),
                             ("triggerType", {"CRON", "MANUAL", "INNER_API"})):
            if key in values:
                _enum(values[key], key, choices)
        if "page" in values:
            _integer(values["page"], "page", 1)
        if "size" in values:
            _integer(values["size"], "size", 1, 200)
    else:
        allowed = {"reportId"} if command == "wait_patrol_report" else {"reportId", "date", "timezone"}
        validate_object(values, "parameters", allowed)
        if ("reportId" in values) == ("date" in values):
            _invalid("Exactly one of reportId or date is required; the wait command supports reportId only.")
        if "reportId" in values:
            validate_string(values["reportId"], "reportId")
        if "date" in values:
            value = values["date"]
            validate_string(value, "date")
            if value not in {"today", "yesterday"}:
                try:
                    if date.fromisoformat(value).isoformat() != value:
                        raise ValueError()
                except ValueError:
                    _invalid("date must be YYYY-MM-DD, today, or yesterday.")
        if "timezone" in values:
            _timezone(values["timezone"])


class _Budget:
    def __init__(self, api, timeout):
        self.api = api
        self.deadline = time.monotonic() + timeout
        self.evidence = {}

    def fail(self, code, message, extra=None, *, request_id=None):
        data = deepcopy(self.evidence)
        if extra:
            data.update(deepcopy(extra))
        if request_id is None:
            request_id = getattr(self.api, "last_request_id", "")
        raise OpsError(code, message, request_id=request_id, data=data)

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            self.fail("Timeout", "The patrol operation reached the total time limit; continue waiting with the same reportId.")
        return remaining

    def request(self, action, parameters=None, body=None):
        remaining = self.remaining()
        try:
            response = self.api.request(action, parameters=parameters, body=body, timeout=remaining)
        except OpsError as exc:
            request_error = {"code": exc.code, "message": str(exc), "data": exc.data}
            if time.monotonic() >= self.deadline:
                self.fail("Timeout", "The patrol request reached the total time limit; the obtained report information is kept for follow-up.",
                          {"requestError": request_error}, request_id=exc.request_id)
            if self.evidence:
                data = deepcopy(self.evidence)
                data["requestError"] = request_error
                raise OpsError(exc.code, str(exc), request_id=exc.request_id, data=data) from exc
            raise
        self.evidence["lastResponse"] = deepcopy(response)
        if action == "TriggerPatrol" and isinstance(response, dict):
            initial = response.get("data")
            self.evidence.update({"triggerResponse": deepcopy(initial), "lastObserved": deepcopy(initial)})
            if isinstance(initial, dict) and isinstance(initial.get("reportId"), str) and initial["reportId"].strip():
                self.evidence["reportId"] = initial["reportId"]
        self.remaining()
        if not isinstance(response, dict) or "data" not in response:
            self.fail("InvalidResponse", f"{action} response is missing data.")
        return response["data"]


def _validate_trigger(budget, result):
    if not isinstance(result, dict) or not isinstance(result.get("reportId"), str) or not result["reportId"].strip():
        budget.fail("InvalidResponse", "The patrol trigger response is missing a valid reportId; the trigger evidence is kept. Do not re-trigger.")
    if not isinstance(result.get("status"), str) or result["status"] not in RESPONSE_STATUSES:
        budget.fail("InvalidResponse", "The patrol trigger response is missing a known status; the trigger evidence is kept. Do not re-trigger.")


def _validate_detail(budget, detail, report_id=None):
    budget.evidence["detail"] = deepcopy(detail)
    if report_id is not None:
        budget.evidence["reportId"] = report_id
    missing = []
    data = detail if isinstance(detail, dict) else {}
    actual_id = data.get("reportId")
    if not isinstance(actual_id, str) or not actual_id.strip() or (report_id is not None and actual_id != report_id):
        missing.append("reportId")
    elif report_id is None:
        budget.evidence["reportId"] = actual_id
    overview = data.get("overview")
    if not isinstance(overview, dict):
        missing.append("overview")
        overview = {}
    if type(overview.get("total")) is not int or overview["total"] < 0:
        missing.append("overview.total")
    risks = overview.get("riskSummary")
    if not isinstance(risks, dict):
        missing.append("overview.riskSummary")
        risks = {}
    for risk in ("critical", "warning", "info"):
        if type(risks.get(risk)) is not int or risks[risk] < 0:
            missing.append("overview.riskSummary." + risk)
    if not isinstance(data.get("unhealthyJobs"), list):
        missing.append("unhealthyJobs")
    if missing:
        budget.fail("IncompleteReport", "The patrol report risk evidence is incomplete; actual health cannot be verified from it.",
                    {"missingEvidence": missing})
    return detail


def _update(budget, patch, confirm):
    current = budget.request("GetPatrolConfig")
    if not isinstance(current, dict):
        budget.fail("InvalidResponse", "GetPatrolConfig did not return a valid configuration.")
    if "scopeType" in patch or "scopeConfig" in patch:
        scope = patch.get("scopeType", current.get("scopeType"))
        config = patch.get("scopeConfig", current.get("scopeConfig"))
        if scope == "ALL" and "scopeConfig" not in patch:
            config = None
        _scope_matches(scope, config)
    changes = {key: {"before": deepcopy(current.get(key)), "after": deepcopy(value)}
               for key, value in patch.items()
               if key not in current or type(current[key]) is not type(value) or current[key] != value}
    if not confirm:
        return {"preview": True, "currentConfig": current, "patch": patch, "changes": changes}
    if not changes:
        return {"updated": False, "unchanged": True, "updateSubmitted": False,
                "verified": True, "patch": patch, "previousConfig": current, "config": current}
    budget.evidence.update({"patch": patch, "previousConfig": current, "changes": changes})
    update_response = budget.request("UpdatePatrolConfig", body=patch)
    budget.evidence["updateResponse"] = deepcopy(update_response)
    actual = budget.request("GetPatrolConfig")
    budget.evidence["config"] = deepcopy(actual)
    mismatches = {key: {"expected": value, "actual": actual.get(key) if isinstance(actual, dict) else None}
                  for key, value in patch.items()
                  if not isinstance(actual, dict) or key not in actual
                  or type(actual[key]) is not type(value) or actual[key] != value}
    if mismatches:
        budget.fail("VerificationFailed", "The read-back values after the configuration update do not match the explicit patch.", {"mismatches": mismatches})
    return {"updated": True, "updateSubmitted": True, "verified": True, "patch": patch,
            "previousConfig": current, "config": actual}


def _scan_report(budget, report_id):
    page_number = 1
    while True:
        budget.remaining()
        if page_number > 1000:
            budget.fail("InvalidResponse", "The report list exceeds the 1000-page per-round limit; retry later with the same reportId.")
        result = budget.request("ListPatrolReports", parameters={"page": page_number, "size": 200})
        budget.evidence["lastPage"] = deepcopy(result)
        if not isinstance(result, dict):
            budget.fail("InvalidResponse", "The report list data must be an object.")
        items, page, size, total = (result.get(key) for key in ("items", "page", "size", "total"))
        if (not isinstance(items, list) or type(page) is not int or page != page_number
                or type(size) is not int or not 1 <= size <= 200
                or type(total) is not int or total < 0):
            budget.fail("InvalidResponse", "The report list pagination metadata is missing or invalid.")
        offset = (page_number - 1) * size
        expected_count = max(0, min(size, total - offset))
        if len(items) != expected_count:
            budget.fail("InvalidResponse", "The report list pagination is incomplete; the patrol status cannot be confirmed.")
        found = None
        for item in items:
            if not isinstance(item, dict):
                budget.fail("InvalidResponse", "The report list contains an invalid entry.")
            if item.get("reportId") == report_id:
                found = item
                break
        if found is not None:
            if not isinstance(found.get("status"), str) or found["status"] not in RESPONSE_STATUSES:
                budget.fail("InvalidResponse", "The patrol report returned an unknown or missing status.")
            budget.evidence["lastObserved"] = deepcopy(found)
            return found
        if offset + len(items) >= total:
            return None
        page_number += 1


def _wait_report(budget, report_id, poll_interval, initial=None):
    budget.evidence["reportId"] = report_id
    if initial is not None:
        budget.evidence["lastObserved"] = deepcopy(initial)
    while True:
        report = _scan_report(budget, report_id)
        if report is not None:
            status = report["status"]
            if status == "FAILED":
                budget.fail("PatrolFailed", "Patrol failed: " + str(report.get("errorMessage") or "the service provided no reason"))
            if status == "COMPLETED":
                detail = budget.request("GetPatrolReportDetail", parameters={"reportId": report_id})
                _validate_detail(budget, detail, report_id)
                return {"reportId": report_id, "status": status, "detail": detail,
                        "evidenceComplete": True, "healthVerified": False}
        time.sleep(min(poll_interval, budget.remaining()))
        budget.remaining()


def run_patrol(api, command, body=None, parameters=None, confirm=False, wait=False,
               timeout=300, poll_interval=5):
    """Run one patrol command; waiting always follows one stable report ID."""
    validate_patrol_request(command, body, parameters, confirm, timeout, poll_interval)
    if type(wait) is not bool:
        _invalid("wait must be a boolean.")
    if wait and command not in {"trigger_patrol", "wait_patrol_report"}:
        _invalid("--wait applies only to the trigger and wait-for-report commands.")
    budget = _Budget(api, timeout)
    body = deepcopy(body)
    parameters = deepcopy(parameters)
    try:
        if command == "update_patrol_config":
            return _update(budget, body, confirm)
        if command == "wait_patrol_report":
            return _wait_report(budget, parameters["reportId"], poll_interval)
        result = budget.request(COMMANDS[command], parameters=parameters, body=body)
        if command == "trigger_patrol":
            _validate_trigger(budget, result)
            if wait:
                return _wait_report(budget, result["reportId"], poll_interval, result)
        if command == "get_patrol_report_detail":
            return _validate_detail(budget, result, (parameters or {}).get("reportId"))
        return result
    except KeyboardInterrupt:
        message = "The local patrol command was interrupted."
        if command == "trigger_patrol" and "reportId" not in budget.evidence:
            message += " The trigger result is unknown. Do not re-trigger. Check for the report with list_patrol_reports."
        elif command in {"trigger_patrol", "wait_patrol_report"}:
            message += " The cloud patrol was not canceled. To continue, use wait_patrol_report with the same reportId."
        elif command == "update_patrol_config" and "patch" in budget.evidence:
            message += " Check the current configuration with get_patrol_config before retrying the update."
        budget.fail("Interrupted", message)


def _prepare_cli(args, body):
    """Translate CLI query names and validate the complete patrol request."""
    request = {
        "command": args.command, "body": body,
        "parameters": {wire: getattr(args, flag) for flag, wire in _QUERY_FIELDS.items()
                       if getattr(args, flag, None) is not None},
        "confirm": getattr(args, "confirm", False),
        "timeout": getattr(args, "timeout", 300),
        "poll_interval": getattr(args, "poll_interval", 5),
    }
    validate_patrol_request(**request)
    return {**request, "wait": getattr(args, "wait", False)}


def register(subparsers, common_parser):
    """Keep patrol command arguments beside their validation and execution."""
    for name, (_, description) in _COMMAND_SPECS.items():
        command = subparsers.add_parser(name, parents=[common_parser],
                                       help=description, description=description)
        if name in {"update_patrol_config", "trigger_patrol"}:
            add_body_arguments(command)
        if name in {"trigger_patrol", "wait_patrol_report"}:
            command.add_argument("--timeout", type=positive_seconds, default=300,
                                 help="Total patrol wait time limit for this run in seconds, default 300.")
            command.add_argument("--poll_interval", type=positive_seconds, default=5,
                                 help="Status polling interval in seconds, default 5.")
        if name == "trigger_patrol":
            command.add_argument("--wait", action="store_true", help="After triggering, wait for the same report and read the detail.")
        elif name == "list_patrol_reports":
            for flag in ("start_date", "end_date", "page", "size"):
                command.add_argument("--" + flag, type=int)
            for flag in ("status", "scope_type", "trigger_type"):
                command.add_argument("--" + flag)
        elif name == "get_patrol_report_detail":
            target = command.add_mutually_exclusive_group(required=True)
            target.add_argument("--report_id")
            target.add_argument("--date", help="YYYY-MM-DD, today, or yesterday.")
            command.add_argument("--timezone", help="IANA timezone for the date, e.g. Asia/Shanghai.")
        elif name == "wait_patrol_report":
            command.add_argument("--report_id", required=True)
        command.set_defaults(prepare=_prepare_cli, execute=run_patrol)
