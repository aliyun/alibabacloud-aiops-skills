"""Run inside the selected ACK container. CONFIG is supplied by ack.py."""

import base64
import datetime
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


class ProbeError(Exception):
    def __init__(self, **details):
        self.details = details


class RejectRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def code(value):
    return value if isinstance(value, str) and re.fullmatch(r"[a-zA-Z0-9_.:-]{1,100}", value) else None


def get_json(url, stage, *, body=None, headers=None):
    request = urllib.request.Request(url, data=body, headers=headers or {})
    opener = urllib.request.build_opener(RejectRedirect())
    try:
        with opener.open(request, timeout=15) as response:
            return json.load(response), code(response.headers.get("x-acs-request-id"))
    except urllib.error.HTTPError as exc:
        try:
            data = json.loads(exc.read(65536))
            if not isinstance(data, dict):
                data = {}
        except ValueError:
            data = {}
        raise ProbeError(stage=stage, http_status=exc.code,
                         error=code(data.get("error") or data.get("code") or data.get("Code")),
                         request_id=code(data.get("RequestId") or data.get("requestId")
                                         or exc.headers.get("x-acs-request-id"))) from None
    except (OSError, ValueError):
        raise ProbeError(stage=stage, error="network_or_response_error") from None


def read_assertion(config):
    try:
        path = os.environ["ALIBABA_CLOUD_OIDC_TOKEN_FILE"]
        if path != config.get("token_file", path):
            raise ValueError("unexpected projected token path")
        with Path(path).open("rb") as token_file:
            token = token_file.read(65537).decode().strip()
        if len(token) > 65536:
            raise ValueError("oversize")
        _, payload, _ = token.split(".")
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        audience = claims["aud"]
        if isinstance(audience, str):
            audience = [audience]
        kube = claims["kubernetes.io"]
        expected_subject = "system:serviceaccount:" + config["namespace"] + ":" + config["service_account"]
        expected = (
            claims["iss"] == config["issuer"],
            "sts.aliyuncs.com" in audience,
            claims["sub"] == expected_subject,
            kube["namespace"] == config["namespace"],
            kube["serviceaccount"]["name"] == config["service_account"],
            kube["pod"]["name"] == config["pod"],
            claims["exp"] > time.time() + 30,
        )
    except (OSError, KeyError, ValueError, TypeError, AttributeError):
        raise ProbeError(stage="rrsa", error="missing_or_invalid_rrsa_token_file") from None
    if not all(expected):
        failed = ("issuer", "audience", "subject", "namespace", "service_account", "pod", "expiration")
        raise ProbeError(stage="rrsa", error="rrsa_claim_mismatch",
                         fields=[key for key, ok in zip(failed, expected) if not ok])
    return token


def caller_identity(credentials, region, target):
    host = "sts." + region + ".aliyuncs.com"
    payload_hash = hashlib.sha256(b"").hexdigest()
    headers = {
        "host": host,
        "x-acs-action": "GetCallerIdentity",
        "x-acs-version": "2015-04-01",
        "x-acs-content-sha256": payload_hash,
        "x-acs-date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "x-acs-security-token": credentials["securityToken"],
        "x-acs-signature-nonce": uuid.uuid4().hex,
    }
    signed = ";".join(sorted(headers))
    canonical_headers = "".join(key + ":" + headers[key] + "\n" for key in sorted(headers))
    canonical = "\n".join(("GET", "/", "", canonical_headers, signed, payload_hash))
    algorithm = "ACS3-HMAC-SHA256"
    message = algorithm + "\n" + hashlib.sha256(canonical.encode()).hexdigest()
    signature = hmac.new(credentials["accessKeySecret"].encode(), message.encode(), hashlib.sha256).hexdigest()
    headers["Authorization"] = (algorithm + " Credential=" + credentials["accessKeyId"]
                                + ",SignedHeaders=" + signed + ",Signature=" + signature)
    reply, request_id = get_json("https://" + host + "/", "sts_identity", headers=headers)
    account, role = target.split("::", 1)[1].split(":role/", 1)
    expected = "acs:ram::" + account + ":assumed-role/" + role + "/"
    if reply.get("AccountId") != account or not reply.get("Arn", "").startswith(expected):
        raise ProbeError(stage="sts_identity", error="target_role_mismatch")
    return code(reply.get("RequestId")) or request_id


def run(config):
    token = read_assertion(config)
    result = {"rrsa": "verified"}
    if "client_id" not in config:
        endpoint = config.get("reachability_endpoint")
        if endpoint:
            try:
                req = urllib.request.Request(endpoint, method="HEAD")
                with urllib.request.build_opener(RejectRedirect()).open(req, timeout=15):
                    pass
            except urllib.error.HTTPError as error:
                if error.code not in (400, 401, 403, 404, 405):
                    raise ProbeError(stage="network", http_status=error.code,
                                     error="eiam_endpoint_check_failed") from None
            except OSError:
                raise ProbeError(stage="network", error="eiam_endpoint_unreachable") from None
            result["eiam_reachable"] = True
        return result
    parameters = {
        "grant_type": "client_credentials",
        "client_id": config["client_id"],
        "client_assertion_type": "urn:cloud:idaas:params:oauth:client-assertion-type:id-token-bearer",
        "client_assertion": token,
        "application_federated_credential_name": config["credential_name"],
        "scope": config["scope"],
    }
    reply, request_id = get_json(config["token_endpoint"], "m2m",
                                 body=urllib.parse.urlencode(parameters).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    access_token = reply.get("access_token")
    if not access_token or reply.get("token_type", "").lower() != "bearer":
        raise ProbeError(stage="m2m", error="missing_bearer_token")
    result["m2m"] = {"status": "verified", "request_id": request_id,
                     "expires_in": reply.get("expires_in") if isinstance(reply.get("expires_in"), int) else None}
    if "role_arn" in config:
        params = urllib.parse.urlencode({"cloudAccountRoleExternalId": config["role_arn"]})
        url = (config["developer_endpoint"] + "/v2/" + config["instance_id"]
               + "/cloudAccountRoles/_/actions/obtainAccessCredential?" + params)
        reply, request_id = get_json(url, "pam_sts", headers={"Authorization": "Bearer " + access_token})
        try:
            credentials = reply["cloudAccountRoleAccessCredential"]["alibabaCloudStsToken"]
            if reply.get("cloudAccountRoleExternalId") != config["role_arn"] or not all(
                credentials[key] for key in ("accessKeyId", "accessKeySecret", "securityToken")
            ):
                raise KeyError("credentials")
        except (KeyError, TypeError):
            raise ProbeError(stage="pam_sts", error="missing_or_mismatched_sts_credentials") from None
        result["sts"] = {"status": "verified", "role_arn": config["role_arn"],
                         "request_id": request_id, "identity_request_id": caller_identity(
                             credentials, config["region"], config["role_arn"])}
    return result


if __name__ == "__main__":
    try:
        result = run(CONFIG)
        if "workbench" in CONFIG:
            result["workbench"] = CONFIG["workbench"]
        print(json.dumps(result))
    except ProbeError as error:
        print(json.dumps({"error": error.details}))
        sys.exit(1)
    except Exception:
        print(json.dumps({"error": {"stage": "probe", "error": "unexpected_response_or_runtime"}}))
        sys.exit(1)
