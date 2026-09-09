#!/usr/bin/env python3
"""从 MCP 服务导出工具与参数的原始 description，写入 references/tool-reference.md 的标记块。

为什么要有这个脚本：人工转录必然丢信息。GetTask 的原始描述里写着
`nextAction: CallGetTask`，手写摘要时若漏掉这一句，就会出现一张不完整的
状态表，诱导出黑名单判终态，导致静默读到 null。源头信息是完整的，损失
百分之百发生在转录这一层。因此工具描述由本脚本按字节导出，不接受手工编辑。

唯一的归一化：把描述里 `aliyun <service> <PascalCaseAction>` 形式的命令动作名
转成插件模式 kebab-case（平台规范 SA-2.11 要求），描述其余文字逐字不动。

用法:
    python3 scripts/gen_tool_reference.py            # 生成并写入 references/tool-reference.md
    python3 scripts/gen_tool_reference.py --check    # 只比对, 有差异则退出 1
    python3 scripts/gen_tool_reference.py --stdout   # 只打印, 不写文件
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mcpx

BEGIN = "<!-- BEGIN GENERATED TOOL REFERENCE -->"
END = "<!-- END GENERATED TOOL REFERENCE -->"

HEADER = """\
> **This section is exported from the MCP service by `scripts/gen_tool_reference.py`. Do not edit it by hand.**
> The content is the tools' and parameters' **original descriptions, verbatim**. Re-run the generator to sync after a server-side update.
>
> Do not rewrite this into a summary: summaries lose information, and what gets lost is often exactly the value needed to decide a branch.
> Keeping the original text verbatim removes that class of loss — the quality of the guidance is then attributable to the MCP descriptions themselves, with no compression layer in between.
>
> Empirical findings **not covered** by the official descriptions are listed in SKILL.md."""

# 目标文件：从 SKILL.md 移到 references/tool-reference.md，以满足 SKILL.md 正文行数上限。
TARGET_RELPATH = os.path.join("references", "tool-reference.md")

# SA-2.11：aliyun CLI 动作名必须用插件模式（kebab-case），不允许 PascalCase。
# MCP 原文描述里偶有 PascalCase 形式的示例命令，导出时统一把动作名规范成
# kebab-case；命令的参数与描述其余文字逐字不动。
_CLI_PASCAL = re.compile(r"\baliyun (\S+) ([A-Z][A-Za-z0-9]+)")


def _kebab(action):
    return re.sub(r"(?<!^)(?=[A-Z])", "-", action).lower()


def normalize_cli(text):
    """把 `aliyun <svc> <PascalCaseAction>` 的动作名转 kebab-case。"""
    return _CLI_PASCAL.sub(lambda m: "aliyun %s %s" % (m.group(1), _kebab(m.group(2))),
                           str(text))


def fetch_tools(timeout=180.0):
    with mcpx.McpSession(timeout=timeout) as session:
        session.initialize()
        return session.list_tools()


def render_param(name, spec, required):
    lines = []
    mark = " **(required)**" if name in required else ""
    type_repr = spec.get("type")
    if type_repr is None:
        for key in ("anyOf", "oneOf", "$ref"):
            if key in spec:
                # sort_keys: 服务端返回的 JSON 键顺序在多次请求间会抖动, 不排序会
                # 让生成结果不稳定, --check 就会永远误报不一致。
                # 这只归一化「类型信息」的呈现, description 原文逐字不动。
                type_repr = json.dumps(spec[key], ensure_ascii=False,
                                       sort_keys=True)
                break
    extras = []
    for key in ("enum", "maximum", "minimum", "default", "defaultValue"):
        if key in spec and spec[key] is not None:
            extras.append("%s=%s" % (key, json.dumps(spec[key],
                                                     ensure_ascii=False,
                                                     sort_keys=True)))
    suffix = (", " + ", ".join(extras)) if extras else ""
    lines.append("- **`%s`**%s — `%s`%s" % (name, mark, type_repr or "?", suffix))
    desc = spec.get("description")
    if desc:
        for para in normalize_cli(desc).split("\n"):
            lines.append("  " + para if para.strip() else "")
    return lines


def render(tools):
    out = [HEADER, ""]
    out.append("%d tools. You can use the short name; the script auto-prepends the `%s` prefix."
               % (len(tools), mcpx.TOOL_PREFIX))
    out.append("")
    for tool in tools:
        full = tool["name"]
        out.append("### %s" % mcpx.short_name(full))
        out.append("")
        out.append("Full name: `%s`" % full)
        out.append("")
        out.append("**Original description:**")
        out.append("")
        for para in normalize_cli(tool.get("description") or "").split("\n"):
            out.append(para)
        out.append("")
        schema = tool.get("inputSchema") or {}
        props = schema.get("properties") or {}
        required = set(schema.get("required") or [])
        if not props:
            out.append("**Parameters:** none")
            out.append("")
            continue
        out.append("**Parameters (descriptions verbatim):**")
        out.append("")
        for name in sorted(props, key=lambda n: (n not in required, n)):
            out.extend(render_param(name, props[name] or {}, required))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def splice(text, block):
    if BEGIN not in text or END not in text:
        raise SystemExit(
            "%s 里找不到标记 %s / %s，无法定位生成块" % (TARGET_RELPATH, BEGIN, END))
    head, rest = text.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    return "%s%s\n%s\n%s%s" % (head, BEGIN, block.rstrip(), END, tail)


def main(argv):
    check = "--check" in argv
    to_stdout = "--stdout" in argv
    target_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), TARGET_RELPATH)

    tools = fetch_tools()
    if not tools:
        raise SystemExit("未取到任何工具，中止")
    block = render(tools)

    if to_stdout:
        sys.stdout.write(block)
        return 0

    current = open(target_path, encoding="utf-8").read()
    updated = splice(current, block)

    if check:
        if updated == current:
            print("✓ %s 的工具描述与服务端一致" % TARGET_RELPATH)
            return 0
        print("✗ %s 的工具描述与服务端不一致，重跑生成器同步" % TARGET_RELPATH)
        return 1

    if updated == current:
        print("工具描述无变化，%s 未改动" % TARGET_RELPATH)
        return 0
    with open(target_path, "w", encoding="utf-8") as handle:
        handle.write(updated)
    print("已写入 %d 个工具的原始描述到 %s" % (len(tools), TARGET_RELPATH))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
