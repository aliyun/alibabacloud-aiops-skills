"""Shared SLS SDK transport, credentials and log queries."""

import re
from urllib.parse import quote, urlsplit

from _skill_user_agent import AttributionError, user_agent


class RequestError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def skill_user_agent():
    try:
        return user_agent()
    except AttributionError as exc:
        raise RequestError("InvalidSkillAttribution", str(exc)) from None


def normalize_endpoint_host(value):
    if not value:
        raise RequestError("InvalidParameter", "Provide an SLS service endpoint or region")
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value):
        raise RequestError("InvalidParameter", "Endpoint must not contain whitespace or control characters")
    parsed = urlsplit(value if "://" in value else "https://" + value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in ("", "/")
            or not re.fullmatch(r"[A-Za-z0-9.-]+(?::\d+)?", parsed.netloc)):
        raise RequestError("InvalidParameter", "Endpoint must be an HTTPS service host, without credentials or a path")
    return parsed.netloc.lower()


class SLSClient:
    def __init__(self, endpoint=None, region=None, timeout=60):
        if region is not None and not re.fullmatch(r"[a-z0-9-]+", region):
            raise RequestError("InvalidParameter", "Invalid SLS region")
        host = normalize_endpoint_host(endpoint or (f"{region}.log.aliyuncs.com" if region else None))
        user_agent = skill_user_agent()
        try:
            from alibabacloud_credentials.client import Client as CredentialClient
            from alibabacloud_sls20201230.client import Client
            from alibabacloud_tea_openapi.utils_models import Config
        except ImportError:
            raise RequestError("MissingDependency", "Install dependencies with python3 -m pip install -r scripts/requirements.txt from the skill directory") from None
        self.client = Client(Config(endpoint=host, region_id=region, protocol="https",
                                    credential=CredentialClient(), connect_timeout=10000,
                                    read_timeout=timeout * 1000, user_agent=user_agent))
        self.timeout = timeout

    def request(self, action, method, path, query=None, body=None, project=None):
        from alibabacloud_tea_openapi.utils_models import OpenApiRequest, Params
        from darabonba.runtime import RuntimeOptions

        if project is not None and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", project):
            raise RequestError("InvalidParameter", "Invalid SLS project name")
        params = Params(action=action, version="2020-12-30", protocol="HTTPS", pathname=path,
                        method=method, auth_type="AK", style="ROA", req_body_type="json", body_type="json")
        # execute is the same public path used by generated SLS SDK methods.
        response = self.client.execute(
            params, OpenApiRequest(query=query, body=body, host_map={"project": project} if project else {}),
            RuntimeOptions(autoretry=False, connect_timeout=10000, read_timeout=self.timeout * 1000))
        if not isinstance(response, dict) or not isinstance(response.get("statusCode"), int):
            raise RequestError("InvalidResponse", "SLS response has no HTTP status")
        if not 200 <= response["statusCode"] < 300:
            raise RequestError("HTTP_" + str(response["statusCode"]), "SLS returned an unsuccessful HTTP status")
        if not isinstance(response.get("body"), dict):
            raise RequestError("InvalidResponse", "SLS response has no JSON object body")
        return response["body"]

    def query_logs(self, project, logstore, query, start, end, lines=100, offset=0, power_sql=False):
        body = self.request("GetLogsV2", "POST", "/logstores/" + quote(logstore, safe="") + "/logs", project=project,
                            body={"from": start, "to": end, "query": query, "line": lines,
                                  "offset": offset, "powerSql": power_sql})
        # REST calls this collection data; the existing CLI exposes it as logs.
        if not isinstance(body.get("meta"), dict) or not isinstance(body.get("data"), list):
            raise RequestError("InvalidResponse", "Log query response requires meta and data")
        if not isinstance(body["meta"].get("progress"), str):
            raise RequestError("InvalidResponse", "Log query response has no progress status")
        return {"meta": body["meta"], "logs": body["data"], "timeRange": {"from": start, "to": end}}
