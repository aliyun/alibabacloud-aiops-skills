"""Single entry point for alibabacloud-ecs-marketplace-image-guide.

What it does
  * read-only fact collection for ECS instances that use an Alibaba Cloud Marketplace or
    other paid third-party image: which image is attached, what the image metadata says,
    what instance type and lifecycle state the instance is in;
  * deterministic routing of the customer symptom to the matching rule set and to the
    customer-side console guidance held in this package's references;
  * a report that always ends with STATUS and NEXT_ACTION.

What it never does
  * it never calls a non-read-only action (see references/ram-policies.md), never runs
    anything inside a customer instance, and never submits an order, cancellation,
    conversion or support ticket on the customer's behalf.

Examples
  python3 ecs_marketplace_image_guide.py --region-id cn-hangzhou \
      --instance-id i-example01 --symptom conversion-blocked
  python3 ecs_marketplace_image_guide.py --region-id cn-shenzhen \
      --image-id m-example001 --intent selection
  python3 ecs_marketplace_image_guide.py --region-id cn-hangzhou --inventory
"""

import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import _cli
import _constants as C
import sts_token

_FAMILY_TOKEN_RE = re.compile(r"ecs\.[A-Za-z0-9][A-Za-z0-9.\-]*", re.I)
_SLASH_LIST_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:/[A-Za-z][A-Za-z0-9]*){1,}\b")
_STOPWORDS = ("and", "or", "the", "spec", "only", "support", "instance", "type")
_PAID_HINTS = ("windows", "red hat", "redhat", "suse", "alibaba cloud linux 3 pro")


# ------------------------------------------------------------------ helpers
def _norm(token):
    return re.sub(r"[^a-z0-9]", "", str(token).lower())


def _instance_family(instance_type):
    parts = str(instance_type or "").split(".")
    if len(parts) >= 2 and parts[0].lower() == "ecs":
        return parts[1]
    return str(instance_type or "")


def _candidate_families(*sources):
    """Pull supported-family hints out of image metadata text, when present."""
    found = []
    for source in sources:
        blob = str(source or "")
        if not blob:
            continue
        for match in _FAMILY_TOKEN_RE.findall(blob):
            pieces = match.strip().rstrip("].,;)").split(".")
            token = pieces[1] if len(pieces) > 1 else pieces[0]
            if token and token not in found:
                found.append(token)
        for match in _SLASH_LIST_RE.findall(blob):
            for piece in match.strip("[](){}").split("/"):
                piece = piece.strip()
                if len(piece) < 2 or piece.lower() in _STOPWORDS:
                    continue
                if piece not in found:
                    found.append(piece)
    return found


def _family_matches(family, candidates):
    """Names that overlap the running family, compared on normalised tokens."""
    target = _norm(family)
    if not target:
        return []
    hits = []
    for candidate in candidates:
        token = _norm(candidate)
        if not token:
            continue
        if token.startswith(target) or target.startswith(token) or token in target:
            hits.append(candidate)
    return hits


def _image_fields(image):
    return {
        "image_id": _cli.text(_cli.pick(image, ("ImageId",))),
        "name": _cli.text(_cli.pick(image, ("ImageName", "Name"))),
        "os_name": _cli.text(_cli.pick(image, ("OSName", "OSNameEn"))),
        "os_type": _cli.text(_cli.pick(image, ("OSType",))),
        "platform": _cli.text(_cli.pick(image, ("Platform",))),
        "architecture": _cli.text(_cli.pick(image, ("Architecture",))),
        "image_size_gib": _cli.text(_cli.pick(image, ("ImageSize",))),
        "owner_alias": _cli.text(_cli.pick(image, ("ImageOwnerAlias",))),
        "product_code": _cli.text(_cli.pick(image, ("ProductCode",))),
        "status": _cli.text(_cli.pick(image, ("Status",))),
        "progress": _cli.text(_cli.pick(image, ("Progress",))),
        "is_public": _cli.text(_cli.pick(image, ("IsPublic",))),
        "resource_group_id": _cli.text(_cli.pick(image, ("ResourceGroupId",))),
        "creation_time": _cli.text(_cli.pick(image, ("CreationTime",))),
    }


