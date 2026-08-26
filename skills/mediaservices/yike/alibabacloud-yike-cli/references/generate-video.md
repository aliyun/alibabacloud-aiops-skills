# Video Generation Operation Reference

When the following scenarios are triggered, convert user requirements into prompt, taskType, aspect ratio, duration, and reference asset parameters for `yike generate video`. See [`generate.md`](generate.md) for command parameters, defaults, and execution rules.

## Scope

Read this document when the following needs are triggered:

- "Generate a video", "make an ad clip / product short / animated cover / transition shot" — text-to-video.
- "Animate this image", "use this image as the first frame / subject reference", "generate a video from this reference image" — image-to-video.
- "Reference this video's motion / camera / pacing / style" — reference-video generation.
- The user provides only a vague video intent, and the Agent needs to fill in action, camera movement, aspect ratio, and duration.

This document only covers video generation.

## Execution Order

1. Identify the true mediaType of each reference input: upload local image/video paths or Agent conversation attachments first; if an existing mediaId's type is unknown, first run `yike media info <mediaId> --format json`. Images and videos retain their respective types — do not guess based on model name or taskType.
2. Select taskType: use `reference_to_video` when a video reference exists; use `image_to_video` when only an image reference exists and the user has not specified an R2V model; use `text_to_video` when neither exists. When the user specifies an R2V model with only an image provided, pass `--reference-image <mediaId> --task-type reference_to_video`.
3. When the user asks about or explicitly specifies a model, read [`video-model-capabilities.md`](video-model-capabilities.md) to verify reference media types and counts. If the model is not recorded, report insufficient information — do not guess based on names.
4. Set `--aspect-ratio` based on the playback scenario: landscape, portrait, square feed, product loop, animated wallpaper, etc.
5. Use the specified duration if the user provides one; use 5 seconds if not specified; set a longer `--duration` when the user explicitly requests a complete extended action.
6. Compile the prompt: must include subject, starting state, action changes, ending state, camera language, and visual quality.
7. Run with complete parameters using `--dry-run --format json`; present the estimated credits to the user and wait for explicit confirmation. After confirmation, keep generation parameters unchanged and replace `--dry-run` with `--yes` to submit. Re-estimate and re-confirm when parameters change.

## taskType & Reference Assets

| User Expression | Parameter Selection |
| --- | --- |
| "Generate a video…" with no reference assets | Do not pass reference parameters; defaults to `text_to_video` |
| "Animate this image / use this image as first frame / keep this subject and animate" | `--reference-image <urlOrMediaId>`; defaults to `image_to_video`. Must use mediaId when explicitly specifying R2V |
| "Reference this video's motion / camera / pacing / style" | `--reference-video <mediaId>`; defaults to `reference_to_video` |
| Local image path or Agent conversation image attachment | Upload first per [`upload.md`](upload.md); after status is `Normal`, pass `--reference-image <mediaId>` |
| Local video path or Agent conversation video attachment | Upload first per [`upload.md`](upload.md); after status is `Normal`, pass `--reference-video <mediaId>` |
| Video generation with only `--reference-media-id` and confirmed mediaType is video | Use `reference_to_video` |
| mediaId intended as a first-frame image | Prefer `--reference-image <mediaId>`; do not use only `--reference-media-id` |
| Using an R2V model with an image as reference | Pass `--reference-image <mediaId> --task-type reference_to_video`; do not use `--reference-video` or `--reference-media-id` |

Upload local paths first, then select the typed parameter based on the upload result or `media info` mediaType; stop if the type does not match the user's specified usage.

Image mediaIds use `--reference-image`; only video mediaIds may use `--reference-video` or video generation's `--reference-media-id`.

For `reference_to_video`, both image and video references use mediaId, passing `--reference-image` and `--reference-video` respectively. Stop and report an error if an HTTP(S) URL is received.

`reference_to_video` / R2V is a task classification and does not mean the reference input must be a video. The taskType model groupings in help also do not declare reference input capabilities.

## Aspect Ratio Selection

Only use aspect ratios currently supported by CLI video generation: `16:9`, `9:16`, `1:1`, `3:4`, `4:3`.

| User Use Case or Keywords | `--aspect-ratio` |
| --- | --- |
| Landscape ad clip, YouTube, website video, demo reel, cinematic shot | `16:9` |
| Douyin, Kuaishou, Xiaohongshu Reels/Story, mobile portrait ad, vertical animated cover | `9:16` |
| Product loop GIF, social media feed, animated avatar, square tile | `1:1` |
| Half-body portrait, vertical product showcase, magazine-style animated poster | `3:4` |
| Retro TV, surveillance perspective, landscape product close-up | `4:3` |
| User did not specify a use case | Default `16:9`; `9:16` for explicit mobile; `1:1` for single-product loops |

