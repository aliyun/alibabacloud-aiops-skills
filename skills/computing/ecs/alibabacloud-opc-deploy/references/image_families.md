# ImageFamily Reference Table

> Companion to advisor SKILL.md iron-rule #28 and deploy SKILL.md iron-rules #29 / #32.
>
> **This table was derived by running `aliyun ecs describe-images` + several `describe-image-from-family` calls against a real account in cn-beijing on 2026-06-25**. The naming convention, family names, and matching ImageIds are all dry-run measured data.
>
> **dry-run measured corrections**:
> - `acs:alibaba_cloud_linux_3_2104_lts_x64` ✓ hit (includes the minor version `_2104_lts_`)
> - `acs:alibaba_cloud_linux_3_x64` ✗ **0 hits** (missing the minor version)
> - `acs:alibaba_cloud_linux_4_lts_x64` ✓ hit (must include the `_lts_` infix)
> - `acs:alibaba_cloud_linux_4_x64` ✗ **0 hits** (missing `_lts_`)
> - Conclusion: the Linux 3 family must carry the minor version `_2104_lts_`; the Linux 4 family must carry the `_lts_` infix.
>
> **Core iron rules**:
> - **The advisor prescription must pass the full family with the minor version + `_lts_` marker** (e.g. `acs:alibaba_cloud_linux_3_2104_lts_x64`, `acs:alibaba_cloud_linux_4_lts_x64`); passing a short name missing the minor version or `_lts_` is not allowed.
> - deploy takes the family → resolves it via `DescribeImageFromFamily` to a concrete ImageId → **writes it to state.resources.ecs.image_id and locks it permanently**; scale-out/rebuild reuse state first (iron-rule #29).
> - Crossing a major version (e.g. Linux 3 → 4) must be reviewed and the family bumped on the advisor side; deploy is **forbidden** to roll it forward on its own.

## ImageFamily naming convention (derived from dry-run measurements)

The real Alibaba Cloud ECS ImageFamily naming convention (dry-run corrected):
- prefix `acs:`
- all lowercase
- **underscore-separated** (not hyphen `-`)
- **the Linux 3 series must carry the minor version `_2104_lts_`** (dry-run measured: `acs:alibaba_cloud_linux_3_x64` = 0 hits)
- **the Linux 4 series must carry the `_lts_` infix** (dry-run measured: `acs:alibaba_cloud_linux_4_x64` = 0 hits, `acs:alibaba_cloud_linux_4_lts_x64` hits)
- architecture suffix `_x64` / `_arm64`
- the container-optimized edition adds the `_container_optimized` suffix
- the GPU-optimized edition adds the `_with_nvidia_gpu_driver_and_cuda` or `_with_nvidia_open_source_gpu_driver_and_cuda` suffix
- the MLPS edition adds the `_dengbao2.0` suffix
- the Pro edition adds the `_pro` infix

Valid examples: `acs:alibaba_cloud_linux_3_2104_lts_x64`, `acs:alibaba_cloud_linux_4_lts_x64`, `acs:ubuntu_24_04_x64`, `acs:rocky_linux_9_7_arm64`
Invalid examples (dry-run measured 0 hits): `acs:alibaba-cloud-linux-3-x64` (hyphens), `acs:alibaba_cloud_linux_3_x64` (missing minor version `_2104_lts_`), `acs:alibaba_cloud_linux_4_x64` (missing `_lts_` infix)

## Primary families

The OSName column values (in backticks) are literal Alibaba Cloud OSName strings used for echo/matching — kept verbatim, not translated.

```text
| Purpose | family (locked) | OSName (for echo) | Locked ImageId example | pinned_at | next_review_due |
|---|---|---|---|---|---|
| **General Web/App x64** (default) | `acs:alibaba_cloud_linux_3_2104_lts_x64` | `Alibaba Cloud Linux  3.2104 LTS 64位` | `aliyun_3_x64_20G_alibase_20260513.vhd` | 2026-06-25 | 2026-12-25 |
| General Web/App ARM | `acs:alibaba_cloud_linux_3_2104_lts_arm64` | `Alibaba Cloud Linux  3.2104 LTS 64位 ARM版` | resolved via DescribeImageFromFamily | 2026-06-25 | 2026-12-25 |
| Linux 4 LTS x64 (experimental, not for production) | `acs:alibaba_cloud_linux_4_lts_x64` | `Alibaba Cloud Linux  4 LTS 64位` | `aliyun_4_x64_20G_alibase_20260430.vhd` | 2026-06-25 | 2026-12-25 |
| Container-optimized scenario | `acs:alibaba_cloud_linux_3_2104_x64_container_optimized` | `Alibaba Cloud Linux  3.2104 LTS 64位 容器优化版` | resolved via DescribeImageFromFamily | 2026-06-25 | 2026-12-25 |
| MLPS 2.0 Level 3 | `acs:alibaba_cloud_linux_3_pro_x64_dengbao2.0` | `Alibaba Cloud Linux  3 Pro 64位 等保2.0三级版` | resolved via DescribeImageFromFamily | 2026-06-25 | 2026-12-25 |
```

## Third-party distributions (alternatives; advisor does not output them by default, requires an explicit user request)

```text
| Distribution | family (measured) | OSName (for echo) |
|---|---|---|
| Ubuntu 24.04 x64 | `acs:ubuntu_24_04_x64` | `Ubuntu 24.04 64位` |
| Ubuntu 22.04 x64 | `acs:ubuntu_22_04_x64` | `Ubuntu 22.04 64位` |
| Rocky Linux 9.7 x64 | `acs:rocky_linux_9_7_x64` | `Rocky Linux 9.7 64位` |
| AlmaLinux 9.7 x64 | `acs:almalinux_9_7_x64` | `AlmaLinux 9.7 64位` |
| Debian 13.5 x64 | `acs:debian_13_5_x64` | `Debian 13.5 64位` |
```

> ⚠️ The ImageIds of the third-party distributions above are resolved by deploy via DescribeImageFromFamily; the advisor prescription defaults to Alibaba Cloud Linux (best compatibility). Switching to a third-party distribution requires the user to **explicitly request it** in the conversation.

## advisor prescription contract (output format)

```yaml
image:
  family: "acs:alibaba_cloud_linux_3_2104_lts_x64"  # required, includes the minor version
  os_series: "Alibaba Cloud Linux 3.2104 LTS"       # required, human-readable name (note: two spaces between "Linux" and "3.2104" —— matches OSName)
  arch: "x64"                                       # required: x64 | arm64
  family_pinned_at: "2026-06-25"                    # required, the date advisor pinned this family
  next_review_due: "2026-12-25"                     # required, the next manual-review date (+6 months)
  # ⚠️ Forbidden fields: image.id / image.name (avoid version drift maintained on both advisor/deploy sides)
```

## deploy resolution flow (iron-rules #29 / #32)

```text
Phase 0 image resolution:

Step 1 primary path:
  aliyun ecs describe-image-from-family \
    --RegionId ${region} \
    --ImageFamily ${image.family}    # from the advisor prescription
  ↓
  hit → get ImageId + CreationTime
  ↓
Step 2 non-blocking info display to the user (iron-rule #32, does NOT wait for a reply):
  to the user:
    "✓ 已为你的服务器选定镜像：
       ${image.os_series}（${image.arch}）
       发布版本：${CreationTime} 的官方镜像
       这是 advisor 处方锁定到 ${image.family_pinned_at} 的稳定次版本，
       后续扩容/重建都会复用同一镜像，不会半夜偷偷换 OS 大版本。"
  after displaying, continue directly (no [Y/n] wait).
  (rationale: a non-technical user cannot make a meaningful ACK on an ImageId hex string; the original [Y/n] was security theater — the meaningful image choice was already settled at the advisor layer via family + os_series human-readable name.)
  ↓
Step 3 write state (lock permanently):
  state.resources.ecs.image_id = ${ImageId}
  state.resources.ecs.image_family = ${image.family}
  state.resources.ecs.image_pinned_by_advisor_at = ${image.family_pinned_at}
  state.resources.ecs.image_locked_by_user_at = ${now}
  ↓
Step 4 RunInstances:
  pass ImageId = state.resources.ecs.image_id (no longer calls DescribeImageFromFamily)

Fallback (when the primary path gets 0 hits):
  aliyun ecs describe-images \
    --RegionId ${region} \
    --ImageFamily ${image.family} \           # same family as the primary path, but via the List API
    --Status Available \
    --ImageOwnerAlias system \
    --PageSize 5
  ↓
  take Images.Image[0].ImageId (in the API default order, newest first)
  ↓
  still 0 hits → hard-stop (crossing a major version as a fallback is not allowed):
    "系统镜像清单里没找到 ${image.family} 锁定的次版本（${image.os_series}）。
     可能阿里云这个区下架了该次版本。
     请回 advisor 重出处方（@opc-cloud-advisor 帮我换一个能用的镜像）。"

⚠️ Removed (dry-run measured):
  - --SortOrder DESC (CLI 3.4.1 does not recognize this parameter → errors)
  - --ImageName "${image.os_series}*" (the Chinese OSName has double spaces → wildcard 0 hits)
  - switching to --ImageFamily hits reliably
```

## Compatibility constraints with InstanceType

- ARM instances (g7arm/c7arm/g9iarm etc.) can only mount ARM images (`_arm64` suffix)
- Shenlong / high-frequency / heterogeneous-compute instance families have extra image allowlists; advisor already avoids them when picking the SKU

## Maintenance governance

- **Manual review every six months**: at the `next_review_due` date, the advisor maintainer runs `DescribeImageFromFamily` once to verify the primary-path family is still valid; if there is a new minor version (e.g. Linux 3.3105 released), evaluate whether to bump the family + write an ADR document explaining the reason
- **Crossing a major version as a fallback is not allowed**: if the whole Linux 3 series is delisted, the family must first be bumped to the Linux 4 series on the advisor side and all users holding the starter_webui/starter_app yaml must be notified to upgrade manually; deploy is not allowed to auto-jump
