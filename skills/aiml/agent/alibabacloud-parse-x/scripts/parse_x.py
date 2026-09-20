#!/usr/bin/env python3
"""
Parse-X Document Parsing & Extraction Tool

Two capabilities:
1. Parse  - Convert documents/media to structured Markdown/JSON/HTML
2. Extract - Schema-driven information extraction from parsed documents

Invocation: Parse-X HTTP (Spectrum gateway) with Bearer token auth via DASHSCOPE_API_KEY.
Accepts file URLs or local file paths — local files are auto-uploaded via DashScope file service.
"""

import os
import sys
import time
import json
import argparse
import secrets

import requests

# ---------------------------------------------------------------------------
# Skill identity — session ID from env, version from manifest.json.
# UA is constructed dynamically at cloud-call time.
# ---------------------------------------------------------------------------

_skill_session_id = None
_skill_version = None


def _get_skill_session_id():
    """Generate a fresh per-invocation session ID for the skill UA.

    External SKILL_SESSION_ID values are treated as untrusted because they may be
    reused across separate skill invocations. A new 32-char hex ID is generated
    for each runtime invocation to preserve the required uniqueness semantics.
    """
    global _skill_session_id
    if _skill_session_id is not None:
        return _skill_session_id

    # Do not reuse externally supplied session IDs. They are not guaranteed to be
    # fresh across distinct invocations, which violates the one-session-per-run
    # requirement for the User-Agent identity.
    sid = secrets.token_hex(16)  # 32 hex chars
    _skill_session_id = sid
    os.environ["SKILL_SESSION_ID"] = sid
    return _skill_session_id


