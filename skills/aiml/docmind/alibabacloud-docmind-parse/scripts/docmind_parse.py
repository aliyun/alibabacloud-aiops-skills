#!/usr/bin/env python3
"""
DocMind Document Parsing Tool

Two invocation modes:
1. V2 API Direct (free mode) - configured via DOCMIND_V2_ENDPOINT
2. Alibaba Cloud POP - credentials obtained via the default credential chain

Routing: prefer POP when credentials are available, otherwise fall back to V2.
"""

import os
import sys
import time
import json
import argparse

SKILL_USER_AGENT = "AlibabaCloud-Agent-Skills/alibabacloud-docmind-parse/" + os.environ.get("SKILL_SESSION_ID", "unknown")


class DocMindV2Client:
    """V2 API direct client (free mode)."""

    def __init__(self, endpoint=None):
        self.endpoint = endpoint or os.environ.get("DOCMIND_V2_ENDPOINT", "docmind.aliyuncs.com")
        if not self.endpoint.startswith("http"):
            self.endpoint = f"http://{self.endpoint}"

    def submit(self, file_url=None, file_name=None, file_base64=None,
               file_name_extension=None, enhancement_mode=None, page_index=None,
               output_format=None, head_foot=None, user_prompt=None, option=None,
               markdown_table=None, markdown_image=None, doc_extra_parameters=None,
               extra_parameters=None, oss_config=None, enable_event_callback=None):
        """Submit a document parsing task."""
        import requests

        payload = {"document": {}}

        if file_url:
            payload["document"]["fileUrl"] = file_url
        if file_base64:
            payload["document"]["fileBase64"] = file_base64
        if file_name:
            payload["document"]["fileName"] = file_name
        if file_name_extension:
            payload["document"]["fileNameExtension"] = file_name_extension

        processing = {}
        if enhancement_mode:
            processing["enhancementMode"] = enhancement_mode
        if page_index:
            processing["pageIndex"] = page_index
        if head_foot is not None:
            processing["headFoot"] = head_foot
        if user_prompt:
            processing["userPrompt"] = user_prompt
        if option:
            processing["option"] = option
        if processing:
            payload["processing"] = processing

        output = {}
        if output_format:
            output["outputFormat"] = output_format if isinstance(output_format, list) else [output_format]
        if markdown_table:
            output["markdownTable"] = markdown_table if isinstance(markdown_table, list) else [markdown_table]
        if markdown_image:
            output["markdownImage"] = markdown_image if isinstance(markdown_image, list) else [markdown_image]
        if doc_extra_parameters:
            output["docExtraParameters"] = doc_extra_parameters
        if extra_parameters:
            output["extraParameters"] = extra_parameters
        if oss_config:
            output["ossConfig"] = oss_config
        if output:
            payload["output"] = output

        if enable_event_callback is not None:
            payload["notification"] = {"enableEventCallback": enable_event_callback}

        url = f"{self.endpoint}/skill/submit"
        try:
            resp = requests.post(url, json=payload, timeout=30,
                                 headers={"User-Agent": SKILL_USER_AGENT})
        except requests.ConnectionError as e:
            raise RuntimeError(
                f"Cannot connect to V2 endpoint '{self.endpoint}'. "
                "Check network connectivity, proxy settings, or firewall rules. "
                f"Details: {e}"
            )
        result = resp.json()

        if result.get("success") or result.get("data", {}).get("bizId"):
            return result["data"]["bizId"]

        code = result.get("code", "")
        message = result.get("message", "")
        if any(kw in code.lower() + message.lower() for kw in ["quota", "notopen", "throttl", "limit", "exceed"]):
            raise QuotaExhaustedException(message)

        raise RuntimeError(f"Failed to submit task: {message} (code: {code})")

    def query(self, biz_id, layout_step_size=100, layout_num=0):
        """Query parsing result."""
        import requests

        url = f"{self.endpoint}/skill/query"
        payload = {
            "bizId": biz_id,
            "layoutStepSize": layout_step_size,
            "layoutNum": layout_num
        }
        try:
            resp = requests.post(url, json=payload, timeout=30,
                                 headers={"User-Agent": SKILL_USER_AGENT})
        except requests.ConnectionError as e:
            raise RuntimeError(
                f"Cannot connect to V2 endpoint '{self.endpoint}' for query. "
                f"Details: {e}"
            )
        result = resp.json()
        return result.get("data", {})

    def parse(self, file_url=None, file_name=None, file_base64=None,
              file_name_extension=None, enhancement_mode=None, page_index=None,
              output_format=None, head_foot=None, user_prompt=None, option=None,
              markdown_table=None, markdown_image=None, doc_extra_parameters=None,
              extra_parameters=None, oss_config=None, enable_event_callback=None,
              poll_interval=3, max_wait=600):
        """Submit and poll until the complete parsing result is retrieved."""
        biz_id = self.submit(
            file_url=file_url, file_name=file_name, file_base64=file_base64,
            file_name_extension=file_name_extension,
            enhancement_mode=enhancement_mode, page_index=page_index,
            output_format=output_format, head_foot=head_foot,
            user_prompt=user_prompt, option=option,
            markdown_table=markdown_table, markdown_image=markdown_image,
            doc_extra_parameters=doc_extra_parameters,
            extra_parameters=extra_parameters, oss_config=oss_config,
            enable_event_callback=enable_event_callback
        )
        print(f"Task submitted, bizId: {biz_id}")

        all_layouts = []
        layout_num = 0
        step_size = 100
        start_time = time.time()

        while True:
            if time.time() - start_time > max_wait:
                raise TimeoutError(f"Timed out waiting for result after {max_wait}s")

            time.sleep(poll_interval)
            data = self.query(biz_id, layout_step_size=step_size, layout_num=layout_num)

            status = data.get("status", "").lower()
            if status == "fail":
                raise RuntimeError("Document parsing failed on the server side")
            if status == "success":
                # Check for audio/video segments format
                if data.get("segments"):
                    items = data["segments"]
                else:
                    items = data.get("layouts", [])

                all_layouts.extend(items)
                if len(items) < step_size:
                    break
                layout_num += len(items)
            else:
                processing = data.get("processing", 0)
                print(f"  Processing... {processing}%")

        return all_layouts


