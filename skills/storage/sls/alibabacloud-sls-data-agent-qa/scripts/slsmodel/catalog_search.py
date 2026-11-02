"""Portable lexical retrieval of original model definitions; no reranker service."""

import math
import re
import unicodedata
from collections import Counter

from .catalog_overview import OVERVIEW_SPL
from .element import ELEMENTS, bindings, member_name, members, metadata, object_cell
from .errors import CatalogError
from .query import ReadMode, literal


def tokens(search_text):
    search_text = unicodedata.normalize("NFC", search_text).lower()
    result = []
    def han(char):
        return "\u3400" <= char <= "\u9fff" or "\U00020000" <= char <= "\U0003134f"
    def identifier(char):
        return char == "_" or (char.isalnum() and not han(char))
    index = 0
    while index < len(search_text):
        end = index + 1
        if han(search_text[index]):
            while end < len(search_text) and han(search_text[end]):
                end += 1
            word = search_text[index:end]
            result.extend(word)
            result.extend(word[i:i + 2] for i in range(len(word) - 1))
        elif identifier(search_text[index]):
            while end < len(search_text) and (identifier(search_text[end]) or
                    (search_text[end] == "." and end + 1 < len(search_text) and identifier(search_text[end + 1]))):
                end += 1
            word = search_text[index:end]
            result.append(word)
            result.extend(part for part in re.split(r"[._]", word) if part and part != word)
        index = end
    return result


def strings(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [search_text for item in value for search_text in strings(item)]
    if isinstance(value, dict):
        return [search_text for key, item in sorted(value.items())
                if key not in ("confidence", "model_binding", "model_bindings") for search_text in strings(item)]
    return []


def search(query_model, search_text, source_tags=None, limit=20, *, include_example_queries=True):
    if not isinstance(search_text, str) or not search_text.strip() or not 1 <= limit <= 200:
        raise CatalogError("InvalidParameter", "Search requires a nonempty query and limit between 1 and 200")
    if source_tags is not None and not source_tags:
        raise CatalogError("InvalidParameter", "Search sources must not be empty")
    elements, identities = [], set()
    for row in query_model(OVERVIEW_SPL, ReadMode.COMPLETE):
        if not all(key in row for key in ("kind", "metadata", "spec")):
            raise CatalogError("IncompleteCatalogRead", "Search requires kind, metadata and spec")
        meta = metadata(row["metadata"])
        for typ, (kind, subtype, key) in ELEMENTS.items():
            if row["kind"] != kind or (subtype and meta["runbook_type"] != subtype):
                continue
            identity = (meta["domain"], kind, meta["name"])
            if identity in identities:
                raise CatalogError("element_ambiguous", "Duplicate Element identity: " + meta["name"])
            identities.add(identity)
            items = members(row["spec"], key)
            names = [member_name(item) for item in items if member_name(item).strip()]
            if len(names) != len(set(names)):
                raise CatalogError("member_ambiguous", "Duplicate Member in " + meta["name"])
            elements.append((typ, identity, meta, items, object_cell(row["metadata"], "InvalidCatalogMetadata")))
            break
    schema_source_tags = {identity: meta["source"] for typ, identity, meta, _, _ in elements
                      if typ == "schema" and identity[0] == "sls" and identity[2].strip() and meta["source"]}
    known = set(schema_source_tags.values())
    if source_tags is not None and set(source_tags) - known:
        raise CatalogError("CatalogSourceNotFound", "Unknown source: " + ", ".join(sorted(set(source_tags) - known)))
    candidates, structure_issues = [], False
    for typ, identity, meta, items, raw_meta in elements:
        if typ == "exampleQuery" and not include_example_queries:
            continue
        try:
            literal(identity[2])
            usable = identity[0] == "sls" and bool(identity[2]) and identity[2].strip() == identity[2]
        except CatalogError:
            usable = False
        for member in items:
            name = member_name(member)
            if not usable or not name.strip():
                structure_issues = True
                continue
            if typ in ("schema", "metric", "overview"):
                attributed = [meta["source"]] if meta["source"] in known else None
            else:
                bound = bindings(member, typ)
                attributed = (sorted({schema_source_tags[item] for item in bound})
                              if bound is not None and all(item in schema_source_tags for item in bound) else None)
            if attributed is None:
                structure_issues = True
                continue
            if source_tags and attributed and not set(attributed).intersection(source_tags):
                continue
            confidence = member.get("confidence")
            applied = isinstance(confidence, dict) and confidence.get("status") in ("auto_applied", "manually_applied")
            factual = typ in ("schema", "metric", "term") and not applied
            if factual and typ != "schema":
                continue
            projection = {key: member[key] for key in ("name", "type") if key in member} if factual else member
            parts = strings(projection) + [identity[2], *attributed]
            if not factual:
                parts += strings(raw_meta.get("description")) + strings(raw_meta.get("display_name"))
            keys = [name] + ([] if factual else strings(member.get("aliases")))
            explicit = any(re.search(r"(?<![\w./:@-])" + re.escape(key) + r"(?![\w./:@-])", search_text)
                           if re.search(r"[A-Za-z0-9_]", key) else key in search_text for key in keys if key)
            candidates.append({"elementType": typ, "element": identity[2], "member": member,
                               "source": meta["source"] if typ in ("schema", "metric", "overview") else "",
                               "factual": factual, "explicit": explicit,
                               "frequency": Counter(tokens(" ".join(parts)))})
    frequencies = Counter(token for candidate in candidates for token in candidate["frequency"])
    average = sum(sum(c["frequency"].values()) for c in candidates) / max(1, len(candidates)) or 1
    for candidate in candidates:
        score, freq = 0, candidate.pop("frequency")
        length = sum(freq.values())
        for token in set(tokens(search_text)):
            if freq[token]:
                idf = math.log(1 + (len(candidates) - frequencies[token] + .5) / (frequencies[token] + .5))
                score += idf * freq[token] * 2.2 / (freq[token] + 1.2 * (.25 + .75 * length / average))
        candidate["score"] = score
    ranked = sorted((c for c in candidates if c["score"] > 0 or c["explicit"]),
                    key=lambda c: (-c["explicit"], -c["score"], c["elementType"], c["element"], member_name(c["member"])))
    return {"candidates": ranked[:limit], "structureIssues": structure_issues,
            "retrieval": {"method": "lexical", "matchedMembers": len(ranked),
                          "selectedMembers": min(limit, len(ranked)), "limited": len(ranked) > limit}}