def _get_skill_version():
    """Read skill version from references/manifest.json.

    Raises RuntimeError if manifest.json cannot be read, to avoid silently
    reporting an incorrect version (e.g. '0.0.0') in the User-Agent header.
    """
    global _skill_version
    if _skill_version is not None:
        return _skill_version
    try:
        manifest_path = os.path.join(os.path.dirname(__file__), "..", "references", "manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        version = manifest.get("version")
        if not version:
            raise RuntimeError("manifest.json is missing the 'version' field")
        _skill_version = version
    except FileNotFoundError:
        raise RuntimeError(
            f"Skill manifest not found at {manifest_path}. "
            "The skill may be incorrectly installed."
        )
    except Exception as e:
        raise RuntimeError(
            f"Failed to read skill version from manifest.json: {e}"
        )
    return _skill_version


def _get_skill_agent_ua():
    """Construct User-Agent at call time per SDK pattern.

    Pattern:
      AlibabaCloud-Agent-Skills/alibabacloud-parse-x/{session-id} skill-version/{version}
    """
    return (
        f"AlibabaCloud-Agent-Skills/alibabacloud-parse-x/{_get_skill_session_id()}"
        f" skill-version/{_get_skill_version()}"
    )

DEFAULT_PARSE_X_ENDPOINT = "https://dashscope.aliyuncs.com/api/v2/apps/parse-x"


# ---------------------------------------------------------------------------
# Parse-X HTTP Client (Spectrum gateway, Bearer token)
# ---------------------------------------------------------------------------

class ParseXHttpClient:
    """Parse-X HTTP client using Spectrum gateway with Bearer token auth."""

    def __init__(self, endpoint=None, api_key=None):
        self.endpoint = (
            endpoint
            or os.environ.get("PARSE_X_ENDPOINT", DEFAULT_PARSE_X_ENDPOINT)
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY", "")
        if not self.api_key:
            raise RuntimeError(
                "DASHSCOPE_API_KEY is not set. "
                "Export it before using Parse-X HTTP mode:\n"
                "  export DASHSCOPE_API_KEY=sk-xxx"
            )

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": _get_skill_agent_ua(),
            "X-DashScope-OssResourceResolve": "enable",
        }

    # ---- Parse ----

    def parse_submit(self, file_url=None, file_name=None, file_name_extension=None,
                     config_id=None, processing=None, output=None, notification=None):
        """Submit a parse task. Returns biz_id."""
        payload = {}
        if file_url:
            payload["file_url"] = file_url
        if file_name:
            payload["file_name"] = file_name
        if file_name_extension:
            payload["file_name_extension"] = file_name_extension
        if config_id:
            payload["config_id"] = config_id
        if processing:
            payload["processing"] = processing
        if output:
            payload["output"] = output
        if notification:
            payload["notification"] = notification

        url = f"{self.endpoint}/parse/submit"
        try:
            resp = requests.post(url, json=payload, timeout=30, headers=self._headers())
        except requests.ConnectionError as e:
            raise RuntimeError(
                f"Cannot connect to Parse-X endpoint '{self.endpoint}'. "
                f"Check network/proxy/firewall. Details: {e}"
            )

        result = resp.json()
        if "data" in result and result["data"].get("biz_id"):
            return result["data"]["biz_id"]

        code = result.get("code", "")
        message = result.get("message", "")
        request_id = result.get("request_id", "")
        if any(kw in str(code).lower() + str(message).lower()
               for kw in ["quota", "exhausted", "notopen", "throttl"]):
            raise QuotaExhaustedException(message)
        raise RuntimeError(f"Parse submit failed: {message} (code: {code}, request_id: {request_id})")

    def parse_result(self, biz_id, step_start=0, step_size=100):
        """Query parse result. Returns data dict."""
        url = f"{self.endpoint}/parse/result"
        payload = {"biz_id": biz_id, "step_start": step_start, "step_size": step_size}
        try:
            resp = requests.post(url, json=payload, timeout=60, headers=self._headers())
        except requests.ConnectionError as e:
            raise RuntimeError(f"Cannot connect to Parse-X for query. Details: {e}")
        result = resp.json()
        if "code" in result and result["code"] != "":
            code = result["code"]
            msg = result.get("message", "")
            request_id = result.get("request_id", "")
            if code == "ResultNotReady":
                return {"status": "processing"}
            raise RuntimeError(f"Parse result error: {msg} (code: {code}, request_id: {request_id})")
        return result.get("data", {})

    def parse(self, file_url=None, file_name=None, file_name_extension=None,
              config_id=None, processing=None, output=None, notification=None,
              poll_interval=3, max_wait=600):
        """Submit and poll parse result until complete.

        Returns a dict with structure:
          {"items": [...], "output_format_result": [...], ...}
        or a list of layout/segment items for backward compatibility.
        """
        biz_id = self.parse_submit(
            file_url=file_url, file_name=file_name,
            file_name_extension=file_name_extension,
            config_id=config_id, processing=processing,
            output=output, notification=notification
        )
        print(f"[Parse-X] Task submitted, biz_id: {biz_id}")

        all_items = []
        step_start = 0
        step_size = 100
        start_time = time.time()

        while True:
            if time.time() - start_time > max_wait:
                raise TimeoutError(f"Timed out waiting for parse result after {max_wait}s")

            time.sleep(poll_interval)
            data = self.parse_result(biz_id, step_start=step_start, step_size=step_size)

            # Check status: API uses 'processing' float (100.0 = complete),
            # but also support legacy 'status' string field
            status = str(data.get("status", "")).lower()
            processing_pct = data.get("processing", 0)

            if status in ("fail", "failed"):
                raise RuntimeError("Document parsing failed on the server side")

            if processing_pct == 100.0 or status == "success":
                # Collect paginated layouts/segments if present
                items = data.get("segments") or data.get("layouts") or []
                all_items.extend(items)

                # Check if more pages available
                if items and len(items) >= step_size:
                    step_start += len(items)
                    continue

                # Build result dict with metadata
                result = {}
                if all_items:
                    result["items"] = all_items

                # Attach synopsis/media fields
                for key in ("synopsis_result", "synopsis_segments", "synopsis_summary",
                            "markdown_content", "output_format_result",
                            "visual_layout_info"):
                    if key in data:
                        result[key] = data[key]

                # Also include page_count, table_count etc. for reference
                for key in ("page_count", "table_count", "image_count",
                            "paragraph_count", "successful_parsing_num"):
                    if key in data:
                        result[key] = data[key]

                # If only items (no metadata), return items directly for backward compat
                if all_items and len(result) == 1 and "items" in result:
                    return all_items
                return result if result else data

            # Still processing
            pct = processing_pct or 0
            print(f"  Processing... {pct}%")

    # ---- Extract ----

    def extract_submit(self, file_url=None, parsed_file_biz_id=None,
                       file_name=None, file_name_extension=None,
                       config_id=None, processing=None, output=None,
                       notification=None):
        """Submit an extract task. Returns biz_id."""
        payload = {}
        if file_url:
            payload["file_url"] = file_url
        if parsed_file_biz_id:
            payload["parsed_file_biz_id"] = parsed_file_biz_id
        if file_name:
            payload["file_name"] = file_name
        if file_name_extension:
            payload["file_name_extension"] = file_name_extension
        if config_id:
            payload["config_id"] = config_id
        if processing:
            payload["processing"] = processing
        if output:
            payload["output"] = output
        if notification:
            payload["notification"] = notification

        url = f"{self.endpoint}/extract/submit"
        try:
            resp = requests.post(url, json=payload, timeout=30, headers=self._headers())
        except requests.ConnectionError as e:
            raise RuntimeError(f"Cannot connect to Parse-X for extract submit. Details: {e}")

        result = resp.json()
        if "data" in result and result["data"].get("biz_id"):
            return result["data"]["biz_id"]

        code = result.get("code", "")
        message = result.get("message", "")
        request_id = result.get("request_id", "")
        raise RuntimeError(f"Extract submit failed: {message} (code: {code}, request_id: {request_id})")

    def extract_result(self, biz_id):
        """Query extract result. Returns data dict."""
        url = f"{self.endpoint}/extract/result"
        payload = {"biz_id": biz_id}
        try:
            resp = requests.post(url, json=payload, timeout=60, headers=self._headers())
        except requests.ConnectionError as e:
            raise RuntimeError(f"Cannot connect to Parse-X for extract query. Details: {e}")
        result = resp.json()
        if "code" in result and result["code"] != "":
            code = result["code"]
            msg = result.get("message", "")
            request_id = result.get("request_id", "")
            if code == "ResultNotReady":
                return {"status": "running"}
            raise RuntimeError(f"Extract result error: {msg} (code: {code}, request_id: {request_id})")
        return result.get("data", {})

    def extract(self, file_url=None, parsed_file_biz_id=None,
                file_name=None, file_name_extension=None,
                config_id=None, processing=None, output=None,
                notification=None, poll_interval=3, max_wait=600):
        """Submit and poll extract result until complete."""
        biz_id = self.extract_submit(
            file_url=file_url, parsed_file_biz_id=parsed_file_biz_id,
            file_name=file_name, file_name_extension=file_name_extension,
            config_id=config_id, processing=processing,
            output=output, notification=notification
        )
        print(f"[Parse-X] Extract task submitted, biz_id: {biz_id}")

        start_time = time.time()
        while True:
            if time.time() - start_time > max_wait:
                raise TimeoutError(f"Timed out waiting for extract result after {max_wait}s")

            time.sleep(poll_interval)
            data = self.extract_result(biz_id)

            status = str(data.get("status", "")).lower()
            if status in ("success", "completed"):
                return data
            elif status == "failed":
                raise RuntimeError("Extraction failed on the server side")
            else:
                print(f"  Extracting... (status: {status})")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FILE_SERVICE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/files"


def _file_service_headers():
    """Headers for file upload/delete operations."""
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    return {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": _get_skill_agent_ua(),
        "X-DashScope-Inner-Include-Url": "true",
    }


class QuotaExhaustedException(Exception):
    pass


def get_quota_exhausted_message():
    return (
        "\n⚠️  Free quota exhausted!\n\n"
        "Please activate Alibaba Cloud Parse-X or check your plan:\n"
        "  https://dashscope.console.aliyun.com\n"
    )


def _download_content_from_url(url):
    """Download text content from a signed OSS URL (e.g., output_format_result file)."""
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"Warning: Failed to download content from {url[:80]}...: {e}", file=sys.stderr)
        return None


