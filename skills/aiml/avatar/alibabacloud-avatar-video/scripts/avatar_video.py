#!/usr/bin/env python3
"""灵眸：自动选择模板创建播报视频并轮询结果。

能力：
- 列出账号下已有播报模板
- 未指定 --template-id 时随机选择一个已有模板
- 自动读取模板 variables，并把文本填入可用的 text 变量（优先 text_content）
- 在 1.7.0+ SDK 下可列出公共模板，并在本地模板为空时复制最多 3 个公共模板
- 注意：复制公共模板成功 ≠ 一定可以立即直接生成视频；有些复制出来的是草稿模板，可能仍需人工补充有效片段/素材
"""
import argparse
import json
import os
import random
import sys
import time
import urllib.request
from typing import Optional

from input_validation import read_text_file_limited, resolve_under_cwd, validate_http_https_url


VENV_PYTHON = os.environ.get(
    "LINGMOU_VENV_PYTHON",
    "/data/xxx-workspace/.venv-alibabacloud-avatar-video/bin/python",
)


def create_client():
    try:
        from alibabacloud_lingmou20250527.client import Client
        from alibabacloud_tea_openapi import models as open_api_models
    except Exception as e:
        raise RuntimeError(
            "需要安装: pip install alibabacloud-lingmou20250527 alibabacloud-tea-openapi"
        ) from e

    config = open_api_models.Config(
        access_key_id=os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"],
        access_key_secret=os.environ["ALIBABA_CLOUD_ACCESS_KEY_SECRET"],
        endpoint=os.environ.get("LINGMOU_ENDPOINT", "lingmou.cn-beijing.aliyuncs.com"),
        region_id=os.environ.get("LINGMOU_REGION", "cn-beijing"),
        user_agent="AlibabaCloud-Agent-Skills/alibabacloud-avatar-video",
    )
    return Client(config)


def sdk_supports_public_templates(client) -> bool:
    return hasattr(client, "list_public_broadcast_scene_templates") and hasattr(client, "copy_broadcast_scene_from_template")


def list_templates(client):
    from alibabacloud_lingmou20250527 import models as lm

    resp = client.list_broadcast_templates(lm.ListBroadcastTemplatesRequest())
    return resp.body.data or []


def list_public_templates(client, size: int = 10):
    from alibabacloud_lingmou20250527 import models as lm

    if not sdk_supports_public_templates(client):
        return []
    req = lm.ListPublicBroadcastSceneTemplatesRequest(size=size)
    resp = client.list_public_broadcast_scene_templates(req)
    return resp.body.data or []


def copy_public_templates(client, public_templates, max_copy: int = 3):
    from alibabacloud_lingmou20250527 import models as lm

    copied = []
    for idx, t in enumerate(public_templates[:max_copy], start=1):
        req = lm.CopyBroadcastSceneFromTemplateRequest(
            name=f"OpenClaw copied template {idx}",
            ratio=getattr(t, "ratio", None) or "16:9",
            template_id=t.id,
        )
        resp = client.copy_broadcast_scene_from_template(req)
        copied.append(resp.body.data)
    return copied


def get_template_detail(client, template_id: str):
    from alibabacloud_lingmou20250527 import models as lm

    req = lm.GetBroadcastTemplateRequest()
    req.template_id = template_id
    resp = client.get_broadcast_template(req)
    return resp.body.data


def choose_template(client, explicit_template_id: Optional[str] = None, seed: Optional[int] = None, auto_copy_public: bool = True):
    templates = list_templates(client)
    if explicit_template_id:
        for t in templates:
            if t.id == explicit_template_id:
                return t, False
        class T:
            pass
        t = T()
        t.id = explicit_template_id
        t.name = explicit_template_id
        return t, False

    if templates:
        rng = random.Random(seed)
        return rng.choice(list(templates)), False

    if auto_copy_public and sdk_supports_public_templates(client):
        publics = list_public_templates(client, size=10)
        if publics:
            copied = copy_public_templates(client, publics, max_copy=3)
            if copied:
                rng = random.Random(seed)
                return rng.choice(list(copied)), True

    raise RuntimeError(
        "当前账号下没有可用播报模板；且未能获得可直接使用的公共模板副本。请先在灵眸中准备至少一个可直接生成的视频模板。"
    )


def build_variables(template_detail, text: str):
    from alibabacloud_lingmou20250527 import models as lm

    variables = getattr(template_detail, "variables", None) or []
    if not variables:
        return [
            lm.TemplateVariable(
                name="text_content",
                type="text",
                properties={"content": text},
            )
        ]

    text_vars = [v for v in variables if getattr(v, "type", None) == "text"]
    if not text_vars:
        raise RuntimeError("模板中没有可替换的 text 变量，暂时无法仅凭脚本生成口播视频")

    preferred_names = ["text_content", "test_text", "content", "text"]
    target = None
    for name in preferred_names:
        for v in text_vars:
            if getattr(v, "name", None) == name:
                target = v
                break
        if target:
            break
    if not target:
        target = text_vars[0]

    return [
        lm.TemplateVariable(
            name=target.name,
            type="text",
            properties={"content": text},
        )
    ]


