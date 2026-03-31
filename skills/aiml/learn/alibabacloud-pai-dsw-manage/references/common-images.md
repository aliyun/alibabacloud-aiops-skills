# Common Images — alibabacloud-pai-dsw-manage

Official preset images for PAI DSW. Pass the image URL via `--image-url` when creating an instance.

> The `pai-dsw` CLI plugin has no `list-images` subcommand. Browse the full catalog on the [PAI Console](https://pai.console.aliyun.com/) during instance creation, or use the images listed below. Versions are updated regularly — verify the latest in the console.

---

## URL Format

```
dsw-registry-vpc.{region}.cr.aliyuncs.com/pai/{framework}:{tag}
```

| Placeholder | Example |
|---|---|
| `{region}` | `cn-hangzhou`, `cn-shanghai`, `cn-beijing`, `cn-wulanchabu` |
| `{framework}` | `modelscope`, `pytorch`, `tensorflow`, `torcheasyrec` |
| `{tag}` | `1.34.0-pytorch2.3.1-cpu-py311-ubuntu22.04` |

Tag format: `{version}-pytorch{ver}-{cpu|gpu}-py{pyVer}[-cu{cudaVer}]-ubuntu{ver}`

---

## CPU Images

| Framework | Image URL (cn-shanghai) |
|---|---|
| ModelScope + PyTorch 2.3 | `dsw-registry-vpc.cn-shanghai.cr.aliyuncs.com/pai/modelscope:1.34.0-pytorch2.3.1-cpu-py311-ubuntu22.04` |
| TorchEasyRec + PyTorch 2.10 | `dsw-registry-vpc.cn-shanghai.cr.aliyuncs.com/pai/torcheasyrec:1.1.0-pytorch2.10.0-cpu-py311-ubuntu22.04` |

## GPU Images

| Framework | Image URL (cn-shanghai) |
|---|---|
| ModelScope + PyTorch 2.8 + CUDA 12.4 | `dsw-registry-vpc.cn-shanghai.cr.aliyuncs.com/pai/modelscope:1.31.0-pytorch2.8.0-gpu-py311-cu124-ubuntu22.04` |

---

## Usage

1. **Replace the region** — match the `{region}` segment to your workspace location.
2. **Match CPU/GPU** — use `cpu` images for CPU specs and `gpu` images for GPU specs.
3. **Choose one image parameter**:
   - `--image-url` — direct URL (official presets or custom ACR images)
   - `--image-id` — PAI-assigned image ID (e.g., `image-xxxxx`), from the console
4. **Custom ACR images** — use a private registry URL and supply `--image-auth` (base64-encoded credentials).

## Not Available via CLI

- **List images** — no `list-images` subcommand. Use the [PAI Console > Create Instance](https://pai.console.aliyun.com/) page.
- **Image metadata** — framework version, Python version, CUDA version, etc. are not queryable via CLI.
