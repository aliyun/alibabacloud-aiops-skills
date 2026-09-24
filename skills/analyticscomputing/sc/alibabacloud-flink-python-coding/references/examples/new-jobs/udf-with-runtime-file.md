# New Job Example: Narrow UDF with a Python Package and Runtime Dictionary

Use this pattern when custom dictionary-based text replacement needs a Python UDF and a runtime file. Check the selected package's UDF and I/O APIs before adapting it.

## Complete `job.py`

```python
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

import pyflink.dataframe as pf
import yaml


SOURCE_JSON_PATH = "oss://<source-bucket>/raw-text/"
SINK_JSON_PATH = "oss://<sink-bucket>/normalized-text/"
DICTIONARY_PATH = Path("/flink/usrlib/normalization.yaml")


@lru_cache(maxsize=1)
def load_replacements() -> Dict[str, str]:
    with DICTIONARY_PATH.open("r", encoding="utf-8") as stream:
        document = yaml.safe_load(stream) or {}

    replacements = document.get("replacements")
    if not isinstance(replacements, dict):
        raise ValueError("normalization.yaml must contain a replacements mapping")

    return {str(source): str(target) for source, target in replacements.items()}


def apply_replacements(value: str, replacements: Dict[str, str]) -> str:
    normalized = " ".join(value.split())
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized


@pf.udf(return_dtype=pf.DataType.string())
def normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return apply_replacements(value, load_replacements())


def main() -> None:
    source = pf.read_json(
        SOURCE_JSON_PATH,
        schema={
            "record_id": pf.DataType.string(),
            "text": pf.DataType.string(),
        },
        ignore_parse_errors=False,
    )

    normalized = source.with_column(
        "normalized_text",
        normalize_text(pf.col("text")),
    ).select(
        "record_id",
        "normalized_text",
    )

    normalized.write_json(
        SINK_JSON_PATH,
        mode="overwrite",
        write_null_properties=False,
    )


if __name__ == "__main__":
    main()
```

## Complete companion files

`requirements.txt`:

```text
PyYAML==6.0.3
```

`normalization.yaml`:

```yaml
replacements:
  " teh ": " the "
  " colour ": " color "
```

## Dependency and file contract

| Item | Consumer | Deployment mapping | Target contract |
|---|---|---|---|
| `PyYAML==6.0.3` | `import yaml` in `load_replacements` | If not documented as target-preinstalled and compatible, build verified `deps.zip` and upload through Python Libraries | Match target Python ABI, CPU, and glibc; otherwise record `deps.zip: not built` |
| `normalization.yaml` | `load_replacements` | Upload the independent file through Additional Dependency Files | `/flink/usrlib/normalization.yaml` |

Keep `apply_replacements` as a pure helper and the UDF as one scalar operation. Source parsing, projection, and sink writing remain DataFrame methods. Never package the dictionary inside `deps.zip`, and never bind target code to a workstation path.

Compile and test the pure helper locally with a bounded dictionary fixture. UDF execution, Python Library loading, Additional Dependency File resolution, filesystem connectors, and sink output remain VVR-only.
