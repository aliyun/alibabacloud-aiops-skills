"""Hand-off ladder for work this skill does not own: local first, then the catalogue.

Why this file exists: the package was assembled out of ~55 single-scope skills, and
every one of them shipped hand-off sentences pointing at its siblings by their old
published codes. Those codes no longer resolve (HTTP 404 against the official
catalogue), so a hand-off written that way sends the customer to a skill that cannot
be installed - a dead end that reads like an answer. The ladder below is the only
sanctioned way to name another skill, and it is deliberately strict:

  1. in-package target  -> stay here; name the check in words, never a code;
  2. installed locally  -> say it is already available, no egress, no download pitch;
  3. published online   -> propose at most two candidates as a confirmation card;
                           nothing is installed until the customer explicitly confirms,
                           after which the agent may install it for them through the
                           platform's sanctioned skill installer (this script itself
                           never downloads or executes external code);
  4. nothing published  -> degrade: state that no matching skill was found and keep
                           answering inside this skill's scope.

ABSOLUTE PROHIBITION: never hand off to a name that was not produced by step 2 or 3,
and never put anything customer-identifying into a catalogue query - that query
leaves this machine.
"""

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

CATALOGUE_HOST = "agentexplorer.aliyuncs.com"
CATALOGUE_DETAIL_URL = "https://" + CATALOGUE_HOST + "/openapi/for-agent/skills/"
CATALOGUE_SEARCH_URL = "https://" + CATALOGUE_HOST + "/openapi/for-agent/skills"
FETCH_TIMEOUT_SECONDS = 8
MAX_BODY_BYTES = 200000
MAX_CANDIDATES = 2

# Catalogue entries that must never be offered as the fix for an ECS fault.
NON_INSTALLABLE_CANDIDATES = frozenset((
    "alibabacloud-find-skills",  # gate:handoff-exempt - a filter, never a target
))

# A hand-off target the customer can act on is either a check this package ships
# (`area:<slug>`), or a code the official catalogue answers 200 for. Anything else
# is a dead name and must not reach an answer.
AREA_TOKEN_PREFIX = "area:"
SELF_PACKAGE_NAME = "alibabacloud-ecs-high-frequency-issues"
LOCAL_ROOTS_ENV = "ECS_LOCAL_SKILL_ROOTS"
LOCAL_ROOTS_DEFAULT = (
    ".agents/skills",
    "~/.agents/skills",
    "~/.codex/skills",
    "~/.qwen/skills",
    "~/.claude/skills",
)
# Anything shaped like a resource id, an account number, an address or a path is
# customer-identifying and is dropped before the query is built.
UNSAFE_QUERY_PATTERNS = (
    re.compile(r"\bi-[a-z0-9]{6,}\b", re.I),
    re.compile(r"\bd-[a-z0-9]{6,}\b", re.I),
    re.compile(r"\bv-[a-z0-9]{6,}\b", re.I),
    re.compile(r"\bsg-[a-z0-9]{6,}\b", re.I),
    re.compile(r"\bLTAI[A-Za-z0-9]{4,}\b"),
    re.compile(r"\b\d{1,3}(\.\d{1,3}){3}\b"),
    re.compile(r"\b\d{10,}\b"),
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    re.compile(r"(?:^|[\s\"'(])(?:[A-Za-z]:)?[/~\.][^\s\"']{2,}"),
)
VERIFIED_DOC_FILE = ("references", "published-handoff-skills.md")
_DOC_ROW_RE = re.compile(r"^\|\s*`(alibabacloud-[a-z0-9-]+)`\s*\|([^|]+)\|", re.I)
_FRONTMATTER_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.M)

_areareas = set()
_verified_cache = None


def register_area_slugs(slugs):
    """Teach the ladder which targets are checks this package already ships."""
    global _areareas
    _areareas = {str(s).strip() for s in (slugs or ()) if s}