def layouts_to_markdown(layouts):
    """Convert parse layouts (or extract result) to Markdown text.

    Handles multiple input shapes:
    - List of layout dicts (legacy items list)
    - Dict with 'items' + metadata (new parse result format)
    - Dict with 'extract_result_json' / 'fields' (extract result)
    """
    if not layouts:
        return ""

    # Extract result is a dict with extract_result_json / fields
    if isinstance(layouts, dict) and "extract_result_json" in layouts:
        return _extract_result_to_markdown(layouts)

    # Check for output_format_result — download markdown from signed URL
    if isinstance(layouts, dict) and "output_format_result" in layouts:
        orf = layouts["output_format_result"]
        if isinstance(orf, list) and orf:
            # Look for markdown output first, fall back to any available
            md_url = None
            json_url = None
            html_url = None
            for item in orf:
                ot = item.get("outputType", "")
                url = item.get("outputFileUrl", "")
                if ot == "markdown" and url:
                    md_url = url
                elif ot == "json" and url:
                    json_url = url
                elif ot == "html" and url:
                    html_url = url

            # Prefer markdown for markdown output
            content = None
            if md_url:
                print(f"[Parse-X] Downloading markdown from output URL...")
                content = _download_content_from_url(md_url)
            if content is not None:
                return content
            # If no markdown URL, try downloading JSON and converting
            if json_url:
                print(f"[Parse-X] Downloading JSON from output URL...")
                content = _download_content_from_url(json_url)
                if content is not None:
                    return content
            if html_url:
                print(f"[Parse-X] Downloading HTML from output URL...")
                content = _download_content_from_url(html_url)
                if content is not None:
                    return content

    # Handle dict wrapper with items + synopsis fields
    synopsis_parts = []
    if isinstance(layouts, dict):
        for key in ("synopsis_result", "synopsis_summary"):
            if layouts.get(key):
                synopsis_parts.append(str(layouts[key]))
        layouts = layouts.get("items", [])

    if not isinstance(layouts, list) or not layouts:
        return "\n".join(synopsis_parts)

    first_item = layouts[0]
    is_multimedia = (
        isinstance(first_item, dict)
        and (first_item.get("video_frames") or first_item.get("audio_frames"))
    )

    if is_multimedia:
        return _segments_to_markdown(layouts, synopsis_parts)

    md_parts = list(synopsis_parts)
    for layout in layouts:
        if isinstance(layout, dict):
            content = layout.get("markdownContent", "") or layout.get("text", "")
            md_parts.append(content)
        elif hasattr(layout, "markdown_content"):
            md_parts.append(layout.markdown_content or layout.text or "")
        else:
            md_parts.append(str(layout))
    return "\n".join(md_parts)


