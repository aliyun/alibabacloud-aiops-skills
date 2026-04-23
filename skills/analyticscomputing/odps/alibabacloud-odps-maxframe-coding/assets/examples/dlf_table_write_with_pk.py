"""
Example: Writing to DLF PK (Primary Key) tables with binary data handling.

This example demonstrates how to write to DLF tables with primary keys,
including handling binary data types.

Environment variables required:
- ODPS_PROJECT, ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_ENDPOINT
"""

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

# Replace with your actual table names
input_table = "your_project.your_schema.your_input_table"  # DLF external table
output_table = "your_project.your_schema.your_output_table"  # DLF external table
pk_table = "your_project.your_schema.your_pk_table"  # DLF PK table
lifecycle = 30

# Configure SQL settings for DLF and PK table support
options.sql.enable_mcqa = False
options.sql.settings = {
    "odps.namespace.schema": "true",
    "odps.sql.allow.fullscan": "true",
    "odps.sql.enable.distributed.limit": "true",  # Enable distributed limit
    "odps.session.image": "maxframe_service_dpe_runtime",
    "odps.maxframe.resolve_dlf_tables": "true",  # Support DLF external tables
    "odps.sql.type.system.odps2": "true",  # Support DLF PK tables
}

options.dag.settings = {
    "engine_order": ["MCSQL"],
    "unavailable_engines": ["DPE", "SPE"],
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

try:
    # Write to DLF Append table (default)
    df = md.read_odps_table(input_table)
    md.to_odps_table(df, output_table, lifecycle=lifecycle, overwrite=True, index=True).execute()

    # Write to DLF PK table with binary data
    df = pd.DataFrame(
        {
            "userid": [11, 22],
            "username": ["name1", "name2"],
            "userbyte": [b"binary_data_11", b"binary_data_22"],
        }
    )

    # Fix incompatible type STRING with destination column userbyte
    # Use Arrow binary type for proper binary data handling
    new_data = md.DataFrame(df.astype({"userbyte": pd.ArrowDtype(pa.binary())}))
    new_data.to_odps_table(f"{pk_table}", overwrite=True).execute()

finally:
    session.destroy()
