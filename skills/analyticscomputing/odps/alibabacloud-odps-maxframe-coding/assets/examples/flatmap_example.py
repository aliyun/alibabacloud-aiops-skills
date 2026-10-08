"""
Example: Explode one row into many rows with DataFrame.mf.flatmap.

Each input row carries a JSON array field. flatmap applies a function to
every row and flattens the returned iterables into output rows
(one input row -> 0..N output rows).

NOTE: flatmap has NO type inference. `dtypes` is required.

Environment variables required:
- ODPS_PROJECT, ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_ENDPOINT
"""

import json
import logging
import os

import dotenv
import maxframe.dataframe as md
import pandas as pd
from maxframe.session import new_session
from odps import ODPS

logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
# Replace with your actual .env file path or use environment variables directly
dotenv.load_dotenv()

import re
from pathlib import Path

skill_manifest = Path("references/manifest.json")  # skill version source of truth
if not skill_manifest.is_file():
    raise RuntimeError(f"Skill manifest not found: {skill_manifest.resolve()}")
skill_version = json.loads(skill_manifest.read_text()).get("version", "")
if not re.fullmatch(r"\d+\.\d+\.\d+", skill_version):
    raise RuntimeError(f"Invalid skill version in {skill_manifest}: {skill_version!r}")

session_id = os.urandom(16).hex()  # fresh 32-char hex session ID per run
o = ODPS(
    access_id=os.getenv("ODPS_ACCESS_ID"),
    secret_access_key=os.getenv("ODPS_ACCESS_KEY"),
    project=os.getenv("ODPS_PROJECT"),
    endpoint=os.getenv("ODPS_ENDPOINT"),
    user_agent=(f'AlibabaCloud-Agent-Skills/alibabacloud-odps-maxframe-coding/{session_id} skill-version/{skill_version}')
)

session = new_session(o)

try:
    df = md.read_pandas(
        pd.DataFrame(
            {
                "event_id": [1, 2, 3],
                "user_id": ["u1", "u2", "u3"],
                "tags": ['["click", "view"]', '["buy"]', "[]"],
            }
        )
    )

    def explode_tags(row):
        # Return an iterable; each element becomes one output row.
        # Returning an empty list drops the input row from the output.
        return [
            {"event_id": row["event_id"], "user_id": row["user_id"], "tag": tag}
            for tag in json.loads(row["tags"])
        ]

    result = df.mf.flatmap(
        explode_tags,
        dtypes={"event_id": "int64", "user_id": "str", "tag": "str"},
    )
    print(result.execute().fetch())

finally:
    session.destroy()
