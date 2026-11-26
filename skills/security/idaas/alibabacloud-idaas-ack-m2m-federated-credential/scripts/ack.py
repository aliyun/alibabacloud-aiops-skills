#!/usr/bin/env python3
"""Discover, configure, and verify ACK-to-EIAM federation."""

import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys
import tempfile
import uuid


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((ROOT / "references/manifest.json").read_text())
AUDIENCE = "sts.aliyuncs.com"
PAM = "iap_pam"
PAM_IDENTIFIER = "urn:cloud:idaas:pam"
PAM_PERMISSION = "cloud_account_role:obtain_access_credential"
PAM_SCOPE = PAM_IDENTIFIER + "|" + PAM_PERMISSION
TOKEN_PATH = "/api/v2/iauths_system/oauth2/token"
INJECTION = "pod-identity.alibabacloud.com/injection"
ROLE_ANNOTATION = "pod-identity.alibabacloud.com/role-name"
TOKEN_ENV = "ALIBABA_CLOUD_OIDC_TOKEN_FILE"
PROJECTED_VOLUME = "idaas-oidc-token"
PROJECTED_DIRECTORY = "/var/run/secrets/idaas.alibabacloud.com"
PROJECTED_TOKEN = PROJECTED_DIRECTORY + "/token"


class Failure(Exception):
    pass


class CloudFailure(Failure):
    def __init__(self, action, doc):
        self.status = doc.get("status_code")
        self.code = doc.get("error_code")
        detail = {k: doc[k] for k in ("error_code", "status_code", "request_id") if doc.get(k)}
        try:
            inner = json.loads(doc.get("message") or "")
        except (TypeError, ValueError):
            inner = {}
        if isinstance(inner, dict):
            for source, target in (("code", "error_code"), ("requestId", "request_id")):
                if isinstance(inner.get(source), str):
                    detail.setdefault(target, inner[source])
        super().__init__(action + " failed: " + json.dumps(detail))


def require(condition, message):
    if not condition:
        raise Failure(message)


def checked(pattern, message="unexpected value format"):
    def parse(value):
        if not re.fullmatch(pattern, value):
            raise argparse.ArgumentTypeError(message)
        return value
    return parse


def application_name(value):
    if not value.strip() or not value.isprintable():
        raise argparse.ArgumentTypeError("enter a nonblank, printable application display name")
    return value


def configured_name(value):
    if not value.strip() or not value.isprintable():
        raise argparse.ArgumentTypeError("use a nonblank, printable name from the local configuration")
    return value


def local_file_path(value):
    filename = value.rsplit("/", 1)[-1]
    if not value.isprintable() or not filename.strip() or filename in (".", "..", "~"):
        raise argparse.ArgumentTypeError("use a printable path to a local file")
    return value


REGION = checked(r"[a-z][a-z0-9-]{1,31}")
NAME = checked(r"[a-z0-9][a-z0-9_-]{0,63}",
               "use 1-64 lowercase letters, digits, hyphens, or underscores and start with a letter or digit")
KUBE_NAME = checked(r"[a-z0-9](?:[-a-z0-9.]{0,251}[a-z0-9])?")
INSTANCE_ID = checked(r"idaas_[a-z0-9]{6,64}")
CLUSTER_ID = checked(r"c[0-9a-f]{32}")
ROLE_ARN = re.compile(r"acs:ram::[0-9]{8,20}:role/[a-zA-Z0-9_@.-]{1,64}")


def json_object(raw):
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {}


def execute(command, *, env=None, stdin=None, timeout=25, timeout_message=None):
    try:
        return subprocess.run(command, env=env, input=stdin, capture_output=True,
                              text=True, timeout=timeout, check=False)
    except FileNotFoundError as error:
        raise Failure("Required executable is unavailable: " + command[0]) from error
    except subprocess.TimeoutExpired as error:
        message = timeout_message or command[0] + " timed out. Reconcile any unknown write result before retrying."
        raise Failure(message) from error


class Cloud:
    def __init__(self, args):
        self.env = os.environ.copy()
        if args.cli_profile:
            # ACK also has a business query parameter named profile.
            self.env["ALIBABA_CLOUD_PROFILE"] = args.cli_profile
        self.args = args
        self.session = args.session_id
        self.user_agent = ("AlibabaCloud-Agent-Skills/" + MANIFEST["name"] + "/" + self.session
                           + " skill-version/" + MANIFEST["version"])

    def call(self, product, action, *params, region=None, instance=None, absent=None):
        command = ["aliyun", product, action, "--user-agent", self.user_agent]
        if region:
            command.extend(("--region", region))
        if instance:
            command.extend(("--InstanceId", instance))
        result = execute(command + list(params), env=self.env)
        if result.returncode:
            error = json_object(result.stderr.strip()) or json_object(result.stdout.strip())
            if absent and error.get("error_code") == "ResourceNotFound." + absent:
                print(action + " absent", file=sys.stderr)
                return {}
            raise CloudFailure(action, error)
        payload = json_object(result.stdout.strip())
        require(isinstance(payload, dict) and payload, action + " returned an invalid or empty response")
        rid = payload.get("RequestId") or payload.get("requestId")
        print(action + ((" request_id=" + str(rid)) if rid else ""), file=sys.stderr)
        return payload

    def eiam(self, action, *params, absent=None):
        return self.call("eiam", action, *params, region=self.args.eiam_region,
                         instance=self.args.instance_id, absent=absent)

    def eiam_list(self, action, field, *params):
        values, seen, token = [], set(), None
        for page in range(1, 101):
            next_arg = ("--NextToken", token) if token else ()
            if action == "ListApplications":
                next_arg = ("--PageNumber", str(page), "--PageSize", "100")
            data = self.eiam(action, *params, *next_arg)
            items = data.get(field)
            require(isinstance(items, list) or (items is None and data.get("TotalCount") == 0),
                    action + " returned an unexpected collection")
            values.extend(items or [])
            token = data.get("NextToken")
            if action == "ListApplications" and len(values) < data.get("TotalCount", len(values)):
                require(bool(items), action + " returned an incomplete page")
                continue
            if not token:
                require(not isinstance(data.get("TotalCount"), int) or len(values) >= data["TotalCount"],
                        action + " returned incomplete results")
                return values
            require(isinstance(token, str) and token not in seen, action + " repeated its pagination token")
            seen.add(token)
        raise Failure(action + " exceeded the pagination limit")

    def identity(self):
        result = self.call("sts", "GetCallerIdentity", region=self.args.ack_region or self.args.eiam_region)
        require(bool(re.fullmatch(r"[0-9]{8,20}", str(result.get("AccountId", "")))),
                "STS did not return a valid caller account")
        return {k: result.get(k) for k in ("AccountId", "Arn", "IdentityType")}


