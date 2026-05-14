# VPC Reference

Script: `scripts/vpc.py` | API style: RPC | Version: vpc/2016-04-28

Almost all products (ECS, ACK, etc.) depend on VPC and VSwitch. Make sure the network is ready before creating compute resources.

## API Quick Reference

### ensure_vpc_and_vswitch(zone_id, ...) → (vpc_id, vswitch_id, vpc_is_new, vswitch_is_new)

**Recommended entry point.** Automatically creates or reuses an existing VPC + VSwitch. **Auto-detects an available CIDR range, no manual conflict avoidance needed.**

Returns four values: the VPC/VSwitch IDs and two booleans indicating whether each was freshly created (`True`) or reused from an existing resource (`False`). Use the boolean flags to decide cleanup scope — only delete newly created resources.

```python
from vpc import ensure_vpc_and_vswitch

vpc_id, vsw_id, vpc_is_new, vsw_is_new = ensure_vpc_and_vswitch(
    zone_id="cn-hangzhou-h",           # required, target zone
    vpc_cidr="192.168.0.0/16",         # VPC CIDR, default 192.168.0.0/16
    vsw_cidr=None,                     # VSwitch CIDR, default None = auto-detect available /24 subnet
    vpc_name="acf-vpc",                # VPC name, used for reuse detection
    vsw_name="acf-vsw",                # VSwitch name
    region=None,                       # region, defaults to env
)
# vpc_is_new=False means the VPC was reused — do NOT delete it during cleanup
# vsw_is_new=True  means the VSwitch was freshly created — safe to delete
```

Logic:
1. Look up an existing VPC by vpc_name → reuse if found → otherwise create
2. Look up an existing VSwitch in the target zone → reuse if found
3. No usable VSwitch → **scan CIDRs of existing VSwitches in the VPC** and pick an unused /24 subnet (e.g. if 192.168.0.0/24 is taken, try 192.168.1.0/24, 192.168.2.0/24, ...)
4. You may also pass `vsw_cidr="192.168.10.0/24"` explicitly to skip auto-detection

### create_vpc(cidr_block, vpc_name, region, description) → dict

Create a VPC and wait for Available. Returns VPC details including `VpcId`.

### describe_vpcs(vpc_id, vpc_name, region, page_size) → dict

Query the VPC list. Returns `Vpcs.Vpc[]`.

### create_vswitch(vpc_id, zone_id, cidr_block, vswitch_name, region, description) → dict

Create a VSwitch and wait for Available. Returns VSwitch details including `VSwitchId`.

### describe_vswitches(vpc_id, vswitch_id, zone_id, region, page_size) → dict

Query the VSwitch list. Returns `VSwitches.VSwitch[]`.

### delete_vswitch(vswitch_id, region) → dict

Delete a VSwitch. The VSwitch must have no associated resources (release ECS instances, security groups, etc. first).

### delete_vpc(vpc_id, region) → dict

Delete a VPC. All VSwitches inside the VPC must be deleted first.

### Release Order

Delete network resources in reverse dependency order: `ECS instances → security groups → VSwitch → VPC`.

```python
from vpc import delete_vswitch, delete_vpc

delete_vswitch(vswitch_id="vsw-xxx")
delete_vpc(vpc_id="vpc-xxx")
```

> Use the `vpc_is_new` / `vsw_is_new` flags from `ensure_vpc_and_vswitch()` to decide: only delete resources where the flag is `True`. Reused resources (`False`) belong to other workloads and must NOT be deleted.

## Documentation Search

When you are unsure about a parameter, hit an unknown error code, or need the latest API docs, use `scripts/doc_search.py` to search the Alibaba Cloud official documentation:

```python
from doc_search import search_and_format

# Search VPC-related docs
print(search_and_format("CreateVpc parameter description", product="vpc"))
print(search_and_format("VSwitch zone constraints", product="vpc"))

# Search by error code
print(search_and_format("InvalidCidrBlock", product="vpc"))
```

Search results include title, summary, and link. Use the web_fetch tool to retrieve full document content.

## Notes

- A VSwitch must specify zone_id, and zone_id must match the zone of any compute resources created later
- Get zone_id via `ecs.describe_zones()` or `ecs.describe_available_resource()`
- VPC CIDR planning: use 10.0.0.0/16 for production; 192.168.0.0/16 or /24 for testing/personal use
