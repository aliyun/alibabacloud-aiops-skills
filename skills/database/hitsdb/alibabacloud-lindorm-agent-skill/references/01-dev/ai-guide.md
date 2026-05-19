# Lindorm AI Engine Guide

本指南说明 Lindorm AI 引擎的独立用法。AI 引擎提供 DashScope 兼容接口，用于 embedding、视觉理解、rerank 和问答生成。业务代码和 Agent 应通过 Lindorm 实例内置 AI 引擎调用模型，认证使用实例用户名和密码对应的 `x-ld-ak` / `x-ld-sk` 请求头，不使用外部平台密钥。

## 连接与连通性

AI 引擎固定端口为 `9002`。公网地址通常包含 `-proxy-ai-pub`，私网地址通常包含 `-proxy-ai-vpc`。

| 网络类型 | 地址示例 | 适用环境 |
|----------|----------|----------|
| VPC 私网 | `<instance_id>-proxy-ai-vpc.lindorm.aliyuncs.com:9002` | 搜索 pipeline、ECS、VPC 内服务 |
| Public 公网 | `<instance_id>-proxy-ai-pub.lindorm.aliyuncs.com:9002` | 本地电脑或公网客户端 |

公网调用前必须确认 AI 引擎公网已开通，并完成白名单检查。搜索引擎公网和 AI 引擎公网是不同入口，不能只开通搜索引擎公网就直接调用 AI。

### 9002 连通性探测

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

成功时应返回 embedding 数据。若返回 `401` / `403`，优先检查 `x-ld-ak` 和 `x-ld-sk` 是否来自同一个 Lindorm 实例。

## 模型配置

| 模型类型 | 典型模型 | 用途 | 关键检查 |
|----------|----------|------|----------|
| Text embedding | `text-embedding-v4` | 知识库文本切分后的向量化 | 输出维度必须等于向量索引 dimension |
| Multimodal embedding | `qwen2.5-vl-embedding` / `qwen3-vl-embedding` | 图文统一向量空间，支持以图搜图和以文搜图 | 图片和文本查询必须写入同一个向量字段 |
| VL | `qwen3-vl-plus` / `qwen3-vl-flash` | 图片 URL 识别、生成图片描述 | 图片 URL 必须可被 AI 引擎访问 |
| Rerank | `qwen3-rerank` / `gte-rerank-v2` | 对召回候选按查询相关性重排 | 保留原始候选数组，用 `results[*].index` 回映射 |
| Chat | `qwen-plus` / `qwen3.5-plus` | 知识库问答生成 | 提示词必须约束只基于召回上下文回答 |

Embedding 模型和向量索引的维度不一致会导致写入或查询失败。每个数据集注册时都应记录 `embedding_model`、`vector_dimension`、`vector_field` 和 `index_algorithm`。

## Embedding 调用

### 文本 embedding

```bash
curl --connect-timeout 10 -m 60 \
  -H 'Content-Type: application/json' \
  -H 'x-ld-ak: <username>' \
  -H 'x-ld-sk: <password>' \
  -XPOST "http://<ai_endpoint>:9002/dashscope/compatible-mode/v1/embeddings" \
  -d '{
    "model": "text-embedding-v4",
    "input": "Lindorm 向量检索支持全文和向量融合"
  }'
```

返回包格式样例：

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

向量读取路径：`data[0].embedding`。

### 多模态 embedding

多模态 embedding 用于图文统一向量空间。输入文本时使用 `text`，输入图片 URL 时使用 `image`。

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

返回包格式样例：

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

向量读取路径：`output.embeddings[0].embedding`。写入前必须验证维度与目标 `knn_vector.dimension` 一致。

## VL 图片理解调用

VL 模型用于把图片 URL 转成结构化或自然语言描述，常用于多模态检索入库阶段。

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
          { "type": "text", "text": "请描述图片中的商品、颜色、材质、风格和适用场景，输出中文。" }
        ]
      }
    ]
  }'
```

返回包格式样例：

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
        "content": "这是一张商品图片，主体为..."
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

描述读取路径：`choices[0].message.content`。

## Rerank 调用

Rerank 是召回后的重排步骤，不负责检索。调用方必须保留候选文档数组，并用返回的 `index` 映射回原候选。

```bash
curl --connect-timeout 10 -m 60 \
  -H 'Content-Type: application/json' \
  -H 'x-ld-ak: <username>' \
  -H 'x-ld-sk: <password>' \
  -XPOST "http://<ai_endpoint>:9002/dashscope/compatible-api/v1/reranks" \
  -d '{
    "model": "qwen3-rerank",
    "query": "适合夏天通勤的白色衬衫",
    "documents": [
      "白色短袖衬衫，棉质，适合通勤",
      "黑色厚外套，适合冬季"
    ],
    "top_n": 2
  }'
```

返回包格式样例：

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

重排规则：按 `results[*].relevance_score` 降序排列，再用 `results[*].index` 取回原候选文档。

## Chat 问答调用

知识库问答使用召回文本拼接上下文后调用 Chat 模型。提示词必须约束模型只基于已知上下文回答。

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
        "content": "你是私域知识库问答助手，只能根据给定上下文回答。"
      },
      {
        "role": "user",
        "content": "已知信息：<retrieved_context>\n问题：<question>"
      }
    ]
  }'
```

回答读取路径：`choices[0].message.content`。

## 错误处理

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| 连接超时 | 公网未开通、白名单未放行、使用了 VPC 地址 | 检查网络类型和白名单 |
| `401` / `403` | 请求头缺失或密码错误 | 检查 `x-ld-ak` / `x-ld-sk` |
| `404` | 访问了错误端口或路径 | 确认端口为 `9002`，路径以 `/dashscope/` 开头 |
| embedding 维度不匹配 | 模型与索引配置不一致 | 重新确认模型维度和 `knn_vector.dimension` |
| VL 内容为空 | 图片 URL 不可访问或图片过大 | 先验证图片 URL 可被服务端访问 |
| rerank 结果为空 | `documents` 为空或 `top_n` 为 0 | 检查召回候选 |

## 输出证据格式

```text
[Connection] engine=AI endpoint=<masked_ai_endpoint>:9002 network=<public|vpc>
[Capability] type=<embedding|vl|rerank|chat> model=<model_name>
[Evidence] http_status=<status> request_id=<id> dim=<n> candidates=<n>
[Blocked] status=<BLOCKED_NETWORK|BLOCKED_AUTH|BLOCKED_MODEL|BLOCKED_INPUT> reason=<reason>
```

永远不要在报告中输出 `x-ld-sk`、密码或完整密钥值。
