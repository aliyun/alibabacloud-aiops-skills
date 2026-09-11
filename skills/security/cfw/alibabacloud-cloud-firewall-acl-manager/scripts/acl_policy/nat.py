"""NAT boundary ACL policy backup plugin"""
import json
from .base import AclPolicyPlugin


# Action value mapping
ACL_ACTION_MAP = {
    "accept": "放行",
    "drop": "拦截",
    "log": "观察",
}

# Action value reverse mapping
ACL_ACTION_REVERSE_MAP = {
    "放行": "accept",
    "拦截": "drop",
    "观察": "log",
}


def _parse_source_cidrs(item):
    """Parse the CIDR list expanded from the source address book"""
    cidrs = item.get("SourceGroupCidrs", [])
    return "\n".join(cidrs) if cidrs else ""


def _parse_dest_cidrs(item):
    """Parse the CIDR list expanded from the destination address book"""
    cidrs = item.get("DestinationGroupCidrs", [])
    return "\n".join(cidrs) if cidrs else ""


def _parse_dest_ports(item):
    """Parse the port list expanded from the port address book"""
    ports = item.get("DestPortGroupPorts", [])
    return "\n".join(ports) if ports else ""


def _parse_address_notes(notes_list):
    """Parse the address/port detail list with notes"""
    if not notes_list:
        return ""
    parts = []
    for item in notes_list:
        addr = item.get("Address", "")
        note = item.get("Note", "")
        if note:
            parts.append(f"{addr} ({note})")
        else:
            parts.append(addr)
    return "\n".join(parts)


def _format_timestamp(ts):
    """Convert a timestamp to a human-readable format"""
    if not ts:
        return ""
    from datetime import datetime, timezone, timedelta
    try:
        dt = datetime.fromtimestamp(int(ts), tz=timezone(timedelta(hours=8)))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)


