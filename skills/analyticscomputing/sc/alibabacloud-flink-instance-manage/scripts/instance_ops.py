#!/usr/bin/env python3
"""
Flink Instance Manager - CLI for Alibaba Cloud Flink OpenAPI (2021-10-28)

Usage:
    python instance_ops.py <command> [options]

Commands:
    create              Create a new Flink instance
    describe            Describe instances
    describe_regions    List supported regions
    describe_zones      List supported zones
    create_namespace    Create a namespace
    describe_namespaces Describe namespaces
    list_tags           List tags for resources

Authentication:
    Uses Alibaba Cloud default credential chain (RAM role, CLI profile, etc.)

Output:
    JSON to stdout, exit code 0 = success
"""

import argparse
import json
import sys

from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_foasconsole20211028 import models as foas_models
from alibabacloud_foasconsole20211028.client import Client
from alibabacloud_tea_openapi import models as openapi_models
from alibabacloud_tea_util import models as util_models

DEFAULT_CONNECT_TIMEOUT_MS = 10_000
DEFAULT_READ_TIMEOUT_MS = 60_000
DEFAULT_USER_AGENT = "AlibabaCloud-Agent-Skills"


class FlinkClient:
    """Flink OpenAPI client (2021-10-28) with automatic authentication."""

    def __init__(self, region_id):
        if not region_id:
            raise ValueError(
                "region_id is required. Please specify the region for this operation."
            )

        config = openapi_models.Config(
            credential=CredentialClient(),
            region_id=region_id,
            endpoint=f"foasconsole.{region_id}.aliyuncs.com",
            user_agent=DEFAULT_USER_AGENT,
        )

        self.client = Client(config)
        self.runtime_options = util_models.RuntimeOptions(
            connect_timeout=DEFAULT_CONNECT_TIMEOUT_MS,
            read_timeout=DEFAULT_READ_TIMEOUT_MS,
        )

    def call_api(self, method_name, request=None):
        """Call API with timeout runtime options when available."""
        method_with_options = None
        for candidate in (f"{method_name}_with_options", f"{method_name}with_options"):
            method_with_options = getattr(self.client, candidate, None)
            if method_with_options:
                break

        if method_with_options:
            if request is None:
                return method_with_options(self.runtime_options)
            return method_with_options(request, self.runtime_options)

        method = getattr(self.client, method_name)
        if request is None:
            return method()
        return method(request)


def _get_resource_spec_values(spec):
    """Return normalized (cpu, memory_gb) tuple from a resource spec map."""
    if not isinstance(spec, dict):
        return None, None
    cpu = spec.get("Cpu")
    memory_gb = spec.get("MemoryGB")
    if cpu is None:
        cpu = spec.get("cpu")
    if memory_gb is None:
        memory_gb = spec.get("memory_gb")
    return cpu, memory_gb


def _confirmation_audit(confirm_provided):
    """Return an auditable confirmation gate snapshot for create operations."""
    provided = bool(confirm_provided)
    return {
        "required_flag": "--confirm",
        "provided": provided,
        "status": "passed" if provided else "missing",
    }


def list_namespaces(client, region_id, instance_id):
    """Return namespace list for an instance."""
    request = foas_models.DescribeNamespacesRequest(
        instance_id=instance_id, region=region_id
    )
    response = client.call_api("describe_namespaces", request)
    return response.body.to_map().get("Namespaces", [])


def find_namespace_by_name(client, region_id, instance_id, namespace_name):
    """Return namespace detail by name from DescribeNamespaces result."""
    namespaces = list_namespaces(client, region_id, instance_id)
    for namespace in namespaces:
        if namespace.get("Namespace") == namespace_name:
            return namespace
    return None


def find_instance_by_name(client, region_id, instance_name):
    """Return instance detail by name from DescribeInstances result."""
    request = foas_models.DescribeInstancesRequest(region=region_id)
    response = client.call_api("describe_instances", request)
    instances = response.body.to_map().get("Instances", [])
    for inst in instances:
        if inst.get("InstanceName") == instance_name:
            return inst
    return None