- When the reference image has a clear aspect ratio and the user has not specified an output scenario, use the reference image's aspect ratio.
- When the user specifies an output scenario, explicitly pass `--aspect-ratio` per the scenario.

## Duration Selection

Use the default value of `5` seconds when the duration is not explicitly stated.

| User Requirement | `--duration` |
| --- | --- |
| Subtle motion effect, blink, wind blow, product micro-rotation, animated cover | `3` to `5` |
| Single complete action, product reveal, short ad shot | `5` |
| One camera push + subject action change | `6` to `8` |
| More complex but still single-shot continuous action | `8` to `10` |
| User explicitly requests longer | Pass the user's value; report the command error on failure — do not silently shorten |

Split multiple shots, multiple scenes, or complete narratives into separate video generations.

## Prompt Compilation Rules

Video prompts follow this structure:

1. Subject & Reference: who is in the frame; whether the reference asset is used for first frame, subject, style, motion, or camera.
2. Starting State: what the frame looks like in the first second.
3. Action Changes: how the subject moves, how the environment responds, how speed and mood change.
4. Physical Feedback: how gravity, wind, fabric, fluid, collision, reflections, or shadows change with motion — do not write only camera movement while the subject looks like a sticker.
5. Ending State: where the last second stops; whether a looping feel is needed.
6. Camera Language: shot scale, camera position, push/pull/pan/tilt, focal change, frame stability.
7. Quality Constraints: lighting, color, materials, sharpness, consistency, no watermarks or subtitles.

Rules for converting natural language:

- Convert "animate it" into filmable actions, e.g., "hair gently blown by wind, hem sways with movement, camera slowly pushes in".
- Convert "cool transition" into a transition mechanism, e.g., "camera pushes into the product's reflective surface; the reflection expands into the next layer's background light".
- Fill in physical feedback: wind blowing fabric/hair, liquid sloshing, smoke dispersing, footsteps kicking up dust, highlights and shadows sliding continuously as the product rotates, inertial pause after collision.
- For image-to-video, emphasize "maintain the reference image subject's appearance, clothing, materials, and proportions", describe only changing actions or camera, and specify how materials behave during motion.
- For reference-video generation, state that the reference video is used for "motion trajectory, camera pacing, or atmosphere" — do not simultaneously demand completely replacing all motion logic.
- Camera movement terms can be in Chinese or stable English terminology, e.g., `slow zoom in`, `pan right`, `tilt up`, `tracking shot`.
- Use `--negative-prompt` when strictly no subtitles, watermarks, or garbled text should appear; do not pile on negative terms when there are no explicit negative requirements.
- Do not promise audio.

## Common Templates

Text-to-video:

```text
[subject] appears in [scene], opening frame shows [first-second state], then [main action], [physical feedback: wind/fabric/fluid/shadow-highlight changes], finally resting at [ending state]. Camera [shot scale and movement], lighting [color and mood], stable frame, consistent subject details, cinematic lighting, sharp focus
```

Image-to-video:

```text
Maintain the appearance, proportions, materials, and colors of [subject] from the reference image. Opening frame continues the reference image composition, then [specific action], [physical feedback: material highlight sliding, fabric/label slight sway, continuous shadow changes], camera [slow push-in/pan/slight orbit], finally resting at [ending state], natural lighting, stable frame, no watermarks no subtitles
```

Reference-video generation:

```text
Reference video is used to replicate motion rhythm and camera trajectory, replacing the subject with [new subject] in [new scene]. Maintain [motion/camera characteristics from reference video] while making [new subject actions and physical feedback] clearly visible, unified lighting, stable frame, sharp details
```

## Self-Check Checklist

- Did you correctly distinguish `--reference-image` from `--reference-video`?
- Did you select parameters based on the true mediaType, confirming that images under an R2V model still use `--reference-image` and did not fall into `--reference-video` or `--reference-media-id`?
- When explaining or explicitly using a model, did you read `video-model-capabilities.md` instead of guessing input capabilities from an `r2v` suffix or taskType?
- Were local attachments uploaded first with a wait for status `Normal`? Did you reuse existing mediaIds within the same task?
- Did you avoid writing only "animate it" without specifying action, starting point, ending point, physical feedback, and camera?
- Does the aspect ratio match the playback scenario?
- Did you keep the 5-second default when the duration was not specified?
- Did you avoid proactively overriding model, resolution, or size unless the user explicitly requested it?
- Did you present the dry-run estimated credits first and submit with `--yes` only after explicit user confirmation?
