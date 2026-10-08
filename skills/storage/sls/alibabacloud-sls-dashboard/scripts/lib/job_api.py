"""Report Job operations through the official SLS OpenAPI gateway and signer."""
from __future__ import annotations

import contextlib
import io
import re
from urllib.parse import quote

from .common import SkillError, resolve_user_agent, sls_endpoint


class JobApi:
    def __init__(self, region, profile=None, timeout=60, user_agent=None, sdk=None, endpoint=None):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", region) or timeout <= 0:
            raise SkillError("Invalid SLS region or timeout")
        self.region, self.profile, self.timeout, self.user_agent = region, profile, timeout, resolve_user_agent(user_agent)
        self.sdk = sdk
        self.endpoint = endpoint

    def call(self, operation, project, name=None, query=None, body=None):
        methods = {"ListJobs": "GET", "CreateJob": "POST", "UpdateJob": "PUT", "DeleteJob": "DELETE"}
        if operation not in methods or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", project):
            raise SkillError("Invalid Report Job operation or project")
        if operation in {"UpdateJob", "DeleteJob"} and (not isinstance(name, str) or not name.strip()):
            raise SkillError("A Report Job name is required")
        if body is not None and (not isinstance(body, dict) or body.get("type") != "Report"):
            raise SkillError("Only Report jobs can be written through this adapter")
        scheme, authority = sls_endpoint(self.endpoint, self.region, project)
        try:
            from alibabacloud_tea_openapi import utils_models as models
            from darabonba.runtime import RuntimeOptions
            from darabonba.policy.retry import RetryOptions
            if self.sdk is None:
                from alibabacloud_sls20201230.client import Client
                from alibabacloud_credentials.client import Client as Credentials
                from alibabacloud_credentials.provider.cli_profile import CLIProfileCredentialsProvider
                self.sdk = Client(models.Config(
                    endpoint=authority, region_id=self.region,
                    credential=Credentials(provider=CLIProfileCredentialsProvider(profile_name=self.profile)),
                    user_agent=self.user_agent, retry_options=RetryOptions(retryable=False)))
        except ImportError as exc:
            raise SkillError("Install the optional packages in references/cli-installation-guide.md#python-dependencies for Report Job operations", "MISSING_DEPENDENCY") from exc
        params = models.Params(
            action=operation, version="2020-12-30", protocol=scheme.upper(),
            pathname="/jobs" + ("/" + quote(name, safe="") if operation in {"UpdateJob", "DeleteJob"} else ""),
            method=methods[operation], auth_type="AK", style="ROA",
            req_body_type="json", body_type="json" if operation == "ListJobs" else "none")
        request = models.OpenApiRequest(host_map={"project": project}, headers={},
                                        query=query or {}, body=body, endpoint_override=authority)
        runtime = RuntimeOptions(retry_options=RetryOptions(retryable=False), autoretry=False,
                                 max_attempts=1, read_timeout=self.timeout * 1000,
                                 connect_timeout=self.timeout * 1000)
        try:
            # Some SDK versions emit transport diagnostics; never expose signed headers.
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                response = self.sdk.execute(params, request, runtime)
        except Exception as exc:
            code = str(getattr(exc, "code", "JOB_REQUEST_FAILED"))
            if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", code):
                code = "JOB_REQUEST_FAILED"
            raise SkillError(f"{operation} failed; inspect the scoped job state before retrying", code) from None
        if not isinstance(response, dict):
            raise SkillError("Job API returned an invalid response", "INVALID_RESPONSE")
        status = response.get("statusCode", 200)
        if not isinstance(status, int) or status >= 400:
            raise SkillError(f"{operation} did not succeed", "JOB_REQUEST_FAILED")
        result = response.get("body")
        if operation == "ListJobs" and not isinstance(result, dict):
            raise SkillError("ListJobs requires an object response", "INVALID_RESPONSE")
        return result or {}
