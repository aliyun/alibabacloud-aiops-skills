#!/usr/bin/env python3
"""Safe Alibaba Cloud CLI wrapper for IDaaS SAML identity-provider onboarding."""

from __future__ import annotations

import argparse
import base64
import hashlib
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen


SAML_IDP_TYPE = "urn:alibaba:idaas:idp:standard:saml2"
MINIMUM_CLI_VERSION = (3, 3, 3)
MAX_METADATA_BYTES = 5 * 1024 * 1024
SAML_METADATA_NS = "urn:oasis:names:tc:SAML:2.0:metadata"
MANIFEST_PATH = Path(__file__).resolve().parent.parent / "references" / "manifest.json"
TERMINAL_JOB_STATES = {"success", "failed", "failure", "error", "completed"}
BINDING_URNS = {
    "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect": "HTTP-REDIRECT",
    "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST": "HTTP-POST",
}
SENSITIVE_KEYS = {
    "accesskeysecret", "appsecret", "clientsecret", "contactsecret", "corpsecret",
    "privatekey", "privatekeypem", "refreshtoken", "verificationtoken",
}


class SkillError(RuntimeError):
    pass


def skill_version() -> str:
    try:
        payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SkillError("Cannot read the skill manifest or its version") from exc
    version = payload.get("version")
    if not isinstance(version, str) or not version.strip():
        raise SkillError("The skill manifest does not contain a valid version")
    return version.strip()


def session_id() -> str:
    for name in ("ALIBABA_CLOUD_AGENT_SESSION_ID", "CLOUDCLI_SESSION_ID", "CODEX_SESSION_ID"):
        value = os.environ.get(name)
        if value:
            return value
    value = os.environ.get("ALIBABACLOUD_SKILL_SESSION_ID")
    if value:
        return value
    value = str(uuid.uuid4())
    os.environ["ALIBABACLOUD_SKILL_SESSION_ID"] = value
    return value


def parse_cli_version(value: str) -> tuple[int, int, int]:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        raise SkillError("Unable to determine the Alibaba Cloud CLI version")
    return tuple(int(part) for part in match.groups())


def require_cli(executable: str) -> str:
    result = subprocess.run([executable, "version"], capture_output=True, text=True, check=False)
    output = (result.stdout or result.stderr).strip()
    if result.returncode or parse_cli_version(output) < MINIMUM_CLI_VERSION:
        raise SkillError(
            "Alibaba Cloud CLI 3.3.3 or later is required. Install or upgrade it from "
            "https://www.alibabacloud.com/help/en/alibaba-cloud-cli/latest/installation-guide"
        )
    return output


def emit(value: Any) -> None:
    print(json.dumps(redact(value), ensure_ascii=False, indent=2))


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***REDACTED***"
            if key.lower().replace("_", "").replace("-", "") in SENSITIVE_KEYS
            else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def cli(
    args: argparse.Namespace,
    operation: str,
    parameters: list[str],
    *,
    force: bool = False,
    method: str | None = None,
) -> Any:
    executable = shutil.which("aliyun")
    if not executable:
        raise SkillError(
            "Alibaba Cloud CLI 3.3.3 or later is required. Install it from "
            "https://www.alibabacloud.com/help/en/alibaba-cloud-cli/latest/installation-guide"
        )
    require_cli(executable)
    version = skill_version()
    invocation_session = session_id()
    command = [
        executable, "eiam", operation,
        "--profile", args.profile,
        "--region", args.region,
        *parameters,
    ]
    if method:
        command.extend(["--method", method])
    if force:
        # EIAM expects flat SamlConfig.* keys, while CLI metadata exposes only
        # the top-level object. --force forwards those service-defined keys.
        command.append("--force")
    env = dict(os.environ)
    env["ALIBABA_CLOUD_USER_AGENT"] = (
        f"AlibabaCloud-Agent-Skills/alibabacloud-idaas-create-saml-idp/{invocation_session} "
        f"skill-version/{version}"
    )
    env["ALIBABA_CLOUD_CLI_AI_MODE"] = "1"
    result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
    if result.returncode:
        raise SkillError((result.stderr or result.stdout or "Alibaba Cloud CLI call failed").strip())
    output = result.stdout.strip()
    if not output:
        return {}
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise SkillError("Alibaba Cloud CLI returned non-JSON output") from exc


def validate_url(value: str, label: str) -> list[str]:
    parsed = urlparse(value)
    errors: list[str] = []
    if parsed.scheme != "https":
        errors.append(f"{label} must use HTTPS")
    if not parsed.hostname:
        errors.append(f"{label} must contain a hostname")
    if parsed.username or parsed.password:
        errors.append(f"{label} must not contain embedded credentials")
    if parsed.fragment:
        errors.append(f"{label} must not contain a URL fragment")
    host = (parsed.hostname or "").lower()
    if host == "localhost" or host.endswith(".localhost"):
        errors.append(f"{label} points to localhost, which the IDaaS backend cannot reach")
    try:
        address = ipaddress.ip_address(host)
        if address.is_loopback or address.is_private or address.is_link_local:
            errors.append(f"{label} points to a non-public IP address")
    except ValueError:
        pass
    return errors


def certificate_pem(value: str) -> str:
    if "PRIVATE KEY" in value.upper():
        raise SkillError("Refusing private key material; provide only an IdP public certificate")
    body = "".join(
        line.strip() for line in value.strip().splitlines()
        if "BEGIN CERTIFICATE" not in line and "END CERTIFICATE" not in line
    )
    if not body:
        raise SkillError("SAML metadata contains an empty X.509 certificate")
    try:
        der = base64.b64decode(body, validate=True)
    except Exception as exc:
        raise SkillError("SAML metadata contains an invalid base64 X.509 certificate") from exc
    if not der or der[0] != 0x30:
        raise SkillError("SAML metadata certificate is not a DER X.509 sequence")
    wrapped = "\n".join(body[index:index + 64] for index in range(0, len(body), 64))
    return f"-----BEGIN CERTIFICATE-----\n{wrapped}\n-----END CERTIFICATE-----"


