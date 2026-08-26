# Video Model Reference Input Capabilities

Read this document when the user asks which video models accept image references, video references, or how many reference assets are allowed.

## Determination Rules

- `reference_to_video` / R2V is a task classification and does not mean the reference input must be a video.
- The taskType groupings in `yike generate video --help` only list model codes — they do not declare the reference media types a model accepts.
- Answer only for models recorded in the table below. If a model is not in the table, report that the current Skill does not have reference input capability information for that model.
- "Not declared" means the current capability record does not have that input type; do not rewrite this as "the server absolutely does not support it".
- Model availability is still subject to the current CLI help, account, and server response.

## Currently Recorded Models

| model | taskType | Image Reference | Video Reference |
| --- | --- | --- | --- |
| `happyhorse-1.1-r2v` | `reference_to_video` | Supported, up to 9 images | Not declared |
| `happyhorse-1.0-r2v` | `reference_to_video` | Supported, up to 9 images | Not declared |
| `wan2.7-r2v` | `reference_to_video` | Supported, up to 5 images | Supported, up to 5 videos |
| `wan2.6-r2v-flash` | `reference_to_video` | Supported, up to 5 images | Supported, up to 5 videos |
| `Wonder-Pro` | `reference_to_video` | Supported, up to 9 images | Supported, up to 3 videos |
| `Wonder-Standard` | `reference_to_video` | Supported, up to 9 images | Supported, up to 3 videos |

The Wonder series only appears in the `yike generate video --help` model catalog after the account is enabled, and becomes the video default model (`Wonder-Pro`). Availability is subject to the account and server response; when explicitly specified via `--model`, the table limits above still apply before submission.

## Parameter Selection

- Image references use `--reference-image <mediaId>`.
- Video references use `--reference-video <mediaId>`.
- With only images and explicit `reference_to_video`, the default model is `happyhorse-1.1-r2v`.
- With videos and `reference_to_video`, the default model is `wan2.7-r2v`.
- When the account has Wonder video series enabled, the above two defaults become `Wonder-Pro`.
- When the explicit model does not match recorded input capabilities, the CLI returns an error before submission; do not silently switch models or rewrite media types.
