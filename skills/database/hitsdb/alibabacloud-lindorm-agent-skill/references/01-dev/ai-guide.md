# Lindorm AI Engine Guide

This guide describes how to use the Lindorm AI engine independently. The AI engine provides DashScope-compatible APIs for embeddings, visual understanding, reranking, and chat-based answer generation. Application code and agents should call models through the AI engine built into the Lindorm instance. Authentication uses the instance username and password through the `x-ld-ak` and `x-ld-sk` request headers. Do not use external platform API keys.

## Connection and Connectivity

The AI engine always uses port `9002`. Public endpoints usually contain `-proxy-ai-pub`; VPC endpoints usually contain `-proxy-ai-vpc`.

| Network type | Endpoint example | Applicable environment |
|--------------|------------------|-------------------------|
| VPC private network | `<instance_id>-proxy-ai-vpc.lindorm.aliyuncs.com:9002` | Search pipelines, ECS, and services inside the VPC |
| Public network | `<instance_id>-proxy-ai-pub.lindorm.aliyuncs.com:9002` | Local computers or public-network clients |

Before making public-network calls, confirm that the public endpoint of the AI engine is enabled and that the IP whitelist is configured. The public endpoint of the search engine and the public endpoint of the AI engine are different entries. Do not assume that the AI engine can be called just because the search engine public endpoint is enabled.

### Connectivity check for port 9002

```bash
curl --connect-timeout 10 -m 60 \
  -H 'Content-Type: application/json' \
  -H 'x-ld-ak: <username>' \
  -H 'x-ld-sk: <password>' \
  -XPOST "http://<ai_endpoint>:9002/dashscope/compatible-mode/v1/embeddings" \
  -d '{
    "model": "text-embedding-v4",
    "input": "connectivity test"
  }'
```

A successful response should include embedding data. If the response returns `401` or `403`, first check whether `x-ld-ak` and `x-ld-sk` come from the same Lindorm instance.

## Model Configuration

| Model type | Typical model | Purpose | Key check |
|------------|---------------|---------|-----------|
| Text embedding | `text-embedding-v4` | Vectorize text chunks in a knowledge base | The output dimension must equal the vector index dimension |
| Multimodal embedding | `qwen2.5-vl-embedding` / `qwen3-vl-embedding` | Build a unified image-text vector space for image-to-image and text-to-image search | Image and text queries must be written to the same vector field |
| VL | `qwen3-vl-plus` / `qwen3-vl-flash` | Recognize image URLs and generate image descriptions | The image URL must be accessible by the AI engine |
| Rerank | `qwen3-rerank` / `gte-rerank-v2` | Rerank recalled candidates by query relevance | Preserve the original candidate array and map results back through `results[*].index` |
| Chat | `qwen-plus` / `qwen3.5-plus` | Generate knowledge-base answers | The prompt must restrict the model to answer only from the recalled context |

If the embedding model dimension and the vector index dimension are inconsistent, writes or queries will fail. Record `embedding_model`, `vector_dimension`, `vector_field`, and `index_algorithm` whenever a dataset is registered.

## Embedding Calls

### Text embeddings

```bash
curl --connect-timeout 10 -m 60 \
  -H 'Content-Type: application/json' \
  -H 'x-ld-ak: <username>' \
  -H 'x-ld-sk: <password>' \
  -XPOST "http://<ai_endpoint>:9002/dashscope/compatible-mode/v1/embeddings" \
  -d '{
    "model": "text-embedding-v4",
    "input": "Lindorm vector search supports hybrid full-text and vector retrieval"
  }'
```

Example response format:

```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "index": 0,
      "embedding": [0.0123, -0.0456]
    }
  ],
  "model": "text-embedding-v4",
  "usage": {
    "prompt_tokens": 12,
    "total_tokens": 12
  }
}
```

Vector read path: `data[0].embedding`.

### Multimodal embeddings

Multimodal embeddings are used for a unified image-text vector space. Use `text` for text input and `image` for image URL input.

```bash
curl --connect-timeout 10 -m 60 \
  -H 'Content-Type: application/json' \
  -H 'x-ld-ak: <username>' \
  -H 'x-ld-sk: <password>' \
  -XPOST "http://<ai_endpoint>:9002/dashscope/api/v1/services/embeddings/multimodal-embedding/multimodal-embedding" \
  -d '{
    "model": "multimodal-embedding-v1",
    "input": {
      "contents": [
        { "image": "https://example.com/product.jpg" }
      ]
    }
  }'
```

Example response format:

```json
{
  "output": {
    "embeddings": [
      {
        "embedding": [0.0123, -0.0456],
        "index": 0,
        "type": "dense"
      }
    ]
  },
  "usage": {
    "duration": 393,
    "image_count": 1,
    "image_tokens": 255,
    "input_tokens": 0
  },
  "request_id": "<request_id>"
}
```

