# Image Generation Operation Reference

When the following scenarios are triggered, convert user requirements into prompt, taskType, aspect ratio, size, and reference asset parameters for `yike generate image`. See [`generate.md`](generate.md) for command parameters, defaults, and execution rules.

## Scope

Read this document when the following needs are triggered:

- "Generate an image", "make a picture", "create a poster / product image / avatar / cover / wallpaper / illustration" — standalone image generation.
- "Use this image as reference", "transform this mediaId into a certain style", "keep the subject and generate another image" — reference-image-to-image.
- The user provides only a vague intent, and the Agent needs to fill in visual language, aspect ratio, and basic prompt.

This document only covers image generation.

## Execution Order

1. Identify the input form: upload local image paths or Agent conversation image attachments first; image URL / mediaId goes directly to `--reference-image`; no reference image means pure text-to-image.
2. Set `--aspect-ratio` based on the use case: avatar, product hero image, poster, banner, social media cover, wallpaper, illustration, etc.
3. Compile the prompt: convert abstract words into visual descriptions; preserve the subject, brand, copy, and constraints given by the user.
4. Pass only necessary parameters: do not proactively override `--model`, `--resolution`, or `--size` by default; prefer `--aspect-ratio` when the ratio can express the requirement.
5. Run with complete parameters using `--dry-run --format json`; present the estimated credits to the user and wait for explicit confirmation. After confirmation, keep generation parameters unchanged and replace `--dry-run` with `--yes` to submit. Re-estimate and re-confirm when parameters change.

## taskType & Reference Image

| User Expression | Parameter Selection |
| --- | --- |
| "Generate an image…" with no reference assets | Do not pass reference parameters; defaults to `text_to_image` |
| "Use this image as reference / keep this subject / match this style" with a URL | `--reference-image <url>`; defaults to `image_to_image` |
| "Use this mediaId as reference / use the previous result" and confirmed as image reference | Prefer `--reference-image <mediaId>`; defaults to `image_to_image` |
| Local image path or Agent conversation image attachment | Upload first per [`upload.md`](upload.md); after status is `Normal`, pass `--reference-image <mediaId>` |
| User says "reference asset" but provides no URL, mediaId, local path, or attachment | Request the asset first; do not fabricate a reference |

Do not merely write "refer to the previous image" in the prompt; you must explicitly pass reference parameters. Do not pass local images directly to `--reference-image` — upload first and use the returned image mediaId.

## Aspect Ratio Selection

Only use aspect ratios currently supported by CLI image generation: `16:9`, `9:16`, `1:1`, `3:4`, `4:3`, `21:9`.

| User Use Case or Keywords | `--aspect-ratio` |
| --- | --- |
| Product hero image, avatar, logo, icon, single-subject asset, square social media image | `1:1` |
| Landscape poster, cover image, website hero, presentation slide, YouTube thumbnail, wide scene | `16:9` |
| Phone wallpaper, portrait poster, short-video cover, Story/Reels/TikTok vertical image | `9:16` |
| Magazine cover, half-body portrait, vertical product poster, book cover | `3:4` |
| Landscape product scene, card cover, architectural/space rendering | `4:3` |
| Cinematic ultra-wide scene, panoramic banner, immersive background | `21:9` |
| User did not specify a use case | Scene image: `16:9`; single-subject asset: `1:1` |

Poster / marketing image aspect ratio by distribution channel:

| Distribution Channel or Keywords | `--aspect-ratio` |
| --- | --- |
| WeChat Moments, Xiaohongshu, Douyin cover, Story, vertical social media marketing poster | `9:16`; use `3:4` for an explicit magazine feel |
| WeChat Official Account header, website hero, YouTube thumbnail, horizontal lightbox/large screen | `16:9` |
| Instagram / Square, explicit square tile request | `1:1` |
| Just says "make a poster" without specifying a channel | `9:16` |

When the user says "poster", first match the distribution channel; use `16:9` for explicit horizontal covers, websites, or YouTube.

- When the user provides explicit pixel dimensions, use `--size <width*height>`.
- Do not pass `4:5`, `3:2`, `2:3`, or other ratios not listed in the current CLI's image size mapping.

## Prompt Compilation Rules

Image prompts should be organized in the following order; prefer Simplified Chinese, but universal image quality or photography terms may remain in English:

1. Medium: real photography, 3D render, hand-drawn illustration, product photography, movie poster, infographic, etc.
2. Subject: characters, products, brand elements, actions, poses, or core objects — place important subjects in the first 10–20 words.
3. Details: materials, textures, expressions, clothing, props, craftsmanship, and visible selling points.
4. Environment & Composition: location, background layers, shot scale, camera position, whitespace, lighting, color.
5. Quality & Constraints: sharp focus, realistic materials, clean background, no watermarks, no garbled text, etc.

Rules for converting natural language:

- Convert "premium feel" into specific visuals: low-saturation palette, soft rim lighting, fine materials, clean background.
- Convert "cute" into specific visuals: rounded contours, bright eyes, soft pastels, toy or illustration quality.
- Convert "cinematic" into specific visuals: shallow depth of field, backlight, film grain, high dynamic range, widescreen composition.
- When the image contains text, write the exact copy in Chinese quotation marks in the prompt and reserve layout space; do not promise 100% text accuracy.
- When the user requests "no watermark / no text / no deformed hands", use `--negative-prompt`; do not pile on lengthy negative terms when there are no explicit negative requirements.
- Use `--n <number>` for multiple same-theme variations; split into separate commands when themes differ significantly.

## Common Templates

Single-subject product image:

```text
Product photography, [product name] centered in frame, fully showing subject silhouette and key materials, [core selling point details] clearly visible, clean background, soft studio lighting, subtle shadow, realistic materials, high detail, sharp focus
```

Landscape scene poster:

```text
Cinematic poster style, [subject] positioned at the rule-of-thirds line, [scene and atmosphere], [action or emotion], [foreground/midground/background layers], clean whitespace reserved for title area, cinematic lighting, high dynamic range, sharp details
```

Reference-image-to-image:

```text
Based on reference image, maintain [subject/product/person] core appearance and proportions, transform the scene to [new scene/new style], [parts to change], [parts to keep], unified lighting, realistic materials, clean composition
```

## Self-Check Checklist

- Did you explicitly pass the reference image URL or mediaId rather than just saying "reference" in the prompt? Were local images uploaded first and did you wait for status `Normal`?
- For the same local image within the same task, did you reuse the already-recorded mediaId?
- Does the aspect ratio match the use case or distribution channel? Did you use `9:16` for marketing posters without a specified channel?
- Does the prompt include medium, subject, details, environment & composition, and quality constraints?
- Did you avoid non-visualizable words like "looks good", "make it premium", "you know what I mean"?
- Did you avoid proactively overriding model, resolution, or size unless the user explicitly requested it?
- Did you present the dry-run estimated credits first and submit with `--yes` only after explicit user confirmation?