def submit_video(client, template_id: str, text: str, name: str, resolution: str, fps: int, watermark: bool):
    from alibabacloud_lingmou20250527 import models as lm

    template_detail = get_template_detail(client, template_id)
    variables = build_variables(template_detail, text)
    req = lm.CreateBroadcastVideoFromTemplateRequest(
        template_id=template_id,
        name=name,
        variables=variables,
        video_options=lm.CreateBroadcastVideoFromTemplateRequestVideoOptions(
            resolution=resolution,
            fps=fps,
            watermark=watermark,
        ),
    )
    resp = client.create_broadcast_video_from_template(req)
    video_id = resp.body.data.id
    return video_id, template_detail, variables


def wait_video(client, video_id: str, interval: int = 3, max_wait: int = 1800):
    from alibabacloud_lingmou20250527 import models as lm

    start = time.time()
    while time.time() - start < max_wait:
        req = lm.ListBroadcastVideosByIdRequest(video_ids=[video_id])
        resp = client.list_broadcast_videos_by_id(req)
        data = resp.body.data or []
        if not data:
            time.sleep(interval)
            continue

        video = data[0]
        status = video.status
        print(f"status={status}")
        if status == "SUCCESS":
            return video.video_url
        if status in ("ERROR", "FAILED"):
            raise RuntimeError(f"LingMou task failed: {status}")

        time.sleep(interval)

    raise TimeoutError("LingMou polling timeout")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--template-id")
    p.add_argument("--list-templates", action="store_true", help="列出账号下已有模板")
    p.add_argument("--list-public-templates", action="store_true", help="列出公共模板（需 SDK 1.7.0+）")
    p.add_argument("--copy-public-templates", action="store_true", help="复制最多 3 个公共模板到当前账号（需 SDK 1.7.0+）")
    p.add_argument("--show-template-detail", action="store_true", help="输出所选模板详情")
    p.add_argument("--seed", type=int, default=None, help="随机模板选择种子，便于复现")
    p.add_argument("--text")
    p.add_argument("--text-file")
    p.add_argument("--name", default="OpenClaw Avatar Video")
    p.add_argument("--resolution", default="720p", choices=["720p", "1080p"])
    p.add_argument("--fps", type=int, default=30, choices=[15, 30])
    p.add_argument("--watermark", action="store_true", default=False)
    p.add_argument("--download", action="store_true")
    p.add_argument("--output", default="lingmou_output.mp4")
    args = p.parse_args()

    client = create_client()

    if args.list_templates:
        templates = list_templates(client)
        print(json.dumps([
            {"id": t.id, "name": getattr(t, "name", None)} for t in templates
        ], ensure_ascii=False, indent=2))

    if args.list_public_templates:
        publics = list_public_templates(client, size=10)
        print(json.dumps([
            {"id": t.id, "name": getattr(t, "name", None), "ratio": getattr(t, "ratio", None), "desc": getattr(t, "desc", None)} for t in publics
        ], ensure_ascii=False, indent=2))

    if args.copy_public_templates:
        publics = list_public_templates(client, size=10)
        copied = copy_public_templates(client, publics, max_copy=3)
        print(json.dumps([
            {"id": t.id, "name": getattr(t, "name", None), "ratio": getattr(t, "ratio", None), "status": getattr(t, "status", None)} for t in copied
        ], ensure_ascii=False, indent=2))
        if not (args.text or args.text_file or args.template_id or args.show_template_detail):
            return

    if (args.list_templates or args.list_public_templates) and not (args.text or args.text_file or args.template_id or args.show_template_detail or args.copy_public_templates):
        return

    chosen, copied_from_public = choose_template(client, args.template_id, seed=args.seed, auto_copy_public=True)
    print(f"template_id={chosen.id}")
    print(f"template_name={getattr(chosen, 'name', '')}")
    print(f"template_from_public_copy={str(copied_from_public).lower()}")

    if args.show_template_detail:
        detail = get_template_detail(client, chosen.id)
        print(json.dumps(detail.to_map(), ensure_ascii=False, indent=2, default=str))
        if not (args.text or args.text_file):
            return

    text = args.text
    if args.text_file:
        text = read_text_file_limited(args.text_file, field="--text-file")
    if not text:
        p.error("Need --text or --text-file")

    try:
        video_id, template_detail, variables = submit_video(
            client,
            template_id=chosen.id,
            text=text,
            name=args.name,
            resolution=args.resolution,
            fps=args.fps,
            watermark=args.watermark,
        )
    except Exception as e:
        if copied_from_public:
            raise RuntimeError(
                f"公共模板已复制，但直接生成失败：{e}。这通常表示复制出的模板仍是草稿或缺少有效片段/素材，需要先在灵眸侧完善模板。"
            )
        raise

    print(f"video_id={video_id}")
    print("variables=" + json.dumps([v.to_map() for v in variables], ensure_ascii=False))
    if args.show_template_detail:
        print("template_detail=" + json.dumps(template_detail.to_map(), ensure_ascii=False, default=str))

    video_url = wait_video(client, video_id)
    print(f"video_url={video_url}")

    if args.download and video_url:
        out_path = resolve_under_cwd(args.output, field="--output")
        safe_url = validate_http_https_url(video_url, field="video URL")
        with urllib.request.urlopen(safe_url, timeout=300) as response:
            with open(out_path, 'wb') as f:
                f.write(response.read())
        print(f"saved={out_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