class DocMindPopClient:
    """Alibaba Cloud POP client (uses default credential chain)."""

    def __init__(self, endpoint="docmind-api.cn-hangzhou.aliyuncs.com"):
        self.endpoint = endpoint
        self.client = self._init_client()

    def _init_client(self):
        from alibabacloud_credentials.client import Client as CredClient
        from alibabacloud_docmind_api20220711.client import Client as DocMindClient
        from alibabacloud_tea_openapi import models as open_api_models

        cred = CredClient()
        config = open_api_models.Config(
            credential=cred,
            endpoint=self.endpoint,
            user_agent=SKILL_USER_AGENT
        )
        return DocMindClient(config)

    def submit(self, file_path=None, file_url=None, file_name=None,
               enhancement_mode=None, page_index=None, output_format=None,
               formula_enhancement=False):
        """Submit a document parsing task."""
        from alibabacloud_docmind_api20220711 import models as docmind_models
        from alibabacloud_tea_util import models as util_models

        if file_path and os.path.isfile(file_path):
            request = docmind_models.SubmitDocParserJobAdvanceRequest(
                file_url_object=open(file_path, "rb"),
                file_name=file_name or os.path.basename(file_path),
            )
            if enhancement_mode:
                request.llm_enhancement = True
                request.enhancement_mode = enhancement_mode
            if page_index:
                request.page_index = page_index
            if output_format:
                request.output_format = output_format if isinstance(output_format, list) else [output_format]
            if formula_enhancement:
                request.formula_enhancement = True

            runtime = util_models.RuntimeOptions()
            response = self.client.submit_doc_parser_job_advance(request, runtime)
        else:
            request = docmind_models.SubmitDocParserJobRequest(
                file_url=file_url,
                file_name=file_name,
            )
            if enhancement_mode:
                request.llm_enhancement = True
                request.enhancement_mode = enhancement_mode
            if page_index:
                request.page_index = page_index
            if output_format:
                request.output_format = output_format if isinstance(output_format, list) else [output_format]
            if formula_enhancement:
                request.formula_enhancement = True

            response = self.client.submit_doc_parser_job(request)

        return response.body.data.id

    def query_status(self, task_id):
        """Query task status."""
        from alibabacloud_docmind_api20220711 import models as docmind_models

        request = docmind_models.QueryDocParserStatusRequest(id=task_id)
        response = self.client.query_doc_parser_status(request)
        return response.body.data

    def get_result(self, task_id, layout_step_size=100, layout_num=0):
        """Retrieve parsing result."""
        from alibabacloud_docmind_api20220711 import models as docmind_models

        request = docmind_models.GetDocParserResultRequest(
            id=task_id,
            layout_step_size=layout_step_size,
            layout_num=layout_num
        )
        response = self.client.get_doc_parser_result(request)
        return response.body.data

    def parse(self, file_path=None, file_url=None, file_name=None,
              enhancement_mode=None, page_index=None, output_format=None,
              formula_enhancement=False, poll_interval=3, max_wait=600):
        """Submit and poll until the complete parsing result is retrieved."""
        task_id = self.submit(
            file_path=file_path, file_url=file_url, file_name=file_name,
            enhancement_mode=enhancement_mode, page_index=page_index,
            output_format=output_format, formula_enhancement=formula_enhancement
        )
        print(f"Task submitted, taskId: {task_id}")

        start_time = time.time()

        while True:
            if time.time() - start_time > max_wait:
                raise TimeoutError(f"Timed out waiting for result after {max_wait}s")

            time.sleep(poll_interval)
            status_data = self.query_status(task_id)
            status = (status_data.status or "").lower()

            if status == "success":
                print("  Parsing complete")
                break
            elif status in ("fail", "failed"):
                raise RuntimeError("Document parsing failed on the server side")
            else:
                processing = getattr(status_data, "processing", 0) or 0
                print(f"  Processing... {processing}%")

        all_results = []
        result_num = 0
        step_size = 100

        while True:
            result_data = self.get_result(task_id, layout_step_size=step_size, layout_num=result_num)

            # Check for audio/video segments format
            if hasattr(result_data, "segments") and result_data.segments:
                items = result_data.segments
            elif isinstance(result_data, dict) and result_data.get("segments"):
                items = result_data["segments"]
            # Standard document layouts
            elif hasattr(result_data, "layouts") and result_data.layouts:
                items = result_data.layouts
            elif isinstance(result_data, dict):
                items = result_data.get("layouts", [])
            else:
                items = []

            all_results.extend(items)
            if len(items) < step_size:
                break
            result_num += len(items)

        return all_results


