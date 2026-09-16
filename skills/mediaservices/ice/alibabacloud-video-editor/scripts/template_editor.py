#!/usr/bin/env python3
"""Create, inspect, expand, and use Alibaba Cloud ICE normal templates."""

import argparse
import json
import os
import re
import sys
from typing import Any, Optional

VALID_REGIONS = [
    "cn-shanghai",
    "cn-beijing",
    "cn-hangzhou",
    "cn-shenzhen",
    "cn-zhangjiakou",
    "ap-southeast-1",
]
TEMPLATE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
PRESETS = (
    "video-concat",
    "opening-ending",
    "watermark",
    "mute",
    "mute-with-audio",
)


class ValidationError(Exception):
    pass


def load_json_input(value: str, name: str) -> dict:
    try:
        with open(value, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        try:
            return json.loads(value)
        except json.JSONDecodeError as error:
            raise ValidationError(f"Invalid JSON for {name}: {error}") from error
    except json.JSONDecodeError as error:
        raise ValidationError(f"Invalid JSON in {name} file: {error}") from error


def validate_output_config(config: dict) -> dict:
    if not isinstance(config, dict):
        raise ValidationError("OutputMediaConfig must be a JSON object")
    media_url = config.get("MediaURL")
    if not isinstance(media_url, str) or not media_url.startswith(("http://", "https://")):
        raise ValidationError("OutputMediaConfig.MediaURL must be an HTTP(S) URL")
    return config


def load_cloud_api():
    try:
        from video_editor import (
            call_api,
            check_output_path_exists,
            create_client,
            generate_client_token,
        )
    except SystemExit as error:
        raise RuntimeError(
            "Cloud commands require the packages in scripts/requirements.txt"
        ) from error
    return call_api, check_output_path_exists, create_client, generate_client_token


def require_explicit_overwrite(output_exists: bool, overwrite: bool) -> None:
    if output_exists and not overwrite:
        raise ValidationError(
            "Output object already exists; choose a new path or pass --overwrite"
        )


def validate_template_id(template_id: str) -> str:
    if not template_id or len(template_id) > 128:
        raise ValidationError("TemplateId must be 1-128 characters")
    if not TEMPLATE_ID_PATTERN.fullmatch(template_id):
        raise ValidationError(
            "TemplateId may contain only letters, digits, hyphens, and underscores"
        )
    return template_id


def validate_template_config(config: dict) -> dict:
    if not isinstance(config, dict):
        raise ValidationError("Template Config must be a JSON object")
    track_fields = ("VideoTracks", "AudioTracks", "ImageTracks", "SubtitleTracks")
    if not any(field in config for field in track_fields):
        raise ValidationError(
            "Template Config must contain at least one video, audio, image, or subtitle track"
        )
    for field in track_fields:
        if field in config and not isinstance(config[field], list):
            raise ValidationError(f"Config.{field} must be an array")
    return config


def array_item(array_name: str, media_field: str) -> dict:
    return {
        "Sys_Type": "ArrayItems",
        "Sys_ArrayObject": f"${array_name}",
        "Sys_Template": {media_field: f"${media_field}"},
    }


def build_preset(
    preset: str,
    opening_media_id: Optional[str] = None,
    ending_media_id: Optional[str] = None,
    watermark_image_id: Optional[str] = None,
) -> dict:
    if preset not in PRESETS:
        raise ValidationError(f"Unknown preset '{preset}'")

    video_item = array_item("VideoArray", "MediaId")
    if preset == "mute":
        video_item["Sys_Template"]["Effects"] = [{"Type": "Volume", "Gain": "0"}]

    video_clips = [video_item]
    if preset == "opening-ending":
        if not opening_media_id or not ending_media_id:
            raise ValidationError(
                "opening-ending requires --opening-media-id and --ending-media-id"
            )
        video_clips = [
            {"MediaId": opening_media_id},
            video_item,
            {"MediaId": ending_media_id},
        ]

    config = {"VideoTracks": [{"VideoTrackClips": video_clips}]}

    if preset == "watermark":
        if not watermark_image_id:
            raise ValidationError("watermark requires --watermark-image-id")
        config["ImageTracks"] = [{
            "ImageTrackClips": [{
                "ImageId": watermark_image_id,
                "Width": 200,
                "Height": 60,
                "X": 40,
                "Y": 40,
            }]
        }]

    if preset == "mute-with-audio":
        video_item["Sys_Template"]["Effects"] = [{"Type": "Volume", "Gain": "0"}]
        config["AudioTracks"] = [{
            "AudioTrackClips": {
                "Sys_Type": "Array",
                "Sys_ArrayObject": "$AudioArray",
                "Sys_Template": {"MediaId": "$MediaId"},
            }
        }]

    return config


def write_json(data: Any, output: Optional[str]) -> None:
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if output:
        os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
        with open(output, "w", encoding="utf-8") as file:
            file.write(payload)
        print(f"Written to {output}")
    else:
        print(payload, end="")


_MISSING = object()
_DROP = object()


def _parameter(value: str, params: dict, local_params: dict) -> Any:
    name, separator, default = value[1:].partition(":")
    result = local_params.get(name, params.get(name, _MISSING))
    if result is not _MISSING:
        return result
    if not separator:
        raise ValidationError(f"Missing template parameter: {name}")
    if default == "NULL":
        return _DROP
    try:
        return json.loads(default)
    except json.JSONDecodeError:
        return default


def _template_parameters(value: Any) -> set[str]:
    if isinstance(value, str) and value.startswith("$"):
        return {value[1:].partition(":")[0]}
    if isinstance(value, list):
        return set().union(*(_template_parameters(item) for item in value), set())
    if isinstance(value, dict):
        return set().union(*(_template_parameters(item) for item in value.values()), set())
    return set()


def _expand_array(node: dict, params: dict) -> list:
    array_ref = node.get("Sys_ArrayObject")
    if not isinstance(array_ref, str) or not array_ref.startswith("$"):
        raise ValidationError("Sys_ArrayObject must be a $parameter")
    name = array_ref[1:].partition(":")[0]
    items = params.get(name, _MISSING)
    if not isinstance(items, list):
        raise ValidationError(f"Template parameter {name} must be an array")
    template = node.get("Sys_Template")
    if template is None:
        raise ValidationError(f"{node.get('Sys_Type')} requires Sys_Template")
    names = _template_parameters(template) - params.keys()
    expanded = []
    for item in items:
        if isinstance(item, dict):
            local_params = item
        elif len(names) == 1:
            local_params = {next(iter(names)): item}
        else:
            raise ValidationError(
                f"Template parameter {name} items must be objects because "
                f"Sys_Template has {len(names)} parameters"
            )
        expanded.append(_expand_template(template, params, local_params))
    return expanded


def _expand_template(value: Any, params: dict, local_params: Optional[dict] = None) -> Any:
    local_params = local_params or {}
    if isinstance(value, str) and value.startswith("$"):
        return _parameter(value, params, local_params)
    if isinstance(value, list):
        result = []
        for item in value:
            expanded = _expand_template(item, params, local_params)
            if expanded is _DROP:
                continue
            if isinstance(item, dict) and item.get("Sys_Type") == "ArrayItems":
                result.extend(expanded)
            else:
                result.append(expanded)
        return result
    if isinstance(value, dict):
        if value.get("Sys_Type") in ("Array", "ArrayItems"):
            return _expand_array(value, params)
        result = {}
        for key, item in value.items():
            expanded = _expand_template(item, params, local_params)
            if expanded is not _DROP:
                result[key] = expanded
        return result
    return value


def video_loop_warnings(timeline: dict) -> tuple[list[str], list[str]]:
    blocking, warnings = [], []
    for track_index, track in enumerate(timeline.get("VideoTracks") or []):
        for clip_index, clip in enumerate(track.get("VideoTrackClips") or []):
            if not isinstance(clip, dict) or not clip.get("LoopMode"):
                continue
            path = f"VideoTracks[{track_index}].VideoTrackClips[{clip_index}]"
            values = {
                "In": clip.get("In", 0),
                "Out": clip.get("Out"),
                "TimelineIn": clip.get("TimelineIn", 0),
                "TimelineOut": clip.get("TimelineOut"),
            }
            invalid = [
                name for name, value in values.items()
                if isinstance(value, bool) or not isinstance(value, (int, float))
            ]
            if invalid:
                blocking.append(
                    f"{path} uses video LoopMode but cannot compare source and "
                    f"timeline spans; missing/non-numeric: {', '.join(invalid)}"
                )
                continue
            source_span = values["Out"] - values["In"]
            timeline_span = values["TimelineOut"] - values["TimelineIn"]
            if source_span <= 0 or timeline_span <= 0:
                blocking.append(
                    f"{path} uses video LoopMode with a non-positive source or "
                    "timeline span"
                )
            elif abs(source_span - timeline_span) > 0.05:
                if source_span > timeline_span:
                    fix = "set Out to In + the timeline span for the shorter narration"
                else:
                    fix = (
                        "video LoopMode will not extend the clip; use adjacent clips "
                        "or ArrayItems for the longer narration"
                    )
                blocking.append(
                    f"{path} uses unsupported video LoopMode with source span "
                    f"{source_span:.3f}s and timeline span {timeline_span:.3f}s; {fix}"
                )
            else:
                source_range = (
                    f"the first {source_span:.3f}s of the source"
                    if values["In"] == 0
                    else f"source range {values['In']:.3f}-{values['Out']:.3f}s"
                )
                warnings.append(
                    f"{path} uses redundant video LoopMode; source and timeline "
                    f"spans already match, so this render trims {source_range} "
                    "and does not loop it. Remove LoopMode"
                )
    return blocking, warnings


def expand_template(template: dict, clips_param: dict) -> dict:
    template = template.get("Template", template)
    config = template.get("Config", template)
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except json.JSONDecodeError as error:
            raise ValidationError(f"Invalid JSON in template Config: {error}") from error
    if not isinstance(config, dict):
        raise ValidationError("Template Config must be a JSON object")
    if not isinstance(clips_param, dict):
        raise ValidationError("ClipsParam must be a JSON object")
    return _expand_template(config, clips_param)


def confirm(action: str, details: list[str], assume_yes: bool) -> bool:
    print(f"\nAbout to {action}:")
    for detail in details:
        print(f"  - {detail}")
    if assume_yes or os.environ.get("VIDEO_EDITOR_SKIP_CONFIRMATION") == "1":
        print("  ⏩ --yes skips this script's stdin prompt only. It is not the user's")
        print("     approval of the Config and slot contract (SKILL.md §2.2, §7.0) —")
        print("     that has to be presented and agreed before this command runs.")
        return True
    if not sys.stdin.isatty():
        print("Non-interactive shell: pass --yes after user confirmation.")
        return False
    return input("Continue? [y/N]: ").strip().lower() in ("y", "yes")


def add_template(client, name: str, config: dict, region: str, call_api) -> dict:
    response = call_api(client, "AddTemplate", {
        "Type": "Timeline",
        "Name": name,
        "Config": json.dumps(config, ensure_ascii=False),
    }, region)
    template = response.get("Template") or {}
    if not template.get("TemplateId"):
        raise RuntimeError(f"AddTemplate returned no TemplateId: {response}")
    return template


def get_template(client, template_id: str, region: str, call_api) -> dict:
    response = call_api(client, "GetTemplate", {"TemplateId": template_id}, region)
    template = response.get("Template") or {}
    if not template:
        raise RuntimeError(f"GetTemplate returned no Template: {response}")
    return template


def submit_template_job(
    client,
    template_id: str,
    clips_param: dict,
    output_config: dict,
    region: str,
    client_token: Optional[str],
    call_api,
    generate_client_token,
) -> tuple[str, str]:
    token = client_token or generate_client_token()
    response = call_api(client, "SubmitMediaProducingJob", {
        "TemplateId": template_id,
        "ClipsParam": json.dumps(clips_param, ensure_ascii=False),
        "OutputMediaConfig": json.dumps(output_config, ensure_ascii=False),
        "ClientToken": token,
    }, region)
    job_id = response.get("JobId")
    if not job_id:
        raise RuntimeError(f"SubmitMediaProducingJob returned no JobId: {response}")
    return job_id, token


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate, create, inspect, and use ICE normal Timeline templates"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate a common Config preset")
    generate.add_argument("--preset", choices=PRESETS, required=True)
    generate.add_argument("--opening-media-id")
    generate.add_argument("--ending-media-id")
    generate.add_argument("--watermark-image-id")
    generate.add_argument("--output", "-o")

    create = subparsers.add_parser("create", help="Create a normal Timeline template")
    create.add_argument("--name", required=True)
    create.add_argument("--config", "-c", required=True, help="Config JSON file or string")
    create.add_argument("--region", "-r", required=True, choices=VALID_REGIONS)
    create.add_argument("--yes", "-y", action="store_true")

    inspect = subparsers.add_parser("get", help="Get template Config and ClipsParam")
    inspect.add_argument("--template-id", "-T", required=True)
    inspect.add_argument("--region", "-r", required=True, choices=VALID_REGIONS)
    inspect.add_argument("--output", "-o")

    expand = subparsers.add_parser("expand", help="Expand a template locally without submitting")
    expand.add_argument("--template", "-t", required=True, help="GetTemplate JSON or Config")
    expand.add_argument("--clips-param", "-p", required=True, help="JSON file or string")
    expand.add_argument("--output", "-o")

    submit = subparsers.add_parser("submit", help="Produce media from a template")
    submit.add_argument("--template-id", "-T", required=True)
    submit.add_argument("--clips-param", "-p", required=True, help="JSON file or string")
    submit.add_argument("--output-config", "-o", required=True, help="JSON file or string")
    submit.add_argument("--region", "-r", required=True, choices=VALID_REGIONS)
    submit.add_argument("--client-token")
    submit.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing OSS output object",
    )
    submit.add_argument("--yes", "-y", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        if args.command == "generate":
            config = build_preset(
                args.preset,
                args.opening_media_id,
                args.ending_media_id,
                args.watermark_image_id,
            )
            write_json(validate_template_config(config), args.output)
            return

        if args.command == "expand":
            template = load_json_input(args.template, "template")
            clips_param = load_json_input(args.clips_param, "clips-param")
            expanded = expand_template(template, clips_param)
            blocking, warnings = video_loop_warnings(expanded)
            write_json(expanded, args.output)
            for warning in warnings:
                print(f"Warning: {warning}", file=sys.stderr)
            if blocking:
                raise ValidationError("Blocking template issues:\n- " + "\n- ".join(blocking))
            return

        if args.region not in VALID_REGIONS:
            raise ValidationError(
                f"Invalid region '{args.region}'. Choose one of: {', '.join(VALID_REGIONS)}"
            )
        call_api, check_output_path_exists, create_client, generate_client_token = load_cloud_api()
        client = create_client(args.region)

        if args.command == "create":
            config = validate_template_config(load_json_input(args.config, "config"))
            if not confirm(
                "create a persistent ICE normal template",
                [f"name: {args.name}", f"region: {args.region}", "type: Timeline"],
                args.yes,
            ):
                print("Operation cancelled.")
                return
            template = add_template(client, args.name, config, args.region, call_api)
            write_json(template, None)
        elif args.command == "get":
            validate_template_id(args.template_id)
            write_json(
                get_template(client, args.template_id, args.region, call_api),
                args.output,
            )
        elif args.command == "submit":
            validate_template_id(args.template_id)
            clips_param = load_json_input(args.clips_param, "clips-param")
            if not isinstance(clips_param, dict):
                raise ValidationError("ClipsParam must be a JSON object")
            output_config = validate_output_config(
                load_json_input(args.output_config, "output-config")
            )
            template = get_template(client, args.template_id, args.region, call_api)
            expanded = expand_template(template, clips_param)
            blocking, warnings = video_loop_warnings(expanded)
            for warning in warnings:
                print(f"Warning: {warning}", file=sys.stderr)
            if blocking:
                raise ValidationError("Blocking template issues:\n- " + "\n- ".join(blocking))
            output_exists = check_output_path_exists(output_config["MediaURL"], args.region)
            require_explicit_overwrite(output_exists, args.overwrite)
            if not confirm(
                "submit a billable template producing job",
                [
                    f"template: {args.template_id}",
                    f"region: {args.region}",
                    f"output: {output_config['MediaURL']}",
                    f"overwrite existing output: {'yes' if output_exists else 'no'}",
                    "ClipsParam: " + json.dumps(clips_param, ensure_ascii=False),
                ],
                args.yes,
            ):
                print("Operation cancelled.")
                return
            job_id, token = submit_template_job(
                client,
                args.template_id,
                clips_param,
                output_config,
                args.region,
                args.client_token,
                call_api,
                generate_client_token,
            )
            print(json.dumps({"JobId": job_id, "ClientToken": token}, indent=2))
            print(
                "Check status with: "
                f"python scripts/video_editor.py status -j {job_id} -r {args.region} --wait"
            )
    except (ValidationError, OSError, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print(f"API error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
