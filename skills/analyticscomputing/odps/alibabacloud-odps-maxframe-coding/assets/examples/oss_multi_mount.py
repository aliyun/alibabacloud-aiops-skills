"""
Minimum example showing how to use oss_mount with single and multiple mounting.

Environment variables required:
- ODPS_PROJECT, ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_ENDPOINT
- OSS_BUCKET_NAME, OSS_ENDPOINT, OSS_ROLE_ARN
"""

import os

import dotenv
import maxframe.dataframe as md
from maxframe.config import options
from maxframe.session import new_session
from maxframe.udf import with_fs_mount, with_running_options
from odps import ODPS

# Load environment variables from .env file
dotenv.load_dotenv()

options.sql.enable_mcqa = False
options.sql.settings = {"odps.session.image": "maxframe_service_dpe_runtime"}
options.dag.settings = {"engine_order": ["DPE", "MCSQL", "SPE"]}

# Initialize ODPS and session
o = ODPS(
    access_id=os.getenv("ODPS_ACCESS_ID"),
    secret_access_key=os.getenv("ODPS_ACCESS_KEY"),
    project=os.getenv("ODPS_PROJECT"),
    endpoint=os.getenv("ODPS_ENDPOINT"),
    user_agent='AlibabaCloud-Agent-Skills/alibabacloud-odps-maxframe-coding'
)

session = new_session(o, major_version=os.getenv("ODPS_MAJOR_VERSION", "default"))
print(f"Logview: {session.get_logview_address()}")
print(f"Session ID: {session.session_id}")


# Example 1: Single OSS mount
# NOTE: memory parameter is in GIGABYTES (GB), not MB!
# memory=2 means 2 GB, NOT 2048 MB
@with_running_options(engine="dpe", cpu=1, memory=2)
@with_fs_mount(
    f"oss://{os.getenv('OSS_ENDPOINT')}/{os.getenv('OSS_BUCKET_NAME')}/data/",
    "/mnt/oss_data",
    storage_options={"role_arn": os.getenv("OSS_ROLE_ARN")},
)
def process_with_single_mount(row):
    """Example with single OSS mount"""
    import os

    mount_path = "/mnt/oss_data"

    if os.path.exists(mount_path):
        files = os.listdir(mount_path)
        print(f"Single mount successful. Files: {files}")
    else:
        print("Single mount failed")

    return row


# Example 2: Multiple OSS mounts
# NOTE: memory parameter is in GIGABYTES (GB), not MB!
# memory=2 means 2 GB, NOT 2048 MB
@with_running_options(engine="dpe", cpu=1, memory=2)
@with_fs_mount(
    f"oss://{os.getenv('OSS_ENDPOINT')}/{os.getenv('OSS_BUCKET_NAME')}/data1/",
    "/mnt/oss_data1",
    storage_options={"role_arn": os.getenv("OSS_ROLE_ARN")},
)
@with_fs_mount(
    f"oss://{os.getenv('OSS_ENDPOINT')}/{os.getenv('OSS_BUCKET_NAME')}/data2/",
    "/mnt/oss_data2",
    storage_options={"role_arn": os.getenv("OSS_ROLE_ARN")},
)
@with_fs_mount(
    f"oss://{os.getenv('OSS_ENDPOINT')}/{os.getenv('OSS_BUCKET_NAME')}/data3/",
    "/mnt/oss_data3",
    storage_options={"role_arn": os.getenv("OSS_ROLE_ARN")},
)
def process_with_multiple_mounts(row):
    """Example with multiple OSS mounts"""
    import os

    mount_paths = ["/mnt/oss_data1", "/mnt/oss_data2", "/mnt/oss_data3"]

    for mount_path in mount_paths:
        if os.path.exists(mount_path):
            files = os.listdir(mount_path)
            print(f"Mount {mount_path} successful. Files: {files}")
        else:
            print(f"Mount {mount_path} failed")

    return row


# Create a simple test dataframe
df = md.DataFrame({"id": [1, 2, 3]})

# Test single mount
print("\n=== Testing Single Mount ===")
df_single = df.apply(
    process_with_single_mount,
    axis=1,
    dtypes=df.dtypes,
    output_type="dataframe",
    result_type="expand",
    skip_infer=True,
)
result_single = df_single.execute().fetch()
print(result_single)

# Test multiple mounts
print("\n=== Testing Multiple Mounts ===")
df_multi = df.apply(
    process_with_multiple_mounts,
    axis=1,
    dtypes=df.dtypes,
    output_type="dataframe",
    result_type="expand",
    skip_infer=True,
)
result_multi = df_multi.execute().fetch()
print(result_multi)

print("\nAll tests completed!")

# Clean up
session.destroy()
