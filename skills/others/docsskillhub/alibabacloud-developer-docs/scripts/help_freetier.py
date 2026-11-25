#!/usr/bin/env python3
"""Anonymous public trial cards; account eligibility always requires the user's own login."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin, urlsplit

from help_const import DEFAULT_SITE, SITES, _UsageError
from help_http import fetch_response
from help_scope import _infer_site, _normalize_lang

_CN_ENTRY = "https://free.aliyun.com/"
_INTL_ENTRY = "https://www.alibabacloud.com"
_PLAN_API = "https://page.aliyun.com/delivery/plan/list"
_MAX_BYTES = 12 * 1024 * 1024
_MAX_CONFIGS = 3
_MAX_POSITIONS = 4
_CONDITIONS = {
    "core_item_descr": "Specification",
    "detail_item_info": "Details / overage conditions",
    "freetier_user_rule": "Published user rule (not your eligibility)",
    "freetier_cert_type": "Published certification rule",
    "freetier_duration_limit": "Published duration-limit flag",
}


class _TrialError(Exception):
    pass


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _scope(args) -> tuple[str, str]:
    lang = _normalize_lang(args.lang)
    site = args.site or (_infer_site(lang) if lang else DEFAULT_SITE)
    if site not in SITES:
        raise _UsageError("ERROR: trial site must be cn or intl.")
    lang = lang or SITES[site]["default_lang"]
    supported = ("zh",) if site == "cn" else ("en", "zh")
    if lang not in supported:
        raise _UsageError(f"ERROR: trial pages on {site} support: {', '.join(supported)}; "
                          "no language or cross-site fallback is performed.")
    return site, lang


def _entry_url(site: str, lang: str, keyword: str) -> str:
    if site == "cn":
        return _CN_ENTRY + "?" + urlencode({"searchKey": keyword})
    path = "/zh/free" if lang == "zh" else "/free"
    params = {"_p_lc": "1", "keywords": keyword} if lang == "zh" else {"keywords": keyword}
    return _INTL_ENTRY + path + "?" + urlencode(params)


def _fetch(url: str, label: str, *, data=None, headers=None) -> str:
    text, meta = fetch_response(url, allow_redirects=False, timeout=30,
                                max_bytes=_MAX_BYTES, attempts=1, data=data, headers=headers)
    if meta.get("truncated"):
        raise _TrialError(f"{label} exceeded the response-size limit; discarded")
    if meta.get("error") or meta.get("status") != 200 or not text.strip():
        raise _TrialError(f"{label} could not be retrieved (HTTP {meta.get('status') or 'unknown'})")
    return text


class _PageData(HTMLParser):
    def __init__(self):
        super().__init__()
        self.configs = []
        self.card_groups = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if not value:
                continue
            if tag == "script" and key == "src":
                try:
                    url = urljoin(_CN_ENTRY, value)
                    parts = urlsplit(url)
                except ValueError:
                    continue
                if (parts.scheme == "https" and parts.netloc == "website.alyasset.com"
                        and re.fullmatch(r"/lowcode/entry/prod/[A-Za-z0-9_-]+\.js", parts.path)
                        and not parts.query and not parts.fragment and url not in self.configs):
                    self.configs.append(url)
            if key == "data-data":
                try:
                    blob = json.loads(value)
                except (ValueError, RecursionError):
                    continue
                if isinstance(blob, dict) and isinstance(blob.get("cardArray"), list):
                    self.card_groups.append(blob["cardArray"])


def _delivery_ids(text: str) -> list[str]:
    match = re.search(r"\bschema:\s*", text)
    if not match:
        raise _TrialError("current trial configuration has no JSON schema")
    try:
        schema, _ = json.JSONDecoder().raw_decode(text[match.end():])
    except (ValueError, RecursionError):
        raise _TrialError("current trial configuration has invalid JSON schema") from None
    if not isinstance(schema, dict):
        raise _TrialError("current trial configuration has an unexpected schema")
    ids = []
    pending = [schema]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            if value.get("componentName") == "AceNewhomonFreecenterGoodsCard":
                props = value.get("props")
                rid = props.get("deliveryId") if isinstance(props, dict) else None
                if isinstance(rid, (str, int)) and not isinstance(rid, bool):
                    rid = str(rid)
                    if re.fullmatch(r"[0-9]{1,12}", rid) and rid not in ids:
                        ids.append(rid)
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    return ids


def _attributes(item: dict) -> dict:
    attrs = {}
    values = item.get("actPromotionCommodityAttributeList")
    for value in values if isinstance(values, list) else []:
        if isinstance(value, dict) and isinstance(value.get("attrCode"), str):
            attrs[value["attrCode"]] = value.get("attrValue")
    if isinstance(item.get("attributeMap"), dict):
        attrs.update(item["attributeMap"])
    return attrs


def _conditions(attrs: dict) -> dict:
    return {key: value for key in _CONDITIONS
            if ((isinstance((value := attrs.get(key)), (str, bool, int, float)) and value != "")
                or (isinstance(value, list) and all(isinstance(part, str) for part in value)))}


def _is_trial(item: dict, attrs: dict) -> bool:
    # Audience restrictions alone also occur on paid siblings; never inherit trial identity.
    desc = _text(item.get("description"))
    return bool(_text(attrs.get("freetier_activity_id")) or
                re.search(r"免费试用|\bfree\s+trial\b", desc, re.IGNORECASE))


def _cn_item(item: dict, keyword: str) -> dict | None:
    attrs = _attributes(item)
    children = item.get("children")
    children = children if isinstance(children, list) else []
    offers = []
    names = [_text(item.get("itemName")), _text(item.get("productCode"))]
    for child in children:
        if not isinstance(child, dict):
            continue
        child_attrs = _attributes(child)
        title = _text(child.get("commodityName")) or _text(child.get("itemName"))
        if _is_trial(child, child_attrs) and title:
            offers.append({"title": title, "description": _text(child.get("description")),
                           "conditions": _conditions(child_attrs)})
            names.extend((title, _text(child.get("itemName"))))
    if not any(keyword.casefold() in name.casefold() for name in names):
        return None
    if not offers and not _is_trial(item, attrs):
        return None
    title = _text(item.get("itemName"))
    if not title:
        return None
    return {"title": title, "product_code": _text(item.get("productCode")),
            "description": _text(item.get("description")) if _is_trial(item, attrs) else "",
            "conditions": _conditions(attrs), "offers": offers}


def _plan_items(text: str, rid: str) -> tuple[list, dict]:
    try:
        blob = json.loads(text)
    except (ValueError, RecursionError):
        raise _TrialError("trial delivery returned invalid JSON") from None
    if not isinstance(blob, dict) or str(blob.get("code")) != "200":
        raise _TrialError("trial delivery returned an application error")
    data = blob.get("data")
    positions = data.get("positionPlanMap") if isinstance(data, dict) else None
    plans = positions.get(rid) if isinstance(positions, dict) else None
    if not isinstance(plans, list) or not plans:
        raise _TrialError("trial delivery returned no usable plan list")
    items, totals = [], []
    complete = True
    for plan in plans:
        try:
            content = json.loads(plan.get("displayContent")) if isinstance(plan, dict) else None
        except (TypeError, ValueError, RecursionError):
            raise _TrialError("trial delivery has invalid serialized displayContent") from None
        if not isinstance(content, dict) or not isinstance(content.get("commodityList"), list):
            raise _TrialError("trial delivery has no commodityList")
        batch = content["commodityList"]
        page = content.get("pageInfo")
        total = page.get("total") if isinstance(page, dict) else None
        valid_total = isinstance(total, int) and not isinstance(total, bool) and total >= len(batch)
        complete = complete and valid_total and total == len(batch)
        totals.append(total if valid_total else None)
        items.extend(batch)
    total = sum(totals) if all(value is not None for value in totals) else None
    return items, {"received": len(items), "total": total, "complete": bool(complete)}


def _china(url: str, keyword: str) -> tuple[list, dict, list]:
    page = _PageData()
    page.feed(_fetch(url, "China trial page"))
    if not page.configs or len(page.configs) > _MAX_CONFIGS:
        raise _TrialError("current trial configuration links are missing or exceed the discovery limit")
    ids = []
    for config in page.configs:
        for rid in _delivery_ids(_fetch(config, "current trial configuration")):
            if rid not in ids:
                ids.append(rid)
    if not ids or len(ids) > _MAX_POSITIONS:
        raise _TrialError("current trial-card delivery positions are missing or exceed the discovery limit")
    results, coverage, warnings = [], [], []
    for rid in ids:
        query = {"adZone": {"positionList": [{"positionId": rid, "preview": False,
                  "context": {}, "contentCount": 100, "byGroup": 0}]},
                 "requestId": "q1", "referrer": "", "returnAll": False}
        body = urlencode({"adPlanQueryParam": json.dumps(query, separators=(",", ":"))}).encode()
        try:
            items, scope = _plan_items(_fetch(_PLAN_API + "?" + urlencode({"resourceId": rid}),
                                            "trial delivery", data=body,
                                            headers={"Referer": _CN_ENTRY, "Origin": _CN_ENTRY.rstrip("/"),
                                                     "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}), rid)
        except _TrialError as exc:
            warnings.append(str(exc))
            coverage.append({"received": 0, "total": None, "complete": False})
            continue
        skipped = 0
        for item in items:
            if not isinstance(item, dict) or not _text(item.get("itemName")):
                skipped += 1
                continue
            children = item.get("children", [])
            if not isinstance(children, list) or any(not isinstance(child, dict) for child in children):
                skipped += 1
            result = _cn_item(item, keyword)
            if result and result not in results:
                results.append(result)
        scope["skipped"] = skipped
        scope["complete"] = scope["complete"] and not skipped
        coverage.append(scope)
    totals = [part["total"] for part in coverage]
    return results, {"received": sum(part["received"] for part in coverage),
                     "total": sum(totals) if all(value is not None for value in totals) else None,
                     "skipped": sum(part.get("skipped", 0) for part in coverage),
                     "complete": all(part["complete"] for part in coverage)}, warnings


def _international(text: str, keyword: str) -> tuple[list, dict]:
    page = _PageData()
    page.feed(text)
    if not page.card_groups:
        raise _TrialError("trial page has no usable cardArray; page layout may have changed")
    cards = []
    for group in page.card_groups:
        for card in group:
            if card not in cards:
                cards.append(card)
    results, hidden, skipped = [], 0, 0
    for card in cards:
        if not isinstance(card, dict) or not _text(card.get("title")):
            skipped += 1
            continue
        if card.get("hideCard") == "yes":
            hidden += 1
            continue
        if card.get("hideCard") not in (None, "", "no"):
            skipped += 1
            continue
        title = _text(card.get("title"))
        if keyword.casefold() not in title.casefold():
            continue
        tags = card.get("checkList")
        results.append({"title": title, "specification": _text(card.get("specification")),
                        "description": _text(card.get("desc")),
                        "published_tags": [tag for tag in tags if isinstance(tag, str)]
                        if isinstance(tags, list) else []})
    return results, {"received": len(cards), "total": len(cards), "hidden": hidden,
                     "skipped": skipped, "complete": not skipped}


def trial_search(args) -> int:
    site, lang = _scope(args)
    keyword = (args.keyword or "").strip()
    if len(keyword) > 200 or args.max_results < 0:
        raise _UsageError("ERROR: trial keyword must be at most 200 characters; -n must be non-negative.")
    source = _entry_url(site, lang, keyword)
    warnings = []
    try:
        if site == "cn":
            results, coverage, warnings = _china(source, keyword)
        else:
            results, coverage = _international(_fetch(source, "international trial page"), keyword)
    except _TrialError as exc:
        results = []
        coverage = {"received": 0, "total": None, "complete": False}
        warnings.append(str(exc))
    if not coverage["complete"]:
        warnings.append("Only the successfully retrieved public cards were checked; "
                        "a missing match does not establish absence of a trial."
                        + ("" if results else " Exit 2 here is a coverage gap, not a network failure: "
                           "retry once with the bare product name, then give the public entry link "
                           "and say the offer could not be verified."))
    output = {"site": site, "language": lang, "source": source,
              "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "keyword": keyword, "eligibility": "unknown_login_required",
              "coverage": coverage, "matched": len(results),
              "results": results[:args.max_results] if args.max_results else results,
              "warnings": warnings}
    for warning in warnings:
        print(f"WARN[trial-coverage]: {warning}", file=sys.stderr)
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"Public trial cards: {site} / {lang}\nSource: {source}")
        print(f"Retrieved: {output['retrieved_at']} | received {coverage['received']} / "
              f"{coverage['total'] if coverage['total'] is not None else 'unknown'} | "
              f"matched {len(results)}")
        print("Your trial eligibility is unknown; log in to the official page yourself to check.")
        for result in output["results"]:
            print(f"\n## {result['title']}")
            for field in ("specification", "description"):
                if result.get(field):
                    print(result[field])
            for key, value in result.get("conditions", {}).items():
                print(f"{_CONDITIONS[key]}: {value}")
            if result.get("published_tags"):
                print("Published audience/categories (not your eligibility): " +
                      ", ".join(result["published_tags"]))
            for offer in result.get("offers", []):
                print(f"- {offer['title']}: {offer['description']}")
                for key, value in offer["conditions"].items():
                    print(f"  {_CONDITIONS[key]}: {value}")
        if not results:
            print("No matching public trial card in the retrieved scope; check the source page.")
    return 0 if results else (1 if coverage["complete"] else 2)
