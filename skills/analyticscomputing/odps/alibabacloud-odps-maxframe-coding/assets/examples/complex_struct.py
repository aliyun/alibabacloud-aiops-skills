"""
Example: Processing complex structured data with groupby and apply_chunk.

This example demonstrates how to process complex data structures using
groupby operations with custom chunk processing.

Environment variables required:
- ODPS_PROJECT, ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_ENDPOINT
"""

import os

import dotenv
import maxframe.dataframe as md
import pandas as pd
from maxframe import options
from maxframe.dataframe.utils import parse_index
from maxframe.session import new_session
from odps import ODPS
from pandas.api.types import pandas_dtype

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

# Sample data
data = {
    "department": ["HR", "Tech", "HR", "Tech"],
    "salary": [6000, 8000, 7000, 9000],
    "experience": [3, 5, 4, 6],
}

try:
    df = md.DataFrame(pd.DataFrame(data))

    def process_each_department(chunk):
        """Process each department group."""
        print(chunk, flush=True)
        return pd.DataFrame(
            {"salary": [chunk["salary"].mean()], "experience": [chunk["experience"].mean()]}
        )

    # Apply chunk processing with groupby
    grouped = df.groupby(["department"], group_keys=True).mf.apply_chunk(
        process_each_department,
        output_type="dataframe",
        dtypes=pd.Series(
            [pandas_dtype("float64"), pandas_dtype("float64")],
            index=["salary", "experience"],
        ),
        skip_infer=True,
        index=parse_index(pd.MultiIndex.from_product([[""], [0]])),
    )

    result = grouped.execute()
    print("Result:")
    print(result)

finally:
    session.destroy()
