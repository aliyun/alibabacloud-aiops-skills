import json

# Defines the JSON schema for metadata-based file search queries.
param_schema = {
    "type": "object",
    "properties": {
        "Query": {
            "type": "object",
            "$id": "#query",
            "description": "Defines metadata search conditions for files. Nested query structures are supported.",
            "properties": {
                "Operation": {
                    "type": "string",
                    "enum": ["not", "or", "prefix", "and", "lt", "match", "gte", "eq", "lte", "gt"],
                    "description": "Required. Specifies the operation type. Supported operations include:\\n- Logical operators: and, or, not (require SubQueries)\\n- Comparison operators: lt, lte, gt, gte, eq\\n- String operators: prefix, match",
                    "examples": ["and"]
                },
                "Field": {
                    "type": "string",
                    "description": "The metadata field to query. Required for all operations except logical operators (and, or, not).",
                    "examples": ["size"]
                },
                "Value": {
                    "type": "string",
                    "description": "The target value to query. All values, including numbers and timestamps, must be provided as strings. Not applicable to logical operators (and, or, not).",
                    "examples": ["10"]
                },
                "SubQueries": {
                    "type": "array",
                    "description": "Required when the operation is a logical operator (and, or, not). Contains nested query conditions that follow the logic of the parent operator. For example, when Operation is 'and', all sub-queries must be true.",
                    "items": {
                        "$ref": "#query"
                    }
                }
            }
        },
        "Sort": {
            "type": "string",
            "description": "The fields used for sorting, separated by commas. Up to 5 fields are allowed. Field order determines sort priority. For example: 'size,name'.",
            "examples": ["size,name"]
        },
        "Order": {
            "type": "string",
            "enum": ["asc", "desc"],
            "description": "The sort direction for each field in Sort. Supported values:\\n- asc: ascending (default)\\n- desc: descending\\nYou may provide multiple directions separated by commas, for example 'asc,desc'. The number of directions cannot exceed the number of Sort fields. If a field has no explicit direction, it defaults to 'asc'.",
            "examples": ["asc,desc"]
        }
    },
    "required": []
}


# Defines supported file metadata fields and their value types.
field_schema = {
    "parent_file_id": {
        "type": "string",
        "description": "The parent folder ID.",
        "examples": ["root"]
    },
    "name": {
        "type": "string",
        "description": "The file name. Supports fuzzy matching with `match`.",
        "examples": ["sampleobject.jpg"]
    },
    "type": {
        "type": "string",
        "enum": ["file", "folder"],
        "description": "The file type: `file` or `folder`.",
        "examples": ["file"]
    },
    "file_extension": {
        "type": "string",
        "description": "The file extension without the dot, such as `pdf` or `jpg`.",
        "examples": ["pdf"]
    },
    "mime_type": {
        "type": "string",
        "description": "The MIME type representing the file format.",
        "examples": ["image/jpeg"]
    },
    "starred": {
        "type": "boolean",
        "description": "Whether the file is starred.",
        "examples": ["true"]
    },
    "created_at": {
        "type": "date",
        "description": "The creation time in UTC, formatted as 2006-01-02T00:00:00.",
        "examples": ["2025-01-01T00:00:00"]
    },
    "updated_at": {
        "type": "date",
        "description": "The last modification time in UTC, formatted as 2006-01-02T00:00:00.",
        "examples": ["2025-01-01T00:00:00"]
    },
    "status": {
        "type": "string",
        "description": "The file status. Currently `available`.",
        "examples": ["available"]
    },
    "hidden": {
        "type": "boolean",
        "description": "Whether the file is hidden.",
        "examples": ["false"]
    },
    "size": {
        "type": "long",
        "description": "The file size in bytes.",
        "examples": ["1000"]
    },
    "image_time": {
        "type": "date",
        "description": "The capture time of an image or video from EXIF metadata, formatted as 2006-01-02T00:00:00.",
        "examples": ["2025-01-01T00:00:00"]
    },
    "last_access_at": {
        "type": "date",
        "description": "The most recent access time, formatted as 2006-01-02T00:00:00.",
        "examples": ["2025-01-01T00:00:00"]
    },
    "category": {
        "type": "string",
        "enum": ["image", "video", "audio", "doc", "app", "others"],
        "description": "The file category: image, video, audio, doc, app, or others.",
        "examples": ["image"]
    },
    "label": {
        "type": "string",
        "description": "The system label name.",
        "examples": ["landscape"]
    },
    "face_group_id": {
        "type": "string",
        "description": "The face-group ID. Use the face-group listing API to get this ID and query photos in that group.",
        "examples": ["group-id-xxx"]
    },
    "address": {
        "type": "string",
        "description": "The address. Query only one administrative level at a time, such as country ('China'), province ('Zhejiang Province'), city ('Hangzhou'), district/county ('Xihu District' or 'Tonglu County'), or street/town ('Xixi Street' or 'Sandun Town').",
        "examples": ["Hangzhou"]
    }
}


