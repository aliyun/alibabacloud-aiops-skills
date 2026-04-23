"""
Example: MaxFrame OSS Mount - Read Model Directory

Demonstrates how to use fs_mount to read files from OSS in a distributed manner.

Environment variables required:
- ODPS_PROJECT, ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_ENDPOINT
- OSS_MOUNT_PATH, OSS_MOUNT_ROLE_ARN
"""

import os
import time

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from maxframe import dataframe as md
from maxframe.config import options
from maxframe.session import new_session
from maxframe.udf import with_fs_mount, with_running_options
from odps import ODPS

load_dotenv()

# MaxFrame configuration
options.sql.enable_mcqa = False
options.sql.settings = {"odps.session.image": "maxframe_service_dpe_runtime"}
options.dag.settings = {"engine_order": ["DPE", "MCSQL", "SPE"]}

# ODPS connection
o = ODPS(
    access_id=os.getenv("ODPS_ACCESS_ID"),
    secret_access_key=os.getenv("ODPS_ACCESS_KEY"),
    project=os.getenv("ODPS_PROJECT"),
    endpoint=os.getenv("ODPS_ENDPOINT"),
    user_agent='AlibabaCloud-Agent-Skills/alibabacloud-odps-maxframe-coding'
)

session = new_session(o)
print(f"Session: {session.session_id}")
print(f"Logview: {session.get_logview_address()}")


# Define function to read entire directory
# NOTE: memory parameter is in GIGABYTES (GB), not MB!
# memory=4 means 4 GB, NOT 4096 MB
@with_running_options(engine="dpe", cpu=2, memory=4)
@with_fs_mount(
    os.getenv("OSS_MOUNT_PATH", "oss://YOUR_BUCKET/YOUR_PATH/"),
    "/mnt/model",
    storage_options={
        "role_arn": os.getenv("OSS_MOUNT_ROLE_ARN", "acs:ram::YOUR_ACCOUNT_ID:role/YOUR_ROLE")
    },
)
def read_model_directory(row):
    """Read all files in the model directory"""
    import json
    import os
    import time

    worker_id = row.get("worker_id", "UNKNOWN")
    model_dir = "/mnt/model"
    chunk_size = 4 * 1024 * 1024  # 4 MB
    start_time = time.time()

    total_bytes = 0
    files_read = 0
    file_details = []

    try:
        if not os.path.exists(model_dir):
            return {
                "worker_id": int(worker_id),
                "task_name": str(row.get("task_name", "unknown")),
                "status": "directory_not_found",
                "total_bytes": 0,
                "files_count": 0,
                "read_time": 0.0,
                "throughput_mbps": 0.0,
                "file_details": "[]",
            }

        for filename in os.listdir(model_dir):
            file_path = os.path.join(model_dir, filename)
            if not os.path.isfile(file_path):
                continue

            file_bytes = 0
            try:
                with open(file_path, "rb") as f:
                    while chunk := f.read(chunk_size):
                        file_bytes += len(chunk)
                        total_bytes += len(chunk)

                file_details.append(
                    {
                        "filename": filename,
                        "size_mb": round(file_bytes / 1024 / 1024, 2),
                    }
                )
                files_read += 1

            except Exception as e:
                file_details.append({"filename": filename, "error": str(e)})

        read_time = time.time() - start_time
        throughput_mbps = (total_bytes / 1024 / 1024) / read_time if read_time > 0 else 0

        print(
            f"[Worker {worker_id}] Read {files_read} files, {total_bytes / 1024**3:.2f} GB in {read_time:.2f}s ({throughput_mbps:.2f} MB/s)"
        )

        return {
            "worker_id": int(worker_id),
            "task_name": str(row.get("task_name", "unknown")),
            "status": "success",
            "total_bytes": int(total_bytes),
            "files_count": int(files_read),
            "read_time": float(read_time),
            "throughput_mbps": float(throughput_mbps),
            "file_details": json.dumps(file_details),
        }

    except Exception as e:
        print(f"[Worker {worker_id}] Error: {str(e)}")
        return {
            "worker_id": int(worker_id),
            "task_name": str(row.get("task_name", "unknown")),
            "status": f"error: {str(e)}",
            "total_bytes": int(total_bytes),
            "files_count": int(files_read),
            "read_time": float(time.time() - start_time),
            "throughput_mbps": 0.0,
            "file_details": "[]",
        }


# Create test tasks
num_workers = 10
print(f"\nCreating {num_workers} concurrent tasks...")

data = [{"worker_id": i, "task_name": f"read_dir_{i}"} for i in range(num_workers)]

try:

    df = md.DataFrame(pd.DataFrame(data))
    df_rebalanced = df.mf.rebalance(num_partitions=num_workers)

    # Define output types
    output_dtypes = df.dtypes.copy()
    output_dtypes.update(
        {
            "status": np.dtype("O"),
            "total_bytes": np.dtype("int64"),
            "files_count": np.dtype("int64"),
            "read_time": np.dtype("float64"),
            "throughput_mbps": np.dtype("float64"),
            "file_details": np.dtype("O"),
        }
    )

    # Execute
    print("Starting test...")
    test_start = time.time()

    result = (
        df_rebalanced.apply(
            read_model_directory,
            axis=1,
            dtypes=output_dtypes,
            output_type="dataframe",
            result_type="expand",
        )
        .execute()
        .fetch()
    )

    total_time = time.time() - test_start

    # Statistics
    successful = result[result["status"] == "success"]
    failed = result[result["status"] != "success"]

    print(f"\n{'='*60}")
    print(f"Total tasks: {len(result)} | Success: {len(successful)} | Failed: {len(failed)}")

    if len(successful) > 0:
        normal = successful[(successful["files_count"] > 0) & (successful["read_time"] > 0)]
        stats = normal if len(normal) > 0 else successful

        print("\nWorker Performance:")
        print(f"{'Worker':<8} {'Files':<8} {'Data(GB)':<12} {'Time(s)':<10} {'MB/s':<10}")
        print("-" * 60)
        for _, row in successful.iterrows():
            print(
                f"{row['worker_id']:<8} {row['files_count']:<8} "
                f"{row['total_bytes']/1024**3:<12.2f} {row['read_time']:<10.2f} {row['throughput_mbps']:<10.2f}"
            )

        print("\nSummary:")
        print(f"  Test time: {total_time:.2f}s")
        print(
            f"  Avg read time: {stats['read_time'].mean():.2f}s (min: {stats['read_time'].min():.2f}s, max: {stats['read_time'].max():.2f}s)"
        )
        print(f"  Avg throughput: {stats['throughput_mbps'].mean():.2f} MB/s")
        print(f"  Total data: {successful['total_bytes'].sum() / 1024**3:.2f} GB")
        print(
            f"  Aggregate throughput: {(successful['total_bytes'].sum() / 1024**2) / total_time:.2f} MB/s"
        )

        if len(stats) > 0:
            speedup = (stats["read_time"].mean() * len(stats)) / total_time if total_time > 0 else 0
            print(f"  Speedup: {speedup:.2f}x | Efficiency: {speedup / len(stats) * 100:.1f}%")

    if len(failed) > 0:
        print(f"\nFailed tasks: {failed[['worker_id', 'status']].to_string(index=False)}")

    print("Done!")
finally:
    session.destroy()
