#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime leg for the declarative doc anchors in references/doc-anchors.json.

The build-time half (tools/build_doc_anchors.py, in the development repo) is
what searches: it runs the help-doc fulltext leg and the llms.txt index leg,
a human adjudicates, and the winning URL is frozen into an anchor. This module
is the other half and it never searches. Given an area it reads back the
frozen URLs, fetches at most one official body per run, checks that the body
still hashes to what was adjudicated, and hands the dispatcher copy-ready
citation lines.

Three boundaries are enforced here:

1. Fail-whole, not fail-partial. The anchor file is validated as one unit --
   field whitelist, unique ids, registered products, legal roles, per-area cap.
   A single bad record rejects the entire file with a `[WARN]` trace, because a
   half-loaded anchor set silently changes what an area is allowed to promise.
   There is deliberately no embedded fallback table: when the anchors are
   unusable the leg reports `anchors-rejected` and the area answers from its
   own references exactly as it did before this leg existed.

2. Never fabricate a document. help.aliyun.com answers HTTP 200 with a
   24,666-byte "page not found" shell for a wrong slug, so a status code is
   not evidence of a body; `_is_soft_404` names that case. A blocked egress,
   an oversized body and a console URL (which cannot be probed unauthenticated
   at all) each degrade to their own named verdict.

3. Never resolve a documented conflict at runtime. `conflict-hold` anchors
   carry two official sources that disagree; the leg surfaces both and the
   pre-adjudicated `customer_wording`, and refuses to pick one. Choosing here
   would make the tool the author of a promise no document makes.

Result dictionaries always carry a `verdict` key. The dispatcher maps verdicts
onto report lines; nothing in this module interprets them.

Pure functions are covered by selftest() below, which makes no network call.
"""

import datetime
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
from typing import Dict, List

SCHEMA = 'ecs-doc-anchors/v2'
HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGE_ROOT = os.path.dirname(HERE)
ANCHORS_RELPATH = os.path.join('references', 'doc-anchors.json')

# China site only. The international site carries different rule wording for
# the same topics, so an anchor adjudicated against help.aliyun.com must not be
# served from www.alibabacloud.com/help.
DOC_HOSTS = ('help.aliyun.com',)
CONSOLE_HOSTS = ('console.aliyun.com', 'usercenter2.aliyun.com')

ROLES = ('verify-only', 'promote', 'doc-answers', 'conflict-hold')
KINDS = ('doc', 'console-entry')

REQUIRED_FIELDS = (
    'id', 'area', 'scene_uid', 'role', 'kind', 'claim',
    'product', 'url', 'title', 'checked_on',
)
OPTIONAL_FIELDS = (
    'truth_class', 'build_query', 'also_covered_by', 'conflict_with', 'excerpt',
    'body_sha256', 'cross_area', 'area_correction', 'note', 'customer_wording',
    'verified_by', 'cited_in', 'alias', 'scope_limit', 'time_sensitive',
    'console_entry', 'demand_tickets', 'match_terms', 'role_overrides',
    'correction_applied',
)
LIST_FIELDS = ('also_covered_by', 'conflict_with', 'cross_area', 'cited_in', 'alias')

# Where a `correction_applied` witness may point. `references/` holds the
# customer-facing rule files; `scripts/` is included because the provenance
# labels themselves live in the per-area `RULE_TOPICS` constants, so a
# correction that promotes a rule topic from ticket-statement to official-doc
# has no references/ file to land in. Both are read off disk by the build-time
# checker, which is why absolute paths and parent traversal are rejected.
CORRECTION_TARGET_DIRS = ('references/', 'scripts/')

# Measured over the 37,750-ticket September corpus: 45.1% of tickets that got a
# support-engineer reply cite a help.aliyun.com page, and the three most-cited
# pages are all snapshot pages (create-a-snapshot 4,403 tickets, snapshots-1
# 5,204 across its two slug forms, delete-a-snapshot-1 1,839). Those warnings
# cut across areas -- "take a snapshot first" precedes any destructive disk or
# OS action, and "snapshots keep billing" explains charges after a refund or
# after cloud backup is stopped -- so they live once under SHARED_AREA and
# declare which areas may cite them, instead of being copied per area where the
# copies would drift.
SHARED_AREA = '_shared'
SHARED_SCENE = '_shared'

# Measured on the 39-anchor pilot file: the busiest area holds 11. The cap is
# headroom, not a target -- its job is to reject a runaway generated file
# before it ships, since every anchor is a promise the area has to keep.
MAX_ANCHORS_PER_AREA = 16
MAX_ANCHORS_TOTAL = 120
# One contract scene can bind many anchors (the busiest in the shipped file
# binds 11 to hbr-backup-diagnosis__qb8783528). Dumping all of them into an
# answer is the opposite of the target: a support engineer cites the one or two
# documents that settle the question. This is the per-dispatch citation cap.
MAX_CITED_PER_RUN = 3
SHA_PREFIX_LEN = 12

# Weight of one verbatim customer-term hit in _relevance(). Two hits saturate.
TERM_HIT_WEIGHT = 0.6
# Floor an anchor must clear on the CUSTOMER'S QUESTION ALONE to be citable.
# Measured on the shipped file, not chosen by taste: a correctly routed bill
# question scored its anchors 0.167, a correctly routed refund question scored
# 1.111 / 0.612 / 0.250, while a refund question routed to the bill area scored
# 0.000 on all 15 of its anchors and a disk-expansion question routed to the
# refund area peaked at 0.056. Without a floor the leg cited three snapshot
# billing documents as the answer to "where does my refund go", because area
# output in `text` lifted irrelevant anchors off zero. 0.1 separates the two
# groups with margin on both sides.
MIN_RELEVANCE = 0.1

FETCH_TIMEOUT_SECONDS = 8
MAX_BODY_BYTES = 600 * 1024
_DOC_REFS_SESSION_ID = uuid.uuid4().hex


def _doc_refs_identity():
    try:
        with open(os.path.join(PACKAGE_ROOT, 'references', 'manifest.json'),
                  encoding='utf-8') as fh:
            meta = json.load(fh)
        return (meta.get('name') or 'alibabacloud-ecs-high-frequency-issues',
                meta.get('version') or '0.0.0')
    except Exception:
        return 'alibabacloud-ecs-high-frequency-issues', '0.0.0'


_DOC_REFS_NAME, _DOC_REFS_VERSION = _doc_refs_identity()
USER_AGENT = ('AlibabaCloud-Agent-Skills/' + _DOC_REFS_NAME + '/'
              + _DOC_REFS_SESSION_ID + ' skill-version/' + _DOC_REFS_VERSION)

# help.aliyun.com returns HTTP 200 plus this exact byte count for a slug that
# does not exist. Both guessed slugs that failed during the pilot build
# (cloud-backup/user-guide/stop-billing.md and
# ecs/user-guide/initialize-a-data-disk-on-a-linux-instance.md) came back at
# this size, which is how the trap was found.
SOFT_404_BYTES = 24666
SOFT_404_MARKERS = (
    'notfound: "true"',
    "notfound: 'true'",
    '"statuscode": "404"',
    '"statuscode":"404"',
    'page not found',
)
SOFT_404_SCAN_BYTES = 8192

CACHE_DIR_ENV = 'ECS_DOC_CACHE_DIR'
CACHE_TTL_ENV = 'ECS_DOC_CACHE_TTL_DAYS'
ENABLE_ENV = 'ECS_DOC_REFS'
CACHE_TTL_DAYS_DEFAULT = 3
CACHE_SUBDIRS = ('alibabacloud-ecs-high-frequency-issues', 'doc-bodies')

_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _warn(message):
    """One degradation trace on the console (eval 15657: the dispatcher-process
    stream is copyable, so no forbidden marker may ride it). The child streams'
    own `[WARN]` lines still key GAP_MARK_RE from inside the collected sinks."""
    sys.stderr.write('not read: doc-refs: {0}\n'.format(message))
    sys.stderr.flush()


def _disabled():
    return os.environ.get(ENABLE_ENV, '').strip().lower() in ('off', '0', 'false', 'no')


def _cache_ttl_days():
    raw = os.environ.get(CACHE_TTL_ENV, '').strip()
    if not raw:
        return CACHE_TTL_DAYS_DEFAULT
    try:
        value = float(raw)
    except ValueError:
        _warn('{0}={1!r} is not a number; using {2} days'.format(
            CACHE_TTL_ENV, raw, CACHE_TTL_DAYS_DEFAULT))
        return CACHE_TTL_DAYS_DEFAULT
    return value if value >= 0 else CACHE_TTL_DAYS_DEFAULT


def _cache_dir():
    raw = os.environ.get(CACHE_DIR_ENV, '').strip()
    if raw:
        return os.path.expanduser(raw)
    xdg = os.environ.get('XDG_CACHE_HOME', '').strip()
    root = os.path.expanduser(xdg) if xdg else os.path.join(
        os.path.expanduser('~'), '.cache')
    return os.path.join(root, *CACHE_SUBDIRS)


def _cache_paths(url):
    """Deterministic body + sidecar paths for one URL. Pure."""
    key = hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]
    root = _cache_dir()
    return os.path.join(root, key + '.md'), os.path.join(root, key + '.json')


def _host_of(url):
    match = re.match(r'^https://([^/]+)/', url or '')
    return match.group(1).lower() if match else ''


def _is_soft_404(raw):
    """True when an HTTP 200 body is actually the not-found shell.

    Two independent judges, because either alone is defeatable: the exact byte
    count the platform serves for a missing slug, and the markers that shell
    carries in its head. A real document can contain the phrase "page not
    found" in its prose, so the marker scan is capped at the head of the body
    where the shell puts its front matter.
    """
    if not raw:
        return False
    if len(raw) == SOFT_404_BYTES:
        return True
    head = raw[:SOFT_404_SCAN_BYTES].decode('utf-8', 'replace').lower()
    return any(marker in head for marker in SOFT_404_MARKERS)


def _validate_anchor(anchor, index, products, seen_ids, per_area):
    """Field-level errors for one anchor record. Returns a list of strings."""
    errors: List[str] = []
    where = 'anchors[{0}]'.format(index)
    if not isinstance(anchor, dict):
        return ['{0} is {1}, not an object'.format(where, type(anchor).__name__)]
    aid = anchor.get('id')
    if isinstance(aid, str) and aid:
        where = 'anchors[{0}] id={1}'.format(index, aid)

    unknown = sorted(set(anchor) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS))
    if unknown:
        errors.append('{0}: unknown field(s) {1}'.format(where, ', '.join(unknown)))
    missing = [f for f in REQUIRED_FIELDS if not str(anchor.get(f, '')).strip()]
    if missing:
        errors.append('{0}: missing required field(s) {1}'.format(where, ', '.join(missing)))

    role = anchor.get('role')
    if role is not None and role not in ROLES:
        errors.append('{0}: role {1!r} not in {2}'.format(where, role, '/'.join(ROLES)))
    kind = anchor.get('kind')
    if kind is not None and kind not in KINDS:
        errors.append('{0}: kind {1!r} not in {2}'.format(where, kind, '/'.join(KINDS)))

    product = anchor.get('product')
    if product is not None and products and product not in products:
        errors.append('{0}: product {1!r} is not registered in products{{}}'.format(where, product))

    url = anchor.get('url') or ''
    host = _host_of(url)
    if url:
        if kind == 'console-entry':
            if not any(host == c or host.endswith('.' + c) for c in CONSOLE_HOSTS):
                errors.append('{0}: console-entry url host {1!r} outside {2}'.format(
                    where, host, '/'.join(CONSOLE_HOSTS)))
        elif host not in DOC_HOSTS:
            errors.append('{0}: doc url host {1!r} is not {2} (China site only)'.format(
                where, host, '/'.join(DOC_HOSTS[0])))
        if kind == 'doc' and not url.endswith('.md'):
            errors.append('{0}: doc url must use the .md source form, got {1!r}'.format(where, url))

    sha = anchor.get('body_sha256')
    if kind == 'doc':
        if not sha:
            errors.append('{0}: kind=doc requires body_sha256'.format(where))
        elif not re.match(r'^[0-9a-f]{%d}$' % SHA_PREFIX_LEN, str(sha)):
            errors.append('{0}: body_sha256 {1!r} is not {2} lowercase hex chars'.format(
                where, sha, SHA_PREFIX_LEN))
    elif kind == 'console-entry':
        # A console page cannot be probed unauthenticated: every probe answers
        # 200 and then redirects to the login page, so a hash would be a hash
        # of the login shell. It is verified by citation instead.
        if not str(anchor.get('verified_by', '')).strip():
            errors.append('{0}: console-entry requires verified_by (it cannot be '
                          'liveness-probed)'.format(where))
        if sha:
            errors.append('{0}: console-entry must not carry body_sha256'.format(where))

    if role == 'conflict-hold' and not anchor.get('conflict_with'):
        errors.append('{0}: role=conflict-hold requires a non-empty conflict_with '
                      '(a conflict with one source is not a conflict)'.format(where))
    for entry in anchor.get('conflict_with') or []:
        if not isinstance(entry, dict) or not entry.get('url') or not entry.get('says'):
            errors.append('{0}: conflict_with entries need {{url, says}}'.format(where))
            break
    for field in LIST_FIELDS:
        value = anchor.get(field)
        if value is not None and not isinstance(value, list):
            errors.append('{0}: {1} must be a list'.format(where, field))
    terms = anchor.get('match_terms')
    if terms is not None:
        if not isinstance(terms, list):
            errors.append('{0}: match_terms must be a list'.format(where))
        elif not all(isinstance(t, str) and t.strip() for t in terms):
            errors.append('{0}: match_terms entries must be non-empty strings '
                          '(customer-side vocabulary)'.format(where))

    checked = anchor.get('checked_on')
    if checked and not _DATE_RE.match(str(checked)):
        errors.append('{0}: checked_on {1!r} is not YYYY-MM-DD'.format(where, checked))

    # A witness is how `area_correction` stops being prose: it names the file the
    # correction had to reach and the strings that prove it landed. The shape is
    # checked here because a malformed witness passes vacuously in the checker --
    # an empty must_contain asserts nothing, and a path outside the package (or
    # one escaping it) either fails closed as "missing file" or reads something
    # the checker was never meant to open.
    witness = anchor.get('correction_applied')
    if witness is not None:
        if not isinstance(witness, dict):
            errors.append('{0}: correction_applied must be an object {{file, '
                          'must_not_contain, must_contain}}'.format(where))
        else:
            extra = sorted(set(witness) - {'file', 'must_not_contain', 'must_contain'})
            if extra:
                errors.append('{0}: correction_applied unknown key(s) {1}'.format(
                    where, ', '.join(extra)))
            path = witness.get('file')
            if not isinstance(path, str) or not path.strip():
                errors.append('{0}: correction_applied.file must be a non-empty '
                              'string'.format(where))
            elif path.startswith('/') or '..' in path.split('/') \
                    or not path.startswith(CORRECTION_TARGET_DIRS):
                errors.append('{0}: correction_applied.file {1!r} must be a relative '
                              'path under {2}'.format(
                                  where, path, '/'.join(CORRECTION_TARGET_DIRS)))
            arms = 0
            for field in ('must_not_contain', 'must_contain'):
                value = witness.get(field)
                if value is None:
                    continue
                if not isinstance(value, list) or not all(
                        isinstance(s, str) and s.strip() for s in value):
                    errors.append('{0}: correction_applied.{1} must be a list of '
                                  'non-empty strings'.format(where, field))
                elif value:
                    arms += 1
            if not arms:
                errors.append('{0}: correction_applied asserts nothing -- at least one '
                              'of must_contain / must_not_contain must be non-empty'.format(where))

    demand = anchor.get('demand_tickets')
    if demand is not None and (not isinstance(demand, int) or isinstance(demand, bool)
                               or demand < 0):
        errors.append('{0}: demand_tickets {1!r} must be a non-negative integer '
                      '(the measured support-citation count)'.format(where, demand))

    # A shared anchor is citable from several areas, so it must name them. Without
    # that list it would either be unreachable or reachable from everywhere.
    area = anchor.get('area')
    if area == SHARED_AREA:
        cross = anchor.get('cross_area')
        if not isinstance(cross, list) or not cross:
            errors.append('{0}: area={1!r} requires a non-empty cross_area list'.format(
                where, SHARED_AREA))
        elif not all(isinstance(x, str) and x and x != SHARED_AREA for x in cross):
            errors.append('{0}: cross_area entries must be non-empty real area '
                          'names'.format(where))
        if anchor.get('scene_uid') != SHARED_SCENE:
            errors.append('{0}: shared anchors use scene_uid {1!r}, since no single '
                          'contract scene owns them'.format(where, SHARED_SCENE))
        if isinstance(aid, str) and not aid.startswith(SHARED_AREA + '__'):
            errors.append('{0}: shared anchor ids start with {1!r}'.format(
                where, SHARED_AREA + '__'))

    # An override may only refine an area that may already cite the anchor, so it
    # can never widen reachability as a side effect of changing a role.
    overrides = anchor.get('role_overrides')
    if overrides is not None:
        if not isinstance(overrides, dict):
            errors.append('{0}: role_overrides must be an object keyed by area'.format(where))
        else:
            allowed = set(anchor.get('cross_area') or []) if area == SHARED_AREA \
                else {area} if isinstance(area, str) else set()
            for key, value in sorted(overrides.items()):
                if not isinstance(key, str) or not key:
                    errors.append('{0}: role_overrides key {1!r} is not an area name'.format(
                        where, key))
                elif allowed and key not in allowed:
                    errors.append('{0}: role_overrides names {1!r}, which may not cite this '
                                  'anchor (not in cross_area)'.format(where, key))
                if value not in ROLES:
                    errors.append('{0}: role_overrides[{1!r}] = {2!r} not in {3}'.format(
                        where, key, value, '/'.join(ROLES)))

    if isinstance(aid, str) and aid:
        if aid in seen_ids:
            errors.append('{0}: duplicate id'.format(where))
        else:
            seen_ids.add(aid)
        area = anchor.get('area')
        if isinstance(area, str) and area:
            per_area[area] = per_area.get(area, 0) + 1
            if per_area[area] == MAX_ANCHORS_PER_AREA + 1:
                errors.append('area {0!r} exceeds the {1}-anchor cap'.format(
                    area, MAX_ANCHORS_PER_AREA))
    return errors


def _validate_document(doc):
    """Whole-file validation. Returns (anchors, errors); anchors is [] when
    errors is non-empty, because a partial anchor set is a different promise
    than the one that was adjudicated."""
    if not isinstance(doc, dict):
        return [], ['top level is {0}, not an object'.format(type(doc).__name__)]
    errors: List[str] = []
    if doc.get('schema') != SCHEMA:
        errors.append('schema {0!r} != {1!r}'.format(doc.get('schema'), SCHEMA))
    if doc.get('site') != 'cn':
        errors.append('site {0!r} != \'cn\' (this package cites the China site only)'.format(
            doc.get('site')))
    anchors = doc.get('anchors')
    if not isinstance(anchors, list) or not anchors:
        return [], errors + ['anchors must be a non-empty list']
    if len(anchors) > MAX_ANCHORS_TOTAL:
        errors.append('{0} anchors exceeds the {1} total cap'.format(
            len(anchors), MAX_ANCHORS_TOTAL))
    products = doc.get('products')
    if not isinstance(products, dict) or not products:
        errors.append('products{{} registry must be a non-empty object')
        products = {}
    seen_ids: set = set()
    per_area: Dict[str, int] = {}
    for index, anchor in enumerate(anchors):
        errors.extend(_validate_anchor(anchor, index, products, seen_ids, per_area))
    return ([] if errors else list(anchors)), errors


def load_anchors(path=None):
    """Read and validate the anchor file as one unit.

    Returns {'verdict', 'anchors', 'detail'}. verdict is one of:
      loaded            the file is valid and usable
      disabled          ECS_DOC_REFS=off; the leg is switched off on purpose
      anchors-missing   the file is not there (a package built before the leg)
      anchors-unreadable  not valid JSON / not readable
      anchors-rejected  validation failed; detail carries every error
    Never raises: the dispatcher must be able to run the area regardless.
    """
    if _disabled():
        return {'verdict': 'disabled', 'anchors': [], 'detail': '{0}=off'.format(ENABLE_ENV)}
    target = path or os.path.join(PACKAGE_ROOT, ANCHORS_RELPATH)
    try:
        with open(target, 'rb') as handle:
            raw = handle.read()
    except FileNotFoundError:
        return {'verdict': 'anchors-missing', 'anchors': [], 'detail': target}
    except OSError as exc:
        return {'verdict': 'anchors-unreadable', 'anchors': [], 'detail': str(exc)}
    try:
        doc = json.loads(raw.decode('utf-8'))
    except (ValueError, UnicodeDecodeError) as exc:
        _warn('anchor file is not valid JSON: {0}'.format(exc))
        return {'verdict': 'anchors-unreadable', 'anchors': [], 'detail': str(exc)}
    anchors, errors = _validate_document(doc)
    if errors:
        for error in errors[:12]:
            _warn('anchor file rejected: {0}'.format(error))
        if len(errors) > 12:
            _warn('anchor file rejected: ... and {0} more error(s)'.format(len(errors) - 12))
        return {'verdict': 'anchors-rejected', 'anchors': [],
                'detail': '{0} error(s); first: {1}'.format(len(errors), errors[0])}
    return {'verdict': 'loaded', 'anchors': anchors,
            'detail': '{0} anchors'.format(len(anchors))}


def _tokens(text):
    """Lexical keys of a string: ascii words plus CJK bigrams. Pure.

    Bigrams rather than a dictionary, because the anchor claims and the area
    output are both Chinese prose and this package carries no segmenter and no
    third-party dependency. A bigram overlap is a coarse relevance signal, which
    is all `lookup` is allowed to use -- it selects, it does not interpret.
    """
    raw = (text or '').lower()
    out = set(re.findall(r'[a-z0-9]{3,}', raw))
    joined = re.sub(r'[^\u4e00-\u9fff]', '', raw)
    for i in range(len(joined) - 1):
        out.add(joined[i:i + 2])
    return out


def _overlap(claim, text_tokens):
    """Fraction of the claim's tokens present in `text_tokens`. Pure."""
    claim_tokens = _tokens(claim)
    if not claim_tokens or not text_tokens:
        return 0.0
    return len(claim_tokens & text_tokens) / float(len(claim_tokens))


