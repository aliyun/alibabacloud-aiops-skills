#!/usr/bin/env python3
#
# SECURITY:
#   - This module is part of a READ-ONLY media diagnostics toolkit.
#   - It only formats already-collected results for output; it performs
#     no I/O and never modifies any file.
#   - No cloud credentials, API keys or tokens are required or used.
"""
Shared human-friendly reporting module.

Every entry script keeps its machine-readable JSON contract on stdout and,
in addition, attaches three plain-language fields for non-technical users:

  - summary:             one plain-English conclusion (what happened, what
                         it means, what the impact is)
  - recommended_actions: concrete next steps the user can take
  - severity_human:      plain severity label ("minor" / "needs attention" /
                         "prompt attention")

On stderr the scripts additionally print a formatted "Media Diagnosis
Report" block (plain conclusion / what was checked / findings / next
steps). The existing [INFO]/[WARN] stderr lines are kept unchanged.
Human-facing findings and checked items are glossed with a short
plain-language explanation of any technical term they contain, so
non-technical users are never left with bare jargon (see GLOSS/gloss).
"""

REPORT_HEADER = "=== Media Diagnosis Report ==="

# Plain-language explanations for technical terms that may appear in
# human-facing findings or checked items. Keys are matched
# case-insensitively as substrings; the first matching gloss is appended.
GLOSS = [
    ("DTS", "DTS is the timestamp that tells the player when each frame should be displayed"),
    ("continuity counter", "the continuity counter is the sequential number on each stream packet, used to detect lost data"),
    ("TS continuity", "TS continuity checks that no stream packets were lost on the way"),
    ("PAT/PMT", "PAT/PMT are the index tables that tell a player which audio and video streams are inside"),
    ("PAT table", "the PAT table is the index that tells a player which streams are inside"),
    ("PMT table", "the PMT table is the index that tells a player which streams are inside"),
    ("sync byte", "the sync byte is the fixed marker at the start of each stream packet"),
    ("B-frame", "B-frames are extra reference frames that improve compression but add decoding delay"),
    ("B-frames", "B-frames are extra reference frames that improve compression but add decoding delay"),
    ("GOP", "GOP is the keyframe interval: how often the video inserts a complete, independently decodable picture"),
    ("keyframe interval", "the keyframe interval controls how often the video inserts a complete, independently decodable picture"),
    ("moov", "the moov atom is the index box that describes the whole file; players need it before playback can start"),
    ("HEVC", "HEVC (also called H.265) is a newer video codec that many browsers cannot play"),
    ("H.265", "H.265 (also called HEVC) is a newer video codec that many browsers cannot play"),
    ("AAC-LC", "AAC-LC is the most compatible audio format for streaming"),
    ("HE-AAC", "HE-AAC is a compressed audio variant with weaker compatibility on older devices"),
    ("sample rate", "the sample rate is how many audio measurements are taken per second"),
    ("variable frame rate", "variable frame rate means the video changes its picture rate over time"),
    ("VFR", "variable frame rate means the video changes its picture rate over time"),
    ("bitrate", "bitrate is how much data the media uses per second"),
    ("targetDuration", "targetDuration is the maximum segment length declared by the playlist"),
    ("DISCONTINUITY", "DISCONTINUITY tags mark points where the encoding parameters change mid-stream"),
    ("discontinuit", "discontinuities mark points where the encoding parameters change mid-stream"),
    ("TS segment", "a TS segment is one of the small video files an HLS stream is cut into"),
]


def gloss(text):
    """Append a short plain-language explanation if the text contains a
    known technical term. Returns the original text unchanged when no
    term matches."""
    lowered = text.lower()
    for term, explanation in GLOSS:
        if term.lower() in lowered:
            return f"{text} -- {explanation}."
    return text

SEVERITY_HUMAN = {
    "minor": "minor",
    "needs_attention": "needs attention",
    "prompt_attention": "prompt attention",
}


def humanize_severity(key):
    """Map an internal severity key to its plain English label."""
    return SEVERITY_HUMAN.get(key, "needs attention")


def render_report(summary, checked, findings, actions, stream=None):
    """Write the formatted human-friendly report block to stderr.

    Sections: Plain conclusion / What we checked / Findings / What to do
    next. The block complements (never replaces) the [INFO]/[WARN] lines.
    Rendering failures are swallowed so the report block can never break
    the main diagnosis flow or alter the exit code.
    """
    import sys

    try:
        out = stream if stream is not None else sys.stderr
        lines = [REPORT_HEADER, ""]
        lines.append("-- Plain conclusion --")
        lines.append(summary)
        lines.append("")
        lines.append("-- What we checked --")
        if checked:
            for item in checked:
                lines.append(f"- {item}")
        else:
            lines.append("- nothing could be checked (see findings)")
        lines.append("")
        lines.append("-- Findings --")
        if findings:
            for item in findings:
                lines.append(f"- {item}")
        else:
            lines.append("- no problems detected")
        lines.append("")
        lines.append("-- What to do next --")
        if actions:
            for item in actions:
                lines.append(f"- {item}")
        else:
            lines.append("- no action required")
        lines.append("=" * len(REPORT_HEADER))
        print("\n".join(lines), file=out)
    except Exception:
        # The human-readable block is best-effort: never let a rendering
        # failure affect the JSON contract, the main flow, or exit codes.
        pass


def emit_json(results, stream=None):
    """Print the machine-readable JSON contract to stdout."""
    import json
    import sys

    out = stream if stream is not None else sys.stdout
    print(json.dumps(results, ensure_ascii=False, indent=2), file=out)


def attach_report(results, summary, severity_key, actions):
    """Attach the three plain-language fields to the JSON result.

    Existing result fields are never renamed or removed; only the three
    new fields are added.
    """
    results["summary"] = summary
    results["recommended_actions"] = list(actions)
    results["severity_human"] = humanize_severity(severity_key)
    return results
