"""Redact labelled credentials without altering original SDK or SSE evidence.

Adapted from the workspace Skill's standalone redaction rules, with masking for
credentials split across SSE text events. Unlabelled and encoded arbitrary secrets
cannot be identified; this is not a general data-loss prevention system.
"""

import json
import re


REDACTED = "***REDACTED***"
_SENSITIVE_NAMES = {
    "ak", "sk", "accessid", "accesskey", "accesskeyid", "accesskeysecret", "secretkey",
    "securitytoken", "ststoken", "token", "accesstoken", "refreshtoken",
    "authtoken", "bearertoken", "idtoken", "apikey", "apisecret",
    "password", "passwd", "pwd", "secret", "clientsecret", "authorization",
    "proxyauthorization", "privatekey", "credential", "credentials",
}
_SENSITIVE_SUFFIXES = (
    "accessid", "accesskey", "accesskeyid", "accesskeysecret", "secretkey",
    "securitytoken", "accesstoken", "refreshtoken", "clientsecret", "apikey",
    "password", "passwd",
)
_ASSIGNMENT = re.compile(
    r"(?<![\w.-])(?P<prefix>(?P<keyquote>['\"]?)(?P<key>[\w.-]+)(?P=keyquote)\s*[:=]\s*)"
    r"(?=(?P<value>'(?:[^'\\]|\\.|'')*'|\"(?:[^\"\\]|\\.|\"\")*\"|[^\s,;&<>\]\}\)]+))",
    re.IGNORECASE,
)
_AUTHORIZATION = re.compile(
    r"((?:proxy-)?authorization\s*[:=]\s*['\"]?)(?:Bearer|Basic)\s+[^\s,'\";<>]+",
    re.IGNORECASE,
)
_URL_USERINFO = re.compile(r"(\b[a-z][a-z0-9+.-]*://)[^\s/@]+:[^\s/@]+@", re.IGNORECASE)
_XML_TOKEN = re.compile(
    r"<!--(?P<comment>.*?)-->|<!\[CDATA\[(?P<cdata>.*?)\]\]>|"
    r"<(?P<closing>/)?(?P<tag>[\w:.-]+)(?=[\s/>])"
    r"(?P<attributes>(?:[^<>\"']|\"[^\"]*\"|'[^']*')*)>",
    re.DOTALL,
)
_XML_ATTRIBUTE = re.compile(
    r"(?:^|\s)(?P<key>[\w:.-]+)\s*=\s*(?P<quote>['\"])(?P<value>.*?)(?P=quote)",
    re.DOTALL,
)
_XML_VALUE_LABEL = re.compile(
    r"<name\s*>(?P<name>[^<]+)</name\s*>\s*(?=<value[\s/>])", re.IGNORECASE,
)


def _is_sensitive_key(name):
    if not isinstance(name, str):
        return False
    normalized = re.sub(r"[^a-z0-9]", "", name.lower())
    if normalized in _SENSITIVE_NAMES or normalized.endswith(_SENSITIVE_SUFFIXES):
        return True
    component = re.split(r"[._-]", name.lower())[-1]
    return component in _SENSITIVE_NAMES


def _has_sensitive_label(items):
    return any(key in ("name", "key") and _is_sensitive_key(item) for key, item in items)


def _redact_json_text(value):
    """Mask labelled value fields in JSON objects embedded in text."""
    changed = False

    def redact_record(pairs):
        nonlocal changed
        record = dict(pairs)
        if _has_sensitive_label(pairs) and any(key == "value" and item is not None for key, item in pairs):
            record["value"] = REDACTED
            changed = True
        return record

    decoder = json.JSONDecoder(object_pairs_hook=redact_record)
    parts = []
    cursor = last_end = 0
    while (start := value.find("{", cursor)) != -1:
        changed = False
        try:
            record, end = decoder.raw_decode(value, start)
        except (ValueError, RecursionError):
            cursor = start + 1
            continue
        cursor = end
        if changed:
            parts.extend((value[last_end:start], json.dumps(record, separators=(",", ":"))))
            last_end = end
    return "".join((*parts, value[last_end:]))


def _xml_secret_spans(value):
    """Find labelled attributes and full contents of matched sensitive elements."""
    labelled_values = {match.end() for match in _XML_VALUE_LABEL.finditer(value)
                       if _is_sensitive_key(match["name"])}
    openings = {}
    spans = []
    for token in _XML_TOKEN.finditer(value):
        if token["tag"] is None:
            group = "comment" if token["comment"] is not None else "cdata"
            offset = token.start(group)
            spans.extend((offset + start, offset + end) for start, end in _xml_secret_spans(token[group]))
            continue
        tag = token["tag"].lower()
        if token["closing"]:
            if openings.get(tag):
                start = openings[tag].pop()
                if start is not None:
                    spans.append((start, token.start()))
            continue

        attributes = list(_XML_ATTRIBUTE.finditer(token["attributes"]))
        sensitive = (
            _is_sensitive_key(tag) or token.start() in labelled_values
            or _has_sensitive_label((attr["key"].lower(), attr["value"]) for attr in attributes)
        )
        if sensitive:
            offset = token.start("attributes")
            for attr in attributes:
                if attr["key"].lower() == "value":
                    spans.append((offset + attr.start("value"), offset + attr.end("value")))
        if not token["attributes"].rstrip().endswith("/"):
            openings.setdefault(tag, []).append(token.end() if sensitive else None)
    return spans


def _redact_xml_text(value):
    parts = []
    end = 0
    for start, stop in sorted(_xml_secret_spans(value)):
        if start >= end:
            parts.extend((value[end:start], REDACTED))
        end = max(end, stop)
    return "".join((*parts, value[end:]))


def _redact_text(value):
    if "{" in value:
        value = _redact_json_text(value)
    if "<" in value:
        value = _redact_xml_text(value)
    value = _URL_USERINFO.sub(lambda match: match[1] + REDACTED + "@", value)
    value = _AUTHORIZATION.sub(lambda match: match[1] + REDACTED, value)
    replacements = []
    previous_end = -1
    for match in _ASSIGNMENT.finditer(value):
        if not _is_sensitive_key(match["key"]) or match.start("value") < previous_end:
            continue
        raw = match["value"]
        quote = raw[0] if raw.startswith(("'", '"')) else ""
        start, end = match.span("value")
        replacements.append((start, end, quote + REDACTED + quote))
        previous_end = end
    for start, end, replacement in reversed(replacements):
        value = value[:start] + replacement + value[end:]
    return value


def redact_sensitive(value):
    """Return a detached redacted copy, including fragmented SSE credentials."""
    if isinstance(value, dict):
        sensitive_value = _has_sensitive_label(value.items())
        result = {
            key: REDACTED if item is not None and (
                _is_sensitive_key(key) or (key == "value" and sensitive_value)
            ) else redact_sensitive(item)
            for key, item in value.items()
        }
        events = value.get("events")
        if isinstance(events, list):
            transcript = "".join(
                event["body"]["text"] for event in events
                if isinstance(event, dict) and isinstance(event.get("body"), dict)
                and isinstance(event["body"].get("text"), str)
            )
            if _redact_text(transcript) != transcript:
                for event in result["events"]:
                    if isinstance(event, dict) and isinstance(event.get("body"), dict) and "text" in event["body"]:
                        event["body"]["text"] = REDACTED
        return result
    if isinstance(value, (list, tuple)):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value