def discover(args, cloud):
    result = {"caller": cloud.identity()}
    regions = cloud.call("cs", "DescribeRegions", "--clusterType", "ManagedKubernetes",
                         region=args.ack_region)
    choices = regions.get("regions")
    require(isinstance(choices, list) and choices, "ACK DescribeRegions returned no supported regions")
    result["regions"] = choices
    if args.ack_region:
        require(any(r.get("regionId") == args.ack_region for r in choices), "Select a region returned by ACK")
        rows = []
        for page in range(1, 101):
            data = cloud.call("cs", "DescribeClustersForRegion", "--region_id", args.ack_region,
                              "--page_number", str(page), "--page_size", "50", region=args.ack_region)
            info = data.get("page_info", {})
            count = info.get("total_count")
            items = data.get("clusters")
            require(isinstance(count, int) and count >= 0 and
                    (isinstance(items, list) or (items is None and count == 0)),
                    "ACK list response has no valid pagination data")
            rows.extend(items or [])
            require(len({row["cluster_id"] for row in rows}) == len(rows), "ACK list repeated a cluster")
            if len(rows) >= count:
                break
            require(items, "ACK pagination stopped before total_count was reached")
        else:
            raise Failure("ACK discovery exceeded the page limit")
        result["clusters"] = [{k: row.get(k) for k in
                               ("cluster_id", "name", "region_id", "state", "cluster_type",
                                "cluster_spec", "profile", "current_version", "rrsa_config")}
                              for row in rows if row.get("cluster_type") == "ManagedKubernetes"
                              and row.get("profile") in (None, "Default")]
        if not result["clusters"]:
            result["note"] = "No managed clusters were listed. A known cluster ID can be checked directly."
    return result


def kube(args, *params, stdin=None, probe=False):
    operation = "kubectl " + params[0]
    result = execute(["kubectl", "--context=" + args.context, "--request-timeout=15s", *params],
                     stdin=stdin, timeout=65 if probe else 20,
                     timeout_message=operation + " timed out. Check the selected context and execution environment.")
    data = json_object(result.stdout.strip())
    if result.returncode:
        if probe and isinstance(data, dict) and isinstance(data.get("error"), dict):
            error = data["error"]
            safe = {k: error[k] for k in ("stage", "error", "http_status", "request_id", "fields") if error.get(k)}
            raise Failure("Pod probe failed: " + json.dumps(safe))
        error = result.stderr.lower()
        for markers, explanation in (
            (("forbidden", "unauthorized", "must be logged in"), "Kubernetes authentication or RBAC denied access"),
            (("x509", "certificate", "tls handshake"), "TLS verification or handshake failed"),
            (("i/o timeout", "deadline exceeded", "timed out"), "the request timed out"),
            (("connection refused", "no route to host", "network is unreachable", "no such host"),
             "the API Server could not be reached"),
            (("notfound", "not found"), "the requested resource or container executable was not found"),
        ):
            if any(marker in error for marker in markers):
                raise Failure(operation + " failed because " + explanation + ".")
        raise Failure(f"{operation} failed (exit code {result.returncode}). Check the context, access and Pod runtime.")
    require(isinstance(data, dict) and data, "kubectl returned an unexpected response")
    return data


def workloads(args, _cloud):
    if not args.namespace:
        items = kube(args, "get", "namespaces", "-o", "json")["items"]
        return {"namespaces": [{"name": x["metadata"]["name"],
                                "injection": x["metadata"].get("labels", {}).get(INJECTION)}
                               for x in items if x.get("status", {}).get("phase") == "Active"]}
    ns = "--namespace=" + args.namespace
    service_accounts = kube(args, "get", "serviceaccounts", ns, "-o", "json")["items"]
    pods = kube(args, "get", "pods", ns, "-o", "json")["items"]
    return {"namespace": args.namespace,
            "service_accounts": [{"name": x["metadata"]["name"],
                                  "rrsa_role": x["metadata"].get("annotations", {}).get(ROLE_ANNOTATION)}
                                 for x in service_accounts],
            "pods": [{"name": x["metadata"]["name"], "service_account": x["spec"]["serviceAccountName"],
                      "phase": x.get("status", {}).get("phase"),
                      "containers": [c["name"] for c in x["spec"]["containers"]]} for x in pods]}