def certificate_summary(pem: str) -> dict[str, str]:
    body = "".join(line for line in pem.splitlines() if not line.startswith("-----"))
    der = base64.b64decode(body)
    digest = hashlib.sha256(der).hexdigest().upper()
    return {"sha256": ":".join(digest[i:i + 2] for i in range(0, len(digest), 2))}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_metadata_xml(content: bytes, source: str) -> dict[str, Any]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise SkillError(f"Invalid SAML metadata XML from {source}: {exc}") from exc

    descriptors = [node for node in root.iter() if local_name(node.tag) == "EntityDescriptor"]
    selected: ET.Element | None = None
    idp_descriptor: ET.Element | None = None
    for descriptor in descriptors:
        candidate = next(
            (child for child in descriptor if local_name(child.tag) == "IDPSSODescriptor"),
            None,
        )
        if candidate is not None:
            selected, idp_descriptor = descriptor, candidate
            break
    if selected is None or idp_descriptor is None:
        raise SkillError("Metadata does not contain a SAML IDPSSODescriptor")

    entity_id = (selected.get("entityID") or "").strip()
    services: list[dict[str, str]] = []
    for node in idp_descriptor:
        if local_name(node.tag) != "SingleSignOnService":
            continue
        binding = BINDING_URNS.get(node.get("Binding", ""))
        location = (node.get("Location") or "").strip()
        if binding and location and {"binding": binding, "location": location} not in services:
            services.append({"binding": binding, "location": location})

    certificates: list[str] = []
    for key_descriptor in idp_descriptor:
        if local_name(key_descriptor.tag) != "KeyDescriptor":
            continue
        use = (key_descriptor.get("use") or "").lower()
        if use not in ("", "signing"):
            continue
        for node in key_descriptor.iter():
            if local_name(node.tag) == "X509Certificate" and node.text:
                pem = certificate_pem(node.text)
                if pem not in certificates:
                    certificates.append(pem)

    return {
        "entityId": entity_id,
        "ssoServices": services,
        "certificates": certificates,
        "wantAuthnRequestsSigned": parse_optional_bool(idp_descriptor.get("WantAuthnRequestsSigned")),
    }


def parse_optional_bool(value: str | bool | None) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in ("true", "1"):
        return True
    if normalized in ("false", "0"):
        return False
    return None


def fetch_metadata(url: str) -> bytes:
    request = Request(url, headers={"Accept": "application/samlmetadata+xml, application/xml, text/xml", "User-Agent": "idaas-create-saml-idp/1.0"})
    try:
        with urlopen(request, timeout=10) as response:
            return response.read(5 * 1024 * 1024 + 1)
    except Exception as exc:
        raise SkillError(f"Local SAML metadata fetch failed: {exc}") from exc


def parse_sp_metadata(content: bytes, expected_entity_id: str | None = None,
                      expected_acs_url: str | None = None) -> str:
    """Accept an SP descriptor, never an HTTP-200 challenge or an IdP document."""
    if len(content) > MAX_METADATA_BYTES:
        raise SkillError("SAML SP metadata exceeds the 5 MiB download limit")
    try:
        raw_xml = content.decode("utf-8-sig")
        root = ET.fromstring(raw_xml)
    except UnicodeDecodeError as exc:
        raise SkillError("IDaaS SP metadata is not UTF-8 encoded") from exc
    except ET.ParseError as exc:
        raise SkillError("IDaaS SP metadata is not valid XML (possibly an HTML/WAF response)") from exc
    entity_tag = f"{{{SAML_METADATA_NS}}}EntityDescriptor"
    if root.tag == entity_tag:
        entities = [root]
    elif root.tag == f"{{{SAML_METADATA_NS}}}EntitiesDescriptor":
        entities = list(root.iter(entity_tag))
    else:
        raise SkillError("IDaaS SP metadata is not a SAML EntityDescriptor (possibly an HTML/WAF response)")
    sp_entities = [entity for entity in entities
                   if entity.get("entityID") and
                   entity.find(f"{{{SAML_METADATA_NS}}}SPSSODescriptor") is not None]
    if expected_entity_id:
        sp_entities = [entity for entity in sp_entities if entity.get("entityID") == expected_entity_id]
    if len(sp_entities) != 1:
        raise SkillError("IDaaS SP metadata must contain one SP descriptor matching the requested SP Entity ID")
    sp = sp_entities[0].find(f"{{{SAML_METADATA_NS}}}SPSSODescriptor")
    if not any(endpoint.get("Location") for endpoint in sp.findall(f"{{{SAML_METADATA_NS}}}AssertionConsumerService")):
        raise SkillError("IDaaS SP metadata has no AssertionConsumerService endpoint")
    if expected_acs_url and expected_acs_url not in {
        endpoint.get("Location") for endpoint in sp.findall(f"{{{SAML_METADATA_NS}}}AssertionConsumerService")
    }:
        raise SkillError("IDaaS SP metadata does not match the requested ACS URL")
    return raw_xml


def fetch_sp_metadata(url: str) -> bytes:
    try:
        content = fetch_metadata(url)
        parse_sp_metadata(content)
        return content
    except SkillError as urllib_error:
        # macOS curl uses the system trust store, which may contain an IDaaS
        # certificate chain that Python's bundled CA store does not. The URL
        # comes from authenticated GetIdentityProvider output. HTTP 200 can
        # also carry an HTML challenge, so validate both download paths.
        # Use argv form without a shell and do not follow redirects.
        executable = shutil.which("curl")
        if not executable:
            raise urllib_error
        result = subprocess.run([
            executable,
            "--fail",
            "--silent",
            "--show-error",
            "--max-time", "10",
            "--max-filesize", str(5 * 1024 * 1024),
            "--proto", "=https",
            url,
        ], capture_output=True, check=False)
        if result.returncode:
            detail = result.stderr.decode("utf-8", errors="replace").strip()
            raise SkillError(f"IDaaS SP metadata fetch failed: {detail or urllib_error}") from urllib_error
        try:
            parse_sp_metadata(result.stdout)
        except SkillError as exc:
            raise SkillError(
                f"IDaaS SP metadata unavailable after both download paths: {urllib_error}; {exc}. "
                "Preserve the created IdP ID and Metadata URL; do not retry creation or synthesize XML."
            ) from exc
        return result.stdout


def normalize_certificates(value: Any) -> list[str]:
    found: list[str] = []

    def visit(node: Any) -> None:
        if isinstance(node, str):
            try:
                pem = certificate_pem(node)
            except SkillError:
                return
            if pem not in found:
                found.append(pem)
        elif isinstance(node, list):
            for item in node:
                visit(item)
        elif isinstance(node, dict):
            for key, item in node.items():
                if key.lower() in ("content", "certificate", "certificates", "cert"):
                    visit(item)

    visit(value)
    return found


def metadata_from_response(response: dict[str, Any]) -> dict[str, Any]:
    root = response.get("IdentityProviderMetadata", response.get("data", response))
    saml = root.get("SamlMetadataConfiguration", root.get("samlMetadataConfiguration", root))
    entity_id = saml.get("IdpEntityId", saml.get("IdPEntityId", saml.get("idpEntityId", "")))
    sso_url = saml.get("IdpSsoUrl", saml.get("IdPSsoUrl", saml.get("idpSsoUrl", "")))
    certificates = normalize_certificates(saml.get("Certificates", saml.get("certificates", [])))
    services = [{"binding": "HTTP-REDIRECT", "location": str(sso_url)}] if sso_url else []
    return {
        "entityId": str(entity_id or ""),
        "ssoServices": services,
        "certificates": certificates,
        "wantAuthnRequestsSigned": None,
    }