def _classify(fields):
    """Classify the image source from returned fields only, naming every signal used."""
    alias = fields["owner_alias"].lower()
    product_code = fields["product_code"].strip()
    blob = " ".join([fields["name"], fields["os_name"], fields["platform"]]).lower()
    paid_hints = [hint for hint in _PAID_HINTS if hint in blob]
    signals = []

    if alias:
        signals.append("ImageOwnerAlias={0}".format(fields["owner_alias"]))
    else:
        signals.append("ImageOwnerAlias absent from the response")
    if product_code:
        signals.append("ProductCode={0}".format(product_code))
    if paid_hints:
        signals.append("licence-charging operating system hint: {0}".format(
            ", ".join(paid_hints)))

    if alias == "self":
        if product_code:
            signals.append("product code present on a customer image: treat it as derived "
                           "from a paid image, the licence charge follows it")
        return "customer-image", signals
    if alias == "marketplace" or (product_code and alias in ("", "others")):
        return "marketplace", signals
    if alias == "system":
        return ("paid-public" if paid_hints else "public"), signals
    if alias == "others":
        return "shared-or-vendor", signals
    return "unknown", signals


def _is_paid(verdict, fields):
    """Whether a licence charge is attached, from the verdict and the raw fields."""
    if verdict in ("marketplace", "paid-public"):
        return True
    return verdict == "customer-image" and bool(fields["product_code"].strip())


def _rows(body, wrapper, inner):
    """Descend the standard response envelope, tolerant of flattened shapes."""
    node = _cli.pick(body or {}, (wrapper,), None)
    if isinstance(node, dict):
        return _cli.unwrap(_cli.pick(node, (inner,), []))
    return _cli.unwrap(node)


def _instance_image_id(item):
    image_node = _cli.pick(item, ("Image",), {}) or {}
    return _cli.text(_cli.pick(image_node, ("ImageId",)))


def _try_call(action, params, session_id, notes):
    if action not in C.READ_ACTIONS:
        raise SystemExit("blocked: {0} is outside the read-only whitelist".format(action))
    try:
        return _cli.call(action, params=params, session_id=session_id)
    except _cli.CliError as exc:
        note = "{0} failed -> {1}".format(action, exc)
        if exc.code in C.NO_PERMISSION_CODES:
            note += ("; the credential is missing the read action listed in "
                     "references/ram-policies.md, grant that action only")
        _cli.warn(note)
        notes.append(note)
        return None


# ------------------------------------------------------------- read-only API
def fetch_instances(region, instance_ids, session_id, notes):
    """DescribeInstances: by identifier when given, else region-wide paging."""
    collected = []
    if instance_ids:
        for start in range(0, len(instance_ids), C.MAX_INSTANCE_IDS):
            chunk = instance_ids[start:start + C.MAX_INSTANCE_IDS]
            body = _try_call("DescribeInstances", {
                "RegionId": region,
                "InstanceIds": json.dumps(chunk),
                "PageSize": C.DEFAULT_PAGE_SIZE,
            }, session_id, notes)
            collected += _rows(body, "Instances", "Instance")
        return collected

    page = 1
    while page <= C.MAX_PAGES:
        body = _try_call("DescribeInstances", {
            "RegionId": region,
            "PageSize": C.DEFAULT_PAGE_SIZE,
            "PageNumber": page,
        }, session_id, notes)
        rows = _rows(body, "Instances", "Instance")
        collected += rows
        try:
            total = int(_cli.pick(body or {}, ("TotalCount",), len(collected)))
        except (TypeError, ValueError):
            total = len(collected)
        if len(rows) < C.DEFAULT_PAGE_SIZE or len(collected) >= total:
            break
        page += 1
    if page > C.MAX_PAGES:
        notes.append("region inventory stopped after {0} pages".format(C.MAX_PAGES))
    return collected


def fetch_images(region, image_ids, session_id, notes):
    """DescribeImages per identifier; returns {image_id: field dict}."""
    result = {}
    for image_id in image_ids:
        if not image_id:
            continue
        body = _try_call("DescribeImages", {
            "RegionId": region,
            "ImageId": image_id,
            "PageSize": C.DEFAULT_PAGE_SIZE,
        }, session_id, notes)
        rows = _rows(body, "Images", "Image")
        if not rows:
            notes.append(
                "DescribeImages returned no row for {0} in {1}: the image may sit in "
                "another region or another account, so its source stays unknown rather "
                "than being called absent.".format(image_id, region))
            continue
        result[image_id] = _image_fields(rows[0])
    return result


def fetch_status(region, instance_ids, session_id, notes):
    """DescribeInstanceStatus: returns {instance_id: lifecycle status}."""
    result = {}
    if not instance_ids:
        return result
    for start in range(0, len(instance_ids), C.MAX_INSTANCE_IDS):
        chunk = instance_ids[start:start + C.MAX_INSTANCE_IDS]
        params = {"RegionId": region, "PageSize": C.DEFAULT_PAGE_SIZE}
        for index, instance_id in enumerate(chunk, start=1):
            params["InstanceId.{0}".format(index)] = instance_id
        body = _try_call("DescribeInstanceStatus", params, session_id, notes)
        for row in _rows(body, "InstanceStatuses", "InstanceStatus"):
            key = _cli.text(_cli.pick(row, ("InstanceId",)))
            if key:
                result[key] = _cli.text(_cli.pick(row, ("Status",)))
    return result