def pod_binding(args):
    projected = getattr(args, "token_source", "webhook") == "projected"
    volume_name = PROJECTED_VOLUME if projected else "rrsa-oidc-token"
    ns = "--namespace=" + args.namespace
    pod = kube(args, "get", "pod", args.pod, ns, "-o", "json")
    ns_data = kube(args, "get", "namespace", args.namespace, "-o", "json")
    sa = kube(args, "get", "serviceaccount", args.service_account, ns, "-o", "json")
    role = None
    if not projected:
        require(ns_data["metadata"].get("labels", {}).get(INJECTION) == "on",
                "Namespace is missing pod-identity.alibabacloud.com/injection=on")
        role = sa["metadata"].get("annotations", {}).get(ROLE_ANNOTATION)
        require(bool(role), "ServiceAccount is missing pod-identity.alibabacloud.com/role-name")
    spec = pod["spec"]
    require(spec.get("serviceAccountName") == args.service_account, "Pod uses a different ServiceAccount")
    require(pod.get("status", {}).get("phase") == "Running", "Select a running RRSA-enabled Pod")
    ready = {c["name"] for c in pod["status"].get("containerStatuses", []) if c.get("ready")}
    mounted = {c["name"]: c for c in spec["containers"] if c["name"] in ready
               and any(e["name"] == TOKEN_ENV for e in c.get("env", []))
               and any(v["name"] == volume_name for v in c.get("volumeMounts", []))}
    container = args.container if args.container else next(iter(mounted)) if len(mounted) == 1 else None
    require(container in mounted, "Choose a ready container with the configured OIDC token variable and volume."
            if projected else "Choose a ready container with RRSA variable and volume. Recreate a Pod after fixing injection.")
    tokens = [s["serviceAccountToken"] for v in spec.get("volumes", []) if v["name"] == volume_name
              for s in v.get("projected", {}).get("sources", []) if "serviceAccountToken" in s]
    if projected:
        selected = mounted[container]
        require([e.get("value") for e in selected["env"] if e["name"] == TOKEN_ENV] == [PROJECTED_TOKEN],
                "Projected token variable must point to " + PROJECTED_TOKEN)
        require(any(v.get("mountPath") == PROJECTED_DIRECTORY and v.get("readOnly") is True
                    and not (v.get("subPath") or v.get("subPathExpr"))
                    for v in selected["volumeMounts"] if v["name"] == PROJECTED_VOLUME),
                "Projected token volume must be mounted read-only at " + PROJECTED_DIRECTORY)
        tokens = [token for token in tokens if token.get("path") == "token"]
    require(any(t.get("audience") == AUDIENCE for t in tokens),
            "OIDC token projection has the wrong audience or path" if projected else "RRSA projection has the wrong audience")
    return container, role


def probe_input(args, container, config):
    command = ["exec", "--namespace=" + args.namespace, "-i", args.pod,
               "--container=" + container, "--", "python3", "-"]
    source = "CONFIG = " + repr(config) + "\n" + (ROOT / "scripts/pod_verify.py").read_text()
    return command, source


def pod_probe(args, container, config):
    command, source = probe_input(args, container, config)
    return kube(args, *command, stdin=source, probe=True)


def workbench_command(args, config):
    command, source = probe_input(args, args.container, config)
    shell = shlex.join(["kubectl", "--request-timeout=65s", *command])
    return shell + " <<'ACK_PROBE_PY'\n" + source + "\nACK_PROBE_PY\n"


@contextmanager
def read_local_file(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as error:
        raise Failure("Use a readable, regular local file") from error
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), "Use a readable, regular local file")
        with os.fdopen(fd, encoding="utf-8", closefd=False) as stream:
            yield stream
    finally:
        os.close(fd)


def read_workbench_preflight(path, binding):
    with read_local_file(Path(path).expanduser()) as stream:
        evidence = json_object(stream.read(8193))
    require(evidence == {"rrsa": "verified", "eiam_reachable": True, "workbench": binding}
            and evidence.get("eiam_reachable") is True,
            "Use the successful Workbench preflight JSON for this exact session and workload")


def ack_environment(args, cloud):
    projected = getattr(args, "token_source", "webhook") == "projected"
    cluster = cloud.call("cs", "DescribeClusterDetail", "--ClusterId", args.cluster_id, region=args.ack_region)
    require(cluster.get("cluster_id") == args.cluster_id and cluster.get("region_id") == args.ack_region and
            cluster.get("cluster_type") == "ManagedKubernetes" and cluster.get("profile") == "Default" and
            cluster.get("state") == "running", "Select a running ACK managed cluster in the selected region")
    version = re.match(r"v?(\d+)\.(\d+)", cluster.get("current_version", ""))
    require(version and tuple(map(int, version.groups())) >= (1, 22), "ACK Kubernetes 1.22 or later is required")
    rrsa = cluster.get("rrsa_config") or {}
    require(rrsa.get("enabled") is True and rrsa.get("oidc_name"), "ACK RRSA OIDC is not enabled")
    if not projected:
        addon = cloud.call("cs", "GetClusterAddonInstance", "--cluster_id", args.cluster_id,
                           "--instance_name", "ack-pod-identity-webhook", region=args.ack_region)
        require(addon.get("name") == "ack-pod-identity-webhook" and addon.get("state") == "active",
                "ACK RRSA webhook is not active")
    provider = cloud.call("ims", "GetOIDCProvider", "--OIDCProviderName", rrsa["oidc_name"],
                          region=args.ack_region)["OIDCProvider"]
    issuer = provider.get("IssuerUrl", "")
    audiences = provider.get("ClientIds", "")
    if isinstance(audiences, str):
        audiences = audiences.split(",")
    require(re.fullmatch(r"https://[a-z0-9.-]+\.aliyuncs\.com/[a-zA-Z0-9_/-]+", issuer)
            and rrsa.get("open_api_configuration_url") == issuer + "/.well-known/openid-configuration"
            and AUDIENCE in audiences, "ACK and RAM RRSA issuer or audience do not match")
    result = {"cluster_id": args.cluster_id, "cluster_name": cluster["name"], "version": cluster["current_version"],
              "issuer": issuer, "audience": AUDIENCE, "namespace": args.namespace,
              "service_account": args.service_account, "pod": args.pod}
    if projected:
        result["token_file"] = PROJECTED_TOKEN
    return result


