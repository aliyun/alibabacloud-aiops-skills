#!/usr/bin/env python3
"""Single entry point of the alibabacloud-ecs-image-encryption-cross-account skill.

Read-only evidence collection for encrypted ECS custom images and the
cross-account limits that apply when such an image is shared or copied.

The script calls three read-only ECS actions and nothing else:
    ecs:DescribeImages           image list, status, progress, encryption evidence
    ecs:DescribeInstances        which instances use which image
    ecs:DescribeInstanceStatus   instance lifecycle state
plus the identity pre-check `aliyun sts get-caller-identity`.

Every mutating step (share, copy, export, launch, unshare) is deliberately
absent: this skill prints console guidance for the customer to perform, then
re-runs the same read-only queries to confirm the outcome.

Output contract: the report ends with `STATUS: OK|DEGRADED|FAIL` and
`NEXT_ACTION: ...`.

Examples:
    python scripts/image_cross_account_check.py --region-id cn-hangzhou \
        --image-id m-bp1xxxxx --intent share-encrypted
    python scripts/image_cross_account_check.py --region-id cn-hangzhou \
        --owner-alias others --intent launch-from-shared
    python scripts/image_cross_account_check.py --region-id cn-hangzhou \
        --instance-id i-bp1xxxxx --with-instances
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _cli import (  # noqa: E402
    CliError,
    call_caller_identity,
    call_ecs_read,
    mask_credentials,
    new_session_id,
    user_agent_for,
)
from _constants import (  # noqa: E402
    CONSOLE_IMAGE_PAGE,
    CONSOLE_QUOTA_PAGE,
    CONSOLE_RAM_PAGE,
    CONSOLE_TASK_PAGE,
    DOC_COPY_CUSTOM_IMAGE,
    DOC_CROSS_ACCOUNT_ENCRYPTED_SHARE,
    DOC_DESCRIBE_IMAGES,
    DOC_ECS_QUOTA_DETAIL,
    DOC_ENCRYPT_CUSTOM_IMAGES,
    DOC_EXPORT_CUSTOM_IMAGE,
    DOC_SHARE_CUSTOM_IMAGE,
    ERROR_IMAGE_OWNER_ID_UNSUPPORTED,
    ERROR_PUBLIC_IMAGE_ALIAS,
    IMAGE_OWNER_ALIASES,
    IMAGE_PAGE_SIZE,
    IMAGE_STATUS_DEFAULT_FILTER,
    IMAGE_STATUS_FILTER_ALL,
    INSTANCE_STATUS_PAGE_SIZE,
    KMS_POLICY_SERVICE_KEY,
    KMS_SERVICE_KEY_ALIAS,
    MAX_PAGES,
    QUOTA_CUSTOM_IMAGE_COUNT,
    QUOTA_SHARE_USER_COUNT,
    ROLE_SHARE_ENCRYPTED_IMAGE,
    ROLE_SHARE_ENCRYPTED_SNAPSHOT,
    SKILL_NAME,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
    TRUSTED_PRINCIPAL_SUFFIX,
)
from sts_token import account_label  # noqa: E402

REGION_PATTERN = re.compile(r"^[a-z][a-z0-9-]{2,40}$")
INTENTS = (
    "verify-presence",
    "share-encrypted",
    "copy-encrypted",
    "launch-from-shared",
    "export-blocked",
    "quota-check",
    "generic",
)

# Console guidance per intent. Facts come from the cited documents only;
# anything they do not cover is reported as unverified instead of guessed.
GUIDANCE = {
    "share-encrypted": (
        "Sharing an encrypted custom image (customer performs this; this skill does not):\n"
        "  1. Pre-authorisation is mandatory for encrypted images. In the SHARING account, "
        f"create the RAM role {ROLE_SHARE_ENCRYPTED_IMAGE} with an Alibaba Cloud account as "
        "trusted entity, then edit its trust policy so the recipient's ECS service principal "
        f"<recipient-account-id>{TRUSTED_PRINCIPAL_SUFFIX} may assume it "
        f"(console: {CONSOLE_RAM_PAGE}).\n"
        f"  2. Key permissions: if the image is encrypted with a customer master key, attach a "
        "custom policy granting kms:List* on acs:kms:<key-region>:<key-owner-uid>:key and "
        "kms:DescribeKey / kms:Encrypt / kms:Decrypt / kms:GenerateDataKey / kms:TagResource / "
        "kms:UntagResource on acs:kms:<key-region>:<key-owner-uid>:key/<key-id>. If it is "
        f"encrypted with the ECS service key ({KMS_SERVICE_KEY_ALIAS}), attach the system "
        f"policy {KMS_POLICY_SERVICE_KEY} instead.\n"
        "  3. Share from the owner side: ECS console > Images, pick the resource group and "
        f"region, Custom Images tab, Actions column > Share Image, enter the recipient main "
        f"account ID, tick the security confirmation, then confirm ({CONSOLE_IMAGE_PAGE}).\n"
        "  4. Scope: sharing is supported only within the SAME region, and only for the account's "
        "own custom images; an image shared to you cannot be shared again. To "
        "reach another region, copy the image there first and share from that region.\n"
        "  5. Recipient side: when launching from a shared encrypted image the disk encryption "
        "flag is fixed on and cannot be turned off; through the API the encryption parameter "
        "must be sent as true or the call fails. The recipient may choose its own key, and an "
        "account-level default encryption key takes precedence over the service key.\n"
        f"  Sources: {DOC_SHARE_CUSTOM_IMAGE} , {DOC_CROSS_ACCOUNT_ENCRYPTED_SHARE} , "
        f"{DOC_ENCRYPT_CUSTOM_IMAGES}\n"
    ),
    "copy-encrypted": (
        "Copying an encrypted custom image (customer performs this):\n"
        "  1. ECS console > Images > Custom Images tab > Actions column > Copy Image, then "
        f"choose the encrypted copy type ({CONSOLE_IMAGE_PAGE}).\n"
        "  2. An encrypted image can only be copied as an encrypted image; the copy direction "
        "encrypted-to-unencrypted does not exist, because encryption is irreversible.\n"
        "  3. The key for the copy must exist in the destination region, in that account. "
        "Without an explicit key the ECS service key is used, and already-encrypted snapshots "
        "keep their original key.\n"
        "  4. Re-encrypting copies take longer than plain copies and produce their own snapshots "
        "in the destination region, which are billed and persist independently of the source.\n"
        f"  5. Track it in Images or in Task Management ({CONSOLE_TASK_PAGE}); the image "
        "reaches Available at 100 percent and an in-flight Creating copy can be cancelled.\n"
        f"  Source: {DOC_ENCRYPT_CUSTOM_IMAGES} , {DOC_COPY_CUSTOM_IMAGE}\n"
    ),
    "launch-from-shared": (
        "Launching from a shared encrypted image (recipient account performs this):\n"
        "  1. In the RECIPIENT account, ECS console > Images, switch the region selector to the "
        f"region where the image was shared, and open the Shared Images tab ({CONSOLE_IMAGE_PAGE}). "
        "This skill cannot see that account, so ask the customer for a screenshot.\n"
        "  2. Launch from the instance purchase page; every disk backed by an encrypted snapshot "
        "of that image is encrypted by default and the option cannot be cleared; through the API "
        "the encryption parameter must be sent as true or the call fails.\n"
        "  3. If the recipient has an account-level default encryption key configured, that key "
        "wins over the service key.\n"
        "  4. If the shared image is absent from that tab, the usual causes are: a different "
        "region was selected, the owner shared to a different account ID, the owner has not "
        "granted the encrypted-share role, or the owner's side still shows the share as pending.\n"
        f"  Sources: {DOC_ENCRYPT_CUSTOM_IMAGES} , {DOC_SHARE_CUSTOM_IMAGE}\n"
    ),
    "export-blocked": (
        "Exporting or transferring an encrypted image:\n"
        "  1. Encrypted custom images cannot be exported, and neither can custom images based on "
        "Marketplace images nor Windows Server images. This is a documented limitation, not a "
        "fault to fix.\n"
        "  2. There is no decrypt-then-export path: encryption cannot be reversed. The supported "
        "route is to launch an instance from the encrypted image, migrate the needed data onto "
        "unencrypted disks, build a new unencrypted custom image from that instance, then export "
        "it through an OSS bucket in the same region.\n"
        "  3. If an export task failed with a name collision on the OSS object, change the bucket "
        "or the file-name prefix and retry.\n"
        f"  Source: {DOC_EXPORT_CUSTOM_IMAGE}\n"
    ),
    "quota-check": (
        "Quota and limit checks a customer can run:\n"
        f"  1. Open the ECS quota page ({CONSOLE_QUOTA_PAGE}) and read "
        f"'{QUOTA_CUSTOM_IMAGE_COUNT}' (custom images kept per region) and "
        f"'{QUOTA_SHARE_USER_COUNT}' (recipients a single custom image may be shared with); "
        "raise the limit from the same page if needed.\n"
        "  2. Sharing does not consume the recipient's custom-image quota; the sender owns that "
        "count.\n"
        "  3. A custom image that is currently shared stays in place until the share to that "
        "account is cancelled; cancelling the share is the prerequisite for any later clean-up "
        "of the image.\n"
        "  4. Cross-site sharing of a custom image derived from a Marketplace image between a "
        "China-site and an international-site account is not supported.\n"
        f"  Sources: {DOC_ECS_QUOTA_DETAIL} , "
        f"{DOC_SHARE_CUSTOM_IMAGE}\n"
    ),
}

GUIDANCE["generic"] = (
    "Next read-only steps: list the region's custom images "
    f"({CONSOLE_IMAGE_PAGE}, Custom Images tab), then re-run this script with --intent "
    "share-encrypted, copy-encrypted, launch-from-shared, export-blocked or quota-check.\n"
)


def parse_list(value):
    if not value:
        return []
    return [item.strip() for item in re.split(r"[,\s]+", value) if item.strip()]


def encryption_state(image):
    """Return (verdict, encrypted_count, mapping_count) from snapshot mappings."""
    mappings = (image.get("DiskDeviceMappings") or {}).get("DiskDeviceMapping") or []
    flags = [bool(mapping.get("Encrypted")) for mapping in mappings if "Encrypted" in mapping]
    total = len(mappings)
    if not flags:
        return "unknown (no Encrypted field in the response)", 0, total
    return ("encrypted" if any(flags) else "not encrypted"), sum(flags), total


def collect_images(session_id, region_id, args, limitations):
    """Page through the read-only image query and return the image records."""
    images = []
    page = 1
    total_reported = None
    while page <= MAX_PAGES:
        params = {
            "PageSize": IMAGE_PAGE_SIZE,
            "PageNumber": page,
            "Status": IMAGE_STATUS_DEFAULT_FILTER if args.available_only else IMAGE_STATUS_FILTER_ALL,
        }
        if len(args.image_id) == 1:
            params["ImageId"] = args.image_id[0]
        if args.image_name:
            params["ImageName"] = args.image_name
        if args.owner_alias:
            params["ImageOwnerAlias"] = args.owner_alias
        if args.peer_account_id and args.owner_alias == "others":
            params["ImageOwnerId"] = args.peer_account_id
        if args.resource_group_id:
            params["ResourceGroupId"] = args.resource_group_id
        params = {key: value for key, value in params.items() if value not in (None, "")}
        try:
            payload = call_ecs_read(session_id, "DescribeImages", region_id, params, args.timeout)
        except CliError as exc:
            limitations.append(f"DescribeImages page {page}: {exc}")
            if exc.is_permission_denied():
                limitations.append(
                    "Read action ecs:DescribeImages is missing for this principal; attach the "
                    "minimal policy from references/ram-policies.md (NoPermission / ImplicitDeny)"
                )
            break
        batch = (payload.get("Images") or {}).get("Image") or []
        images.extend(batch)
        total_reported = payload.get("TotalCount", total_reported)
        if not batch or len(images) >= int(total_reported or 0):
            break
        page += 1
    if len(images) >= MAX_PAGES * IMAGE_PAGE_SIZE:
        limitations.append("image paging stopped at the built-in page cap; results are partial")
    return images


def filter_by_ids(images, wanted_ids):
    """Match the requested ids against the collected list.

    With a single id the API already filters server side. With several ids the
    query is unfiltered (ImageId is single-valued), so an id absent from this
    account and region legitimately yields no match.
    """
    if not wanted_ids:
        return images
    wanted = set(wanted_ids)
    return [image for image in images if image.get("ImageId") in wanted]


def render_image(image, lines):
    verdict, encrypted_count, mapping_count = encryption_state(image)
    lines.append(f"  ImageId: {image.get('ImageId', '-')}")
    lines.append(f"    name={image.get('ImageName', '-')} status={image.get('Status', '-')} "
                 f"progress={image.get('Progress', '-')} usable={image.get('Usable', '-')}")
    lines.append(f"    source={image.get('ImageOwnerAlias', '-')} "
                 f"ownerAccountId={image.get('ImageOwnerId', '-')} "
                 f"public={image.get('IsPublic', '-')}")
    lines.append(f"    encryption={verdict} "
                 f"({encrypted_count}/{mapping_count} snapshot mappings report Encrypted=true)")
    lines.append(f"    everSharedOut={image.get('IsSelfShared', '-')} "
                 f"producedByCopy={image.get('IsCopied', '-')} "
                 f"inUse={image.get('Usage', '-')}")
    lines.append(f"    os={image.get('OSNameEn') or image.get('OSName', '-')} "
                 f"osType={image.get('OSType', '-')} arch={image.get('Architecture', '-')} "
                 f"sizeGiB={image.get('Size', '-')}")
    mappings = (image.get("DiskDeviceMappings") or {}).get("DiskDeviceMapping") or []
    for mapping in mappings[:10]:
        lines.append(
            f"    mapping type={mapping.get('Type', '-')} device={mapping.get('Device', '-')} "
            f"snapshot={mapping.get('SnapshotId', '-')} encrypted={mapping.get('Encrypted', 'absent')} "
            f"copyProgress={mapping.get('Progress', '-')} remainSeconds={mapping.get('RemainTime', '-')}"
        )
    if len(mappings) > 10:
        lines.append(f"    ... {len(mappings) - 10} more snapshot mappings not listed")
    return verdict


def collect_instance_context(session_id, region_id, args, limitations, image_ids):
    """Read the instance side; returns (instances, statuses, used_by)."""
    instances, statuses, used_by = [], [], {}
    if args.instance_id:
        params = {"InstanceIds": json.dumps(args.instance_id)}
        try:
            payload = call_ecs_read(session_id, "DescribeInstances", region_id, params, args.timeout)
            instances = (payload.get("Instances") or {}).get("Instance") or []
        except CliError as exc:
            limitations.append(f"DescribeInstances by instance id: {exc}")
    if args.with_instances and image_ids:
        probe = image_ids[:10]
        if len(image_ids) > len(probe):
            limitations.append(
                f"instance lookup capped at {len(probe)} of {len(image_ids)} matched images; "
                "the remaining images were not probed for instances"
            )
        for image_id in probe:
            try:
                payload = call_ecs_read(
                    session_id, "DescribeInstances", region_id,
                    {"ImageId": image_id, "PageSize": 50}, args.timeout,
                )
                used_by[image_id] = (payload.get("Instances") or {}).get("Instance") or []
            except CliError as exc:
                limitations.append(f"DescribeInstances by image {image_id}: {exc}")
    targets = [instance.get("InstanceId") for instance in instances if instance.get("InstanceId")]
    for bucket in used_by.values():
        targets.extend(instance.get("InstanceId") for instance in bucket if instance.get("InstanceId"))
    targets = [target for target in dict.fromkeys(targets) if target][:INSTANCE_STATUS_PAGE_SIZE]
    if targets:
        params = {f"InstanceId.{index + 1}": target for index, target in enumerate(targets)}
        params["PageSize"] = INSTANCE_STATUS_PAGE_SIZE
        try:
            payload = call_ecs_read(
                session_id, "DescribeInstanceStatus", region_id, params, args.timeout)
            statuses = (payload.get("InstanceStatuses") or {}).get("InstanceStatus") or []
        except CliError as exc:
            limitations.append(f"DescribeInstanceStatus: {exc}")
    return instances, statuses, used_by


def build_findings(args, images, verdicts, limitations):
    """Route the evidence to findings; returns (findings, next_action)."""
    findings, next_action = [], "Report the evidence above to the customer."
    if not images:
        queried = IMAGE_STATUS_DEFAULT_FILTER if args.available_only else IMAGE_STATUS_FILTER_ALL
        findings.append(
            "No image matched in this region under this account. This run filtered on "
            f"Status='{queried}'."
            + (" The API default is 'Available', which hides images that are still being "
               "produced or queued; drop --available-only to query 'ALL' before concluding "
               "the image is missing."
               if args.available_only else
               " 'ALL' was used, so an image that is still being produced or queued would "
               "have appeared.")
        )
        findings.append(
            f"Likely causes to check with the customer, in order: wrong region selector in the "
            f"console, wrong account (peer-owned images are only visible from the peer's own "
            f"credentials), image id typed as a name, or a query that mixed parameters and hit "
            f"{ERROR_IMAGE_OWNER_ID_UNSUPPORTED} / {ERROR_PUBLIC_IMAGE_ALIAS}."
        )
        next_action = (
            "Ask the customer to switch the console region selector and re-run this script per "
            "candidate region; if the image belongs to another account, ask for evidence taken in "
            "that account (see references/customer-selfcheck.md)."
        )
        return findings, next_action

    encrypted = [image for image in images if verdicts.get(image.get("ImageId")) == "encrypted"]
    plain = [image for image in images if verdicts.get(image.get("ImageId")) == "not encrypted"]
    unknown = [image for image in images if str(verdicts.get(image.get("ImageId"))).startswith("unknown")]

    def is_busy(image):
        progress = str(image.get("Progress", "")).rstrip("%")
        in_flight = progress.replace(".", "", 1).isdigit() and float(progress or 100) < 100
        return image.get("Status") in ("Creating", "Waiting") or (
            in_flight and image.get("Status") != "Available")

    busy = [image for image in images if is_busy(image)]
    failed = [image for image in images if image.get("Status") in ("CreateFailed", "UnAvailable", "Deprecated")]

    if encrypted:
        findings.append(
            f"{len(encrypted)} image(s) carry at least one encrypted snapshot mapping, so the "
            "encrypted-share path applies: same region only, and the sharing account must own "
            f"{ROLE_SHARE_ENCRYPTED_IMAGE} (or {ROLE_SHARE_ENCRYPTED_SNAPSHOT} for the underlying "
            "snapshots) with the recipient ECS service in its trust policy."
        )
    if plain:
        findings.append(
            f"{len(plain)} image(s) report no encrypted mapping. If the customer's question is "
            "about those, this symptom axis does not apply and the request belongs to the "
            "unencrypted image region-to-region copy and OSS image transfer skill (see "
            "references/boundary-and-handoff.md)."
        )
    if unknown:
        findings.append(
            f"{len(unknown)} image(s) returned no Encrypted field, so encryption state is "
            "UNVERIFIED here; confirm it in the console disk/snapshot view instead of assuming."
        )
    if busy:
        findings.append(
            f"{len(busy)} image(s) are still produced or queued (status Creating/Waiting or "
            "progress below 100%); a copy task reports per-mapping progress and remaining seconds."
        )
    if failed:
        findings.append(
            f"{len(failed)} image(s) are in a non-usable state "
            "(CreateFailed/UnAvailable/Deprecated); that is an image production problem, not a "
            "cross-account encryption limit, and is handed off."
        )
    shared_out = [image for image in images if str(image.get("IsSelfShared")).lower() == "true"]
    if shared_out:
        findings.append(
            f"{len(shared_out)} image(s) were already shared out at least once "
            "(IsSelfShared=true). Only the owner account can inspect or cancel that grant."
        )
    received = [image for image in images if image.get("ImageOwnerAlias") == "others"]
    if received:
        findings.append(
            f"{len(received)} image(s) come from another account (source=others). They cannot be "
            "shared again by this account, and launching from an encrypted one requires the "
            "encryption parameter to be sent as true."
        )

    if args.intent == "share-encrypted":
        next_action = (
            "Have the owner account complete the encrypted-share authorisation and the console "
            "share step from references/guide-steps.md, then re-run this script and ask for the "
            "recipient-side Shared Images tab screenshot."
        )
    elif args.intent == "launch-from-shared":
        next_action = (
            "Hand the recipient-account checklist in references/customer-selfcheck.md to the "
            "customer; re-check this account's side only for the grant and the region."
        )
    elif args.intent == "copy-encrypted":
        next_action = (
            "Ask the customer to run the encrypted copy in the console with a key that exists in "
            "the destination region, then re-run this script in the destination region."
        )
    elif args.intent == "export-blocked":
        next_action = (
            "State the documented export exclusion for encrypted images and offer the "
            "instance-then-unencrypted-image route; do not attempt any export here."
        )
    elif args.intent == "quota-check":
        next_action = (
            "Read the two image quota items in the ECS quota page and raise them from Quota "
            "Center if the customer is at the ceiling."
        )
    elif limitations:
        next_action = "Resolve the recorded query limitations, then re-run before advising."
    return findings, next_action


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only evidence and console guidance for encrypted ECS custom images "
                    "shared or copied across accounts.",
    )
    parser.add_argument("--region-id", required=True,
                        help="Region whose images are inspected (every query is region-scoped)")
    parser.add_argument("--image-id", help="Comma-separated image ids, e.g. m-bp1xxxx,m-bp1yyyy")
    parser.add_argument("--image-name", help="Image name, fuzzy matched by the API")
    parser.add_argument("--owner-alias", choices=IMAGE_OWNER_ALIASES,
                        help="Image source filter: self (own custom), others (shared/community), "
                             "system, marketplace")
    parser.add_argument("--peer-account-id",
                         help="Recipient/owner main account ID; used only as a query filter and "
                              "as a placeholder in guidance, never verified by this skill")
    parser.add_argument("--resource-group-id", help="Restrict the image query to one resource group")
    parser.add_argument("--instance-id", help="Comma-separated instance ids for instance context")
    parser.add_argument("--with-instances", action="store_true",
                        help="Also list instances that were launched from each matched image")
    parser.add_argument("--intent", choices=INTENTS, default="generic",
                        help="What the customer is trying to do; selects the guidance branch")
    parser.add_argument("--available-only", action="store_true",
                        help=f"Query only status {IMAGE_STATUS_DEFAULT_FILTER} instead of ALL")
    parser.add_argument("--skip-identity", action="store_true",
                        help="Do not run the caller-identity pre-check")
    parser.add_argument("--timeout", type=int, default=90,
                        help="Per-call timeout in seconds for every CLI invocation")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable evidence only")
    args = parser.parse_args(argv)

    if not REGION_PATTERN.match(args.region_id):
        print("STATUS: FAIL")
        print("NEXT_ACTION: --region-id must be a region id such as cn-hangzhou; "
              "callers choose it explicitly, there is no silent default.")
        print(f"[ERROR] InvalidParameter: RegionId={mask_credentials(args.region_id)!r}")
        return 2

    args.image_id = parse_list(args.image_id)
    args.instance_id = parse_list(args.instance_id)
    session_id = new_session_id()
    limitations = []
    identity = {}

    if not args.skip_identity:
        try:
            identity = call_caller_identity(session_id, args.timeout)
        except CliError as exc:
            limitations.append(f"caller identity: {exc}")
            if exc.is_permission_denied():
                limitations.append(
                    "Identity call denied (NoPermission / ImplicitDeny): the principal cannot even "
                    "confirm its own account, so the account attribution below is unavailable."
                )

    images = collect_images(session_id, args.region_id, args, limitations)
    matched = filter_by_ids(images, args.image_id)
    verdicts = {image.get("ImageId"): encryption_state(image)[0] for image in matched}
    instances, statuses, used_by = collect_instance_context(
        session_id, args.region_id, args, limitations,
        [image.get("ImageId") for image in matched if image.get("ImageId")])
    findings, next_action = build_findings(args, matched, verdicts, limitations)

    if limitations and not images:
        resolved_status = STATUS_FAIL
    elif limitations or (not identity and not args.skip_identity):
        resolved_status = STATUS_DEGRADED
    else:
        resolved_status = STATUS_OK

    evidence = {
        "skill": SKILL_NAME,
        "sessionId": session_id,
        "userAgent": user_agent_for(session_id),
        "regionId": args.region_id,
        "intent": args.intent,
        "account": account_label(identity) if identity else "unknown",
        "query": {
            "statusFilter": IMAGE_STATUS_DEFAULT_FILTER if args.available_only else IMAGE_STATUS_FILTER_ALL,
            "imageIds": args.image_id,
            "imageOwnerAlias": args.owner_alias,
        },
        "images": [
            {
                "imageId": image.get("ImageId"),
                "imageName": image.get("ImageName"),
                "status": image.get("Status"),
                "progress": image.get("Progress"),
                "encryption": verdicts.get(image.get("ImageId")),
                "imageOwnerAlias": image.get("ImageOwnerAlias"),
                "imageOwnerId": image.get("ImageOwnerId"),
                "isSelfShared": image.get("IsSelfShared"),
                "isCopied": image.get("IsCopied"),
                "osType": image.get("OSType"),
                "architecture": image.get("Architecture"),
                "sizeGiB": image.get("Size"),
                "usage": image.get("Usage"),
                "creationTime": image.get("CreationTime"),
                "snapshotMappings": [
                    {
                        "type": mapping.get("Type"),
                        "device": mapping.get("Device"),
                        "snapshotId": mapping.get("SnapshotId"),
                        "encrypted": mapping.get("Encrypted", "absent"),
                        "copyProgress": mapping.get("Progress"),
                        "remainSeconds": mapping.get("RemainTime"),
                    }
                    for mapping in (image.get("DiskDeviceMappings") or {}).get("DiskDeviceMapping") or []
                ],
            }
            for image in matched
        ],
        "instances": [
            {
                "instanceId": instance.get("InstanceId"),
                "instanceName": instance.get("InstanceName"),
                "imageId": instance.get("ImageId"),
                "status": instance.get("Status"),
                "instanceType": instance.get("InstanceType"),
                "osType": instance.get("OSType"),
            }
            for instance in instances
        ],
        "instanceStatuses": [
            {"instanceId": item.get("InstanceId"), "status": item.get("Status")}
            for item in statuses
        ],
        "usedByInstances": {
            image_id: [instance.get("InstanceId") for instance in bucket]
            for image_id, bucket in used_by.items()
        },
        "findings": findings,
        "limitations": limitations,
        "identityCheckSkipped": bool(args.skip_identity),
        "status": resolved_status,
        "nextAction": next_action,
    }

    if args.json:
        print(json.dumps(evidence, indent=2, ensure_ascii=False))
        return 0 if evidence["status"] != STATUS_FAIL else 1

    lines = [
        "=" * 72,
        "ECS encrypted image / cross-account read-only check",
        "=" * 72,
        f"skill        : {SKILL_NAME}",
        f"session      : {session_id}",
        f"user-agent   : {user_agent_for(session_id)}",
        f"region       : {args.region_id} (queried explicitly; results are region-scoped)",
        f"intent       : {args.intent}",
        f"caller       : {evidence['account']}",
        "",
        "[1] Image evidence (read-only: DescribeImages)",
        f"    matched {len(matched)} image(s) after filtering; status filter "
        f"'{evidence['query']['statusFilter']}'",
    ]
    if not matched:
        lines.append("    (no image matched - see findings for the candidate causes)")
    for image in matched:
        render_image(image, lines)
    lines += ["", "[2] Instance context (read-only: DescribeInstances / DescribeInstanceStatus)"]
    if not (instances or statuses or used_by):
        lines.append("    not requested, or unavailable; pass --with-instances / --instance-id")
    for instance in instances:
        lines.append(f"    {instance.get('InstanceId')} image={instance.get('ImageId')} "
                     f"status={instance.get('Status')} type={instance.get('InstanceType')} "
                     f"os={instance.get('OSType')}")
    for image_id, bucket in used_by.items():
        lines.append(f"    image {image_id} is used by {len(bucket)} instance(s) in this region: "
                     + ", ".join(str(item.get("InstanceId")) for item in bucket[:10])
                     + (" ..." if len(bucket) > 10 else ""))
    for item in statuses:
        lines.append(f"    status {item.get('InstanceId')} = {item.get('Status')}")
    lines += ["", "[3] Findings"]
    lines += [f"    - {finding}" for finding in findings] or ["    - nothing conclusive"]
    lines += ["", "[4] Guidance (the customer performs every action; this skill changes nothing)",
              GUIDANCE[args.intent].rstrip(), ""]
    lines += ["[5] Boundary of this check",
              "    - only resources of the account behind the default credential chain are visible;",
              "      the peer account's view can never be confirmed from here.",
              "    - only the selected region is covered; an image copied or shared elsewhere",
              "      needs one run per region.",
              "    - the KMS key behind an encrypted mapping is not returned by the queried",
              "      actions; ask the customer to read it in the console.",
              "    - no in-guest check is performed: this skill never runs commands inside an",
              "      instance; ask for read-only output to be pasted back instead.",
              f"    - field semantics used above (Encrypted, IsSelfShared, Progress) are defined in",
              f"      the API reference: {DOC_DESCRIBE_IMAGES}",
              ""]
    if limitations:
        lines += ["[6] Limitations recorded during this run"]
        lines += [f"    - {mask_credentials(item)}" for item in limitations]
        lines.append("")
    lines += [f"STATUS: {evidence['status']}", f"NEXT_ACTION: {next_action}"]
    print("\n".join(lines))
    return 0 if evidence["status"] != STATUS_FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
