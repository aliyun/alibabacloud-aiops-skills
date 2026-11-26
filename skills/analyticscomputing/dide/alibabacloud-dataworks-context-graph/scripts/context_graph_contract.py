"""Request, response, and safe-output contracts for read-only OpenAPI calls."""

import json
import re
from urllib.parse import urlsplit


ACTIONS = frozenset({
    "RetrieveKnowledgePoints", "GetKnowledgePoint", "ListKnowledgePoints",
    "ListKnowledgeBases", "GetKnowledgeBase",
})
POINT_TYPES = frozenset({"GRAPH", "WIKI", "KNOWLEDGE_CONTENT"})
FIELDS = {
    "RetrieveKnowledgePoints": {"Query", "KnowledgeBaseIds", "MaxResults", "FocusObjects"},
    "GetKnowledgePoint": {"KnowledgeBaseId", "Type", "Id", "MaxResults", "NextToken"},
    "ListKnowledgePoints": {"KnowledgeBaseId", "Type", "MaxResults", "NextToken"},
    "ListKnowledgeBases": {"MaxResults", "NextToken"},
    "GetKnowledgeBase": {"KnowledgeBaseId"},
}


class SkillError(Exception):
    def __init__(self, code, message, *, request_id=None, retryable=False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.request_id = request_id
        self.retryable = retryable

    def envelope(self, action=None):
        result = {"Success": False, "Error": {
            "Code": self.code, "Message": self.message, "Retryable": self.retryable,
        }}
        if action:
            result["Action"] = action
        if self.request_id:
            result["RequestId"] = self.request_id
        return result


def invalid(message):
    raise SkillError("InvalidParameter", message)


def text(value, field, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        invalid(f"{field} must be a nonempty string of at most {limit} characters.")
    return value


def region_endpoint(region):
    if not isinstance(region, str) or len(region) > 63 or not re.fullmatch(
            r"[a-z][a-z0-9]*(?:-[a-z0-9]+)+", region):
        invalid("Explicitly provide a valid region such as cn-beijing, not an endpoint or URL.")
    return f"dataworks.{region}.aliyuncs.com"


def normalize_endpoint(region, value=None):
    """Normalize endpoint syntax only; historical route metadata is not network authorization."""
    default = region_endpoint(region)
    if value is None:
        return default
    message = "DATAWORKS_ENDPOINT must be a valid host with optional port or an HTTPS root URL, without user information, paths, queries, or fragments."
    try:
        if (not isinstance(value, str) or not value or len(value) > 2048 or not value.isascii()
                or any(ord(char) <= 32 or ord(char) == 127 for char in value)
                or any(char in value for char in ("?", "#", "\\"))):
            raise ValueError
        parsed = urlsplit(value if "://" in value else "//" + value)
        host, port = parsed.hostname, parsed.port
        if (parsed.scheme not in ("", "https") or not host or len(host) > 253
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment
                or parsed.netloc.endswith(":") or (port is not None and not 1 <= port <= 65535)):
            raise ValueError
        if any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
               for label in host.split(".")):
            raise ValueError
        return host + (f":{port}" if port is not None else "")
    except ValueError:
        # Do not echo invalid targets, which may accidentally contain credentials or signed URLs.
        raise SkillError("InvalidEndpoint", message) from None


def _forbidden_endpoint_host(host):
    # IPv6 already fails DNS syntax. Legacy IPv4 parsers can treat a bare 0x component as zero.
    return host == "localhost" or host.endswith(".localhost") or re.fullmatch(
        r"(?:0x[0-9a-f]*|[0-9]+)(?:\.(?:0x[0-9a-f]*|[0-9]+))*", host) is not None


def _allowed_endpoint(value):
    """Validate one exact DNS authority and return its effective HTTPS host/port."""
    if not isinstance(value, str) or any(char in value for char in "/?#\\@"):
        raise ValueError
    try:
        endpoint = normalize_endpoint("cn-beijing", value)
    except SkillError:
        raise ValueError from None
    host, separator, port = endpoint.partition(":")
    if _forbidden_endpoint_host(host):
        raise ValueError
    return host + ":" + (port if separator else "443")


def _normalize_allowed_hosts(allowed_hosts):
    try:
        if not isinstance(allowed_hosts, (tuple, list, set, frozenset)):
            raise ValueError
        return frozenset(_allowed_endpoint(value) for value in allowed_hosts)
    except (ValueError, TypeError):
        # Configuration can contain accidental secrets; never echo entries or parser errors.
        raise SkillError("InvalidEndpointAllowlist", "DATAWORKS_ENDPOINT_ALLOWLIST must contain comma-separated exact DNS hosts with optional ports; URLs, wildcards, IP addresses, and localhost are not allowed.") from None


def endpoint_allowlist(environ):
    """Read authorization only from the supplied trusted host environment, without global fallback."""
    if "DATAWORKS_ENDPOINT_ALLOWLIST" not in environ:
        return ()
    value = environ["DATAWORKS_ENDPOINT_ALLOWLIST"]
    entries = [entry.strip() for entry in value.split(",")] if isinstance(value, str) else [None]
    return tuple(sorted(_normalize_allowed_hosts(entries)))


def resolve_endpoint(region, value=None, *, allowed_hosts=()):
    """Authorize the initial network destination independently of syntax normalization."""
    endpoint = normalize_endpoint(region, value)
    allowed = _normalize_allowed_hosts(allowed_hosts)
    host, separator, port = endpoint.partition(":")
    authority = host + ":" + (port if separator else "443")
    if _forbidden_endpoint_host(host) or not (host.endswith(".aliyuncs.com") or authority in allowed):
        raise SkillError("InvalidEndpoint", "DATAWORKS_ENDPOINT must use a DNS subdomain of aliyuncs.com or an exact host and port authorized by the trusted DATAWORKS_ENDPOINT_ALLOWLIST; IP addresses and localhost are always rejected.")
    return endpoint


def integer(value, limit):
    if type(value) is not int or not 1 <= value <= limit:
        invalid(f"MaxResults must be an integer from 1 to {limit}.")
    return value


def parse_json(value):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                invalid("The JSON object contains duplicate fields.")
            result[key] = item
        return result

    def constant(_):
        invalid("JSON does not accept nonfinite numbers.")

    try:
        return json.loads(value, object_pairs_hook=pairs, parse_constant=constant)
    except (TypeError, ValueError, RecursionError):
        invalid("The parameter must be valid JSON.")


def reference(item, *, graph_only=False):
    if not isinstance(item, dict) or set(item) != {"KnowledgeBaseId", "Type", "Id"}:
        invalid("A focus reference must contain exactly KnowledgeBaseId, Type, and Id.")
    text(item["KnowledgeBaseId"], "KnowledgeBaseId", 128)
    text(item["Id"], "Id", 512)
    if not isinstance(item["Type"], str) or item["Type"] not in (POINT_TYPES if not graph_only else {"GRAPH"}):
        invalid("Invalid point Type; focus objects support GRAPH only.")
    return item


def validate_request(action, parameters):
    if not isinstance(action, str) or action not in ACTIONS:
        invalid("Only the five registered read-only Actions are allowed.")
    if not isinstance(parameters, dict) or set(parameters) - FIELDS[action]:
        invalid("The request contains unregistered fields; caller identity, URLs, and arbitrary parameters cannot pass through.")
    params = dict(parameters)
    if any(value is None for value in params.values()):
        invalid("Omit unused optional parameters rather than passing null.")
    if action == "RetrieveKnowledgePoints":
        query = text(params.get("Query"), "Query", 100000).strip()
        if len(query) > 256:
            invalid("Query must contain 1-256 Unicode code points after trimming surrounding whitespace.")
        params["Query"] = query
        params["MaxResults"] = integer(params.get("MaxResults", 10), 50)
        if "KnowledgeBaseIds" in params:
            ids = params["KnowledgeBaseIds"]
            if not isinstance(ids, list) or not 1 <= len(ids) <= 50:
                invalid("KnowledgeBaseIds must contain 1-50 distinct knowledge base IDs.")
            for item in ids:
                text(item, "KnowledgeBaseIds", 128)
            if len(set(ids)) != len(ids):
                invalid("KnowledgeBaseIds cannot contain duplicate IDs.")
        if "FocusObjects" in params:
            items = params["FocusObjects"]
            if not isinstance(items, list) or not 1 <= len(items) <= 2:
                invalid("FocusObjects must contain 1-2 distinct GRAPH references.")
            identities = []
            for item in items:
                reference(item, graph_only=True)
                identities.append(tuple(item[key] for key in ("KnowledgeBaseId", "Type", "Id")))
                if "KnowledgeBaseIds" in params and item["KnowledgeBaseId"] not in params["KnowledgeBaseIds"]:
                    invalid("Every focus base must be within KnowledgeBaseIds.")
            if len(set(identities)) != len(identities):
                invalid("FocusObjects cannot contain duplicate references.")
        return params
    if action != "ListKnowledgeBases":
        text(params.get("KnowledgeBaseId"), "KnowledgeBaseId", 128)
    if "Type" in params and (not isinstance(params["Type"], str) or params["Type"] not in POINT_TYPES):
        invalid("Type must be GRAPH, WIKI, or KNOWLEDGE_CONTENT.")
    if action == "GetKnowledgePoint":
        text(params.get("Id"), "Id", 512)
        if "Type" not in params:
            invalid("GetKnowledgePoint requires Type.")
        if params["Type"] != "GRAPH" and ({"MaxResults", "NextToken"} & set(params)):
            invalid("Only GRAPH details accept MaxResults and NextToken.")
    paged = action.startswith("List") or (action == "GetKnowledgePoint" and params["Type"] == "GRAPH")
    if paged:
        params["MaxResults"] = integer(params.get("MaxResults", 20), 100)
        if "NextToken" in params:
            text(params["NextToken"], "NextToken", 16384)
    return params


def validate_response(action, params, payload):
    request_id = payload.get("RequestId") if isinstance(payload, dict) else None
    valid_request_id = isinstance(request_id, str) and bool(request_id.strip())

    def check(condition):
        if not condition:
            raise SkillError("InvalidResponse", "The returned business structure or object identity does not match the request contract.",
                             request_id=request_id if valid_request_id else None)

    check(isinstance(payload, dict) and payload.get("Success") is True)
    check(valid_request_id)
    data = payload.get("Data")
    check(isinstance(data, dict))

    def identity(item, *, graph=False, scope=None):
        check(isinstance(item, dict))
        check(isinstance(item.get("KnowledgeBaseId"), str) and bool(item["KnowledgeBaseId"]))
        check(isinstance(item.get("Id"), str) and bool(item["Id"]))
        check(isinstance(item.get("Type"), str) and item["Type"] in ({"GRAPH"} if graph else POINT_TYPES))
        if scope:
            check(item["KnowledgeBaseId"] in scope)

    def warnings():
        check(isinstance(data.get("Warnings"), list))
        for item in data["Warnings"]:
            check(isinstance(item, dict) and isinstance(item.get("Code"), str))

    if "NextToken" in data:
        check(data["NextToken"] is None or isinstance(data["NextToken"], str))
    if action == "RetrieveKnowledgePoints":
        for key in ("Results", "Paths", "Ambiguities"):
            check(isinstance(data.get(key), list))
        warnings()
        check(len(data["Results"]) <= params["MaxResults"])
        scope = params.get("KnowledgeBaseIds")
        for row in data["Results"]:
            identity(row, scope=scope)
        for path in data["Paths"]:
            check(isinstance(path, dict) and isinstance(path.get("Nodes"), list)
                  and isinstance(path.get("Edges"), list))
            for node in path["Nodes"]:
                identity(node, graph=True, scope=scope)
            ids = {node["Id"] for node in path["Nodes"]}
            for edge in path["Edges"]:
                check(isinstance(edge, dict) and isinstance(edge.get("FromId"), str)
                      and isinstance(edge.get("ToId"), str) and edge["FromId"] in ids and edge["ToId"] in ids)
        for group in data["Ambiguities"]:
            check(isinstance(group, dict) and isinstance(group.get("Mention"), str)
                  and isinstance(group.get("Candidates"), list))
            for node in group["Candidates"]:
                identity(node, graph=True, scope=scope)
    elif action == "GetKnowledgePoint":
        check(all(data.get(key) == params[key] for key in ("KnowledgeBaseId", "Type", "Id")))
        warnings()
        branch = {"GRAPH": "Graph", "WIKI": "Wiki", "KNOWLEDGE_CONTENT": "KnowledgeContent"}[params["Type"]]
        check(isinstance(data.get(branch), dict))
        check(not ({"Graph", "Wiki", "KnowledgeContent"} - {branch}) & set(data))
        item = data[branch]
        if branch == "Graph":
            check(item.get("KnowledgeBaseId") == params["KnowledgeBaseId"] and item.get("RootNodeId") == params["Id"])
            check(isinstance(item.get("Nodes"), list) and isinstance(item.get("Edges"), list))
            for node in item["Nodes"]:
                check(isinstance(node, dict) and node.get("KnowledgeBaseId") == params["KnowledgeBaseId"]
                      and isinstance(node.get("NodeId"), str) and bool(node["NodeId"]))
            ids = {node["NodeId"] for node in item["Nodes"]}
            check(params["Id"] in ids)
            for edge in item["Edges"]:
                check(isinstance(edge, dict) and edge.get("KnowledgeBaseId") == params["KnowledgeBaseId"]
                      and isinstance(edge.get("FromNodeId"), str) and isinstance(edge.get("ToNodeId"), str)
                      and edge.get("FromNodeId") in ids and edge.get("ToNodeId") in ids
                      and params["Id"] in (edge.get("FromNodeId"), edge.get("ToNodeId")))
        else:
            check(isinstance(item.get("Title"), str) and isinstance(item.get("Content"), str))
    elif action == "ListKnowledgePoints":
        check(isinstance(data.get("KnowledgePoints"), list))
        for item in data["KnowledgePoints"]:
            identity(item, scope={params["KnowledgeBaseId"]})
            if "Type" in params:
                check(item["Type"] == params["Type"])
    elif action == "ListKnowledgeBases":
        check(isinstance(data.get("KnowledgeBases"), list))
        for item in data["KnowledgeBases"]:
            check(isinstance(item, dict) and isinstance(item.get("KnowledgeBaseId"), str))
    else:
        check(data.get("KnowledgeBaseId") == params["KnowledgeBaseId"])
    return payload


SIGNED_URL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
SENSITIVE_KEYS = {"accesskeyid", "accesskeysecret", "securitytoken", "authorization", "password", "cookie"}


def safe_output(value, secrets=(), *, include_source_urls=False, in_sources=False, allow_source_url=False):
    """Remove credentials and retain Sources download links only when explicitly requested by the user."""
    if isinstance(value, dict):
        output = {}
        for key, item in value.items():
            normalized = key.lower().replace("_", "").replace("-", "")
            if normalized in SENSITIVE_KEYS or (normalized == "downloadurl" and not (include_source_urls and in_sources)):
                output[key] = "[REDACTED]"
            else:
                output[key] = safe_output(item, secrets, include_source_urls=include_source_urls,
                                          in_sources=in_sources or key == "Sources",
                                          allow_source_url=include_source_urls and in_sources and normalized == "downloadurl")
        return output
    if isinstance(value, list):
        return [safe_output(item, secrets, include_source_urls=include_source_urls, in_sources=in_sources) for item in value]
    if isinstance(value, str):
        for secret in sorted((item for item in secrets if item), key=len, reverse=True):
            value = value.replace(secret, "[REDACTED]")
        if not allow_source_url:
            def clean_url(match):
                url = match.group()
                return "[REDACTED_SIGNED_URL]" if any(
                    token in url.lower() for token in ("signature=", "security-token=", "accesskeyid=", "x-amz-credential=")) else url
            value = SIGNED_URL.sub(clean_url, value)
    return value