def skill_root(default=None):
    return os.path.abspath(default or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def verified_external():
    """Codes pinned as published, read from the document that states it.

    One source of truth: `references/published-handoff-skills.md` is the file a human
    adjudicates against the catalogue, so the code follows the document instead of
    drifting from it. Returns {code: one-line scope}.
    """
    global _verified_cache
    if _verified_cache is not None:
        return _verified_cache
    path = os.path.join(skill_root(), *VERIFIED_DOC_FILE)
    found = {}
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle.read().splitlines():
                row = _DOC_ROW_RE.match(line.strip())
                if row:
                    found[row.group(1).lower()] = row.group(2).strip()
    except OSError:
        found = {}
    _verified_cache = found
    return found


def target_kind(token):
    """'area' for a check this package ships, 'self', 'verified' or None."""
    text = str(token or "").strip().lower()
    if not text:
        return None
    if text.startswith(AREA_TOKEN_PREFIX):
        slug = text[len(AREA_TOKEN_PREFIX):]
        return "area" if (not _areareas or slug in _areareas) else None
    if text == SELF_PACKAGE_NAME:
        return "self"
    bare = re.sub(r"^alibabacloud-(?:ecs-)?", "", text)
    if bare in _areareas:
        return "area"
    if text in verified_external():
        return "verified"
    return None


def humanise(token):
    words = re.sub(r"^alibabacloud-(?:ecs-)?", "", str(token or "").strip().lower())
    words = words.replace(AREA_TOKEN_PREFIX, "").replace("-", " ").strip()
    return words or "that check"


def local_skill_names():
    """Skills already present on this machine: {name: path}.

    Offline by construction - a directory scan of the known skill roots. Nothing here
    reaches the network, which is the point: an installed skill needs no download card.
    """
    configured = os.environ.get(LOCAL_ROOTS_ENV, "").strip()
    roots = ([p for p in configured.split(os.pathsep) if p.strip()]
             if configured else list(LOCAL_ROOTS_DEFAULT))
    installed = {}
    for root in roots:
        base = os.path.expanduser(os.path.expandvars(root.strip()))
        if not os.path.isabs(base):
            base = os.path.join(skill_root(), base)
        try:
            entries = sorted(os.listdir(base))
        except OSError:
            continue
        for name in entries:
            manifest = os.path.join(base, name, "SKILL.md")
            try:
                with open(manifest, encoding="utf-8") as handle:
                    head = handle.read(2000)
            except (OSError, UnicodeDecodeError):
                continue
            match = _FRONTMATTER_NAME_RE.search(head)
            declared = (match.group(1).strip().lower() if match else name.lower())
            installed.setdefault(declared, os.path.join(base, name))
    return installed


def safe_keywords(text, limit=6):
    """Generic symptom words only; every identifier-shaped token is dropped."""
    cleaned = str(text or "")
    for pattern in UNSAFE_QUERY_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    stop = {"the", "a", "an", "is", "are", "to", "of", "and", "or", "in", "on", "my",
            "it", "this", "that", "not", "cannot", "can", "for", "with", "please"}
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9+#-]{2,}|[一-鿿]{2,}", cleaned)
             if w.lower() not in stop]
    return " ".join(words[:limit]).strip()


