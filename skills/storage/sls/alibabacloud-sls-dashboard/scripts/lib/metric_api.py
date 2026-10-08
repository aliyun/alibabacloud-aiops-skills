"""Documented SLS Metricstore/StoreView HTTP API, using official credential providers."""
from __future__ import annotations

import base64
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .common import SkillError, resolve_user_agent, sls_endpoint


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class MetricApi:
    """Read-only, SLS-hosted Prometheus-compatible protocol; no external instances."""

    def __init__(self, profile=None, timeout=60, user_agent=None,
                 provider=None, opener=None, endpoint=None):
        self.profile, self.timeout, self.user_agent = profile, timeout, resolve_user_agent(user_agent)
        self.provider = provider
        self.opener = opener or build_opener(NoRedirect())
        self.endpoint = endpoint

    def _credentials(self):
        if self.provider is None:
            try:
                from alibabacloud_credentials.provider.cli_profile import CLIProfileCredentialsProvider
                self.provider = CLIProfileCredentialsProvider(profile_name=self.profile)
            except ImportError as exc:
                raise SkillError("Install the optional packages in references/cli-installation-guide.md#python-dependencies for metric view queries",
                                 "MISSING_DEPENDENCY") from exc
        try:
            value = self.provider.get_credentials()
            key, secret, token = value.get_access_key_id(), value.get_access_key_secret(), value.get_security_token()
        except Exception:
            # Provider exceptions can contain profile or authentication details.
            raise SkillError("The official credential provider could not resolve the selected CLI profile",
                             "CREDENTIAL_UNAVAILABLE") from None
        if not key or not secret:
            raise SkillError("SLS metric HTTP API requires AK or STS credentials", "CREDENTIAL_UNAVAILABLE")
        # Official MetricStore HTTP API: STS password is secret + '$' + token.
        password = secret + ("$" + token if token else "")
        return base64.b64encode((key + ":" + password).encode()).decode()

    def request(self, source, operation, params):
        if source["type"] != "metricstore_storeview":
            raise SkillError("This transport is for SLS metric StoreViews")
        if operation not in {"query", "query_range", "series", "label/__name__/values"}:
            raise SkillError("Unsupported metric read operation")
        project, region, name = source["project"], source["region"], source["name"]
        if not all(re.fullmatch(r"[a-z0-9][a-z0-9-]*", value) for value in (project, region)):
            raise SkillError("Invalid SLS project or region")
        scheme, authority = sls_endpoint(self.endpoint, region, project)
        url = (f"{scheme}://{project}.{authority}/prometheus/"
               f"{quote(project, safe='')}/{quote(name, safe='')}/api/v1/{operation}?"
               + urlencode(params, doseq=True))
        request = Request(url, headers={"Authorization": "Basic " + self._credentials(),
                                       "User-Agent": self.user_agent, "Accept": "application/json"})
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                content = response.read(16 * 1024 * 1024 + 1)
        except HTTPError as exc:
            raise SkillError(f"SLS metric HTTP API returned HTTP {exc.code}", "METRIC_HTTP_ERROR") from None
        except (URLError, TimeoutError, OSError):
            raise SkillError("SLS metric HTTP request failed", "METRIC_HTTP_ERROR") from None
        if len(content) > 16 * 1024 * 1024:
            raise SkillError("Metric response exceeds 16 MiB; narrow the time range or selectors",
                             "RESPONSE_TOO_LARGE")
        try:
            payload = json.loads(content)
        except (ValueError, UnicodeError):
            raise SkillError("Metric endpoint did not return JSON", "INVALID_RESPONSE") from None
        if not isinstance(payload, dict) or payload.get("status") != "success" or "data" not in payload:
            # Do not echo server errors: auth errors may contain credential material.
            raise SkillError("SLS metric API did not report success; verify query, access and time range",
                             "METRIC_QUERY_FAILED")
        return payload

    def query(self, source, query, start, end, mode, step, limit):
        params = {"query": query, "timeout": str(self.timeout) + "s"}
        if mode == "instant":
            params["time"] = end
        else:
            params.update(start=start, end=end, step=step)
        raw = self.request(source, "query" if mode == "instant" else "query_range", params)
        data = raw["data"]
        if not isinstance(data, dict) or data.get("resultType") not in {"vector", "matrix", "scalar", "string"}:
            raise SkillError("Unknown metric result type", "INVALID_RESPONSE")
        rows = []
        result = data.get("result")
        if not isinstance(result, list):
            raise SkillError("Metric result must be an array", "INVALID_RESPONSE")
        if data["resultType"] in {"scalar", "string"}:
            if len(result) != 2:
                raise SkillError("Invalid scalar metric result", "INVALID_RESPONSE")
            rows.append({"labels": {}, "time": result[0], "value": result[1]})
        else:
            for series in result:
                if not isinstance(series, dict) or not isinstance(series.get("metric"), dict):
                    raise SkillError("Invalid metric series", "INVALID_RESPONSE")
                points = [series.get("value")] if data["resultType"] == "vector" else series.get("values", [])
                if not isinstance(points, list):
                    raise SkillError("Invalid metric samples", "INVALID_RESPONSE")
                for point in points:
                    if not isinstance(point, list) or len(point) != 2:
                        raise SkillError("Invalid metric sample", "INVALID_RESPONSE")
                    rows.append({"labels": series["metric"], "time": point[0], "value": point[1]})
        warnings = raw.get("warnings", [])
        return {"source": source, "query": query, "window": {"from": start, "to": end},
                "rows": rows[:limit], "complete": not warnings and len(rows) <= limit,
                "progress": "Complete" if not warnings else "Partial",
                "truncated": len(rows) > limit, "limitReached": len(rows) >= limit,
                "limit": limit, "meta": {"resultType": data["resultType"], "warnings": warnings,
                                       "timeSemantics": "Prometheus API end is inclusive"},
                "raw": raw}

    def metrics(self, source, start, end, limit, keyword):
        raw = self.request(source, "label/__name__/values", {"start": start, "end": end})
        if not isinstance(raw["data"], list) or any(not isinstance(x, str) for x in raw["data"]):
            raise SkillError("Metric names must be an array of strings", "INVALID_RESPONSE")
        names = sorted({name for name in raw["data"] if keyword.lower() in name.lower()})
        return {"source": source, "metrics": names[:limit], "complete": len(names) <= limit and not raw.get("warnings"),
                "truncated": len(names) > limit, "limitReached": len(names) >= limit,
                "window": {"from": start, "to": end}, "raw": raw,
                "meta": {"scope": "Endpoint metadata lookback; not a historical inventory"}}

    def labels(self, source, metric, start, end, limit):
        raw = self.request(source, "series", {"match[]": metric, "start": start, "end": end})
        if not isinstance(raw["data"], list) or any(not isinstance(x, dict) for x in raw["data"]):
            raise SkillError("Metric series metadata must be an array of label objects", "INVALID_RESPONSE")
        labels = {}
        for row in raw["data"][:limit]:
            for key, value in row.items():
                if key != "__name__":
                    labels.setdefault(key, set()).add(str(value))
        return {"source": source, "metric": metric, "window": {"from": start, "to": end},
                "labels": {key: {"sampleValues": sorted(values), "sampleCardinality": len(values)}
                           for key, values in sorted(labels.items())},
                "complete": len(raw["data"]) <= limit and not raw.get("warnings"),
                "truncated": len(raw["data"]) > limit, "limitReached": len(raw["data"]) >= limit,
                "raw": raw, "meta": {"scope": "Endpoint metadata lookback; values are sampled"}}