def effective_role(anchor, area=None):
    """The role that applies when `area` cites `anchor`. Pure.

    A shared anchor does not have one role, because whether the official body
    adds anything depends on what the citing area already says. Measured case:
    `snapshot-billing-cleanup`'s own Important Notes already state "No service
    switch exists to 'close' snapshots" and "bill by capacity and duration, per
    region", so for that area the snapshot anchors are `verify-only` -- the leg
    may back the statement with a URL but must not present it as new knowledge.
    For `disk-attach-os-visibility`, which says nothing about snapshot billing,
    the same anchor is `doc-answers`.

    `role_overrides` is adjudicated build-time data keyed by area. An override
    for an area that is not in `cross_area` is rejected at validation, so an
    override can never make an anchor reachable from an area that did not
    declare it.
    """
    if not isinstance(anchor, dict):
        return ''
    base = anchor.get('role', '')
    if not area:
        return base
    overrides = anchor.get('role_overrides')
    if isinstance(overrides, dict):
        return overrides.get(area) or base
    return base


def _term_hits(anchor, text):
    """How many of the anchor's adjudicated customer terms appear verbatim.

    Split out of `_relevance` because `lookup` needs the count as a hard gate,
    not only as a score: an anchor whose terms never fire matched on claim/title
    overlap alone, which is bigram intersection with the anchor's own wording and
    is shared by every anchor sourced from the same page. See lookup().
    """
    lower = (text or '').lower()
    return sum(1 for t in (anchor.get('match_terms') or [])
               if isinstance(t, str) and t.strip() and t.strip().lower() in lower)


def _relevance(anchor, text):
    """How strongly `anchor` is indicated by the run's own text. Pure.

    Two signals, because neither alone reaches the vocabulary a customer
    actually uses:

      claim/title overlap   catches the question phrased in the document's own
                            words ("快照计费周期")
      match_terms substring catches the question phrased in the customer's words
                            ("删不掉", "提现不了", "会不会丢数据")

    Measured need for the second signal: ranking on claim overlap alone put the
    wrong anchor first for "快照删不掉" (the claim says "不允许直接删除", and the
    bigrams of 删不掉 never meet 删除) and dropped the highest-cited document in
    the whole corpus -- create-a-snapshot, 4,403 tickets, the warning a support
    engineer pastes before any destructive action -- for "初始化会不会丢数据",
    because that document's claim lists 回滚云盘/更换操作系统 and never says
    初始化. match_terms is adjudicated build-time data, not a runtime guess.

    The substring signal is weighted above the overlap signal: a customer term
    present verbatim is stronger evidence than a partial bigram intersection.
    It is counted, not divided by the size of the term list -- a rich vocabulary
    must not be penalised for being rich, so one hit is already a strong signal
    and two saturate it.
    """
    raw = text or ''
    term_score = min(1.0, _term_hits(anchor, raw) * TERM_HIT_WEIGHT)
    text_tokens = _tokens(raw)
    overlap = max(_overlap(anchor.get('claim', ''), text_tokens),
                  _overlap(anchor.get('title', ''), text_tokens))
    return term_score + overlap