def validate_source_args(args: argparse.Namespace) -> str:
    sources = [bool(args.metadata_url), bool(args.metadata_file), bool(args.sso_url or args.entity_id or args.certificate_file)]
    if sum(sources) != 1:
        raise SkillError("Choose exactly one source: --metadata-url, --metadata-file, or complete manual fields")
    if args.metadata_url:
        return "metadata-url"
    if args.metadata_file:
        return "metadata-file"
    if not args.sso_url or not args.certificate_file:
        raise SkillError("Manual mode requires --sso-url and at least one --certificate-file")
    return "manual"


def read_certificate_files(paths: list[str]) -> list[str]:
    certificates: list[str] = []
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        try:
            pem = certificate_pem(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise SkillError(f"Cannot read certificate file {path}: {exc}") from exc
        if pem not in certificates:
            certificates.append(pem)
    return certificates


def certificate_constraint(args: argparse.Namespace, source_type: str) -> set[str]:
    """Retain a supplied pin across CLI calls, including after a failed resolution."""
    expected = getattr(args, "expected_certificate_sha256", None)
    pins = {value.replace(":", "").lower() for value in expected or []}
    if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in pins):
        raise SkillError("Expected certificate SHA-256 must be a 64-digit hex fingerprint")
    guard_file = getattr(args, "input_guard_file", None)
    if not guard_file:
        return pins
    path = Path(guard_file).expanduser()
    lock = path.with_name(path.name + ".lock")
    if not pins and not path.exists() and not lock.exists():
        return set()
    source = (args.metadata_url if source_type == "metadata-url" else
              str(Path(args.metadata_file).expanduser().resolve()) if source_type == "metadata-file" else
              sorted(str(Path(p).expanduser().resolve()) for p in args.certificate_file or []))
    key = hashlib.sha256(json.dumps([args.profile, args.region, args.instance_id, source_type, source],
                                   sort_keys=True).encode()).hexdigest()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock.open("x")
    except FileExistsError as exc:
        raise SkillError("Metadata constraint file is locked; stop rather than bypassing it") from exc
    except OSError as exc:
        raise SkillError("Cannot access metadata constraints; stop before cloud write") from exc
    try:
        handle.close()
        try:
            state = json.loads(path.read_text()) if path.exists() else {"version": 1, "sources": {}}
            if state.get("version") != 1 or not isinstance(state.get("sources"), dict):
                raise ValueError("invalid constraint schema")
            saved = state["sources"].get(key, [])
            if (not isinstance(saved, list) or (key in state["sources"] and not saved) or
                    any(not isinstance(p, str) or not re.fullmatch(r"[0-9a-f]{64}", p) for p in saved)):
                raise ValueError("invalid stored fingerprint")
        except (OSError, ValueError, AttributeError) as exc:
            raise SkillError("Cannot read metadata constraints; preserve the file and stop. This is script-owned state, not an input template; do not hand-write, repair or replace it.") from exc
        if saved and pins and set(saved) != pins:
            raise SkillError("Certificate constraint conflicts with the original pin; do not replace or remove it")
        if pins and not saved:
            state["sources"][key] = sorted(pins)
            temporary = path.with_name(path.name + ".tmp")
            try:
                with temporary.open("w", encoding="utf-8") as stream:
                    json.dump(state, stream, indent=2)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, path)
            except OSError as exc:
                raise SkillError("Cannot persist certificate constraint; stop before cloud write") from exc
        return set(saved) or pins
    finally:
        lock.unlink(missing_ok=True)


def resolve_source(args: argparse.Namespace) -> dict[str, Any]:
    source_type = validate_source_args(args)
    expected = certificate_constraint(args, source_type)
    warnings: list[str] = []
    idaas_error: str | None = None

    if source_type == "metadata-url":
        url_errors = validate_url(args.metadata_url, "Metadata URL")
        if url_errors and not args.allow_insecure_test:
            raise SkillError("; ".join(url_errors))
        warnings.extend(url_errors)
        try:
            parameters = ["--InstanceId", args.instance_id, "--SamlMetadataUrl", args.metadata_url]
            if args.network_access_endpoint_id:
                parameters.extend(["--NetworkAccessEndpointId", args.network_access_endpoint_id])
            metadata = metadata_from_response(cli(args, "ExecIdentityProviderMetadataUrlResolution", parameters))
            resolved_by = "idaas"
        except SkillError as exc:
            idaas_error = str(exc)
            content = fetch_metadata(args.metadata_url)
            if len(content) > 5 * 1024 * 1024:
                raise SkillError("SAML metadata exceeds the 5 MiB local parsing limit")
            metadata = parse_metadata_xml(content, args.metadata_url)
            resolved_by = "local-fallback"
            warnings.append("The official IDaaS metadata resolver failed; local parsing is diagnostic only")
    elif source_type == "metadata-file":
        path = Path(args.metadata_file).expanduser()
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise SkillError(f"Cannot read metadata file {path}: {exc}") from exc
        if len(content) > 5 * 1024 * 1024:
            raise SkillError("SAML metadata exceeds the 5 MiB parsing limit")
        metadata = parse_metadata_xml(content, str(path))
        resolved_by = "local-file"
    else:
        metadata = {
            "entityId": args.entity_id or "",
            "ssoServices": [{"binding": args.binding or "HTTP-REDIRECT", "location": args.sso_url}],
            "certificates": read_certificate_files(args.certificate_file or []),
            "wantAuthnRequestsSigned": None,
        }
        resolved_by = "manual"

    if not metadata["ssoServices"]:
        warnings.append("Metadata has no supported HTTP-Redirect or HTTP-POST SingleSignOnService")
    for service in metadata["ssoServices"]:
        warnings.extend(validate_url(service["location"], "SSO URL"))
    if not metadata["certificates"]:
        warnings.append("Metadata has no signing certificate")
    if len(metadata["certificates"]) > 2:
        warnings.append("Metadata has more than two signing certificates; EIAM accepts at most two")
    if not metadata["entityId"]:
        warnings.append("Metadata has no IdP Entity ID")
    if expected:
        actual = {certificate_summary(cert)["sha256"].replace(":", "").lower()
                  for cert in metadata["certificates"]}
        if actual != expected:
            raise SkillError(
                "Certificate SHA-256 mismatch; stop before cloud write. "
                f"Expected {sorted(expected)}, parsed {sorted(actual)}. "
                "Restore the original input; do not replace its certificate or copy an expected digest into the result."
            )
    return {
        "sourceType": source_type,
        "resolvedBy": resolved_by,
        "idaasResolutionError": idaas_error,
        "metadata": metadata,
        "warnings": list(dict.fromkeys(warnings)),
    }


def public_resolution(resolved: dict[str, Any]) -> dict[str, Any]:
    metadata = resolved["metadata"]
    return {
        "sourceType": resolved["sourceType"],
        "resolvedBy": resolved["resolvedBy"],
        "idaasResolutionError": resolved["idaasResolutionError"],
        "metadata": {
            "entityId": metadata["entityId"],
            "ssoServices": metadata["ssoServices"],
            "wantAuthnRequestsSigned": metadata["wantAuthnRequestsSigned"],
            "certificates": [certificate_summary(cert) for cert in metadata["certificates"]],
        },
        "warnings": resolved["warnings"],
    }