def instance_environment(cloud):
    instance = cloud.eiam("GetInstance")["Instance"]
    license_data = cloud.eiam("GetInstanceLicense")["License"]
    require(instance.get("InstanceId") == cloud.args.instance_id and instance.get("Status") == "running",
            "EIAM instance is unavailable")
    details = license_data.get("InstanceLicenseDetail") or {}
    require(license_data.get("Edition") == "enterprise" and license_data.get("LicenseStatus") == "valid" and
            details.get("M2mApplicationLicenseStatus") == "enabled",
            "A running EIAM Enterprise instance with valid machine identity management (M2M) is required")
    endpoint = instance.get("DefaultEndpoint") or {}
    host = endpoint.get("Endpoint", "")
    require(endpoint.get("Status") == "resolved" and re.fullmatch(r"[a-z0-9-]+\.aliyunidaas\.com", host),
            "EIAM must report a resolved Alibaba Cloud default endpoint for token exchange")
    return {"instance_id": cloud.args.instance_id, "edition": license_data["Edition"], "m2m": "enabled",
            "token_endpoint": "https://" + host + TOKEN_PATH}


def preflight(args, cloud, *, show_candidates=True):
    generate = getattr(args, "workbench", False)
    evidence_path = getattr(args, "workbench_result", None)
    if generate or evidence_path:
        require(args.container, "Select the exact Workbench container with --container")
    caller = cloud.identity()
    eiam = instance_environment(cloud)
    config = ack_environment(args, cloud)
    probe = dict(config, reachability_endpoint=eiam["token_endpoint"])
    result = {"caller": caller, "eiam": eiam, "ack": config}
    if generate or evidence_path:
        binding = dict(boundary(args, cloud, caller["AccountId"]), pod=args.pod,
                       container=args.container, issuer=config["issuer"], endpoint=eiam["token_endpoint"])
        if getattr(args, "token_source", "webhook") == "projected":
            binding["token_source"] = "projected"
        result.update(container=args.container, execution="workbench")
        if generate:
            result["workbench_command"] = workbench_command(args, dict(probe, workbench=binding))
        else:
            read_workbench_preflight(evidence_path, binding)
            result["rrsa"] = "verified"
    else:
        container, role = pod_binding(args)
        rrsa = pod_probe(args, container, probe)
        require(rrsa.get("rrsa") == "verified" and rrsa.get("eiam_reachable") is True,
                "Pod did not verify the RRSA token claims and EIAM connectivity")
        result.update(container=container, rrsa_role=role, rrsa="verified")
    if show_candidates:
        providers = cloud.eiam_list("ListFederatedCredentialProviders", "FederatedCredentialProviders",
                                    "--FederatedCredentialProviderType", "oidc")
        result["provider_candidates"] = [
            {"id": p["FederatedCredentialProviderId"], "name": p["FederatedCredentialProviderName"]}
            for p in providers if matching_provider(p, config)]
    return result


def matching_provider(p, config):
    settings = p.get("OidcProviderConfig") or {}
    return (p.get("Status") == "enabled" and settings.get("Issuer") == config["issuer"]
            and settings.get("Audiences") == [AUDIENCE] and settings.get("JwksSource") == "dynamic_from_issuer")


def boundary(args, cloud, account):
    return {"account": account, "instance": args.instance_id, "eiam_region": args.eiam_region,
            "ack_region": args.ack_region, "cluster": args.cluster_id, "namespace": args.namespace,
            "service_account": args.service_account, "session_id": cloud.session}


