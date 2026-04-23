# AI Function Guide

This guide covers how to use MaxFrame AI Function with GPU resources (GU) for large language model (LLM) offline inference.

## Overview

MaxFrame AI Function is an end-to-end solution for LLM offline inference on MaxCompute, integrating data processing with AI capabilities.

## Prerequisites

### Environment Requirements

| Requirement | Version/Description |
|-------------|---------------------|
| MaxFrame SDK | 2.3.0 or higher |
| Python | 3.11 |
| MaxCompute Project | GPU quota (GU) enabled |

### Permissions

- MaxCompute project-level read/write access
- Purchased MaxCompute GU quota (`gu_quota_name`)

## Environment Configuration

### Basic Setup

```python
import os
import maxframe.dataframe as md
import numpy as np
from maxframe import new_session
from maxframe.config import options
from maxframe.udf import with_running_options
from odps import ODPS
import logging

# Configure engine order
options.dag.settings = {
    "engine_order": ["DPE", "MCSQL"],
    "unavailable_engines": ["SPE"],
}

logging.basicConfig(level=logging.INFO)

# Initialize MaxFrame Session
o = ODPS(
    access_id=os.getenv('ODPS_ACCESS_ID'),
    secret_access_key=os.getenv('ODPS_ACCESS_KEY'),
    project=os.getenv('ODPS_PROJECT'),
    endpoint=os.getenv('ODPS_ENDPOINT'),
)

session = new_session(o)

# Set GU quota name (required for GPU usage)
options.session.gu_quota_name = "<your-gu-quota-name>"

print("LogView:", session.get_logview_address())
```

## Using Managed LLM Models

### Step 1: Prepare Input Data

```python
import pandas as pd

# Construct query list
query_list = [
    "What is the average distance from Earth to the Sun?",
    "What year did the American Revolutionary War begin?",
    "What is the boiling point of water?",
    "How to quickly relieve a headache?",
    "Who is the protagonist in the Harry Potter series?",
]

# Convert to MaxFrame DataFrame
df = md.DataFrame({"query": query_list})
df.execute()
```

### Step 2: Initialize LLM Instance

```python
from maxframe.learn.contrib.llm.models.managed import ManagedTextGenLLM

llm = ManagedTextGenLLM(
    name="Qwen3-4B-Instruct-2507-FP8"  # Model name must match exactly
)
```

**Note:** For supported models, refer to MaxFrame AI Function supported models documentation.

### Step 3: Define Prompt Template

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Please answer the following question: {query}"},
]
```

**Template Syntax:**

- Use `{column_name}` placeholders for DataFrame field substitution
- Supports multi-turn conversations (messages list)
- System prompt (`role: system`) sets model behavior

### Step 4: Execute Generation

```python
result_df = llm.generate(
    df,  # Input data
    prompt_template=messages,
    running_options={
        "max_tokens": 4096,  # Maximum output length
        "verbose": True,     # Enable verbose logging
    },
    params={"temperature": 0.7},
)

# Execute and fetch results
result_df.execute()
```

## Output Structure

The result DataFrame contains the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | Original input |
| `generated_text` | string | Model-generated response |
| `finish_reason` | string | Completion reason: `stop`, `length`, etc. |
| `usage.prompt_tokens` | int | Input token count |
| `usage.completion_tokens` | int | Output token count |
| `usage.total_tokens` | int | Total token count |

## Performance Tuning

### Optimization Guidelines

| Aspect | Recommendation |
|--------|----------------|
| Batch size | Keep batches < 100 to avoid OOM |
| GU allocation | `gu=2` for 4B models; larger models need more GU |
| Parallelism | MaxFrame auto-schedules; control with `num_workers` |
| Intermediate results | Save with `to_odps_table()` to avoid recomputation |
| Timeout | Set `timeout=3600` to prevent hanging |

## Debugging

### View Execution Logs

```python
print(session.get_logview_address())  # Click to view real-time MaxFrame job logs
```

### Small-Scale Testing

```python
df_sample = df.head(2)  # Take 2 rows for testing
result_sample = llm.generate(
    df_sample,
    prompt_template=messages,
    running_options={"gu": 2}
)
result_sample.execute()
```

### Check Resource Usage

View job execution details through MaxFrame LogView.

## Common Patterns

### Custom System Prompt

```python
messages = [
    {"role": "system", "content": "You are an expert in data analysis. Provide concise answers."},
    {"role": "user", "content": "Analyze the following data: {data}"},
]
```

### Multi-Turn Conversation

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "My name is {name}."},
    {"role": "assistant", "content": "Hello {name}! How can I help you today?"},
    {"role": "user", "content": "{query}"},
]
```

### Batch Processing Large Datasets

```python
# Read from MaxCompute table
df = md.read_odps_table("project.schema.input_table")

# Process with LLM
result = llm.generate(
    df,
    prompt_template=messages,
    running_options={"max_tokens": 2048},
)

# Save results to table
result.to_odps_table("project.schema.output_table")
result.execute()
```