def lookup(anchors, area, scene_uid=None, roles=None, text=None,
           limit=MAX_CITED_PER_RUN, question=None):
    """Select the anchors that apply to one dispatch. Pure; no I/O.

    The pool is the area's own anchors followed by the shared anchors that name
    this area in `cross_area` (see SHARED_AREA). Narrowing is applied in order
    and each stage is allowed to empty the pool:

      area       the only mandatory key
      scene_uid  when the caller knows the contract scene. It narrows the area's
                 own anchors only; shared anchors are not scene-specific. A
                 scene that binds no anchor returns `no-anchor` and deliberately
                 does NOT fall back to the area's other scenes, because citing
                 another scene's document into this answer is a promise no one
                 adjudicated.
      roles      e.g. the dispatcher keeps `verify-only` out of the
                 customer-facing block, since those carry only a freshness
                 signal.
      text       the run's own question/output. Used only to rank when the pool
                 is larger than `limit`.
      question   the customer's question ALONE, without area output. When given,
                 an anchor must score >= MIN_RELEVANCE against it AND land at
                 least one of its own `match_terms` in it to be citable at all,
                 so area output can rank the survivors but can never lift an
                 irrelevant anchor into the answer. Failing the term test returns
                 reason `no-term-hit`, distinct from `below-floor`.

    `limit` exists because one contract scene can bind many anchors (the busiest
    in the shipped file binds 11) and a support engineer cites one or two
    documents, not eleven. When `text` is given the survivors are the highest
    lexical overlap; otherwise file order is kept, which puts the area's own
    adjudicated anchors ahead of the shared warnings. `omitted` counts what was
    dropped so the dispatcher can leave a trace instead of silently under-citing.

    verdict: matched | matched-narrowed | matched-truncated | no-anchor | no-area
    """
    if not area:
        return {'verdict': 'no-area', 'anchors': [], 'omitted': 0,
                'detail': 'empty area'}
    records = [a for a in (anchors or []) if isinstance(a, dict)]
    own = [a for a in records if a.get('area') == area]
    if scene_uid and scene_uid != SHARED_SCENE:
        own = [a for a in own if a.get('scene_uid') == scene_uid]
    # Shared anchors come after the area's own, so a file-order truncation keeps
    # the area's adjudicated answer rather than crowding it out with a generic
    # warning. With text= the overlap ranking decides instead. A named contract
    # scene still gets the shared warnings: they are not scene-specific.
    shared = [a for a in records
              if a.get('area') == SHARED_AREA and area in (a.get('cross_area') or [])]
    pool = own + shared
    if not pool:
        scene_unbound = bool(scene_uid and not own and not shared)
        detail = ('scene {0} binds no anchor and area {1} has no shared anchor; '
                  'not widened to the rest of the area'.format(scene_uid, area)
                  if scene_unbound
                  else 'no anchor recorded for area {0}'.format(area))
        return {'verdict': 'no-anchor', 'anchors': [], 'omitted': 0,
                'reason': 'scene-unbound' if scene_unbound else 'area-unanchored',
                'detail': detail}
    if question and str(question).strip():
        # Citable at all is decided by the customer's question alone; `text` (which
        # also carries area output) only ranks the survivors. See MIN_RELEVANCE.
        relevant = [a for a in pool if _relevance(a, question) >= MIN_RELEVANCE]
        if not relevant:
            return {'verdict': 'no-anchor', 'anchors': [], 'omitted': 0,
                    'reason': 'below-floor',
                    'detail': 'none of the {0} anchor(s) reachable from area {1} '
                              'cleared the relevance floor {2} against the customer '
                              'question, so no document may be cited'.format(
                                  len(pool), area, MIN_RELEVANCE)}
        pool = relevant
        # Clearing the floor is necessary but not sufficient: a match_term must
        # actually fire. The floor is reachable by claim/title overlap alone, and
        # every anchor taken from one page shares that page's title, so overlap
        # pulls in siblings from the same document that do not answer the
        # question. Measured on the shipped file: for "系统换成Linux之后，原来的
        # 数据盘挂载后读不出来" the leg cited the MBR 2 TiB limit and the 云助手
        # init constraint alongside the cross-type rule that does answer it - both
        # from the same initialize-a-data-disk page, both overlap-only, neither
        # term present in the question. Two of three citation slots spent on noise
        # is worse than one citation, because it reads as three sources agreeing.
        termed = [a for a in pool if _term_hits(a, question)]
        if not termed:
            return {'verdict': 'no-anchor', 'anchors': [], 'omitted': 0,
                    'reason': 'no-term-hit',
                    'detail': 'the {0} anchor(s) reachable from area {1} that cleared '
                              'the relevance floor matched only on claim/title overlap '
                              'with the customer question, not on any adjudicated '
                              'customer term, so no document may be cited'.format(
                                  len(pool), area)}
        pool = termed
    if roles:
        wanted = tuple(roles)
        pool = [a for a in pool if a.get('role') in wanted]
        if not pool:
            return {'verdict': 'no-anchor', 'anchors': [], 'omitted': 0,
                    'reason': 'role-filtered',
                    'detail': 'no anchor for {0} with role in {1}'.format(
                        area, '/'.join(wanted))}
    if text:
        # Ties go to the area's own anchor over a shared one, for the same
        # reason file-order truncation does: the own anchor was adjudicated
        # for this area, the shared one is a generic warning. Measured need:
        # without it, "云盘扩容后分区没变大，2T以上的盘用不了" ranked the
        # snapshot warning (term hit on 扩容后) above the MBR 2 TiB limit
        # that actually answers the question.
        #
        # Ranking runs whether or not the cap bites, because the FIRST cited
        # anchor is the one the customer reads first - order is part of the
        # answer, not only a truncation device. Measured need: the relevance
        # floor shrank "快照删除按钮是灰的，删不掉怎么办" to two anchors, the
        # cap stopped biting, and file order then put a 0.143 shared billing
        # warning above the 1.111 document that actually answers it.
        pool = [anchor for _, anchor in sorted(
            enumerate(pool),
            key=lambda pair: (-_relevance(pair[1], text),
                              pair[1].get('area') == SHARED_AREA,
                              pair[0]))]
    if limit is not None and limit >= 0 and len(pool) > limit:
        return {'verdict': 'matched-narrowed' if text else 'matched-truncated',
                'anchors': pool[:limit],
                'omitted': len(pool) - limit,
                'detail': ('{0} of {1} anchor(s) kept by overlap with the run text'
                           .format(limit, len(pool)) if text else
                           '{0} of {1} anchor(s) kept in file order; pass text= '
                           'to rank instead'.format(limit, len(pool)))}
    return {'verdict': 'matched', 'anchors': pool, 'omitted': 0,
            'detail': '{0} anchor(s)'.format(len(pool))}


def _read_cache(url):
    """Fresh cached body for `url`, or None. Sidecar carries url+fetched_at so a
    hash collision across URLs cannot serve the wrong document."""
    body_path, meta_path = _cache_paths(url)
    try:
        with open(meta_path, 'rb') as handle:
            meta = json.loads(handle.read().decode('utf-8'))
    except (OSError, ValueError):
        return None
    if meta.get('url') != url:
        return None
    try:
        fetched = datetime.datetime.fromisoformat(str(meta.get('fetched_at', '')))
    except ValueError:
        return None
    ttl = _cache_ttl_days()
    age_days = (datetime.datetime.now(fetched.tzinfo) - fetched).total_seconds() / 86400.0
    if age_days > ttl:
        return None
    try:
        with open(body_path, 'rb') as handle:
            raw = handle.read()
    except OSError:
        return None
    if not raw:
        return None
    return {'raw': raw, 'fetched_at': meta.get('fetched_at', ''), 'source': 'cache'}


def _write_cache(url, raw):
    """Best effort. A read-only or full cache must not fail the leg."""
    body_path, meta_path = _cache_paths(url)
    try:
        os.makedirs(os.path.dirname(body_path), exist_ok=True)
        with open(body_path, 'wb') as handle:
            handle.write(raw)
        meta = {'url': url, 'fetched_at': datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec='seconds'), 'bytes': len(raw)}
        with open(meta_path, 'wb') as handle:
            handle.write(json.dumps(meta).encode('utf-8'))
        os.chmod(body_path, 0o600)
        os.chmod(meta_path, 0o600)
        return True
    except OSError as exc:
        _warn('body cache write failed ({0}); continuing uncached'.format(exc))
        return False


def body(url, kind='doc', use_cache=True, timeout=FETCH_TIMEOUT_SECONDS):
    """Fetch one official body. Returns {'verdict', 'text', 'sha256', ...}.

    At most one network call, and only for `kind='doc'`. verdict is one of:
      fetched               live body read
      cached                body came from the on-disk cache, no HTTP call
      skipped-console-entry console URLs are not probeable unauthenticated
      soft-404              HTTP 200 carrying the not-found shell
      not-found             HTTP 404
      rejected              HTTP 4xx/5xx other than 404
      too-large             body over MAX_BODY_BYTES; not truncated, because a
                            truncated body would hash to nothing meaningful
      blocked               egress restricted, DNS failed, TLS rejected, timeout
      malformed-url         the anchor url is not an https URL on an allowed host
      disabled              the leg is switched off
    """
    if _disabled():
        return {'verdict': 'disabled', 'url': url, 'text': '', 'sha256': '', 'bytes': 0}
    if kind == 'console-entry':
        return {'verdict': 'skipped-console-entry', 'url': url, 'text': '',
                'sha256': '', 'bytes': 0,
                'detail': 'console pages answer 200 then redirect to login when '
                          'probed unauthenticated; verified by citation only'}
    host = _host_of(url)
    if host not in DOC_HOSTS or not url.endswith('.md'):
        return {'verdict': 'malformed-url', 'url': url, 'text': '', 'sha256': '', 'bytes': 0,
                'detail': 'expected https://{0}/....md'.format(DOC_HOSTS[0])}
    if use_cache:
        hit = _read_cache(url)
        if hit is not None:
            raw = hit['raw']
            return {'verdict': 'cached', 'url': url, 'source': 'cache',
                    'fetched_at': hit['fetched_at'], 'bytes': len(raw),
                    'sha256': hashlib.sha256(raw).hexdigest()[:SHA_PREFIX_LEN],
                    'text': raw.decode('utf-8', 'replace')}
    request = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT, 'Accept': 'text/markdown, text/plain;q=0.9, */*;q=0.5'})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_BODY_BYTES + 1)
            status = getattr(response, 'status', 200)
    except urllib.error.HTTPError as exc:
        verdict = 'not-found' if exc.code == 404 else 'rejected'
        detail = 'HTTP {0}'.format(exc.code)
        if verdict == 'rejected':
            _warn('{0}: {1}'.format(url, detail))
        return {'verdict': verdict, 'url': url, 'text': '', 'sha256': '', 'bytes': 0,
                'detail': detail, 'http_status': exc.code}
    except (urllib.error.URLError, OSError, ValueError) as exc:
        _warn('{0}: egress blocked or unreachable ({1})'.format(url, str(exc)[:160]))
        return {'verdict': 'blocked', 'url': url, 'text': '', 'sha256': '', 'bytes': 0,
                'detail': str(exc)[:200]}
    if len(raw) > MAX_BODY_BYTES:
        _warn('{0}: body exceeds {1} bytes; not truncated'.format(url, MAX_BODY_BYTES))
        return {'verdict': 'too-large', 'url': url, 'text': '', 'sha256': '',
                'bytes': len(raw), 'detail': 'over the {0}-byte ceiling'.format(MAX_BODY_BYTES)}
    if _is_soft_404(raw):
        _warn('{0}: HTTP {1} but the body is the not-found shell ({2} bytes); '
              'the slug is wrong or the page moved'.format(url, status, len(raw)))
        return {'verdict': 'soft-404', 'url': url, 'text': '', 'sha256': '',
                'bytes': len(raw), 'detail': 'HTTP 200 carrying a 404 body',
                'http_status': status}
    if use_cache:
        _write_cache(url, raw)
    return {'verdict': 'fetched', 'url': url, 'source': 'network', 'bytes': len(raw),
            'http_status': status,
            'sha256': hashlib.sha256(raw).hexdigest()[:SHA_PREFIX_LEN],
            'text': raw.decode('utf-8', 'replace')}