def _get_json(url):
    """One GET, host-pinned, bounded. Returns (verdict, payload)."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.netloc != CATALOGUE_HOST:
        return "malformed-url", None
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            raw = response.read(MAX_BODY_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return "not-found", None
        return "rejected", None
    except (urllib.error.URLError, TimeoutError, OSError):
        return "blocked", None
    if len(raw) > MAX_BODY_BYTES:
        return "too-large", None
    try:
        payload = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return "malformed-body", None
    return "ok", payload


def _candidate_from_detail(name, payload):
    content = str((payload or {}).get("content") or "")
    declared = _FRONTMATTER_NAME_RE.search(content)
    if declared and declared.group(1).strip().lower() != name.lower():
        # The catalogue answered for a different skill than was asked for. Naming it
        # would send the customer to something they did not choose.
        return None
    summary = _frontmatter_description(content) or verified_external().get(name.lower(), "")
    return {"name": name.lower(), "scope": _one_line(summary)}


# A frontmatter description is written for an agent, in either spelling:
# `description: one line` or `description: |` followed by an indented block. Taking
# the block indicator as the value printed `|` as the skill's scope, which reads as
# a broken card; and the trigger keyword list is machine input, not something to
# hand a customer.
_YAML_BLOCK_INDICATOR_RE = re.compile(r"^[|>][-+]?\d*$")
_DESCRIPTION_KEY_RE = re.compile(r"^description:\s*(.*)$")
_SCOILER_RE = re.compile(r"\b(?:Triggers|trigger)\s*:.*$", re.S)
MAX_SCOPE_CHARS = 180


def _frontmatter_description(content):
    """The declared description of a skill document, block scalar included."""
    lines = (content or "").splitlines()
    for index, line in enumerate(lines):
        match = _DESCRIPTION_KEY_RE.match(line.strip())
        if not match:
            continue
        value = match.group(1).strip().strip("'\"")
        if value and not _YAML_BLOCK_INDICATOR_RE.match(value):
            return value
        collected = []
        for following in lines[index + 1:]:
            if following.strip() and not following[:1].isspace():
                break
            if following.strip():
                collected.append(following.strip())
        return " ".join(collected)
    return ""


def _one_line(text, limit=MAX_SCOPE_CHARS):
    """Collapse a multi-line scope into one readable sentence, without cutting it
    mid-word or carrying the keyword list meant for the router."""
    text = _SCOILER_RE.sub("", str(text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    window = text[:limit]
    for boundary in (". ", "\u3002", "! ", "? ", "; ", ", "):
        cut = window.rfind(boundary)
        if cut >= limit // 2:
            return window[:cut + len(boundary)].strip()
    space = window.rfind(" ")
    return (window[:space] if space > 0 else window).rstrip(" ,;") + "..."


def _candidates_from_search(payload):
    items = payload if isinstance(payload, list) else (payload or {}).get("data") or []
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("skillName") or "").strip().lower()
        if not name or name == SELF_PACKAGE_NAME or name in out:
            continue
        if name in NON_INSTALLABLE_CANDIDATES:
            # A skill whose job is to look skills up cannot be the answer to a fault:
            # this ladder already queried the catalogue, so recommending its search
            # box would send the customer in a circle instead of to a fix.
            continue
        scope = _one_line(str(item.get("description") or item.get("displayName") or ""))
        out.append({"name": name, "scope": scope})
        if len(out) >= MAX_CANDIDATES:
            break
    return out


def plan(token="", keywords="", local=None):
    """Run the ladder for one hand-off need. Never egresses for an in-package target."""
    installed = local_skill_names() if local is None else local
    kind = target_kind(token)
    name = re.sub(r"^alibabacloud-(?:ecs-)?", "", str(token or "").strip().lower())
    code = str(token or "").strip().lower()
    if code and not code.startswith("alibabacloud-"):
        code = "alibabacloud-ecs-" + code
    if kind == "area" and name:
        return {"verdict": "stay-here", "target": name,
                "detail": "the %s check ships inside this skill" % name}
    if kind == "self":
        return {"verdict": "stay-here", "target": SELF_PACKAGE_NAME,
                "detail": "this skill is the one already answering"}
    if code and code in installed:
        return {"verdict": "local", "name": code, "path": installed[code],
                "target": name}
    query_words = safe_keywords(keywords or humanise(token))
    if kind == "verified" and code:
        verdict, payload = _get_json(CATALOGUE_DETAIL_URL + urllib.parse.quote(code))
        if verdict == "ok":
            candidate = _candidate_from_detail(code, payload)
            if candidate:
                return {"verdict": "card", "candidates": [candidate],
                        "source": "catalogue", "query": query_words, "target": name}
        elif verdict in ("blocked", "rejected", "too-large", "malformed-body"):
            return {"verdict": "degrade", "reason": verdict,
                    "detail": "the published skill could not be confirmed right now",
                    "target": name}
        return {"verdict": "degrade", "reason": "not-found", "target": name}
    if not query_words:
        return {"verdict": "degrade", "reason": "no-safe-keywords",
                "detail": "no generic symptom words were left after identifiers were "
                          "removed, and an identifier must never be sent to the "
                          "catalogue", "target": name}
    verdict, payload = _get_json(CATALOGUE_SEARCH_URL + "?q=" + urllib.parse.quote(query_words))
    if verdict != "ok":
        return {"verdict": "degrade", "reason": verdict,
                "detail": "the catalogue could not be reached right now",
                "target": name}
    found = _candidates_from_search(payload)
    if not found:
        return {"verdict": "degrade", "reason": "no-match", "query": query_words,
                "target": name}
    return {"verdict": "card", "candidates": found, "source": "catalogue-search",
            "query": query_words, "target": name}


def lines_for(result):
    """The customer-facing lines. Prose only: no code is ever invented, and at most
    two candidates are offered so the block cannot grow."""
    verdict = (result or {}).get("verdict")
    if verdict == "stay-here":
        return ["Continue here: the %s check is part of this skill, so nothing else "
                "needs to be installed." % humanise(result.get("target"))]
    if verdict == "local":
        return ["This machine already has the %s check available, so use it directly; "
                "no download is needed." % humanise(result.get("name"))]
    if verdict == "card":
        lines = ["The official skill catalogue lists these for the part of the "
                 "question this skill does not own. Compare each stated scope with "
                 "the remaining question first: if none of them covers it, there is "
                 "no hand-off and this skill keeps answering. Nothing is installed "
                 "until you confirm:"]
        for candidate in result.get("candidates", [])[:MAX_CANDIDATES]:
            scope = candidate.get("scope") or "its own document states what it settles"
            lines.append("  - %s - %s" % (candidate.get("name"), scope))
        lines.append("  - Next: tell me to go ahead and I will install it for you "
                     "through the official platform skill installer; until then this "
                     "skill keeps answering within its own scope.")
        return lines
    reason = (result or {}).get("reason") or "no-match"
    detail = (result or {}).get("detail") or "no matching published skill was found"
    return ["No separate skill was found for this part of the question (%s): %s. "
            "This stays inside the current diagnosis, and the parts that still need a "
            "human are named below." % (reason, detail)]
