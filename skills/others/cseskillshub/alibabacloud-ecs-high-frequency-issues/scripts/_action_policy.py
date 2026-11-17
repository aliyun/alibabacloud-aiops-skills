"""Action classes: what this skill may execute, what it may only explain.

The table is `../references/action-classes.json`, and it is the only place a class is
decided. Three classes, from the customer's own ruling (2026-11-12):

  auto-read       changes nothing                 runs on its own
  consent-write   configuration or a billable     runs only after the customer agrees to
                  object                          that one operation, with its effects and
                                                  cost printed
  guide-only      interrupts service or destroys  never dispatched; the guide is printed
                  data / changes paid config that
                  lands through a restart

Two things this module owns that prose cannot:

1. it refuses an argv that names a guide-only action, before the child process starts;
2. it prints the disclosure an executed consent-write owes (a snapshot bills), instead of
   trusting each of the 55 areas to remember it - today only 3 areas dispatch
   `CreateSnapshot` and none of them states the billing basis in the customer body.

Pattern strictness follows what a wrong hit costs (the same rule the evidence-source table
states): a refusal or an extra disclosure line is visible and reversible, so the argv match
is loose; a *violation* claim says the skill mutated a customer resource, so that match is
anchored to dispatch shapes that a customer-facing sentence cannot accidentally produce.
"""

import json
import os
import re

TABLE_REL = os.path.join("..", "references", "action-classes.json")

GUIDE_HEAD = "Guide only, not executed for you: %s"
DISCLOSE_HEAD = "What that operation does to you: %s"
VIOLATION_HEAD = "This run dispatched %s, which this skill's own action table reserves " \
                 "to you: treat that effect as real and verify it before relying on it."

# An area names an action it means to execute either as its own argv element or as the
# value of an action-shaped flag. Free text (a symptom sentence) is deliberately not
# scanned: an exact-element match refuses the leg it can prove, and prose that happens
# to contain the words must not silently lose its diagnosis.
_ACTION_FLAG_RE = re.compile(r'(?i)^--.*(action|api|operation|verb)(=|$)')

# Dispatch evidence for a guide-only action. Deliberately narrow: it matches the
# shapes a CLI invocation or a request record takes, not advice prose. Measured
# against the 55 areas, an answer may legitimately say "restart the instance in the
# console" - it may not emit `ecs reboot-instance` or `Action=RebootInstance`.
_VIOLATION_RES = (
    ("cli-invocation", re.compile(r"(?i)\baliyun\s+[a-z]+[\s-]+"
                                  r"(reboot-instance|stop-instance|start-instance|delete-instance|"
                                  r"re-init-disk|replace-system-disk|redeploy-instance|"
                                  r"modify-instance-spec|modify-instance-network-spec|"
                                  r"modify-prepay-instance-spec|release-eip-address|"
                                  r"delete-snapshot|install-cloud-assistant)\b")),
    ("request-record", re.compile(r"(?i)(?:Action|\"Action\")\s*[=:]\s*\"?("
                                  r"Reboot(?:Instances?)?|Stop(?:Instances?)?|Start(?:Instances?)?|"
                                  r"Delete(?:Instance|Snapshot)|ReInitDisk|ReplaceSystemDisk|"
                                  r"RedeployInstance|Modify(?:Instance|PrepayInstance|InstanceNetwork)Spec|"
                                  r"ReleaseEipAddress|InstallCloudAssistant)\"?")),
    ("api-called", re.compile(r"(?i)\b(?:invoked|called|dispatched|submitted)\s+"
                              r"(?:the\s+)?(?:ecs[:_-])?("
                              r"Reboot(?:Instances?)?|Stop(?:Instances?)?|Delete(?:Instance|Snapshot)|"
                              r"ReInitDisk|ReplaceSystemDisk|RedeployInstance|InstallCloudAssistant)"
                              r"\b(?:\s+api)?")),
)


def load(here):
    """(actions, error). `actions` is a list of table rows, or an empty list with a
    reason naming what is wrong with the file - the same contract the routing table
    uses, so a missing table degrades the answer instead of killing the run."""
    path = os.path.join(here, TABLE_REL)
    if not os.path.isfile(path):
        return [], "missing"
    try:
        with open(path, encoding="utf-8") as handle:
            table = json.load(handle)
    except ValueError as exc:
        return [], "unparseable: %s" % exc
    actions = table.get("actions")
    if not isinstance(actions, list):
        return [], "no actions list"
    return actions, None


def index(actions):
    """Both spellings of an action map to its row: plugin-mode cli name and RPC api name."""
    out = {}
    for row in actions:
        for key in (row.get("api"), row.get("cli"), row.get("id")):
            if key:
                out[key.lower()] = row
    return out


def classes_of(actions):
    """{class: [rows]} in table order; what the gate and the doc both read."""
    out = {}
    for row in actions:
        out.setdefault(row.get("class"), []).append(row)
    return out


