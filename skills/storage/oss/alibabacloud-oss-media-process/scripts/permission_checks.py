"""Shared RAM permission checks for OSS and IMM operations."""

import credential


def check_oss_permission(bucket: str, region: str):
    """Check OSS bucket access permission by calling GetBucketInfo."""
    try:
        import oss2
    except ImportError:
        return False, "oss2 SDK not installed"

    if not credential.has_credential_material():
        return False, "AccessKey not configured"

    endpoint = f"https://oss-{region}.aliyuncs.com"
    auth = oss2.ProviderAuth(credential.get_oss_credentials_provider())
    bucket_obj = oss2.Bucket(
        auth, endpoint, bucket,
        connect_timeout=(10, 30),
        app_name=credential.USER_AGENT,
    )

    try:
        bucket_obj.get_bucket_info()
        return True, ""
    except oss2.exceptions.NoSuchBucket:
        return False, f"Bucket '{bucket}' does not exist in region '{region}'"
    except oss2.exceptions.AccessDenied:
        return False, "Access denied to bucket (lacks OSS read permission)"
    except oss2.exceptions.ServerError as exc:
        details = getattr(exc, "details", {})
        code = details.get("Code", "") if isinstance(details, dict) else ""
        if code == "InvalidAccessKeyId":
            return False, "Invalid AccessKey ID"
        return False, f"OSS error: {code or exc}"
    except Exception as exc:
        return False, f"Unexpected error: {exc}"


def check_imm_permission(project: str, region: str):
    """Check IMM project access permission by calling GetProject."""
    if not project:
        return None, ""

    try:
        from alibabacloud_imm20200930.client import Client
        from alibabacloud_imm20200930 import models
        from alibabacloud_tea_openapi.models import Config
    except ImportError:
        return False, "IMM SDK not installed"

    credential_client = credential.get_credential_client(required=False)
    if credential_client is None:
        return False, "AccessKey not configured"

    imm_region = region.replace("oss-", "")
    config = Config(
        credential=credential_client,
        endpoint=f"imm.{imm_region}.aliyuncs.com",
        region_id=imm_region,
        connect_timeout=10,
        read_timeout=30,
        user_agent=credential.USER_AGENT,
    )
    client = Client(config)

    try:
        req = models.GetProjectRequest(project_name=project)
        resp = client.get_project(req)
        proj = getattr(resp.body, "project", None)
        if proj:
            return True, ""
        return False, f"Project '{project}' not found"
    except Exception as exc:
        error_str = str(exc)
        if "Forbidden" in error_str or "AccessDenied" in error_str:
            return False, "Access denied to IMM project (lacks IMM permission)"
        return False, f"IMM check failed: {exc}"