# ------------------------------------------------------------------ printing
def _section(title):
    print("\n[{0}]".format(title))


def _lines(items, prefix="  - "):
    for item in items or ():
        print("{0}{1}".format(prefix, item))


def _numbered(items):
    for index, item in enumerate(items or (), start=1):
        print("      {0}. {1}".format(index, item))


def print_playbook(symptoms):
    for symptom in symptoms:
        block = C.SYMPTOM_PLAYBOOK.get(symptom)
        if not block:
            continue
        _section("PLAYBOOK: {0}".format(block["title"]))
        print("  route: {0}".format(symptom))
        print("  first question for the customer: {0}".format(block["first-question"]))
        _lines([C.RULES[key] for key in block["rules"] if key in C.RULES],
               prefix="  rule: ")
        print("  steps performed by the customer in the console:")
        _numbered(block["steps"])
        _lines([C.RISK_BLOCKS[key] for key in block["risk"] if key in C.RISK_BLOCKS],
               prefix="  risk before submitting: ")
        _lines(block["recheck"], prefix="  recheck after the customer acts: ")
        print("  escalation: {0}".format(block["escalation"]))


def print_help_docs():
    _section("HELP LIBRARY")
    _lines(["{0}: {1}".format(title, url) for title, url in C.HELP_DOCS])


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="ecs_marketplace_image_guide.py",
        description=(
            "Read-only Marketplace and paid-image fact collection plus guided resolution "
            "for Alibaba Cloud ECS. This tool only queries; every change is performed by "
            "the customer in the console."),
        epilog="Queries use the default credential chain; never pass credentials here.")
    parser.add_argument("--region-id", default="",
                        help="Required by every read-only action used here.")
    parser.add_argument("--instance-id", action="append", default=[],
                        help="Instance identifier, repeatable or comma separated.")
    parser.add_argument("--image-id", action="append", default=[],
                        help="Image identifier, repeatable or comma separated.")
    parser.add_argument("--inventory", action="store_true",
                        help="Scan every visible instance in the region for paid images.")
    parser.add_argument("--symptom", choices=list(C.SYMPTOMS),
                        help="Routed symptom, chosen after the customer wording is read.")
    parser.add_argument("--intent", choices=list(C.INTENTS),
                        help="Customer goal when no single console message is quoted.")
    parser.add_argument("--error-text", default="",
                        help="Verbatim console message, used to auto-route the symptom.")
    parser.add_argument("--target-image-id", default="",
                        help="Candidate image for a supported-family comparison.")
    parser.add_argument("--facts-only", action="store_true",
                        help="Skip rule and guidance blocks; print facts and verdict only.")
    parser.add_argument("--list-symptoms", action="store_true",
                        help="Print the routing vocabulary and exit.")
    args = parser.parse_args(argv)
    if not args.list_symptoms and not args.region_id:
        parser.error(
            "--region-id is required: every read-only action used here takes RegionId "
            "as a mandatory parameter")
    return args


def _split_values(values):
    out = []
    for value in values or ():
        for piece in str(value).split(","):
            piece = piece.strip()
            if piece and piece not in out:
                out.append(piece)
    return out


def _auto_symptom(args, error_text):
    if args.symptom:
        return args.symptom
    blob = (error_text or "").lower()
    if not blob:
        return ""
    scored = []
    for symptom, keywords in C.SYMPTOM_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in blob)
        if score:
            scored.append((score, symptom))
    if not scored:
        return ""
    scored.sort(key=lambda item: (-item[0], item[1]))
    return scored[0][1]