def verify(anchor, fetched=None, use_cache=True, area=None):
    """Check one anchor against the live official body.

    Returns {'verdict', ...} where verdict is one of:
      hash-match      body still hashes to the adjudicated value
      hash-drift      the official body changed since checked_on; the anchor's
                      excerpt is now a snapshot of a document that has moved, so
                      it must not be quoted as current
      not-required    conflict-hold: the answer is the pre-adjudicated
                      customer_wording, which never quotes a body, so spending a
                      fetch on it buys nothing
      no-hash         the anchor carries no body_sha256 to compare against
      not-checkable   console-entry: no unauthenticated probe exists
      <body verdict>  the fetch itself failed (soft-404 / blocked / ...); the
                      body verdict is passed through unchanged so the
                      dispatcher can tell "changed" from "unreachable"
    `fetched` lets the caller reuse one body read across several anchors that
    share a URL, which is how the per-run HTTP budget stays at one call.
    """
    if not isinstance(anchor, dict):
        return {'verdict': 'no-hash', 'detail': 'anchor is not an object'}
    if effective_role(anchor, area) == 'conflict-hold':
        return {'verdict': 'not-required', 'url': anchor.get('url', ''),
                'anchor_id': anchor.get('id', ''),
                'detail': 'conflict-hold answers from customer_wording and names '
                          'both sources; no body read is needed at runtime'}
    kind = anchor.get('kind', 'doc')
    url = anchor.get('url', '')
    if kind == 'console-entry':
        return {'verdict': 'not-checkable', 'url': url, 'anchor_id': anchor.get('id', ''),
                'detail': anchor.get('verified_by', 'official-doc-citation')}
    expected = str(anchor.get('body_sha256', '')).strip()
    if not expected:
        return {'verdict': 'no-hash', 'url': url, 'anchor_id': anchor.get('id', ''),
                'detail': 'anchor carries no body_sha256'}
    got = fetched if fetched is not None else body(url, kind=kind, use_cache=use_cache)
    out = {'url': url, 'anchor_id': anchor.get('id', ''), 'expected': expected,
           'actual': got.get('sha256', ''), 'bytes': got.get('bytes', 0),
           'source': got.get('source', ''), 'fetch_verdict': got.get('verdict', '')}
    if got.get('verdict') not in ('fetched', 'cached'):
        out['verdict'] = got.get('verdict', 'blocked')
        out['detail'] = got.get('detail', '')
        return out
    if got.get('sha256', '') == expected:
        out['verdict'] = 'hash-match'
        return out
    out['verdict'] = 'hash-drift'
    out['detail'] = ('official body changed since {0}: {1} != {2}'.format(
        anchor.get('checked_on', '?'), expected, got.get('sha256', '')))
    _warn('{0}: {1}'.format(url, out['detail']))
    return out


# "The official body could not be read, and the attempt was made." The excerpt
# snapshot, copied verbatim from that body on checked_on, is then the best
# available evidence -- refusing to use it would leave the customer with nothing
# on a question the project has already adjudicated. 'no-hash' and 'unchecked'
# used to sit here; they are NOT_ATTEMPTED_STATES now, because their snapshot
# fallback is identical but their customer-facing reason is not.
UNREADABLE_STATES = frozenset((
    'blocked', 'soft-404', 'not-found', 'rejected', 'too-large',
    'malformed-url', 'disabled',
))
# "The official body was read and it differs." The opposite case: the snapshot
# is now a quote from a document that has moved, so it is withheld. This split
# is what keeps the excerpt fallback from becoming a stale-promise machine.
DRIFTED_STATES = frozenset(('hash-drift',))
# "Nobody asked the site." `unchecked` is what the dispatcher records when this
# run's read budget went to higher-ranked citations first; `no-hash` is what
# verify() returns without fetching when the anchor carries nothing to compare.
# Both fall back to the same snapshot as UNREADABLE_STATES, but the customer-
# facing reason must not claim a read that failed when no read was attempted:
# measured on "数据盘挂载不上，实例在杭州，云盘买在上海", which degraded on
# create-a-snapshot -- a page the freshness gate had verified live minutes before.
NOT_ATTEMPTED_STATES = frozenset(('unchecked', 'no-hash'))


def render_citation(anchor, verification=None, area=None):
    """Copy-ready citation lines for one anchor. Pure; no I/O, no interpretation.

    Returns {'verdict', 'lines', 'customer_lines', 'role'}. `lines` is the
    machine-readable block the dispatcher appends (`DOC-REF:` prefixed, so
    grading can key on it); `customer_lines` is what may be shown to the
    customer. `area` selects the effective role (see effective_role).

    The role decides what may be promised:

      doc-answers    the document answers the customer directly: quote the
                     claim, name the document, give the URL
      promote        the official wording replaces the area's [support-position]
                     wording: same as doc-answers plus the correction note
      verify-only    the area already states this correctly, so no new claim is
                     added -- only the citation that backs it, which is still
                     what a support engineer hands the customer
      conflict-hold  two official sources disagree: both are named and the
                     pre-adjudicated customer_wording is used. The leg never
                     picks a side.

    The verification state then decides whether the body may be quoted live or
    only as a dated snapshot (see UNREADABLE_STATES / DRIFTED_STATES). Every
    outcome is named in `lines`, so a degraded run leaves a trace rather than
    quietly promising less.
    """
    if not isinstance(anchor, dict):
        return {'verdict': 'not-an-anchor', 'lines': [], 'customer_lines': [], 'role': ''}
    role = effective_role(anchor, area)
    if role not in ROLES:
        return {'verdict': 'unknown-role', 'lines': [], 'customer_lines': [], 'role': role}

    aid = anchor.get('id', '')
    url = anchor.get('url', '')
    human_url = url[:-3] if url.endswith('.md') else url
    title = anchor.get('title', '')
    excerpt = str(anchor.get('excerpt', '')).strip()
    claim = str(anchor.get('claim', '')).strip()
    checked = anchor.get('checked_on', '?')
    state = (verification or {}).get('verdict', '') or 'unchecked'

    lines = ['DOC-REF: [{0}] {1} role={2} kind={3} state={4}'.format(
        aid, title, role, anchor.get('kind', 'doc'), state)]
    lines.append('DOC-REF-URL: {0}'.format(url))
    for alias in anchor.get('alias') or []:
        lines.append('DOC-REF-ALIAS: {0}'.format(alias))
    for covered in anchor.get('also_covered_by') or []:
        lines.append('DOC-REF-ALSO: {0}'.format(covered))
    if anchor.get('scope_limit'):
        lines.append('DOC-REF-SCOPE-LIMIT: {0}'.format(anchor['scope_limit']))

    def out(verdict, customer):
        return {'verdict': verdict, 'lines': lines,
                'customer_lines': customer, 'role': role}

    # --- conflict-hold: answered from the adjudicated wording, never from a
    # --- body, so it is immune to both drift and unreachability.
    if role == 'conflict-hold':
        wording = str(anchor.get('customer_wording', '')).strip()
        conflicts = [e for e in (anchor.get('conflict_with') or []) if isinstance(e, dict)]
        lines.append('DOC-REF-CONFLICT: {0}'.format(claim))
        for entry in conflicts:
            lines.append('DOC-REF-CONFLICT-SOURCE: {0} -- {1}'.format(
                entry.get('url', ''), entry.get('says', '')))
        if not wording:
            # No adjudicated wording exists, so no promise may be rendered.
            lines.append('DOC-REF-DEGRADED: conflict-hold without customer_wording')
            return out('degraded', [])
        lines.append('DOC-REF-CUSTOMER-WORDING: {0}'.format(wording))
        # A range answer with no source reads as a promise the platform made. The
        # customer gets both pages and what each says, which is what a support
        # engineer pastes: the disagreement is the reason the answer is a range.
        customer = [wording]
        if conflicts:
            customer.append('Official pages state this differently, so the range '
                            'above is not a single commitment:')
            for entry in conflicts:
                source_url = str(entry.get('url', ''))
                customer.append('- {0} ({1})'.format(
                    entry.get('says', ''),
                    source_url[:-3] if source_url.endswith('.md') else source_url))
        return out('conflict-held', customer)

    # --- drift: the document moved. Nothing here may be quoted as current.
    if state in DRIFTED_STATES:
        lines.append('DOC-REF-WITHHELD: official body changed since {0}; the '
                     'snapshot excerpt is not quotable and the area statement '
                     'needs re-adjudication'.format(checked))
        _warn('{0}: body drifted; citation withheld'.format(aid))
        return out('withheld-drift', [])

    # not-checkable counts as verified: a console entry is verified by official
    # citation because no unauthenticated probe of it exists, and labelling it
    # "snapshot" would imply a document we failed to read.
    verified = state in ('hash-match', 'not-checkable')
    if state == 'hash-match':
        basis = 'source: {0}'.format(title)
    elif state == 'not-checkable':
        basis = 'source: {0} ({1})'.format(
            title, (verification or {}).get('detail', 'official-doc-citation'))
    elif state in NOT_ATTEMPTED_STATES:
        basis = ('source: {0}, checked on {1}; the official body was not re-read '
                 'this run'.format(title, checked))
        if excerpt:
            lines.append('DOC-REF-SNAPSHOT: {0}'.format(excerpt))
        elif role != 'verify-only':
            lines.append('DOC-REF-SNAPSHOT-MISSING: no excerpt recorded, so the '
                         'claim cannot be sourced offline')
    else:
        basis = ('source: {0}, checked on {1}; the official body could not be '
                 're-read online this run'.format(title, checked))
        if excerpt:
            lines.append('DOC-REF-SNAPSHOT: {0}'.format(excerpt))
        elif role != 'verify-only':
            lines.append('DOC-REF-SNAPSHOT-MISSING: no excerpt recorded, so the '
                         'claim cannot be sourced offline')

    if role == 'verify-only':
        lines.append('DOC-REF-FRESHNESS: area statement {0} the official body '
                     'as of {1}'.format(
                         'agrees with' if verified else 'was last checked against',
                         checked))
        customer = ['This conclusion agrees with the official page ({0}): {1}'
                    .format(basis, human_url)]
        return out('verified-only' if verified else 'verified-only-snapshot', customer)

    # The claim, title and wording stay in their original language on purpose:
    # they are copied verbatim from the China-site official page, and translating
    # them would make this module the author of a promise no document makes.
    # Only the sentence frame around them is English, matching the rest of the
    # answer block (MUST 4.1.2 keeps SKILL.md English-only, so a frame the agent
    # has to be told about in paraphrase is a frame it cannot match verbatim).
    customer = ['{0} ({1})'.format(claim, basis)]
    if anchor.get('kind') == 'console-entry':
        customer.append('Console entry: {0}'.format(url))
    else:
        customer.append('Official page: {0}'.format(human_url))
    if verified and excerpt:
        lines.append('DOC-REF-EXCERPT: {0}'.format(excerpt))
    if role == 'promote' and anchor.get('area_correction'):
        lines.append('DOC-REF-PROMOTED-FROM: {0}'.format(anchor['area_correction']))
    return out('cited-verified' if verified else 'cited-snapshot', customer)