class QuotaExhaustedException(Exception):
    """Raised when the free quota is exhausted."""
    pass


def get_quota_exhausted_message(fell_back_from_pop=False):
    """Return a user-facing message for quota exhaustion."""
    if fell_back_from_pop:
        return (
            "\n⚠️  Both POP and V2 modes are unavailable!\n\n"
            "POP mode failed (see error above), and the V2 free quota is also exhausted.\n\n"
            "Please fix POP mode and retry:\n\n"
            "1. Upgrade dependencies to resolve version conflicts:\n"
            "   pip install --upgrade alibabacloud-credentials alibabacloud-gateway-pop\n\n"
            "2. Verify Alibaba Cloud credentials are configured:\n"
            "   export ALIBABA_CLOUD_ACCESS_KEY_ID=your_id\n"
            "   export ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_secret\n\n"
            "3. Alternatively, activate DocMind service to use V2 quota:\n"
            "   https://docmind.console.aliyun.com/doc-overview\n"
        )
    return (
        "\n⚠️  Free quota exhausted!\n\n"
        "You can continue using the document parsing service by:\n\n"
        "1. Activating Alibaba Cloud DocMind (3,000 pages/month free):\n"
        "   https://docmind.console.aliyun.com/doc-overview\n\n"
        "2. Configuring credentials via the default credential chain\n"
        "   (env vars, config file, or ECS RAM role):\n"
        "   https://help.aliyun.com/zh/sdk/developer-reference/v2-manage-python-access-credentials\n\n"
        "3. Re-running the parse command after setup.\n"
    )