def _segments_to_markdown(segments, extra_parts=None):
    md_parts = list(extra_parts or [])
    for seg_idx, seg in enumerate(segments):
        if not isinstance(seg, dict):
            continue
        md_parts.append(f"## Segment {seg.get('index', seg_idx)}")
        md_parts.append(f"- Video URL: {seg.get('file_url', '')}")
        md_parts.append(f"- Time: {seg.get('start_time', 0):.2f}s - {seg.get('end_time', 0):.2f}s")

        for frame_type, label in [("video_frames", "Video Frames"), ("audio_frames", "Audio Frames")]:
            frames = seg.get(frame_type, [])
            if frames:
                md_parts.append(f"\n### {label}\n")
                for i, frame in enumerate(frames):
                    md_parts.append(f"#### {label[:-1]} {i+1}")
                    md_parts.append(f"- URL: {frame.get('file_url', '')}")
                    md_parts.append(f"- Time: {frame.get('start_time', 0):.2f}s - {frame.get('end_time', 0):.2f}s")
                    info = frame.get("text_info") or frame.get("ASR_info", "")
                    if info:
                        md_parts.append(f"- Info: {info}")
                    md_parts.append("")
    return "\n".join(md_parts)


def _extract_result_to_markdown(data):
    """Render extract result (with fields + citations) as Markdown."""
    parts = []
    parts.append("# Extraction Result\n")

    extract_json = data.get("extract_result_json") or {}
    if extract_json:
        parts.append("## Structured Data\n")
        parts.append("```json")
        parts.append(json.dumps(extract_json, ensure_ascii=False, indent=2))
        parts.append("```\n")

    fields = data.get("fields") or []
    if fields:
        parts.append("## Field Details\n")
        for f in fields:
            path = f.get("path", "")
            value = f.get("value", "")
            status = f.get("status", "")
            schema_type = f.get("schema_type", "")
            reason = f.get("reason", "")
            parts.append(f"### `{path}`")
            parts.append(f"- **Type**: {schema_type}")
            parts.append(f"- **Status**: {status}")
            parts.append(f"- **Value**: {value}")
            if reason:
                parts.append(f"- **Reason**: {reason}")
            citations = f.get("citations") or []
            if citations:
                parts.append("- **Citations**:")
                for c in citations:
                    quote = c.get("quote", "")
                    page = c.get("page", "")
                    parts.append(f"  - p.{page}: \"{quote}\"")
            parts.append("")

    return "\n".join(parts)


def can_use_parse_x():
    """Check if Parse-X HTTP mode is available (DASHSCOPE_API_KEY set)."""
    return bool(os.environ.get("DASHSCOPE_API_KEY"))