def selftest(verbose=False):
    """Inline boundary assertions over the pure functions. No network, no disk
    write, and no dependency on the shipped anchor file existing.

    Returns (passed, failures). Run as `python3 scripts/_doc_refs.py selftest`.
    """
    passed = 0
    failures: List[str] = []

    def check(name, got, want):
        nonlocal passed
        if got == want:
            passed += 1
        else:
            failures.append('{0}: got {1!r}, want {2!r}'.format(name, got, want))

    check('ua_carries_real_package_name',
          USER_AGENT.startswith('AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/'),
          True)
    check('ua_carries_skill_version', ' skill-version/' in USER_AGENT, True)
    check('ua_session_is_32_hex',
          len(_DOC_REFS_SESSION_ID) == 32
          and all(c in '0123456789abcdef' for c in _DOC_REFS_SESSION_ID), True)
    check('ua_never_internal_eval', 'internal-eval' in USER_AGENT.lower(), False)

    products = {'ecs': '云服务器 ECS', 'user-center': '费用与成本'}
    good_doc = {
        'id': 'a__one', 'area': 'a', 'scene_uid': 'a__q1', 'role': 'doc-answers',
        'kind': 'doc', 'claim': 'c', 'product': 'ecs', 'checked_on': '2026-11-05',
        'url': 'https://help.aliyun.com/zh/ecs/x.md', 'title': 'T',
        'body_sha256': 'a' * 12, 'excerpt': 'e', 'conflict_with': [],
    }
    good_console = {
        'id': 'a__two', 'area': 'a', 'scene_uid': 'a__q2', 'role': 'promote',
        'kind': 'console-entry', 'claim': 'c', 'product': 'user-center',
        'checked_on': '2026-11-05', 'url': 'https://billing-cost.console.aliyun.com/refund/',
        'title': 'T', 'verified_by': 'official-doc-citation', 'alias': ['https://u.example/'],
    }
    good_conflict = dict(good_doc, id='a__three', role='conflict-hold',
                         customer_wording='W',
                         conflict_with=[{'url': 'https://help.aliyun.com/zh/ecs/y.md',
                                         'says': 'S'}])

    # --- normal ---
    doc = {'schema': SCHEMA, 'site': 'cn', 'products': products,
           'anchors': [good_doc, good_console, good_conflict]}
    anchors, errors = _validate_document(doc)
    check('valid_document_has_no_errors', errors, [])
    check('valid_document_keeps_all_anchors', len(anchors), 3)
    check('lookup_by_area', lookup(anchors, 'a')['verdict'], 'matched')
    check('lookup_area_count', len(lookup(anchors, 'a')['anchors']), 3)
    # good_conflict deliberately shares scene_uid 'a__q1' with good_doc: one
    # contract scene carries many anchors in the shipped file (the busiest
    # binds 11), so scene narrowing must return all of them, not one.
    check('lookup_by_scene_returns_every_anchor_on_that_scene',
          len(lookup(anchors, 'a', scene_uid='a__q1')['anchors']), 2)
    check('lookup_by_unique_scene',
          len(lookup(anchors, 'a', scene_uid='a__q2')['anchors']), 1)
    # No widening: an unbound scene must not inherit the area's other anchors.
    unbound = lookup(anchors, 'a', scene_uid='a__q999')
    check('lookup_by_unbound_scene_does_not_widen', unbound['verdict'], 'no-anchor')
    check('lookup_by_unbound_scene_returns_nothing', unbound['anchors'], [])
    check('lookup_unknown_area', lookup(anchors, 'zz')['verdict'], 'no-anchor')
    check('lookup_empty_area', lookup(anchors, '')['verdict'], 'no-area')
    check('lookup_role_filter',
          len(lookup(anchors, 'a', roles=('doc-answers',))['anchors']), 1)
    check('lookup_role_filter_empties',
          lookup(anchors, 'a', scene_uid='a__q1', roles=('verify-only',))['verdict'],
          'no-anchor')
    check('lookup_none_anchors', lookup(None, 'a')['verdict'], 'no-anchor')

    # --- relevance floor: the customer's question alone decides citability ---
    floored = [dict(good_doc, id='a__hit', match_terms=['退订']),
               dict(good_doc, id='a__miss', match_terms=['快照'],
                    claim='快照按地域单独结算', title='快照计费规则')]
    refund_q = '退订之后钱退到哪里了'
    check('floor_absent_keeps_everything',
          len(lookup(floored, 'a', text=refund_q)['anchors']), 2)
    check('floor_drops_what_the_question_does_not_reach',
          [x['id'] for x in lookup(
              floored, 'a', text=refund_q + '\n快照计费规则',
              question=refund_q)['anchors']], ['a__hit'])
    none_left = lookup(floored, 'a', text='快照 计费 地域',
                       question='云盘扩容后分区没变大')
    check('floor_can_empty_the_pool', none_left['verdict'], 'no-anchor')
    check('floor_returns_nothing_when_it_empties', none_left['anchors'], [])
    check('floor_says_why', 'relevance floor' in none_left['detail'], True)
    check('floor_ignores_a_blank_question',
          len(lookup(floored, 'a', text='快照', question='   ')['anchors']), 2)
    check('floor_is_applied_before_the_role_filter',
          lookup(floored, 'a', question=refund_q,
                 roles=('verify-only',))['verdict'], 'no-anchor')
    # Regression pin: ranking used to run only when the cap bit. A pool that the
    # floor shrank below the cap came back in file order, which put a weakly
    # related anchor first in the customer's answer.
    under_cap = [dict(good_doc, id='a__weak', claim='无关内容', title='无关标题'),
                 dict(good_doc, id='a__strong', match_terms=['退订'])]
    ranked = lookup(under_cap, 'a', text=refund_q)
    check('under_cap_pool_is_still_ranked',
          [x['id'] for x in ranked['anchors']], ['a__strong', 'a__weak'])
    check('under_cap_verdict_stays_matched', ranked['verdict'], 'matched')
    check('under_cap_omits_nothing', ranked['omitted'], 0)
    # The dispatcher keys the customer-visible 跳过 line on `reason`, so the
    # distinction between "this area has no anchors" and "it has anchors but none
    # is relevant" is part of the contract, not a diagnostic detail.
    check('reason_area_unanchored', lookup(floored, 'zz')['reason'], 'area-unanchored')
    check('reason_below_floor', none_left['reason'], 'below-floor')
    check('reason_role_filtered',
          lookup(floored, 'a', roles=('conflict-hold',))['reason'], 'role-filtered')
    check('reason_scene_unbound',
          lookup([dict(good_doc, scene_uid='a__q1')], 'a',
                 scene_uid='a__q999')['reason'], 'scene-unbound')
    check('matched_has_no_reason', 'reason' not in lookup(floored, 'a'), True)

    # --- citation cap and overlap narrowing ---
    many = [dict(good_doc, id='m__%d' % i, area='m', scene_uid='m__q1',
                 claim='退订 退款 到账 时限 %d' % i) for i in range(6)]
    check('pool_under_cap_is_matched', lookup(many[:MAX_CITED_PER_RUN], 'm')['verdict'],
          'matched')
    check('pool_under_cap_keeps_everything',
          len(lookup(many[:MAX_CITED_PER_RUN], 'm')['anchors']), MAX_CITED_PER_RUN)
    truncated = lookup(many, 'm')
    check('pool_over_cap_truncates_in_file_order', truncated['verdict'],
          'matched-truncated')
    check('truncation_keeps_the_cap', len(truncated['anchors']), MAX_CITED_PER_RUN)
    check('truncation_counts_omitted', truncated['omitted'], 6 - MAX_CITED_PER_RUN)
    check('truncation_keeps_file_order',
          [a['id'] for a in truncated['anchors']],
          ['m__0', 'm__1', 'm__2'])
    ranked = lookup(many, 'm', text='客户问退款到账时限是多久')
    check('overlap_narrowing_verdict', ranked['verdict'], 'matched-narrowed')
    check('overlap_narrowing_keeps_the_cap', len(ranked['anchors']), MAX_CITED_PER_RUN)
    check('overlap_narrowing_is_deterministic',
          [a['id'] for a in lookup(many, 'm', text='客户问退款到账时限是多久')['anchors']],
          [a['id'] for a in ranked['anchors']])
    check('unlimited_lookup_returns_all', len(lookup(many, 'm', limit=None)['anchors']), 6)
    check('zero_cap_returns_none', lookup(many, 'm', limit=0)['anchors'], [])
    check('overlap_empty_text_scores_zero', _overlap('退订 退款', set()), 0.0)
    check('overlap_empty_claim_scores_zero', _overlap('', _tokens('退款')), 0.0)
    check('overlap_full_match', _overlap('退款', _tokens('退款到账')), 1.0)
    check('overlap_partial_is_fractional',
          0.0 < _overlap('退款到账时限', _tokens('退款')) < 1.0, True)
    check('tokens_cjk_bigrams', '退款' in _tokens('退款到账'), True)
    check('tokens_ascii_words', 'refund' in _tokens('the REFUND page'), True)
    check('tokens_short_ascii_dropped', 'a' in _tokens('a b cd'), False)
    check('tokens_none_is_empty', _tokens(None), set())
    check('single_cjk_char_has_no_bigram', _tokens('退'), set())

    # --- _relevance: customer vocabulary beats document vocabulary ---
    plain = dict(good_doc, id='r__plain', claim='回滚云盘或更换操作系统前应创建快照')
    termed = dict(plain, id='r__termed',
                  match_terms=['初始化', '会不会丢数据', '删不掉'])
    question = '初始化会不会丢数据'
    check('relevance_without_terms_is_weak',
          _relevance(plain, question) < 0.5, True)
    check('relevance_with_terms_is_strong',
          _relevance(termed, question) >= 1.0, True)
    check('relevance_terms_outrank_claim_overlap',
          _relevance(termed, question) > _relevance(plain, question), True)
    check('relevance_one_hit_is_weighted',
          _relevance(termed, '删不掉'), TERM_HIT_WEIGHT)
    check('relevance_two_hits_saturate',
          _relevance(termed, '初始化 删不掉'), 1.0)
    check('relevance_many_hits_stay_saturated',
          _relevance(termed, '初始化 删不掉 会不会丢数据'), 1.0)
    check('relevance_rich_list_is_not_penalised',
          _relevance(dict(termed, match_terms=termed['match_terms'] + ['x' * 3] * 20),
                     '删不掉'), TERM_HIT_WEIGHT)
    check('relevance_empty_text_is_zero', _relevance(termed, ''), 0.0)
    check('relevance_none_text_is_zero', _relevance(termed, None), 0.0)
    check('relevance_no_match_is_claim_overlap_only',
          _relevance(termed, '无关的问题'), 0.0)
    check('relevance_term_match_is_case_insensitive',
          _relevance(dict(plain, match_terms=['FSTAB']), 'my fstab entry') > 0.0, True)
    check('relevance_ignores_blank_terms',
          _relevance(dict(plain, match_terms=['', '  ', '删不掉']), '删不掉'),
          TERM_HIT_WEIGHT)
    check('relevance_title_overlap_counts',
          _relevance(dict(plain, claim='无关', title='退款去向查询'), '退款去向') > 0.0, True)
    check('relevance_lookup_prefers_termed_anchor',
          lookup([plain, termed], 'a', text=question, limit=1)['anchors'][0]['id'],
          'r__termed')
    # Equal relevance: the area's own anchor outranks a shared one.
    tied_own = dict(good_doc, id='t__own', area='t', scene_uid='t__q1',
                    claim='快照 计费', match_terms=['快照'])
    tied_shared = dict(good_doc, id='_shared__tied', area=SHARED_AREA,
                       scene_uid=SHARED_SCENE, claim='快照 计费',
                       match_terms=['快照'], cross_area=['t'])
    check('relevance_tie_prefers_own_over_shared',
          [x['id'] for x in lookup([tied_shared, tied_own], 't', text='快照',
                                   limit=2)['anchors']],
          ['t__own', '_shared__tied'])
    check('reject_match_terms_not_list',
          any('match_terms must be a list' in e for e in _validate_document(
              {'schema': SCHEMA, 'site': 'cn', 'products': products,
               'anchors': [dict(good_doc, match_terms='退款')]})[1]), True)
    check('reject_match_terms_blank_entry',
          any('non-empty strings' in e for e in _validate_document(
              {'schema': SCHEMA, 'site': 'cn', 'products': products,
               'anchors': [dict(good_doc, match_terms=['退款', '  '])]})[1]), True)
    check('accept_match_terms_empty_list', _validate_document(
        {'schema': SCHEMA, 'site': 'cn', 'products': products,
         'anchors': [dict(good_doc, match_terms=[])]})[1], [])

    # --- effective_role: one shared anchor, a different role per citing area ---
    overridden = dict(good_doc, id='_shared__ov', area=SHARED_AREA,
                      scene_uid=SHARED_SCENE, cross_area=['a', 'snap'],
                      role_overrides={'snap': 'verify-only'})
    check('effective_role_default_without_area', effective_role(overridden), 'doc-answers')
    check('effective_role_default_for_undeclared_area',
          effective_role(overridden, 'a'), 'doc-answers')
    check('effective_role_override_applies',
          effective_role(overridden, 'snap'), 'verify-only')
    check('effective_role_unknown_area_falls_back',
          effective_role(overridden, 'nope'), 'doc-answers')
    check('effective_role_no_overrides_field', effective_role(good_doc, 'a'), 'doc-answers')
    check('effective_role_non_dict_anchor', effective_role('x', 'a'), '')
    check('effective_role_bad_overrides_type',
          effective_role(dict(overridden, role_overrides=['verify-only']), 'snap'),
          'doc-answers')
    # The override must change what the customer is promised.
    ov_verified = {'verdict': 'hash-match'}
    as_own = render_citation(overridden, verification=ov_verified, area='a')
    as_snap = render_citation(overridden, verification=ov_verified, area='snap')
    check('override_renders_doc_answers_for_own_area', as_own['verdict'], 'cited-verified')
    check('override_renders_verify_only_for_overridden_area',
          as_snap['verdict'], 'verified-only')
    check('override_adds_no_new_claim_to_customer',
          len(as_snap['customer_lines']), 1)
    check('override_still_cites_the_url',
          any('help.aliyun.com' in line for line in as_snap['customer_lines']), True)
    check('render_without_area_uses_base_role',
          render_citation(overridden, verification=ov_verified)['verdict'], 'cited-verified')
    check('render_reports_the_effective_role', as_snap['role'], 'verify-only')
    # conflict-hold via override also skips the body read.
    ov_conflict = dict(good_doc, id='_shared__ovc', area=SHARED_AREA,
                       scene_uid=SHARED_SCENE, cross_area=['a', 'snap'],
                       role_overrides={'snap': 'conflict-hold'},
                       customer_wording='W',
                       conflict_with=[{'url': 'https://help.aliyun.com/zh/ecs/y.md',
                                       'says': 'S'}])
    check('override_to_conflict_hold_skips_body',
          verify(ov_conflict, area='snap')['verdict'], 'not-required')
    check('override_to_conflict_hold_not_applied_to_other_area',
          verify(ov_conflict, area='a', fetched={'verdict': 'fetched',
                                                 'sha256': 'a' * 12, 'bytes': 1})['verdict'],
          'hash-match')
    check('reject_role_overrides_not_dict',
          any('must be an object' in e for e in _validate_document(
              {'schema': SCHEMA, 'site': 'cn', 'products': products,
               'anchors': [dict(overridden, role_overrides=['x'])]})[1]), True)
    check('reject_role_overrides_illegal_role',
          any('not in' in e for e in _validate_document(
              {'schema': SCHEMA, 'site': 'cn', 'products': products,
               'anchors': [dict(overridden, role_overrides={'snap': 'invented'})]})[1]), True)
    check('reject_role_overrides_area_outside_cross_area',
          any('may not cite this anchor' in e for e in _validate_document(
              {'schema': SCHEMA, 'site': 'cn', 'products': products,
               'anchors': [dict(overridden, role_overrides={'zz': 'verify-only'})]})[1]), True)
    check('reject_own_anchor_override_for_other_area',
          any('may not cite this anchor' in e for e in _validate_document(
              {'schema': SCHEMA, 'site': 'cn', 'products': products,
               'anchors': [dict(good_doc, role_overrides={'b': 'verify-only'})]})[1]), True)
    check('accept_own_anchor_override_for_own_area', _validate_document(
        {'schema': SCHEMA, 'site': 'cn', 'products': products,
         'anchors': [dict(good_doc, role_overrides={'a': 'verify-only'})]})[1], [])

    # --- shared cross-area anchors ---
    shared = dict(good_doc, id='_shared__snap', area=SHARED_AREA,
                  scene_uid=SHARED_SCENE, claim='快照按地域单独结算',
                  cross_area=['a', 'b'], demand_tickets=4403)
    other_shared = dict(shared, id='_shared__other', cross_area=['b'])
    mixed = {'schema': SCHEMA, 'site': 'cn', 'products': products,
             'anchors': [good_doc, shared, other_shared]}
    check('shared_anchor_is_valid', _validate_document(mixed)[1], [])
    merged_pool = lookup(mixed['anchors'], 'a')
    check('lookup_merges_own_then_shared',
          [x['id'] for x in merged_pool['anchors']], ['a__one', '_shared__snap'])
    check('lookup_excludes_shared_not_naming_the_area',
          [x['id'] for x in lookup(mixed['anchors'], 'b', limit=None)['anchors']],
          ['_shared__snap', '_shared__other'])
    check('lookup_area_with_only_shared_anchors',
          lookup([shared], 'a')['verdict'], 'matched')
    check('lookup_unknown_area_with_shared_present',
          lookup(mixed['anchors'], 'zz')['verdict'], 'no-anchor')
    check('shared_survives_scene_narrowing',
          [x['id'] for x in lookup(mixed['anchors'], 'a', scene_uid='a__q1',
                                   limit=None)['anchors']],
          ['a__one', '_shared__snap'])
    # An unbound scene gets no area anchor of its own -- but it still gets the
    # shared warnings, which are not scene-specific.
    unbound_scene = lookup(mixed['anchors'], 'a', scene_uid='a__q999', limit=None)
    check('unbound_scene_still_gets_shared_anchors',
          [x['id'] for x in unbound_scene['anchors']], ['_shared__snap'])
    check('unbound_scene_with_shared_is_matched', unbound_scene['verdict'], 'matched')
    # Own anchors must win the cap: a generic warning may not crowd out the
    # area's own adjudicated answer.
    shared_c = dict(shared, id='_shared__snapc', cross_area=['c'])
    crowded = [dict(good_doc, id='c__%d' % i, area='c', scene_uid='c__q%d' % i)
               for i in range(MAX_CITED_PER_RUN)] + [shared_c]
    kept = lookup(crowded, 'c', limit=MAX_CITED_PER_RUN)
    check('cap_prefers_own_over_shared',
          [x['id'] for x in kept['anchors']], ['c__0', 'c__1', 'c__2'])
    check('cap_reports_shared_as_omitted', kept['omitted'], 1)
    ranked_shared = lookup(crowded, 'c', text='快照 地域 结算 费用', limit=2)
    check('overlap_ranking_can_promote_a_shared_anchor',
          ranked_shared['anchors'][0]['id'], '_shared__snapc')
    check('overlap_ranking_verdict', ranked_shared['verdict'], 'matched-narrowed')

    def reject_shared(mutate, expect):
        broken = dict(shared)
        mutate(broken)
        errs = _validate_document({'schema': SCHEMA, 'site': 'cn', 'products': products,
                                   'anchors': [broken]})[1]
        check('reject_shared_' + expect, any(expect in e for e in errs), True)

    reject_shared(lambda a: a.update(cross_area=[]), 'non-empty cross_area')
    reject_shared(lambda a: a.pop('cross_area'), 'non-empty cross_area')
    reject_shared(lambda a: a.update(cross_area='a'), 'non-empty cross_area')
    reject_shared(lambda a: a.update(cross_area=['a', SHARED_AREA]), 'real area')
    reject_shared(lambda a: a.update(cross_area=['']), 'real area')
    reject_shared(lambda a: a.update(scene_uid='c__q1'), 'shared anchors use scene_uid')
    reject_shared(lambda a: a.update(id='shared__snap'), 'shared anchor ids start with')
    check('reject_shared_demand_not_int',
          any('demand_tickets' in e for e in _validate_document(
              {'schema': SCHEMA, 'site': 'cn', 'products': products,
               'anchors': [dict(shared, demand_tickets='4403')]})[1]), True)
    check('reject_shared_demand_negative',
          any('demand_tickets' in e for e in _validate_document(
              {'schema': SCHEMA, 'site': 'cn', 'products': products,
               'anchors': [dict(shared, demand_tickets=-1)]})[1]), True)
    check('reject_shared_demand_bool',
          any('demand_tickets' in e for e in _validate_document(
              {'schema': SCHEMA, 'site': 'cn', 'products': products,
               'anchors': [dict(shared, demand_tickets=True)]})[1]), True)
    check('accept_shared_demand_zero', _validate_document(
        {'schema': SCHEMA, 'site': 'cn', 'products': products,
         'anchors': [dict(shared, demand_tickets=0)]})[1], [])

    # --- boundary: one anchor per area, cap exactly at the limit ---
    cap_doc = {'schema': SCHEMA, 'site': 'cn', 'products': products,
               'anchors': [dict(good_doc, id='cap__%d' % i, area='cap',
                                scene_uid='cap__q%d' % i)
                           for i in range(MAX_ANCHORS_PER_AREA)]}
    check('area_at_cap_is_accepted', _validate_document(cap_doc)[1], [])
    over_doc = {'schema': SCHEMA, 'site': 'cn', 'products': products,
                'anchors': [dict(good_doc, id='cap__%d' % i, area='cap',
                                 scene_uid='cap__q%d' % i)
                            for i in range(MAX_ANCHORS_PER_AREA + 1)]}
    check('area_over_cap_is_rejected',
          any('exceeds' in e for e in _validate_document(over_doc)[1]), True)
    check('rejected_document_returns_no_anchors', _validate_document(over_doc)[0], [])

    # --- boundary: soft-404 judges ---
    check('soft404_by_exact_size', _is_soft_404(b'x' * SOFT_404_BYTES), True)
    check('soft404_by_marker', _is_soft_404(b'---\nnotfound: "true"\n---\nhi'), True)
    check('soft404_marker_is_case_insensitive',
          _is_soft_404(b'{"statusCode": "404"}'), True)
    check('soft404_one_byte_off_size_is_not_404',
          _is_soft_404(b'x' * (SOFT_404_BYTES - 1)), False)
    check('soft404_marker_beyond_scan_window_is_ignored',
          _is_soft_404(b'z' * SOFT_404_SCAN_BYTES + b'notfound: "true"'), False)
    check('soft404_empty_body', _is_soft_404(b''), False)
    check('real_doc_body_is_not_404', _is_soft_404('# 退订规则\n\n正文'.encode('utf-8')), False)

    # --- boundary: cache path determinism and host parsing ---
    p1 = _cache_paths('https://help.aliyun.com/zh/ecs/x.md')
    p2 = _cache_paths('https://help.aliyun.com/zh/ecs/x.md')
    check('cache_paths_are_deterministic', p1, p2)
    check('cache_paths_differ_per_url',
          _cache_paths('https://help.aliyun.com/zh/ecs/y.md') != p1, True)
    check('cache_body_suffix', p1[0].endswith('.md'), True)
    check('cache_meta_suffix', p1[1].endswith('.json'), True)
    check('host_of_https', _host_of('https://help.aliyun.com/zh/ecs/x.md'), 'help.aliyun.com')
    check('host_of_subdomain',
          _host_of('https://billing-cost.console.aliyun.com/refund/'),
          'billing-cost.console.aliyun.com')
    check('host_of_garbage', _host_of('not a url'), '')
    check('host_of_none', _host_of(None), '')

    # --- illegal input: each rejection reason fires on its own ---
    def reject(mutate, expect_substring):
        broken = dict(good_doc)
        mutate(broken)
        errs = _validate_document({'schema': SCHEMA, 'site': 'cn',
                                   'products': products, 'anchors': [broken]})[1]
        check('reject_' + expect_substring,
              any(expect_substring in e for e in errs), True)
        return errs

    reject(lambda a: a.update(role='invented'), 'not in')
    reject(lambda a: a.update(kind='webpage'), 'not in')
    reject(lambda a: a.update(product='oss'), 'not registered')
    reject(lambda a: a.update(url='https://www.alibabacloud.com/help/en/ecs/x.md'),
           'China site only')
    reject(lambda a: a.update(url='https://help.aliyun.com/zh/ecs/x'), '.md source form')
    reject(lambda a: a.pop('body_sha256'), 'requires body_sha256')
    reject(lambda a: a.update(body_sha256='ZZZZZZZZZZZZ'), 'lowercase hex')
    reject(lambda a: a.update(body_sha256='a' * 11), 'lowercase hex')
    reject(lambda a: a.update(checked_on='05/11/2026'), 'not YYYY-MM-DD')
    reject(lambda a: a.update(also_covered_by='https://x'), 'must be a list')
    reject(lambda a: a.update(invented_field=1), 'unknown field')

    # --- correction witness: the shape check that keeps the build-time checker
    # from passing vacuously. A witness asserting nothing is worse than no
    # witness at all, because it reports the correction as enforced while it
    # holds no string to enforce; and a witness pointing outside references/
    # fails closed as "missing file" instead of naming the file never edited.
    def witness_errs(value):
        return _validate_document({'schema': SCHEMA, 'site': 'cn', 'products': products,
                                   'anchors': [dict(good_doc, correction_applied=value)]})[1]

    check('accept_witness_must_contain_only',
          witness_errs({'file': 'references/x.md', 'must_contain': ['official wording']}), [])
    check('accept_witness_must_not_contain_only',
          witness_errs({'file': 'references/x.md', 'must_not_contain': ['old wording']}), [])
    check('accept_witness_both_arms',
          witness_errs({'file': 'references/a/b.md', 'must_not_contain': ['old'],
                        'must_contain': ['new']}), [])
    # Provenance labels live in the per-area RULE_TOPICS constants, so a witness
    # pointing at scripts/ is the normal shape for a label correction. Measured:
    # 6 of the 7 shipped witnesses target references/, 1 targets _constants.py.
    check('accept_witness_targeting_area_constants',
          witness_errs({'file': 'scripts/areas/a/_constants.py',
                        'must_contain': ['official-doc']}), [])
    check('reject_witness_not_an_object',
          any('correction_applied must be an object' in e for e in
              witness_errs(['references/x.md'])), True)
    check('reject_witness_unknown_key',
          any('correction_applied unknown key' in e for e in
              witness_errs({'file': 'references/x.md', 'must_contain': ['n'],
                            'cited_in': ['nope']})), True)
    check('reject_witness_missing_file',
          any('correction_applied.file must be a non-empty' in e for e in
              witness_errs({'must_contain': ['n']})), True)
    check('reject_witness_blank_file',
          any('correction_applied.file must be a non-empty' in e for e in
              witness_errs({'file': '   ', 'must_contain': ['n']})), True)
    check('reject_witness_absolute_path',
          any('must be a relative path under' in e for e in
              witness_errs({'file': '/tmp/references/x.md', 'must_contain': ['n']})), True)
    check('reject_witness_parent_traversal',
          any('must be a relative path under' in e for e in
              witness_errs({'file': 'references/../SKILL.md', 'must_contain': ['n']})), True)
    check('reject_witness_traversal_from_scripts',
          any('must be a relative path under' in e for e in
              witness_errs({'file': 'scripts/../../.sts_cache.json', 'must_contain': ['n']})),
          True)
    check('reject_witness_outside_package_dirs',
          any('must be a relative path under' in e for e in
              witness_errs({'file': 'evals/scenarios/x.jsonc', 'must_contain': ['n']})), True)
    check('reject_witness_bare_filename',
          any('must be a relative path under' in e for e in
              witness_errs({'file': 'SKILL.md', 'must_contain': ['n']})), True)
    check('reject_witness_empty_string_arm',
          any('must be a list of non-empty' in e for e in
              witness_errs({'file': 'references/x.md', 'must_contain': ['n', '']})), True)
    check('reject_witness_non_list_arm',
          any('must be a list of non-empty' in e for e in
              witness_errs({'file': 'references/x.md', 'must_not_contain': 'old'})), True)
    check('reject_witness_asserting_nothing',
          any('asserts nothing' in e for e in
              witness_errs({'file': 'references/x.md', 'must_contain': [],
                            'must_not_contain': []})), True)
    reject(lambda a: a.pop('claim'), 'missing required')
    conflict_broken = dict(good_conflict, conflict_with=[])
    check('reject_empty_conflict_with',
          any('conflict-hold' in e for e in _validate_document(
              {'schema': SCHEMA, 'site': 'cn', 'products': products,
               'anchors': [conflict_broken]})[1]), True)
    conflict_entry_broken = dict(good_conflict, conflict_with=[{'url': 'https://x'}])
    check('reject_conflict_entry_without_says',
          any('says' in e for e in _validate_document(
              {'schema': SCHEMA, 'site': 'cn', 'products': products,
               'anchors': [conflict_entry_broken]})[1]), True)
    console_no_verified = dict(good_console)
    console_no_verified.pop('verified_by')
    check('reject_console_without_verified_by',
          any('verified_by' in e for e in _validate_document(
              {'schema': SCHEMA, 'site': 'cn', 'products': products,
               'anchors': [console_no_verified]})[1]), True)
    console_with_hash = dict(good_console, body_sha256='b' * 12)
    check('reject_console_with_hash',
          any('must not carry body_sha256' in e for e in _validate_document(
              {'schema': SCHEMA, 'site': 'cn', 'products': products,
               'anchors': [console_with_hash]})[1]), True)
    dup = {'schema': SCHEMA, 'site': 'cn', 'products': products,
           'anchors': [good_doc, dict(good_doc)]}
    check('reject_duplicate_id',
          any('duplicate id' in e for e in _validate_document(dup)[1]), True)
    check('reject_wrong_schema',
          any('schema' in e for e in _validate_document(
              {'schema': 'v1', 'site': 'cn', 'products': products,
               'anchors': [good_doc]})[1]), True)
    check('reject_wrong_site',
          any("!= 'cn'" in e for e in _validate_document(
              {'schema': SCHEMA, 'site': 'intl', 'products': products,
               'anchors': [good_doc]})[1]), True)
    check('reject_empty_anchors', _validate_document(
        {'schema': SCHEMA, 'site': 'cn', 'products': products, 'anchors': []})[0], [])
    check('reject_non_dict_top', _validate_document(['x'])[0], [])
    check('reject_non_list_anchors',
          any('non-empty list' in e for e in _validate_document(
              {'schema': SCHEMA, 'site': 'cn', 'products': products,
               'anchors': {}})[1]), True)
    check('reject_missing_products',
          any('products' in e for e in _validate_document(
              {'schema': SCHEMA, 'site': 'cn', 'anchors': [good_doc]})[1]), True)
    check('reject_non_dict_anchor',
          any('not an object' in e for e in _validate_document(
              {'schema': SCHEMA, 'site': 'cn', 'products': products,
               'anchors': ['x']})[1]), True)

    # --- load_anchors on illegal/absent files: never raises ---
    check('load_missing_file', load_anchors('/nonexistent/doc-anchors.json')['verdict'],
          'anchors-missing')
    check('load_missing_file_has_no_anchors',
          load_anchors('/nonexistent/doc-anchors.json')['anchors'], [])
    check('load_directory_is_unreadable',
          load_anchors(os.path.dirname(PACKAGE_ROOT))['verdict'] in
          ('anchors-unreadable', 'anchors-missing'), True)

    # --- body() on non-fetchable input: no network is attempted ---
    check('body_console_entry_skips_network',
          body('https://billing-cost.console.aliyun.com/refund/',
               kind='console-entry')['verdict'], 'skipped-console-entry')
    check('body_wrong_host_is_malformed',
          body('https://www.alibabacloud.com/help/zh/ecs/x.md')['verdict'], 'malformed-url')
    check('body_missing_md_suffix_is_malformed',
          body('https://help.aliyun.com/zh/ecs/x')['verdict'], 'malformed-url')
    check('body_empty_url_is_malformed', body('')['verdict'], 'malformed-url')
    check('body_malformed_has_no_text', body('')['text'], '')

    # --- verify() ---
    check('verify_console_entry_not_checkable',
          verify(good_console)['verdict'], 'not-checkable')
    check('verify_without_hash',
          verify({k: v for k, v in good_doc.items() if k != 'body_sha256'})['verdict'],
          'no-hash')
    check('verify_non_dict', verify('x')['verdict'], 'no-hash')
    matched = verify(good_doc, fetched={'verdict': 'fetched', 'sha256': 'a' * 12,
                                        'bytes': 10, 'source': 'network'})
    check('verify_hash_match', matched['verdict'], 'hash-match')
    drifted = verify(good_doc, fetched={'verdict': 'fetched', 'sha256': 'b' * 12,
                                        'bytes': 10, 'source': 'network'})
    check('verify_hash_drift', drifted['verdict'], 'hash-drift')
    check('verify_drift_names_both_hashes',
          ('a' * 12 in drifted['detail'] and 'b' * 12 in drifted['detail']), True)
    passed_through = verify(good_doc, fetched={'verdict': 'soft-404', 'sha256': '',
                                               'bytes': 0, 'detail': 'shell'})
    check('verify_passes_through_body_verdict', passed_through['verdict'], 'soft-404')
    check('verify_blocked_passes_through',
          verify(good_doc, fetched={'verdict': 'blocked', 'sha256': '', 'bytes': 0})['verdict'],
          'blocked')
    check('verify_carries_fetch_verdict', matched['fetch_verdict'], 'fetched')

    # --- render_citation() per role, and per verification state ---
    blocked_state = {'verdict': 'blocked'}
    not_required = {'verdict': 'not-required'}
    doc_cite = render_citation(good_doc, verification=matched)
    check('render_doc_answers_cited_verified', doc_cite['verdict'], 'cited-verified')
    check('render_doc_answers_has_customer_lines', len(doc_cite['customer_lines']) >= 2, True)
    check('render_customer_url_strips_md',
          any('https://help.aliyun.com/zh/ecs/x' in line and '.md' not in line
              for line in doc_cite['customer_lines']), True)
    check('render_machine_line_prefix',
          all(line.startswith('DOC-REF') for line in doc_cite['lines']), True)
    check('render_verified_carries_live_excerpt',
          any(line.startswith('DOC-REF-EXCERPT:') for line in doc_cite['lines']), True)
    check('render_state_in_header',
          any('state=hash-match' in line for line in doc_cite['lines']), True)
    check('render_verified_basis_omits_the_snapshot_caveat',
          any('could not be re-read online' in line for line in doc_cite['customer_lines']), False)

    # Unreadable body: the dated excerpt snapshot is the best available evidence,
    # so the answer survives -- but it must say it was not re-checked.
    snap = render_citation(good_doc, verification=blocked_state)
    check('render_on_blocked_falls_back_to_snapshot', snap['verdict'], 'cited-snapshot')
    check('render_snapshot_still_answers_the_customer',
          len(snap['customer_lines']) >= 2, True)
    check('render_snapshot_carries_the_excerpt',
          any(line.startswith('DOC-REF-SNAPSHOT:') for line in snap['lines']), True)
    check('render_snapshot_does_not_claim_a_live_excerpt',
          any(line.startswith('DOC-REF-EXCERPT:') for line in snap['lines']), False)
    check('render_snapshot_states_the_check_date',
          any('checked on 2026-11-05' in line for line in snap['customer_lines']), True)
    check('render_snapshot_admits_no_recheck',
          any('could not be re-read online this run' in line for line in snap['customer_lines']), True)
    check('render_without_verification_is_a_snapshot',
          render_citation(good_doc, verification=None)['verdict'], 'cited-snapshot')
    no_excerpt_snap = render_citation(dict(good_doc, excerpt=''),
                                      verification=blocked_state)
    check('render_snapshot_without_excerpt_records_the_gap',
          any(line.startswith('DOC-REF-SNAPSHOT-MISSING:')
              for line in no_excerpt_snap['lines']), True)

    # Drifted body: the opposite case. The document moved, so the snapshot is a
    # quote from something that no longer says this. Withhold, do not fall back.
    drifted_cite = render_citation(good_doc, verification=drifted)
    check('render_on_drift_withholds', drifted_cite['verdict'], 'withheld-drift')
    check('render_on_drift_withholds_excerpt',
          any('DOC-REF-EXCERPT' in line for line in drifted_cite['lines']), False)
    check('render_on_drift_withholds_snapshot',
          any('DOC-REF-SNAPSHOT:' in line for line in drifted_cite['lines']), False)
    check('render_on_drift_promises_nothing', drifted_cite['customer_lines'], [])
    check('render_on_drift_leaves_a_trace',
          any(line.startswith('DOC-REF-WITHHELD:') for line in drifted_cite['lines']), True)

    promote = render_citation(dict(good_doc, id='a__p', role='promote',
                                   area_correction='references/x.md:25'),
                              verification=matched)
    check('render_promote_cited_verified', promote['verdict'], 'cited-verified')
    check('render_promote_records_correction',
          any(line.startswith('DOC-REF-PROMOTED-FROM:') for line in promote['lines']), True)

    # verify-only adds no new claim, but it does hand over the citation that
    # backs the area's own statement -- that is what a support engineer does.
    only = render_citation(dict(good_doc, id='a__v', role='verify-only',
                                excerpt=''), verification=matched)
    check('render_verify_only_verdict', only['verdict'], 'verified-only')
    check('render_verify_only_cites_the_backing_document',
          len(only['customer_lines']), 1)
    check('render_verify_only_names_the_url',
          any('https://help.aliyun.com/zh/ecs/x' in line
              for line in only['customer_lines']), True)
    check('render_verify_only_adds_no_new_claim',
          any('c' == line for line in only['customer_lines']), False)
    check('render_verify_only_has_freshness_line',
          any(line.startswith('DOC-REF-FRESHNESS:') for line in only['lines']), True)
    check('render_verify_only_snapshot_verdict',
          render_citation(dict(good_doc, id='a__v2', role='verify-only'),
                          verification=blocked_state)['verdict'],
          'verified-only-snapshot')

    # conflict-hold never quotes a body, so it is immune to both unreadable and
    # not-required states -- the adjudicated wording is the answer.
    held = render_citation(good_conflict, verification=matched)
    check('render_conflict_hold_verdict', held['verdict'], 'conflict-held')
    check('render_conflict_uses_adjudicated_wording', held['customer_lines'][0], 'W')
    check('render_conflict_customer_block_names_the_disagreement',
          any('not a single commitment' in line for line in held['customer_lines']), True)
    check('render_conflict_customer_block_cites_each_source',
          [line for line in held['customer_lines'] if line.startswith('- ')],
          ['- S (https://help.aliyun.com/zh/ecs/y)'])
    check('render_conflict_customer_source_strips_md',
          not any(line.endswith('.md)') for line in held['customer_lines']), True)
    check('render_conflict_without_sources_has_no_source_block',
          render_citation(dict(good_conflict, conflict_with=[]),
                          verification=matched)['customer_lines'], ['W'])
    check('render_conflict_names_every_source',
          sum(1 for line in held['lines']
              if line.startswith('DOC-REF-CONFLICT-SOURCE:')), 1)
    check('render_conflict_immune_to_blocked',
          render_citation(good_conflict, verification=blocked_state)['verdict'],
          'conflict-held')
    check('render_conflict_immune_to_drift',
          render_citation(good_conflict, verification=drifted)['verdict'],
          'conflict-held')
    check('render_conflict_with_not_required_state',
          render_citation(good_conflict, verification=not_required)['verdict'],
          'conflict-held')
    no_wording = render_citation(dict(good_conflict, customer_wording=''),
                                 verification=matched)
    check('render_conflict_without_wording_degrades', no_wording['verdict'], 'degraded')
    check('render_conflict_without_wording_promises_nothing',
          no_wording['customer_lines'], [])
    check('verify_conflict_hold_needs_no_body',
          verify(good_conflict)['verdict'], 'not-required')

    console_cite = render_citation(good_console, verification=verify(good_console))
    check('render_console_entry_cited_verified', console_cite['verdict'], 'cited-verified')
    check('render_console_entry_is_not_a_snapshot',
          any('could not be re-read online this run' in line
              for line in console_cite['customer_lines']), False)
    check('render_console_entry_gives_entry_line',
          any(line.startswith('Console entry:')
              for line in console_cite['customer_lines']), True)
    check('render_console_entry_lists_alias',
          any(line.startswith('DOC-REF-ALIAS:') for line in console_cite['lines']), True)
    check('render_non_dict', render_citation('x')['verdict'], 'not-an-anchor')
    check('render_unknown_role', render_citation(dict(good_doc, role='x'))['verdict'],
          'unknown-role')
    check('render_scope_limit_is_surfaced',
          any(line.startswith('DOC-REF-SCOPE-LIMIT:') for line in
              render_citation(dict(good_doc, scope_limit='仅限包年包月'),
                              verification=matched)['lines']), True)
    scoped = dict(good_doc, scope_limit='仅限包年包月')
    # A scope_limit is an instruction to the agent, and the shipped ones carry
    # internal vocabulary (match_term, support-position, handoff-boundaries.md), so
    # it must stay out of the customer block. SKILL.md law-4b binds the agent to the
    # machine line instead; this pins the split so it is not "fixed" by leaking.
    check('render_scope_limit_never_leaks_to_the_customer',
          any('仅限包年包月' in line for line in
              render_citation(scoped, verification=matched)['customer_lines']), False)
    # The emit sits before every role and state branch, so it must survive all the
    # roles that produce a customer block. Pinning that stops a later refactor from
    # moving the emit inside one branch and silently dropping it for the others --
    # which is how a constraint becomes decorative without any test failing.
    check('render_scope_limit_survives_every_customer_facing_role',
          all(any(line.startswith('DOC-REF-SCOPE-LIMIT:') for line in
                  render_citation(dict(scoped, role=role),
                                  verification=matched)['lines'])
              for role in ('doc-answers', 'promote', 'verify-only', 'conflict-hold')),
          True)
    check('render_scope_limit_survives_a_drifted_body',
          any(line.startswith('DOC-REF-SCOPE-LIMIT:') for line in
              render_citation(scoped, verification={'verdict': 'hash-drift'})['lines']),
          True)

    # --- environment switches ---
    saved = {name: os.environ.get(name) for name in
             (ENABLE_ENV, CACHE_DIR_ENV, CACHE_TTL_ENV)}
    try:
        os.environ[ENABLE_ENV] = 'off'
        check('disabled_switch_blocks_load', load_anchors()['verdict'], 'disabled')
        check('disabled_switch_blocks_body', body('https://help.aliyun.com/zh/ecs/x.md')['verdict'],
              'disabled')
        del os.environ[ENABLE_ENV]
        os.environ[CACHE_TTL_ENV] = 'not-a-number'
        check('bad_ttl_falls_back', _cache_ttl_days(), CACHE_TTL_DAYS_DEFAULT)
        os.environ[CACHE_TTL_ENV] = '-1'
        check('negative_ttl_falls_back', _cache_ttl_days(), CACHE_TTL_DAYS_DEFAULT)
        os.environ[CACHE_TTL_ENV] = '0'
        check('zero_ttl_is_honoured', _cache_ttl_days(), 0.0)
        del os.environ[CACHE_TTL_ENV]
        check('default_ttl', _cache_ttl_days(), CACHE_TTL_DAYS_DEFAULT)
        os.environ[CACHE_DIR_ENV] = '/tmp/docleg-selftest-cache'
        check('cache_dir_env_is_honoured',
              _cache_paths('https://help.aliyun.com/zh/ecs/x.md')[0].startswith(
                  '/tmp/docleg-selftest-cache'), True)
        del os.environ[CACHE_DIR_ENV]
        check('cache_dir_default_is_absolute', os.path.isabs(_cache_dir()), True)
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    # --- the shipped file, when present, must load clean ---
    shipped = load_anchors()
    check('shipped_anchor_file_loads', shipped['verdict'], 'loaded')
    if shipped['verdict'] == 'loaded':
        for anchor in shipped['anchors']:
            cite = render_citation(anchor, verification={'verdict': 'hash-match'})
            if cite['verdict'] not in ('cited-verified', 'verified-only', 'conflict-held'):
                failures.append('shipped anchor {0} renders {1}'.format(
                    anchor.get('id'), cite['verdict']))
            else:
                passed += 1
            if anchor.get('role') == 'conflict-hold' and not cite['customer_lines']:
                failures.append('shipped conflict-hold {0} has no adjudicated wording'.format(
                    anchor.get('id')))
        per_area: Dict[str, int] = {}
        for anchor in shipped['anchors']:
            per_area[anchor['area']] = per_area.get(anchor['area'], 0) + 1
        check('shipped_areas_within_cap',
              max(per_area.values()) <= MAX_ANCHORS_PER_AREA, True)

        # Every declared citing area must render a legal verdict, and a declared
        # override must actually change the effective role.
        for anchor in shipped['anchors']:
            if anchor.get('area') != SHARED_AREA:
                continue
            overrides = anchor.get('role_overrides') or {}
            for citing in anchor.get('cross_area') or []:
                cite = render_citation(anchor, verification={'verdict': 'hash-match'},
                                       area=citing)
                if cite['verdict'] not in ('cited-verified', 'verified-only',
                                           'conflict-held'):
                    failures.append('shipped shared anchor {0} renders {1} for area {2}'
                                    .format(anchor.get('id'), cite['verdict'], citing))
                else:
                    passed += 1
                want = overrides.get(citing, anchor.get('role'))
                if cite['role'] != want:
                    failures.append('shipped shared anchor {0} role for {1} is {2}, '
                                    'override says {3}'.format(
                                        anchor.get('id'), citing, cite['role'], want))
            for citing, want in overrides.items():
                if citing not in (anchor.get('cross_area') or []):
                    failures.append('shipped anchor {0} overrides role for {1}, which is '
                                    'not in cross_area'.format(anchor.get('id'), citing))
                elif effective_role(anchor, citing) != want:
                    failures.append('shipped anchor {0} effective_role({1}) != {2}'.format(
                        anchor.get('id'), citing, want))

    # ---- _term_hits: the count lookup() now requires to be >= 1 -------------
    # Normal, boundary and illegal inputs, because this count decides whether a
    # document may be cited at all.
    th = {'id': 'th', 'area': 'a', 'match_terms': ['分区名', 'NVMe', ' fdisk ']}
    check('term_hits_counts_every_verbatim_term', _term_hits(th, '分区名变了'), 1)
    check('term_hits_counts_two', _term_hits(th, '分区名变了，fdisk 看不到'), 2)
    # Latin terms are matched case-insensitively: customers write nvme, the
    # document writes NVMe, and neither spelling is wrong.
    check('term_hits_is_case_insensitive', _term_hits(th, '实例是nvme的'), 1)
    # Whitespace around a term is build-time noise, not a matching requirement.
    check('term_hits_strips_the_term', _term_hits(th, 'run fdisk -lu'), 1)
    check('term_hits_empty_text_is_zero', _term_hits(th, ''), 0)
    check('term_hits_none_text_is_zero', _term_hits(th, None), 0)
    check('term_hits_no_terms_is_zero', _term_hits({'id': 'x'}, '分区名'), 0)
    # A non-string entry must be ignored, not raise: the file is adjudicated by
    # hand and one bad row must not take the whole leg down.
    check('term_hits_ignores_non_string_entries',
          _term_hits({'match_terms': ['分区名', None, 7, '']}, '分区名'), 1)
    check('term_hits_does_not_count_a_partial_term',
          _term_hits(th, '分区变了'), 0)

    # ---- lookup(): overlap alone is not evidence ---------------------------
    # Both anchors share the page title, so both score the same claim/title
    # overlap against a question that mentions 数据盘. Only one has a term that
    # fires. Measured origin: five billing anchors cleared the 0.1 floor at 0.167
    # each on the single word 账单, and three of them were cited as `completed`
    # for a CDT traffic question none of them answers.
    shared_title = 'Linux 数据盘初始化（GPT/MBR 分区）'
    termless = {'id': 'ov__overlap-only', 'area': 'ov', 'scene_uid': 'ov__s',
                'role': 'doc-answers', 'kind': 'doc', 'product': 'ecs',
                'url': 'https://help.aliyun.com/zh/ecs/x.md', 'title': shared_title,
                'claim': 'MBR分区不支持超过2 TiB的数据盘容量', 'checked_on': '2026-11-05',
                'match_terms': ['2tib', 'mbr']}
    termed = dict(termless, id='ov__termed',
                  claim='数据盘挂载后须先初始化才能使用',
                  match_terms=['读不出来'])
    q = '系统换成Linux之后，原来的数据盘读不出来'
    r = lookup([termless], 'ov', question=q, text=q)
    check('overlap_only_is_not_citable', r['verdict'], 'no-anchor')
    check('overlap_only_names_its_reason', r.get('reason'), 'no-term-hit')
    check('overlap_only_explains_the_cause',
          'claim/title overlap' in r.get('detail', ''), True)
    check('overlap_only_is_not_reported_as_below_floor',
          r.get('detail', '').startswith('none of the'), False)
    r = lookup([termed], 'ov', question=q, text=q)
    check('a_term_hit_is_citable', r['verdict'], 'matched')
    check('a_term_hit_selects_the_anchor', [a['id'] for a in r['anchors']],
          ['ov__termed'])
    r = lookup([termless, termed], 'ov', question=q, text=q)
    check('the_overlap_only_sibling_is_dropped_not_just_outranked',
          [a['id'] for a in r['anchors']], ['ov__termed'])
    # Without a question the gate does not apply: there is nothing to hit
    # against, and reachability must stay as it was.
    r = lookup([termless], 'ov')
    check('no_question_means_no_term_gate', r['verdict'], 'matched')
    # The floor still fires first, and says so with its own reason.
    r = lookup([termed], 'ov', question='退订之后钱退到哪里了', text='退订之后钱退到哪里了')
    check('below_floor_still_has_its_own_reason', r.get('reason'), 'below-floor')

    # ---- NOT_ATTEMPTED_STATES: the citation must not blame the network ------
    snap_anchor = {'id': 'na__one', 'area': 'na', 'scene_uid': 'na__s',
                   'role': 'doc-answers', 'kind': 'doc', 'product': 'ecs',
                   'url': 'https://help.aliyun.com/zh/ecs/na.md',
                   'title': 'T', 'claim': 'C', 'excerpt': 'E',
                   'checked_on': '2026-11-05', 'body_sha256': 'abcd1234abcd'}
    for state_name in ('unchecked', 'no-hash'):
        cite = render_citation(snap_anchor, verification={'verdict': state_name})
        joined = ' '.join(cite['customer_lines'])
        check('not_attempted_%s_says_not_re_read' % state_name,
              'was not re-read this run' in joined, True)
        check('not_attempted_%s_does_not_claim_a_failed_read' % state_name,
              'could not be re-read online' in joined, False)
        check('not_attempted_%s_still_falls_back_to_the_snapshot' % state_name,
              any(l.startswith('DOC-REF-SNAPSHOT:') for l in cite['lines']), True)
        check('not_attempted_%s_is_not_withheld' % state_name,
              cite['verdict'], 'cited-snapshot')
    check('not_attempted_states_are_disjoint_from_drifted',
          bool(NOT_ATTEMPTED_STATES & DRIFTED_STATES), False)
    check('not_attempted_states_are_disjoint_from_unreadable',
          bool(NOT_ATTEMPTED_STATES & UNREADABLE_STATES), False)
    # The refused read keeps its own wording, or the split is decorative.
    cite = render_citation(snap_anchor, verification={'verdict': 'blocked'})
    joined = ' '.join(cite['customer_lines'])
    check('refused_read_says_could_not_be_re_read',
          'could not be re-read online this run' in joined, True)
    check('refused_read_is_not_worded_as_not_attempted',
          'was not re-read this run' in joined, False)
    check('refused_read_still_falls_back_to_the_snapshot',
          any(l.startswith('DOC-REF-SNAPSHOT:') for l in cite['lines']), True)
    # A not-attempted anchor with no excerpt must say so rather than imply the
    # claim is sourced.
    cite = render_citation(dict(snap_anchor, excerpt=''),
                           verification={'verdict': 'unchecked'})
    check('not_attempted_without_excerpt_reports_the_gap',
          any(l.startswith('DOC-REF-SNAPSHOT-MISSING:') for l in cite['lines']), True)
    # verify-only keeps its own frame under the same state.
    cite = render_citation(dict(snap_anchor, role='verify-only'),
                           verification={'verdict': 'unchecked'})
    check('verify_only_not_attempted_uses_the_snapshot_verdict',
          cite['verdict'], 'verified-only-snapshot')
    check('verify_only_not_attempted_does_not_blame_the_network',
          'could not be re-read online' in ' '.join(cite['customer_lines']), False)

    if verbose:
        for line in failures:
            sys.stderr.write('SELFTEST-FAIL: {0}\n'.format(line))
    return passed, failures


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'selftest'
    if mode == 'selftest':
        ok, bad = selftest(verbose=True)
        sys.stderr.write('doc-refs selftest: {0} passed, {1} failed\n'.format(ok, len(bad)))
        sys.exit(1 if bad else 0)
    elif mode == 'dump':
        state = load_anchors()
        area = sys.argv[2] if len(sys.argv) > 2 else ''
        scene = sys.argv[3] if len(sys.argv) > 3 else None
        picked = lookup(state['anchors'], area, scene_uid=scene)
        sys.stderr.write('load={0} ({1}); lookup={2} ({3})\n'.format(
            state['verdict'], state['detail'], picked['verdict'], picked['detail']))
        for anchor in picked['anchors']:
            checked = verify(anchor)
            rendered = render_citation(anchor, verification=checked)
            print('\n'.join(rendered['lines']))
            for line in rendered['customer_lines']:
                print('CUSTOMER: {0}'.format(line))
        sys.exit(0)
    else:
        sys.stderr.write('usage: _doc_refs.py [selftest | dump <area> [scene_uid]]\n')
        sys.exit(2)