@contextmanager
def inventory(args, cloud, account, *, new=False):
    path = Path(args.state).expanduser().absolute()
    require(path.parent.is_dir() and not path.is_symlink(), "The state path must be in an existing directory")
    lk = os.open(str(path) + ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    with os.fdopen(lk, "w") as lock:
        require(stat.S_ISREG(os.fstat(lock.fileno()).st_mode), "Unsafe state lock file")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Failure("Another command is using this state file") from exc
        if path.exists():
            require(path.is_file() and not path.is_symlink(), "Unsafe state file")
            with read_local_file(path) as stream:
                doc = json_object(stream.read())
        else:
            require(new, "Supply the existing state from configure")
            doc = {"binding": boundary(args, cloud, account), "resources": {}}
        require(doc.get("binding") == boundary(args, cloud, account) and isinstance(doc.get("resources"), dict),
                "State belongs to a different account, scope, or session")

        def save():
            fd, temp = tempfile.mkstemp(prefix=".ack-state-", dir=path.parent)
            try:
                with os.fdopen(fd, "w") as stream:
                    json.dump(doc, stream, indent=2)
                    stream.write("\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp, path)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)

        yield doc, save


def record(doc, save, key, name, id_field, action, request, *, reused=None):
    resources = doc["resources"]
    if key in resources:
        prior = resources[key]
        require(prior["name"] == name and (not reused or prior["id"] == reused),
                key + " differs from the recorded selection")
        return prior["id"]
    if reused:
        resources[key] = {"id": reused, "name": name, "owned": False}
    else:
        require(not doc.get("pending"), "A previous write has an unknown result: " + json.dumps(doc.get("pending")))
        doc["pending"] = {"resource": key, "name": name, "action": action}
        save()
        try:
            value = request().get(id_field)
        except CloudFailure as error:
            if error.status in (400, 401, 403, 404, 409, 429):
                del doc["pending"]
                save()
            raise
        require(isinstance(value, str) and value, action + " did not return an ID. Reconcile by exact name.")
        resources[key] = {"id": value, "name": name, "owned": True}
        del doc["pending"]
    save()
    return resources[key]["id"]


def verify_credential(cloud, app, cred, provider, args):
    config = cloud.eiam("GetApplicationFederatedCredential", "--ApplicationId", app,
                        "--ApplicationFederatedCredentialId", cred)["ApplicationFederatedCredential"]
    verification = config.get("OidcVerificationConfig") or {}
    k8s = verification.get("KubernetesConfig") or {}
    require(config.get("Status") == "enabled" and config.get("FederatedCredentialProviderId") == provider and
            config.get("VerificationMode") == "structured" and verification.get("Profile") == "kubernetes" and
            k8s.get("Namespace") == args.namespace and k8s.get("ServiceAccountName") == args.service_account and
            (k8s.get("PodNamePrefix") or None) == args.pod_prefix, "EIAM application credential readback mismatch")
    return config


def find_pam_scope(cloud):
    info = cloud.eiam("GetApplication", "--ApplicationId", PAM)["Application"]
    require(info.get("ResourceServerIdentifier") == PAM_IDENTIFIER, "The built-in PAM application is unavailable")
    scopes = cloud.eiam_list("ListResourceServerScopes", "ResourceServerScopes", "--ApplicationId", PAM,
                             "--ResourceServerScopeType", "all")
    found = [s["ResourceServerScopeId"] for s in scopes if s.get("ResourceServerScopeValue") == PAM_PERMISSION]
    require(len(found) == 1, "The required PAM scope is unavailable or ambiguous")
    return found[0]


def pam_feature(cloud, app, scope_id):
    params = ("--ClientApplicationId", app, "--ResourceServerApplicationId", PAM)
    cloud.eiam("AuthorizeResourceServerToClient", *params, "--yes")
    cloud.eiam("AuthorizeResourceServerScopesToClient", *params, "--force", "--method", "POST",
               "--ResourceServerScopeIds.1", scope_id, "--yes")


def configure(args, cloud):
    require(args.confirmed, "Confirm the target, names/IDs, and PAM feature permission before configure")
    env = preflight(args, cloud, show_candidates=False)
    with inventory(args, cloud, env["caller"]["AccountId"], new=True) as (doc, save):
        require(not doc.get("closed"), "Use a new session and state path after cleanup")
        require(not args.pod_prefix or args.pod.startswith(args.pod_prefix),
                "The selected Pod must match the requested credential Pod name prefix")
        res = doc["resources"]
        desired = {"provider_name": args.provider_name, "provider_id": args.provider_id,
                   "app_name": args.app_name, "app_id": args.app_id, "credential_name": args.credential_name,
                   "pod_prefix": args.pod_prefix, "pam_feature": args.pam_feature}
        require(doc.get("selection", desired) == desired, "Use the original selection when resuming configure")
        doc["selection"] = desired
        require(not doc.get("pending"), "Reconcile the recorded unknown write result before configure")
        scope_id = find_pam_scope(cloud) if args.pam_feature and not doc.get("pam_scope_id") else None
        # Reconcile read-only selections before creating any dependency.
        providers = cloud.eiam_list("ListFederatedCredentialProviders", "FederatedCredentialProviders",
                                    "--FederatedCredentialProviderType", "oidc")
        selected_provider = args.provider_id or res.get("provider", {}).get("id")
        if selected_provider:
            p = cloud.eiam("GetFederatedCredentialProvider", "--FederatedCredentialProviderId",
                           selected_provider)["FederatedCredentialProvider"]
            require(matching_provider(p, env["ack"]), "Selected trust source does not match the ACK issuer, audience, and JWKS mode")
        else:
            require(not any(p["FederatedCredentialProviderName"] == args.provider_name for p in providers),
                    "Trust source name already exists. Choose it by ID if it matches, or use a different name.")
        apps = cloud.eiam_list("ListApplications", "Applications", "--SsoType", "oidc+oauth2/m2m")
        selected_app = args.app_id or res.get("application", {}).get("id")
        if selected_app:
            app_info = cloud.eiam("GetApplication", "--ApplicationId", selected_app)["Application"]
            require(app_info.get("Status") == "enabled" and
                    (not args.app_id or app_info.get("M2MClientStatus") == "enabled"),
                    "Selected application is disabled or has no enabled M2M Client")
            credentials = cloud.eiam_list("ListApplicationFederatedCredentials", "ApplicationFederatedCredentials",
                                          "--ApplicationId", selected_app)
            require("credential" in res or not any(c["ApplicationFederatedCredentialName"] == args.credential_name
                                                    for c in credentials),
                    "The application already has a credential with that name")
        else:
            require(not any(a["ApplicationName"] == args.app_name for a in apps), "M2M application name already exists")
        provider = record(doc, save, "provider", p["FederatedCredentialProviderName"] if selected_provider else args.provider_name,
                          "FederatedCredentialProviderId", "CreateFederatedCredentialProvider",
                          lambda: cloud.eiam("CreateFederatedCredentialProvider", "--force", "--method", "POST",
                                             "--FederatedCredentialProviderName", args.provider_name,
                                             "--FederatedCredentialProviderType", "oidc",
                                             "--NetworkAccessEndpointId", "inae_public",
                                             "--OidcProviderConfig.Issuer", env["ack"]["issuer"],
                                             "--OidcProviderConfig.Audiences.1", AUDIENCE,
                                             "--OidcProviderConfig.JwksSource", "dynamic_from_issuer", "--yes"),
                          reused=args.provider_id)
        p = cloud.eiam("GetFederatedCredentialProvider", "--FederatedCredentialProviderId",
                       provider)["FederatedCredentialProvider"]
        require(matching_provider(p, env["ack"]), "Trust source readback mismatch")
        app = record(doc, save, "application", app_info["ApplicationName"] if selected_app else args.app_name,
                     "ApplicationId", "CreateApplication",
                     lambda: cloud.eiam("CreateApplication", "--ApplicationName", args.app_name,
                                        "--ApplicationSourceType", "urn:alibaba:idaas:app:source:standard",
                                        "--SsoType", "oidc+oauth2/m2m", "--yes"), reused=args.app_id)
        app_id = ("--ApplicationId", app)
        a = cloud.eiam("GetApplication", *app_id)["Application"]
        require(a.get("Status") == "enabled" and a.get("M2MClientStatus") == "enabled",
                "The application M2M Client is not enabled. Check the application before continuing.")
        prefix = ("--OidcVerificationConfig.KubernetesConfig.PodNamePrefix", args.pod_prefix) if args.pod_prefix else ()
        cred = record(doc, save, "credential", args.credential_name, "ApplicationFederatedCredentialId",
                      "CreateApplicationFederatedCredential",
                      lambda: cloud.eiam("CreateApplicationFederatedCredential", *app_id, "--force", "--method", "POST",
                                         "--FederatedCredentialProviderId", provider,
                                         "--ApplicationFederatedCredentialType", "oidc",
                                         "--ApplicationFederatedCredentialName", args.credential_name,
                                         "--VerificationMode", "structured", "--OidcVerificationConfig.Profile", "kubernetes",
                                         "--OidcVerificationConfig.KubernetesConfig.Namespace", args.namespace,
                                         "--OidcVerificationConfig.KubernetesConfig.ServiceAccountName", args.service_account,
                                         *prefix, "--yes"))
        verify_credential(cloud, app, cred, provider, args)
        if scope_id:
            pam_feature(cloud, app, scope_id)
            doc["pam_scope_id"] = scope_id
            save()
        return {"configuration": "verified", "state": args.state, "resources": res,
                "pam_feature_scope": PAM_SCOPE if doc.get("pam_scope_id") else None}


def choose_roles(args, cloud):
    cloud.identity()
    if not args.cloud_account_id:
        rows = cloud.eiam_list("ListCloudAccounts", "CloudAccounts")
        return {"cloud_accounts": [{k: row.get(k) for k in ("CloudAccountId", "CloudAccountName", "Status")}
                                   for row in rows]}
    rows = cloud.eiam_list("ListCloudAccountRoles", "CloudAccountRoles", "--CloudAccountId", args.cloud_account_id)
    return {"roles": [{k: row.get(k) for k in ("CloudAccountRoleId", "CloudAccountRoleName", "CloudAccountRoleExternalId",
                                              "Status", "CloudAccountRoleHealth")}
                      for row in rows if (row.get("Status") == "enabled" and
                                          row.get("CloudAccountRoleUsageType") != "system" and
                                          ROLE_ARN.fullmatch(row.get("CloudAccountRoleExternalId", "")))]}


def grant(args, cloud):
    require(args.confirmed, "Confirm the exact PAM target role and application before grant")
    account = cloud.identity()["AccountId"]
    with inventory(args, cloud, account) as (doc, save):
        require(not doc.get("pending"), "Reconcile the recorded unknown write result before grant")
        require(doc.get("pam_scope_id") and "credential" in doc["resources"],
                "Configure a federated M2M Client with the PAM feature grant first")
        res = doc["resources"]
        app = res["application"]["id"]
        identity = ("--CloudAccountId", args.cloud_account_id, "--CloudAccountRoleId", args.cloud_role_id)
        role = cloud.eiam("GetCloudAccountRole", *identity)["CloudAccountRole"]
        arn = role.get("CloudAccountRoleExternalId", "")
        require(role.get("CloudAccountRoleId") == args.cloud_role_id and role.get("Status") == "enabled"
                and ROLE_ARN.fullmatch(arn), "Select an enabled Alibaba Cloud RAM role from PAM")
        require(role.get("CloudAccountRoleUsageType") != "system",
                "The PAM system role cannot be granted to an application. Select a user role.")
        expected_arn = getattr(args, "expected_role_arn", None)
        require(expected_arn is None or arn == expected_arn,
                "The selected PAM role does not match the confirmed role ARN")
        target = {"id": args.cloud_role_id, "arn": arn, "account_id": args.cloud_account_id}
        require(doc.get("target_role", target) == target, "This state already records a different target role")
        doc["target_role"] = target
        save()
        rule = record(doc, save, "rule", args.rule_name, "AuthorizationRuleId", "CreateAuthorizationRule",
                      lambda: cloud.eiam("CreateAuthorizationRule", "--ProjectId", "iprj_system_default",
                                         "--AuthorizationRuleName", args.rule_name, "--AuthorizationResourceScope", "custom",
                                         "--ClientToken", "ack-rule-" + cloud.session, "--yes"))
        rule_args = ("--AuthorizationRuleId", rule)
        current = cloud.eiam("GetAuthorizationRule", *rule_args)["AuthorizationRule"]
        require(current.get("AuthorizationResourceScope") == "custom" and current.get("Status") == "enabled",
                "Authorization rule is disabled or outside the expected scope")
        asset = record(doc, save, "asset", args.cloud_role_id, "AuthorizationResourceId", "CreateAuthorizationResource",
                       lambda: cloud.eiam("CreateAuthorizationResource", *rule_args, "--AuthorizationResourceEntityType",
                                          "cloud_account_role", "--AuthorizationResourceEntityId", args.cloud_role_id,
                                          "--ClientToken", "ack-resource-" + cloud.session, "--yes"))
        if not doc.get("role_grant_readback"):
            cloud.eiam("AddApplicationToAuthorizationRule", *rule_args, "--ApplicationId", app, "--ValidityType",
                       "permanent", "--ClientToken", "ack-attachment-" + cloud.session, "--yes")
        rows = cloud.eiam_list("ListAuthorizationResources", "AuthorizationResources", *rule_args)
        rules = cloud.eiam_list("ListAuthorizationRulesForApplication", "AuthorizationRules", "--ApplicationId", app)
        require([(x["AuthorizationResourceId"], x["AuthorizationResourceEntityId"]) for x in rows] ==
                [(asset, args.cloud_role_id)] and any(x["AuthorizationRuleId"] == rule for x in rules) and
                cloud.eiam("GetAuthorizationRule", *rule_args)["AuthorizationRule"].get("Status") == "enabled",
                "PAM rule and role attachment readback mismatch")
        doc["role_grant_readback"] = True
        save()
        return {"role_grant": "verified", "role": target, "rule": rule, "asset": asset, "application": app}


def verify(args, cloud):
    env = preflight(args, cloud, show_candidates=False)
    with inventory(args, cloud, env["caller"]["AccountId"]) as (doc, _save):
        res = doc["resources"]
        require("credential" in res, "Configure the federated M2M Client before verifying")
        config = dict(env["ack"], client_id=res["application"]["id"],
                      credential_name=res["credential"]["name"], token_endpoint=env["eiam"]["token_endpoint"],
                      scope=args.scope or PAM_SCOPE)
        if not args.scope:
            require(doc.get("pam_scope_id"), "Supply an authorized business scope or configure the PAM feature grant")
        if args.sts:
            require(config["scope"] == PAM_SCOPE and doc.get("role_grant_readback"),
                    "Verify STS only after the PAM scope and target role grant have been read back")
            config.update(role_arn=doc["target_role"]["arn"], instance_id=args.instance_id, region=args.eiam_region,
                          developer_endpoint="https://eiam-developerapi." + args.eiam_region + ".aliyuncs.com")
        if getattr(args, "workbench_result", None):
            return {"execution": "workbench", "status": "pending",
                    "workbench_command": workbench_command(args, config)}
        result = pod_probe(args, env["container"], config)
        require(result.get("m2m", {}).get("status") == "verified" and
                (not args.sts or result.get("sts", {}).get("status") == "verified"),
                "Pod did not return the required token-verification evidence")
        return result


def cleanup(args, cloud):
    require(args.confirmed, "Review the exact owned IDs in the state file and confirm cleanup first")
    account = cloud.identity()["AccountId"]
    with inventory(args, cloud, account) as (doc, save):
        require(not doc.get("pending"), "Reconcile the recorded unknown write result before cleanup")
        res = doc["resources"]
        app = res.get("application", {}).get("id")
        removed = {}

        def forget(key):
            removed[key] = res.pop(key)["id"]
            save()

        def retire(key, kind, flag, name_field, parent=(), check=None, extras=()):
            item = res.get(key)
            if not item or not item["owned"]:
                return
            params = (*parent, flag, item["id"])
            current = cloud.eiam("Get" + kind, *params, absent=kind).get(kind)
            if current:
                require(current.get(name_field) == item["name"], kind + " name no longer matches the state")
                if check:
                    check(item["id"])
                if current.get("Status") != "disabled":
                    cloud.eiam("Disable" + kind, *params, *extras, "--yes")
                cloud.eiam("Delete" + kind, *params, "--yes")
            require(not cloud.eiam("Get" + kind, *params, absent=kind), kind + " is still present")
            forget(key)

        def unlink_rule(rule):
            rule_id = ("--AuthorizationRuleId", rule)
            links = cloud.eiam_list("ListApplicationsForAuthorizationRule", "Applications", *rule_id)
            assets = cloud.eiam_list("ListAuthorizationResources", "AuthorizationResources", *rule_id)
            asset = res.get("asset", {}).get("id")
            require({x["ApplicationId"] for x in links} <= {app} and
                    {x["AuthorizationResourceId"] for x in assets} <= {asset},
                    "Rule has unowned attachments. Review it before cleanup.")
            if links:
                cloud.eiam("RemoveApplicationFromAuthorizationRule", *rule_id, "--ApplicationId", app, "--yes")
            if assets:
                cloud.eiam("DeleteAuthorizationResource", *rule_id, "--AuthorizationResourceId", asset, "--yes")
            if asset:
                remaining = cloud.eiam_list("ListAuthorizationResources", "AuthorizationResources", *rule_id)
                require(not remaining, "Authorization resources were not removed")
                forget("asset")

        retire("rule", "AuthorizationRule", "--AuthorizationRuleId", "AuthorizationRuleName",
               check=unlink_rule, extras=("--ClientToken", "ack-disable-" + cloud.session))
        if "asset" in res:
            require("rule" not in res, "Review the rule before removing its recorded asset")
            forget("asset")
        retire("credential", "ApplicationFederatedCredential", "--ApplicationFederatedCredentialId",
               "ApplicationFederatedCredentialName", parent=("--ApplicationId", app))

        def no_provider_dependents(id):
            links = cloud.eiam_list("ListApplicationFederatedCredentialsForProvider", "ApplicationFederatedCredentials",
                                   "--FederatedCredentialProviderId", id)
            require(not links, "Trust source has an existing dependent credential")

        retire("provider", "FederatedCredentialProvider", "--FederatedCredentialProviderId",
               "FederatedCredentialProviderName", check=no_provider_dependents)

        def no_application_dependents(id):
            for action, field in (("ListApplicationFederatedCredentials", "ApplicationFederatedCredentials"),
                                  ("ListAuthorizationRulesForApplication", "AuthorizationRules")):
                require(not cloud.eiam_list(action, field, "--ApplicationId", id),
                        "Application has an existing dependent resource: " + field)

        retire("application", "Application", "--ApplicationId", "ApplicationName", check=no_application_dependents)
        if not any(item["owned"] for item in res.values()):
            doc["closed"] = True
            save()
        return {"removed": removed, "preserved": res, "state": args.state}


def scoped_parser(sub, name, handler, *, state=False, pod=False):
    parser = sub.add_parser(name)
    parser.add_argument("--ack-region", type=REGION, required=True)
    parser.add_argument("--cluster-id", type=CLUSTER_ID, required=True)
    parser.add_argument("--eiam-region", type=REGION, required=True)
    parser.add_argument("--instance-id", type=INSTANCE_ID, required=True)
    parser.add_argument("--namespace", type=KUBE_NAME, required=True)
    parser.add_argument("--service-account", type=KUBE_NAME, required=True)
    if pod:
        execution = parser.add_mutually_exclusive_group(required=True)
        execution.add_argument("--context", type=configured_name)
        execution.add_argument("--workbench-result", type=local_file_path,
                               help="JSON file from the user-run Workbench preflight")
        if name == "preflight":
            execution.add_argument("--workbench", action="store_true", help="generate a Workbench preflight command")
        parser.add_argument("--pod", type=KUBE_NAME, required=True)
        parser.add_argument("--container", type=KUBE_NAME)
        parser.add_argument("--token-source", choices=("webhook", "projected"), default="webhook",
                            help="use ACK webhook injection or an explicit ServiceAccount token projection")
    if state:
        parser.add_argument("--state", type=local_file_path, required=True)
    parser.set_defaults(handler=handler)
    return parser


def scope_value(value):
    audience, separator, permission = value.partition("|")
    if (not separator or not audience or not permission or len(value) > 512 or value.count("|") != 1 or
            not re.fullmatch(r"[A-Za-z0-9_.@:/+-]+\|[A-Za-z0-9_.@:/+-]+", value)):
        raise argparse.ArgumentTypeError("use an authorized single ResourceServerIdentifier|ScopeValue")
    return value


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--cli-profile", type=configured_name)
    root.add_argument("--session-id", type=checked(r"[a-z0-9]{8,32}"),
                      default=os.environ.get("ACK_SKILL_SESSION_ID") or uuid.uuid4().hex)
    root.set_defaults(ack_region=None, eiam_region=None)
    sub = root.add_subparsers(dest="command", required=True)
    target = sub.add_parser("discover")
    target.add_argument("--ack-region", type=REGION)
    target.set_defaults(handler=discover)
    target = sub.add_parser("workloads")
    target.add_argument("--context", type=configured_name, required=True)
    target.add_argument("--namespace", type=KUBE_NAME)
    target.set_defaults(handler=workloads)
    scoped_parser(sub, "preflight", preflight, pod=True)

    target = scoped_parser(sub, "configure", configure, state=True, pod=True)
    choice = target.add_mutually_exclusive_group(required=True)
    choice.add_argument("--provider-name", type=NAME)
    choice.add_argument("--provider-id", type=checked(r"fcp_[a-z0-9]{6,64}"))
    choice = target.add_mutually_exclusive_group(required=True)
    choice.add_argument("--app-name", type=application_name)
    choice.add_argument("--app-id", type=checked(r"app_[a-z0-9]{6,64}"))
    target.add_argument("--credential-name", type=NAME, required=True)
    target.add_argument("--pod-prefix", type=NAME)
    target.add_argument("--pam-feature", action="store_true")
    target.add_argument("--confirmed", action="store_true")

    target = sub.add_parser("roles")
    target.add_argument("--eiam-region", type=REGION, required=True)
    target.add_argument("--instance-id", type=INSTANCE_ID, required=True)
    target.add_argument("--cloud-account-id", type=checked(r"ca_[a-z0-9]{6,64}"))
    target.set_defaults(handler=choose_roles)

    target = scoped_parser(sub, "grant", grant, state=True)
    target.add_argument("--cloud-account-id", type=checked(r"ca_[a-z0-9]{6,64}"), required=True)
    target.add_argument("--cloud-role-id", type=checked(r"carole_[a-z0-9]{6,64}"), required=True)
    target.add_argument("--expected-role-arn", type=checked(ROLE_ARN.pattern))
    target.add_argument("--rule-name", type=NAME, required=True)
    target.add_argument("--confirmed", action="store_true")

    target = scoped_parser(sub, "verify", verify, state=True, pod=True)
    target.add_argument("--scope", type=scope_value)
    target.add_argument("--sts", action="store_true")

    target = scoped_parser(sub, "cleanup", cleanup, state=True)
    target.add_argument("--confirmed", action="store_true")
    return root


def main():
    args = parser().parse_args()
    try:
        result = args.handler(args, Cloud(args))
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except Failure as exc:
        print(str(exc), file=sys.stderr)
    except (OSError, TypeError, ValueError, KeyError) as exc:
        print("Unexpected local input or API response: " + type(exc).__name__, file=sys.stderr)
    if getattr(args, "state", None) and Path(args.state).expanduser().is_file():
        print("Review the state for recorded or pending resources: " + args.state, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
