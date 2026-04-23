"""
Example: GroupBy operations with apply_chunk for batch processing.

This example demonstrates how to use groupby with apply_chunk to process
data in batches efficiently.

Environment variables required:
- ODPS_PROJECT, ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_ENDPOINT
"""

import logging
import os

import dotenv
import maxframe.dataframe as md
import numpy as np
import pandas as pd
from maxframe.dataframe.utils import parse_index
from maxframe.session import new_session
from odps import ODPS

logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
# Replace with your actual .env file path or use environment variables directly
dotenv.load_dotenv()

o = ODPS(
    access_id=os.getenv("ODPS_ACCESS_ID"),
    secret_access_key=os.getenv("ODPS_ACCESS_KEY"),
    project=os.getenv("ODPS_PROJECT"),
    endpoint=os.getenv("ODPS_ENDPOINT"),
    user_agent='AlibabaCloud-Agent-Skills/alibabacloud-odps-maxframe-coding'
)

session = new_session(o)

try:
    # Create sample DataFrame
    df = md.read_pandas(
        pd.DataFrame(
            {
                "A": np.random.choice(["group1", "group2", "group3"], 3000),
                "B": np.random.randn(3000),
                "C": np.random.randn(3000),
                "D": np.random.randn(3000),
                "E": np.random.randn(3000),
            }
        )
    )
    df.execute()

    def process_batch(chunk):
        """Process a batch of data."""
        return chunk[["B"]]

    # Apply chunk processing with groupby
    result_df = df.groupby(["A"], group_keys=True).mf.apply_chunk(
        process_batch,
        batch_rows=1000,
        output_type="dataframe",
    )
    print(f"Result dtypes: {result_df.dtypes}")
    print(f"Result index: {result_df.index_value}")
    result_df.execute()

    def process_to_json(chunk):
        """Process chunk and convert to JSON string."""
        import json

        print(chunk, flush=True)
        print(f"Group shape: {chunk.shape}")
        list_value = json.dumps(chunk["B"].tolist(), ensure_ascii=False)
        result = pd.DataFrame({"B": [list_value]})
        print(result, flush=True)
        return result

    # Apply chunk with custom index
    result_df = df.groupby(["A"], group_keys=True).mf.apply_chunk(
        process_to_json,
        batch_rows=1000,
        output_type="dataframe",
        index=parse_index(pd.MultiIndex.from_product([[""], [0]])),
    )
    print(f"Result dtypes: {result_df.dtypes}")
    print(f"Result index: {result_df.index_value}")
    result_df.execute()

finally:
    session.destroy()