# Standard scalar-query JSON schema.
def get_json_schema(param_schema: dict) -> dict:
    json_schema = {
        "type": "object",
        "properties": {
            "valid": {
                "type": "boolean",
                "description": "A boolean flag indicating whether the user's input can be mapped to the defined query schema. It must be false in either of these cases: 1) the input does not contain any recognizable reference to a supported field; 2) the input only contains terms for fields that are not defined in the schema, such as 'color' or 'importance'."
            },
            "result": param_schema
        },
        "required": ["valid"]
    }
    return json_schema


# Describes how to decide whether scalar search should be used and how to extract its parameters.
def schalar_search_prompt() -> str:
    output = f"""
# Task

Convert natural-language input into database query parameters:

{json.dumps(param_schema, ensure_ascii=False, indent=None)}

## Supported Query Fields

{json.dumps(field_schema, ensure_ascii=False, indent=None)}

## Field Validation Rules

Before processing any query, you must:
1. Only process queries that clearly refer to fields defined above.
2. If the input violates this rule, for example because it does not refer to any supported field or only refers to unsupported concepts, you must return an output with `"valid": false`.

Examples that must return {json.dumps({"valid": False}, ensure_ascii=False)}:
- "Leshan Giant Buddha" (no field is specified; do not assume this means filename)
- "red ones" (`color` is not a supported field)
- "important files" (`importance` is not a supported field)

Example that should not be marked invalid:
- "image files" (`category eq image`)

## Query Operation Guide

Each operation has a specific meaning and usage.

### Numeric comparison operations

- `eq`: exact equality, such as "equals", "is", "is set to"
- `gt`: greater than, such as "greater than", "over"
- `gte`: greater than or equal to, such as "at least", "no less than"
- `lt`: less than, such as "less than", "below"
- `lte`: less than or equal to, such as "at most", "no more than"

### Text operations

- `match`: search for specific text within a field
- `prefix`: prefix matching for path-like values or string prefixes

### Logical operations

- `and`: all conditions must be true
- `or`: any condition may be true
- `not`: negate a condition

## Sort and Order Guide

### Sort

Supports up to 5 comma-separated sort fields. Field order determines priority. Common usage:
- Single field: `"size"`
- Multiple fields: `"size,name"` meaning sort by size first, then by name when sizes are equal

Common mappings:
- "sort by size" -> `"size"`
- "sort by capture time" -> `"image_time"`
- "sort by name" -> `"name"`
- "sort by size and then by time" -> `"size,image_time"`

Recommended combinations:
- `"size,name"`: useful when sorting by size while keeping a deterministic tie-breaker
- `"image_time,name"`: useful when listing results in time order while keeping a deterministic tie-breaker
- `"name"`: alphabetical order

### Order

Use comma-separated directions:
- `asc`: ascending
- `desc`: descending

If fewer Order values are provided than Sort fields, the remaining fields default to `asc`. For example:
- Sort: `"size,image_time,name"`, Order: `"desc"` -> equivalent to `"desc,asc,asc"`

## Important Rules

1. `match` can only be used for filename search on `name`.
2. `prefix` must not be used for `name`.
3. Follow the principle of minimal inference: only add filters that are explicitly requested by the user. For example, if the user does not mention filename conditions, the query must not contain `name` filters. This rule applies to all fields.
4. The `category` field can be used for multi-modal filtering in pure scalar search, such as images or videos.
5. If this scalar query will later be combined with semantic search, the final modality will be narrowed to the single modality chosen by semantic search. Therefore, when the user already implies a semantic target, keep `category` compatible with that semantic modality whenever possible.
""".strip()
    output += "\n\n"
    output += """
## Examples

### Example 1

Some natural-language inputs are colloquial and use abbreviations.

`"The file's mime type is docx"`

You should normalize the abbreviation to its canonical form whenever possible:

`{"Query": {"Operation": "eq", "Field": "mime_type", "Value": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}}`

`"Search for pdf files"`

You should normalize the abbreviation to its canonical form whenever possible:

`{"Query": {"Operation": "eq", "Field": "file_extension", "Value": "pdf"}}`

### Example 2: Time-range queries

Time expressions usually imply a range rather than a single point in time.

UserQueryDatetime: 2025-05-26T11:33:52+08:00
Input: `"Files created on June 6"`
This should be converted into a full-day range in UTC. For the entire day of June 6 in Beijing time, the UTC start should be `2025-06-05T16:00:00` and the end should be `2025-06-06T16:00:00`. The start of day and the end boundary must always use exactly `16:00:00`. Do not use non-zero minutes or seconds at day boundaries:
`{"Query": {"Operation":"and","SubQueries":[{"Operation":"gte","Field":"created_at","Value":"2025-06-05T16:00:00"},{"Operation":"lt","Field":"created_at","Value":"2025-06-06T16:00:00"}]}}`

UserQueryDatetime: 2025-05-26T11:33:52+08:00
Input: `"Accessed in the last three and a half hours"`
This should be converted into a UTC time span:
`{"Query": {"Operation":"and","SubQueries":[{"Operation":"gte","Field":"last_access_at","Value":"2025-05-26T00:03:52"},{"Operation":"lte","Field":"last_access_at","Value":"2025-05-26T03:33:52"}]}}`

Key patterns:
- A calendar date = a full-day range
- "recent" = a range ending at the current time
- "before/after" = a bounded interval
- Finally, always convert from Beijing time to UTC. The timestamp must end at whole seconds, with no milliseconds or timezone suffix.

### Example 3: Language consistency

Always keep the output in the same language as the input query.

Input: `"Find files whose name is 蛋糕"`
Correct: `{"Query": {"Operation": "eq", "Field": "name", "Value": "蛋糕"}}`

Incorrect: `{"Query": {"Operation": "eq", "Field": "name", "Value": "cake"}}`

### Example 4: Choosing the right time field

There are four different time fields:
- `image_time`: when an image or video was captured
  - Example: `"Photos taken in the summer of 2023"` -> use `image_time`
- `last_access_at`: when the file was last accessed from the drive
  - Example: `"Files accessed yesterday"` -> use `last_access_at`
- `created_at`: when the file was created or uploaded into the drive
  - Example: `"Files created yesterday"` -> use `created_at`
  - Example: `"Files uploaded yesterday"` -> use `created_at`
- `updated_at`: when the file was last updated
  - Example: `"Files updated yesterday"` -> use `updated_at`

For photo or video capture-time queries, always prefer `image_time`.

### Example 5: Basic sorting

Input: `"Find files larger than 1 GB and sort by size in descending order"`
`{"Query": {"Operation": "gt", "Field": "size", "Value": "1073741824"}, "Sort": "size", "Order": "desc"}`

### Example 6: Multi-field sorting

Input: `"Find docx files, sort by modification time descending, then by name ascending"`
`{"Query": {"Operation": "eq", "Field": "mime_type", "Value": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}, "Sort": "updated_at,name", "Order": "desc,asc"}`

### Example 7: Pure sorting with no query condition

Input: `"Sort all files by name"`
`{"Sort": "name"}`

### Example 8: Multi-field sorting with default order

Input: `"Sort all files by size and creation time"`
`{"Sort": "size,created_at"}`

### Example 9: Query simplification

Input: `"Document files or text files"`
`{"Query": {"Operation": "eq", "Field": "category", "Value": "doc"}}`

### Example 10: Pure scalar multi-modal filtering

Input: `"Images or videos larger than 10 MB"`
`{"Query": {"Operation": "and", "SubQueries": [{"Operation": "gt", "Field": "size", "Value": "10485760"}, {"Operation": "or", "SubQueries": [{"Operation": "eq", "Field": "category", "Value": "image"}, {"Operation": "eq", "Field": "category", "Value": "video"}]}]}}`
"""
    output += "\n\n"
    json_schema = get_json_schema(param_schema=param_schema)
    output += f"""
## JSON Output Format

Your output must strictly follow this JSON schema:

```json
{json.dumps(json_schema, indent=None, ensure_ascii=False)}
```

### Output Requirements

- Your response must be a single valid JSON object.
- Critically important: do not add any explanatory text, comments, or extra content outside the JSON object. Your entire response must contain only that JSON.
""".strip()
    return output


if __name__ == "__main__":
    print(schalar_search_prompt())