def find_instance_by_id(client, region_id, instance_id):
    """Return instance detail by id from DescribeInstances result."""
    request = foas_models.DescribeInstancesRequest(region=region_id)
    response = client.call_api("describe_instances", request)
    instances = response.body.to_map().get("Instances", [])
    for inst in instances:
        if inst.get("InstanceId") == instance_id:
            return inst
    return None


def _sum_namespace_allocations(namespaces):
    """Return aggregated namespace allocation as (cpu, memory_gb)."""
    total_cpu = 0
    total_memory = 0
    for namespace in namespaces:
        cpu, memory_gb = _get_resource_spec_values(namespace.get("ElasticResourceSpec"))
        if cpu is None and memory_gb is None:
            cpu, memory_gb = _get_resource_spec_values(namespace.get("ResourceSpec"))
        total_cpu += int(cpu or 0)
        total_memory += int(memory_gb or 0)
    return total_cpu, total_memory


def create_instance(args):
    """Create a new Flink instance."""
    try:
        if not args.confirm:
            result = {
                "success": False,
                "operation": "create",
                "confirmation_check": _confirmation_audit(args.confirm),
                "error": {
                    "code": "SafetyCheckRequired",
                    "message": (
                        "Creating an instance is a cost-incurring operation. "
                        "Please confirm by adding --confirm flag."
                    ),
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        if not args.region_id:
            raise ValueError("region_id is required. Please specify the region.")

        has_cpu = args.cpu is not None
        has_memory = args.memory_gb is not None
        has_cu = args.cu_count is not None

        if has_cpu != has_memory:
            result = {
                "success": False,
                "operation": "create",
                "confirmation_check": _confirmation_audit(args.confirm),
                "error": {
                    "code": "MissingParameter",
                    "message": "--cpu and --memory_gb must be provided together.",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        if not (has_cu or (has_cpu and has_memory)):
            result = {
                "success": False,
                "operation": "create",
                "confirmation_check": _confirmation_audit(args.confirm),
                "error": {
                    "code": "MissingParameter",
                    "message": (
                        "Must specify --cpu and --memory_gb, or --cu_count parameter"
                    ),
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        cpu = args.cpu if has_cpu else args.cu_count
        memory_gb = args.memory_gb if has_memory else args.cu_count * 4
        charge_type = "POST" if args.instance_type == "PayAsYouGo" else "PRE"

        client = FlinkClient(region_id=args.region_id)

        existing_instance = find_instance_by_name(client, args.region_id, args.name)
        if existing_instance:
            existing_charge_type = existing_instance.get("ChargeType")
            existing_cpu, existing_memory = _get_resource_spec_values(
                existing_instance.get("ResourceSpec", {})
            )
            if (
                existing_charge_type == charge_type
                and existing_cpu == cpu
                and existing_memory == memory_gb
            ):
                result = {
                    "success": True,
                    "operation": "create",
                    "confirmation_check": _confirmation_audit(args.confirm),
                    "idempotent_noop": True,
                    "message": (
                        f"Instance '{args.name}' already exists with the same "
                        "configuration. Skipped duplicate create."
                    ),
                    "data": {"ExistingInstance": existing_instance},
                    "request_id": "",
                }
                print(json.dumps(result, indent=2))
                return 0

            result = {
                "success": False,
                "operation": "create",
                "confirmation_check": _confirmation_audit(args.confirm),
                "error": {
                    "code": "InstanceNameConflict",
                    "message": (
                        f"Instance name '{args.name}' already exists with a different "
                        "configuration. Refuse to create to avoid non-idempotent "
                        "side effects."
                    ),
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        request = foas_models.CreateInstanceRequest(
            region=args.region_id,
            instance_name=args.name,
            charge_type=charge_type,
            v_switch_ids=[args.vswitch_id],
            vpc_id=args.vpc_id,
            resource_spec=foas_models.CreateInstanceRequestResourceSpec(
                cpu=cpu, memory_gb=memory_gb
            ),
            storage=foas_models.CreateInstanceRequestStorage(fully_managed=True),
        )

        if args.zone_id:
            request.zone_id = args.zone_id
        if args.auto_renew:
            request.auto_renew = True
        if args.period:
            request.duration = args.period
            request.pricing_cycle = "Month"

        response = client.call_api("create_instance", request)
        result = {
            "success": True,
            "operation": "create",
            "confirmation_check": _confirmation_audit(args.confirm),
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as exc:
        result = {
            "success": False,
            "operation": "create",
            "confirmation_check": _confirmation_audit(getattr(args, "confirm", False)),
            "error": {"code": type(exc).__name__, "message": str(exc)},
        }
        print(json.dumps(result, indent=2))
        return 1


def describe_instances(args):
    """Describe Flink instances."""
    try:
        if not args.region_id:
            raise ValueError("region_id is required. Please specify the region.")
        client = FlinkClient(region_id=args.region_id)
        request = foas_models.DescribeInstancesRequest(region=args.region_id)
        response = client.call_api("describe_instances", request)

        result = {
            "success": True,
            "operation": "describe",
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as exc:
        result = {
            "success": False,
            "operation": "describe",
            "error": {"code": type(exc).__name__, "message": str(exc)},
        }
        print(json.dumps(result, indent=2))
        return 1


def describe_regions(_args):
    """Describe supported regions."""
    try:
        client = FlinkClient(region_id="cn-beijing")
        response = client.call_api("describe_supported_regions")

        result = {
            "success": True,
            "operation": "describe_regions",
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as exc:
        result = {
            "success": False,
            "operation": "describe_regions",
            "error": {"code": type(exc).__name__, "message": str(exc)},
        }
        print(json.dumps(result, indent=2))
        return 1


def describe_zones(args):
    """Describe supported zones."""
    try:
        if not args.region_id:
            raise ValueError("region_id is required. Please specify the region.")

        client = FlinkClient(region_id=args.region_id)
        request = foas_models.DescribeSupportedZonesRequest(region=args.region_id)
        response = client.call_api("describe_supported_zones", request)

        result = {
            "success": True,
            "operation": "describe_zones",
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as exc:
        result = {
            "success": False,
            "operation": "describe_zones",
            "error": {"code": type(exc).__name__, "message": str(exc)},
        }
        print(json.dumps(result, indent=2))
        return 1


def create_namespace(args):
    """Create a namespace."""
    try:
        if not args.confirm:
            result = {
                "success": False,
                "operation": "create_namespace",
                "confirmation_check": _confirmation_audit(args.confirm),
                "error": {
                    "code": "SafetyCheckRequired",
                    "message": (
                        "Creating a namespace consumes cluster resources. "
                        "Please confirm by adding --confirm flag."
                    ),
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        has_cpu = args.cpu is not None
        has_memory = args.memory_gb is not None
        if has_cpu != has_memory:
            result = {
                "success": False,
                "operation": "create_namespace",
                "confirmation_check": _confirmation_audit(args.confirm),
                "error": {
                    "code": "MissingParameter",
                    "message": (
                        "--cpu and --memory_gb must be provided together when "
                        "specifying namespace resources."
                    ),
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        client = FlinkClient(region_id=args.region_id)
        existing_namespace = find_namespace_by_name(
            client, args.region_id, args.instance_id, args.name
        )
        if existing_namespace:
            existing_cpu, existing_memory = _get_resource_spec_values(
                existing_namespace.get("ElasticResourceSpec")
            )
            if existing_cpu is None and existing_memory is None:
                existing_cpu, existing_memory = _get_resource_spec_values(
                    existing_namespace.get("ResourceSpec")
                )

            if not has_cpu and not has_memory:
                result = {
                    "success": True,
                    "operation": "create_namespace",
                    "confirmation_check": _confirmation_audit(args.confirm),
                    "idempotent_noop": True,
                    "message": (
                        f"Namespace '{args.name}' already exists. "
                        "Skipped duplicate create."
                    ),
                    "data": {"ExistingNamespace": existing_namespace},
                    "request_id": "",
                }
                print(json.dumps(result, indent=2))
                return 0

            if existing_cpu == args.cpu and existing_memory == args.memory_gb:
                result = {
                    "success": True,
                    "operation": "create_namespace",
                    "confirmation_check": _confirmation_audit(args.confirm),
                    "idempotent_noop": True,
                    "message": (
                        f"Namespace '{args.name}' already exists with the same "
                        "resource specification. Skipped duplicate create."
                    ),
                    "data": {"ExistingNamespace": existing_namespace},
                    "request_id": "",
                }
                print(json.dumps(result, indent=2))
                return 0

            result = {
                "success": False,
                "operation": "create_namespace",
                "confirmation_check": _confirmation_audit(args.confirm),
                "error": {
                    "code": "NamespaceConflict",
                    "message": (
                        f"Namespace '{args.name}' already exists with a different "
                        "configuration. Refuse to create to avoid non-idempotent "
                        "side effects."
                    ),
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        if not has_cpu and not has_memory:
            result = {
                "success": False,
                "operation": "create_namespace",
                "confirmation_check": _confirmation_audit(args.confirm),
                "error": {
                    "code": "MissingParameter",
                    "message": (
                        "New namespace creation requires explicit --cpu and --memory_gb. "
                        "If the target namespace already exists, reuse the same --name to "
                        "perform an idempotent create."
                    ),
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        instance = find_instance_by_id(client, args.region_id, args.instance_id)
        if not instance:
            result = {
                "success": False,
                "operation": "create_namespace",
                "confirmation_check": _confirmation_audit(args.confirm),
                "error": {
                    "code": "NamespaceNotFound",
                    "message": (
                        f"Instance '{args.instance_id}' was not found in region "
                        f"'{args.region_id}'."
                    ),
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        total_cpu, total_memory = _get_resource_spec_values(instance.get("ResourceSpec", {}))
        total_cpu = int(total_cpu or 0)
        total_memory = int(total_memory or 0)
        used_cpu, used_memory = _sum_namespace_allocations(
            list_namespaces(client, args.region_id, args.instance_id)
        )
        available_cpu = max(total_cpu - used_cpu, 0)
        available_memory = max(total_memory - used_memory, 0)

        if args.cpu > available_cpu or args.memory_gb > available_memory:
            result = {
                "success": False,
                "operation": "create_namespace",
                "confirmation_check": _confirmation_audit(args.confirm),
                "error": {
                    "code": "InsufficientResources",
                    "message": (
                        "Requested namespace resources exceed available capacity. "
                        f"requested=({args.cpu} CPU, {args.memory_gb} GB), "
                        f"available=({available_cpu} CPU, {available_memory} GB), "
                        f"instance_total=({total_cpu} CPU, {total_memory} GB), "
                        f"allocated=({used_cpu} CPU, {used_memory} GB). "
                        "This skill does not support instance scale-up. "
                        "Please manually expand or reallocate instance resources, "
                        "then retry create_namespace."
                    ),
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        request = foas_models.CreateNamespaceRequest(
            instance_id=args.instance_id,
            region=args.region_id,
            namespace=args.name,
        )
        if has_cpu and has_memory:
            request.resource_spec = foas_models.CreateNamespaceRequestResourceSpec(
                cpu=args.cpu, memory_gb=args.memory_gb
            )

        response = client.call_api("create_namespace", request)
        result = {
            "success": True,
            "operation": "create_namespace",
            "confirmation_check": _confirmation_audit(args.confirm),
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as exc:
        result = {
            "success": False,
            "operation": "create_namespace",
            "confirmation_check": _confirmation_audit(getattr(args, "confirm", False)),
            "error": {"code": type(exc).__name__, "message": str(exc)},
        }
        print(json.dumps(result, indent=2))
        return 1


def describe_namespaces(args):
    """Describe namespaces."""
    try:
        client = FlinkClient(region_id=args.region_id)
        request = foas_models.DescribeNamespacesRequest(
            instance_id=args.instance_id, region=args.region_id
        )
        response = client.call_api("describe_namespaces", request)

        result = {
            "success": True,
            "operation": "describe_namespaces",
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as exc:
        result = {
            "success": False,
            "operation": "describe_namespaces",
            "error": {"code": type(exc).__name__, "message": str(exc)},
        }
        print(json.dumps(result, indent=2))
        return 1


def list_tags(args):
    """List tags for resources."""
    try:
        if not args.region_id:
            raise ValueError("region_id is required. Please specify the region.")
        client = FlinkClient(region_id=args.region_id)

        request = foas_models.ListTagResourcesRequest(
            region_id=args.region_id, resource_type=args.resource_type
        )
        if args.resource_ids:
            resource_ids = (
                args.resource_ids.split(",")
                if "," in args.resource_ids
                else [args.resource_ids]
            )
            request.resource_id = resource_ids

        response = client.call_api("list_tag_resources", request)
        result = {
            "success": True,
            "operation": "list_tags",
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as exc:
        result = {
            "success": False,
            "operation": "list_tags",
            "error": {"code": type(exc).__name__, "message": str(exc)},
        }
        print(json.dumps(result, indent=2))
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Flink Instance Manager (API 2021-10-28)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    create_parser = subparsers.add_parser("create", help="Create a new Flink instance")
    create_parser.add_argument("--region_id", required=True, help="Region ID")
    create_parser.add_argument("--name", required=True, help="Instance name")
    create_parser.add_argument(
        "--instance_type",
        required=True,
        choices=["Subscription", "PayAsYouGo"],
        help="Billing type",
    )
    create_parser.add_argument(
        "--zone_id", help="Zone ID (optional, passed through when provided)"
    )
    create_parser.add_argument("--vswitch_id", required=True, help="VSwitch ID")
    create_parser.add_argument("--vpc_id", required=True, help="VPC ID")
    create_parser.add_argument(
        "--cu_count", type=int, help="Compute unit count (1 CU = 1 Core + 4 GB)"
    )
    create_parser.add_argument(
        "--cpu", type=int, help="CPU in Core (override cu_count)"
    )
    create_parser.add_argument(
        "--memory_gb", type=int, help="Memory in GB (override cu_count)"
    )
    create_parser.add_argument("--auto_renew", action="store_true", help="Auto-renew")
    create_parser.add_argument(
        "--period", type=int, choices=[1, 2, 3, 6, 12], help="Period (months)"
    )
    create_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm creation (cost-incurring operation)",
    )
    create_parser.set_defaults(func=create_instance)

    describe_parser = subparsers.add_parser("describe", help="Describe instances")
    describe_parser.add_argument("--region_id", required=True, help="Region ID")
    describe_parser.set_defaults(func=describe_instances)

    regions_parser = subparsers.add_parser("describe_regions", help="Describe regions")
    regions_parser.set_defaults(func=describe_regions)

    zones_parser = subparsers.add_parser("describe_zones", help="Describe zones")
    zones_parser.add_argument("--region_id", required=True, help="Region ID")
    zones_parser.set_defaults(func=describe_zones)

    ns_create_parser = subparsers.add_parser(
        "create_namespace", help="Create namespace"
    )
    ns_create_parser.add_argument("--region_id", required=True, help="Region ID")
    ns_create_parser.add_argument("--instance_id", required=True, help="Instance ID")
    ns_create_parser.add_argument("--name", required=True, help="Namespace name")
    ns_create_parser.add_argument("--cpu", type=int, help="CPU in Core (optional)")
    ns_create_parser.add_argument(
        "--memory_gb", type=int, help="Memory in GB (optional)"
    )
    ns_create_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm creation (resource-consuming operation)",
    )
    ns_create_parser.set_defaults(func=create_namespace)

    ns_desc_parser = subparsers.add_parser(
        "describe_namespaces", help="Describe namespaces"
    )
    ns_desc_parser.add_argument("--region_id", required=True, help="Region ID")
    ns_desc_parser.add_argument("--instance_id", required=True, help="Instance ID")
    ns_desc_parser.set_defaults(func=describe_namespaces)

    list_tags_parser = subparsers.add_parser("list_tags", help="List tags")
    list_tags_parser.add_argument("--region_id", required=True, help="Region ID")
    list_tags_parser.add_argument(
        "--resource_type", required=True, help="Resource type"
    )
    list_tags_parser.add_argument("--resource_ids", help="Resource IDs")
    list_tags_parser.set_defaults(func=list_tags)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