class NatAclPlugin(AclPolicyPlugin):
    """NAT boundary ACL policy"""

    name = "NAT边界"
    order = 2
    sheet_name = "NAT边界墙ACL"
    api_action = "DescribeNatFirewallControlPolicy"
    result_key = "Policys"
    group_types = []  # GroupType is not used for ACL policies

    columns = [
        # --- Core configuration fields (required when creating policies) ---
        ("NAT网关ID",       lambda item: item.get("NatGatewayId", "")),
        ("优先级",          lambda item: item.get("Order", "")),
        ("访问源",          lambda item: item.get("Source", "")),
        ("源地址类型",      lambda item: item.get("SourceType", "")),
        ("源地址簿类型",    lambda item: item.get("SourceGroupType", "")),
        ("目的",            lambda item: item.get("Destination", "")),
        ("目的地址类型",    lambda item: item.get("DestinationType", "")),
        ("目的地址簿类型",  lambda item: item.get("DestinationGroupType", "")),
        ("网络传输协议",    lambda item: item.get("Proto", "")),
        ("应用",            lambda item: ", ".join(item.get("ApplicationNameList", []))),
        ("目的端口",        lambda item: item.get("DestPort", "")),
        ("端口类型",        lambda item: item.get("DestPortType", "")),
        ("端口地址簿",      lambda item: item.get("DestPortGroup", "")),
        ("动作",            lambda item: ACL_ACTION_MAP.get(item.get("AclAction", ""), item.get("AclAction", ""))),
        ("策略有效期",      lambda item: item.get("RepeatType", "")),
        ("重复周期",        lambda item: ", ".join(str(d) for d in item.get("RepeatDays", [])) if item.get("RepeatDays") else ""),
        ("重复开始时间",    lambda item: item.get("RepeatStartTime", "")),
        ("重复结束时间",    lambda item: item.get("RepeatEndTime", "")),
        ("启用状态",        lambda item: item.get("Release", "")),
        ("描述",            lambda item: item.get("Description", "")),
        ("生效日期开始",    lambda item: _format_timestamp(item.get("StartTime", 0))),
        ("生效日期结束",    lambda item: _format_timestamp(item.get("EndTime", 0))),
        ("域名解析类型",    lambda item: item.get("DomainResolveType", "")),
        ("展开数量",        lambda item: item.get("SpreadCnt", "")),
    ]

    col_widths = [28, 8, 30, 12, 15, 30, 12, 15, 15, 15, 15, 10, 20, 10, 12, 15, 15, 15, 10, 30, 20, 20, 15, 10]

    def custom_fetch(self, ak, sk, endpoint, call_api_fn, page_size=50, security_token=None):
        """
        NAT boundary ACL backup flow:
        1. Query all NAT firewall instances first (DescribeNatFirewallList)
        2. For each instance, query ACL policies (DescribeNatFirewallControlPolicy)
           Note: Direction only supports "out"
        """
        all_items = []

        # Step 1: get all NAT firewall instances
        nat_list_data = call_api_fn(ak, sk, endpoint, "DescribeNatFirewallList", {
            "CurrentPage": "1",
            "PageSize": str(page_size),
            "Lang": "zh",
        }, security_token)

        if not nat_list_data:
            print(f"  [{self.name}] failed to query the NAT firewall instance list")
            return all_items

        nat_items = nat_list_data.get("NatFirewallList", [])
        nat_count = len(nat_items)
        print(f"  [{self.name}] found {nat_count} NAT firewall instance(s)")

        # Step 2: query ACL policies for each NAT firewall
        for nat in nat_items:
            nat_gw_id = nat.get("NatGatewayId", "")
            if not nat_gw_id:
                continue

            # Direction for NAT firewall only supports "out"
            page = 1
            while True:
                params = {
                    "CurrentPage": str(page),
                    "PageSize": str(page_size),
                    "Direction": "out",
                    "NatGatewayId": nat_gw_id,
                    "Lang": "zh",
                }
                data = call_api_fn(ak, sk, endpoint, self.api_action, params, security_token)
                if not data:
                    break

                items = data.get("Policys", [])
                if not items:
                    total = int(data.get("TotalCount", 0))
                    print(f"  [{self.name}] NAT gateway={nat_gw_id}, direction=out, {total} policies in total")
                    break

                all_items.extend(items)
                total = int(data.get("TotalCount", 0))
                print(f"  [{self.name}] NAT gateway={nat_gw_id}, direction=out, page {page}, {len(items)} rows on this page, accumulated {len(all_items)}/{total}")

                if len(all_items) >= total:
                    break
                page += 1

        return all_items

    # ==================== Restore configuration ====================
    restore_api = "CreateNatFirewallControlPolicy"
    name_column = "描述"
    uid_column = "AclUuid"

    def restore(self, ak, sk, region, call_api_fn, excel_file, security_token=None,
                nat_target_gateways=None):
        """NAT boundary ACL policy restore (overrides the base class to handle NAT gateway ID and fixed Direction)

        nat_target_gateways: optional, list of target NAT gateway IDs explicitly specified by the
        user (append mode). When specified, it takes priority: regardless of whether the gateways
        in the backup exist in this account, all policies' resource IDs are rewritten to the
        specified targets and restored in a broadcast manner (covering both gateway-swap-in-same-
        account and cross-account scenarios). When not specified and the backup gateways are
        missing in this account, an interactive selection is shown or a hint to use the parameter.
        """
        import pandas as pd
        import sys as _sys
        from datetime import datetime, timezone, timedelta

        endpoint = f"cloudfw.{region}.aliyuncs.com"

        # Skip if the sheet does not exist (no sheet is generated for boundaries without data at backup time)
        if self.sheet_name not in pd.ExcelFile(excel_file).sheet_names:
            print(f"  [{self.name}] no sheet '{self.sheet_name}' in the backup file, skipped (no data at backup time)")
            return (0, 0, 0, 0)

        df = pd.read_excel(excel_file, sheet_name=self.sheet_name)
        print(f"  [{self.name}] loaded {len(df)} records")

        if '恢复状态' not in df.columns:
            df['恢复状态'] = '待恢复'
        else:
            df['恢复状态'] = df['恢复状态'].astype(str).replace('nan', '待恢复')

        success_count = 0
        fail_count = 0
        skip_count = 0
        exist_count = 0

        # ===== Target NAT gateway selection (gateway-swap-in-same-account/cross-account restore support, multi-select broadcast) =====
        def _available_gateways():
            """Query NAT gateways visible to Cloud Firewall in this account (DescribeNatFirewallList, same source as the backup, paginated)

            Note: the pagination parameter of this API is PageNo (not CurrentPage), and the result
            key is NatFirewallList; historically, mistakenly using DescribeSecurityProxy +
            CurrentPage + SecurityProxyList always returned an empty list and led to the false
            conclusion that "no available NAT gateway exists in this account".
            """
            gws, page = set(), 1
            while True:
                data = call_api_fn(ak, sk, endpoint, "DescribeNatFirewallList", {
                    "PageNo": str(page), "PageSize": "50", "Lang": "zh"}, security_token)
                batch = (data or {}).get("NatFirewallList", [])
                for it in batch:
                    gw = it.get("NatGatewayId")
                    if gw:
                        gws.add(gw)
                total = int((data or {}).get("TotalCount", 0) or 0)
                if not batch or page * 50 >= total:
                    break
                page += 1
            return sorted(gws)

        source_gws = sorted({str(g) for g in df["NAT网关ID"].astype(str).unique()
                             if g and g != "nan"})
        available_gws = _available_gateways()
        missing_gws = [g for g in source_gws if g not in available_gws]
        remap_gws = None
        if nat_target_gateways:
            # User explicitly specified target gateways: takes priority, rewrite resource IDs and broadcast-restore (gateway-swap-in-same-account/cross-account)
            invalid = [g for g in nat_target_gateways if g not in available_gws]
            if invalid:
                print(f"  [{self.name}] [FAIL] specified gateways do not exist: {', '.join(invalid)}; "
                      f"available gateways: {', '.join(available_gws) if available_gws else '(no available NAT gateway in this account)'}")
                return (0, len(df[df["恢复状态"] != "成功"]), 0, 0)
            remap_gws = list(nat_target_gateways)
            print(f"  [{self.name}] [INFO] rewriting gateway IDs to the specified targets: backup gateways [{', '.join(source_gws)}] -> target gateways [{', '.join(remap_gws)}]")
        elif missing_gws:
            print(f"  [{self.name}] [WARN] {len(missing_gws)} NAT gateway(s) in the backup do not exist in this account: {', '.join(missing_gws)}")
            if not available_gws:
                print(f"  [{self.name}] no available NAT gateway in this account (Cloud Firewall view). "
                      f"Please create a NAT gateway first and retry; this boundary is skipped for now.")
                df["恢复状态"] = ["失败" if s != "成功" else s for s in df["恢复状态"]]
                fail_count = int((df["恢复状态"] == "失败").sum())
                import openpyxl
                wb = openpyxl.load_workbook(excel_file)
                ws = wb[self.sheet_name]
                header_row = [cell.value for cell in ws[1]]
                if "恢复状态" in header_row:
                    col = header_row.index("恢复状态") + 1
                    for i, v in enumerate(df["恢复状态"]):
                        ws.cell(row=i + 2, column=col, value=v)
                    wb.save(excel_file)
                print(f"  [{self.name}] restore completed: success 0, failed {fail_count}, skipped 0, already existing 0")
                return (0, fail_count, 0, 0)
            if _sys.stdin.isatty():
                print(f"  Available NAT gateways in this account (multiple allowed, comma-separated indices):")
                for i, g in enumerate(available_gws, 1):
                    print(f"    [{i}] {g}")
                while True:
                    sel = input("  Please select the NAT gateway(s) to restore to: ").strip()
                    try:
                        picked = [available_gws[int(t) - 1] for t in sel.split(",") if t.strip()]
                        if picked:
                            remap_gws = picked
                            break
                    except (ValueError, IndexError):
                        pass
                    print("  Invalid input, please select again")
            else:
                print(f"  [{self.name}] [FAIL] in a non-interactive environment, use --nat-target-gateways ngw-xxx[,ngw-yyy] "
                      f"to specify the target gateways (multiple allowed; policies will be broadcast-restored to each gateway); "
                      f"available gateways: {', '.join(available_gws)}")
                return (0, len(df[df["恢复状态"] != "成功"]), 0, 0)
            print(f"  [{self.name}] all policies will be restored to target gateways: {', '.join(remap_gws)}")
        else:
            # No targets specified and all backup gateways exist in this account: keep the gateway IDs from the backup (same-resource append scenario)
            print(f"  [{self.name}] [INFO] no target gateway specified, using the gateways from the backup: {', '.join(source_gws)}"
                  f"(to restore to other gateways, specify them with --nat-target-gateways; "
                  f"to restore the existing configuration of the same gateway, use --mode diff instead)")

        # Iterate in ascending order (NewOrder=-1 inserts at the end, so ascending order keeps the sequence consistent)
        for idx in range(len(df)):
            row = df.iloc[idx]
            record_name = str(row.get("描述", f"record{idx+1}"))
            nat_gw_id = str(row.get("NAT网关ID", ""))
            targets = remap_gws if remap_gws else [nat_gw_id]

            # Skip if already restored successfully
            current_status = df.at[df.index[idx], '恢复状态']
            if current_status == '成功':
                skip_count += 1
                continue

            # ===== Build API parameters =====
            api_params = {}

            # NatGatewayId
            api_params["NatGatewayId"] = nat_gw_id

            # Direction: NAT is fixed to out
            api_params["Direction"] = "out"

            # AclAction: accept=accept, log=observe, drop=reject
            action_str = str(row.get("动作", ""))
            acl_action = ACL_ACTION_REVERSE_MAP.get(action_str, action_str)
            api_params["AclAction"] = acl_action

            # Source / SourceType
            api_params["Source"] = str(row.get("访问源", ""))
            api_params["SourceType"] = str(row.get("源地址类型", ""))

            # Destination / DestinationType
            api_params["Destination"] = str(row.get("目的", ""))
            api_params["DestinationType"] = str(row.get("目的地址类型", ""))

            # Proto
            api_params["Proto"] = str(row.get("网络传输协议", ""))

            # ApplicationNameList: flattened format, required (including ANY)
            app_str = str(row.get("应用", ""))
            if app_str and app_str != "nan":
                apps = [a.strip() for a in app_str.split(",") if a.strip()]
                for i, app in enumerate(apps, 1):
                    api_params[f"ApplicationNameList.{i}"] = app

            # DestPortType
            dest_port_type = str(row.get("端口类型", ""))
            api_params["DestPortType"] = dest_port_type

            # DestPort / DestPortGroup
            if dest_port_type == "group":
                dest_port_group = str(row.get("端口地址簿", ""))
                if dest_port_group and dest_port_group != "nan":
                    api_params["DestPortGroup"] = dest_port_group
                api_params["DestPort"] = ""
            else:
                dest_port = str(row.get("目的端口", ""))
                api_params["DestPort"] = dest_port if dest_port != "nan" else ""

            # NewOrder: insert at the end by default
            api_params["NewOrder"] = "-1"

            # Release: enable status
            release_str = str(row.get("启用状态", ""))
            if release_str == "True" or release_str == "true":
                api_params["Release"] = "true"
            elif release_str == "False" or release_str == "false":
                api_params["Release"] = "false"
            else:
                api_params["Release"] = "true"

            # Description (required)
            description = str(row.get("描述", ""))
            api_params["Description"] = description if description != "nan" else ""

            # RepeatType
            repeat_type = str(row.get("策略有效期", ""))
            if repeat_type and repeat_type != "nan":
                api_params["RepeatType"] = repeat_type

                # Pass time parameters when not Permanent
                if repeat_type != "Permanent":
                    start_time_str = str(row.get("生效日期开始", ""))
                    end_time_str = str(row.get("生效日期结束", ""))

                    if start_time_str and start_time_str != "nan":
                        try:
                            dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                            dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
                            api_params["StartTime"] = str(int(dt.timestamp()))
                        except:
                            pass

                    if end_time_str and end_time_str != "nan":
                        try:
                            dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
                            dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
                            api_params["EndTime"] = str(int(dt.timestamp()))
                        except:
                            pass

                    repeat_start = str(row.get("重复开始时间", ""))
                    repeat_end = str(row.get("重复结束时间", ""))
                    if repeat_start and repeat_start != "nan":
                        api_params["RepeatStartTime"] = repeat_start
                    if repeat_end and repeat_end != "nan":
                        api_params["RepeatEndTime"] = repeat_end

                    # RepeatDays (Weekly/Monthly types)
                    repeat_days_str = str(row.get("重复周期", ""))
                    if repeat_days_str and repeat_days_str != "nan":
                        days = [d.strip() for d in repeat_days_str.split(",") if d.strip()]
                        for i, day in enumerate(days, 1):
                            api_params[f"RepeatDays.{i}"] = day
            else:
                # When the policy validity period is empty but effective dates exist, pass RepeatType=None (one-off time range)
                start_time_str = str(row.get("生效日期开始", ""))
                end_time_str = str(row.get("生效日期结束", ""))
                if (start_time_str and start_time_str != "nan") or (end_time_str and end_time_str != "nan"):
                    api_params["RepeatType"] = "None"
                    if start_time_str and start_time_str != "nan":
                        try:
                            dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                            dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
                            api_params["StartTime"] = str(int(dt.timestamp()))
                        except:
                            pass
                    if end_time_str and end_time_str != "nan":
                        try:
                            dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
                            dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
                            api_params["EndTime"] = str(int(dt.timestamp()))
                        except:
                            pass

            # DomainResolveType: pass it when the destination address type is domain
            dest_type = str(row.get("目的地址类型", ""))
            if dest_type == "domain":
                domain_resolve_type = str(row.get("域名解析类型", ""))
                if domain_resolve_type and domain_resolve_type != "nan" and domain_resolve_type != "0":
                    api_params["DomainResolveType"] = domain_resolve_type

            print(f"  [{self.name}] [{idx+1}] restoring: {record_name} (target gateways: {', '.join(targets)})")
            print(f"    action: {acl_action}, proto: {api_params['Proto']}, source: {api_params['Source']}")

            ok_t, exists_t, fail_t = 0, 0, 0
            fail_msgs = []
            for gw in targets:
                params = dict(api_params)
                params["NatGatewayId"] = gw
                try:
                    result = call_api_fn(ak, sk, endpoint, self.restore_api, params, security_token)

                    if self.uid_column in result and result[self.uid_column]:
                        print(f"    [OK] {gw} success, {self.uid_column}: {result[self.uid_column]}")
                        ok_t += 1
                    else:
                        code = result.get("Code", "")
                        message = result.get("Message", "")
                        if "already exists" in message.lower() or "Duplicates" in code:
                            print(f"    [WARN] {gw} already exists")
                            exists_t += 1
                        else:
                            print(f"    [FAIL] {gw} failed: {code} - {message}")
                            fail_t += 1
                            fail_msgs.append(f"{gw}:{code}")

                except Exception as e:
                    error_str = str(e)
                    if "already exist" in error_str.lower() or "Duplicates" in error_str:
                        print(f"    [WARN] {gw} already exists")
                        exists_t += 1
                    else:
                        print(f"    [FAIL] {gw} exception: {error_str[:200]}")
                        fail_t += 1
                        fail_msgs.append(f"{gw}:{error_str[:50]}")

            total_t = len(targets)
            if fail_t == 0 and ok_t + exists_t == total_t:
                df.at[df.index[idx], '恢复状态'] = '成功'
                success_count += 1
            elif ok_t + exists_t == 0:
                df.at[df.index[idx], '恢复状态'] = '失败'
                fail_count += 1
            else:
                df.at[df.index[idx], '恢复状态'] = f"部分成功({ok_t+exists_t}/{total_t}，失败:{';'.join(fail_msgs)})"
                fail_count += 1

        # Update the restore status in Excel
        import openpyxl
        wb = openpyxl.load_workbook(excel_file)
        ws = wb[self.sheet_name]
        header_row = [cell.value for cell in ws[1]]
        if '恢复状态' in header_row:
            status_col_idx = header_row.index('恢复状态') + 1
        else:
            status_col_idx = ws.max_column + 1
            ws.cell(row=1, column=status_col_idx, value='恢复状态')

        for i, (_, row) in enumerate(df.iterrows()):
            ws.cell(row=i + 2, column=status_col_idx, value=row.get('恢复状态', '待恢复'))

        wb.save(excel_file)

        print(f"  [{self.name}] restore completed: success {success_count}, failed {fail_count}, skipped {skip_count}, already existing {exist_count}")
        return (success_count, fail_count, skip_count, exist_count)
