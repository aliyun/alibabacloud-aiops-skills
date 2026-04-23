# Official Image Categories

> **Usage**: After user selects a category, call the API to query images in that category.

## Category List

```
| # | Category          | Description                    | Frameworks                        |
|---|-------------------|-------------------------------|----------------------------------|
| 1 | LLM Inference     | Large language model inference | vLLM, SGLang                    |
| 2 | Image Generation  | Text-to-image, image processing| ComfyUI, Stable Diffusion, Kohya |
| 3 | Speech Synthesis  | TTS voice synthesis           | CosyVoice                       |
| 4 | RAG               | Retrieval-augmented generation | PaiRag                          |
| 5 | General Inference | General deep learning inference| PyTorch, Triton, TF Serving     |
| 6 | Tools             | General tool images           | OpenClaw, CoPaw, Python         |
```

## Category Details

### 1. LLM Inference

**Flow**: Let user select framework first, then query

**Framework selection**:
```
| # | Framework | Description            |
|---|-----------|------------------------|
| 1 | vLLM      | High-performance LLM inference |
| 2 | SGLang    | Efficient LLM serving framework |
```

**Query commands** (call once after user selects framework):

```bash
# vLLM - fuzzy search by Name
aliyun aiworkspace list-images --verbose true --name vllm \
  --labels 'system.official=true,system.supported.eas=true' \
  --page-size 50 --user-agent AlibabaCloud-Agent-Skills | jq -r '.Images[] | "\(.ImageId)\t\(.Name)\t\(.Labels[] | select(.Key == "system.chipType") | .Value)"'

# SGLang - fuzzy search by Name
aliyun aiworkspace list-images --verbose true --name sglang \
  --labels 'system.official=true,system.supported.eas=true' \
  --page-size 50 --user-agent AlibabaCloud-Agent-Skills | jq -r '.Images[] | "\(.ImageId)\t\(.Name)\t\(.Labels[] | select(.Key == "system.chipType") | .Value)"'
```

**Image info**:

| Framework | Versions | Chips |
|-----------|----------|-------|
| vLLM | 0.7.x - 0.14.0 | GPU, PPU |
| SGLang | 0.5.2 - 0.5.8 | GPU, PPU |

### 2. Image Generation

**ComfyUI**: Node-based image generation workflow
- Versions: 2.1, 2.2
- Chip: GPU

**Stable Diffusion WebUI**: Classic SD interface
- Versions: 4.1, 4.2
- Chip: GPU

**Kohya**: Model training tool
- Versions: 2.2, 25.0.3
- Chip: GPU

**EasyAnimate**: Video generation
- Versions: 1.1.4, 1.1.5

**Query command**:

```bash
# ComfyUI - fuzzy search by Name
aliyun aiworkspace list-images --verbose true --name comfyui \
  --labels 'system.official=true,system.supported.eas=true' \
  --page-size 50 --user-agent AlibabaCloud-Agent-Skills | jq -r '.Images[] | "\(.ImageId)\t\(.Name)"'
```

### 3. Speech Synthesis

**CosyVoice**: Alibaba speech synthesis
- Versions: 0.1.5, 2.2.6, 3.0.6
- Components: webui, backend, frontend
- Chips: GPU, PPU

**Query command**:

```bash
aliyun aiworkspace list-images --verbose true \
  --labels 'system.official=true,system.supported.eas=true' \
  --page-size 100 | jq '.Images[] | select(.Name | test("cosyvoice"; "i"))'
```

### 4. RAG

**PaiRag**: PAI RAG framework
- Versions: 0.3.5, 0.4.3
- Chips: CPU, PPU

**Query command**:

```bash
# PaiRag - fuzzy search by Name
aliyun aiworkspace list-images --verbose true --name pairag \
  --labels 'system.official=true,system.supported.eas=true' \
  --page-size 50 --user-agent AlibabaCloud-Agent-Skills | jq -r '.Images[] | "\(.ImageId)\t\(.Name)"'
```

### 5. General Inference

**PyTorch**: General deep learning framework
- Versions: 2.2, 2.3.1, 2.5.1, 2.7.1
- Chips: GPU, CPU, PPU

**Triton Server**: NVIDIA inference server
- Versions: 21.09 - 25.03
- Chip: GPU

**TensorFlow Serving**: TF model serving
- Versions: 1.15.0, 2.11.1, 2.14.1, 2.17.1, 2.18.1

**Query command**:

```bash
# PyTorch - fuzzy search by Name
aliyun aiworkspace list-images --verbose true --name pytorch \
  --labels 'system.official=true,system.supported.eas=true' \
  --page-size 50 --user-agent AlibabaCloud-Agent-Skills | jq -r '.Images[] | "\(.ImageId)\t\(.Name)"'
```

### 6. Tools

**OpenClaw**: PAI tool image
- Version: 2026.3.13
- Chip: CPU

**CoPaw**: CoPaw tool image
- Version: v0.0.7
- Chip: CPU

**Query command**:

```bash
# OpenClaw - fuzzy search by Name
aliyun aiworkspace list-images --verbose true --name openclaw \
  --labels 'system.official=true,system.supported.eas=true' \
  --page-size 50 --user-agent AlibabaCloud-Agent-Skills | jq -r '.Images[] | "\(.ImageId)\t\(.Name)"'
```

---

## Query Parameter Reference

**Labels filter syntax**:

```bash
# Multiple labels separated by comma, format: Key=Value
--labels 'system.official=true,system.supported.eas=true'

# Fuzzy search image name via Name parameter
--name vllm
```

**Common labels**:

| Label Key | Description |
|-----------|-------------|
| `system.official` | `true` = official image |
| `system.supported.eas` | `true` = supports EAS deployment |
| `system.chipType` | `GPU`/`CPU`/`PPU`/`XPU` = chip type |
| `system.framework.xxx` | Framework type label, value = version |
