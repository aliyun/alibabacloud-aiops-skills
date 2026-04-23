"""
Example: Using GPU Units (GU) with DPE engine for accelerated processing.

This example demonstrates how to use the @with_running_options decorator
to allocate GPU Units (GU) when running operations on the DPE engine.
GU allocation enables GPU-accelerated processing for compute-intensive tasks.

Environment variables required:
- ODPS_PROJECT, ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_ENDPOINT
"""

import os

import dotenv
import maxframe.dataframe as md
import numpy as np
from maxframe.config import options
from maxframe.session import new_session
from maxframe.udf import with_running_options
from odps import ODPS

# Load environment variables from .env file
# Replace with your actual .env file path or use environment variables directly
dotenv.load_dotenv()

# Configure DPE engine settings
options.dag.settings = {
    "engine_order": ["DPE"],
    "unavailable_engines": ["MCSQL", "SPE"],
}
options.sql.settings = {"odps.session.image": "maxframe_service_dpe_runtime"}
options.local_execution.enabled = False

# Create ODPS connection
o = ODPS(
    access_id=os.getenv("ODPS_ACCESS_ID"),
    secret_access_key=os.getenv("ODPS_ACCESS_KEY"),
    project=os.getenv("ODPS_PROJECT"),
    endpoint=os.getenv("ODPS_ENDPOINT"),
    tunnel_endpoint=os.getenv("ODPS_TUNNEL_ENDPOINT"),
    user_agent='AlibabaCloud-Agent-Skills/alibabacloud-odps-maxframe-coding'
)

# Create MaxFrame session
session = new_session(o)
print(f"Session created: {session.get_logview_address()}")


# Define a function that uses GPU resources
# Replace 'your_gu_quota' with your actual GU quota name
# NOTE: This example uses GPU Units (GU) instead of CPU/memory
# For CPU/memory allocation, use parameters like: cpu=2, memory=4 (memory in GB!)
@with_running_options(engine="dpe", gu=1, gu_quota="your_gu_quota")
def gpu_accelerated_process(row):
    """
    Process data with GPU acceleration.

    This function will be executed on DPE engine with 1 GU allocated.
    Replace this with your actual GPU-accelerated logic.
    """
    # Example: perform some computation
    result = row.copy()
    result["C"] = result["A"] * result["B"]
    return result


# Create sample DataFrame
df_input = md.DataFrame(
    {
        "A": np.random.randint(1, 100, 1000),
        "B": np.random.randint(1, 100, 1000),
    }
)

try:
    # Apply the GPU-accelerated function
    df_result = df_input.apply(
        gpu_accelerated_process,
        axis=1,
        dtypes=df_input.dtypes,
        output_type="dataframe",
        result_type="expand",
        skip_infer=True,
    )

    # Execute and fetch results
    result = df_result.execute().fetch()
    print(f"Processing completed. Result shape: {result.shape}")
    print(f"First 5 rows:\n{result.head()}")

finally:
    # Clean up session
    session.destroy()
    print("Session destroyed")
