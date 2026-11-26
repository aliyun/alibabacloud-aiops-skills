"""Validate and render source extracts from an already supplied knowledge-response batch."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import sys

from context_graph_contract import SkillError, parse_json, reference, validate_request, validate_response

SCHEMA = "context-graph-knowledge-answer-job-v1"
REPORT_SCHEMA = "context-graph-knowledge-answer-report-v1"
MAX_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_SELECTIONS = 128
IDENTITY = ("KnowledgeBaseId", "Type", "Id")
BLOCKED_KEYS = frozenset({"sources", "sourceurl", "downloadurl", "accesskeyid", "accesskeysecret",
                          "securitytoken", "authorization", "password", "cookie", "credentials", "token"})


class AnswerError(Exception):
    """Carry only fixed reason codes, never input values or parser exceptions."""

    def __init__(self, code="InvalidJob"):
        self.code = code
        super().__init__("The local knowledge answer job is invalid or exceeds safe limits.")


def require(condition, code="InvalidJob"):
    if not condition:
        raise AnswerError(code)


def fields(value, required, optional=()):
    require(isinstance(value, dict) and set(required) <= set(value)
            and not set(value) - set(required) - set(optional))


def text(value, limit=1024, *, controls=False):
    require(isinstance(value, str) and bool(value.strip()) and len(value) <= limit
            and (controls or not any(ord(char) < 32 for char in value)))
    return value


def encoded(value, *, indent=None):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=None if indent else (",", ":"), indent=indent)


def check_size(value, limit):
    total = 0
    for chunk in json.JSONEncoder(ensure_ascii=False, allow_nan=False).iterencode(value):
        total += len(chunk.encode("utf-8"))
        require(total <= limit, "BudgetExceeded")
    return total


def bounded(value):
    """Bound both file and Python callers, including finite floating score metadata."""
    stack, count = [(value, 0)], 0
    while stack:
        item, depth = stack.pop()
        count += 1
        require(depth <= 32 and count <= 300000, "BudgetExceeded")
        if isinstance(item, dict):
            require(all(isinstance(key, str) for key in item))
            stack.extend((entry, depth + 1) for entry in item.values())
        elif isinstance(item, list):
            stack.extend((entry, depth + 1) for entry in item)
        elif isinstance(item, str):
            require(len(item) <= MAX_BYTES, "BudgetExceeded")
        else:
            require(item is None or type(item) in (bool, int, float))
            require(type(item) is not float or math.isfinite(item), "InvalidNumber")
    check_size(value, MAX_BYTES)


def decode_job(content):
    require(len(content) <= MAX_BYTES, "BudgetExceeded")
    try:
        result = parse_json(content.decode("utf-8"))
        bounded(result)
        return result
    except (UnicodeError, SkillError, ValueError, RecursionError):
        raise AnswerError("InvalidInput") from None


def load_job(path):
    """Never block on a FIFO or follow an input symlink; read at most the input budget."""
    descriptor = None
    try:
        require(all(type(getattr(os, name, None)) is int for name in ("O_NONBLOCK", "O_NOFOLLOW")),
                "UnsupportedPlatform")
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_BYTES, "UnsafeInputFile")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None
            content = stream.read(MAX_BYTES + 1)
        return decode_job(content)
    except OSError:
        raise AnswerError("InvalidInput") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def new_job(directory, *, content=None):
    """Create only inside the caller's trusted existing output parent, using exclusive private files."""
    if content is None:
        empty_job = {"schema": SCHEMA, "question": "", "responses": [], "selections": []}
        content = (encoded(empty_job, indent=2) + "\n").encode("utf-8")
    else:
        job = decode_job(content)
        fields(job, {"schema", "question", "responses", "selections"},
               {"unconfirmed_question_fragments", "applicability_unresolved"})
        require(job["schema"] == SCHEMA)
    parent = child = None
    try:
        require(os.name == "posix" and hasattr(os, "fchmod")
                and all(type(getattr(os, flag, None)) is int for flag in ("O_NOFOLLOW", "O_DIRECTORY"))
                and {os.open, os.mkdir} <= os.supports_dir_fd, "UnsupportedPlatform")
        parent = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        name = "knowledge-answer-" + secrets.token_hex(16)
        os.mkdir(name, 0o700, dir_fd=parent)
        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        os.fchmod(child, 0o700)
        descriptor = os.open("job.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=child)
        with os.fdopen(descriptor, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(content)
        return str(Path(directory).absolute() / name / "job.json")
    except OSError:
        raise AnswerError("UnsafeOutputDirectory") from None
    finally:
        for descriptor in (child, parent):
            if descriptor is not None:
                os.close(descriptor)


def _identity(item):
    require(isinstance(item, dict) and all(key in item for key in IDENTITY), "InvalidResponse")
    result = {key: item[key] for key in IDENTITY}
    for key in IDENTITY:
        text(result[key], 128 if key == "KnowledgeBaseId" else 512)
    reference(result)
    return result


def _response(response):
    require(isinstance(response, dict) and response.get("Success") is True, "InvalidResponse")
    action = response.get("Action")
    require(action in ("RetrieveKnowledgePoints", "GetKnowledgePoint"), "InvalidResponse")
    text(response.get("RequestId"), 1024)
    data = response.get("Data")
    require(isinstance(data, dict), "InvalidResponse")
    if action == "GetKnowledgePoint":
        params = validate_request(action, _identity(data))
    else:
        params = {"MaxResults": 50}
    validate_response(action, params, response)
    if action == "RetrieveKnowledgePoints":
        for hit in data["Results"]:
            _identity(hit)
    return data


def _tokens(pointer):
    text(pointer, 4096)
    require(pointer.startswith("/") and not re.search(r"~(?![01])", pointer), "InvalidPointer")
    return [token.replace("~1", "/").replace("~0", "~") for token in pointer[1:].split("/")]


def _resolve(value, tokens):
    for token in tokens:
        if isinstance(value, list):
            require(re.fullmatch(r"0|[1-9][0-9]*", token) is not None and len(token) <= 8,
                    "InvalidPointer")
            index = int(token)
            require(index < len(value), "InvalidPointer")
            value = value[index]
        else:
            require(isinstance(value, dict) and token in value, "InvalidPointer")
            value = value[token]
    return value


def _normal_key(value):
    return value.lower().replace("_", "").replace("-", "")


def _safe_subtree(value):
    """Credentials and source-download structures are never an extractable business field."""
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            require(not any(_normal_key(key) in BLOCKED_KEYS for key in item), "UnsafeSelection")
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)


def _file_names(*containers):
    names, seen = [], set()
    for container in containers:
        sources = container.get("Sources", [])
        require(isinstance(sources, list), "InvalidResponse")
        for source in sources:
            require(isinstance(source, dict), "InvalidResponse")
            if "FileName" in source:
                value = text(source["FileName"], 4096, controls=True)
                if value not in seen:
                    names.append(value)
                    seen.add(value)
    return names


def _edge_context(graph, tokens):
    """Resolve endpoint labels only within the selected edge's own graph detail."""
    edges = graph["Edges"]
    context = {}
    if len(tokens) > 3:
        edge = _resolve(edges, tokens[3:4])
        context = {key: edge[key] for key in ("FromNodeId", "ToNodeId")}
        edges = [edge]
    ids = {edge[key] for edge in edges for key in ("FromNodeId", "ToNodeId")}
    nodes = {}
    for node in graph["Nodes"]:
        node_id = node["NodeId"]
        if node_id in ids:
            # A repeated id cannot uniquely identify a returned label.
            nodes[node_id] = None if node_id in nodes else node.get("Name")
    context["Nodes"] = [{"NodeId": node_id, "Name": name} for node_id, name in nodes.items()
                        if isinstance(name, str) and name.strip() and len(name) <= 4096]
    if len(edges) == 1 and tokens[4:] in ([], ["Join"], ["Join", "JoinKeys"]):
        join = edges[0].get("Join")
        keys = join.get("JoinKeys") if isinstance(join, dict) else None
        if isinstance(keys, list) and all(isinstance(pair, dict) and
                all(isinstance(pair.get(key), str) and pair[key].strip() for key in ("FromField", "ToField"))
                for pair in keys):
            pairs = {(pair["FromField"], pair["ToField"]) for pair in keys}
            if len(pairs) > 1:
                context["JoinKeyPairCount"] = len(pairs)
    return context


def _selection(responses, selection, full_selected_fields=False):
    fields(selection, {"response_index", "pointer"}, {"quote"})
    index = selection["response_index"]
    require(type(index) is int and 0 <= index < len(responses), "InvalidSelection")
    response, tokens = responses[index], _tokens(selection["pointer"])
    data = response["Data"]
    require(not any(_normal_key(token) in BLOCKED_KEYS for token in tokens), "UnsafeSelection")
    if response["Action"] == "RetrieveKnowledgePoints":
        require(len(tokens) == 4 and tokens[:2] == ["Data", "Results"] and tokens[3] == "Summary",
                "InvalidSelection")
        owner = _resolve(response, tokens[:3])
        identity = _identity(owner)
        value = _resolve(response, tokens)
        require(isinstance(value, str), "InvalidSelection")
        title, containers = owner.get("Title", ""), [owner]
    else:
        identity = _identity(data)
        branch = {"WIKI": "Wiki", "KNOWLEDGE_CONTENT": "KnowledgeContent", "GRAPH": "Graph"}[identity["Type"]]
        require(tokens[:2] == ["Data", branch], "InvalidSelection")
        require(branch == "Graph" or len(tokens) == 3 and tokens[2] in ("Title", "Content"),
                "InvalidSelection")
        value = _resolve(response, tokens)
        owner = data[branch]
        title, containers = owner.get("Title", ""), [data, owner]
        if branch == "Graph":
            roots = [node for node in owner["Nodes"] if node["NodeId"] == owner["RootNodeId"]]
            require(len(roots) == 1, "InvalidResponse")
            title = roots[0].get("Name", "")
    require(isinstance(title, str) and len(title) <= 4096, "InvalidResponse")
    _safe_subtree(value)
    original = value
    if "quote" in selection:
        quote = text(selection["quote"], MAX_BYTES, controls=True)
        require(isinstance(value, str) and quote in value, "UnboundQuote")
        if not full_selected_fields:
            value = quote
    original_bytes = (original if isinstance(original, str) else encoded(original)).encode("utf-8")
    source = {**identity, "Title": title, "FileNames": _file_names(*containers),
            "RequestId": response["RequestId"], "response_index": index, "pointer": selection["pointer"],
            "content_sha256": hashlib.sha256(original_bytes).hexdigest(),
            "excerpt_sha256": hashlib.sha256((value if isinstance(value, str) else encoded(value)).encode("utf-8")).hexdigest()}
    if full_selected_fields and tokens[:3] == ["Data", "Graph", "Edges"]:
        source["GraphEndpoints"] = _edge_context(owner, tokens)
    if full_selected_fields and tokens == ["Data", "Graph", "Nodes"]:
        # This selection contains the complete returned node set. Cite the
        # connecting edges from this same detail, excluding arbitrary properties.
        source["GraphRelationships"] = [
            {key: edge[key] for key in ("EdgeId", "FromNodeId", "ToNodeId", "Type", "RelationType")
             if isinstance(edge.get(key), str)}
            for edge in owner["Edges"]
        ]
    return {"value": value, "source": source}


def evaluate_job(job, expected_response_sha256=None, full_selected_fields=False):
    """Check source bindings only; never certify intent, relevance, business truth or completeness."""
    try:
        bounded(job)
        require(type(full_selected_fields) is bool, "InvalidArguments")
        fields(job, {"schema", "question", "responses", "selections"},
               {"unconfirmed_question_fragments", "applicability_unresolved"})
        require(job["schema"] == SCHEMA)
        text(job["question"], 100000, controls=True)
        require(isinstance(job["responses"], list) and len(job["responses"]) <= 64)
        if expected_response_sha256 is not None:
            require(isinstance(expected_response_sha256, str)
                    and re.fullmatch(r"[0-9a-f]{64}", expected_response_sha256) is not None,
                    "InvalidBatchDigest")
            actual_digest = hashlib.sha256(encoded(job["responses"]).encode("utf-8")).hexdigest()
            require(actual_digest == expected_response_sha256, "BatchDigestMismatch")
        require(isinstance(job["selections"], list) and len(job["selections"]) <= MAX_SELECTIONS)
        warnings = []
        for index, response in enumerate(job["responses"]):
            data = _response(response)
            for warning in data["Warnings"]:
                # Retain the original warning as literal data, including unfamiliar fields/codes.
                _safe_subtree(warning)
                warnings.append({"response_index": index, "RequestId": response["RequestId"], "warning": warning})
        unknowns = job.get("unconfirmed_question_fragments", [])
        require(isinstance(unknowns, list) and len(unknowns) <= 128)
        for fragment in unknowns:
            text(fragment, 100000, controls=True)
            require(fragment in job["question"], "UnboundQuestionFragment")
        require(len(set(unknowns)) == len(unknowns))
        excerpts, used = [], 0
        for selection in job["selections"]:
            excerpt = _selection(job["responses"], selection, full_selected_fields)
            used += check_size(excerpt, MAX_OUTPUT_BYTES - used) + 2
            require(used <= MAX_OUTPUT_BYTES, "BudgetExceeded")
            excerpts.append(excerpt)
        require(excerpts or unknowns, "EmptyAnswer")
        applicability = job.get("applicability_unresolved", False)
        require(type(applicability) is bool)
        identities = {tuple(item["source"][key] for key in IDENTITY) for item in excerpts}
        require(not applicability or len(identities) >= 2, "InvalidApplicability")
        result = {"schema": REPORT_SCHEMA, "status": "validated_extracts", "semantic_review_required": True,
                  "scope": "supplied_response_batch_only", "live_identity_verified": False,
                  "question": job["question"], "excerpts": excerpts, "warnings": warnings,
                  "unconfirmed_question_fragments": list(unknowns), "applicability_unresolved": applicability}
        check_size(result, MAX_OUTPUT_BYTES)
        return result
    except (SkillError, ValueError, UnicodeError, RecursionError, TypeError, KeyError):
        raise AnswerError("InvalidJob") from None


def _fence(value, kind="text"):
    body = value if isinstance(value, str) else encoded(value, indent=2)
    longest = max((len(match.group()) for match in re.finditer(r"`+", body)), default=0)
    fence = "`" * max(3, longest + 1)
    return fence + kind + "\n" + body + "\n" + fence


def _render_markdown(report, language):
    labels = json.loads((Path(__file__).resolve().parents[1] / "assets/answer-labels.json").read_text(encoding="utf-8"))[language]
    lines = ["## " + labels["conclusion"], ""]
    if not report["excerpts"]:
        lines += [labels["no_extracts"], ""]
    for index, excerpt in enumerate(report["excerpts"], 1):
        lines += ["[" + str(index) + "]", ""]
        key_pairs = excerpt["source"].get("GraphEndpoints", {}).get("JoinKeyPairCount")
        if key_pairs:
            lines += [labels["compound_join"].format(count=key_pairs), ""]
        lines += [_fence(excerpt["value"], "text" if isinstance(excerpt["value"], str) else "json"), ""]
    lines += ["## " + labels["evidence"], "", labels["scope"], ""]
    for index, excerpt in enumerate(report["excerpts"], 1):
        source = excerpt["source"]
        # Values stay in a fence, so evidence titles/IDs never become active HTML, links or instructions.
        citation = {key: source[key] for key in (*IDENTITY, "Title", "FileNames", "RequestId")}
        for key in ("GraphEndpoints", "GraphRelationships"):
            if key in source:
                citation[key] = source[key]
        lines += ["[" + str(index) + "]", "", _fence(citation, "json"), ""]
    if report["warnings"]:
        lines += [labels["warnings"], "", _fence(report["warnings"], "json"), ""]
    lines += ["## " + labels["unknowns"], ""]
    for fragment in report["unconfirmed_question_fragments"]:
        lines += [labels["unconfirmed_fragment"], "", _fence(fragment), ""]
    if report["applicability_unresolved"]:
        lines += [labels["applicability_unresolved"], ""]
    if not report["unconfirmed_question_fragments"] and not report["applicability_unresolved"]:
        lines += [labels["no_listed_unknowns"], ""]
    lines += [labels["semantic_limit"], ""]
    result = "\n".join(lines)
    require(len(result.encode("utf-8")) <= MAX_OUTPUT_BYTES, "BudgetExceeded")
    return result


def render_markdown(job, language="en", expected_response_sha256=None, full_selected_fields=False):
    require(language in ("zh", "en"), "InvalidArguments")
    return _render_markdown(evaluate_job(job, expected_response_sha256, full_selected_fields), language)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise AnswerError("InvalidArguments")


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        commands = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
        create = commands.add_parser("new-job", help="Create a private job in a trusted existing output directory.")
        create.add_argument("--directory", required=True)
        create.add_argument("--from-stdin", action="store_true", help="Initialize the job from a bounded JSON stdin payload.")
        render = commands.add_parser("render", help="Validate the original job and render only bound extracts.")
        render.add_argument("--input", required=True)
        render.add_argument("--language", choices=("zh", "en"), default="en")
        render.add_argument("--format", choices=("markdown", "json"), default="markdown")
        render.add_argument("--expected-response-sha256", help="Check the canonical response batch against an authoritative digest.")
        render.add_argument("--full-selected-fields", action="store_true",
                            help="Keep the complete selected field value; an exact quote remains a checked anchor.")
        args = parser.parse_args(argv)
        if args.command == "new-job":
            content = sys.stdin.buffer.read(MAX_BYTES + 1) if args.from_stdin else None
            print(new_job(args.directory, content=content))
        else:
            report = evaluate_job(load_job(args.input), args.expected_response_sha256, args.full_selected_fields)
            output = _render_markdown(report, args.language) if args.format == "markdown" else encoded(report, indent=2)
            require(len(output.encode("utf-8")) <= MAX_OUTPUT_BYTES, "BudgetExceeded")
            print(output)
        return 0
    except AnswerError as error:
        print(json.dumps({"Success": False, "Error": {"Code": error.code,
              "Message": "The local knowledge answer job is invalid or exceeds safe limits."}}))
        return 2
    except (OSError, ValueError, UnicodeError, RecursionError):
        print('{"Success": false, "Error": {"Code": "InvalidInput", "Message": "The local knowledge answer job is invalid or exceeds safe limits."}}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
