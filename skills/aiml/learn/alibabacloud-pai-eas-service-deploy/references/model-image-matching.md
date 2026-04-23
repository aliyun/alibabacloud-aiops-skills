# Model-Image Matching Guide

> **Important**: Before selecting an image, confirm your model type matches the image type. Mismatch will cause deployment failure!

## Quick Matching Table

| Model Type | Recommended Image Category | Specific Image | Model Format |
|-----------|--------------------------|---------------|-------------|
| **LLM** (Qwen, Llama, Mistral, Baichuan, etc.) | LLM Inference | vLLM, SGLang | HuggingFace (safetensors) |
| **LLM** (quantized) | LLM Inference | llama.cpp | GGUF |
| **Image Generation** (Stable Diffusion, SDXL) | Image Generation | ComfyUI, SD WebUI | .safetensors, .ckpt |
| **Speech Synthesis** (TTS) | Speech Synthesis | CosyVoice | Model-specific format |
| **RAG Applications** | RAG | PaiRag | - |
| **Custom Inference** | General Inference | PyTorch, Triton | .pt, .pth, .onnx |

## Common Errors

### ❌ Wrong Example

```
Model: Qwen3.5-0.8B (LLM)
Image: ComfyUI (Image Generation)
Result: Deployment failed, image does not support LLM inference
```

### ✅ Correct Example

```
Model: Qwen3.5-0.8B (LLM)
Image: vLLM or SGLang
Result: Deployment successful
```

## Detailed Matching Rules

### 1. LLM Models

**HuggingFace Format** (.safetensors, model.bin):
```
Image: vLLM, SGLang
Model directory structure:
├── config.json
├── model.safetensors (or model.bin)
├── tokenizer.json
├── tokenizer_config.json
└── vocab.json
```

**GGUF Format**:
```
Image: llama.cpp
Model file: *.gguf
```

**Note**: Do not use vLLM for GGUF models; do not use llama.cpp for HuggingFace format.

### 2. Image Generation Models

**Stable Diffusion Series**:
```
Image: ComfyUI, Stable Diffusion WebUI
Model format: .safetensors, .ckpt
Storage path: /models/checkpoints/ or /models/stable-diffusion/
```

**Note**: LLM models cannot be used with image generation images.

### 3. Speech Synthesis Models

**CosyVoice**:
```
Image: CosyVoice
Requires: Pre-trained model files
```

## Model Download Sources

| Source | Format | Description |
|--------|--------|-------------|
| HuggingFace | safetensors | Most common, natively supported by vLLM/SGLang |
| ModelScope | safetensors | Faster access in China, HuggingFace compatible |
| HuggingFace GGUF | GGUF | Quantized models, requires llama.cpp |

## How to Determine Model Type

1. **Check file extension**:
   - `.safetensors` + `config.json` → HuggingFace LLM
   - `.gguf` → GGUF LLM
   - `.ckpt` / `.safetensors` (no config.json) → Image model

2. **Check model name**:
   - Contains `llama`, `qwen`, `mistral`, `baichuan` → LLM
   - Contains `sd`, `stable-diffusion`, `sdxl` → Image generation
   - Contains `cosyvoice`, `tts` → Speech synthesis

3. **Check source page**:
   - HuggingFace model page indicates model type

## Chip Type Compatibility (Important)

> **⚠️ Image chip type must match instance type, otherwise deployment fails!**

### Image Chip Types

Images use `system.chipType` label to indicate supported chips:

| Chip Type | Description | Instance Type Prefix |
|-----------|-------------|---------------------|
| **GPU** | NVIDIA GPU | `ecs.gn`, `ecs.gn6`, `ecs.gn7`, `ecs.gn8` |
| **CPU** | CPU only | Non-GPU instances |
| **PPU** | Alibaba Hanguang chip | `ecs.ebmppu` |
| **XPU** | Alibaba XPU | `ecs.egs` |

### Compatibility Matrix

| Image Chip Type | Compatible Instance Types |
|----------------|--------------------------|
| GPU | gn6i, gn6v, gn7, gn6e, gn8 (NVIDIA GPU instances) |
| CPU | Any non-GPU instance |
| PPU | ebmppu (Hanguang instances) |
| XPU | egs (XPU instances) |

### Query Image Chip Type

```bash
aliyun aiworkspace get-image --image-id <image-id> --user-agent AlibabaCloud-Agent-Skills | \
  jq -r '.Labels[] | select(.Key == "system.chipType") | .Value'
```

### Query Instance Type GPU Info

```bash
aliyun eas describe-machine-spec --region <region> --user-agent AlibabaCloud-Agent-Skills | \
  jq -r '.InstanceMetas[] | select(.InstanceType == "<instance-type>") | {InstanceType, GPUAmount, GPU}'
```

### Common Errors

```
❌ Wrong:
Image: vllm:0.14.0-xpu (XPU chip)
Instance: ecs.gn7-c12g1.12xlarge (GPU instance)
Result: Instance crashed - chip type mismatch

✅ Correct:
Image: vllm:0.14.0-gpu (GPU chip)
Instance: ecs.gn7-c12g1.12xlarge (GPU instance)
Result: Deployment successful
```

---

## Pre-deployment Checklist

```
□ Confirm model type (LLM / Image / Speech / Custom)
□ Select matching image category
□ Confirm model format is compatible with image
□ Confirm image chip type matches instance type
□ Confirm model file completeness (config.json, tokenizer, etc.)
□ Confirm model path is mounted correctly
```
