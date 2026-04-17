# OSS upload (for EMO / AA)

Local files must be uploaded to OSS first; pass the public URL to DashScope.

## Environment variables

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=xxx
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=xxx
export OSS_BUCKET=your-bucket
export OSS_ENDPOINT=oss-cn-beijing.aliyuncs.com
```

## Python examples

### Public bucket (direct public URL)

```python
import os
import oss2


def upload_to_oss(local_path: str, oss_key: str) -> str:
    auth = oss2.Auth(
        os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"],
        os.environ["ALIBABA_CLOUD_ACCESS_KEY_SECRET"],
    )
    bucket_name = os.environ["OSS_BUCKET"]
    endpoint = os.environ.get("OSS_ENDPOINT", "oss-cn-beijing.aliyuncs.com")
    bucket = oss2.Bucket(auth, f"https://{endpoint}", bucket_name)
    bucket.put_object_from_file(oss_key, local_path)
    return f"https://{bucket_name}.{endpoint}/{oss_key}"
```

### Private bucket (signed URL, default 3-day expiry)

```python
import os
import oss2

DEFAULT_EXPIRES = 3 * 24 * 3600  # 3 days, seconds


def upload_to_oss(local_path: str, oss_key: str, expires: int = DEFAULT_EXPIRES) -> str:
    """
    Upload a file to a private OSS bucket and return a signed temporary URL.

    Args:
        local_path: Local file path
        oss_key:    OSS object key (e.g. "avatars/face.jpg")
        expires:    Signed URL lifetime in seconds (default 3 days)

    Returns:
        Signed publicly reachable URL
    """
    auth = oss2.Auth(
        os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"],
        os.environ["ALIBABA_CLOUD_ACCESS_KEY_SECRET"],
    )
    bucket_name = os.environ["OSS_BUCKET"]
    endpoint = os.environ.get("OSS_ENDPOINT", "oss-cn-beijing.aliyuncs.com")
    bucket = oss2.Bucket(auth, f"https://{endpoint}", bucket_name)

    bucket.put_object_from_file(oss_key, local_path)

    signed_url = bucket.sign_url("GET", oss_key, expires)
    return signed_url
```

#### Usage

```python
url = upload_to_oss("./face.jpg", "avatars/face.jpg")
# → https://your-bucket.oss-cn-beijing.aliyuncs.com/avatars/face.jpg?OSSAccessKeyId=...&Expires=...&Signature=...

# Custom expiry (7 days)
url = upload_to_oss("./speech.mp3", "audio/speech.mp3", expires=7 * 24 * 3600)
```

## Notes

- The URL must be reachable on the public internet (http/https); DashScope must download it directly.
- Signed URL lifetime should cover task duration (EMO jobs often 2–10 minutes; 3 days is plenty).
- For private buckets use a signed URL; **do not** pass intranet URLs or `oss://` to DashScope.
- Consider OSS lifecycle rules to purge temporary assets (e.g. delete after 7 days).
- `bucket.sign_url()` returns a `str` usable as `image_url` / `audio_url`.