# ---------------------------------------------------------------------------
# Build processing / output dicts from CLI args
# ---------------------------------------------------------------------------

def build_parse_processing(args):
    """Build the `processing` block for /parse/submit from CLI args."""
    processing = {}
    if args.enhancement:
        processing["enhancement_mode"] = args.enhancement

    doc_cfg = {}
    if args.pages:
        doc_cfg["page_index"] = args.pages
    if args.head_foot:
        doc_cfg["head_foot"] = True
    if args.layout_position:
        doc_cfg["layout_position"] = True
    if args.image_caption:
        doc_cfg["image_caption"] = True
    if doc_cfg:
        processing["doc_processing_config"] = doc_cfg

    # Audio/video media config
    media_cfg = {}
    if args.enable_diarization:
        media_cfg["enable_diarization"] = True
    if args.enable_synopsis:
        media_cfg["enable_synopsis_parse"] = True
        media_cfg["enable_synopsis_segments"] = True
        media_cfg["enable_synopsis_summary"] = True
    if media_cfg:
        processing["media_processing_config"] = media_cfg

    if args.user_prompt:
        processing["user_prompt"] = args.user_prompt

    return processing or None


def build_parse_output(args):
    """Build the `output` block for /parse/submit from CLI args.

    Always includes 'markdown' to ensure the API returns output_format_result
    with downloadable content URLs, even for JSON/HTML output modes.
    """
    output = {}
    fmts = []
    if args.output:
        fmts.append(args.output)
    if args.visual_layout:
        fmts.append("visual_layout_info")
    # Always request markdown to get output_format_result URLs (content delivery)
    if "markdown" not in fmts:
        fmts.append("markdown")
    if fmts:
        output["output_file_format"] = fmts
    if args.layout_table_format:
        output["layout_table_format"] = args.layout_table_format
    if args.layout_image_format:
        output["layout_image_format"] = args.layout_image_format
    return output or None


def build_extract_processing(args):
    """Build the `processing` block for /extract/submit from CLI args."""
    extract_cfg = {}
    if args.extract_schema:
        # Allow passing a JSON file path or inline JSON string
        schema_str = args.extract_schema
        if os.path.isfile(schema_str):
            with open(schema_str, "r", encoding="utf-8") as f:
                schema_str = f.read()
        extract_cfg["extract_schema"] = schema_str
    if args.no_citation:
        extract_cfg["citation_required"] = False
    if args.allow_inference:
        extract_cfg["allow_inference"] = True

    processing = {}
    if extract_cfg:
        processing["extract_processing_config"] = extract_cfg
    if args.user_prompt:
        processing["user_prompt"] = args.user_prompt
    return processing


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------

def _resolve_local_file(input_path):
    """Upload a local file and return (file_url, file_name, cleanup_fn).

    cleanup_fn() should be called after processing to delete the uploaded file.
    Raises RuntimeError on upload failure.
    """
    if not os.path.isfile(input_path):
        raise RuntimeError(f"File not found: {input_path}")

    filename = os.path.basename(input_path)
    print(f"[FileService] Uploading local file: {filename} ...")
    with open(input_path, "rb") as f:
        resp = requests.post(
            FILE_SERVICE_URL,
            headers=_file_service_headers(),
            data={"purpose": "data"},
            files={"file": (filename, f)},
            timeout=300,
        )
    result = resp.json()
    if "error" in result:
        raise RuntimeError(
            f"File upload failed: {result['error'].get('message', result['error'])}"
        )
    file_id = result.get("id")
    if not file_id:
        raise RuntimeError(f"Upload response missing file id: {result}")
    print(f"[FileService] Uploaded, file_id: {file_id}")

    file_url = f"oss://bailian/{file_id}"

    def cleanup():
        print(f"[FileService] Cleaning up uploaded file: {file_id}")
        try:
            requests.delete(
                f"{FILE_SERVICE_URL}/{file_id}",
                headers=_file_service_headers(),
                timeout=30,
            )
            print("[FileService] Cleanup complete.")
        except Exception:
            pass

    return file_url, filename, cleanup


