"""
Example: Writing to DLF (Data Lake Formation) external tables.

This example demonstrates how to configure MaxFrame to write to DLF external tables.

Environment variables required:
- ODPS_PROJECT, ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_ENDPOINT
"""

import os

import dotenv
import maxframe.dataframe as md
from maxframe import options
from maxframe.session import new_session
from odps import ODPS

# Load environment variables
dotenv.load_dotenv()

# Replace with your actual table names
input_table = "your_project.your_schema.your_input_table"  # DLF external table
output_table = "your_project.your_schema.your_output_table"  # DLF external table
lifecycle = 30

# Configure SQL settings for DLF support
options.sql.enable_mcqa = False
options.sql.settings = {
    "odps.namespace.schema": "true",
    "odps.sql.allow.fullscan": "true",
    "odps.sql.enable.distributed.limit": "true",  # Enable distributed limit
    "odps.session.image": "maxframe_service_dpe_runtime",
    "odps.maxframe.resolve_dlf_tables": "true",  # Support DLF external tables
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

# Create session (adjust major_version if needed)
session = new_session(o)

try:
    # Read from DLF table
    df = md.read_odps_query(f"SELECT * FROM {input_table} LIMIT 100")

    # Write to DLF table
    md.to_odps_table(df, output_table, lifecycle=lifecycle, overwrite=True, index=True).execute()

finally:
    session.destroy()
