#!/usr/bin/env python3
"""Turn collected evidence into a visibility verdict and a customer-facing report.

Two jobs live here:
  * parse the text a guest diagnostic printed, without pretending the layout is stable
    (token-based, tolerant, always accompanied by the raw text in the report);
  * evaluate the five-step chain from the cloud and guest facts and render the report.

Nothing in this module calls the platform, and nothing in it changes anything.
"""

import json
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from _constants import (
    FINDING_DEVICE_NOT_ENUMERATED,
    FINDING_DISK_ATTACHED_TO_THIS_INSTANCE,
    FINDING_DISK_NOT_ATTACHED,
    FINDING_DISK_NOT_FOUND_IN_REGION,
    FINDING_DISK_ON_OTHER_INSTANCE,
    FINDING_EXPLANATION,
    FINDING_FILESYSTEM_NOT_MOUNTED,
    FINDING_MULTI_ATTACH,
    FINDING_NEXT_STEP,
    FINDING_NO_FILESYSTEM,
    FINDING_NO_PARTITION,
    FINDING_MOUNT_POINT_SHADOWING,
    FINDING_MOUNTED_AND_READABLE,
    FINDING_PROBE_NOT_RUN,
    FINDING_PROBE_UNAVAILABLE,
    FINDING_SUBSCRIPTION_PLACEMENT_LOCKED,
    FINDING_WINDOWS_VOLUME_OFFLINE_OR_UNMAPPED,
    FINDING_WINDOWS_VOLUME_TARGET_AMBIGUOUS,
    VISIBILITY_CHAIN,
    WINDOWS_CHAIN_STOP,
)

# Filesystem types seen often enough on ECS guests to be recognised as a column value
# rather than guessed at by position.
KNOWN_FSTYPES = (
    "ext2", "ext3", "ext4", "xfs", "btrfs", "vfat", "fat32", "ntfs", "exfat", "swap",
    "iso9660", "tmpfs", "overlay", "squashfs", "nfs", "nfs4", "cifs", "fuse", "gfs2", "reiserfs",
)

_TREE_PREFIX = re.compile(r"^[├└│─`|+\- ]+")
_NUMBERED = re.compile(r"^\d+(\.\d+)?$")
_GB_TOKEN = re.compile(r"^(\d+(?:\.\d+)?)\s*([KMGT]?)B?$", re.IGNORECASE)
_UUID_TOKEN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                         r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def to_gib(raw: Any) -> Optional[float]:
    """Best-effort conversion of a size token to GiB. Returns None when not a size."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip().upper().replace(",", "")
    if not text:
        return None
    match = re.match(r"^(\d+(?:\.\d+)?)\s*([KMGT]?)I?B?$", text)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2)
    factors = {"K": 1.0 / 1024 / 1024, "M": 1.0 / 1024, "G": 1.0, "T": 1024.0, "": None}
    if unit == "":
        # A bare number larger than a GiB is almost certainly bytes, otherwise GiB.
        return value / 1073741824.0 if value > 1073741824 else value
    return value * factors[unit]


def sizes_match(a: Optional[float], b: Optional[float]) -> bool:
    if a is None or b is None or a <= 0 or b <= 0:
        return False
    return abs(a - b) <= max(1.0, 0.03 * max(a, b))


def _is_mount_target(token: str) -> bool:
    return token.startswith("/") and not re.match(r"^[0-9a-fA-F-]+$", token)


def parse_lsblk(text: str) -> List[Dict[str, Any]]:
    """Parse `lsblk` and `lsblk -f` output into one record per device or partition.

    Columns are located by content, not by offset, because the column set differs
    between the two invocations and between util-linux versions.
    """
    devices: List[Dict[str, Any]] = []
    for line in (text or "").splitlines():
        if not line.strip() or line.lstrip().startswith(("NAME", "KNAME")):
            continue
        indent = len(line) - len(line.lstrip())
        body = _TREE_PREFIX.sub("", line.strip())
        tokens = body.split()
        if not tokens:
            continue
        name = tokens[0]
        if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", name):
            continue
        record: Dict[str, Any] = {
            "name": name,
            "size_gib": None,
            "fstype": "",
            "mountpoint": "",
            "uuid": "",
            "is_child": bool(indent) or bool(_TREE_PREFIX.match(line.strip())),
            "kind": "",
            "raw": line.rstrip(),
        }
        for token in tokens[1:]:
            lowered = token.lower()
            if lowered in KNOWN_FSTYPES and not record["fstype"]:
                record["fstype"] = lowered
            elif _UUID_TOKEN.match(token) and not record["uuid"]:
                record["uuid"] = token
            elif _is_mount_target(token) and not record["mountpoint"]:
                record["mountpoint"] = token
            elif _GB_TOKEN.match(token) and record["size_gib"] is None and to_gib(token):
                record["size_gib"] = to_gib(token)
            elif lowered in ("disk", "part", "lvm", "crypt") and not record["kind"]:
                record["kind"] = lowered
        devices.append(record)
    return devices


def parse_df(text: str) -> List[Dict[str, Any]]:
    """Parse `df -h` into mount records: source device plus the mounted path."""
    mounts: List[Dict[str, Any]] = []
    for line in (text or "").splitlines():
        tokens = line.split()
        if len(tokens) < 6 or tokens[0].lower() == "filesystem":
            continue
        device = tokens[0]
        mountpoint = " ".join(tokens[5:])
        if not device.startswith("/") and not any(device.startswith(prefix) for prefix in ("udev", "tmpfs")):
            continue
        mounts.append({"device": device, "mountpoint": mountpoint, "raw": line.rstrip()})
    return mounts


def parse_findmnt(text: str) -> List[Dict[str, Any]]:
    """Parse `findmnt` output (TARGET SOURCE FSTYPE ...) into mount records."""
    mounts: List[Dict[str, Any]] = []
    for line in (text or "").splitlines():
        body = _TREE_PREFIX.sub("", line.strip())
        tokens = body.split()
        if len(tokens) < 2 or tokens[0].lower() == "target":
            continue
        target, source = tokens[0], tokens[1]
        if not target.startswith("/"):
            continue
        fstype = tokens[2].lower() if len(tokens) > 2 and tokens[2].lower() in KNOWN_FSTYPES else ""
        mounts.append({"device": source, "mountpoint": target, "fstype": fstype, "raw": line.rstrip()})
    return mounts


def parse_proc_partitions(text: str) -> List[Dict[str, Any]]:
    """Parse /proc/partitions: major minor #blocks name."""
    devices: List[Dict[str, Any]] = []
    for line in (text or "").splitlines():
        tokens = line.split()
        if len(tokens) != 4 or not _NUMBERED.match(tokens[0]) or not _NUMBERED.match(tokens[1]):
            continue
        try:
            blocks = float(tokens[2])
        except ValueError:
            continue
        devices.append({
            "name": tokens[3],
            "size_gib": blocks / 1048576.0,
            "fstype": "",
            "mountpoint": "",
            "is_child": re.search(r"\d+$", tokens[3]) is not None,
            "kind": "",
            "raw": line.rstrip(),
        })
    return devices


