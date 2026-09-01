# Phase 0.4: Centralized image resolution (iron-rule #27)

> Runs after Phase 0 (credential + probe + connectivity all green), before Phase 1.
>
> - **Entry**: credential works AND the Step 0.2b policy probe passed.
> - **Exit**: `state.resources.ecs.image_id` written and locked → go to Phase 1 (`confirm-authorize.md`).
> - Note: this is **Phase 0.4** (image resolution). The connectivity check is **Step 0.5** in
>   `credential-setup.md` — different thing, previously both numbered "0.4".

```text
Every SKU containing ECS RunInstances (starter_webui / starter_app / lite_seed / lite_growth / lite_traction / pro_steady / pro_burst) must run this step first to resolve the image and write it to state; **yamls after Phase 1 only consume state.resources.ecs.image_id**.

Step 0.4.1: Check whether state already locked an image
  if state.resources.ecs.image_id already exists:
    → skip the whole Phase 0.4 (iron-rule #27 reuse clause; scale-out/rebuild use the same binary)
    → go straight to Phase 1
  else continue to Step 0.4.2

Step 0.4.2: Primary path DescribeImageFromFamily
    # family source: prefer the advisor prescription image.family; without advisor context use deploy's built-in default
    #   (image_families primary family: acs:alibaba_cloud_linux_3_2104_lts_x64 / x64;
    #    for ARM instance families use acs:alibaba_cloud_linux_3_2104_lts_arm64)
  FAMILY=${advisor prescription image.family:-image_families primary default}
  aliyun ecs describe-image-from-family --profile opc \
    --biz-region-id ${region} \
    --image-family ${FAMILY}
    # the advisor prescription family must include the minor-version underscore format, e.g. acs:alibaba_cloud_linux_3_2104_lts_x64
    # dry-run measured: a short name (acs:alibaba_cloud_linux_3_x64) gets 0 hits
    # ⚠️ Do NOT add `--output cols=ImageId rows=Image`: Image is a single OBJECT and `rows=` needs an array
    #    (measured: "jmespath 'RootFilter[0].Image' failed: need array expression"). Parse the raw JSON.

  hit → extract Image.ImageId / Image.CreationTime / Image.OSName → Step 0.4.4
  0 hits → Step 0.4.3 fallback

Step 0.4.3: Fallback DescribeImages (same family, List API path)
  aliyun ecs describe-images --profile opc \
    --biz-region-id ${region} \
    --image-family ${advisor prescription image.family} \
    --status Available \
    --image-owner-alias system \
    --page-size 5
    # ⚠️ do not add a sort flag (neither --SortOrder nor --sort-order exists on DescribeImages)
    # ⚠️ do not use the --image-name wildcard (the Chinese OSName's double spaces are unreliable)

  hit → take Images.Image[0].ImageId / CreationTime / OSName → Step 0.4.4
  0 hits → hard-stop, to the user:
    "系统镜像清单里没找到 ${image.family} 锁定的次版本（${image.os_series}）。
     可能该次版本在 ${region} 区下架了。
     请回 advisor 重出处方：「@alibabacloud-opc-advisor 帮我把镜像换成能用的次版本」。"
  Forbidden behaviors: ① retrying with a mutated family string; ② cross-major-version fallback (Linux 3→4 breaks the app layer); ③ switching to another family on its own

Step 0.4.4: Write state, lock permanently
  state.resources.ecs.image_id = ${resolved ImageId}
  state.resources.ecs.image_family = ${FAMILY}
  state.resources.ecs.image_os_series = ${advisor prescription image.os_series:-resolved OSName}
  state.resources.ecs.image_creation_time = ${resolved CreationTime}
  state.resources.ecs.image_pinned_by_advisor_at = ${advisor prescription image.family_pinned_at:-null (no advisor context, deploy used the default family)}
  state.resources.ecs.image_locked_at = ${now}

Step 0.4.5: Non-blocking info display (iron-rule #32)
  User-facing copy (informational, **does NOT wait for a reply**):
    "✓ 已锁定服务器镜像：
       系统：${image.os_series}（${image.arch}）
       发布版本：${image.creation_time} 的官方镜像
       ${when advisor context exists: 这是 advisor 在 ${image.family_pinned_at} 锁定的次版本}
       ${when no advisor context: 这是当前推荐的稳定次版本}——已写入 state 永久绑定，
       后续扩容/重建复用同一镜像，避免半夜偷偷换 OS 大版本炸应用。"
  After displaying, go straight to Phase 1, do not wait for [Y/n].
```