def resolve(args: argparse.Namespace) -> dict[str, Any]:
    result = public_resolution(resolve_source(args))
    result["instanceId"] = args.instance_id
    metadata = result["metadata"]
    result["entityId"] = metadata["entityId"]
    result["ssoUrl"] = choose_service(metadata, getattr(args, "binding", None))["location"]
    fingerprints = [c["sha256"].replace(":", "").lower() for c in metadata["certificates"]]
    result["certificateSha256s"] = fingerprints
    if len(fingerprints) == 1:
        result["certificateSha256"] = fingerprints[0]
    output = getattr(args, "output_file", None)
    if output:
        path = Path(output).expanduser()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(result, stream, ensure_ascii=False, indent=2)
            try:
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        except OSError as exc:
            raise SkillError("Cannot save computed metadata resolution; stop and fix the output path") from exc
    return result


def choose_service(metadata: dict[str, Any], binding: str | None) -> dict[str, str]:
    services = metadata["ssoServices"]
    preferred = binding or "HTTP-REDIRECT"
    selected = next((item for item in services if item["binding"] == preferred), None)
    if selected:
        return selected
    if binding:
        raise SkillError(f"Metadata does not advertise the selected binding {binding}")
    if services:
        return services[0]
    raise SkillError("No supported SSO service is available")


