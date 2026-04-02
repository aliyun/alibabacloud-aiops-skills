#!/usr/bin/env python3
"""
Flink Instance Manager - CLI for Alibaba Cloud Flink OpenAPI (2021-10-28)

Usage:
    python instance_ops.py <command> [options]

Commands:
    create              Create a new Flink instance
    describe            Describe instances
    modify_spec         Modify instance specifications (upgrade)
    delete              Delete an instance
    renew               Renew a subscription instance
    convert             Convert billing type
    describe_regions    List supported regions
    describe_zones      List supported zones
    create_namespace    Create a namespace
    describe_namespaces Describe namespaces
    tag_resources       Add tags to resources
    list_tags           List tags for resources
    untag_resources     Remove tags from resources

Authentication:
    Uses Alibaba Cloud default credential chain (RAM role, CLI profile, etc.)

Output:
    JSON to stdout, exit code 0 = success
"""

import argparse
import json
import sys

from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_foasconsole20211028.client import Client
from alibabacloud_foasconsole20211028 import models as foas_models
from alibabacloud_tea_openapi import models as openapi_models
from alibabacloud_tea_util import models as util_models

DEFAULT_CONNECT_TIMEOUT_MS = 10_000
DEFAULT_READ_TIMEOUT_MS = 60_000
DEFAULT_USER_AGENT = "AlibabaCloud-Agent-Skills"
DEFAULT_NAMESPACE_NAME = "default"


class FlinkClient:
    """Flink OpenAPI client (2021-10-28) with automatic authentication."""

    def __init__(self, region_id):
        """
        Initialize Flink client.

        Args:
            region_id: Region ID (required, no default)

        Raises:
            ValueError: If region_id is not provided
        """
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

        # Fallback for SDK methods that do not expose *_with_options.
        method = getattr(self.client, method_name)
        if request is None:
            return method()
        return method(request)


def parse_bool_arg(value):
    """Parse strict boolean CLI argument."""
    lowered = value.strip().lower()
    if lowered in ("1", "true", "yes", "y"):
        return True
    if lowered in ("0", "false", "no", "n"):
        return False
    raise argparse.ArgumentTypeError(
        f"Invalid boolean value '{value}', expected true/false."
    )


