"""
Example: Two-table pairwise matching with DataFrame.mf.cartesian_chunk.

func runs on EVERY pair of (left chunk, right chunk) and receives two
pandas DataFrames. Use it for two-table logic that merge/join cannot
express, e.g. matching every product against every blacklist rule.

NOTE: cartesian_chunk is not covered by lookup_operator.py or the bundled
API docs; see references/practical-guides/udf-development-guide.md.
Output can grow quadratically - filter aggressively inside func.

Environment variables required:
- ODPS_PROJECT, ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_ENDPOINT
"""

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

import json
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
    products = md.read_pandas(
        pd.DataFrame(
            {
                "product_id": ["p1", "p2", "p3"],
                "title": ["fake brand shoes", "organic green tea", "replica watch"],
            }
        )
    )
    rules = md.read_pandas(
        pd.DataFrame(
            {
                "rule_id": ["r1", "r2"],
                "keyword": ["fake", "replica"],
            }
        )
    )

    def match_rules(product_chunk, rule_chunk):
        # product_chunk / rule_chunk: pandas DataFrames from each input.
        pairs = product_chunk.merge(rule_chunk, how="cross")
        hit = [
            keyword in title
            for title, keyword in zip(pairs["title"], pairs["keyword"])
        ]
        return pairs.loc[hit, ["product_id", "rule_id"]]

    result = products.mf.cartesian_chunk(
        rules,
        match_rules,
        output_type="dataframe",
        dtypes={"product_id": "str", "rule_id": "str"},
    )
    print(result.execute().fetch())

finally:
    session.destroy()
