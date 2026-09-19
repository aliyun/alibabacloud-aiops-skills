#!/usr/bin/env python3
"""Neutral core layer for alibabacloud-agent-observability scripts.

Data-source-agnostic infrastructure shared by both trajectory sources:
- loongsuit mode: CMS 2.0 workspace trajectory via UModel GetEntityStoreData
  (see cms_trace.py) — Session / Turn / Step and framework state
- ebpf mode: SLS project 'ebpf-event' logstore (see sls_event.py) — runtime
  facts (process / container / host / network / HTTP)

Responsibilities:
- Data source binding via required command-line flags (clarified with the user)
- Local result cache (stable-window entries never expire)
- Time-window grid alignment, read-only CLI user agent
- Argument parsing / output emission / error-handling wrappers
- Truncation / JSON-parsing utilities

This module performs no API calls itself; the SLS and CMS gateways live in
sls_event.py and cms_trace.py respectively.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time

SKILL_NAME = "alibabacloud-agent-observability"

# Local result cache. Entries whose window ended before CACHE_STABLE_AGE are
# immutable (ingestion lag) and never expire; newer entries expire after
# AGENT_OBS_CACHE_TTL seconds.
CACHE_STABLE_AGE = 300
CACHE_DEFAULT_TTL = 1800
CACHE_MAX_FILES = 1000
CACHE_PRUNE_KEEP = 800
# Relative windows snap their end up onto this grid (see resolve_window) so
# back-to-back runs share identical query windows and cache keys.
WINDOW_GRID = 300
# Default window SPAN in hours, shared by every script. The span CAP is an
# agent-side clarification discipline (AGENT_OBS_MAX_WINDOW_HOURS, see
# SKILL.md section 8 Step 0); no script reads or enforces it.
DEFAULT_HOURS = 4

_CACHE_STATS = {"hits": 0, "misses": 0, "puts": 0}


class ObsError(RuntimeError):
    """User-facing error; message printed without traceback."""


def cache_enabled():
    return os.environ.get("AGENT_OBS_NO_CACHE", "").lower() not in ("1", "true", "yes")


def cache_dir():
    return os.environ.get("AGENT_OBS_CACHE_DIR") or os.path.join(
        tempfile.gettempdir(), "agent_obs_cache")


def cache_stats():
    return {"enabled": cache_enabled(), "dir": cache_dir(), **_CACHE_STATS}


def _cache_path(key_dict):
    digest = hashlib.sha256(
        json.dumps(key_dict, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:32]
    return os.path.join(cache_dir(), digest + ".json")


def cache_get(key_dict):
    """Return the cached response for key_dict, or None (miss/expired/disabled).

    Best-effort: any cache error degrades to a normal API call."""
    if not cache_enabled():
        return None
    try:
        with open(_cache_path(key_dict), encoding="utf-8") as fh:
            entry = json.load(fh)
    except (OSError, ValueError):
        _CACHE_STATS["misses"] += 1
        return None
    if entry.get("v") != 1 or "data" not in entry:
        _CACHE_STATS["misses"] += 1
        return None
    if not entry.get("stable"):
        try:
            ttl = int(os.environ.get("AGENT_OBS_CACHE_TTL", "") or CACHE_DEFAULT_TTL)
        except ValueError:
            ttl = CACHE_DEFAULT_TTL
        if time.time() - entry.get("ts", 0) > ttl:
            _CACHE_STATS["misses"] += 1
            return None
    _CACHE_STATS["hits"] += 1
    return entry["data"]


def cache_put(key_dict, data, stable=False):
    """Store a response atomically; prune the directory occasionally."""
    if not cache_enabled():
        return
    try:
        os.makedirs(cache_dir(), exist_ok=True)
        entry = {"v": 1, "ts": int(time.time()), "stable": stable,
                 "key": key_dict, "data": data}
        path = _cache_path(key_dict)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(entry, fh, ensure_ascii=False)
        os.replace(tmp, path)
        _CACHE_STATS["puts"] += 1
        _cache_prune()
    except OSError:
        pass


def _cache_prune():
    if _CACHE_STATS["puts"] % 25 != 0:
        return
    try:
        entries = []
        for name in os.listdir(cache_dir()):
            path = os.path.join(cache_dir(), name)
            try:
                entries.append((os.path.getmtime(path), path))
            except OSError:
                pass
        if len(entries) <= CACHE_MAX_FILES:
            return
        entries.sort()
        for _, path in entries[:len(entries) - CACHE_PRUNE_KEEP]:
            try:
                os.remove(path)
            except OSError:
                pass
    except OSError:
        pass


def missing_bindings(region, project, workspace):
    """Return one entry per missing required data-source binding.

    --region is always required (both APIs need it to build their endpoint).
    The two data-set bindings are required COLLECTIVELY: at least ONE of
    --project (eBPF/SLS) or --workspace (LoongSuit/CMS) must be present, so
    they are reported as a single item and only when both are absent. Bindings
    come from CLI args or env vars (CLI takes precedence). Empty list = complete."""
    missing = []
    if not region:
        missing.append("--region (region shared by both data sources, "
                       "e.g. cn-hangzhou)")
    if not project and not workspace:
        missing.append(
            "--project and/or --workspace (at least ONE of the two is required "
            "— --project = the SLS project holding the 'ebpf-event' logstore "
            "(eBPF runtime facts), --workspace = the CMS 2.0 workspace queried "
            "via GetEntityStoreData for the LoongSuit agent trajectory "
            "(Session/Turn/Step))")
    return missing


class Config:
    def __init__(self, project, logstore, region, workspace, service_name=None):
        self.project = project          # eBPF source: SLS project
        self.logstore = logstore        # explicit ebpf logstore override (csv)
        self.region = region            # CMS biz-region / SLS region
        self.workspace = workspace      # loongsuit source: CMS 2.0 workspace
        self.service_name = service_name  # loongsuit-side application filter
        self.event_logstores = []       # finalized by resolve_mode (ebpf mode)
        self.mode = None                # effective scope after auto-narrowing
        self.source_gap = []            # sources absent from this binding

    @property
    def has_ebpf(self):
        return bool(self.project)

    @property
    def has_loongsuit(self):
        return bool(self.workspace)

    @classmethod
    def resolve(cls, args):
        """Resolve the binding from the command line or environment variables.
        --region is required and at least ONE of --project (eBPF/SLS) /
        --workspace (LoongSuit/CMS) is required. CLI args take precedence over
        env vars (AGENT_OBS_REGION / AGENT_OBS_SLS_PROJECT / AGENT_OBS_CMS_WORKSPACE).
        Every missing item is reported at once; supplying only one side is legal
        and the run then auto-narrows to that source (see sls_event.resolve_mode),
        reporting the other as an instrumentation gap — never silently."""
        if getattr(args, "no_cache", False):
            os.environ["AGENT_OBS_NO_CACHE"] = "1"
        # env var fallback (CLI args take precedence)
        region = getattr(args, "region", None) or os.environ.get("AGENT_OBS_REGION")
        project = getattr(args, "project", None) or os.environ.get("AGENT_OBS_SLS_PROJECT")
        workspace = getattr(args, "workspace", None) or os.environ.get("AGENT_OBS_CMS_WORKSPACE")
        service_name = getattr(args, "service_name", None) or os.environ.get("AGENT_OBS_SERVICE_NAME")
        missing = missing_bindings(region, project, workspace)
        if missing:
            raise ObsError(
                "missing required data-source binding(s): " + "; ".join(missing) +
                ". Bindings come from CLI args or env vars (AGENT_OBS_REGION / "
                "AGENT_OBS_SLS_PROJECT / AGENT_OBS_CMS_WORKSPACE; CLI takes precedence). "
                "Ask the user for the SLS project name (the project holding the "
                "'ebpf-event' logstore) and the CMS 2.0 workspace name (console "
                "label 云监控 2.0 工作空间); at least one of the two is enough. "
                "Supplying only one is allowed: the run then auto-narrows to that "
                "source and reports the other as an instrumentation gap. Run "
                "'python3 scripts/preflight.py --region <region> ...' to verify "
                "the binding before analysing. Pass the flag(s) on every command "
                "and re-run.")
        cfg = cls(
            project,
            getattr(args, "logstore", None),
            region,
            workspace,
            service_name,
        )
        cfg.source_gap = [name for name, bound in
                          (("ebpf", cfg.has_ebpf), ("loongsuit", cfg.has_loongsuit))
                          if not bound]
        # the ebpf narrowing flags live on the parser, but the ebpf query and
        # client-side filter read them from the config — carry them across
        for attr in ("agent_type", "comm", "container_id", "host", "event_name",
                     "trace_id", "match"):
            setattr(cfg, attr, getattr(args, attr, None))
        return cfg


def binding_block(cfg):
    """The shared `binding` dict echoed by every result."""
    return {"region": cfg.region, "project": cfg.project,
            "workspace": cfg.workspace, "logstores": cfg.event_logstores or None,
            "service_name": cfg.service_name}


def source_availability(cfg, mode):
    """Per-source availability for the `sources` output block. The side that is
    not bound is reported as an instrumentation gap — a binding/onboarding
    gap, never proof that no data exists."""
    queried = {"both": ("ebpf", "loongsuit"), "ebpf": ("ebpf",),
               "loongsuit": ("loongsuit",)}.get(mode, ())
    out = {}
    for name, bound in (("ebpf", cfg.has_ebpf), ("loongsuit", cfg.has_loongsuit)):
        entry = {"bound": bound, "queried": bound and name in queried}
        if name == "ebpf":
            entry["project"] = cfg.project
            entry["logstore"] = (cfg.event_logstores or [None])[0]
        else:
            entry["workspace"] = cfg.workspace
        if not bound:
            if name == "ebpf":
                entry["gap"] = ("instrumentation gap: --project not supplied, so "
                                "the SLS 'ebpf-event' logstore (eBPF runtime "
                                "facts) was not queried; this is a "
                                "binding/onboarding gap, not proof that no "
                                "runtime data exists")
            else:
                entry["gap"] = ("instrumentation gap: --workspace not supplied, "
                                "so the CMS 2.0 workspace (LoongSuit "
                                "Session/Turn/Step) was not queried; this is a "
                                "binding/onboarding gap, not proof that no "
                                "trajectory exists")
        out[name] = entry
    return out


def gap_note(cfg):
    """One note line per unbound source (empty list when both are bound)."""
    notes = []
    for name in cfg.source_gap:
        flag = "--project" if name == "ebpf" else "--workspace"
        what = ("the SLS 'ebpf-event' logstore (eBPF runtime facts)"
                if name == "ebpf" else
                "the CMS 2.0 workspace (LoongSuit Session/Turn/Step)")
        notes.append(f"{name} source not bound ({flag} not supplied): {what} "
                     "was not queried — instrumentation/binding gap, not proof "
                     "that no data exists")
    return notes


_MANIFEST_PATH = os.path.join(os.path.dirname(__file__), os.pardir,
                              "references", "manifest.json")


def skill_version():
    try:
        with open(_MANIFEST_PATH) as f:
            return json.load(f).get("version", "0.0.0")
    except (OSError, json.JSONDecodeError, AttributeError):
        return "0.0.0"


def session_id():
    return os.environ.get("SKILL_SESSION_ID", "")


def user_agent():
    return (f"AlibabaCloud-Agent-Skills/{SKILL_NAME}"
            f"/skill-version/{skill_version()}/{session_id()}")


def cli_plugin_hint(err, product, plugin):
    """Detect the aliyun CLI 'product not built-in / plugin required' error
    and return an actionable ObsError; None when the error is unrelated."""
    if "is not a valid built-in product" in err or "plugin install --names" in err:
        return ObsError(
            f"aliyun CLI product '{product}' needs the '{plugin}' plugin, which is not "
            f"installed. Run: aliyun configure set --auto-plugin-install true && "
            f"aliyun plugin install --names {plugin}  — then retry "
            f"(see SKILL.md pre-check / references/cli-installation-guide.md).\n{err[:400]}")
    return None


# --- generic helpers ---

def ms_iso(value):
    """Millisecond epoch (string or number) -> local 'YYYY-mm-dd HH:MM:SS'."""
    ts = to_int(value, default=None)
    if not ts:
        return None
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts / 1000))


def parse_json_field(row, field):
    raw = row.get(field) or "{}"
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def truncate(value, limit):
    if value is None:
        return None
    s = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    if len(s) <= limit:
        return s
    return s[:limit] + f"...<truncated {len(s) - limit} chars>"


def to_int(value, default=0):
    """SLS returns SQL NULL as the literal string 'null'; parse defensively."""
    if value is None or value in ("", "null", "NULL"):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def resolve_window(args):
    """Return (from_ts, to_ts) unix seconds from --from/--to or --hours.

    Relative windows (--hours) snap their end UP onto a WINDOW_GRID-second
    grid so that runs inside the same grid slot issue byte-identical queries
    and share cached results. The snapped end is at most WINDOW_GRID seconds
    in the future, which the APIs simply treat as 'now'; the start is pushed
    one extra grid back so the window still fully covers [now - hours, now]."""
    now = int(time.time())
    if getattr(args, "from_ts", None) and getattr(args, "to_ts", None):
        return int(args.from_ts), int(args.to_ts)
    hours = getattr(args, "hours", None) or DEFAULT_HOURS
    to = ((now // WINDOW_GRID) + 1) * WINDOW_GRID
    return to - int(hours * 3600) - WINDOW_GRID, to


def base_parser(desc, default_hours=DEFAULT_HOURS):
    p = argparse.ArgumentParser(description=desc)
    p.add_argument("--project", help="eBPF source binding: the SLS project that stores "
                                     "the 'ebpf-event' logstore. At least ONE of "
                                     "--project / --workspace is required")
    p.add_argument("--logstore", help="ebpf source: comma-separated logstore override "
                                      "(default: ebpf-event)")
    p.add_argument("--region", help="REQUIRED: region shared by both sources")
    p.add_argument("--workspace", help="LoongSuit source binding: the CMS 2.0 workspace "
                                       "name, a real GetEntityStoreData query parameter "
                                       "(console label 云监控 2.0 工作空间). At least ONE of "
                                       "--project / --workspace is required")
    p.add_argument("--service-name", dest="service_name",
                   help="agent application name (console \"AI 应用\" list). Narrows the "
                        "loongsuit source only (CMS serviceName filter): the ebpf-event "
                        "index carries no service.name, so the ebpf side is narrowed via "
                        "--agent-type / --comm / --container-id instead. Omitted = every "
                        "application sharing the binding")
    p.add_argument("--agent-type", dest="agent_type",
                   help="ebpf source: filter by agent.type (e.g. qwenpaw); the field is "
                        "not indexed, so this is applied client-side after the raw fetch")
    p.add_argument("--comm", help="ebpf source: filter by process comm; client-side")
    p.add_argument("--container-id", dest="container_id",
                   help="ebpf source: filter by container.id (indexed, applied server-side)")
    p.add_argument("--host", help="ebpf source: filter by host.id / host.name / host.ip "
                                  "(indexed, applied server-side)")
    p.add_argument("--event-name", dest="event_name",
                   help="ebpf source: filter by event.name (indexed, applied server-side)")
    p.add_argument("--trace-id", dest="trace_id",
                   help="trace id, read out of http.request.header.traceparent and "
                        "used to join the loongsuit source; the anchor of the analysis "
                        "(trace_chain.py / decision_evidence.py). On the ebpf source it "
                        "is applied client-side because that header is not in the "
                        "ebpf-event index")
    p.add_argument("--mode",
                   help="query scope: both = dual-source combined query (default, "
                        "auto-narrows to whichever sources are bound); loongsuit / ebpf = "
                        "single source")
    p.add_argument("--hours", type=float, default=default_hours,
                   help=f"window SPAN in hours ending now (default {default_hours}); "
                        f"a shorthand for the slice that happens to end now - use "
                        f"--from/--to to pin any past slice of the same span")
    p.add_argument("--from", dest="from_ts", type=int,
                   help="window start, unix seconds (with --to); pins an arbitrary past "
                        "slice (preferred: exact span, no grid push, and past slices hit "
                        "the permanent cache)")
    p.add_argument("--to", dest="to_ts", type=int,
                   help="window end, unix seconds (with --from); the span to - from is "
                        "what the window limit constrains, not how far back the slice sits")
    p.add_argument("--no-cache", dest="no_cache", action="store_true",
                   help="bypass the local result cache (same as AGENT_OBS_NO_CACHE=1)")
    p.add_argument("--format", choices=["json", "yaml"], default="json",
                   help="output format: json (default, stable machine contract for "
                        "programmatic parsing) or yaml (the same full result, "
                        "YAML serialization)")
    return p


_YAML_SAFE_KEY = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-]*$")


def _yaml_key(k):
    k = str(k)
    return k if _YAML_SAFE_KEY.match(k) else json.dumps(k, ensure_ascii=False)


def _yaml_scalar(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    # a JSON-quoted string is a valid YAML scalar (YAML 1.2 superset)
    return json.dumps(str(v), ensure_ascii=False)


def _yaml_lines(v, indent):
    pad = "  " * indent
    if isinstance(v, dict):
        if not v:
            return [pad + "{}"]
        out = []
        for k, val in v.items():
            key = _yaml_key(k)
            if isinstance(val, dict) and val:
                out.append(f"{pad}{key}:")
                out.extend(_yaml_lines(val, indent + 1))
            elif isinstance(val, list) and val:
                out.append(f"{pad}{key}:")
                out.extend(_yaml_lines(val, indent + 1))
            elif isinstance(val, dict):
                out.append(f"{pad}{key}: {{}}")
            elif isinstance(val, list):
                out.append(f"{pad}{key}: []")
            else:
                out.append(f"{pad}{key}: {_yaml_scalar(val)}")
        return out
    if isinstance(v, list):
        if not v:
            return [pad + "[]"]
        out = []
        for item in v:
            if isinstance(item, (dict, list)) and item:
                sub = _yaml_lines(item, indent + 1)
                out.append(f"{pad}- {sub[0].strip()}")
                out.extend(sub[1:])
            elif isinstance(item, dict):
                out.append(f"{pad}- {{}}")
            elif isinstance(item, list):
                out.append(f"{pad}- []")
            else:
                out.append(f"{pad}- {_yaml_scalar(item)}")
        return out
    return [pad + _yaml_scalar(v)]


def to_yaml(obj):
    """Serialize the result with the same structure as the JSON output.

    Stdlib-only emitter: strings are always JSON-quoted (valid YAML scalar),
    keys are quoted unless they match the safe identifier pattern."""
    return "\n".join(_yaml_lines(obj, 0))


def emit(result, fmt="json"):
    if fmt == "yaml":
        print(to_yaml(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def main_wrapper(main_fn):
    try:
        main_fn()
    except ObsError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        sys.exit(130)
