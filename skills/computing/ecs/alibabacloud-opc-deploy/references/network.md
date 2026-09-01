# Phase 2: Network infrastructure

> Runs after Phase 1 authorization, before Phase 3 paid creation.
>
> - **Entry**: Step 1.5 self-check all green (including the Step 0.2b probe).
> - **Exit**: VPC + VSwitch + security group ready and tagged → go to Phase 3 (`provision.md`).
> - Everything created here is **free** (VPC / VSwitch / SecurityGroup) — the PAYMENT GATE does not apply
>   to this phase, but the probe and the payment confirmation must already have happened.
> - Flag conventions (`--biz-region-id` required everywhere, tag syntax, `--output` quoting): `cli-meta.md`.

```text
Step 2.1: Query existing OPC VPCs (QuotaExceeded.Vpc handling + ownership field)
  ① First query opc:managed-tagged VPCs:
    aliyun vpc describe-vpcs \
      --biz-region-id <region> \
      --tag Key=opc:managed Value=true
    # The `--tag Key=… Value=…` form is accepted here (E2E-measured), but server-side filtering has NOT
    # been confirmed to actually narrow the result set. Treat the response as advisory: if it comes back
    # non-empty, re-check each returned VPC's own Tags for opc:managed=true before claiming ownership; if
    # it errors on the flag, fall back to the unfiltered list in step ② and filter locally. Never infer
    # ownership from the mere fact that the tagged query returned rows.
    has result → extract VpcId + VSwitchId → state.resources.vpc.owned = true → jump to 2.4
    no result → go to step ②

  ② Before trying to create, list **all VPCs under the account** for the user to choose
    aliyun vpc describe-vpcs --biz-region-id <region>
    Scenario A: list empty → go straight to 2.2 create
    Scenario B: list non-empty (the account already has VPCs, creation may have failed with QuotaExceeded.Vpc) →
      To the user: "你账号下已经有 ${N} 个 VPC（VPC 是云上的虚拟内网）：
             ${vpc_list 友好显示}

             两个选项：
             ① 复用现有 ${某个 VPC name} → 我把这次的服务器放进去（不删它）
             ② 让我新建一个独立 VPC → 默认推荐，账号有配额时优选

             选哪个？"
      user picks ① → record state.resources.vpc.id = ${reused_id}, owned = false → jump to 2.3, create a new VSwitch in the reused VPC (do NOT add the opc:managed tag to someone else's VPC)
      user picks ② → go to 2.2 to try creating; if it returns QuotaExceeded.Vpc, return here to let the user re-pick ①
      # Default VPC quota is 1 per region — a leftover VPC from an earlier run will make creation fail here.

Step 2.2: Create VPC (only the ownership=true path)
  Command: aliyun vpc create-vpc \
    --biz-region-id <region> \
    --vpc-name OPC-VPC \
    --cidr-block 10.0.0.0/16 \
    --tag Key=opc:managed Value=true
  → record VpcId
  → wait for VPC status to become Available
    # vpc CreateVpc --Tag measured NOT to persist; must post-call TagResources to backfill
  → backfill the tag:
    aliyun vpc tag-resources \
      --biz-region-id <region> \
      --resource-type VPC \
      --resource-id <vpc_id> \
      --tag Key=opc:managed Value=true

Step 2.3: Create the VSwitch
  First resolve a usable zone. **Prefer** `describe-available-resource` (returns real-time stock, compact output):
    aliyun ecs describe-available-resource --biz-region-id <region> --destination-resource InstanceType --instance-type <type>
    # returns which zones actually have stock for the target instance type — pick the first available zone.
    # ⚠️ Do NOT default to `aliyun ecs describe-zones` for this: measured, its full-region output can reach
    #    ~30KB and gets truncated by the terminal capture layer, breaking JSON parsing. describe-zones is
    #    acceptable ONLY with a tight --cli-query / narrow filter; otherwise use describe-available-resource.
  Pick the first zone that supports the target instance type
  Command: aliyun vpc create-vswitch \
    --vpc-id <vpc_id> \
    --biz-region-id <region> \
    --zone-id <zone_id> \
    --cidr-block 10.0.0.0/24 \
    --vswitch-name OPC-VSwitch
  → record VSwitchId
    # vpc CreateVSwitch does not accept --Tag; must post-call TagResources to backfill,
    # otherwise teardown DeleteVSwitch (RAM condition opc:managed=true) is denied with Forbidden.RAM
  → backfill the tag:
    aliyun vpc tag-resources \
      --biz-region-id <region> \
      --resource-type VSWITCH \
      --resource-id <vswitch_id> \
      --tag Key=opc:managed Value=true

Step 2.4: Security group (SSH tightened to ${MY_IP}/32, 8080 removed)
  Query existing: aliyun ecs describe-security-groups \
    --biz-region-id <region> \
    --vpc-id <vpc_id> \
    --tag Key=opc:managed Value=true
  has → reuse the group, but you MUST STILL tighten SSH for the CURRENT user: resolve MY_IP (per the tiers below) and call authorize-security-group to set port 22 = ${MY_IP}/32. A reused group may not include the current user's IP, or may be too loose — NEVER assume its rules are correct, and NEVER skip authorize-security-group just because the group already exists; if it carries a 0.0.0.0/0 SSH rule, do not leave it in place. (Run the MY_IP resolution + port-22 authorize-security-group steps below either way.)
  none → create + open rules:
    aliyun ecs create-security-group \
      --biz-region-id <region> \
      --vpc-id <vpc_id> \
      --security-group-name OPC-SecurityGroup \
      --tag Key=opc:managed Value=true
    # ⚠️ --biz-region-id is REQUIRED on every ecs/vpc plugin call, including this one (E2E-measured:
    #    omitting it here made CreateSecurityGroup return empty output and the whole step failed).
    # ecs CreateSecurityGroup --Tag measured NOT to persist; must post-call TagResources to backfill
    aliyun ecs tag-resources \
      --biz-region-id <region> \
      --resource-type securitygroup \
      --resource-id <security_group_id> \
      --tag Key=opc:managed Value=true

    # Auto-detect the user's egress IP (prefer an Alibaba Cloud-owned probe endpoint,
    # fall back to ifconfig.me/ipinfo.io, and if all fail have the user type it in, to avoid writing a garbage value into the allowlist)
    # Note: the Alibaba Cloud ECS metadata 100.100.100.200 is only reachable inside ECS, not from a local terminal.
    #     Here we use a lightweight aliyun CLI call instead; the CLI carries its own Signature and the response can yield RemoteAddr (some versions).
    #     The most robust is still the third-party + user-input three-tier fallback.
    MY_IP=""
    # Tier 1: Alibaba Cloud GetCallerIdentity over https, CLI-built-in signing resists MITM (more trusted than plaintext ifconfig.me)
    MY_IP=$(aliyun sts get-caller-identity --profile opc 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('RemoteAddress',''))" 2>/dev/null)
    # Tier 2: HTTPS ifconfig.me/ipinfo.io (must be https + -4 to force IPv4; the security group SourceCidrIp only accepts IPv4)
    if ! echo "$MY_IP" | grep -Eq '^[0-9]{1,3}(\.[0-9]{1,3}){3}$'; then
      RAW=$(curl -4 -s --max-time 5 https://ifconfig.me 2>/dev/null || curl -4 -s --max-time 5 https://ipinfo.io/ip 2>/dev/null)
      echo "$RAW" | grep -Eq '^[0-9]{1,3}(\.[0-9]{1,3}){3}$' && MY_IP="$RAW"
    fi
    if [ -z "$MY_IP" ]; then
      To the user: "自动获取你的网络出口 IP 失败。安全起见我不能开 0.0.0.0/0。
            请打开 https://ipw.cn 查到自己的公网 IP，告诉我，我用它写白名单。"
      Wait for the user to input an IP, validate it (IPv4 regex) then assign to MY_IP, otherwise keep asking; do not accept an empty value
    fi

    ⚠️ HARD RULE (weak-model-proof): SSH port 22 with SourceCidrIp 0.0.0.0/0 is FORBIDDEN. Before authorizing port 22, self-check: is MY_IP a concrete IPv4 resolved via the tiers above? If NOT → do NOT authorize port 22; go back and resolve MY_IP (or ask the user for their public IP). NEVER use 0.0.0.0/0 as an SSH fallback. (HTTP 80 / HTTPS 443 to 0.0.0.0/0 is correct — those are public web ports.)
    Open rules one by one (SSH uses ${MY_IP}/32 single IP; HTTP/HTTPS use 0.0.0.0/0):
      aliyun ecs authorize-security-group --biz-region-id <region> --security-group-id <sg> --ip-protocol tcp \
        --port-range 22/22  --source-cidr-ip ${MY_IP}/32   # SSH self only
      aliyun ecs authorize-security-group --biz-region-id <region> --security-group-id <sg> --ip-protocol tcp \
        --port-range 80/80  --source-cidr-ip 0.0.0.0/0     # HTTP (Pro force-redirects to HTTPS)
      aliyun ecs authorize-security-group --biz-region-id <region> --security-group-id <sg> --ip-protocol tcp \
        --port-range 443/443 --source-cidr-ip 0.0.0.0/0    # HTTPS
      # ⚠️ TCP 8080 removed: OpenClaw is accessed via the SWAS console "应用详情→登录 Web UI" entry (white-box product capability: random port + Token + public access off by default); 8080 is no longer exposed raw

  User-facing copy: "✓ 已创建安全门禁。SSH（远程登录端口）只对你当前的网络 IP 开放（${MY_IP}），别人就算拿到密钥从别的网络也连不上。HTTP/HTTPS 对外开放给访客访问业务。"
  → record SecurityGroupId
  → after deployment, **keep** the SSH rule (the user can tighten/close it in the console, balancing convenience and security)

  ControlPolicy interception handling (do not teach circumvention):
    If AuthorizeSecurityGroup returns OperationDenied.NoPermission caused by an org-level ControlPolicy:
    To the user: "你的账号被组织管控策略限制，普通子账号无法直接放行端口。请联系你的云账号管理员申请例外，或扩大 opc-deploy 子账号的权限范围。提工单：https://smartservice.console.aliyun.com/service/create-ticket"
    Abort, do not retry.
```