def layouts_to_markdown(layouts):
    """Convert layouts or segments to Markdown text."""
    if not layouts:
        return ""

    # Detect audio/video segments format
    first_item = layouts[0] if isinstance(layouts, list) and layouts else None
    is_multimedia = (
        isinstance(first_item, dict) and
        (first_item.get("video_frames") or first_item.get("audio_frames"))
    )

    if is_multimedia:
        md_parts = []
        for seg_idx, seg in enumerate(layouts):
            if isinstance(seg, dict):
                file_url = seg.get("file_url", "")
                start_time = seg.get("start_time", 0)
                end_time = seg.get("end_time", 0)
                index = seg.get("index", seg_idx)

                md_parts.append(f"## Segment {index}")
                md_parts.append(f"- Video URL: {file_url}")
                md_parts.append(f"- Time: {start_time:.2f}s - {end_time:.2f}s")

                # Video frames
                video_frames = seg.get("video_frames", [])
                if video_frames:
                    md_parts.append("")
                    md_parts.append("### Video Frames")
                    md_parts.append("")
                    for i, frame in enumerate(video_frames):
                        frame_url = frame.get("file_url", "")
                        frame_start = frame.get("start_time", 0)
                        frame_end = frame.get("end_time", 0)
                        text_info = frame.get("text_info", "")
                        md_parts.append(f"#### Frame {i+1}")
                        md_parts.append(f"- URL: {frame_url}")
                        md_parts.append(f"- Time: {frame_start:.2f}s - {frame_end:.2f}s")
                        if text_info:
                            md_parts.append(f"- Description: {text_info}")
                        md_parts.append("")

                # Audio frames
                audio_frames = seg.get("audio_frames", [])
                if audio_frames:
                    md_parts.append("")
                    md_parts.append("### Audio Frames")
                    md_parts.append("")
                    for i, frame in enumerate(audio_frames):
                        frame_url = frame.get("file_url", "")
                        frame_start = frame.get("start_time", 0)
                        frame_end = frame.get("end_time", 0)
                        asr_info = frame.get("ASR_info", "")
                        md_parts.append(f"#### Audio {i+1}")
                        md_parts.append(f"- URL: {frame_url}")
                        md_parts.append(f"- Time: {frame_start:.2f}s - {frame_end:.2f}s")
                        if asr_info:
                            md_parts.append(f"- ASR: {asr_info}")
                        md_parts.append("")

        return "\n".join(md_parts)

    # Standard document layouts
    md_parts = []
    for layout in layouts:
        if isinstance(layout, dict):
            content = layout.get("markdownContent", "") or layout.get("text", "")
            md_parts.append(content)
        elif hasattr(layout, "markdown_content"):
            md_parts.append(layout.markdown_content or layout.text or "")
        else:
            md_parts.append(str(layout))
    return "\n".join(md_parts)


def check_pop_dependencies():
    """Check POP mode dependency version compatibility. Returns (ok, error_message)."""
    try:
        from importlib.metadata import version
    except ImportError:
        from importlib_metadata import version  # Python < 3.8 fallback

    try:
        cred_version = version("alibabacloud-credentials")
    except Exception:
        return True, None  # Not installed; skip version check, let credential check handle it

    try:
        gateway_version = version("alibabacloud-gateway-pop")
    except Exception:
        return True, None  # Not installed; skip

    def parse_version(v):
        try:
            return tuple(int(x) for x in v.split(".")[:3])
        except (ValueError, AttributeError):
            return (0, 0, 0)

    cred_ver = parse_version(cred_version)
    gateway_ver = parse_version(gateway_version)

    # alibabacloud-credentials >= 1.0 requires alibabacloud-gateway-pop >= 0.1
    if cred_ver >= (1, 0, 0) and gateway_ver < (0, 1, 0):
        return False, (
            f"POP mode dependency version conflict: alibabacloud-credentials=={cred_version} "
            f"requires alibabacloud-gateway-pop>=0.1.0, but {gateway_version} is installed.\n"
            "Please upgrade:\n"
            "  pip install --upgrade alibabacloud-gateway-pop"
        )

    return True, None