def main(argv=None):
    args = parse_args(argv)
    if args.list_symptoms:
        print("symptoms: {0}".format(", ".join(C.SYMPTOMS)))
        print("intents: {0}".format(", ".join(C.INTENTS)))
        return 0

    session_id = _cli.new_session_id()
    notes = []
    instances = []
    images = {}
    statuses = {}
    verdicts = {}

    print("== {0} v{1} ==".format(C.SKILL_NAME, C.SKILL_VERSION))
    print("session_id: {0}".format(session_id))
    print("user_agent: {0}".format(_cli.user_agent(session_id)))
    print("region: {0}".format(args.region_id))
    print("scope: read-only Describe queries only; this tool changes nothing")

    identity = sts_token.describe_for_report(session_id=session_id)
    print("account: {0}".format(identity["account_id"] or "-"))
    print("       {0}".format(identity["note"]))
    if identity["error"]:
        notes.append("caller identity unavailable: {0}".format(identity["error"]))

    instance_ids = _split_values(args.instance_id)
    image_ids = _split_values(args.image_id)

    _section("FACTS: DescribeInstances")
    if instance_ids or args.inventory:
        instances = fetch_instances(args.region_id, instance_ids, session_id, notes)
        if not instances:
            print("  no instance row was returned for this account and region")
        for item in instances:
            print("  {0} name={1} status={2} type={3} image={4} charge={5} zone={6} "
                  "rg={7}".format(
                      _cli.text(_cli.pick(item, ("InstanceId",))),
                      _cli.text(_cli.pick(item, ("InstanceName",))),
                      _cli.text(_cli.pick(item, ("Status",))),
                      _cli.text(_cli.pick(item, ("InstanceType",))),
                      _instance_image_id(item) or "-",
                      _cli.text(_cli.pick(item, ("InstanceChargeType",))),
                      _cli.text(_cli.pick(item, ("ZoneId",))),
                      _cli.text(_cli.pick(item, ("ResourceGroupId",))) or "-"))
            attached = _instance_image_id(item)
            if attached and attached not in image_ids:
                image_ids.append(attached)
    else:
        print("  skipped: pass --instance-id or --inventory to collect instance facts")

    _section("FACTS: DescribeImages")
    if args.target_image_id and args.target_image_id not in image_ids:
        image_ids.append(args.target_image_id)
    if image_ids:
        images = fetch_images(args.region_id, image_ids, session_id, notes)
        for image_id in image_ids:
            fields = images.get(image_id)
            if not fields:
                continue
            verdict, signals = _classify(fields)
            verdicts[image_id] = (verdict, signals, fields)
            print("  {0} source-verdict={1}".format(image_id, verdict))
            print("       name={0} os={1} platform={2} arch={3} size={4}GB status={5} "
                  "progress={6} ownerAlias={7} productCode={8} resourceGroup={9}".format(
                      fields["name"] or "-", fields["os_name"] or "-",
                      fields["platform"] or "-", fields["architecture"] or "-",
                      fields["image_size_gib"] or "-", fields["status"] or "-",
                      fields["progress"] or "-", fields["owner_alias"] or "-",
                      fields["product_code"] or "-", fields["resource_group_id"] or "-"))
            _lines(signals, prefix="       signal: ")
    else:
        print("  skipped: no image identifier was available to query")

    _section("FACTS: DescribeInstanceStatus")
    queried_ids = [_cli.text(_cli.pick(item, ("InstanceId",))) for item in instances]
    queried_ids = [item for item in queried_ids if item] or instance_ids
    if queried_ids:
        statuses = fetch_status(args.region_id, queried_ids, session_id, notes)
        for instance_id in queried_ids:
            print("  {0} status={1}".format(instance_id, statuses.get(instance_id, "-")))
        if not statuses:
            print("  no status row was returned for the requested identifiers")
    else:
        print("  skipped: no instance identifier in scope")

    _section("VERDICT: paid-image involvement")
    if not verdicts:
        print("  undetermined: no image metadata was resolved. Ask the customer for the "
              "exact image name and identifier shown in the console before concluding.")
    for image_id in image_ids:
        entry = verdicts.get(image_id)
        if not entry:
            continue
        verdict, _signals, _fields = entry
        if verdict == "marketplace":
            print("  {0}: Marketplace image. The licence charges and the restriction "
                  "matrix in references/restriction-matrix.md apply.".format(image_id))
        elif verdict == "paid-public":
            print("  {0}: Alibaba-provided image whose operating system carries a "
                  "licence: renewal renews that licence too.".format(image_id))
        elif verdict == "public":
            print("  {0}: public image with no licence hint: Marketplace restrictions do "
                  "not apply to it.".format(image_id))
        elif verdict == "customer-image":
            print("  {0}: customer-built image. Check whether it was derived from a paid "
                  "image, because the fee follows the derived image.".format(image_id))
        else:
            print("  {0}: source undetermined from the queried fields; confirm on the "
                  "Marketplace product page before applying any rule.".format(image_id))

    _section("COMPATIBILITY")
    if args.target_image_id:
        entry = verdicts.get(args.target_image_id)
        if not entry:
            print("  target image {0} was not resolved, so no comparison is "
                  "possible.".format(args.target_image_id))
        else:
            fields = entry[2]
            families = _candidate_families(fields["name"], fields["os_name"],
                                           fields["platform"])
            rows = dict((_cli.text(_cli.pick(item, ("InstanceId",))), item)
                        for item in instances)
            for instance_id in (queried_ids or instance_ids):
                instance_type = _cli.text(_cli.pick(rows.get(instance_id, {}),
                                                    ("InstanceType",)))
                if not instance_type:
                    print("  {0}: instance type not known, so the comparison needs the "
                          "customer to state it.".format(instance_id))
                    continue
                if not families:
                    print("  {0} type={1}: the queried metadata carries no "
                          "supported-family hint. The Marketplace product detail page is "
                          "the authority; this tool does not guess.".format(
                              instance_id, instance_type))
                    continue
                family = _instance_family(instance_type)
                hits = _family_matches(family, families)
                if hits:
                    print("  {0} type={1}: family {2} matches the image hint ({3}). "
                          "Compatible on this axis.".format(
                              instance_id, instance_type, family, ", ".join(families)))
                else:
                    print("  {0} type={1}: family {2} is outside the image hint ({3}). "
                          "Select a supported family, or a newer image."
                          .format(instance_id, instance_type, family,
                                  ", ".join(families)))
    else:
        print("  skipped: pass --target-image-id to compare a candidate image with the "
              "running instance type")

    _section("STATE CHECK: instance state required by console flows")
    for instance_id in (queried_ids or []):
        state = statuses.get(instance_id, "")
        if state.lower() == "stopped":
            print("  {0}: Stopped, so the console flows that require a stopped instance "
                  "can proceed once the backup is confirmed.".format(instance_id))
        elif state:
            print("  {0}: {1}. The system-disk and image-change flows require Stopped; "
                  "stopping the instance is a customer-side action that interrupts the "
                  "workload.".format(instance_id, state))
        else:
            print("  {0}: state not returned; ask the customer to read it from the "
                  "console list.".format(instance_id))

    if not args.facts_only:
        symptom = _auto_symptom(args, args.error_text)
        symptoms = [symptom] if symptom else list(
            C.INTENT_SYMPTOMS.get(args.intent or "", ()))
        if args.intent == "selection":
            _section("SELECTION RULES")
            _lines(["{0}: {1}".format(label, rule) for label, rule in C.SELECTION_RULES])
        if symptoms:
            print_playbook(symptoms)
        else:
            _section("GUIDANCE")
            print("  nothing routed yet. Ask the customer which operation was in front of "
                  "them: billing-method conversion, public IP or bandwidth billing, "
                  "cancellation, system-disk change, transfer, export or authorization. "
                  "Then re-run with --symptom or --intent.")
        if args.inventory or args.intent == "inventory":
            _section("INVENTORY")
            paid_rows = []
            for item in instances:
                instance_id = _cli.text(_cli.pick(item, ("InstanceId",)))
                attached = _instance_image_id(item)
                entry = verdicts.get(attached)
                if entry and _is_paid(entry[0], entry[2]):
                    paid_rows.append((instance_id, attached, entry[0]))
            print("  instances on a paid or Marketplace image: {0} of {1} visible"
                  .format(len(paid_rows), len(instances)))
            for instance_id, attached, verdict in paid_rows:
                image_name = verdicts[attached][2]["name"] or "-"
                print("    {0} -> {1} ({2}, {3})".format(
                    instance_id, attached, verdict, image_name))
            if paid_rows:
                print("  renewal exposure: each row above renews its image licence with "
                      "the instance, and renewal promotions do not cover that order.")
        print_help_docs()

    _section("CUSTOMER SELF-CHECK (not visible to any read-only API)")
    _lines(C.CUSTOMER_SELF_CHECK_ITEMS)

    _section("LIMITS AND DEGRADATIONS")
    _lines(C.DEGRADE_HINTS)
    _lines(notes)

    if not instances and not images:
        status = "FAIL" if notes else "DEGRADED"
        next_action = ("Collect the region identifier plus an instance or image "
                       "identifier from the customer and re-run; conclude nothing about an "
                       "image that was not resolved.")
    elif notes:
        status = "DEGRADED"
        next_action = ("Report the facts above, name the query that degraded, and ask the "
                       "first question of the routed playbook before giving any console "
                       "step.")
    else:
        status = "OK"
        next_action = ("Deliver the five-part answer: facts, rule, customer-side steps "
                       "with the risk notice, then re-check with this tool.")

    print("\nSTATUS: {0}".format(status))
    print("NEXT_ACTION: {0}".format(next_action))
    return 0 if status in ("OK", "DEGRADED") else 2


if __name__ == "__main__":
    sys.exit(main())
