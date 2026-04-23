"""
Example: Processing complex Arrow structures with groupby operations.

This example demonstrates how to work with complex Arrow data types
and process them using groupby with apply_chunk.

Environment variables required:
- ODPS_PROJECT, ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_ENDPOINT
"""

import json
import os

import dotenv
import maxframe.dataframe as md
import pandas as pd
import pyarrow as pa
from maxframe import options
from maxframe.session import new_session
from odps import ODPS

# Load environment variables
dotenv.load_dotenv()

# Configure SQL settings
options.sql.enable_mcqa = False
options.sql.settings = {
    "odps.namespace.schema": "true",
    "odps.sql.allow.fullscan": "true",
    "odps.sql.enable.distributed.limit": "true",
    "odps.session.image": "common",
    "odps.maxframe.resolve_dlf_tables": "true",
    "odps.sql.type.system.odps2": "true",
}
options.dag.settings = {
    "engine_order": ["MCSQL", "DPE"],
}

# Create ODPS connection
o = ODPS(
    access_id=os.getenv("ODPS_ACCESS_ID"),
    secret_access_key=os.getenv("ODPS_ACCESS_KEY"),
    project=os.getenv("ODPS_PROJECT"),
    endpoint=os.getenv("ODPS_ENDPOINT"),
    user_agent='AlibabaCloud-Agent-Skills/alibabacloud-odps-maxframe-coding'
)

session = new_session(o)

# Define Arrow struct type
struct_type = [
    pa.field("calibration_bucket", pa.string()),
    pa.field("calibration_file_name", pa.string()),
    pa.field("calibration_path", pa.string()),
    pa.field("data_id", pa.string()),
    pa.field("datanode_info", pa.string()),
    pa.field("hdfs_path", pa.string()),
    pa.field("meta_uuid", pa.string()),
    pa.field("sensor_type", pa.string()),
    pa.field("timestamp_bucket", pa.string()),
    pa.field("timestamp_path", pa.string()),
]

# Sample data
data = {
    "calibration_bucket": ["bucket1", "bucket1", "bucket2", "bucket2", "bucket1"],
    "calibration_file_name": ["file1", "file2", "file3", "file4", "file5"],
    "calibration_path": ["/path1", "/path2", "/path3", "/path4", "/path5"],
    "data_id": ["id1", "id2", "id3", "id4", "id5"],
    "datanode_info": ["node1", "node2", "node3", "node4", "node5"],
    "hdfs_path": ["/hdfs1", "/hdfs2", "/hdfs3", "/hdfs4", "/hdfs5"],
    "meta_uuid": ["uuid1", "uuid1", "uuid2", "uuid2", "uuid1"],
    "sensor_type": ["type1", "type1", "type2", "type2", "type1"],
    "timestamp_bucket": ["ts1", "ts1", "ts2", "ts2", "ts1"],
    "timestamp_path": ["/ts1", "/ts1", "/ts2", "/ts2", "/ts1"],
}

try:

    df = md.DataFrame(pd.DataFrame(data))

    def process_group(chunk):
        """Process a group and convert records to JSON."""
        records = chunk.to_dict(orient="records")
        return pd.DataFrame({"records": [json.dumps(records)]})

    # Group by meta_uuid and process
    grouped = df.groupby("meta_uuid", group_keys=True).mf.apply_chunk(
        process_group,
        output_type="dataframe",
        dtypes=pd.Series(
            [pd.ArrowDtype(pa.string())],
            index=["records"],
        ),
        skip_infer=True,
    )

    result = grouped.execute()
    print("Result:")
    print(result)

finally:
    session.destroy()