def run_parse(args):
    """Run the parse capability."""
    processing = build_parse_processing(args)
    output = build_parse_output(args)

    input_path = args.input
    is_url = input_path.startswith("http://") or input_path.startswith("https://")

    if not can_use_parse_x():
        print("Error: DASHSCOPE_API_KEY is not set.")
        print("Export it before running:")
        print("  export DASHSCOPE_API_KEY=sk-xxx")
        sys.exit(1)

    cleanup_fn = None
    try:
        if is_url:
            file_url = input_path
            file_name = input_path.split("/")[-1].split("?")[0]
        else:
            # Local file: upload via file service to obtain a URL
            file_url, file_name, cleanup_fn = _resolve_local_file(input_path)

        file_name_extension = args.file_ext
        if not file_name_extension and not is_url:
            ext = os.path.splitext(input_path)[1].lstrip(".")
            if ext:
                file_name_extension = ext

        print("Using Parse-X HTTP mode...")
        endpoint = args.endpoint
        client = ParseXHttpClient(endpoint=endpoint)
        return client.parse(
            file_url=file_url, file_name=file_name,
            file_name_extension=file_name_extension,
            processing=processing, output=output
        )
    except QuotaExhaustedException:
        print(get_quota_exhausted_message())
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        if cleanup_fn:
            cleanup_fn()


def run_extract(args):
    """Run the extract capability."""
    processing = build_extract_processing(args)
    if not processing or "extract_processing_config" not in processing:
        print("Error: --extract-schema is required for extract mode.")
        sys.exit(1)

    input_path = args.input
    parsed_biz_id = args.parsed_biz_id

    if not input_path and not parsed_biz_id:
        print("Error: Either <file_url>, <local_path>, or --parsed-biz-id is required for extract.")
        sys.exit(1)

    if not can_use_parse_x():
        print("Error: Extract mode requires DASHSCOPE_API_KEY.")
        print("  export DASHSCOPE_API_KEY=sk-xxx")
        sys.exit(1)

    is_url = input_path and (input_path.startswith("http://") or input_path.startswith("https://"))
    cleanup_fn = None

    try:
        if is_url:
            file_url = input_path
            file_name = input_path.split("/")[-1].split("?")[0]
        elif input_path and not parsed_biz_id:
            # Local file: upload via file service
            file_url, file_name, cleanup_fn = _resolve_local_file(input_path)
        else:
            file_url = None
            file_name = None

        file_name_extension = args.file_ext
        if not file_name_extension:
            # Auto-detect extension from URL or local file name
            if file_url:
                ext = os.path.splitext(file_url.split("?")[0])[1].lstrip(".")
                if ext:
                    file_name_extension = ext
            elif file_name:
                ext = os.path.splitext(file_name)[1].lstrip(".")
                if ext:
                    file_name_extension = ext

        print("Using Parse-X HTTP mode (extract)...")
        endpoint = args.endpoint
        client = ParseXHttpClient(endpoint=endpoint)
        return client.extract(
            file_url=file_url, parsed_file_biz_id=parsed_biz_id,
            file_name=file_name, file_name_extension=file_name_extension,
            processing=processing,
            output={},
            notification={"enable_event_callback": False}
        )
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        if cleanup_fn:
            cleanup_fn()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Parse-X Document Parsing & Extraction Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse a document URL
  python scripts/parse_x.py parse https://example.com/doc.pdf

  # Parse with VLM enhancement, pages 1-5
  python scripts/parse_x.py parse https://example.com/doc.pdf --enhancement AUTO --pages 1-5

  # Parse with visual layout info and markdown tables
  python scripts/parse_x.py parse https://example.com/doc.pdf \\
    --visual-layout --layout-table-format markdown

  # Parse audio/video with synopsis
  python scripts/parse_x.py parse https://example.com/video.mp4 --enable-synopsis

  # Parse a local file (auto-uploads, parses, then cleans up)
  python scripts/parse_x.py parse ./contract.pdf --output markdown

  # Extract structured data using a schema file
  python scripts/parse_x.py extract https://example.com/contract.pdf \\
    --extract-schema schema.json --user-prompt "金额用小写"

  # Extract from an already-parsed document (reuse parse result)
  python scripts/parse_x.py extract --parsed-biz-id parse-x-xxx \\
    --extract-schema '{"type":"object","properties":{"buyer":{"type":"string"}}}'