def effective_config(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    resolved = resolve_source(args)
    metadata = resolved["metadata"]
    service = choose_service(metadata, args.binding)
    certificates = metadata["certificates"]
    if not certificates:
        raise SkillError("At least one IdP signing certificate is required")
    if len(certificates) > 2:
        raise SkillError("EIAM accepts at most two certificates; provide manual fields with the active/rollover certificates")
    require_signed = args.require_request_signed
    if require_signed is None:
        require_signed = bool(metadata["wantAuthnRequestsSigned"])
    if not 0 <= args.max_clock_skew <= 360:
        raise SkillError("--max-clock-skew must be between 0 and 360 seconds")
    config = {
        "entityId": metadata["entityId"],
        "ssoUrl": service["location"],
        "binding": service["binding"],
        "requireRequestSigned": require_signed,
        "maxClockSkew": args.max_clock_skew,
        "certificates": certificates,
    }
    return resolved, config


def plan(args: argparse.Namespace) -> dict[str, Any]:
    resolved, config = effective_config(args)
    return {
        "operation": "create-saml-identity-provider",
        "instanceId": args.instance_id,
        "name": args.name,
        "identityProviderType": SAML_IDP_TYPE,
        "sourceType": resolved["sourceType"],
        "networkAccessEndpointId": args.network_access_endpoint_id,
        "saml": {
            "idpEntityId": config["entityId"],
            "idpSsoUrl": config["ssoUrl"],
            "bindingMethod": config["binding"],
            "requireRequestSigned": config["requireRequestSigned"],
            "wantResponseSigned": args.want_response_signed,
            "wantAssertionsSigned": args.want_assertions_signed,
            "maxClockSkew": config["maxClockSkew"],
            "certificates": [certificate_summary(cert) for cert in config["certificates"]],
        },
        "externalIdpRequirements": external_idp_requirements(args),
        "authenticationStatusAfterCreate": args.authn_status,
        "warnings": resolved["warnings"],
        "ready": not resolved["warnings"],
    }


def require_confirmation(actual: str | None, expected: str) -> None:
    if actual != expected:
        raise SkillError(f"Write operation requires --confirm {expected}")


def create(args: argparse.Namespace) -> dict[str, Any]:
    require_confirmation(args.confirm, "CREATE")
    resolved, config = effective_config(args)
    if resolved["warnings"] and not args.accept_warnings:
        raise SkillError("Preflight has warnings; resolve them or explicitly pass --accept-warnings")
    parameters = [
        "--InstanceId", args.instance_id,
        "--IdentityProviderName", args.name,
        "--IdentityProviderType", SAML_IDP_TYPE,
        "--AuthnConfig.AuthnStatus", args.authn_status,
        "--SamlConfig.IdPEntityId", config["entityId"],
        "--SamlConfig.IdPSsoUrl", config["ssoUrl"],
        "--SamlConfig.BindingMethod", config["binding"],
        "--SamlConfig.RequireRequestSigned", str(config["requireRequestSigned"]).lower(),
        "--SamlConfig.WantResponseSigned", str(args.want_response_signed).lower(),
        "--SamlConfig.WantAssertionsSigned", str(args.want_assertions_signed).lower(),
        "--SamlConfig.MaxClockSkew", str(config["maxClockSkew"]),
        "--ClientToken", args.client_token or str(uuid.uuid4()),
        "--yes",
    ]
    if args.network_access_endpoint_id:
        parameters.extend(["--NetworkAccessEndpointId", args.network_access_endpoint_id])
    for index, certificate in enumerate(config["certificates"], 1):
        parameters.extend([f"--SamlConfig.Certificates.{index}.Content", certificate])
    state_file = getattr(args, "state_file", None)
    if state_file:
        return create_once(args, parameters, Path(state_file).expanduser())
    return perform_create(args, parameters)


def create_once(args: argparse.Namespace, parameters: list[str], path: Path) -> dict[str, Any]:
    """Persist one creation attempt across agent restarts; uncertain writes never auto-retry."""
    path = path.resolve()
    token_index = parameters.index("--ClientToken") + 1
    target = parameters.copy()
    target[token_index] = "<persisted-client-token>"
    fingerprint = hashlib.sha256(json.dumps(
        [args.profile, args.region, target], ensure_ascii=False,
    ).encode()).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise SkillError(f"Creation state is locked: {lock}; inspect the existing attempt, do not create again") from exc
    os.close(descriptor)
    try:
        if path.exists():
            try:
                state = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise SkillError("Cannot read creation state; stop rather than starting another creation") from exc
            if not isinstance(state, dict) or state.get("configurationSha256") != fingerprint:
                raise SkillError("Creation state belongs to a different configuration; do not reuse or overwrite it")
            if state.get("status") == "created" and isinstance(state.get("result"), dict) and state["result"].get("identityProviderId"):
                return {**state["result"], "reusedCreationResult": True,
                        "creationStateFile": str(path),
                        "next": "Reuse this IdP ID; run show and the requested SP handoff. No new create call was made."}
            raise SkillError(
                f"An earlier creation attempt has an uncertain outcome; inspect {path} and list/show "
                "the target before recovery. Do not generate a new Entity ID, ClientToken, or creation state."
            )
        preflight = creation_preflight(args, parameters)
        state = {"status": "pending", "configurationSha256": fingerprint,
                 "instanceId": args.instance_id, "clientToken": parameters[token_index]}
        with path.open("x", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            result = perform_create(args, parameters, preflight)
        except SkillError as exc:
            raise SkillError(f"{exc}\nPreserve creation state at {path}; reconcile this attempt before another POST.") from exc
        result["creationStateFile"] = str(path)
        if not result.get("identityProviderId"):
            # Retain a successful response's request/receipt even when it lacks
            # a usable ID. Never turn it into a fresh POST on the next round.
            state["lastResult"] = result
            path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            raise SkillError("Create returned no IdP ID; preserve the pending state and inspect the target")
        state.update(status="created", result=result)
        temporary = path.with_name(path.name + ".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        return result
    finally:
        lock.unlink(missing_ok=True)


def creation_preflight(args: argparse.Namespace, parameters: list[str]) -> dict[str, Any]:
    """Fresh complete inventory before POST; no implicit quota or recovery write."""
    entity = parameters[parameters.index("--SamlConfig.IdPEntityId") + 1]
    limit = getattr(args, "idp_quota", None)
    if limit is not None and limit < 1:
        raise SkillError("--idp-quota must be positive")
    providers: list[dict[str, Any]] = []
    requests = []
    total = None
    seen_ids: set[str] = set()
    for page in range(1, 101):
        reply = cli(args, "ListIdentityProviders", ["--InstanceId", args.instance_id,
                    "--PageNumber", str(page), "--PageSize", "100"])
        rows = reply.get("IdentityProviders")
        count = reply.get("TotalCount")
        if (not isinstance(rows, list) or not isinstance(count, int) or isinstance(count, bool) or
                count < 0 or any(not isinstance(row, dict) for row in rows)):
            raise SkillError("Creation preflight received an invalid inventory; no create was attempted")
        if total is not None and total != count:
            raise SkillError("Inventory changed while paging; reconcile before creating")
        for row in rows:
            provider_id = row.get("IdentityProviderId")
            if not isinstance(provider_id, str) or not provider_id or provider_id in seen_ids:
                raise SkillError("Creation preflight inventory has missing or repeated IDs; no create was attempted")
            seen_ids.add(provider_id)
        total = count
        providers.extend(rows)
        requests.append(reply.get("RequestId"))
        if len(providers) >= total:
            break
        if not rows:
            raise SkillError("Creation preflight inventory is incomplete; no create was attempted")
    if total is None or len(providers) != total:
        raise SkillError("Creation preflight inventory is incomplete; no create was attempted")
    if any(row.get("IdentityProviderExternalId") == entity for row in providers):
        raise SkillError("An existing IdP has this Entity ID; do not create, reuse or delete it")
    if limit is not None and total >= limit:
        raise SkillError("Identity-provider quota is full; no create was attempted")
    return {"instanceId": args.instance_id, "entityId": entity,
            "source": "ListIdentityProviders", "listSucceeded": True,
            "checkedBeforeCreate": True, "existingCount": total,
            "quotaLimit": limit, "entityIdConflict": False, "requestIds": requests}


def write_receipt(args: argparse.Namespace, parameters: list[str], operation: str,
                  response: dict[str, Any], idp_id: str | None) -> dict[str, Any]:
    certificates = [parameters[i + 1] for i, flag in enumerate(parameters)
                    if re.fullmatch(r"--SamlConfig\.Certificates\.\d+\.Content", flag)]
    return {"operation": operation, "instanceId": args.instance_id,
            "identityProviderId": idp_id,
            "requestId": response.get("RequestId", response.get("requestId")),
            "submittedCertificateSha256s": [certificate_summary(cert)["sha256"].replace(":", "").lower()
                                              for cert in certificates]}


def perform_create(args: argparse.Namespace, parameters: list[str],
                   preflight: dict[str, Any] | None = None) -> dict[str, Any]:
    if preflight is None:
        preflight = creation_preflight(args, parameters)
    receipt = write_receipt(args, parameters, "CreateIdentityProvider", {}, None)
    response = cli(args, "CreateIdentityProvider", parameters, method="POST", force=True)
    idp_id = find_key(response, {"identityproviderid"})
    if idp_id is None and isinstance(response.get("data"), str):
        idp_id = response["data"]
    if not isinstance(idp_id, str) or not re.fullmatch(r"idp_[a-z0-9]+", idp_id):
        idp_id = None
    receipt.update(identityProviderId=idp_id,
                   requestId=response.get("RequestId", response.get("requestId")))
    return {
        "created": True,
        "identityProviderId": idp_id,
        "requestId": response.get("RequestId", response.get("requestId")),
        "creationPreflight": preflight,
        "writeReceipt": receipt,
        "authenticationStatus": args.authn_status,
        "externalIdpRequirements": external_idp_requirements(args),
        "next": "Ask the user to choose SP output mode 1 (separate fields) or 2 (raw Metadata XML), then run sp-metadata with the selected --output-mode. This handoff is mandatory. Then run check when supported.",
    }


def external_idp_requirements(args: argparse.Namespace) -> list[str]:
    requirements = ["The SSO URL must be reachable by the user's browser"]
    if args.want_response_signed:
        requirements.append("Sign the SAML Response root element with a configured IdP certificate")
    if args.want_assertions_signed:
        requirements.append("Sign the SAML Assertion with a configured IdP certificate")
    requirements.append("Send a NameID/attributes that match the configured IDaaS account mapping")
    return requirements


def instances(args: argparse.Namespace) -> Any:
    response = cli(args, "ListEiamInstances", [])
    values = response.get("Instances", [])
    if isinstance(values, dict):
        values = values.get("Instance", [])
    if getattr(args, "running_only", False):
        values = [item for item in values if str(item.get("InstanceStatus", "")).lower() == "running"]
    return [{
        "selection": index,
        "instanceId": item.get("InstanceId"),
        "description": item.get("Description"),
        "status": item.get("InstanceStatus"),
        "version": item.get("InstanceVersion"),
        "ssoDomain": item.get("SSODomain"),
    } for index, item in enumerate(values, 1)]


def list_idps(args: argparse.Namespace) -> Any:
    return cli(args, "ListIdentityProviders", [
        "--InstanceId", args.instance_id,
        "--PageNumber", "1", "--PageSize", str(args.page_size),
    ])


def show(args: argparse.Namespace) -> Any:
    return cli(args, "GetIdentityProvider", ["--InstanceId", args.instance_id, "--IdentityProviderId", args.idp_id])


def find_key(value: Any, names: set[str]) -> Any:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in names and item is not None:
                return item
        for item in value.values():
            found = find_key(item, names)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_key(item, names)
            if found is not None:
                return found
    return None


def handoff_state(args: argparse.Namespace, changes: dict[str, Any] | None = None) -> dict[str, Any]:
    """Keep staged handoff prerequisites separate for each authenticated target."""
    filename = getattr(args, "handoff_state_file", None)
    if not filename:
        return {}
    path = Path(filename).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".lock")
    key = json.dumps([args.profile, args.region, args.instance_id, args.idp_id])
    try:
        with lock.open("x"):
            pass
    except OSError as exc:
        raise SkillError("Cannot lock SP handoff journal; preserve it and stop") from exc
    try:
        try:
            state = json.loads(path.read_text()) if path.exists() else {"version": 1, "targets": {}}
            if state.get("version") != 1 or not isinstance(state.get("targets"), dict):
                raise ValueError("Invalid handoff journal")
            entry = state["targets"].get(key, {})
            if not isinstance(entry, dict):
                raise ValueError("Invalid target entry")
            if changes is not None:
                entry.update(changes)
                state["targets"][key] = entry
                temporary = path.with_name(path.name + ".tmp")
                temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
                os.replace(temporary, path)
            return entry
        except (OSError, ValueError, AttributeError) as exc:
            raise SkillError("Cannot read/write SP handoff journal; preserve it and stop") from exc
    finally:
        lock.unlink(missing_ok=True)


def check_result(args: argparse.Namespace, result: dict[str, Any], outcome: str) -> dict[str, Any]:
    result.setdefault("serviceError", None)
    result.setdefault("readbackVerified", False)
    result.update(instanceId=args.instance_id, identityProviderId=args.idp_id, outcome=outcome)
    handoff_state(args, {"check": result})
    return result


def sp_metadata(args: argparse.Namespace) -> dict[str, Any]:
    if getattr(args, "output_file", None) and getattr(args, "output_mode", "fields") != "raw":
        raise SkillError("--output-file requires --output-mode raw")
    if getattr(args, "raw_input_file", None) and getattr(args, "output_mode", "fields") != "raw":
        raise SkillError("--raw-input-file requires --output-mode raw")
    detail = show(args)
    metadata_url = find_key(detail, {"samlmetaendpoint", "samlmetadataendpoint"})
    entity_id = find_key(detail, {"samlentityid"})
    acs_url = find_key(detail, {"samlacsendpoint", "samlacsurl"})
    want_response_signed = find_key(detail, {"wantresponsesigned"})
    want_assertions_signed = find_key(detail, {"wantassertionssigned"})
    if not any((metadata_url, entity_id, acs_url)):
        raise SkillError("GetIdentityProvider did not return SAML SP endpoint metadata")

    output_mode = getattr(args, "output_mode", "fields")
    staged = str(find_key(detail, {"authnstatus"})).lower() == "disabled"
    entry = handoff_state(args)
    if staged:
        # A failed raw request cannot be cleared by switching to fields mode.
        handoff_state(args, {"staged": True,
                             "rawRequired": output_mode == "raw" or entry.get("rawRequired", False),
                             "spComplete": False})
    common = {
        "identityProviderId": args.idp_id,
        "outputMode": output_mode,
        "spMetadataUrl": metadata_url,
    }
    if output_mode == "raw":
        if not metadata_url:
            raise SkillError("GetIdentityProvider did not return an SP Metadata URL")
        # The URL comes from authenticated GetIdentityProvider output, not user input.
        url_errors = validate_url(str(metadata_url), "SP Metadata URL")
        if url_errors:
            raise SkillError("; ".join(url_errors))
        supplied_file = getattr(args, "raw_input_file", None)
        if supplied_file:
            if not entity_id or not acs_url:
                raise SkillError("Cannot validate supplied SP XML without the target's SP Entity ID and ACS URL")
            try:
                with Path(supplied_file).expanduser().open("rb") as stream:
                    content = stream.read(MAX_METADATA_BYTES + 1)
            except OSError as exc:
                raise SkillError(f"Cannot read supplied SP XML: {exc}") from exc
        else:
            try:
                content = fetch_sp_metadata(str(metadata_url))
            except SkillError as exc:
                raise SkillError(f"SP XML delivery incomplete: {exc}. Ask ONLY for original SP XML downloaded from {metadata_url} for instance {args.instance_id}, IdP {args.idp_id}; preserve disabled status and do not request ENABLE or IdP signing certificates in this question.") from exc
        raw_xml = parse_sp_metadata(content, str(entity_id) if entity_id else None,
                                    str(acs_url) if acs_url else None)
        saved: dict[str, Any] = {}
        output_file = getattr(args, "output_file", None)
        if output_file or staged or entry.get("staged"):
            path = Path(output_file or f"outputs/sp-metadata-{args.idp_id}.xml").expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(raw_xml, encoding="utf-8")
            digest = hashlib.sha256(raw_xml.encode("utf-8")).hexdigest()
            saved = {"rawMetadataFile": str(Path(output_file).expanduser()) if output_file else str(path),
                     "rawMetadataSha256": digest}
            if staged or entry.get("staged"):
                handoff_state(args, {"spComplete": True, "rawFile": str(path), "rawSha256": digest})
        return {
            **common,
            **saved,
            "rawMetadataXml": raw_xml,
            "rawMetadataSource": "user-supplied-file" if supplied_file else "download",
            "next": "Import this raw SP metadata XML at the external IdP, authorize users, then run a real login test.",
        }

    if staged and not entry.get("rawRequired") and all((metadata_url, entity_id, acs_url)):
        handoff_state(args, {"spComplete": True})
    return {
        **common,
        "spEntityId": entity_id,
        "spAcsUrl": acs_url,
        "signatureRequirements": {
            "response": want_response_signed,
            "assertion": want_assertions_signed,
        },
        "next": "Configure these SP fields at the external IdP, authorize users, then run a real login test.",
    }


def sp_handoff_markdown(result: dict[str, Any]) -> str:
    """Render the complete handoff instead of an action-only summary."""
    if result.get("outputMode") == "raw":
        return ("## IDaaS SP Metadata (raw XML)\n\n"
                f"- Metadata source URL: {result['spMetadataUrl']}\n"
                f"- XML source: {result['rawMetadataSource']}\n\n"
                f"```xml\n{result['rawMetadataXml']}\n```\n")
    fields = [("SP Metadata URL", "spMetadataUrl"), ("SP Entity ID", "spEntityId"), ("ACS URL", "spAcsUrl")]
    missing = [label for label, key in fields if not result.get(key)]
    if missing:
        raise SkillError("SP field handoff is incomplete: " + ", ".join(missing))
    return "## IDaaS SP information (separate fields)\n\n" + "\n".join(
        f"- {label}: {result[key]}" for label, key in fields
    ) + "\n"


def enable(args: argparse.Namespace) -> Any:
    require_confirmation(args.confirm, "ENABLE")
    entry = handoff_state(args)
    final_handoff = None
    if entry.get("staged"):
        checked = entry.get("check", {})
        if not isinstance(checked, dict):
            raise SkillError("Staged enable blocked: invalid check evidence")
        if not entry.get("spComplete"):
            raise SkillError("Staged enable blocked: SP handoff is incomplete; request the same target's original SP XML separately")
        if (checked.get("instanceId") != args.instance_id or
                checked.get("identityProviderId") != args.idp_id or
                checked.get("outcome") not in {"supported", "unsupported"}) or (
                checked.get("outcome") == "unsupported" and not checked.get("readbackVerified")):
            raise SkillError("Staged enable blocked: record the actual status check and required same-target readback first")
        # Prepare the final handoff before the write. A delivery error must not
        # turn a successful enable into an ambiguous failure to be retried.
        detail = show(args)
        if (find_key(detail, {"identityproviderid"}) not in (None, args.idp_id) or
                find_key(detail, {"instanceid"}) not in (None, args.instance_id)):
            raise SkillError("Staged enable blocked: SP handoff readback target mismatch")
        metadata_url = find_key(detail, {"samlmetaendpoint", "samlmetadataendpoint"})
        if entry.get("rawRequired"):
            try:
                content = Path(entry["rawFile"]).read_bytes()
            except (KeyError, OSError) as exc:
                raise SkillError("Staged enable blocked: validated SP XML file is missing") from exc
            if hashlib.sha256(content).hexdigest() != entry.get("rawSha256"):
                raise SkillError("Staged enable blocked: SP XML file changed")
            entity = find_key(detail, {"samlentityid"})
            acs = find_key(detail, {"samlacsendpoint", "samlacsurl"})
            if not entity or not acs:
                raise SkillError("Staged enable blocked: cannot verify target SP endpoints")
            raw_xml = parse_sp_metadata(content, str(entity), str(acs))
            if not metadata_url:
                raise SkillError("Staged enable blocked: SP Metadata URL is missing")
            final_handoff = {"outputMode": "raw", "identityProviderId": args.idp_id,
                             "spMetadataUrl": metadata_url, "rawMetadataXml": raw_xml,
                             "rawMetadataSource": "previously-validated-file"}
        else:
            final_handoff = {"outputMode": "fields", "identityProviderId": args.idp_id,
                             "spMetadataUrl": metadata_url,
                             "spEntityId": find_key(detail, {"samlentityid"}),
                             "spAcsUrl": find_key(detail, {"samlacsendpoint", "samlacsurl"})}
        final_markdown = sp_handoff_markdown(final_handoff)
    response = cli(args, "EnableIdentityProviderAuthn", [
        "--InstanceId", args.instance_id, "--IdentityProviderId", args.idp_id, "--yes",
    ])
    result = {"enabled": True, "identityProviderId": args.idp_id, "response": response}
    if final_handoff is not None:
        result.update(spHandoff=final_handoff, spHandoffMarkdown=final_markdown,
                      next="Include spHandoffMarkdown in the final answer, including the complete XML in raw mode; do not replace it with a summary or file path.")
    return result


def check(args: argparse.Namespace) -> Any:
    # Invalidate older evidence before a new attempt, including an attempt that fails.
    handoff_state(args, {"check": {"instanceId": args.instance_id,
                                  "identityProviderId": args.idp_id, "outcome": "pending"}})
    if args.skip_check:
        return check_result(args, {
            "supported": None,
            "skipped": True,
            "warning": "Status check was skipped by request; this does not prove the configuration is valid.",
            "next": "Run show/sp-metadata, present the SP handoff fields, and verify configuration in the console.",
        }, "skipped")
    try:
        created = cli(args, "CreateIdentityProviderStatusCheckJob", [
            "--InstanceId", args.instance_id, "--IdentityProviderId", args.idp_id, "--yes",
        ])
    except SkillError as exc:
        if "UnsupportedAction" in str(exc) or "cannot supported this action" in str(exc):
            return unsupported_check_result(str(exc), args)
        raise
    job_id = created.get("IdentityProviderStatusCheckJobId", created.get("data"))
    if not job_id:
        raise SkillError("IDaaS did not return a status-check job ID")
    deadline = time.monotonic() + args.timeout
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        try:
            response = cli(args, "GetIdentityProviderStatusCheckJob", [
                "--InstanceId", args.instance_id,
                "--IdentityProviderId", args.idp_id,
                "--IdentityProviderStatusCheckJobId", str(job_id),
            ])
        except SkillError as exc:
            if "UnsupportedAction" in str(exc) or "cannot supported this action" in str(exc):
                return unsupported_check_result(str(exc), args)
            raise
        latest = response.get("IdentityProviderStatusCheckJob", response.get("data", response))
        status = str(latest.get("Status", latest.get("status", ""))).lower()
        if status in TERMINAL_JOB_STATES:
            return check_result(args, {"jobId": job_id, "job": latest, "supported": True},
                                "supported" if status == "success" else "failed")
        time.sleep(args.interval)
    return check_result(args, {"jobId": job_id, "job": latest, "timedOut": True, "supported": True}, "failed")


def unsupported_check_result(error: str, args: argparse.Namespace) -> dict[str, Any]:
    result = {
        "supported": False,
        "skipped": True,
        "warning": "The current instance does not support the identity-provider status-check API; this does not mean the SAML configuration failed.",
        "serviceError": error,
        "next": "Continue with show/sp-metadata, provide the SP integration details, and verify the configuration in the console.",
    }

    try:
        detail = show(args)
        returned_id = find_key(detail, {"identityproviderid"})
        returned_instance = find_key(detail, {"instanceid"})
        result["readbackVerified"] = (returned_id == args.idp_id and
                                      returned_instance in (None, args.instance_id))
        result["readback"] = detail
    except SkillError as exc:
        result["readbackVerified"] = False
        result["readbackError"] = str(exc)
    return check_result(args, result, "unsupported")


def update(args: argparse.Namespace) -> dict[str, Any]:
    require_confirmation(args.confirm, "UPDATE")
    resolved, config = effective_config(args)
    if resolved["warnings"] and not args.accept_warnings:
        raise SkillError("Preflight has warnings; resolve them or explicitly pass --accept-warnings")
    parameters = [
        "--InstanceId", args.instance_id,
        "--IdentityProviderId", args.idp_id,
        "--SamlConfig.IdPEntityId", config["entityId"],
        "--SamlConfig.IdPSsoUrl", config["ssoUrl"],
        "--SamlConfig.BindingMethod", config["binding"],
        "--SamlConfig.RequireRequestSigned", str(config["requireRequestSigned"]).lower(),
        "--SamlConfig.WantResponseSigned", str(args.want_response_signed).lower(),
        "--SamlConfig.WantAssertionsSigned", str(args.want_assertions_signed).lower(),
        "--SamlConfig.MaxClockSkew", str(config["maxClockSkew"]),
        "--ClientToken", args.client_token or str(uuid.uuid4()),
        "--yes",
    ]
    if args.name:
        parameters.extend(["--IdentityProviderName", args.name])
    if args.network_access_endpoint_id:
        parameters.extend(["--NetworkAccessEndpointId", args.network_access_endpoint_id])
    for index, certificate in enumerate(config["certificates"], 1):
        parameters.extend([f"--SamlConfig.Certificates.{index}.Content", certificate])
    receipt = write_receipt(args, parameters, "UpdateIdentityProvider", {}, args.idp_id)
    response = cli(args, "UpdateIdentityProvider", parameters, method="POST", force=True)
    receipt["requestId"] = response.get("RequestId", response.get("requestId"))
    return {
        "updated": True,
        "identityProviderId": args.idp_id,
        "requestId": response.get("RequestId", response.get("requestId")),
        "writeReceipt": receipt,
        "externalIdpRequirements": external_idp_requirements(args),
        "next": "Run the actual check, then sp-metadata with the user's selected --output-mode and --output-format markdown. Include its complete handoff in the LAST answer: all three SP endpoint values for fields, or complete validated XML for raw. A file path or completion summary is not delivery. A real login remains a separate verification.",
    }


def doctor(args: argparse.Namespace) -> Any:
    executable = shutil.which("aliyun")
    if not executable:
        raise SkillError(
            "Alibaba Cloud CLI 3.3.3 or later is required. Install it from "
            "https://www.alibabacloud.com/help/en/alibaba-cloud-cli/latest/installation-guide"
        )
    version = require_cli(executable)
    manifest_version = skill_version()
    visible = instances(args)
    return {
        "cliPath": executable,
        "cliVersion": version,
        "minimumCliVersion": "3.3.3",
        "skillVersion": manifest_version,
        "profile": args.profile,
        "region": args.region,
        "credentialUsable": True,
        "visibleInstanceCount": len(visible),
    }


def common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", default="default")
    parser.add_argument("--region", default="cn-hangzhou")


def identity_target(parser: argparse.ArgumentParser) -> None:
    common(parser)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--idp-id", required=True)


def source_args(parser: argparse.ArgumentParser) -> None:
    parser.set_defaults(input_guard_file="outputs/metadata-constraints.json")
    parser.add_argument("--metadata-url")
    parser.add_argument("--metadata-file")
    parser.add_argument("--entity-id")
    parser.add_argument("--sso-url")
    parser.add_argument("--certificate-file", action="append")
    parser.add_argument("--expected-certificate-sha256", action="append",
                        help="Verify the exact set of public signing-certificate fingerprints before proceeding")
    parser.add_argument("--network-access-endpoint-id")
    parser.add_argument("--binding", choices=("HTTP-REDIRECT", "HTTP-POST"))
    parser.add_argument("--allow-insecure-test", action="store_true")


def creation_args(parser: argparse.ArgumentParser) -> None:
    common(parser)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--name", required=True)
    source_args(parser)
    parser.add_argument("--require-request-signed", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--want-response-signed", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--want-assertions-signed", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-clock-skew", type=int, default=180)
    parser.add_argument("--authn-status", choices=("enabled", "disabled"), default="enabled")


def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    doctor_parser = commands.add_parser("doctor")
    common(doctor_parser)
    doctor_parser.set_defaults(handler=doctor)

    instances_parser = commands.add_parser("instances")
    common(instances_parser)
    instances_parser.add_argument("--running-only", action="store_true")
    instances_parser.set_defaults(handler=instances)

    list_parser = commands.add_parser("list")
    common(list_parser)
    list_parser.add_argument("--instance-id", required=True)
    list_parser.add_argument("--page-size", type=int, default=20)
    list_parser.set_defaults(handler=list_idps)

    show_parser = commands.add_parser("show")
    identity_target(show_parser)
    show_parser.set_defaults(handler=show)

    metadata_parser = commands.add_parser("sp-metadata")
    identity_target(metadata_parser)
    metadata_parser.add_argument("--output-mode", choices=("fields", "raw"), default="fields")
    metadata_parser.add_argument("--output-file", help="Save validated raw SP XML, never an HTML/error response")
    metadata_parser.add_argument("--raw-input-file", help="User-supplied original SP XML; verify Entity ID and ACS against the target")
    metadata_parser.add_argument("--output-format", choices=("json", "markdown"), default="json")
    metadata_parser.set_defaults(handler=sp_metadata)

    resolve_parser = commands.add_parser("resolve")
    common(resolve_parser)
    resolve_parser.add_argument("--instance-id", required=True)
    source_args(resolve_parser)
    resolve_parser.add_argument("--output-file", default="outputs/metadata-resolution.json",
                                help="Atomically save the actual computed resolution JSON")
    resolve_parser.set_defaults(handler=resolve)

    plan_parser = commands.add_parser("plan")
    creation_args(plan_parser)
    plan_parser.set_defaults(handler=plan)

    create_parser = commands.add_parser("create")
    creation_args(create_parser)
    create_parser.add_argument("--client-token")
    create_parser.add_argument("--state-file", help="Persist one creation attempt and reuse its successful IdP ID")
    create_parser.add_argument("--idp-quota", type=int,
                               help="Optional known per-instance quota; do not infer a universal limit")
    create_parser.add_argument("--accept-warnings", action="store_true")
    create_parser.add_argument("--confirm")
    create_parser.set_defaults(handler=create)

    update_parser = commands.add_parser("update")
    common(update_parser)
    update_parser.add_argument("--instance-id", required=True)
    update_parser.add_argument("--idp-id", required=True)
    update_parser.add_argument("--name")
    source_args(update_parser)
    update_parser.add_argument("--require-request-signed", action=argparse.BooleanOptionalAction, default=None)
    update_parser.add_argument("--want-response-signed", action=argparse.BooleanOptionalAction, default=True)
    update_parser.add_argument("--want-assertions-signed", action=argparse.BooleanOptionalAction, default=True)
    update_parser.add_argument("--max-clock-skew", type=int, default=180)
    update_parser.add_argument("--client-token")
    update_parser.add_argument("--accept-warnings", action="store_true")
    update_parser.add_argument("--confirm")
    update_parser.set_defaults(handler=update)

    check_parser = commands.add_parser("check")
    identity_target(check_parser)
    check_parser.add_argument("--timeout", type=int, default=45)
    check_parser.add_argument("--interval", type=float, default=2.0)
    check_parser.add_argument("--skip-check", action="store_true")
    check_parser.set_defaults(handler=check)

    enable_parser = commands.add_parser("enable")
    identity_target(enable_parser)
    enable_parser.add_argument("--confirm")
    enable_parser.set_defaults(handler=enable)
    for target_parser in (metadata_parser, check_parser, enable_parser):
        target_parser.set_defaults(handoff_state_file="outputs/sp-handoff-state.json")
    return root


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = args.handler(args)
        if getattr(args, "output_format", "json") == "markdown":
            print(sp_handoff_markdown(result))
        else:
            emit(result)
        return 0
    except SkillError as exc:
        emit({"ok": False, "error": str(exc)})
        return 2
    except KeyboardInterrupt:
        emit({"ok": False, "error": "Interrupted"})
        return 130


if __name__ == "__main__":
    sys.exit(main())