def parse_windows_volumes(text: str) -> List[Dict[str, Any]]:
    """Parse `Get-Volume` / `Get-PSDrive` tables into volume records."""
    volumes: List[Dict[str, Any]] = []
    for line in (text or "").splitlines():
        tokens = line.split()
        if len(tokens) < 2:
            continue
        lowered = [token.lower() for token in tokens]
        if "filesystem" in lowered and "operationalstatus" in lowered:
            continue
        if set(tokens[0]) <= set("-=" ):
            continue
        record: Dict[str, Any] = {
            "name": tokens[0],
            "size_gib": None,
            "fstype": "",
            "mountpoint": "",
            "is_child": False,
            "kind": "volume",
            "health": "",
            "operational": "",
            "raw": line.rstrip(),
        }
        for token in tokens[1:]:
            low = token.lower()
            if low in KNOWN_FSTYPES:
                record["fstype"] = low
            elif low in ("healthy", "offline", "online", "ok", "missing", "unknown", "regenerating"):
                record["health"] = record["health"] or low
                if low in ("offline", "online"):
                    record["operational"] = low
                elif low == "ok":
                    record["operational"] = record["operational"] or "online"
            elif re.match(r"^[A-Za-z]:$", token):
                record["mountpoint"] = token
            elif record["size_gib"] is None and to_gib(token) is not None:
                record["size_gib"] = to_gib(token)
        if re.match(r"^[A-Za-z]:$", record["name"]):
            record["mountpoint"] = record["name"]
        elif re.match(r"^[A-Za-z]$", record["name"]):
            record["mountpoint"] = record["name"] + ":"
        if record["fstype"] or record["mountpoint"] or record["operational"]:
            volumes.append(record)
    return volumes


def parse_windows_disks(text: str) -> List[Dict[str, Any]]:
    """Parse `Get-Disk | Select Number,SerialNumber,OperationalStatus | ConvertTo-Json`.

    The cloud disk SerialNumber equals the Windows disk serial (live-verified),
    so this is the join key that lets a specific disk be isolated even when several
    volumes share its size. Tolerates a single object or an array.
    """
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return []
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []
    disks: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        serial = str(item.get("SerialNumber") or "").strip()
        number = item.get("Number")
        status = item.get("OperationalStatus")
        if isinstance(status, str):
            operational = status.strip().lower()
        elif isinstance(status, int):
            operational = {0: "online", 1: "offline"}.get(status, "unknown")
        else:
            operational = "unknown"
        if serial and number is not None:
            disks.append({"number": number, "serial": serial, "operational": operational})
    return disks


def parse_windows_partitions(text: str) -> List[Dict[str, Any]]:
    """Parse `Get-Partition | Select DiskNumber,DriveLetter | ConvertTo-Json`.

    Maps a Windows disk number to its drive letter(s); a partition with no letter
    (offline disk, or a reserved partition) carries null and is kept as empty.
    """
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return []
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []
    partitions: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        disk_number = item.get("DiskNumber")
        letter = item.get("DriveLetter")
        letter = str(letter).strip().upper() if letter else ""
        if disk_number is not None:
            partitions.append({"disk_number": disk_number, "drive_letter": letter})
    return partitions


