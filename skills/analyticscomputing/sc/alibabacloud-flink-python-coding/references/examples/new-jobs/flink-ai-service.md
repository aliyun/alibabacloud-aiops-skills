# New Job Example: Flink AI Service Summarization

Use this pattern for JSON input, built-in summarization through Flink AI Service, and JSON output. `OpenAICompatProvider` selects the protocol/task here; Flink AI Service supplies model access without API keys or endpoints. Verify the provider and summarization APIs against the selected package, and choose a model supported by the service.

## Complete `job.py`

```python
import pyflink.dataframe as pf


SOURCE_JSON_PATH = "oss://<source-bucket>/support-tickets/"
SINK_JSON_PATH = "oss://<sink-bucket>/ticket-summaries/"
FLINK_AI_SERVICE_MODEL = "<supported-flink-ai-service-model>"
SUMMARY_MAX_LENGTH = 300


def main() -> None:
    pf.set_model_provider(pf.OpenAICompatProvider(task="chat/completions"))
    tickets = pf.read_json(
        SOURCE_JSON_PATH,
        schema={
            "ticket_id": pf.DataType.string(),
            "body": pf.DataType.string(),
        },
        ignore_parse_errors=False,
    )

    summarized = tickets.llm.ai_summarize(
        "body",
        SUMMARY_MAX_LENGTH,
        model=FLINK_AI_SERVICE_MODEL,
    ).select(
        "ticket_id",
        "summary",
    )

    summarized.write_json(
        SINK_JSON_PATH,
        mode="overwrite",
        write_null_properties=False,
    )


if __name__ == "__main__":
    main()
```

## Deployment contract

- Replace both OSS paths after the source and sink interfaces are confirmed.
- Select `FLINK_AI_SERVICE_MODEL` from the supported Flink AI Service models and configure the provider as documented for the target VVR release.
- Put no model credential, service endpoint, or secret value in the job, dependency archive, additional files, or README.
- Select no Python model SDK or local model file for this pipeline.
- Keep summarization as the documented `df.llm.ai_summarize` operation rather than wrapping the model call in a general UDF.

The job has no third-party Python dependency or runtime-file attachment. Syntax and artifact checks are local; filesystem access, provider/model resolution, model invocation, schema materialization, and sink output are VVR-only.