def _parse_float(value):
    """Parse value into float; return None when value is missing/invalid."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
    describe_request = foas_models.DescribeInstancesRequest(region=region_id)
    describe_response = client.call_api("describe_instances", describe_request)
    instances = describe_response.body.to_map().get("Instances", [])
    for inst in instances:
        if inst.get("InstanceName") == instance_name:
            return inst
    return None


def _get_namespace_usage(namespace):
    """
    Return namespace usage tuple (cpu, memory_gb, cu), or None if unavailable.
    """
    resource_used = namespace.get("ResourceUsed")
    if not isinstance(resource_used, dict):
        return None
    cpu = _parse_float(resource_used.get("Cpu"))
    memory_gb = _parse_float(resource_used.get("MemoryGB"))
    cu = _parse_float(resource_used.get("Cu"))
    if cpu is None and memory_gb is None and cu is None:
        return None
    return (cpu or 0.0), (memory_gb or 0.0), (cu or 0.0)


def _namespace_has_non_default_associations(namespaces):
    """Check whether instance still has non-default namespaces."""
    for namespace in namespaces:
        namespace_name = namespace.get("Namespace")
        if namespace_name and namespace_name != DEFAULT_NAMESPACE_NAME:
            return True
    return False


def _namespace_elastic_spec(namespace):
    """
    Return preferred namespace spec tuple (cpu, memory_gb) for comparisons.
    """
    elastic_spec = namespace.get("ElasticResourceSpec")
    cpu, memory_gb = _get_resource_spec_values(elastic_spec)
    if cpu is not None and memory_gb is not None:
        return cpu, memory_gb

    resource_spec = namespace.get("ResourceSpec")
    return _get_resource_spec_values(resource_spec)


def _collect_existing_tags(client, region_id, resource_type, resource_ids):
    """
    Return existing tags grouped by resource id.
    """
    request = foas_models.ListTagResourcesRequest(
        region_id=region_id, resource_type=resource_type, resource_id=resource_ids
    )
    response = client.call_api("list_tag_resources", request)
    raw_items = response.body.to_map().get("TagResources", [])
    if not isinstance(raw_items, list):
        raw_items = []

    tag_map = {resource_id: {} for resource_id in resource_ids}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        resource_id = item.get("ResourceId")
        tag_key = item.get("TagKey")
        tag_value = item.get("TagValue")
        if resource_id in tag_map and tag_key:
            tag_map[resource_id][tag_key] = tag_value
    return tag_map


def find_instance_by_id(client, region_id, instance_id):
    """Return instance detail by ID from DescribeInstances result."""
    describe_request = foas_models.DescribeInstancesRequest(region=region_id)
    describe_response = client.call_api("describe_instances", describe_request)
    instances = describe_response.body.to_map().get("Instances", [])
    for inst in instances:
        if inst.get("InstanceId") == instance_id:
            return inst
    return None


def create_instance(args):
    """Create a new Flink instance."""
    try:
        # Safety check: require explicit confirmation for instance creation (cost-incurring operation)
        if not args.confirm:
            result = {
                "success": False,
                "operation": "create",
                "error": {
                    "code": "SafetyCheckRequired",
                    "message": "Creating an instance is a cost-incurring operation. Please confirm by adding --confirm flag.",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        region_id = args.region_id

        # Validate resource parameters: must specify CPU and Memory, defaults are not allowed
        if not hasattr(args, "cpu") or not args.cpu:
            if not hasattr(args, "cu_count") or not args.cu_count:
                result = {
                    "success": False,
                    "operation": "create",
                    "error": {
                        "code": "MissingParameter",
                        "message": "Must specify --cpu and --memory_gb, or --cu_count parameter",
                    },
                }
                print(json.dumps(result, indent=2))
                return 1

        client = FlinkClient(region_id=region_id)

        # Map instance_type to charge_type
        # PayAsYouGo -> POST, Subscription -> PRE
        charge_type = "POST" if args.instance_type == "PayAsYouGo" else "PRE"

        # Build resource spec
        # CU (Compute Unit) conversion: 1 CU = 1 Core + 4 GB Memory
        # This is the standard resource ratio for Flink instances
        if hasattr(args, "cpu") and args.cpu:
            # Use --cpu and --memory_gb parameters
            if not hasattr(args, "memory_gb") or not args.memory_gb:
                result = {
                    "success": False,
                    "operation": "create",
                    "error": {
                        "code": "MissingParameter",
                        "message": "When specifying --cpu, --memory_gb is also required",
                    },
                }
                print(json.dumps(result, indent=2))
                return 1
            cpu = args.cpu
            memory_gb = args.memory_gb
        elif hasattr(args, "cu_count") and args.cu_count:
            # Use --cu_count parameter (1 CU = 1 Core + 4 GB)
            cpu = args.cu_count
            memory_gb = args.cu_count * 4
        else:
            # Should not reach here, already checked above
            result = {
                "success": False,
                "operation": "create",
                "error": {
                    "code": "MissingParameter",
                    "message": "Must specify either --cpu and --memory_gb, or --cu_count parameter",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        # Idempotency check (check-then-act): same name + same spec + same charge type.
        existing_instance = find_instance_by_name(client, region_id, args.name)
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
                    "idempotent_noop": True,
                    "message": f"Instance '{args.name}' already exists with the same configuration. Skipped duplicate create.",
                    "data": {"ExistingInstance": existing_instance},
                    "request_id": "",
                }
                print(json.dumps(result, indent=2))
                return 0

            result = {
                "success": False,
                "operation": "create",
                "error": {
                    "code": "InstanceNameConflict",
                    "message": (
                        f"Instance name '{args.name}' already exists with a different configuration. "
                        "Refuse to create to avoid non-idempotent side effects."
                    ),
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        resource_spec = foas_models.CreateInstanceRequestResourceSpec(
            cpu=cpu, memory_gb=memory_gb
        )

        # Build storage config (required)
        storage = foas_models.CreateInstanceRequestStorage(fully_managed=True)

        request = foas_models.CreateInstanceRequest(
            region=region_id,
            instance_name=args.name,
            charge_type=charge_type,
            v_switch_ids=[args.vswitch_id],
            vpc_id=args.vpc_id,
            resource_spec=resource_spec,
            storage=storage,
        )

        # Optional parameters
        if hasattr(args, "zone_id") and args.zone_id:
            request.zone_id = args.zone_id
        if hasattr(args, "auto_renew") and args.auto_renew:
            request.auto_renew = args.auto_renew
        if hasattr(args, "period") and args.period:
            request.duration = args.period
            request.pricing_cycle = "Month"

        response = client.call_api("create_instance", request)

        result = {
            "success": True,
            "operation": "create",
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as e:
        result = {
            "success": False,
            "operation": "create",
            "error": {"code": type(e).__name__, "message": str(e)},
        }
        print(json.dumps(result, indent=2))
        return 1


def describe_instances(args):
    """Describe Flink instances."""
    try:
        if not args.region_id:
            raise ValueError("region_id is required. Please specify the region.")

        region_id = args.region_id
        client = FlinkClient(region_id=region_id)

        request = foas_models.DescribeInstancesRequest(region=region_id)

        response = client.call_api("describe_instances", request)

        result = {
            "success": True,
            "operation": "describe",
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as e:
        result = {
            "success": False,
            "operation": "describe",
            "error": {"code": type(e).__name__, "message": str(e)},
        }
        print(json.dumps(result, indent=2))
        return 1


def modify_instance_spec(args):
    """Modify instance specifications (upgrade)."""
    try:
        if not args.confirm_price:
            result = {
                "success": False,
                "operation": "modify_spec",
                "error": {
                    "code": "SafetyCheckRequired",
                    "message": "Price confirmation required. Use --confirm_price flag.",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        # Region is required
        if not hasattr(args, "region_id") or not args.region_id:
            result = {
                "success": False,
                "operation": "modify_spec",
                "error": {
                    "code": "MissingParameter",
                    "message": "--region_id is required for modify_spec operation",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        client = FlinkClient(region_id=args.region_id)

        # Build resource spec for modification
        # args.new_cu_count is required, so we don't need fallback logic
        new_cpu = args.new_cu_count
        new_memory = args.new_cu_count * 4

        instance_info = find_instance_by_id(client, args.region_id, args.instance_id)
        if not instance_info:
            result = {
                "success": False,
                "operation": "modify_spec",
                "error": {
                    "code": "InstanceNotFound",
                    "message": f"Instance {args.instance_id} not found in region {args.region_id}",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        current_cpu, current_memory = _get_resource_spec_values(
            instance_info.get("ResourceSpec", {})
        )
        if current_cpu == new_cpu and current_memory == new_memory:
            result = {
                "success": True,
                "operation": "modify_spec",
                "idempotent_noop": True,
                "message": "Instance already has the target resource specification. Skipped duplicate modify.",
                "data": {"ExistingInstance": instance_info},
                "request_id": "",
            }
            print(json.dumps(result, indent=2))
            return 0

        resource_spec = foas_models.ModifyInstanceSpecRequestResourceSpec(
            cpu=new_cpu, memory_gb=new_memory
        )

        request = foas_models.ModifyInstanceSpecRequest(
            instance_id=args.instance_id,
            region=args.region_id,
            resource_spec=resource_spec,
        )

        response = client.call_api("modify_instance_spec", request)

        result = {
            "success": True,
            "operation": "modify_spec",
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as e:
        result = {
            "success": False,
            "operation": "modify_spec",
            "error": {"code": type(e).__name__, "message": str(e)},
        }
        print(json.dumps(result, indent=2))
        return 1


def delete_instance(args):
    """Delete a Flink instance."""
    try:
        if not args.region_id:
            result = {
                "success": False,
                "operation": "delete",
                "error": {
                    "code": "MissingParameter",
                    "message": "--region_id is required for delete operation",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        # If force_confirmation is not provided, ask for user confirmation
        if not args.force_confirmation:
            # First, get instance details to show to user
            try:
                client = FlinkClient(region_id=args.region_id)
                instance_info = find_instance_by_id(
                    client, args.region_id, args.instance_id
                )

                if instance_info:
                    print(
                        f"\n⚠️  WARNING: You are about to DELETE the following Flink instance:"
                    )
                    print(
                        f"\n  Instance ID:   {instance_info.get('InstanceId', 'N/A')}"
                    )
                    print(
                        f"  Instance Name: {instance_info.get('InstanceName', 'N/A')}"
                    )
                    print(f"  Region:        {instance_info.get('Region', 'N/A')}")
                    print(
                        f"  Charge Type:   {instance_info.get('ChargeType', 'N/A')}"
                    )
                    print(
                        f"  Status:        {instance_info.get('ClusterStatus', 'N/A')}"
                    )
                    print(
                        f"  Resource Spec: CPU {instance_info.get('ResourceSpec', {}).get('Cpu', 'N/A')} Core, Memory {instance_info.get('ResourceSpec', {}).get('MemoryGB', 'N/A')} GB"
                    )
                    if instance_info.get("ChargeType") != "POST":
                        print(
                            "\n⚠️  NOTE: Official API only supports deleting POST (PayAsYouGo) instances."
                        )
                    print(
                        f"\n⚠️  This action CANNOT be undone. All data and configurations will be permanently lost."
                    )
                    print(
                        f"\n📝 To confirm deletion, please run the command with --force_confirmation flag:"
                    )
                    print(
                        f"   python scripts/instance_ops.py delete --instance_id {args.instance_id} --region_id {args.region_id} --force_confirmation\n"
                    )
                else:
                    print(
                        f"\n⚠️  WARNING: You are about to DELETE instance {args.instance_id}"
                    )
                    print(f"⚠️  This action CANNOT be undone.")
                    print(
                        f"\n📝 To confirm deletion, please run the command with --force_confirmation flag:"
                    )
                    print(
                        f"   python scripts/instance_ops.py delete --instance_id {args.instance_id} --region_id <region> --force_confirmation\n"
                    )

            except Exception:
                # If we can't get instance details, still show warning
                print(
                    f"\n⚠️  WARNING: You are about to DELETE instance {args.instance_id}"
                )
                print(f"⚠️  This action CANNOT be undone.")
                print(
                    f"\n📝 To confirm deletion, please run the command with --force_confirmation flag:"
                )
                print(
                    f"   python scripts/instance_ops.py delete --instance_id {args.instance_id} --region_id <region> --force_confirmation\n"
                )

            return 1

        # Force confirmation provided, enforce API constraints before deletion
        client = FlinkClient(region_id=args.region_id)
        instance_info = find_instance_by_id(client, args.region_id, args.instance_id)
        if not instance_info:
            result = {
                "success": True,
                "operation": "delete",
                "idempotent_noop": True,
                "message": f"Instance {args.instance_id} does not exist in region {args.region_id}. Nothing to delete.",
                "data": {
                    "InstanceId": args.instance_id,
                    "RegionId": args.region_id,
                },
                "request_id": "",
            }
            print(json.dumps(result, indent=2))
            return 0

        if instance_info.get("ChargeType") != "POST":
            result = {
                "success": False,
                "operation": "delete",
                "error": {
                    "code": "UnsupportedChargeType",
                    "message": "DeleteInstance only supports POST (PayAsYouGo) instances.",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        namespaces = list_namespaces(client, args.region_id, args.instance_id)
        if _namespace_has_non_default_associations(namespaces):
            linked_namespaces = [
                ns.get("Namespace")
                for ns in namespaces
                if ns.get("Namespace") and ns.get("Namespace") != DEFAULT_NAMESPACE_NAME
            ]
            result = {
                "success": False,
                "operation": "delete",
                "error": {
                    "code": "NamespaceAssociationExists",
                    "message": (
                        "Delete is blocked because the instance still has associated namespaces. "
                        "Delete all non-default namespaces first."
                    ),
                    "details": {"linked_namespaces": linked_namespaces},
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        request = foas_models.DeleteInstanceRequest(
            instance_id=args.instance_id, region=args.region_id
        )

        response = client.call_api("delete_instance", request)

        result = {
            "success": True,
            "operation": "delete",
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as e:
        result = {
            "success": False,
            "operation": "delete",
            "error": {"code": type(e).__name__, "message": str(e)},
        }
        print(json.dumps(result, indent=2))
        return 1


def renew_instance(args):
    """Renew a subscription instance."""
    try:
        # Safety check: require explicit confirmation for renewal (cost-incurring operation)
        if not args.confirm:
            result = {
                "success": False,
                "operation": "renew",
                "error": {
                    "code": "SafetyCheckRequired",
                    "message": "Renewal is a cost-incurring operation. Please confirm by adding --confirm flag.",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        if not args.region_id:
            raise ValueError("region_id is required. Please specify the region.")
        region_id = args.region_id
        client = FlinkClient(region_id=region_id)
        instance_info = find_instance_by_id(client, region_id, args.instance_id)
        if not instance_info:
            result = {
                "success": False,
                "operation": "renew",
                "error": {
                    "code": "InstanceNotFound",
                    "message": f"Instance {args.instance_id} not found in region {region_id}",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        if instance_info.get("ChargeType") != "PRE":
            result = {
                "success": False,
                "operation": "renew",
                "error": {
                    "code": "UnsupportedChargeType",
                    "message": "RenewInstance only supports PRE (Subscription) instances.",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        request = foas_models.RenewInstanceRequest(
            instance_id=args.instance_id,
            region=region_id,
            duration=args.period,
            pricing_cycle="Month",
        )

        response = client.call_api("renew_instance", request)

        result = {
            "success": True,
            "operation": "renew",
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as e:
        result = {
            "success": False,
            "operation": "renew",
            "error": {"code": type(e).__name__, "message": str(e)},
        }
        print(json.dumps(result, indent=2))
        return 1


def convert_instance(args):
    """Convert instance billing type (PrePaid <-> PostPaid)."""
    try:
        if not args.confirm_price:
            result = {
                "success": False,
                "operation": "convert",
                "error": {
                    "code": "SafetyCheckRequired",
                    "message": "Price confirmation required. Use --confirm_price flag.",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        # Region is required
        if not hasattr(args, "region_id") or not args.region_id:
            result = {
                "success": False,
                "operation": "convert",
                "error": {
                    "code": "MissingParameter",
                    "message": "--region_id is required for convert operation",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        client = FlinkClient(region_id=args.region_id)
        instance_info = find_instance_by_id(client, args.region_id, args.instance_id)
        if not instance_info:
            result = {
                "success": False,
                "operation": "convert",
                "error": {
                    "code": "InstanceNotFound",
                    "message": f"Instance {args.instance_id} not found in region {args.region_id}",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        target_charge_type = "PRE" if args.target_type == "Subscription" else "POST"
        if instance_info.get("ChargeType") == target_charge_type:
            result = {
                "success": True,
                "operation": "convert",
                "idempotent_noop": True,
                "message": f"Instance is already {args.target_type}. Skipped duplicate convert.",
                "data": {"ExistingInstance": instance_info},
                "request_id": "",
            }
            print(json.dumps(result, indent=2))
            return 0

        # Determine conversion direction based on target_type
        # PayAsYouGo (PostPaid) -> Subscription (PrePaid): use ConvertInstanceRequest
        # Subscription (PrePaid) -> PayAsYouGo (PostPaid): use ConvertPrepayInstanceRequest
        if args.target_type == "Subscription":
            # Converting PostPaid -> PrePaid
            # First get namespace configurations
            describe_request = foas_models.DescribeNamespacesRequest(
                instance_id=args.instance_id, region=args.region_id
            )
            describe_response = client.call_api("describe_namespaces", describe_request)
            namespaces_data = describe_response.body.to_map().get("Namespaces", [])

            # Build namespace_resource_specs from existing namespaces
            namespace_resource_specs = []
            for ns in namespaces_data:
                ns_resource_spec = ns.get("ResourceSpec", {})
                if (
                    not ns_resource_spec
                    or "Cpu" not in ns_resource_spec
                    or "MemoryGB" not in ns_resource_spec
                ):
                    result = {
                        "success": False,
                        "operation": "convert",
                        "error": {
                            "code": "InvalidNamespaceSpec",
                            "message": f"Namespace '{ns.get('Namespace', 'unknown')}' has invalid ResourceSpec",
                        },
                    }
                    print(json.dumps(result, indent=2))
                    return 1
                ns_spec = foas_models.ConvertInstanceRequestNamespaceResourceSpecs(
                    namespace=ns.get("Namespace"),
                    resource_spec=foas_models.ConvertInstanceRequestNamespaceResourceSpecsResourceSpec(
                        cpu=ns_resource_spec.get("Cpu"),
                        memory_gb=ns_resource_spec.get("MemoryGB"),
                    ),
                )
                namespace_resource_specs.append(ns_spec)

            request = foas_models.ConvertInstanceRequest(
                instance_id=args.instance_id,
                region=args.region_id,
                pricing_cycle="Month",
                duration=getattr(args, "period", 1) or 1,
                is_auto_renew=getattr(args, "auto_renew", False),
                namespace_resource_specs=namespace_resource_specs,
            )
            response = client.call_api("convert_instance", request)
        else:
            # Converting PrePaid -> PostPaid
            request = foas_models.ConvertPrepayInstanceRequest(
                instance_id=args.instance_id, region=args.region_id
            )
            response = client.call_api("convert_prepay_instance", request)

        result = {
            "success": True,
            "operation": "convert",
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as e:
        result = {
            "success": False,
            "operation": "convert",
            "error": {"code": type(e).__name__, "message": str(e)},
        }
        print(json.dumps(result, indent=2))
        return 1


def describe_regions(args):
    """Describe supported regions."""
    try:
        # describe_regions is a global API, use a default region for client initialization
        client = FlinkClient(region_id="cn-beijing")

        # This API doesn't require request model or runtime
        response = client.call_api("describe_supported_regions")

        result = {
            "success": True,
            "operation": "describe_regions",
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as e:
        result = {
            "success": False,
            "operation": "describe_regions",
            "error": {"code": type(e).__name__, "message": str(e)},
        }
        print(json.dumps(result, indent=2))
        return 1


def describe_zones(args):
    """Describe supported zones."""
    try:
        if not args.region_id:
            raise ValueError("region_id is required. Please specify the region.")
        region_id = args.region_id
        client = FlinkClient(region_id=region_id)

        # This API requires a request model with region parameter
        request = foas_models.DescribeSupportedZonesRequest(region=region_id)

        response = client.call_api("describe_supported_zones", request)

        result = {
            "success": True,
            "operation": "describe_zones",
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as e:
        result = {
            "success": False,
            "operation": "describe_zones",
            "error": {"code": type(e).__name__, "message": str(e)},
        }
        print(json.dumps(result, indent=2))
        return 1


def create_namespace(args):
    """Create a namespace."""
    try:
        # Safety check: require explicit confirmation for namespace creation (resource-consuming operation)
        if not args.confirm:
            result = {
                "success": False,
                "operation": "create_namespace",
                "error": {
                    "code": "SafetyCheckRequired",
                    "message": "Creating a namespace consumes cluster resources. Please confirm by adding --confirm flag.",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        # ResourceSpec is optional in OpenAPI; if provided, CPU and Memory must both be set
        has_cpu = hasattr(args, "cpu") and args.cpu is not None
        has_memory = hasattr(args, "memory_gb") and args.memory_gb is not None
        if has_cpu != has_memory:
            result = {
                "success": False,
                "operation": "create_namespace",
                "error": {
                    "code": "MissingParameter",
                    "message": "--cpu and --memory_gb must be provided together when specifying namespace resources.",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        client = FlinkClient(region_id=args.region_id)
        existing_namespace = find_namespace_by_name(
            client, args.region_id, args.instance_id, args.name
        )
        if existing_namespace:
            existing_cpu, existing_memory = _namespace_elastic_spec(existing_namespace)
            if not has_cpu and not has_memory:
                result = {
                    "success": True,
                    "operation": "create_namespace",
                    "idempotent_noop": True,
                    "message": f"Namespace '{args.name}' already exists. Skipped duplicate create.",
                    "data": {"ExistingNamespace": existing_namespace},
                    "request_id": "",
                }
                print(json.dumps(result, indent=2))
                return 0

            if existing_cpu == args.cpu and existing_memory == args.memory_gb:
                result = {
                    "success": True,
                    "operation": "create_namespace",
                    "idempotent_noop": True,
                    "message": (
                        f"Namespace '{args.name}' already exists with the same resource specification. "
                        "Skipped duplicate create."
                    ),
                    "data": {"ExistingNamespace": existing_namespace},
                    "request_id": "",
                }
                print(json.dumps(result, indent=2))
                return 0

            result = {
                "success": False,
                "operation": "create_namespace",
                "error": {
                    "code": "NamespaceConflict",
                    "message": (
                        f"Namespace '{args.name}' already exists with a different configuration. "
                        "Refuse to create to avoid non-idempotent side effects."
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
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as e:
        result = {
            "success": False,
            "operation": "create_namespace",
            "error": {"code": type(e).__name__, "message": str(e)},
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

    except Exception as e:
        result = {
            "success": False,
            "operation": "describe_namespaces",
            "error": {"code": type(e).__name__, "message": str(e)},
        }
        print(json.dumps(result, indent=2))
        return 1


def delete_namespace(args):
    """Delete a namespace."""
    try:
        # Safety check: require explicit confirmation for namespace deletion (destructive operation)
        if not args.confirm:
            result = {
                "success": False,
                "operation": "delete_namespace",
                "error": {
                    "code": "SafetyCheckRequired",
                    "message": "Deleting a namespace is a destructive operation. Please confirm by adding --confirm flag.",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        client = FlinkClient(region_id=args.region_id)
        instance_info = find_instance_by_id(client, args.region_id, args.instance_id)
        if not instance_info:
            result = {
                "success": True,
                "operation": "delete_namespace",
                "idempotent_noop": True,
                "message": (
                    f"Instance {args.instance_id} does not exist in region {args.region_id}. "
                    "Nothing to delete."
                ),
                "data": {
                    "InstanceId": args.instance_id,
                    "RegionId": args.region_id,
                },
                "request_id": "",
            }
            print(json.dumps(result, indent=2))
            return 0

        namespace_info = find_namespace_by_name(
            client, args.region_id, args.instance_id, args.name
        )
        if not namespace_info:
            result = {
                "success": True,
                "operation": "delete_namespace",
                "idempotent_noop": True,
                "message": (
                    f"Namespace '{args.name}' does not exist in instance {args.instance_id}. "
                    "Nothing to delete."
                ),
                "data": {
                    "InstanceId": args.instance_id,
                    "Namespace": args.name,
                    "RegionId": args.region_id,
                },
                "request_id": "",
            }
            print(json.dumps(result, indent=2))
            return 0

        usage = _get_namespace_usage(namespace_info)
        if usage is None and not args.confirm_no_running_jobs:
            result = {
                "success": False,
                "operation": "delete_namespace",
                "error": {
                    "code": "PrecheckRequired",
                    "message": (
                        "Cannot verify running workload status from namespace usage metrics. "
                        "Please confirm manual job precheck with --confirm_no_running_jobs."
                    ),
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        if usage is not None:
            used_cpu, used_memory, used_cu = usage
            if used_cpu > 0 or used_memory > 0 or used_cu > 0:
                result = {
                    "success": False,
                    "operation": "delete_namespace",
                    "error": {
                        "code": "NamespaceInUse",
                        "message": (
                            "Namespace appears to have active workload resources in use. "
                            "Stop running jobs and wait for usage to drop to zero before deletion."
                        ),
                        "details": {
                            "used_cpu": used_cpu,
                            "used_memory_gb": used_memory,
                            "used_cu": used_cu,
                        },
                    },
                }
                print(json.dumps(result, indent=2))
                return 1

        request = foas_models.DeleteNamespaceRequest(
            instance_id=args.instance_id,
            region=args.region_id,
            namespace=args.name,
        )

        response = client.call_api("delete_namespace", request)

        result = {
            "success": True,
            "operation": "delete_namespace",
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as e:
        result = {
            "success": False,
            "operation": "delete_namespace",
            "error": {"code": type(e).__name__, "message": str(e)},
        }
        print(json.dumps(result, indent=2))
        return 1


def modify_namespace_spec(args):
    """Modify namespace specifications."""
    try:
        # Safety check: require explicit confirmation for namespace modification (resource-changing operation)
        if not args.confirm:
            result = {
                "success": False,
                "operation": "modify_namespace_spec",
                "error": {
                    "code": "SafetyCheckRequired",
                    "message": "Modifying namespace specifications is a resource-changing operation. Please confirm by adding --confirm flag.",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        if args.ha is None:
            result = {
                "success": False,
                "operation": "modify_namespace_spec",
                "error": {
                    "code": "MissingParameter",
                    "message": "--ha is required for modify_namespace_spec. Please clarify whether namespace HA should be true or false.",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        client = FlinkClient(region_id=args.region_id)

        # Guardrail: modify only existing namespace; never auto-create on modify path
        ns_request = foas_models.DescribeNamespacesRequest(
            instance_id=args.instance_id, region=args.region_id
        )
        ns_response = client.call_api("describe_namespaces", ns_request)
        namespaces = ns_response.body.to_map().get("Namespaces", [])
        namespace_info = next(
            (ns for ns in namespaces if ns.get("Namespace") == args.name), None
        )
        if not namespace_info:
            result = {
                "success": False,
                "operation": "modify_namespace_spec",
                "error": {
                    "code": "NamespaceNotFound",
                    "message": f"Namespace '{args.name}' does not exist in instance {args.instance_id}. Refusing to auto-create namespace during modify operation; explicit user confirmation is required for create_namespace.",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        current_cpu, current_memory = _namespace_elastic_spec(namespace_info)
        guaranteed_spec = namespace_info.get("GuaranteedResourceSpec", {})
        current_guaranteed_cpu, current_guaranteed_memory = _get_resource_spec_values(
            guaranteed_spec
        )
        current_ha = namespace_info.get("Ha")

        same_elastic = current_cpu == args.cpu and current_memory == args.memory_gb
        same_guaranteed = (
            (args.guaranteed_cpu is None and args.guaranteed_memory_gb is None)
            or (
                current_guaranteed_cpu == args.guaranteed_cpu
                and current_guaranteed_memory == args.guaranteed_memory_gb
            )
        )
        same_ha = current_ha == args.ha
        if same_elastic and same_guaranteed and same_ha:
            result = {
                "success": True,
                "operation": "modify_namespace_spec",
                "idempotent_noop": True,
                "message": "Namespace already has the target configuration. Skipped duplicate modify.",
                "data": {"ExistingNamespace": namespace_info},
                "request_id": "",
            }
            print(json.dumps(result, indent=2))
            return 0

        request = foas_models.ModifyNamespaceSpecV2Request(
            instance_id=args.instance_id,
            region=args.region_id,
            namespace=args.name,
        )
        request.elastic_resource_spec = (
            foas_models.ModifyNamespaceSpecV2RequestElasticResourceSpec(
                cpu=args.cpu, memory_gb=args.memory_gb
            )
        )
        if args.guaranteed_cpu is not None or args.guaranteed_memory_gb is not None:
            if args.guaranteed_cpu is None or args.guaranteed_memory_gb is None:
                result = {
                    "success": False,
                    "operation": "modify_namespace_spec",
                    "error": {
                        "code": "MissingParameter",
                        "message": "--guaranteed_cpu and --guaranteed_memory_gb must be provided together.",
                    },
                }
                print(json.dumps(result, indent=2))
                return 1
            request.guaranteed_resource_spec = (
                foas_models.ModifyNamespaceSpecV2RequestGuaranteedResourceSpec(
                    cpu=args.guaranteed_cpu,
                    memory_gb=args.guaranteed_memory_gb,
                )
            )
        if args.ha is not None:
            request.ha = args.ha

        response = client.call_api("modify_namespace_spec_v2", request)

        result = {
            "success": True,
            "operation": "modify_namespace_spec",
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as e:
        result = {
            "success": False,
            "operation": "modify_namespace_spec",
            "error": {"code": type(e).__name__, "message": str(e)},
        }
        print(json.dumps(result, indent=2))
        return 1


def tag_resources(args):
    """Tag resources."""
    try:
        # Safety check: require explicit confirmation for tagging (resource metadata change)
        if not args.confirm:
            result = {
                "success": False,
                "operation": "tag_resources",
                "error": {
                    "code": "SafetyCheckRequired",
                    "message": "Adding tags modifies resource metadata. Please confirm by adding --confirm flag.",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        if not args.region_id:
            raise ValueError("region_id is required. Please specify the region.")
        region_id = args.region_id
        client = FlinkClient(region_id=region_id)

        resource_ids = (
            args.resource_ids.split(",")
            if "," in args.resource_ids
            else [args.resource_ids]
        )

        tags = []
        desired_tags = {}
        if args.tags:
            for tag_pair in args.tags.split(","):
                parts = tag_pair.split(":")
                if len(parts) != 2:
                    raise ValueError(
                        f"Invalid tag format: '{tag_pair}'. Expected 'key:value'"
                    )
                key, value = parts
                desired_tags[key] = value
                tags.append(foas_models.TagResourcesRequestTag(key=key, value=value))

        existing_tag_map = _collect_existing_tags(
            client, region_id, args.resource_type, resource_ids
        )
        already_tagged = True
        for resource_id in resource_ids:
            current_tags = existing_tag_map.get(resource_id, {})
            for key, value in desired_tags.items():
                if current_tags.get(key) != value:
                    already_tagged = False
                    break
            if not already_tagged:
                break

        if already_tagged:
            result = {
                "success": True,
                "operation": "tag_resources",
                "idempotent_noop": True,
                "message": "All requested tags already exist with the same values. Skipped duplicate tag operation.",
                "data": {"resource_ids": resource_ids, "tags": desired_tags},
                "request_id": "",
            }
            print(json.dumps(result, indent=2))
            return 0

        request = foas_models.TagResourcesRequest(
            region_id=region_id,
            resource_id=resource_ids,
            resource_type=args.resource_type,
            tag=tags,
        )

        response = client.call_api("tag_resources", request)

        result = {
            "success": True,
            "operation": "tag_resources",
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as e:
        result = {
            "success": False,
            "operation": "tag_resources",
            "error": {"code": type(e).__name__, "message": str(e)},
        }
        print(json.dumps(result, indent=2))
        return 1


def list_tags(args):
    """List tags for resources."""
    try:
        if not args.region_id:
            raise ValueError("region_id is required. Please specify the region.")
        region_id = args.region_id
        client = FlinkClient(region_id=region_id)

        request = foas_models.ListTagResourcesRequest(
            region_id=region_id, resource_type=args.resource_type
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

    except Exception as e:
        result = {
            "success": False,
            "operation": "list_tags",
            "error": {"code": type(e).__name__, "message": str(e)},
        }
        print(json.dumps(result, indent=2))
        return 1


def untag_resources(args):
    """Untag resources."""
    try:
        # Safety check: require explicit confirmation for untagging (resource metadata change)
        if not args.confirm:
            result = {
                "success": False,
                "operation": "untag_resources",
                "error": {
                    "code": "SafetyCheckRequired",
                    "message": "Removing tags modifies resource metadata. Please confirm by adding --confirm flag.",
                },
            }
            print(json.dumps(result, indent=2))
            return 1

        if not args.region_id:
            raise ValueError("region_id is required. Please specify the region.")
        region_id = args.region_id
        client = FlinkClient(region_id=region_id)

        resource_ids = (
            args.resource_ids.split(",")
            if "," in args.resource_ids
            else [args.resource_ids]
        )
        tag_keys = args.tag_keys.split(",") if "," in args.tag_keys else [args.tag_keys]

        existing_tag_map = _collect_existing_tags(
            client, region_id, args.resource_type, resource_ids
        )
        has_target_tags = False
        for resource_id in resource_ids:
            current_tags = existing_tag_map.get(resource_id, {})
            if any(tag_key in current_tags for tag_key in tag_keys):
                has_target_tags = True
                break

        if not has_target_tags:
            result = {
                "success": True,
                "operation": "untag_resources",
                "idempotent_noop": True,
                "message": "Requested tag keys are already absent on target resources. Skipped duplicate untag operation.",
                "data": {"resource_ids": resource_ids, "tag_keys": tag_keys},
                "request_id": "",
            }
            print(json.dumps(result, indent=2))
            return 0

        request = foas_models.UntagResourcesRequest(
            region_id=region_id,
            resource_id=resource_ids,
            resource_type=args.resource_type,
            tag_key=tag_keys,
        )

        response = client.call_api("untag_resources", request)

        result = {
            "success": True,
            "operation": "untag_resources",
            "data": response.body.to_map(),
            "request_id": getattr(response, "headers", {}).get("x-acs-request-id", ""),
        }
        print(json.dumps(result, indent=2))
        return 0

    except Exception as e:
        result = {
            "success": False,
            "operation": "untag_resources",
            "error": {"code": type(e).__name__, "message": str(e)},
        }
        print(json.dumps(result, indent=2))
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Flink Instance Manager (API 2021-10-28)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Create command
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

    # Describe command
    describe_parser = subparsers.add_parser("describe", help="Describe instances")
    describe_parser.add_argument("--region_id", required=True, help="Region ID")
    describe_parser.set_defaults(func=describe_instances)

    # Modify spec command
    modify_parser = subparsers.add_parser(
        "modify_spec", help="Modify instance specifications"
    )
    modify_parser.add_argument("--instance_id", required=True, help="Instance ID")
    modify_parser.add_argument("--region_id", required=True, help="Region ID")
    modify_parser.add_argument(
        "--new_cu_count", type=int, required=True, help="New CU count"
    )
    modify_parser.add_argument(
        "--confirm_price", action="store_true", help="Confirm price"
    )
    modify_parser.set_defaults(func=modify_instance_spec)

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete an instance")
    delete_parser.add_argument("--instance_id", required=True, help="Instance ID")
    delete_parser.add_argument("--region_id", required=True, help="Region ID")
    delete_parser.add_argument(
        "--force_confirmation", action="store_true", help="Force confirmation"
    )
    delete_parser.set_defaults(func=delete_instance)

    # Renew command
    renew_parser = subparsers.add_parser("renew", help="Renew an instance")
    renew_parser.add_argument("--instance_id", required=True, help="Instance ID")
    renew_parser.add_argument("--region_id", required=True, help="Region ID")
    renew_parser.add_argument(
        "--period", type=int, required=True, choices=[1, 2, 3, 6, 12], help="Period"
    )
    renew_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm renewal (cost-incurring operation)",
    )
    renew_parser.set_defaults(func=renew_instance)

    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert billing type")
    convert_parser.add_argument("--instance_id", required=True, help="Instance ID")
    convert_parser.add_argument("--region_id", required=True, help="Region ID")
    convert_parser.add_argument(
        "--target_type",
        required=True,
        choices=["Subscription", "PayAsYouGo"],
        help="Target type",
    )
    convert_parser.add_argument(
        "--confirm_price", action="store_true", help="Confirm price"
    )
    convert_parser.add_argument(
        "--period",
        type=int,
        choices=[1, 2, 3, 6, 12],
        help="Subscription period (months)",
    )
    convert_parser.add_argument(
        "--auto_renew", action="store_true", help="Enable auto-renew"
    )
    convert_parser.set_defaults(func=convert_instance)

    # Describe regions command
    regions_parser = subparsers.add_parser("describe_regions", help="Describe regions")
    regions_parser.set_defaults(func=describe_regions)

    # Describe zones command
    zones_parser = subparsers.add_parser("describe_zones", help="Describe zones")
    zones_parser.add_argument("--region_id", required=True, help="Region ID")
    zones_parser.set_defaults(func=describe_zones)

    # Create namespace command
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

    # Describe namespaces command
    ns_desc_parser = subparsers.add_parser(
        "describe_namespaces", help="Describe namespaces"
    )
    ns_desc_parser.add_argument("--region_id", required=True, help="Region ID")
    ns_desc_parser.add_argument("--instance_id", required=True, help="Instance ID")
    ns_desc_parser.set_defaults(func=describe_namespaces)

    # Delete namespace command
    ns_delete_parser = subparsers.add_parser(
        "delete_namespace", help="Delete a namespace"
    )
    ns_delete_parser.add_argument("--region_id", required=True, help="Region ID")
    ns_delete_parser.add_argument("--instance_id", required=True, help="Instance ID")
    ns_delete_parser.add_argument("--name", required=True, help="Namespace name")
    ns_delete_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm deletion (destructive operation)",
    )
    ns_delete_parser.add_argument(
        "--confirm_no_running_jobs",
        action="store_true",
        help="Acknowledge manual verification that no jobs are running when usage metrics are unavailable",
    )
    ns_delete_parser.set_defaults(func=delete_namespace)

    # Modify namespace spec command
    modify_ns_parser = subparsers.add_parser(
        "modify_namespace_spec", help="Modify namespace specifications"
    )
    modify_ns_parser.add_argument("--region_id", required=True, help="Region ID")
    modify_ns_parser.add_argument("--instance_id", required=True, help="Instance ID")
    modify_ns_parser.add_argument("--name", required=True, help="Namespace name")
    modify_ns_parser.add_argument(
        "--cpu", type=int, required=True, help="New CPU (Core)"
    )
    modify_ns_parser.add_argument(
        "--memory_gb", type=int, required=True, help="New Memory (GB)"
    )
    modify_ns_parser.add_argument(
        "--guaranteed_cpu",
        type=int,
        help="Guaranteed CPU for subscription/hybrid namespace (optional)",
    )
    modify_ns_parser.add_argument(
        "--guaranteed_memory_gb",
        type=int,
        help="Guaranteed memory for subscription/hybrid namespace (optional)",
    )
    modify_ns_parser.add_argument(
        "--ha",
        type=parse_bool_arg,
        help="Whether namespace is HA (required by API, true/false)",
    )
    modify_ns_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm modification (resource-changing operation)",
    )
    modify_ns_parser.set_defaults(func=modify_namespace_spec)

    # Tag resources command
    tag_parser = subparsers.add_parser("tag_resources", help="Tag resources")
    tag_parser.add_argument("--region_id", required=True, help="Region ID")
    tag_parser.add_argument("--resource_type", required=True, help="Resource type")
    tag_parser.add_argument("--resource_ids", required=True, help="Resource IDs")
    tag_parser.add_argument(
        "--tags", required=True, help="Tags (key1:value1,key2:value2)"
    )
    tag_parser.add_argument(
        "--confirm", action="store_true", help="Confirm tagging (metadata change)"
    )
    tag_parser.set_defaults(func=tag_resources)

    # List tags command
    list_tags_parser = subparsers.add_parser("list_tags", help="List tags")
    list_tags_parser.add_argument("--region_id", required=True, help="Region ID")
    list_tags_parser.add_argument(
        "--resource_type", required=True, help="Resource type"
    )
    list_tags_parser.add_argument("--resource_ids", help="Resource IDs")
    list_tags_parser.set_defaults(func=list_tags)

    # Untag resources command
    untag_parser = subparsers.add_parser("untag_resources", help="Untag resources")
    untag_parser.add_argument("--region_id", required=True, help="Region ID")
    untag_parser.add_argument("--resource_type", required=True, help="Resource type")
    untag_parser.add_argument("--resource_ids", required=True, help="Resource IDs")
    untag_parser.add_argument("--tag_keys", required=True, help="Tag keys to remove")
    untag_parser.add_argument(
        "--confirm", action="store_true", help="Confirm untagging (metadata change)"
    )
    untag_parser.set_defaults(func=untag_resources)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
