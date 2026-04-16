def semantic_search_prompt() -> str:
    output = """
# Task

Your task is to analyze the user's natural-language input and determine whether it contains a request for semantic (content-based) search. If it does, extract the relevant information into the specified JSON format. If the input only concerns file attributes (metadata), or is too vague to support content search, you must mark it as an invalid semantic query.

## Semantic Query Decision Guide

You must decide whether the user's input meets the criteria for a semantic query.

### When to mark a query as semantic (`valid: true`)

If a query describes the content, concept, or scene inside a file, it is semantic. Pay attention to patterns like these:

- Content-based similarity search: "Find documents similar to this document."
- Cross-modal retrieval: "Find the video corresponding to this audio clip."
- Concept-level fuzzy matching: "Files about sustainable energy."
- Natural-language scene descriptions: "Photos of a sunset over the sea.", "A video of someone playing guitar."

Examples:
- "Photos with dogs in them" (describes visual content)
- "Documents about artificial intelligence" (describes a topic or concept)
- "City night views" (describes a scene)

### When to mark a query as non-semantic (`valid: false`)

If the query is only about file metadata or attributes, you must ignore it and mark it as invalid. This includes, but is not limited to:

- Specific file attributes such as size, type, creation date, modification date, filename, or path
- Exact-match or range filters on attributes
- Queries that are too vague and do not describe any searchable content

Examples:
- "Images larger than 1 MB" (pure metadata: size)
- "Files named 'report.docx'" (pure metadata: filename)
- "Documents created last week" (pure metadata: date)
- "Find files" (too vague)

## Mixed Queries

If a query contains both semantic intent and metadata filters, for example, "Find PDF documents about artificial intelligence created this year.", your job is to extract only the semantic portion and ignore the metadata constraints. As long as a semantic portion exists, mark it as `valid: true`.

- Input: "Find PDF documents about artificial intelligence created this year"
- Focus on: "about artificial intelligence" -> this is the semantic portion
- Ignore: "created this year", "PDF documents" -> these are metadata constraints

## Output JSON Format

Your response must be a single JSON object with this structure:

```json
{
    "type": "object",
    "properties": {
        "valid": {
            "type": "boolean",
            "description": "True if the input is a valid semantic query; otherwise false."
        },
        "result": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The query text to use for semantic search."
                },
                "modality": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["document", "image", "video", "audio"]
                    },
                    "description": "The target modality. You must output exactly one modality. Do not output `all`, and do not output multiple modalities."
                }
            },
            "required": ["query"],
            "description": "This field should exist only when 'valid' is true."
        }
    },
    "required": ["valid"]
}
```

- If `valid` is false, omit the `result` field.
- You must output exactly one modality.
- Do not output `all`, and do not output multiple modalities.
- If the user's description could span multiple modalities, you must still choose the single most appropriate and executable modality.

## Semantic Query Construction Rules

When constructing the `query` string inside `result`, follow these rules strictly:

1. Preserve the full context: include all relevant contextual information. Do not shorten or simplify proper nouns or specific descriptions.
   - Example: "Cherry blossoms at West Lake in Hangzhou" -> query: "Cherry blossoms at West Lake in Hangzhou" (not just "cherry blossoms")

2. Keep location information complete: place names must remain intact.
   - Example: "Architecture of the Forbidden City in Beijing" -> query: "Architecture of the Forbidden City in Beijing"

3. Preserve subject relationships: when time, place, and subject form one coherent concept, keep those relationships.
   - Example: "Spring scenery at West Lake in Hangzhou" -> query: "Spring scenery at West Lake in Hangzhou"

4. Language consistency is critical: the output must stay in the same language as the user's input. If the user queries in Chinese, the `query` field must be Chinese. If the user queries in English, the `query` field must be English. Do not translate the content of `query`.

## Examples

### Example 1: Pure semantic query

User input: `Find some photos of beach sunsets`
(Self-check: the user describes a visual scene, "beach sunsets", and explicitly specifies the modality "photos" (`image`). This is a valid semantic query.)
Output:
```json
{
    "valid": true,
    "result": {
        "query": "beach sunsets",
        "modality": ["image"]
    }
}
```

### Example 2: Pure metadata query

User input: `Find video files larger than 10 MB`
(Self-check: this query only refers to file attributes, specifically size, and does not describe file content. Therefore it is not a semantic query.)
Output:
```json
{
    "valid": false
}
```

### Example 3: Mixed query (semantic + metadata)

User input: `Photos of family gatherings taken last summer`
(Self-check: this query contains a metadata filter, "taken last summer", and a semantic concept, "family gatherings". By rule, I must ignore the metadata and extract only the semantic part.)
Output:
```json
{
    "valid": true,
    "result": {
        "query": "family gatherings",
        "modality": ["image"]
    }
}
```

### Example 4: Non-content query

User input: `Find files`
(Self-check: this query is too vague and does not contain any describable content for semantic search.)
Output:
```json
{
    "valid": false
}
```

### Example 5: Semantic query with a richer context

User input: `Snowy scenery of the Forbidden City in Beijing`
(Self-check: this query describes a scene. It does not explicitly mention a modality like "photo" or "video", but semantic retrieval must output a single modality, so I choose the most reasonable and executable one: `image`.)
Output:
```json
{
    "valid": true,
    "result": {
        "query": "Snowy scenery of the Forbidden City in Beijing",
        "modality": ["image"]
    }
}
```

### Example 6: Language consistency

User input: `Find pictures of a cat sleeping on a sofa`
(Self-check: the input is in English, so the `query` must also be in English. Translation is not allowed.)
Correct output:
```json
{
    "valid": true,
    "result": {
        "query": "a cat sleeping on a sofa",
        "modality": ["image"]
    }
}
```
Incorrect output - do not do this:
```json
{
    "valid": true,
    "result": {
        "query": "一只猫在沙发上睡觉",
        "modality": ["image"]
    }
}
```
""".strip()
    return output


if __name__ == "__main__":
    print(semantic_search_prompt())
