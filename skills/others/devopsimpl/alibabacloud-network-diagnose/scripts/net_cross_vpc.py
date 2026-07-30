"""Implementation detail."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from net_common import _call_with_retry, cidr_contains, cidr_prefix_len




def describe_vpc_peer_connections(vpc_id: str = None, region: str = None) -> dict:
    """Implementation detail."""
    params = {"MaxResults": "50"}
    if vpc_id:
        params["VpcId.1"] = vpc_id

    result = _call_with_retry("vpcpeer", "list-vpc-peer-connections", params, region)
    if "error" in result:

        return result

    connections = result.get("VpcPeerConnects", [])

    summary = []
    for conn in connections:
        vpc_info = conn.get("Vpc", {})
        accepting_vpc = conn.get("AcceptingVpc", {})
        summary.append({
            "InstanceId": conn.get("InstanceId", ""),
            "Name": conn.get("Name", ""),
            "Status": conn.get("Status", ""),
            "RequesterVpcId": vpc_info.get("VpcId", ""),
            "RequesterRegionId": vpc_info.get("RegionId", ""),
            "RequesterCidr": vpc_info.get("Ipv4Cidrs", []),
            "AcceptingVpcId": accepting_vpc.get("VpcId", ""),
            "AcceptingRegionId": accepting_vpc.get("RegionId", ""),
            "AcceptingCidr": accepting_vpc.get("Ipv4Cidrs", []),
            "BandwidthPackageId": conn.get("Bandwidth", 0),
        })

    return {"peering_connections": summary, "total": len(summary)}


def check_peering_for_vpcs(src_vpc_id: str, dst_vpc_id: str,
                            region: str = None) -> dict:
    """Implementation detail."""

    result = describe_vpc_peer_connections(vpc_id=src_vpc_id, region=region)
    if "error" in result:
        return result

    for conn in result.get("peering_connections", []):
        if (conn["RequesterVpcId"] == src_vpc_id and conn["AcceptingVpcId"] == dst_vpc_id) or \
           (conn["RequesterVpcId"] == dst_vpc_id and conn["AcceptingVpcId"] == src_vpc_id):
            status = conn["Status"]
            return {
                "found": True,
                "connection": conn,
                "is_active": status == "Activated",
                "status": status,
                "details": f"对等连接 {conn['InstanceId']} 状态: {status}",
            }


    result2 = describe_vpc_peer_connections(vpc_id=dst_vpc_id, region=region)
    if "error" not in result2:
        for conn in result2.get("peering_connections", []):
            if (conn["RequesterVpcId"] == src_vpc_id and conn["AcceptingVpcId"] == dst_vpc_id) or \
               (conn["RequesterVpcId"] == dst_vpc_id and conn["AcceptingVpcId"] == src_vpc_id):
                status = conn["Status"]
                return {
                    "found": True,
                    "connection": conn,
                    "is_active": status == "Activated",
                    "status": status,
                    "details": f"对等连接 {conn['InstanceId']} 状态: {status}",
                }

    return {
        "found": False,
        "connection": None,
        "is_active": False,
        "status": "NotFound",
        "details": f"VPC {src_vpc_id} 和 {dst_vpc_id} 之间未找到对等连接",
    }




def describe_cens(region: str = None) -> dict:
    """Implementation detail."""
    params = {"PageSize": "50"}

    all_cens = []
    page_number = 1

    while True:
        params["PageNumber"] = str(page_number)
        result = _call_with_retry("cbn", "describe-cens", params, region)
        if "error" in result:
            return result

        cens = result.get("Cens", {}).get("Cen", [])
        all_cens.extend(cens)

        total_count = result.get("TotalCount", 0)
        if len(all_cens) >= total_count or not cens:
            break
        page_number += 1

    summary = []
    for cen in all_cens:
        summary.append({
            "CenId": cen.get("CenId"),
            "Name": cen.get("Name", ""),
            "Status": cen.get("Status", ""),
            "Description": cen.get("Description", ""),
            "ProtectionLevel": cen.get("ProtectionLevel", ""),
        })

    return {"cens": summary, "total": len(summary)}


def describe_cen_attached_child_instances(cen_id: str, region: str = None) -> dict:
    """Implementation detail."""
    params = {
        "CenId": cen_id,
        "PageSize": "50",
    }

    result = _call_with_retry("cbn", "describe-cen-attached-child-instances", params, region)
    if "error" in result:
        return result

    instances = result.get("ChildInstances", {}).get("ChildInstance", [])

    summary = []
    for inst in instances:
        summary.append({
            "ChildInstanceId": inst.get("ChildInstanceId"),
            "ChildInstanceType": inst.get("ChildInstanceType", ""),  # VPC / VBR / CCN
            "ChildInstanceRegionId": inst.get("ChildInstanceRegionId", ""),
            "ChildInstanceOwnerId": inst.get("ChildInstanceOwnerId", ""),
            "Status": inst.get("Status", ""),
            "CenId": cen_id,
        })

    return {"child_instances": summary, "total": len(summary), "cen_id": cen_id}


def describe_cen_route_entries(cen_id: str, child_instance_id: str,
                                child_instance_type: str = "VPC",
                                child_instance_region: str = None,
                                region: str = None) -> dict:
    """Implementation detail."""
    effective_region = child_instance_region or region or "cn-hangzhou"
    params = {
        "CenId": cen_id,
        "ChildInstanceId": child_instance_id,
        "ChildInstanceType": child_instance_type,
        "ChildInstanceRegionId": effective_region,
        "PageSize": "100",
    }

    result = _call_with_retry("cbn", "describe-cen-region-domain-route-entries", params, region)
    if "error" in result:
        return result

    entries = result.get("CenRouteEntries", {}).get("CenRouteEntry", [])

    summary = []
    for entry in entries:
        aspath = entry.get("AsPaths", {}).get("AsPath", [])
        communities = entry.get("Communities", {}).get("Community", [])
        summary.append({
            "DestinationCidrBlock": entry.get("DestinationCidrBlock", ""),
            "Type": entry.get("Type", ""),
            "Status": entry.get("Status", ""),
            "NextHopInstanceId": entry.get("NextHopInstanceId", ""),
            "NextHopType": entry.get("NextHopType", ""),
            "NextHopRegionId": entry.get("NextHopRegionId", ""),
            "AsPaths": aspath,
            "Communities": communities,
        })

    return {"cen_routes": summary, "total": len(summary), "cen_id": cen_id}


def describe_cen_child_instance_route_entries(cen_id: str, child_instance_id: str,
                                                child_instance_type: str = "VPC",
                                                child_instance_region: str = None,
                                                region: str = None) -> dict:
    """Implementation detail."""
    effective_region = child_instance_region or region or "cn-hangzhou"
    
    all_entries = []
    page_number = 1
    page_size = 50
    
    while True:
        params = {
            "CenId": cen_id,
            "ChildInstanceId": child_instance_id,
            "ChildInstanceType": child_instance_type,
            "ChildInstanceRegionId": effective_region,
            "PageNumber": str(page_number),
            "PageSize": str(page_size),
        }
        
        result = _call_with_retry("cbn", "describe-cen-child-instance-route-entries", params, region)
        if "error" in result:
            return result
        
        entries = result.get("CenRouteEntries", {}).get("CenRouteEntry", [])
        
        for entry in entries:

            next_hop_info = {
                "NextHopInstanceId": entry.get("NextHopInstanceId", ""),
                "NextHopType": entry.get("NextHopType", ""),
                "NextHopRegionId": entry.get("NextHopRegionId", ""),
                "NextHopName": entry.get("NextHopName", ""),
            }
            

            vpc_peer_id = entry.get("VpcPeerId", "")
            if vpc_peer_id:
                next_hop_info["VpcPeerId"] = vpc_peer_id
            
            all_entries.append({
                "DestinationCidrBlock": entry.get("DestinationCidrBlock", ""),
                "Type": entry.get("Type", ""),  # System / Custom
                "Status": entry.get("Status", ""),
                "PublishStatus": entry.get("PublishStatus", ""),  # Published / NonPublished
                "NextHop": next_hop_info,
                "RoutePriority": entry.get("RoutePriority", ""),
                "PolicyRouteName": entry.get("PolicyRouteName", ""),
            })
        
        total_count = result.get("TotalCount", 0)
        page_number += 1
        

        if len(all_entries) >= total_count:
            break
    
    return {"cen_routes": all_entries, "total": len(all_entries), "cen_id": cen_id}


def check_vbr_route_sync(cen_id: str, vbr_id: str,
                          cen_region: str = None,
                          region: str = None) -> dict:
    """Implementation detail."""
    effective_cen_region = cen_region or region or "cn-hangzhou"



    cen_params = {
        "CenId": cen_id,
        "CenRegionId": effective_cen_region,
        "PageSize": "100",
    }
    cen_raw = _call_with_retry("cbn", "describe-cen-region-domain-route-entries", cen_params, region)
    if "error" in cen_raw:
        return {"error": cen_raw["error"], "verdict": "error",
                "cen_id": cen_id, "vbr_id": vbr_id}

    cen_entries = cen_raw.get("CenRouteEntries", {}).get("CenRouteEntry", [])
    cen_routes = []
    for entry in cen_entries:
        cen_routes.append({
            "DestinationCidrBlock": entry.get("DestinationCidrBlock", ""),
            "Status": entry.get("Status", ""),
            "NextHopInstanceId": entry.get("NextHopInstanceId", ""),
            "NextHopType": entry.get("NextHopType", ""),
            "NextHopRegionId": entry.get("NextHopRegionId", ""),
        })


    vbr_result = describe_cen_child_instance_route_entries(
        cen_id, vbr_id,
        child_instance_type="VBR",
        child_instance_region=effective_cen_region,
        region=region,
    )
    if "error" in vbr_result:
        return {"error": vbr_result["error"], "verdict": "error",
                "cen_id": cen_id, "vbr_id": vbr_id}



    routes_for_vbr = []
    for r in cen_routes:
        if r.get("NextHopInstanceId") != vbr_id and r.get("Status") == "Active":
            routes_for_vbr.append({
                "DestinationCidrBlock": r.get("DestinationCidrBlock", ""),
                "NextHopType": r.get("NextHopType", ""),
                "NextHopInstanceId": r.get("NextHopInstanceId", ""),
                "Status": r.get("Status", ""),
            })


    vbr_routes = vbr_result.get("cen_routes", [])
    vbr_cen_cidrs = set()
    vbr_cen_routes = []
    for r in vbr_routes:
        if r.get("Type") == "CEN":
            cidr = r.get("DestinationCidrBlock", "")
            vbr_cen_cidrs.add(cidr)
            vbr_cen_routes.append({
                "DestinationCidrBlock": cidr,
                "Type": r.get("Type", ""),
                "Status": r.get("Status", ""),
            })


    synced = []
    missing = []
    missing_details = []
    for r in routes_for_vbr:
        cidr = r["DestinationCidrBlock"]
        if cidr in vbr_cen_cidrs:
            synced.append(cidr)
        else:
            missing.append(cidr)
            missing_details.append(r)


    if not routes_for_vbr:
        verdict = "ok"
        sync_mode = "unknown"
        details = "CEN 区域路由表中无需同步到 VBR 的路由（无其他子实例路由）"
    elif not missing:
        verdict = "ok"
        sync_mode = "full"
        details = f"CEN 区域路由表中 {len(routes_for_vbr)} 条来自其他子实例的路由已全部同步到 VBR"
    else:
        verdict = "route_sync_missing"
        sync_mode = "selective"
        details = (
            f"CEN 区域路由表中有 {len(missing)} 条来自其他子实例的路由未同步到 VBR，"
            f"VBR 可能配置了「指定路由同步」模式。未同步网段: {', '.join(missing)}"
        )

    return {
        "cen_id": cen_id,
        "vbr_id": vbr_id,
        "verdict": verdict,
        "sync_mode": sync_mode,
        "cen_routes_for_vbr": routes_for_vbr,
        "vbr_cen_routes": vbr_cen_routes,
        "synced": synced,
        "missing": missing,
        "missing_details": missing_details,
        "details": details,
    }


def check_cen_for_vpcs(src_vpc_id: str, dst_vpc_id: str,
                        src_region: str = None, dst_region: str = None,
                        region: str = None) -> dict:
    """Implementation detail."""
    cens_result = describe_cens(region=region)
    if "error" in cens_result:
        return cens_result

    for cen in cens_result.get("cens", []):
        cen_id = cen["CenId"]
        children = describe_cen_attached_child_instances(cen_id, region=region)
        if "error" in children:
            continue

        child_ids = {c["ChildInstanceId"] for c in children.get("child_instances", [])}
        if src_vpc_id in child_ids and dst_vpc_id in child_ids:

            src_child = None
            dst_child = None
            for c in children["child_instances"]:
                if c["ChildInstanceId"] == src_vpc_id:
                    src_child = c
                if c["ChildInstanceId"] == dst_vpc_id:
                    dst_child = c

            return {
                "found": True,
                "cen_id": cen_id,
                "cen_name": cen["Name"],
                "cen_status": cen["Status"],
                "source_attachment": src_child,
                "destination_attachment": dst_child,
                "all_children": children["child_instances"],
                "details": f"VPC {src_vpc_id} 和 {dst_vpc_id} 均挂载到 CEN {cen_id} ({cen['Name']})",
            }

    return {
        "found": False,
        "cen_id": None,
        "details": f"未找到同时包含 VPC {src_vpc_id} 和 {dst_vpc_id} 的 CEN 实例",
    }




def list_transit_routers(cen_id: str = None, region: str = None) -> dict:
    """Implementation detail."""
    params = {"PageSize": "50"}
    if region:
        params["RegionId"] = region
    if cen_id:
        params["CenId"] = cen_id
    
    result = _call_with_retry("cbn", "list-transit-routers", params, region)
    if "error" in result:
        return result
    
    trs = result.get("TransitRouters", {})
    if isinstance(trs, list):
        tr_list = trs
    else:
        tr_list = trs.get("TransitRouter", [])
    
    summary = []
    for tr in tr_list:
        tr_info = {
            "TransitRouterId": tr.get("TransitRouterId", ""),
            "TransitRouterName": tr.get("TransitRouterName", ""),
            "TransitRouterDescription": tr.get("TransitRouterDescription", ""),
            "CenId": tr.get("CenId", ""),
            "RegionId": tr.get("RegionId", ""),
            "TransitRouterType": tr.get("Type", ""),  # Basic / Enterprise (API field is "Type")
            "Status": tr.get("Status", ""),
            "CreationTime": tr.get("CreationTime", ""),
        }
            
        summary.append(tr_info)
    
    return {"transit_routers": summary, "total": len(summary)}


def list_transit_router_vpc_attachments(transit_router_id: str, region: str = None,
                                          vpc_id: str = None) -> dict:
    """Implementation detail."""
    params = {
        "RegionId": region or "cn-hangzhou",
        "TransitRouterId": transit_router_id,
        "MaxResults": "50",
    }
    
    result = _call_with_retry("cbn", "list-transit-router-vpc-attachments", params, region)
    if "error" in result:
        return result
    
    attachments = result.get("TransitRouterAttachments", {})
    if isinstance(attachments, list):
        att_list = attachments
    else:
        att_list = attachments.get("TransitRouterAttachment", [])
    
    summary = []
    for att in att_list:

        resource_type = att.get("ResourceType") or att.get("AttachmentType", "")
        if resource_type != "VPC":
            continue
        

        if vpc_id and att.get("VpcId") != vpc_id:
            continue
        
        att_info = {
            "TransitRouterAttachmentId": att.get("TransitRouterAttachmentId", ""),
            "TransitRouterId": att.get("TransitRouterId", ""),
            "ResourceType": resource_type,
            "VpcId": att.get("VpcId", ""),
            "VpcOwnerId": att.get("VpcOwnerId", ""),
            "Status": att.get("Status", ""),
            "RouteTableId": att.get("RouteTableId", ""),
            "AutoPublishRouteEnabled": att.get("AutoPublishRouteEnabled", False),
            "CreationTime": att.get("CreationTime", ""),
        }
        
        summary.append(att_info)
    
    return {"vpc_attachments": summary, "total": len(summary)}


def list_transit_router_route_tables(transit_router_id: str, region: str = None) -> dict:
    """Implementation detail."""
    params = {
        "RegionId": region or "cn-hangzhou",
        "TransitRouterId": transit_router_id,
        "MaxResults": "50",
    }
    
    result = _call_with_retry("cbn", "list-transit-router-route-tables", params, region)
    if "error" in result:
        return result
    
    route_tables = result.get("TransitRouterRouteTables", {})
    if isinstance(route_tables, list):
        rt_list = route_tables
    else:
        rt_list = route_tables.get("TransitRouterRouteTable", [])
    
    summary = []
    for rt in rt_list:
        rt_info = {
            "TransitRouterRouteTableId": rt.get("TransitRouterRouteTableId", ""),
            "TransitRouterRouteTableName": rt.get("TransitRouterRouteTableName", ""),
            "TransitRouterId": rt.get("TransitRouterId", ""),
            "TransitRouterRouteTableType": rt.get("TransitRouterRouteTableType", ""),  # System / Custom
            "CreationTime": rt.get("CreationTime", ""),
            "AssociationCount": rt.get("AssociationCount", 0),
            "PropagationCount": rt.get("PropagationCount", 0),
        }
        
        summary.append(rt_info)
    
    return {"route_tables": summary, "total": len(summary)}


def list_transit_router_route_entries(transit_router_route_table_id: str,
                                       region: str = None,
                                       status: str = None) -> dict:
    """Implementation detail."""
    params = {
        "RegionId": region or "cn-hangzhou",
        "TransitRouterRouteTableId": transit_router_route_table_id,
        "MaxResults": "100",
    }
    if status:
        params["TransitRouterRouteEntryStatus"] = status

    all_entries = []
    next_token = None

    while True:
        if next_token:
            params["NextToken"] = next_token

        result = _call_with_retry("cbn", "list-transit-router-route-entries", params, region)
        if "error" in result:
            if "NotFound" in result.get("error", ""):
                return {
                    "route_entries": [],
                    "total": 0,
                    "note": "基础版 TR 不支持此 API，请使用 DescribeCenChildInstanceRouteEntries"
                }
            return result

        entries = result.get("TransitRouterRouteEntries", [])
        if isinstance(entries, dict):
            entries = entries.get("TransitRouterRouteEntry", [])

        for entry in entries:
            path_attrs = entry.get("PathAttributes", {})
            entry_info = {
                "DestinationCidrBlock": entry.get("TransitRouterRouteEntryDestinationCidrBlock",
                                                   entry.get("DestinationCidrBlock", "")),
                "RouteType": entry.get("TransitRouterRouteEntryType",
                                        entry.get("RouteType", "")),
                "Status": entry.get("TransitRouterRouteEntryStatus",
                                     entry.get("Status", "")),
                "NextHopType": entry.get("TransitRouterRouteEntryNextHopType",
                                          entry.get("NextHopType", "")),
                "NextHopId": entry.get("TransitRouterRouteEntryNextHopId",
                                        entry.get("NextHopId", "")),
                "NextHopResourceId": entry.get("TransitRouterRouteEntryNextHopResourceId", ""),
                "NextHopResourceType": entry.get("TransitRouterRouteEntryNextHopResourceType", ""),
                "OriginResourceId": path_attrs.get("OriginInstanceId",
                                                     entry.get("TransitRouterRouteEntryOriginResourceId", "")),
                "OriginResourceType": path_attrs.get("OriginInstanceType",
                                                       entry.get("TransitRouterRouteEntryOriginResourceType", "")),
                "OriginRouteType": path_attrs.get("OriginRouteType", ""),
                "Preference": path_attrs.get("Preference", ""),
            }

            all_entries.append(entry_info)

        next_token = result.get("NextToken")
        total_count = result.get("TotalCount", 0)
        if not next_token or len(all_entries) >= total_count:
            break

    return {"route_entries": all_entries, "total": len(all_entries)}


def list_transit_router_route_table_associations(transit_router_route_table_id: str,
                                                   region: str = None) -> dict:
    """Implementation detail."""
    params = {
        "RegionId": region or "cn-hangzhou",
        "TransitRouterRouteTableId": transit_router_route_table_id,
        "MaxResults": "100",
    }

    all_associations = []
    next_token = None

    while True:
        if next_token:
            params["NextToken"] = next_token

        result = _call_with_retry("cbn", "list-transit-router-route-table-associations", params, region)
        if "error" in result:
            return result

        associations = result.get("TransitRouterAssociations", [])
        if isinstance(associations, dict):
            associations = associations.get("TransitRouterAssociation", [])

        for assoc in associations:
            all_associations.append({
                "TransitRouterAttachmentId": assoc.get("TransitRouterAttachmentId", ""),
                "ResourceId": assoc.get("ResourceId", ""),
                "ResourceType": assoc.get("ResourceType", ""),
                "Status": assoc.get("Status", ""),
                "TransitRouterRouteTableId": transit_router_route_table_id,
            })

        next_token = result.get("NextToken")
        if not next_token:
            break

    return {"associations": all_associations, "total": len(all_associations)}


def list_transit_router_route_table_propagations(transit_router_route_table_id: str,
                                                    region: str = None) -> dict:
    """Implementation detail."""
    params = {
        "RegionId": region or "cn-hangzhou",
        "TransitRouterRouteTableId": transit_router_route_table_id,
        "MaxResults": "100",
    }

    all_propagations = []
    next_token = None

    while True:
        if next_token:
            params["NextToken"] = next_token

        result = _call_with_retry("cbn", "list-transit-router-route-table-propagations", params, region)
        if "error" in result:
            return result

        propagations = result.get("TransitRouterPropagations", [])
        if isinstance(propagations, dict):
            propagations = propagations.get("TransitRouterPropagation", [])

        for prop in propagations:
            all_propagations.append({
                "TransitRouterAttachmentId": prop.get("TransitRouterAttachmentId", ""),
                "ResourceId": prop.get("ResourceId", ""),
                "ResourceType": prop.get("ResourceType", ""),
                "Status": prop.get("Status", ""),
                "TransitRouterRouteTableId": transit_router_route_table_id,
            })

        next_token = result.get("NextToken")
        if not next_token:
            break

    return {"propagations": all_propagations, "total": len(all_propagations)}


def describe_cen_route_maps(cen_id: str, cen_region_id: str = None,
                             region: str = None) -> dict:
    """Implementation detail."""
    params = {
        "CenId": cen_id,
        "PageSize": "50",
    }
    if cen_region_id:
        params["CenRegionId"] = cen_region_id

    all_maps = []
    page_number = 1

    while True:
        params["PageNumber"] = str(page_number)

        result = _call_with_retry("cbn", "describe-cen-route-maps", params, region)
        if "error" in result:
            return result

        route_maps = result.get("RouteMaps", {}).get("RouteMap", [])

        for rm in route_maps:
            src_instance_ids = rm.get("SourceInstanceIds", {})
            if isinstance(src_instance_ids, dict):
                src_instance_ids = src_instance_ids.get("SourceInstanceId", [])

            dst_instance_ids = rm.get("DestinationInstanceIds", {})
            if isinstance(dst_instance_ids, dict):
                dst_instance_ids = dst_instance_ids.get("DestinationInstanceId", [])

            dst_cidr_blocks = rm.get("DestinationCidrBlocks", {})
            if isinstance(dst_cidr_blocks, dict):
                dst_cidr_blocks = dst_cidr_blocks.get("DestinationCidrBlock", [])

            src_region_ids = rm.get("SourceRegionIds", {})
            if isinstance(src_region_ids, dict):
                src_region_ids = src_region_ids.get("SourceRegionId", [])

            all_maps.append({
                "RouteMapId": rm.get("RouteMapId", ""),
                "CenId": rm.get("CenId", ""),
                "CenRegionId": rm.get("CenRegionId", ""),
                "Description": rm.get("Description", ""),
                "MapResult": rm.get("MapResult", ""),  # Permit / Deny
                "Priority": rm.get("Priority", 0),
                "TransmitDirection": rm.get("TransmitDirection", ""),  # RegionIn / RegionOut
                "Status": rm.get("Status", ""),
                "SourceInstanceIds": src_instance_ids,
                "DestinationInstanceIds": dst_instance_ids,
                "DestinationCidrBlocks": dst_cidr_blocks,
                "CidrMatchMode": rm.get("CidrMatchMode", ""),  # Include / Exclude
                "SourceRegionIds": src_region_ids,
                "TransitRouterRouteTableId": rm.get("TransitRouterRouteTableId", ""),
            })

        total_count = result.get("TotalCount", 0)
        if len(all_maps) >= total_count:
            break
        page_number += 1


    all_maps.sort(key=lambda x: x.get("Priority", 9999))

    return {"route_maps": all_maps, "total": len(all_maps)}


def find_associated_route_table_for_attachment(route_tables: list,
                                                 attachment_id: str,
                                                 region: str = None) -> dict:
    """Implementation detail."""
    if not route_tables:
        return {"error": "无可用的 TR 路由表"}


    if len(route_tables) == 1:
        rt = route_tables[0]
        return {
            "route_table_id": rt.get("TransitRouterRouteTableId", ""),
            "route_table_name": rt.get("TransitRouterRouteTableName", ""),
            "route_table_type": rt.get("TransitRouterRouteTableType", ""),
            "association_status": "Active",
            "single_table": True,
            "details": "TR 仅有一张路由表，直接使用",
        }


    for rt in route_tables:
        rt_id = rt.get("TransitRouterRouteTableId", "")
        if not rt_id:
            continue

        assoc_result = list_transit_router_route_table_associations(rt_id, region)
        if "error" in assoc_result:
            continue

        for assoc in assoc_result.get("associations", []):
            if assoc.get("TransitRouterAttachmentId") == attachment_id:
                return {
                    "route_table_id": rt_id,
                    "route_table_name": rt.get("TransitRouterRouteTableName", ""),
                    "route_table_type": rt.get("TransitRouterRouteTableType", ""),
                    "association_status": assoc.get("Status", ""),
                    "single_table": False,
                    "details": (
                        f"Attachment {attachment_id} 关联到路由表 {rt_id} "
                        f"(类型: {rt.get('TransitRouterRouteTableType', '')}, "
                        f"状态: {assoc.get('Status', '')})"
                    ),
                }


    rt = route_tables[0]
    return {
        "route_table_id": rt.get("TransitRouterRouteTableId", ""),
        "route_table_name": rt.get("TransitRouterRouteTableName", ""),
        "route_table_type": rt.get("TransitRouterRouteTableType", ""),
        "association_status": "Unknown",
        "single_table": False,
        "fallback": True,
        "details": f"未找到 Attachment {attachment_id} 的关联路由表，回退使用第一张路由表",
    }


def check_propagation_for_attachment(route_table_id: str, attachment_id: str,
                                       region: str = None) -> dict:
    """Implementation detail."""
    prop_result = list_transit_router_route_table_propagations(route_table_id, region)
    if "error" in prop_result:
        return {
            "propagated": False,
            "propagation_status": "Error",
            "details": f"查询传播关系失败: {prop_result.get('error', '')}",
        }

    for prop in prop_result.get("propagations", []):
        if prop.get("TransitRouterAttachmentId") == attachment_id:
            status = prop.get("Status", "")
            return {
                "propagated": True,
                "propagation_status": status,
                "details": (
                    f"Attachment {attachment_id} 已向路由表 {route_table_id} "
                    f"配置路由学习（状态: {status}）"
                ),
            }

    return {
        "propagated": False,
        "propagation_status": "NotConfigured",
        "details": (
            f"Attachment {attachment_id} 未向路由表 {route_table_id} 配置路由学习（Propagation 未配置）"
        ),
    }


def describe_transit_router_vpc_attachment(transit_router_attachment_id: str, 
                                            region: str = None) -> dict:
    """Implementation detail."""
    params = {
        "RegionId": region or "cn-hangzhou",
        "TransitRouterAttachmentId": transit_router_attachment_id,
    }
    
    result = _call_with_retry("cbn", "describe-transit-router-vpc-attachment", params, region)
    if "error" in result:
        return result
    
    att = result.get("TransitRouterAttachment", {})
    
    return {
        "attachment": {
            "TransitRouterAttachmentId": att.get("TransitRouterAttachmentId", ""),
            "TransitRouterId": att.get("TransitRouterId", ""),
            "VpcId": att.get("VpcId", ""),
            "Status": att.get("Status", ""),
            "RouteTableId": att.get("RouteTableId", ""),
            "AutoPublishRouteEnabled": att.get("AutoPublishRouteEnabled", False),
            "PublishVpcRouteEnabled": att.get("PublishVpcRouteEnabled", False),
            "EnableIpv6": att.get("EnableIpv6", False),
            "CreationTime": att.get("CreationTime", ""),
        }
    }


def _basic_tr_route_lookup_via_cen(cen_id: str, cen_region_id: str,
                                    dst_ip: str) -> dict:
    """Implementation detail."""
    params = {
        "CenId": cen_id,
        "CenRegionId": cen_region_id,
        "PageSize": "100",
    }

    all_entries = []
    page_number = 1

    while True:
        params["PageNumber"] = str(page_number)
        result = _call_with_retry("cbn", "describe-cen-region-domain-route-entries",
                                   params, cen_region_id)
        if "error" in result:
            return {
                "matched": False,
                "route": None,
                "prefix_len": -1,
                "rejected_routes": [],
                "conflict": False,
                "details": f"基础版 TR 降级查询失败: {result.get('error', '')}",
            }

        entries = result.get("CenRouteEntries", {}).get("CenRouteEntry", [])
        all_entries.extend(entries)

        total = result.get("TotalCount", 0)
        if len(all_entries) >= total or not entries:
            break
        page_number += 1


    best = None
    best_prefix = -1
    for entry in all_entries:
        cidr = entry.get("DestinationCidrBlock", "")
        status = entry.get("Status", "")
        if cidr and status == "Active" and cidr_contains(cidr, dst_ip):
            plen = cidr_prefix_len(cidr)
            if plen > best_prefix:
                best_prefix = plen
                best = entry

    if best:
        next_hop_id = best.get("NextHopInstanceId", "")
        next_hop_type = best.get("NextHopType", "")
        next_hop_region = best.get("NextHopRegionId", "")
        route_type = best.get("Type", "")
        return {
            "matched": True,
            "route": {
                "DestinationCidrBlock": best.get("DestinationCidrBlock", ""),
                "RouteType": route_type,
                "Status": "Active",
                "NextHopType": next_hop_type,
                "NextHopId": next_hop_id,
                "NextHopResourceId": next_hop_id,
                "NextHopResourceType": next_hop_type,
                "NextHopRegionId": next_hop_region,
            },
            "prefix_len": best_prefix,
            "rejected_routes": [],
            "conflict": False,
            "next_hop_summary": f"{next_hop_type}({next_hop_id}) @{next_hop_region}",
            "is_active": True,
            "details": (
                f"[基础版TR] 匹配路由: {best.get('DestinationCidrBlock', '')} → "
                f"{next_hop_type}({next_hop_id}) @{next_hop_region} "
                f"(类型: {route_type}, 状态: Active)"
            ),
        }
    else:
        return {
            "matched": False,
            "route": None,
            "prefix_len": -1,
            "rejected_routes": [],
            "conflict": False,
            "details": (
                f"[基础版TR] CEN {cen_id} 地域 {cen_region_id} 路由域中"
                f"未找到匹配 {dst_ip} 的 Active 路由"
            ),
        }


def tr_route_lookup(transit_router_route_table_id: str, dst_ip: str,
                    region: str = None, cen_id: str = None,
                    cen_region_id: str = None) -> dict:
    """Implementation detail."""

    active_result = list_transit_router_route_entries(
        transit_router_route_table_id, region, status="Active")
    rejected_result = list_transit_router_route_entries(
        transit_router_route_table_id, region, status="Rejected")


    is_basic_tr = False
    if (active_result.get("note") and "基础版" in active_result.get("note", "")
            and active_result.get("total", 0) == 0):
        is_basic_tr = True
        if cen_id:
            effective_region = cen_region_id or region
            fallback_result = _basic_tr_route_lookup_via_cen(
                cen_id, effective_region, dst_ip)
            fallback_result["basic_tr_fallback"] = True
            return fallback_result
        else:
            return {
                "matched": False,
                "route": None,
                "prefix_len": -1,
                "rejected_routes": [],
                "conflict": False,
                "basic_tr_fallback": True,
                "details": (
                    f"基础版 TR 不支持 ListTransitRouterRouteEntries API，"
                    f"且未提供 cen_id 参数，无法降级查询。"
                    f"请使用 --cen-id 参数指定 CEN 实例 ID"
                ),
            }

    if "error" in active_result:
        return active_result


    best_active = None
    best_active_prefix = -1
    for entry in active_result.get("route_entries", []):
        cidr = entry.get("DestinationCidrBlock", "")
        if cidr and cidr_contains(cidr, dst_ip):
            prefix_len = cidr_prefix_len(cidr)
            if prefix_len > best_active_prefix:
                best_active_prefix = prefix_len
                best_active = entry


    rejected_matches = []
    if "error" not in rejected_result:
        for entry in rejected_result.get("route_entries", []):
            cidr = entry.get("DestinationCidrBlock", "")
            if cidr and cidr_contains(cidr, dst_ip):
                rejected_matches.append(entry)


    result = {
        "matched": best_active is not None,
        "route": best_active,
        "prefix_len": best_active_prefix if best_active else -1,
        "rejected_routes": rejected_matches,
        "conflict": False,
    }

    if best_active:
        next_hop_type = best_active.get("NextHopType", "")
        next_hop_id = best_active.get("NextHopId", "")
        result["next_hop_summary"] = f"{next_hop_type}({next_hop_id})"
        result["is_active"] = True
        result["details"] = (
            f"匹配路由: {best_active.get('DestinationCidrBlock', '')} → "
            f"{next_hop_type}({next_hop_id}) "
            f"(类型: {best_active.get('RouteType', '')}, "
            f"状态: Active)"
        )

    if rejected_matches:
        result["conflict"] = True
        rejected_summaries = []
        for r in rejected_matches:
            r_cidr = r.get("DestinationCidrBlock", "")
            r_origin = r.get("OriginResourceId", "")
            r_origin_type = r.get("OriginResourceType", "")
            r_nexthop = r.get("NextHopId", "")
            rejected_summaries.append(
                f"{r_cidr} (来源: {r_origin_type} {r_origin}, "
                f"下一跳: {r_nexthop}, 状态: Rejected)"
            )
        result["rejected_details"] = rejected_summaries

        if best_active:

            result["conflict_details"] = (
                f"存在路由前缀冲突: 目的 {dst_ip} 匹配到 Active 路由 "
                f"{best_active.get('DestinationCidrBlock', '')} → {best_active.get('NextHopId', '')}，"
                f"同时有 {len(rejected_matches)} 条同前缀路由因冲突被 Rejected"
            )
        else:

            result["details"] = (
                f"TR 路由表 {transit_router_route_table_id} 中未找到匹配 {dst_ip} "
                f"的 Active 路由，但发现 {len(rejected_matches)} 条 Rejected 路由（前缀冲突）"
            )
    elif not best_active:
        result["details"] = (
            f"TR 路由表 {transit_router_route_table_id} 中未找到匹配 {dst_ip} 的路由"
            f"（Active 和 Rejected 均无）"
        )

    return result


def check_tr_routing_for_vpcs(src_vpc_id: str, dst_vpc_id: str,
                               src_region: str = None, dst_region: str = None,
                               cen_id: str = None,
                               dst_ip: str = None, src_ip: str = None) -> dict:
    """Implementation detail."""
    result = {
        "source_tr": None,
        "destination_tr": None,
        "source_attachment": None,
        "destination_attachment": None,
        "source_route_table": None,
        "destination_route_table": None,
        "routing_configured": False,
        "details": "",
    }
    

    src_trs = list_transit_routers(cen_id=cen_id, region=src_region)
    if "error" in src_trs or not src_trs.get("transit_routers"):
        result["details"] = f"未找到源端 {src_region} 的转发路由器"
        return result
    
    src_tr = src_trs["transit_routers"][0]
    result["source_tr"] = src_tr
    

    src_atts = list_transit_router_vpc_attachments(
        transit_router_id=src_tr["TransitRouterId"],
        region=src_region,
        vpc_id=src_vpc_id
    )
    if "error" in src_atts or not src_atts.get("vpc_attachments"):
        result["details"] = f"VPC {src_vpc_id} 未连接到源端 TR {src_tr['TransitRouterId']}"
        return result
    
    src_att = src_atts["vpc_attachments"][0]
    result["source_attachment"] = src_att
    

    if src_region == dst_region:
        dst_tr = src_tr
    else:
        dst_trs = list_transit_routers(cen_id=cen_id, region=dst_region)
        if "error" in dst_trs or not dst_trs.get("transit_routers"):
            result["details"] = f"未找到目的端 {dst_region} 的转发路由器"
            return result
        dst_tr = dst_trs["transit_routers"][0]
    
    result["destination_tr"] = dst_tr
    

    dst_atts = list_transit_router_vpc_attachments(
        transit_router_id=dst_tr["TransitRouterId"],
        region=dst_region,
        vpc_id=dst_vpc_id
    )
    if "error" in dst_atts or not dst_atts.get("vpc_attachments"):
        result["details"] = f"VPC {dst_vpc_id} 未连接到目的端 TR {dst_tr['TransitRouterId']}"
        return result
    
    dst_att = dst_atts["vpc_attachments"][0]
    result["destination_attachment"] = dst_att
    

    src_rts = list_transit_router_route_tables(
        transit_router_id=src_tr["TransitRouterId"],
        region=src_region
    )
    if "error" not in src_rts and src_rts.get("route_tables"):
        result["source_route_table"] = src_rts["route_tables"]
    

    if src_region != dst_region:
        dst_rts = list_transit_router_route_tables(
            transit_router_id=dst_tr["TransitRouterId"],
            region=dst_region
        )
        if "error" not in dst_rts and dst_rts.get("route_tables"):
            result["destination_route_table"] = dst_rts["route_tables"]
    
    result["routing_configured"] = True
    result["details"] = (
        f"源端: VPC {src_vpc_id} → TR {src_tr['TransitRouterId']} ({src_tr['TransitRouterType']}) "
        f"连接 {src_att['TransitRouterAttachmentId']}\n"
        f"目的端: VPC {dst_vpc_id} → TR {dst_tr['TransitRouterId']} ({dst_tr['TransitRouterType']}) "
        f"连接 {dst_att['TransitRouterAttachmentId']}"
    )


    if dst_ip and result.get("source_route_table"):

        src_assoc = find_associated_route_table_for_attachment(
            result["source_route_table"],
            src_att["TransitRouterAttachmentId"],
            region=src_region,
        )
        result["source_associated_route_table"] = src_assoc

        forward_rt_id = src_assoc.get("route_table_id", "")

        if forward_rt_id:

            dst_prop = check_propagation_for_attachment(
                forward_rt_id,
                dst_att["TransitRouterAttachmentId"],
                region=src_region,
            )
            result["destination_propagation"] = dst_prop


            result["forward_route_check"] = tr_route_lookup(forward_rt_id, dst_ip, src_region)


            forward_check = result.get("forward_route_check", {})


            if forward_check.get("conflict"):
                rejected = forward_check.get("rejected_routes", [])
                result["route_conflict"] = {
                    "detected": True,
                    "type": "prefix_conflict",
                    "rejected_count": len(rejected),
                    "rejected_routes": rejected,
                    "active_route": forward_check.get("route"),
                    "details": forward_check.get("conflict_details",
                                                  forward_check.get("details", "")),
                }


            elif not forward_check.get("matched") and not forward_check.get("rejected_routes") \
                    and dst_prop.get("propagated"):
                cen_id_for_maps = src_tr.get("CenId") or cen_id
                if cen_id_for_maps:
                    route_maps = describe_cen_route_maps(
                        cen_id_for_maps,
                        cen_region_id=src_region,
                        region=src_region,
                    )
                    if "error" not in route_maps:
                        blocking_maps = []
                        for rm in route_maps.get("route_maps", []):
                            if rm.get("MapResult") != "Deny" or rm.get("Status") != "Active":
                                continue
                            if rm.get("TransmitDirection") != "RegionIn":
                                continue
                            dst_cidrs = rm.get("DestinationCidrBlocks", [])
                            if dst_cidrs:
                                for cidr in dst_cidrs:
                                    if cidr_contains(cidr, dst_ip):
                                        blocking_maps.append(rm)
                                        break
                        result["route_map_check"] = {
                            "total_maps": route_maps.get("total", 0),
                            "blocking_maps": blocking_maps,
                            "blocked": len(blocking_maps) > 0,
                            "details": (
                                f"发现 {len(blocking_maps)} 条 Deny 路由策略匹配目的网段"
                                if blocking_maps else
                                "未发现匹配的 Deny 路由策略"
                            ),
                        }


    if src_ip:

        return_rts = result.get("destination_route_table") or result.get("source_route_table")
        return_region = dst_region if src_region != dst_region else src_region
        return_att_id = dst_att["TransitRouterAttachmentId"]

        if return_rts:

            dst_assoc = find_associated_route_table_for_attachment(
                return_rts, return_att_id, region=return_region,
            )
            result["destination_associated_route_table"] = dst_assoc

            return_rt_id = dst_assoc.get("route_table_id", "")
            if return_rt_id:

                src_prop = check_propagation_for_attachment(
                    return_rt_id,
                    src_att["TransitRouterAttachmentId"],
                    region=return_region,
                )
                result["source_propagation"] = src_prop

                result["return_route_check"] = tr_route_lookup(return_rt_id, src_ip, return_region)

    return result




def main():
    import argparse

    parser = argparse.ArgumentParser(description="CEN / VPC Peering 诊断")
    sub = parser.add_subparsers(dest="action")

    # VPC Peering
    p = sub.add_parser("peering", help="查询 VPC 对等连接")
    p.add_argument("--vpc-id", help="VPC ID")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("peering-check", help="检查两个 VPC 间的对等连接")
    p.add_argument("--src-vpc", required=True, help="源 VPC ID")
    p.add_argument("--dst-vpc", required=True, help="目的 VPC ID")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("cen", help="查询 CEN 实例")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("cen-children", help="查询 CEN 挂载的网络实例")
    p.add_argument("--cen-id", required=True, help="CEN 实例 ID")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("cen-routes", help="查询 CEN 路由条目 (DescribeCenRegionDomainRouteEntries)")
    p.add_argument("--cen-id", required=True, help="CEN 实例 ID")
    p.add_argument("--child-id", required=True, help="网络实例 ID")
    p.add_argument("--child-type", default="VPC", help="网络实例类型")
    p.add_argument("--child-region", help="网络实例地域")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("cen-child-routes", help="查询 CEN 路由条目 - VPC 视角 (DescribeCenChildInstanceRouteEntries)")
    p.add_argument("--cen-id", required=True, help="CEN 实例 ID")
    p.add_argument("--child-id", required=True, help="网络实例 ID（如 VPC ID）")
    p.add_argument("--child-type", default="VPC", help="网络实例类型")
    p.add_argument("--child-region", help="网络实例地域")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("cen-check", help="检查两个 VPC 是否通过 CEN 连接")
    p.add_argument("--src-vpc", required=True, help="源 VPC ID")
    p.add_argument("--dst-vpc", required=True, help="目的 VPC ID")
    p.add_argument("--src-region", help="源 VPC 地域")
    p.add_argument("--dst-region", help="目的 VPC 地域")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("tr-list", help="查询转发路由器实例")
    p.add_argument("--cen-id", help="CEN 实例 ID")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("tr-vpc-attachments", help="查询 TR 的 VPC 连接")
    p.add_argument("--tr-id", required=True, help="转发路由器 ID")
    p.add_argument("--vpc-id", help="VPC ID")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("tr-route-tables", help="查询 TR 路由表")
    p.add_argument("--tr-id", required=True, help="转发路由器 ID")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("tr-routes", help="查询 TR 路由表条目")
    p.add_argument("--tr-route-table-id", required=True, help="TR 路由表 ID")
    p.add_argument("--status", help="路由状态过滤（Active / Rejected）")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("tr-route-check", help="对 TR 路由表做目的 IP 精确匹配")
    p.add_argument("--tr-route-table-id", required=True, help="TR 路由表 ID")
    p.add_argument("--dst-ip", required=True, help="目的 IP 地址")
    p.add_argument("--cen-id", help="CEN ID（基础版 TR 降级查询时使用）")
    p.add_argument("--cen-region-id", help="CEN 地域 ID（基础版 TR 降级查询，默认同 --region）")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("tr-associations", help="查询 TR 路由表的关联关系（关联转发）")
    p.add_argument("--tr-route-table-id", required=True, help="TR 路由表 ID")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("tr-propagations", help="查询 TR 路由表的路由学习关系（Propagation）")
    p.add_argument("--tr-route-table-id", required=True, help="TR 路由表 ID")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("cen-route-maps", help="查询 CEN 路由策略（Route Map）")
    p.add_argument("--cen-id", required=True, help="CEN 实例 ID")
    p.add_argument("--cen-region-id", help="地域过滤")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("vbr-route-sync-check", help="检查 VBR 指定路由同步（交叉对比 CEN 区域路由表与 VBR 子实例路由）")
    p.add_argument("--cen-id", required=True, help="CEN 实例 ID")
    p.add_argument("--vbr-id", required=True, help="VBR 实例 ID")
    p.add_argument("--cen-region", help="CEN 地域（默认同 --region）")
    p.add_argument("--region", help="地域")


    p = sub.add_parser("tr-check", help="检查两个 VPC 通过 TR 的路由关联和转发")
    p.add_argument("--src-vpc", required=True, help="源 VPC ID")
    p.add_argument("--dst-vpc", required=True, help="目的 VPC ID")
    p.add_argument("--src-region", help="源 VPC 地域")
    p.add_argument("--dst-region", help="目的 VPC 地域")
    p.add_argument("--cen-id", help="CEN ID")
    p.add_argument("--dst-ip", help="目的 IP，用于 TR 路由表精确匹配")
    p.add_argument("--src-ip", help="源 IP，用于 TR 回程路由精确匹配")

    args = parser.parse_args()

    if args.action == "peering":
        result = describe_vpc_peer_connections(vpc_id=args.vpc_id, region=args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "peering-check":
        result = check_peering_for_vpcs(args.src_vpc, args.dst_vpc, region=args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "cen":
        result = describe_cens(region=args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "cen-children":
        result = describe_cen_attached_child_instances(args.cen_id, region=args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "cen-routes":
        result = describe_cen_route_entries(
            args.cen_id, args.child_id,
            child_instance_type=args.child_type,
            child_instance_region=args.child_region,
            region=args.region,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "cen-child-routes":
        result = describe_cen_child_instance_route_entries(
            args.cen_id, args.child_id,
            child_instance_type=args.child_type,
            child_instance_region=args.child_region,
            region=args.region,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "cen-check":
        result = check_cen_for_vpcs(
            args.src_vpc, args.dst_vpc,
            src_region=args.src_region, dst_region=args.dst_region,
            region=args.region,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "tr-list":
        result = list_transit_routers(cen_id=args.cen_id, region=args.region)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "tr-vpc-attachments":
        result = list_transit_router_vpc_attachments(
            transit_router_id=args.tr_id,
            region=args.region,
            vpc_id=args.vpc_id,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "tr-route-tables":
        result = list_transit_router_route_tables(
            transit_router_id=args.tr_id,
            region=args.region,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "tr-routes":
        result = list_transit_router_route_entries(
            transit_router_route_table_id=args.tr_route_table_id,
            region=args.region,
            status=getattr(args, 'status', None),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "tr-route-check":
        result = tr_route_lookup(
            transit_router_route_table_id=args.tr_route_table_id,
            dst_ip=args.dst_ip,
            region=args.region,
            cen_id=getattr(args, 'cen_id', None),
            cen_region_id=getattr(args, 'cen_region_id', None),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "tr-associations":
        result = list_transit_router_route_table_associations(
            transit_router_route_table_id=args.tr_route_table_id,
            region=args.region,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "tr-propagations":
        result = list_transit_router_route_table_propagations(
            transit_router_route_table_id=args.tr_route_table_id,
            region=args.region,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "cen-route-maps":
        result = describe_cen_route_maps(
            cen_id=args.cen_id,
            cen_region_id=getattr(args, 'cen_region_id', None),
            region=args.region,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "vbr-route-sync-check":
        result = check_vbr_route_sync(
            cen_id=args.cen_id,
            vbr_id=args.vbr_id,
            cen_region=getattr(args, 'cen_region', None),
            region=args.region,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "tr-check":
        result = check_tr_routing_for_vpcs(
            src_vpc_id=args.src_vpc,
            dst_vpc_id=args.dst_vpc,
            src_region=args.src_region,
            dst_region=args.dst_region,
            cen_id=args.cen_id,
            dst_ip=getattr(args, 'dst_ip', None),
            src_ip=getattr(args, 'src_ip', None),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(json.dumps({"error": "用户中断"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(json.dumps({"error": f"未处理的异常: {type(e).__name__}: {e}"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