def can_use_pop_mode():
    """Check if the default credential chain is available. Returns (ok, error_message)."""
    # Check dependency version compatibility first
    deps_ok, deps_error = check_pop_dependencies()
    if not deps_ok:
        return False, deps_error

    try:
        from alibabacloud_credentials.client import Client as CredClient
        cred = CredClient()
        cred.get_credential()
        return True, None
    except ModuleNotFoundError as e:
        missing = getattr(e, "name", "alibabacloud_credentials")
        return False, (
            f"POP mode is missing the Alibaba Cloud SDK package: {missing}\n"
            "Install required dependencies:\n"
            "  pip install alibabacloud-credentials "
            "alibabacloud_docmind_api20220711 "
            "alibabacloud_tea_openapi alibabacloud_tea_util"
        )
    except Exception as e:
        return False, (
            f"POP mode credential chain error: {e}\n"
            "Verify environment variables are set:\n"
            "  export ALIBABA_CLOUD_ACCESS_KEY_ID=your_id\n"
            "  export ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_secret"
        )


def parse_document(input_path, mode="auto", enhancement_mode=None,
                   page_index=None, output_format=None, head_foot=None,
                   user_prompt=None, option=None, markdown_table=None,
                   markdown_image=None, doc_extra_parameters=None,
                   extra_parameters=None, oss_config=None,
                   enable_event_callback=None, file_name_extension=None):
    """Unified entry point for document parsing."""
    V2_MAX_FILE_SIZE = int(3.75 * 1024 * 1024)  # 3.75MB (5MB limit with ~33% base64 overhead)

    is_url = input_path.startswith("http://") or input_path.startswith("https://")
    file_path = None if is_url else input_path
    file_url = input_path if is_url else None
    file_name = os.path.basename(input_path) if not is_url else input_path.split("/")[-1].split("?")[0]

    if not output_format:
        output_format = ["markdown"]

    pop_available, pop_error = can_use_pop_mode()
    fell_back_from_pop = False

    use_pop = False
    if mode == "pop":
        use_pop = True
    elif mode == "v2":
        use_pop = False
    elif mode == "auto":
        use_pop = pop_available

    if use_pop:
        if not pop_available:
            print(f"Error: {pop_error}")
            sys.exit(1)
        try:
            print("Using Alibaba Cloud POP mode...")
            client = DocMindPopClient()
            return client.parse(
                file_path=file_path, file_url=file_url, file_name=file_name,
                enhancement_mode=enhancement_mode, page_index=page_index,
                output_format=output_format
            )
        except Exception as e:
            if mode == "auto":
                print(f"⚠ POP mode failed: {e}")
                print("Falling back to V2 mode...")
                fell_back_from_pop = True
            else:
                print(f"Error: POP mode execution failed: {e}")
                sys.exit(1)

    # V2 mode path (direct or fallback from POP)
    file_base64 = None
    if not is_url:
        import base64
        if not os.path.isfile(input_path):
            print(f"Error: File not found: {input_path}")
            print("Please verify the file path and try again.")
            sys.exit(1)

        # File size pre-check
        file_size = os.path.getsize(input_path)
        if file_size > V2_MAX_FILE_SIZE:
            size_mb = file_size / 1024 / 1024
            if mode == "auto" and pop_available:
                print(f"⚠ File size ({size_mb:.1f}MB) exceeds V2 limit, switching to POP mode...")
                client = DocMindPopClient()
                return client.parse(
                    file_path=file_path, file_url=file_url, file_name=file_name,
                    enhancement_mode=enhancement_mode, page_index=page_index,
                    output_format=output_format
                )
            elif mode == "v2":
                print(f"Error: File size ({size_mb:.1f}MB) exceeds V2 limit (5MB after base64 encoding)")
                print("Use --mode pop or configure Alibaba Cloud credentials for POP mode (supports 150MB)")
                sys.exit(1)
            else:
                print(f"Error: File size ({size_mb:.1f}MB) exceeds V2 limit and POP mode is unavailable")
                print("Configure Alibaba Cloud credentials for POP mode (supports 150MB):")
                print("  pip install alibabacloud-credentials alibabacloud_docmind_api20220711 alibabacloud_tea_openapi alibabacloud_tea_util")
                print("  export ALIBABA_CLOUD_ACCESS_KEY_ID=your_id")
                print("  export ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_secret")
                sys.exit(1)

        with open(input_path, "rb") as f:
            file_base64 = base64.b64encode(f.read()).decode("utf-8")
        if not file_name_extension:
            ext = os.path.splitext(input_path)[1].lstrip(".")
            if ext:
                file_name_extension = ext

    print("Using V2 API free mode...")
    try:
        client = DocMindV2Client()
        return client.parse(
            file_url=file_url, file_name=file_name,
            file_base64=file_base64,
            file_name_extension=file_name_extension,
            enhancement_mode=enhancement_mode, page_index=page_index,
            output_format=output_format, head_foot=head_foot,
            user_prompt=user_prompt, option=option,
            markdown_table=markdown_table, markdown_image=markdown_image,
            doc_extra_parameters=doc_extra_parameters,
            extra_parameters=extra_parameters, oss_config=oss_config,
            enable_event_callback=enable_event_callback
        )
    except QuotaExhaustedException:
        print(get_quota_exhausted_message(fell_back_from_pop=fell_back_from_pop))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="DocMind Document Parsing Tool")
    parser.add_argument("input", help="Local file path or file URL")
    parser.add_argument("--mode", choices=["auto", "v2", "pop"], default="auto",
                        help="Invocation mode (default: auto)")
    parser.add_argument("--enhancement", choices=["VLM", "LLM", "DIGITAL", "OCR", "AUTO"],
                        help="Enhancement mode")
    parser.add_argument("--output", choices=["markdown", "json", "html"], default="markdown",
                        help="Output format (default: markdown)")
    parser.add_argument("--pages", help="Page range to parse, e.g. 1-5")
    parser.add_argument("--output-file", help="Output file path")
    parser.add_argument("--head-foot", action="store_true", default=None,
                        help="Parse headers and footers")
    parser.add_argument("--user-prompt", help="Custom user prompt")
    parser.add_argument("--option", help="Document parsing options")
    parser.add_argument("--markdown-table", choices=["html", "markdown"],
                        help="Table output format")
    parser.add_argument("--markdown-image", choices=["html", "markdown"],
                        help="Image output format")
    parser.add_argument("--file-ext", help="File extension (alternative to fileName)")

    args = parser.parse_args()
    output_format = [args.output] if args.output else ["markdown"]

    layouts = parse_document(
        input_path=args.input, mode=args.mode,
        enhancement_mode=args.enhancement, page_index=args.pages,
        output_format=output_format, head_foot=args.head_foot,
        user_prompt=args.user_prompt, option=args.option,
        markdown_table=args.markdown_table, markdown_image=args.markdown_image,
        file_name_extension=args.file_ext
    )

    if not layouts:
        print("No parsing result obtained")
        sys.exit(1)

    if args.output == "json":
        content = json.dumps(layouts, ensure_ascii=False, indent=2)
    else:
        content = layouts_to_markdown(layouts)

    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Result saved to: {args.output_file}")
    else:
        print("\n" + "=" * 60)
        print("Parsing Result:")
        print("=" * 60)
        print(content)


if __name__ == "__main__":
    main()
