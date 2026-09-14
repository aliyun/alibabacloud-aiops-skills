#!/usr/bin/env python3
"""asset_attr_shelve.py — 资产属性完善 + 上架 CLI（Step 1/2/3 一站式）。

用法（先按 SKILL.md §3 导出环境变量）：

  # Step 1 查某类资产可用属性定义（只读）
  python3 asset_attr_shelve.py codes --asset-type TABLE [--writable-only] [--required-only]

  # 回读某些资产当前属性值（只读，覆盖写前务必留存原值）
  python3 asset_attr_shelve.py read --guid <GUID> [--guid <GUID2>] [--code shelve_description]

  # 上架前盘点：列出还没填的属性（拿着这份清单问用户“保持为空还是继续写”）
  python3 asset_attr_shelve.py read --guid <GUID> --only-empty

  # Step 2 覆盖写属性值（⚠ 写操作，需先 HITL 确认）
  #   默认先按属性定义本地 precheck、再回读留存原值，输出 previousValues 与
  #   rollbackCommands 便于回滚；--no-precheck 可跳过本地校验
  python3 asset_attr_shelve.py update --asset-type TABLE \\
      --guid <GUID> --set shelve_description="已治理，可对外" --set business_owner="数仓团队"

  # Step 3 提交上架（⚠ 写操作）。失败时输出缺失项清单，退出码 3
  python3 asset_attr_shelve.py shelve --guid <GUID> [--guid <GUID2>]

退出码：0 成功 / 1 部分或全部失败 / 2 参数、环境或本地 precheck 未通过 /
        3 上架因信息未完善被拒
"""
import argparse
import json
import shlex
import sys

from dataphin_asset_api import (ASSET_TYPES, ON_SHELVE_REQUIRED, AssetApiClient,
                                DataphinApiError, diff_written,
                                parse_missing_fields, precheck_attributes)


def out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def cmd_codes(client, args):
    items = client.get_attribute_codes(args.asset_type)
    if args.writable_only:
        items = [x for x in items if x.get("EditableIn")]
    if args.required_only:
        items = [x for x in items if x.get("Required")]
    out({"assetType": args.asset_type, "total": len(items), "attributes": [{
        "AttributeCode": x.get("AttributeCode"),
        "AttributeName": x.get("AttributeName"),
        "AttributeSource": x.get("AttributeSource"),
        "Required": x.get("Required"),
        "InputMode": x.get("InputMode"),
        "ValueType": x.get("ValueType"),
        "MaxLength": x.get("MaxLength"),
        "EditableIn": x.get("EditableIn"),
        "EnumSourceType": x.get("EnumSourceType"),
        "SystemReferenceType": x.get("SystemReferenceType"),
        "EnumValues": x.get("EnumValues"),
        "LinkTarget": x.get("LinkTarget"),
    } for x in items]})
    return 0


def cmd_read(client, args):
    data = client.get_attributes(args.guid, args.code or None)
    if not (args.only_empty or args.only_filled):
        out(data)
        return 0
    # 上架前盘点用：把已填/未填分开列出，避免人工比对漏项。
    # 未填清单是「上架前是否继续补属性」这个决策的输入，必须完整给用户看。
    result = {}
    for guid, attrs in data.items():
        empty = sorted(c for c, v in attrs.items() if not v)
        filled = {c: v for c, v in attrs.items() if v}
        item = {"writableTotal": len(attrs)}
        if args.only_empty:
            item["emptyCount"] = len(empty)
            item["emptyAttributes"] = empty
        if args.only_filled:
            item["filledCount"] = len(filled)
            item["filledAttributes"] = filled
        result[guid] = item
    out(result)
    return 0


def _rollback_command(asset_type, guid, previous):
    """拼出把该 GUID 属性还原成 previous 的命令，便于人工回滚。"""
    parts = ["python3 scripts/asset_attr_shelve.py update",
             "--asset-type " + asset_type, "--guid " + shlex.quote(guid)]
    for code, values in previous.items():
        parts.append("--set " + shlex.quote(code + "=" + "||".join(values)))
    return " ".join(parts)