def _mentions(argv, by_key):
    """Rows whose action name is this argv's stated target: an element equal to the
    name, or the value of an action-shaped flag. Not free text."""
    hits, prev_flag = [], None
    for tok in list(argv or []):
        if tok.startswith('--'):
            prev_flag = tok
            names = [tok.split('=', 1)[1]] if ('=' in tok and _ACTION_FLAG_RE.match(tok)) else []
        else:
            names = [tok]
            if prev_flag and not _ACTION_FLAG_RE.match(prev_flag):
                names = []          # the value of an ordinary flag is free text
            prev_flag = None
        for name in names:
            row = by_key.get(name.lower())
            if row is not None and row.get('class') == 'guide-only' and row not in hits:
                hits.append(row)
    return hits


def refusal_lines(argv, actions):
    """Customer-facing refusal for a guide-only action this call tried to run.

    Returns ([], []) when nothing is refused: the caller keeps going, and the read-only
    legs still answer. A refusal never executes the leg it names.
    """
    by_key = index(actions)
    hits = _mentions(argv, by_key)
    lines, ids = [], []
    for row in hits:
        ids.append(row.get("api") or row.get("id"))
        lines.extend(guidance_lines(row))
    return lines, ids


def guidance_lines(row):
    """The guide block, in customer words only.

    The row's `obligations` are deliberately NOT printed: they are the table's internal
    vocabulary (state-cost, rollback-point), and pasting them into an answer is the same
    defect as pasting a switch name - the customer cannot act on a label of our own
    making. What they mean is carried by the disclosure sentence instead.
    """
    out = [GUIDE_HEAD % (row.get("why_this_class") or "that operation")]
    text = row.get("customer_disclosure")
    if text:
        out.append("  - " + text)
    return out


def disclosure_lines(actions, body_lines):
    """The disclosure an executed consent-write owes but the area did not print.

    Only for rows this run can be shown to have touched: the run's own lines must name
    the action's api or cli. Nothing here is printed speculatively - a snapshot that was
    not created does not get a billing lecture, and an answer that already states the
    cost is left alone.
    """
    text = "\n".join(body_lines or [])
    out = []
    for row in classes_of(actions).get("consent-write", []):
        if row.get("capability") != "dispatched":
            continue
        names = [row.get("api"), row.get("cli")]
        if not any(n and n.lower() in text.lower() for n in names):
            continue
        obligation = row.get("obligations") or []
        if "state-cost" not in obligation:
            continue
        disclosure = (row.get("customer_disclosure") or "").strip()
        if not disclosure:
            continue
        if _cost_already_said(text, row):
            continue
        out.append(DISCLOSE_HEAD % disclosure)
    return out


_COST_MARKS = {
    # Each consent-write that bills gets its own way of recognising "cost already said",
    # because the areas spell a charge many ways. An action with no rule here is always
    # disclosed, which prints one extra line rather than hiding a charge.
    "create-snapshot": re.compile(
        r"(?i)(?:snapshot|backup).{0,80}(?:fee|fees|charged?|bill|cost|price|capacity)"
        r"|(?:fee|charge|bill|cost).{0,80}(?:snapshot|backup)"),
}


def _cost_already_said(text, row):
    """True when the run's own words already state this action's cost."""
    pattern = _COST_MARKS.get(row.get("id"))
    return bool(pattern and pattern.search(text))


def violations(lines):
    """Guide-only actions this run's own output claims were dispatched, with the shape
    that said so. A non-empty result is a defect in this package, not a customer problem:
    it means a leg executed something the class table reserves to the customer."""
    text = "\n".join(lines or [])
    out = []
    for shape, pattern in _VIOLATION_RES:
        for match in pattern.findall(text):
            if (shape, match) not in out:
                out.append((shape, match))
    return out


def violation_customer_line(violations_found):
    """A caution the customer is owed when a leg actually executed a guide-only action.

    Only the strongest evidence shape speaks: `cli-invocation` means a command string
    ran, which the customer's resources feel. A `request-record` or `api-called` match
    can come from quoting a RAM policy or a log line, so it stays on the run log as a
    defect signal instead of alarming the customer with a mutation that did not happen.
    """
    names = sorted(set(a for shape, a in violations_found if shape == "cli-invocation"))
    return VIOLATION_HEAD % ", ".join(names) if names else None


def writes_seen(actions, lines):
    """Which dispatched write-class actions this run's own output names.

    Reported, never inferred from the exit code, and never used to print anything by
    itself - it is the `executed-write=` field of ACTION-CLASS, so two runs of the same
    ticket can be compared on what they touched.
    """
    text = "\n".join(lines or []).lower()
    out = []
    for row in classes_of(actions).get("consent-write", []):
        if row.get("capability") != "dispatched":
            continue
        for name in (row.get("api"), row.get("cli")):
            if name and name.lower() in text:
                if row.get("api") not in out:
                    out.append(row.get("api"))
                break
    return out


def class_note(refused, disclosed, violations_found, table_error, dispatched_writes):
    """One stderr line, so a re-run can be compared: what this run executed, refused,
    disclosed, and what it should never have done."""
    if table_error:
        return "action record: table unavailable (%s); classes not applied" % table_error
    parts = ["executed-write=%s" % (",".join(dispatched_writes) or "none"),
             "refused=%s" % (",".join(refused) or "none"),
             "disclosure-added=%d" % len(disclosed)]
    if violations_found:
        parts.append("VIOLATION=%s" % ",".join(sorted(set(a for _, a in violations_found))))
    return "action record: " + " ".join(parts)