"""
    )

    # Top-level sub-commands: parse / extract
    subparsers = parser.add_subparsers(dest="command", help="Capability to invoke")

    # ---- parse sub-command ----
    parse_parser = subparsers.add_parser("parse", help="Parse a document or media file")
    parse_parser.add_argument("input", help="File URL or local file path to parse")
    parse_parser.add_argument(
        "--enhancement", choices=["BASIC", "ADVANCE", "AUTO"],
        help="Enhancement mode"
    )
    parse_parser.add_argument(
        "--output", choices=["markdown", "json", "html", "visual_layout_info"],
        default="markdown", help="Output format (default: markdown)"
    )
    parse_parser.add_argument("--pages", help="Page range, e.g. 1-5")
    parse_parser.add_argument("--output-file", help="Output file path")
    parse_parser.add_argument(
        "--head-foot", action="store_true", default=False,
        help="Parse headers and footers"
    )
    parse_parser.add_argument("--user-prompt", help="Custom user prompt")
    parse_parser.add_argument(
        "--visual-layout", action="store_true", default=False,
        help="Include visual_layout_info in output formats"
    )
    parse_parser.add_argument(
        "--layout-table-format", choices=["markdown", "html"],
        help="Table output format in markdown"
    )
    parse_parser.add_argument(
        "--layout-image-format", choices=["url"],
        help="Image output format"
    )
    parse_parser.add_argument(
        "--layout-position", action="store_true", default=False,
        help="Return bounding box coordinates"
    )
    parse_parser.add_argument(
        "--image-caption", action="store_true", default=False,
        help="Enable image description"
    )
    parse_parser.add_argument(
        "--enable-diarization", action="store_true", default=False,
        help="Enable speaker diarization (audio/video)"
    )
    parse_parser.add_argument(
        "--enable-synopsis", action="store_true", default=False,
        help="Enable synopsis parsing (audio/video)"
    )
    parse_parser.add_argument("--file-ext", help="File extension override")
    parse_parser.add_argument("--endpoint", help="Parse-X endpoint override")

    # ---- extract sub-command ----
    extract_parser = subparsers.add_parser(
        "extract", help="Extract structured data from a document"
    )
    extract_parser.add_argument("input", nargs="?", help="File URL or local path (optional if --parsed-biz-id given)")
    extract_parser.add_argument(
        "--parsed-biz-id",
        help="Reuse an already-parsed document's biz_id (skip re-parsing)"
    )
    extract_parser.add_argument(
        "--extract-schema", required=True,
        help="JSON schema for extraction (inline JSON or path to .json file)"
    )
    extract_parser.add_argument("--user-prompt", help="Custom user prompt for extraction")
    extract_parser.add_argument(
        "--no-citation", action="store_true", default=False,
        help="Disable citation in extract result"
    )
    extract_parser.add_argument(
        "--allow-inference", action="store_true", default=False,
        help="Allow the model to infer missing fields"
    )
    extract_parser.add_argument("--output-file", help="Output file path")
    extract_parser.add_argument("--file-ext", help="File extension override")
    extract_parser.add_argument("--endpoint", help="Parse-X endpoint override")

    args = parser.parse_args()

    if not args.command:
        # Backward compatibility: if no subcommand, default to parse with old-style args
        # Show help instead of silently failing
        parser.print_help()
        sys.exit(0)

    if args.command == "parse":
        result = run_parse(args)
    elif args.command == "extract":
        result = run_extract(args)
    else:
        parser.print_help()
        sys.exit(0)

    if not result:
        print("No result obtained.")
        sys.exit(1)

    # Render output
    output_format = getattr(args, "output", "markdown")
    if output_format == "json" or args.command == "extract":
        # For JSON output: download content from output_format_result if available
        if isinstance(result, dict) and "output_format_result" in result:
            orf = result["output_format_result"]
            if isinstance(orf, list):
                for item in orf:
                    ot = item.get("outputType", "")
                    url = item.get("outputFileUrl", "")
                    if ot == "markdown" and url:
                        downloaded = _download_content_from_url(url)
                        if downloaded:
                            result["markdown_content"] = downloaded
                            break
        content = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        # Markdown/HTML: try to get content from output_format_result URLs,
        # fall back to constructing from layouts
        content = layouts_to_markdown(result)
        if not content and isinstance(result, dict):
            # Last resort: serialize as JSON
            content = json.dumps(result, ensure_ascii=False, indent=2)

    output_file = getattr(args, "output_file", None)
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Result saved to: {output_file}")
    else:
        print("\n" + "=" * 60)
        print(f"{'Extraction' if args.command == 'extract' else 'Parsing'} Result:")
        print("=" * 60)
        print(content)


if __name__ == "__main__":
    main()
