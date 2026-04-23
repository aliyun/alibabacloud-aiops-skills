"""
Example: Basic AI function usage with MaxFrame ManagedTextLLM.

This example demonstrates the minimum setup for using MaxFrame's AI functions
with the managed LLM models. It shows how to perform basic Q&A tasks using
the built-in managed models without requiring external API keys.

Environment variables required:
- ODPS_PROJECT, ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_ENDPOINT
"""

import os

import dotenv
import maxframe.dataframe as md
from maxframe import options
from maxframe.learn.contrib.llm.models.managed import ManagedTextLLM
from maxframe.session import new_session
from odps import ODPS

# Load environment variables from .env file
# Replace with your actual .env file path or use environment variables directly
dotenv.load_dotenv()

# Configure SQL settings for AI functions
options.sql.settings = {
    "odps.sql.split.dop": '{"*":10}',
}

# Create ODPS connection
o = ODPS(
    access_id=os.getenv("ODPS_ACCESS_ID"),
    secret_access_key=os.getenv("ODPS_ACCESS_KEY"),
    project=os.getenv("ODPS_PROJECT"),
    endpoint=os.getenv("ODPS_ENDPOINT"),
    user_agent='AlibabaCloud-Agent-Skills/alibabacloud-odps-maxframe-coding'
)

# Create MaxFrame session
session = new_session(o)
print(f"Session created: {session.session_id}")

# Create a DataFrame with questions
df = md.DataFrame(
    {
        "query": [
            "地球距离太阳的平均距离是多少？",
            "美国独立战争是从哪一年开始的？",
            "什么是水的沸点？",
        ]
    }
)
df.execute()

# Use ManagedTextLLM for inference
# Available managed models: qwen2.5-0.5b-instruct, qwen2.5-1.5b-instruct,
# qwen2.5-3b-instruct, Qwen2.5-7B-instruct, DeepSeek-R1-Distill-Qwen-1.5B, etc.
llm = ManagedTextLLM(name="qwen2.5-1.5b-instruct")

# Define prompt template
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "{query}"},
]

# Generate responses
result = llm.generate(df, prompt_template=messages)
result.execute()

# Display results
print("AI Function Results:")
print(
    result.response.mf.flatjson(
        ["$.choices[0].message.content"],
        dtypes=["str"],
    )
    .execute()
    .fetch()
)

# Clean up session
session.destroy()
print("Session destroyed")
