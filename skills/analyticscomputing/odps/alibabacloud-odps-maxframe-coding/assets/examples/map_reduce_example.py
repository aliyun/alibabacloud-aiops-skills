"""
Example: Custom aggregation with DataFrame.mf.map_reduce.

Built-in aggregations cannot express custom group logic (here: counting
words inside a text column). map_reduce runs the mapper on data chunks,
shuffles mapper output by group_cols, then runs the reducer per key.
It is a shortcut for:

    df.mf.apply_chunk(mapper).groupby(group_cols).mf.apply_chunk(reducer)

TIP: pass `combiner=` to pre-aggregate mapper output before the shuffle
when group keys have high cardinality.

Environment variables required:
- ODPS_PROJECT, ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_ENDPOINT
"""

import logging
import os
from collections import defaultdict

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
    df = md.read_pandas(
        pd.DataFrame(
            {
                "doc_id": [1, 2, 3, 4],
                "content": [
                    "hello maxframe",
                    "hello odps",
                    "maxframe udf",
                    "odps sql",
                ],
            }
        )
    )

    def mapper(batch):
        # Receives a pandas DataFrame chunk; emits (key, partial_value) rows.
        word_to_count = defaultdict(int)
        for text in batch["content"]:
            for w in text.split():
                word_to_count[w] += 1
        return pd.DataFrame(
            [(w, c) for w, c in word_to_count.items()], columns=["word", "cnt"]
        )

    class WordCountReducer:
        # One reducer instance per key. Batches of that key arrive via
        # __call__; end=True marks the last batch, whose return value is
        # the final output row(s) for the key.
        def __init__(self):
            self._total = 0

        def __call__(self, batch, end=False):
            key = None
            for row in batch.itertuples(index=False):
                key = row[0]
                self._total += row[1]
            if end:
                return pd.DataFrame([[key, self._total]], columns=["word", "cnt"])

        def close(self):
            # Cleanup hook (connections, temp files), called after the last batch.
            pass

    result = df.mf.map_reduce(
        mapper,
        WordCountReducer,
        group_cols=["word"],
        mapper_dtypes={"word": "str", "cnt": "int64"},
        mapper_index=pd.Index([0]),
        reducer_dtypes={"word": "str", "cnt": "int64"},
        reducer_index=pd.Index([0]),
        ignore_index=True,
    )
    print(result.execute().fetch())

finally:
    session.destroy()
