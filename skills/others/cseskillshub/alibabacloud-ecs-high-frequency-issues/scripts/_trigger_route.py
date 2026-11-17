"""Lexical area suggestion from a Chinese customer question (P3 / Bug 2).

Read-only routing aid: it ranks areas by the evidenced Chinese trigger lexicon in
references/trigger-lexicon.json and never dispatches anything. The scoring mirrors
the build-time gate check_trigger_lexicon.py so the suggestion and the gate agree.
"""
import json
import math
import os
import re

_CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")
_LATIN_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9]{1,7}")


def ngrams(text, lo=2, hi=6):
    out = set()
    for run in _CJK_RUN.findall(text):
        for size in range(lo, hi + 1):
            for start in range(len(run) - size + 1):
                out.add(run[start:start + size])
    for token in _LATIN_TOKEN.findall(text):
        out.add(token.upper())
    return out


def load_lexicon(here):
    path = os.path.join(here, "..", "references", "trigger-lexicon.json")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    areas = data.get("areas", {})
    return areas if isinstance(areas, dict) else {}


def rank_areas(question, lexicon):
    grams = ngrams(question)
    scored = []
    for area, rows in lexicon.items():
        total = 0.0
        matched = []
        matched_len = 0
        for row in rows:
            term = row.get("term", "")
            fires = row.get("fires", 0)
            if term in grams and fires > 0:
                total += row.get("correct_share", 0.0) / (1.0 + math.log10(fires))
                matched.append(term)
                matched_len += len(term)
        if total > 0:
            scored.append((area, total, matched_len, matched))
    scored.sort(key=lambda item: (-item[1], -item[2]))
    return scored
