# 10 · Multimodal input: answering questions about images

Scenario: a user submits an image and a question to a business service. The service uploads the image, waits for file review, and passes a mixed text-and-image message to MA; the application verifies that the answer actually addresses the image.

**Test scope**: retested on 2026-10-09, cn-beijing, using the local environment-variable API key against the online service. Image `file_id` input correctly identified a synthetic 64×64 red PNG with `qwen3.8-max`, `qwen3.7-plus`, and `auto`. Each answered `Red` without tools. This recipe covers the verified image path; video input was not tested.

**Auto-model follow-up (2026-09-19)**: in the same cn-beijing test workspace, an Agent created with `model: {"id": "auto"}` was read back as `auto`. A synthetic 64×64 red PNG was uploaded, reviewed to `available`, and sent as `type: "image"` with `file_id`. The assistant answered exactly `Red` with no tool calls. This verifies this image path with `auto`; it does not establish which underlying model the router selected or guarantee every multimodal format. The temporary Session, Environment, and uploaded File were deleted, and the Agent was archived.

**Model limitation (user-confirmed, 2026-10-09): `performance` does not support multimodal input.** The 2026-09-19 check and 2026-10-09 retest both returned an inability to view the uploaded red image, consistent with this product limitation. Do not use `performance` for this recipe. Select `auto` or an explicitly supported model such as the two tested above, create a new Session, and send the image there. Updating an Agent does not change an existing Session's pinned Agent version.

## Run the complete example

Use the [shared smoke-test setup](index.md#shared-smoke-test-setup), then run from the repository root:

```bash
/tmp/ma-cookbook-env/bin/python scripts/cookbook_smoke.py \
  --execute \
  --scenarios image --output /tmp/ma-image-check
```

In [cookbook_smoke.py](../../scripts/cookbook_smoke.py), `image_test` generates a red PNG without user data, uploads it, waits for review, then sends it. The script cleans up its own temporary resources.

## Image input: use the verified file_id path

1. Upload a PNG with multipart `POST /files`; save its File ID.
2. Poll `GET /files/{id}` with a deadline until `available`; stop on rejection.
3. Send this to a new Session:

```json
{
  "input": [{
    "type": "message",
    "role": "user",
    "content": [
      {"type": "text", "text": "Identify the dominant color. Answer just the color name."},
      {"type": "image", "file_id": "<available_image_file_id>"}
    ]
  }]
}
```

4. Check the assistant's answer and terminal state. Expect `Red`; HTTP 200 or `end_turn` alone is insufficient.

**Current limitation (user-confirmed, 2026-09-18)**: MA does not currently support Base64 `image_data` input. The earlier official claim of support for `image_data` + `media_type` was incorrect. In tests, POST accepted synthetic PNG data and history retained the image block, but both models reported no image. Uploaded `file_id` inputs worked. The max trials used 32×32 Base64 images versus 64×64 file uploads; the plus comparison used the exact same 64×64 PNG for both carriers, and only `file_id` worked. The user confirmed the unsupported status and documentation error, resolving the earlier uncertainty about the cause. Use `file_id` now rather than repeating Base64 attempts. Documentation may be corrected later; retest if support is subsequently announced. This limitation does not mean multimodal events are unavailable. See [product status](../product/status.md).

`type: "image"` supplies model vision input. `type: "file"` with `file_id` and `filename` materializes a file for tool access; these serve different purposes.

## Sources

- [Send events: multimodal content blocks](https://docs.agent.bailian.aliyun.com/zh/api/managed-agents/session/send-event.md)