Vector read path: `output.embeddings[0].embedding`. Before writing the vector, verify that its dimension is consistent with the target `knn_vector.dimension`.

## VL Image Understanding Calls

VL models convert image URLs into structured or natural-language descriptions. They are commonly used during multimodal retrieval ingestion.

```bash
curl --connect-timeout 10 -m 60 \
  -H 'Content-Type: application/json' \
  -H 'x-ld-ak: <username>' \
  -H 'x-ld-sk: <password>' \
  -XPOST "http://<ai_endpoint>:9002/dashscope/compatible-mode/v1/chat/completions" \
  -d '{
    "model": "qwen3-vl-plus",
    "messages": [
      {
        "role": "user",
        "content": [
          { "type": "image_url", "image_url": { "url": "https://example.com/product.jpg" } },
          { "type": "text", "text": "Describe the product, color, material, style, and applicable scenarios in this image. Output in English." }
        ]
      }
    ]
  }'
```

Example response format:

```json
{
  "id": "<completion_id>",
  "object": "chat.completion",
  "created": 1770000000,
  "model": "qwen3-vl-plus",
  "choices": [
    {
      "index": 0,
      "finish_reason": "stop",
      "message": {
        "role": "assistant",
        "content": "This is a product image. The main item is..."
      }
    }
  ],
  "usage": {
    "prompt_tokens": 256,
    "completion_tokens": 80,
    "total_tokens": 336
  }
}
```

Description read path: `choices[0].message.content`.

## Rerank Calls

Reranking is a post-recall step and does not perform retrieval. The caller must keep the candidate document array and use the returned `index` to map each result back to the original candidate.

```bash
curl --connect-timeout 10 -m 60 \
  -H 'Content-Type: application/json' \
  -H 'x-ld-ak: <username>' \
  -H 'x-ld-sk: <password>' \
  -XPOST "http://<ai_endpoint>:9002/dashscope/compatible-api/v1/reranks" \
  -d '{
    "model": "qwen3-rerank",
    "query": "white shirt suitable for summer commuting",
    "documents": [
      "White short-sleeve cotton shirt suitable for commuting",
      "Black thick coat suitable for winter"
    ],
    "top_n": 2
  }'
```

Example response format:

```json
{
  "object": "list",
  "results": [
    {
      "index": 0,
      "relevance_score": 0.7791645121619432
    },
    {
      "index": 1,
      "relevance_score": 0.2119340804000243
    }
  ],
  "model": "qwen3-rerank",
  "id": "<rerank_id>",
  "usage": {
    "total_tokens": 73
  }
}
```

Reranking rule: sort by `results[*].relevance_score` in descending order, then retrieve the original candidate document through `results[*].index`.

## Chat-based Q&A Calls

Knowledge-base Q&A concatenates recalled text into context and then calls the Chat model. The prompt must restrict the model to answer only based on the provided context.

```bash
curl --connect-timeout 10 -m 60 \
  -H 'Content-Type: application/json' \
  -H 'x-ld-ak: <username>' \
  -H 'x-ld-sk: <password>' \
  -XPOST "http://<ai_endpoint>:9002/dashscope/compatible-mode/v1/chat/completions" \
  -d '{
    "model": "qwen-plus",
    "messages": [
      {
        "role": "system",
        "content": "You are a private-domain knowledge-base Q&A assistant. Answer only according to the provided context."
      },
      {
        "role": "user",
        "content": "Known information: <retrieved_context>\nQuestion: <question>"
      }
    ]
  }'
```

Answer read path: `choices[0].message.content`.

## Error Handling

| Symptom | Possible cause | Handling |
|---------|----------------|----------|
| Connection timeout | Public endpoint is not enabled, whitelist is not configured, or a VPC endpoint is used from outside the VPC | Check the network type and whitelist |
| `401` / `403` | Missing request headers or incorrect password | Check `x-ld-ak` and `x-ld-sk` |
| `404` | Wrong port or path | Confirm that the port is `9002` and that the path starts with `/dashscope/` |
| Embedding dimension mismatch | Model and index configuration are inconsistent | Reconfirm the model dimension and `knn_vector.dimension` |
| Empty VL content | Image URL is inaccessible or the image is too large | Verify that the image URL can be accessed by the server first |
| Empty rerank result | `documents` is empty or `top_n` is `0` | Check recalled candidates |

## Evidence Output Format

```text
[Connection] engine=AI endpoint=<masked_ai_endpoint>:9002 network=<public|vpc>
[Capability] type=<embedding|vl|rerank|chat> model=<model_name>
[Evidence] http_status=<status> request_id=<id> dim=<n> candidates=<n>
[Blocked] status=<BLOCKED_NETWORK|BLOCKED_AUTH|BLOCKED_MODEL|BLOCKED_INPUT> reason=<reason>
```

Never include `x-ld-sk`, passwords, or complete secret values in reports.