def cmd_update(client, args):
    attrs = {}
    for pair in args.set:
        if "=" not in pair:
            sys.stderr.write("--set 需为 code=value 格式：%s\n" % pair)
            return 2
        code, value = pair.split("=", 1)
        # 空串表示清空（values=[]）；多值用 || 分隔
        attrs[code.strip()] = [] if value == "" else value.split("||")

    # 写前本地 precheck：写入是资产级原子的，一个非法值会让整条白写
    warnings = []
    if not args.no_precheck:
        violations, warnings = precheck_attributes(client, args.asset_type, attrs)
        if violations:
            out({"precheck": "FAILED", "violations": violations,
                 "warnings": warnings, "updateResult": None,
                 "hint": "未发起任何写入。修正后重试；确认要绕过本地校验可加 "
                         "--no-precheck。"})
            return 2

    # 覆盖写不可自动回滚：先回读原值另存，并给出回滚命令
    previous = client.get_attributes(args.guid, list(attrs.keys()))

    updates = [{"guid": g, "assetType": args.asset_type, "attributes": attrs}
               for g in args.guid]
    data = client.update_attributes(updates)

    # 写后回读校验：实测部分属性会「返回成功但值被静默丢弃」
    dropped = diff_written(client, args.guid, attrs)

    out({"precheck": "SKIPPED" if args.no_precheck else "PASSED",
         "warnings": warnings or None,
         "previousValues": previous,
         "rollbackCommands": [
             _rollback_command(args.asset_type, g, previous.get(g, {}))
             for g in args.guid],
         "updateResult": data, "silentlyDropped": dropped,
         "hint": ("部分属性写入返回成功但值未落库，常见于引用型属性（如 "
                  "shelve_directory_ids 需合法目录 ID）与清空无效的属性（如 "
                  "shelve_display_name / shelve_description）"
                  if dropped else None)})
    return 1 if (data.get("FailCount") or dropped) else 0


def cmd_shelve(client, args):
    """上架。失败为逐条失败且无副作用，故本命令同时充当上架预检。"""
    data = client.submit_on_shelve(args.guid)
    results, blocked = [], {}
    for r in data.get("ResultList") or []:
        guid, msg = r.get("Guid"), r.get("ErrorMessage")
        missing = parse_missing_fields(msg)
        results.append({"guid": guid, "success": r.get("Success"),
                        "errorCode": r.get("ErrorCode"), "errorMessage": msg,
                        "missingFields": missing})
        if missing:
            blocked[guid] = [{
                "field": f,
                # 未登记的缺失项没有已知属性编码，给 null 而不是魔法串
                "attributeCode": ON_SHELVE_REQUIRED.get(f),
                "fixableViaApi": bool(ON_SHELVE_REQUIRED.get(f)),
                "known": f in ON_SHELVE_REQUIRED,
            } for f in missing]

    payload = {"summary": {k: data.get(k) for k in
                           ("TotalCount", "SuccessCount", "FailCount")},
               "results": results}
    if blocked:
        payload["blockedByMissingInfo"] = blocked
        payload["nextAction"] = (
            "向用户逐项索要缺失信息。fixableViaApi=true 的项拿到值后用 update "
            "子命令写入再重试上架；fixableViaApi=false 的项（如可见范围）OpenAPI "
            "无对应属性编码，只能由用户到界面配置。用户若暂时提供不了，"
            "则本次仅保存已写入的属性、不上架，并提示其到界面补齐后再上架。")
        out(payload)
        return 3
    out(payload)
    return 1 if data.get("FailCount") else 0


def main():
    p = argparse.ArgumentParser(description="Dataphin 资产属性完善 + 上架")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("codes", help="查资产类型下可用属性定义（只读）")
    c.add_argument("--asset-type", required=True, choices=ASSET_TYPES)
    c.add_argument("--writable-only", action="store_true", help="仅 EditableIn 非空")
    c.add_argument("--required-only", action="store_true", help="仅 Required=true")
    c.set_defaults(func=cmd_codes)

    r = sub.add_parser("read", help="回读资产当前属性值（只读）")
    r.add_argument("--guid", action="append", required=True)
    r.add_argument("--code", action="append", help="限定属性编码，可多次")
    r.add_argument("--only-empty", action="store_true",
                   help="只列未填（空值）属性编码 —— 上架前盘点用")
    r.add_argument("--only-filled", action="store_true",
                   help="只列已填属性及其值（可与 --only-empty 同时给）")
    r.set_defaults(func=cmd_read)

    u = sub.add_parser("update", help="覆盖写属性值（写操作）")
    u.add_argument("--asset-type", required=True, choices=ASSET_TYPES)
    u.add_argument("--guid", action="append", required=True)
    u.add_argument("--set", action="append", required=True,
                   help="code=value；空串清空；多值用 || 分隔")
    u.add_argument("--no-precheck", action="store_true",
                   help="跳过写前的属性定义本地校验（不推荐）")
    u.set_defaults(func=cmd_update)

    s = sub.add_parser("shelve", help="提交上架（写操作，兼作上架预检）")
    s.add_argument("--guid", action="append", required=True)
    s.set_defaults(func=cmd_shelve)

    args = p.parse_args()
    try:
        client = AssetApiClient()
        return args.func(client, args)
    except DataphinApiError as e:
        sys.stderr.write("错误：%s\n" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