def merge_device_rows(devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fold the rows several invocations report for one device into a single row.

    `lsblk` carries SIZE and TYPE but no FSTYPE; `lsblk -f` carries FSTYPE and UUID
    but no SIZE. Keeping both rows means the size filter selects the FSTYPE-less
    copy, so a whole-disk filesystem reads as "no filesystem" and the guidance
    tells the customer to mkfs a disk that already holds data.
    """
    merged: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for row in devices:
        name = str(row.get("name") or "")
        if not name:
            continue
        if name not in merged:
            merged[name] = dict(row)
            order.append(name)
            continue
        kept = merged[name]
        for field in ("size_gib", "fstype", "mountpoint", "kind", "uuid", "label"):
            if not kept.get(field) and row.get(field):
                kept[field] = row[field]
        kept["is_child"] = bool(kept.get("is_child")) or bool(row.get("is_child"))
        if row.get("fstype") and row.get("raw"):
            kept["raw"] = row["raw"]
    return [merged[name] for name in order]


def parse_guest_results(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge the output of every collected command into one guest view."""
    view: Dict[str, Any] = {"devices": [], "mounts": [], "volumes": [], "commands": [], "raw": {},
                            "windows_disks": [], "windows_partitions": [],
                            "collected": False, "gaps": []}
    view["source"] = str(payload.get("source") or "") if payload else ""
    if not payload:
        return view
    items: Sequence[Dict[str, Any]] = payload.get("results") or []
    if not items and isinstance(payload.get("output"), str):
        items = [{"command": payload.get("command", ""), "output": payload["output"]}]
    for item in items:
        command = str(item.get("command", ""))
        output = str(item.get("output", ""))
        view["commands"].append({"command": command, "state": item.get("state", "")})
        key = command or "command-%d" % len(view["raw"])
        if key in view["raw"] and output:
            view["raw"][key] = (view["raw"][key] + "\n" + output).strip()
        else:
            view["raw"][key] = output
        if item.get("errors"):
            view["gaps"].extend("%s (%s)" % (error, command) for error in item["errors"])
        lowered = command.lower()
        if "lsblk" in lowered:
            view["devices"].extend(parse_lsblk(output))
        elif "partitions" in lowered:
            view["devices"].extend(parse_proc_partitions(output))
        elif lowered.startswith("df"):
            view["mounts"].extend(parse_df(output))
        elif "findmnt" in lowered:
            view["mounts"].extend(parse_findmnt(output))
        elif lowered.startswith("get-volume") or lowered.startswith("get-psdrive") or "fsutil" in lowered:
            view["volumes"].extend(parse_windows_volumes(output))
        elif lowered.startswith("get-disk"):
            view["windows_disks"].extend(parse_windows_disks(output))
        elif lowered.startswith("get-partition"):
            view["windows_partitions"].extend(parse_windows_partitions(output))
    view["devices"] = merge_device_rows(view["devices"])
    view["collected"] = bool(view["devices"] or view["mounts"] or view["volumes"]
                             or view["windows_disks"])
    if not view["collected"]:
        view["gaps"].append("No guest device, mount or volume rows could be read from the collected output.")
    return view


def _attached_instances(record: Dict[str, Any]) -> List[str]:
    instances: List[str] = []
    direct = record.get("InstanceId")
    if isinstance(direct, str) and direct:
        instances.append(direct)
    for attachment in _attachment_rows(record):
        value = attachment.get("InstanceId")
        if isinstance(value, str) and value and value not in instances:
            instances.append(value)
    return instances


def _attachment_rows(record: Any) -> List[Dict[str, Any]]:
    """Collect attachment rows wherever the response nests them."""
    rows: List[Dict[str, Any]] = []
    if isinstance(record, dict):
        for key, value in record.items():
            if str(key).lower() == "attachment" and isinstance(value, list):
                rows.extend(item for item in value if isinstance(item, dict))
            else:
                rows.extend(_attachment_rows(value))
    elif isinstance(record, list):
        for item in record:
            rows.extend(_attachment_rows(item))
    return rows


def _device_of(record: Dict[str, Any]) -> str:
    for attachment in _attachment_rows(record):
        value = attachment.get("Device")
        if isinstance(value, str) and value:
            return value
    value = record.get("Device")
    return value if isinstance(value, str) else ""


def extract_disk_facts(record: Dict[str, Any]) -> Dict[str, Any]:
    """Pull the fields the chain needs, reporting absence instead of assuming a name."""
    return {
        "disk_id": str(record.get("DiskId") or record.get("diskId") or ""),
        "size_gib": to_gib(record.get("Size")),
        "disk_type": str(record.get("Type") or ""),
        "category": str(record.get("Category") or ""),
        "status": str(record.get("Status") or ""),
        "attached_instances": _attached_instances(record),
        "cloud_device": _device_of(record),
        "portable": record.get("Portable"),
        "billing": str(record.get("DiskChargeType") or record.get("BillingType") or ""),
        "delete_with_instance": record.get("DeleteWithInstance"),
        "serial": str(record.get("SerialNumber") or ""),
        "multi_attach": str(record.get("MultiAttach") or ""),
        "raw": record,
    }


def extract_instance_facts(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "instance_id": str(record.get("InstanceId") or ""),
        "status": str(record.get("Status") or ""),
        "instance_type": str(record.get("InstanceType") or ""),
        "os_hint": str(record.get("OSName") or record.get("OSType") or record.get("OsName") or ""),
        "zone_id": str(record.get("ZoneId") or ""),
        "raw": record,
    }


def os_family_from(instance_facts: Dict[str, Any]) -> str:
    hint = str(instance_facts.get("os_hint", "")).lower()
    if "windows" in hint:
        return "windows"
    if any(token in hint for token in ("linux", "centos", "ubuntu", "debian", "alibaba cloud linux",
                                       "anolis", "suse", "coreos", "fedora")):
        return "linux"
    return ""


def _candidates(devices: List[Dict[str, Any]], size_gib: Optional[float]) -> List[Dict[str, Any]]:
    if size_gib is None:
        return []
    return [device for device in devices
            if not device["is_child"] and device["kind"] in ("", "disk", "volume")
            and sizes_match(device["size_gib"], size_gib)]


def _guest_device_basename(cloud_device: str) -> str:
    """Map a control-plane device name to the bare guest device name. The cloud
    reports xen-style /dev/xvdb while a virtio guest enumerates /dev/vdb; NVMe
    namespaces (/dev/nvme1n1) keep their name. Used only to disambiguate."""
    name = (cloud_device or "").rstrip("/").split("/")[-1]
    if name.startswith("xvd"):
        return "vd" + name[3:]
    return name


def _narrow_by_cloud_device(candidates: List[Dict[str, Any]],
                            cloud_device: str) -> List[Dict[str, Any]]:
    """When several guest devices share the disk's size (e.g. a 20G system disk
    and a 20G data disk), size alone cannot tell them apart and a mount on the
    system disk leaks onto the data disk. Prefer the candidate whose name matches
    the cloud device; fall back to the size set when the name does not align."""
    if len(candidates) <= 1:
        return candidates
    target = _guest_device_basename(cloud_device)
    if not target:
        return candidates
    matched = [device for device in candidates if device["name"] == target]
    return matched or candidates


def _mount_for(devices: List[Dict[str, Any]], mounts: List[Dict[str, Any]],
               candidate_names: Iterable[str]) -> List[Dict[str, Any]]:
    # lsblk/proc report bare names (vda1, centos-root) while df/findmnt report
    # the kernel source path (/dev/vda1, /dev/mapper/centos-root). Compare on the
    # basename so a mounted filesystem is actually attributed to its device --
    # stripping only the leading slash left "dev/vda1" and never matched, so
    # every mounted data disk was wrongly reported as not mounted.
    def _base(tok: str) -> str:
        return tok.rstrip("/").split("/")[-1]

    names = {_base(name) for name in candidate_names}
    hits: List[Dict[str, Any]] = []
    for mount in mounts:
        source = _base(mount["device"])
        base = re.sub(r"\d+$", "", source)
        if source in names or base in names:
            hits.append(mount)
    return hits


def evaluate_disk(disk: Dict[str, Any], instance_id: str, guest: Dict[str, Any],
                  os_family: str, symptom: str) -> Dict[str, Any]:
    """Return the chain verdict for one disk: findings, where it stops, and the manual step."""
    findings: List[str] = []
    evidence: Dict[str, Any] = {"disk_id": disk["disk_id"], "size_gib": disk["size_gib"]}

    if not disk["disk_id"]:
        findings.append(FINDING_DISK_NOT_FOUND_IN_REGION)
        return _finish(findings, evidence, os_family, symptom)

    attached = [item for item in disk["attached_instances"] if item]
    if not attached:
        findings.append(FINDING_DISK_NOT_ATTACHED)
        if str(disk.get("billing", "")).lower() in ("prepaid", "subscription"):
            findings.append(FINDING_SUBSCRIPTION_PLACEMENT_LOCKED)
        return _finish(findings, evidence, os_family, symptom)
    if instance_id not in attached:
        findings.append(FINDING_DISK_NOT_ATTACHED)
        findings.append(FINDING_DISK_ON_OTHER_INSTANCE)
        evidence["attached_instances"] = attached
        return _finish(findings, evidence, os_family, symptom)
    findings.append(FINDING_DISK_ATTACHED_TO_THIS_INSTANCE)
    if str(disk.get("multi_attach", "")).lower() in ("enabled", "true"):
        findings.append(FINDING_MULTI_ATTACH)

    if not guest.get("collected"):
        findings.append(FINDING_PROBE_UNAVAILABLE if guest.get("gaps") else FINDING_PROBE_NOT_RUN)
        return _finish(findings, evidence, os_family, symptom)

    if os_family == "windows":
        return _evaluate_windows(disk, guest, evidence, findings, symptom)

    pool = list(guest["devices"])
    candidates = _candidates(pool, disk["size_gib"])
    candidates = _narrow_by_cloud_device(candidates, disk.get("cloud_device", ""))
    evidence["size_matched_devices"] = [device["name"] for device in candidates]
    child_names: List[str] = []
    for device in candidates:
        base = re.sub(r"\d+$", "", device["name"])
        child_names.extend(other["name"] for other in pool
                           if other["name"] != device["name"] and other["name"].startswith(base))
    evidence["child_devices"] = child_names

    if not candidates:
        findings.append(FINDING_DEVICE_NOT_ENUMERATED)
        return _finish(findings, evidence, os_family, symptom)

    rows = candidates + [other for other in pool if other["name"] in child_names]
    filesystems = [row for row in rows if row.get("fstype")]
    mounts = _mount_for(rows, guest["mounts"],
                        [row["name"] for row in rows if row.get("fstype")] +
                        [device["name"] for device in candidates])

    if not filesystems and not child_names:
        findings.append(FINDING_NO_PARTITION)
    if not filesystems:
        findings.append(FINDING_NO_FILESYSTEM)
        return _finish(findings, evidence, os_family, symptom)
    evidence["filesystems"] = sorted({row["fstype"] for row in filesystems})
    if not mounts:
        findings.append(FINDING_FILESYSTEM_NOT_MOUNTED)
        return _finish(findings, evidence, os_family, symptom)
    evidence["mount_points"] = sorted({mount["mountpoint"] for mount in mounts})
    findings.append(FINDING_MOUNTED_AND_READABLE)
    if _symptom_reports_hidden_data(symptom) and evidence["mount_points"] != ["/"]:
        findings.append(FINDING_MOUNT_POINT_SHADOWING)
    return _finish(findings, evidence, os_family, symptom)


def _windows_disk_by_serial(guest: Dict[str, Any], serial: str) -> Optional[Dict[str, Any]]:
    """Find the Windows disk record whose serial equals the cloud disk serial.

    Live-verified: DescribeDisks SerialNumber == Get-Disk SerialNumber. This is the
    only reliable join when several volumes share a size and drive letters are
    assigned out of disk order.
    """
    if not serial:
        return None
    for record in guest.get("windows_disks") or []:
        if record.get("serial") == serial:
            return record
    return None


def _evaluate_windows(disk: Dict[str, Any], guest: Dict[str, Any], evidence: Dict[str, Any],
                      findings: List[str], symptom: str) -> Dict[str, Any]:
    volumes = guest["volumes"] or guest["devices"]
    serial = str(disk.get("serial", "") or "")
    win_disk = _windows_disk_by_serial(guest, serial)
    isolated_by_serial = False
    if win_disk is not None:
        evidence["serial_matched_disk"] = serial
        if win_disk.get("operational") == "offline":
            findings.append(FINDING_WINDOWS_VOLUME_OFFLINE_OR_UNMAPPED)
            return _finish(findings, evidence, "windows", symptom)
        number = win_disk.get("number")
        letters = [part["drive_letter"] for part in guest.get("windows_partitions") or []
                   if part.get("disk_number") == number and part.get("drive_letter")]
        target_volume = None
        for letter in letters:
            for volume in volumes:
                mount = str(volume.get("mountpoint", "")).rstrip(":").upper()
                if mount and mount == letter:
                    target_volume = volume
                    break
            if target_volume is not None:
                break
        if target_volume is not None:
            candidates = [target_volume]
            isolated_by_serial = True
            evidence["isolated_by_serial"] = True
        elif letters:
            findings.append(FINDING_WINDOWS_VOLUME_OFFLINE_OR_UNMAPPED)
            return _finish(findings, evidence, "windows", symptom)
        else:
            findings.append(FINDING_NO_FILESYSTEM)
            return _finish(findings, evidence, "windows", symptom)
    else:
        candidates = _candidates(volumes, disk["size_gib"])
        candidates = _narrow_by_cloud_device(candidates, disk.get("cloud_device", ""))
    evidence["size_matched_devices"] = [volume["name"] for volume in candidates]
    if not candidates:
        findings.append(FINDING_DEVICE_NOT_ENUMERATED)
        return _finish(findings, evidence, "windows", symptom)
    offline = [volume for volume in candidates
               if volume.get("operational") == "offline" or not volume.get("mountpoint")]
    target = _guest_device_basename(disk.get("cloud_device", ""))
    isolated = isolated_by_serial or len(candidates) == 1 or any(
        volume["name"] == target for volume in candidates)
    if not isolated and offline and len(offline) < len(candidates):
        evidence["ambiguous_volumes"] = [volume["name"] for volume in candidates]
        findings.append(FINDING_WINDOWS_VOLUME_TARGET_AMBIGUOUS)
        return _finish(findings, evidence, "windows", symptom)
    if offline:
        findings.append(FINDING_WINDOWS_VOLUME_OFFLINE_OR_UNMAPPED)
        return _finish(findings, evidence, "windows", symptom)
    evidence["mount_points"] = sorted({volume["mountpoint"] for volume in candidates})
    findings.append(FINDING_MOUNTED_AND_READABLE)
    if _symptom_reports_hidden_data(symptom):
        findings.append(FINDING_MOUNT_POINT_SHADOWING)
    return _finish(findings, evidence, "windows", symptom)


_SHADOWING_MARKERS = ("lost", "missing", "disappear", "cannot see my files", "hidden",
                      "old data", "previous data", "empty directory", "files gone")


def _symptom_reports_hidden_data(symptom: str) -> bool:
    lowered = (symptom or "").lower()
    return any(marker in lowered for marker in _SHADOWING_MARKERS)


def _finish(findings: List[str], evidence: Dict[str, Any], os_family: str,
            symptom: str) -> Dict[str, Any]:
    blocked = next((finding for finding in findings if finding not in (
        FINDING_DISK_ATTACHED_TO_THIS_INSTANCE, FINDING_MULTI_ATTACH,
        FINDING_SUBSCRIPTION_PLACEMENT_LOCKED, FINDING_MOUNTED_AND_READABLE,
        FINDING_MOUNT_POINT_SHADOWING, FINDING_PROBE_NOT_RUN)), findings[0] if findings else "")
    stop_step = next((link["step"] for link in VISIBILITY_CHAIN
                      if link["blocked_finding"] in findings), None)
    if stop_step is None:
        stop_step = next((WINDOWS_CHAIN_STOP[finding] for finding in findings
                          if finding in WINDOWS_CHAIN_STOP), None)
    steps_done = []
    for link in VISIBILITY_CHAIN:
        if stop_step is not None and link["step"] >= stop_step:
            break
        if (FINDING_PROBE_NOT_RUN in findings or FINDING_PROBE_UNAVAILABLE in findings) \
                and link["plane"] == "os":
            break
        steps_done.append(link["step"])
    return {
        "findings": findings,
        "blocked_step": blocked,
        "explanation": FINDING_EXPLANATION.get(blocked, ""),
        "manual_next_step": FINDING_NEXT_STEP.get(blocked, ""),
        "chain_steps_confirmed": steps_done,
        "os_family": os_family,
        "symptom_reported": bool(symptom),
        "evidence": evidence,
    }


def chain_table(verdict: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """One markdown row per link of the chain: step, plane, state."""
    rows: List[Tuple[str, str, str]] = []
    confirmed = set(verdict.get("chain_steps_confirmed", []))
    blocked = verdict.get("blocked_step")
    findings = verdict.get("findings", [])
    os_family = verdict.get("os_family")
    probe_missing = (FINDING_PROBE_NOT_RUN in findings
                     or FINDING_PROBE_UNAVAILABLE in findings)
    stop_step = next((link["step"] for link in VISIBILITY_CHAIN
                      if link["blocked_finding"] == blocked), None)
    if stop_step is None:
        stop_step = WINDOWS_CHAIN_STOP.get(blocked)
    for link in VISIBILITY_CHAIN:
        if link["step"] in confirmed:
            state = "checked and in place"
        elif link["step"] == stop_step:
            state = "this is where it stops"
        elif probe_missing and link["plane"] == "os":
            state = "not verified (guest not read)"
        else:
            state = "not reached"
        name = link.get("name_windows") if os_family == "windows" else None
        rows.append((str(link["step"]), "%s / %s" % (link["plane"], name or link["name"]), state))
    return rows


def device_map_rows(results: List[Dict[str, Any]], guest: Dict[str, Any]) -> List[Tuple[str, str, str, str]]:
    """Cloud disk id against the device name the guest most likely shows for it."""
    rows: List[Tuple[str, str, str, str]] = []
    pool = list(guest.get("devices", [])) + list(guest.get("volumes", []))
    for verdict in results:
        evidence = verdict.get("evidence", {})
        candidates = evidence.get("size_matched_devices") or []
        names = ", ".join(candidates) if candidates else "no size-matched device"
        mounts = ", ".join(evidence.get("mount_points", [])) or "-"
        rows.append((str(evidence.get("disk_id", "")), str(evidence.get("size_gib", "")), names, mounts))
    if not rows and pool:
        rows.append(("(no cloud disk supplied)", "-",
                     ", ".join(device["name"] for device in pool[:8]),
                     ", ".join(mount["mountpoint"] for mount in guest.get("mounts", [])[:8])))
    return rows


def render_markdown(title: str, sections: Iterable[Tuple[str, List[str]]]) -> str:
    lines: List[str] = ["# %s" % title, ""]
    for heading, body in sections:
        if not body:
            continue
        lines.append("## %s" % heading)
        lines.extend(body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def markdown_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> List[str]:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join([" --- "] * len(headers)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return out


def _run_selftest() -> int:
    """Offline boundary locks for the disk-visibility matching core.

    Two regressions this pins (both were live defects): ``parse_lsblk`` must
    mark an unindented top-level disk as NOT a child so ``_candidates`` can pick
    it (a tree-prefix regex that matched the empty string made every device a
    child, so no disk was ever enumerated), and ``_mount_for`` must attribute a
    ``/dev/vdb1`` findmnt/df source to the bare lsblk name ``vdb1`` (comparing
    after stripping only the leading slash left ``dev/vdb1`` and never matched,
    so every mounted disk read as not mounted). The size / os / attachment
    helpers feed those matches. Pure logic only - no cloud, no subprocess.
    """
    rc = 0

    def expect(name, cond):
        nonlocal rc
        if cond:
            print(f"PASS {name}")
        else:
            print(f"FAIL {name}")
            rc = 1

    # --- to_gib: units, byte heuristic, None on junk / non-size
    expect("tg_int", to_gib(40) == 40.0)
    expect("tg_gib_forms", to_gib("40G") == 40.0 and to_gib("40 GiB") == 40.0 and to_gib("40GB") == 40.0)
    expect("tg_mib", to_gib("40960M") == 40.0)
    expect("tg_tib", to_gib("1T") == 1024.0)
    expect("tg_bytes_large", to_gib("42949672960") == 40.0)
    expect("tg_none", to_gib(None) is None and to_gib("") is None)
    expect("tg_junk_none", to_gib("abc") is None and to_gib("40X") is None)
    expect("tg_negative_none", to_gib("-5") is None)

    # --- sizes_match: 3% with 1 GiB floor; None/non-positive never match
    expect("sm_exact", sizes_match(40, 40) is True)
    expect("sm_within_floor", sizes_match(40, 41) is True)
    expect("sm_outside", sizes_match(40, 42) is False)
    expect("sm_zero_none", sizes_match(40, 0) is False and sizes_match(40, None) is False)

    # --- os_family_from
    expect("osf_windows", os_family_from({"os_hint": "Windows Server 2019"}) == "windows")
    expect("osf_linux", os_family_from({"os_hint": "Alibaba Cloud Linux 3"}) == "linux")
    expect("osf_blank", os_family_from({"os_hint": ""}) == "")

    # --- _attached_instances / _device_of: nested-cloud-shape tolerant
    expect("ai_direct", _attached_instances({"InstanceId": "i-1"}) == ["i-1"])
    expect("ai_nested", _attached_instances(
        {"Attachments": {"Attachment": [{"InstanceId": "i-2"}, {"InstanceId": "i-3"}]}}) == ["i-2", "i-3"])
    expect("ai_dedup", _attached_instances(
        {"InstanceId": "i-1", "Attachments": {"Attachment": [{"InstanceId": "i-1"}, {"InstanceId": "i-9"}]}}
    ) == ["i-1", "i-9"])
    expect("do_attachment", _device_of({"Attachments": {"Attachment": [{"Device": "/dev/xvdb"}]}}) == "/dev/xvdb")
    expect("do_direct", _device_of({"Device": "/dev/vdc"}) == "/dev/vdc")
    expect("do_missing", _device_of({}) == "")

    # --- parse_lsblk regression (tree prefix): unindented parent is NOT a child
    devs = parse_lsblk(
        "NAME   SIZE RO TYPE MOUNTPOINTS\n"
        "vdb    40G  0 disk \n"
        "\u2514\u2500vdb1 40G  0 part /mnt/data\n")
    by_name = {d["name"]: d for d in devs}
    expect("lsblk_parent_present", "vdb" in by_name)
    expect("lsblk_parent_not_child", by_name.get("vdb", {}).get("is_child") is False)
    expect("lsblk_child_parsed", "vdb1" in by_name)
    expect("lsblk_child_is_child", by_name.get("vdb1", {}).get("is_child") is True)

    # --- _candidates: only non-child disk/volume rows that size-match
    cands = _candidates(devs, 40)
    expect("cand_parent_disk_only", [c["name"] for c in cands] == ["vdb"])
    expect("cand_none_size_empty", _candidates(devs, None) == [])

    # --- _mount_for regression: bare lsblk name vs /dev/ and /dev/mapper/ source
    mounts = [{"device": "/dev/vdb1", "mountpoint": "/mnt/data"}]
    expect("mount_bare_vs_devpath", len(_mount_for(devs, mounts, ["vdb1", "vdb"])) == 1)
    expect("mount_lvm_mapper", len(_mount_for([], [{"device": "/dev/mapper/vg-lv", "mountpoint": "/srv"}],
                                               ["vg-lv"])) == 1)
    expect("mount_no_false_hit", _mount_for([], [{"device": "tmpfs", "mountpoint": "/run"}], ["vdb"]) == [])

    # --- size-collision disambiguation by cloud device (live repro, D160 §46):
    # a 20G system disk and a 20G data disk both size-match; without the cloud
    # device the system disk's mount leaks onto the data disk.
    expect("gdb_xvd", _guest_device_basename("/dev/xvdb") == "vdb")
    expect("gdb_nvme", _guest_device_basename("/dev/nvme1n1") == "nvme1n1")
    expect("gdb_empty", _guest_device_basename("") == "")
    _collide_devs = parse_lsblk(
        "NAME SIZE FSTYPE MOUNTPOINT\n"
        "vda 20G\n"
        "\u2514\u2500vda3 19.8G ext4 /\n"
        "vdb 20G\n")
    _collide_cands = _candidates(_collide_devs, 20)
    expect("collide_two_candidates", len(_collide_cands) == 2)
    expect("narrow_to_vdb",
           [c["name"] for c in _narrow_by_cloud_device(_collide_cands, "/dev/xvdb")] == ["vdb"])
    expect("narrow_to_vda",
           [c["name"] for c in _narrow_by_cloud_device(_collide_cands, "/dev/xvda")] == ["vda"])
    expect("narrow_fallback_no_match",
           len(_narrow_by_cloud_device(_collide_cands, "/dev/sdz")) == 2)
    _collide_guest = {"devices": _collide_devs,
                      "mounts": [{"device": "/dev/vda3", "mountpoint": "/"}],
                      "volumes": [], "collected": True, "gaps": [], "raw": {}}
    _data_disk = {"disk_id": "d-data", "size_gib": 20, "attached_instances": ["i-x"],
                  "multi_attach": "", "billing": "", "cloud_device": "/dev/xvdb"}
    _sys_disk = dict(_data_disk, disk_id="d-sys", cloud_device="/dev/xvda")
    _v_data = evaluate_disk(_data_disk, "i-x", _collide_guest, "linux", "")
    _v_sys = evaluate_disk(_sys_disk, "i-x", _collide_guest, "linux", "")
    expect("collide_data_not_mounted",
           FINDING_MOUNTED_AND_READABLE not in _v_data["findings"]
           and FINDING_NO_FILESYSTEM in _v_data["findings"])
    expect("collide_sys_mounted", FINDING_MOUNTED_AND_READABLE in _v_sys["findings"])

    # --- Windows size-collision: a drive letter never equals the cloud device
    # basename (vdb), so the name narrowing falls back to the whole size set.
    # When those same-size volumes disagree on online/offline the target disk
    # cannot be isolated and a per-disk verdict would leak another volume's
    # state (fixture repro of the Windows branch gap). Uniform states stay safe;
    # a mixed set must be flagged ambiguous rather than guessed.
    def _win_vol(name, size, mountpoint, operational):
        return {"name": name, "size_gib": size, "fstype": "ntfs",
                "mountpoint": mountpoint, "is_child": False, "kind": "volume",
                "health": "healthy", "operational": operational, "raw": name}

    _win_disk = {"disk_id": "d-win", "size_gib": 40, "attached_instances": ["i-w"],
                 "multi_attach": "", "billing": "", "cloud_device": "/dev/xvdb"}

    def _win_guest(vols):
        return {"devices": [], "mounts": [], "volumes": vols,
                "collected": True, "gaps": [], "raw": {}}

    _v_mixed = evaluate_disk(_win_disk, "i-w", _win_guest(
        [_win_vol("C", 40, "C:", "online"), _win_vol("D", 40, "D:", "online"),
         _win_vol("E", 40, "", "offline")]), "windows", "")
    expect("win_mixed_ambiguous",
           FINDING_WINDOWS_VOLUME_TARGET_AMBIGUOUS in _v_mixed["findings"])
    expect("win_mixed_no_false_offline",
           FINDING_WINDOWS_VOLUME_OFFLINE_OR_UNMAPPED not in _v_mixed["findings"])
    expect("win_mixed_no_false_mounted",
           FINDING_MOUNTED_AND_READABLE not in _v_mixed["findings"])
    _v_online = evaluate_disk(_win_disk, "i-w", _win_guest(
        [_win_vol("C", 40, "C:", "online"), _win_vol("D", 40, "D:", "online")]), "windows", "")
    expect("win_uniform_online_mounted",
           FINDING_MOUNTED_AND_READABLE in _v_online["findings"]
           and FINDING_WINDOWS_VOLUME_TARGET_AMBIGUOUS not in _v_online["findings"])
    _v_offline = evaluate_disk(_win_disk, "i-w", _win_guest(
        [_win_vol("C", 40, "", "offline"), _win_vol("D", 40, "", "offline")]), "windows", "")
    expect("win_uniform_offline",
           FINDING_WINDOWS_VOLUME_OFFLINE_OR_UNMAPPED in _v_offline["findings"]
           and FINDING_WINDOWS_VOLUME_TARGET_AMBIGUOUS not in _v_offline["findings"])
    _v_single = evaluate_disk(_win_disk, "i-w", _win_guest(
        [_win_vol("D", 40, "D:", "online")]), "windows", "")
    expect("win_single_precise",
           FINDING_MOUNTED_AND_READABLE in _v_single["findings"]
           and FINDING_WINDOWS_VOLUME_TARGET_AMBIGUOUS not in _v_single["findings"])
    expect("win_ambiguous_has_explanation",
           bool(FINDING_EXPLANATION.get(FINDING_WINDOWS_VOLUME_TARGET_AMBIGUOUS)))
    expect("win_ambiguous_has_next_step",
           bool(FINDING_NEXT_STEP.get(FINDING_WINDOWS_VOLUME_TARGET_AMBIGUOUS)))

    # --- Windows serial-based isolation. Live-verified: the cloud disk
    # SerialNumber equals the Windows Get-Disk serial, and drive letters are
    # assigned out of disk order (Disk 1 -> E:, Disk 2 -> D:), so size + name
    # narrowing cannot isolate a disk but the serial join can. The JSON below was
    # captured from a live Windows size-collision repro (one data disk offline).
    _live_disks_json = (
        '[{"Number":2,"SerialNumber":"bp19swk7qwy0n6s8lyh7","OperationalStatus":"Offline"},'
        '{"Number":1,"SerialNumber":"bp17manhh8ygnwzjx0r6","OperationalStatus":"Online"},'
        '{"Number":0,"SerialNumber":"bp19swk7qwy0n6s8lygt","OperationalStatus":"Online"}]')
    _live_parts_json = (
        '[{"DiskNumber":2,"DriveLetter":null},{"DiskNumber":1,"DriveLetter":"E"},'
        '{"DiskNumber":0,"DriveLetter":"C"}]')
    _wdisks = parse_windows_disks(_live_disks_json)
    expect("win_disks_parse_count", len(_wdisks) == 3)
    expect("win_disks_parse_serial", {d["serial"] for d in _wdisks} ==
           {"bp19swk7qwy0n6s8lyh7", "bp17manhh8ygnwzjx0r6", "bp19swk7qwy0n6s8lygt"})
    expect("win_disks_parse_offline",
           next(d["operational"] for d in _wdisks if d["number"] == 2) == "offline")
    expect("win_disks_parse_junk", parse_windows_disks("not json") == [])
    _wparts = parse_windows_partitions(_live_parts_json)
    expect("win_parts_parse_letter",
           next(p["drive_letter"] for p in _wparts if p["disk_number"] == 1) == "E")
    expect("win_parts_parse_null",
           all(p["drive_letter"] == "" for p in _wparts if p["disk_number"] == 2))
    _serial_guest = {"devices": [], "mounts": [], "collected": True, "gaps": [], "raw": {},
                     "volumes": [_win_vol("C", 40, "C:", "online"),
                                 _win_vol("E", 40, "E:", "online")],
                     "windows_disks": _wdisks, "windows_partitions": _wparts}
    _off_disk = dict(_win_disk, disk_id="d-off", serial="bp19swk7qwy0n6s8lyh7",
                     cloud_device="/dev/xvdc")
    _v_off = evaluate_disk(_off_disk, "i-w", _serial_guest, "windows", "")
    expect("win_serial_offline_correct",
           FINDING_WINDOWS_VOLUME_OFFLINE_OR_UNMAPPED in _v_off["findings"]
           and FINDING_MOUNTED_AND_READABLE not in _v_off["findings"])
    _on_disk = dict(_win_disk, disk_id="d-on", serial="bp17manhh8ygnwzjx0r6",
                    cloud_device="/dev/xvdb")
    _v_on = evaluate_disk(_on_disk, "i-w", _serial_guest, "windows", "")
    expect("win_serial_online_isolated",
           FINDING_MOUNTED_AND_READABLE in _v_on["findings"]
           and _v_on["evidence"].get("size_matched_devices") == ["E"]
           and _v_on["evidence"].get("isolated_by_serial") is True)
    expect("win_serial_absent_falls_back",
           FINDING_WINDOWS_VOLUME_TARGET_AMBIGUOUS in evaluate_disk(
               dict(_win_disk, serial=""), "i-w",
               _win_guest([_win_vol("C", 40, "C:", "online"),
                           _win_vol("D", 40, "D:", "online"),
                           _win_vol("E", 40, "", "offline")]), "windows", "")["findings"])

    # --- parse_windows_volumes must read the REAL Get-Volume layout: bare drive
    # letters (C, not C:) and OperationalStatus "OK" (not "Online"). Captured live.
    _real_getvolume = (
        "DriveLetter FileSystemLabel        Size OperationalStatus\n"
        "----------- ---------------        ---- -----------------\n"
        "                              100663296 OK               \n"
        "C                           42842714112 OK               \n"
        "E                           42931843072 OK               \n")
    _rv_by = {v["name"]: v for v in parse_windows_volumes(_real_getvolume)}
    expect("winvol_real_bare_letter_mountpoint", _rv_by.get("C", {}).get("mountpoint") == "C:")
    expect("winvol_real_ok_online", _rv_by.get("E", {}).get("operational") == "online")
    expect("winvol_real_size", sizes_match(_rv_by.get("E", {}).get("size_gib"), 40) is True)

    # --- Windows chain table must stop at the mapped step, not mark every OS step
    # "checked and in place" for an offline disk. Offline volume blocks step 5;
    # ambiguous target blocks step 3; a mounted disk confirms all five. OS steps
    # render Windows probe names (Get-Disk/Get-Partition/Get-Volume), not lsblk/df.
    _ct_off = chain_table(_v_offline)
    expect("win_chain_offline_stops_at_5",
           _ct_off[4][2] == "this is where it stops"
           and [r[0] for r in _ct_off if r[2] == "checked and in place"] == ["1", "2", "3", "4"])
    expect("win_chain_offline_not_all_in_place",
           sum(1 for r in _ct_off if r[2] == "checked and in place") == 4)
    _ct_on = chain_table(_v_online)
    expect("win_chain_online_all_confirmed",
           all(r[2] == "checked and in place" for r in _ct_on))
    _ct_amb = chain_table(_v_mixed)
    expect("win_chain_ambiguous_stops_at_3",
           _ct_amb[2][2] == "this is where it stops"
           and [r[0] for r in _ct_amb if r[2] == "checked and in place"] == ["1", "2"])
    expect("win_chain_os_names_windows",
           "Get-Disk" in _ct_on[2][1] and "Get-Volume" in _ct_on[4][1]
           and "lsblk" not in _ct_on[2][1])
    _ct_linux = chain_table({"chain_steps_confirmed": [1, 2, 3, 4, 5],
                             "blocked_step": FINDING_MOUNTED_AND_READABLE,
                             "findings": [FINDING_MOUNTED_AND_READABLE], "os_family": "linux"})
    expect("linux_chain_names_unchanged",
           "guest kernel enumerates" in _ct_linux[2][1] and "Get-Disk" not in _ct_linux[2][1])

    print(f"SELFTEST: {'PASS' if rc == 0 else 'FAIL'}")
    return rc


if __name__ == "__main__":
    import sys as _sys
    if "--selftest" in _sys.argv[1:]:
        _sys.exit(_run_selftest())
