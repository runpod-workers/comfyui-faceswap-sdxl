# VRAM Budget & Image Tokenization Analysis

Measured on a Runpod 4090 pod (24 GB VRAM) running the ComfyUI faceswap worker with Qwen2.5-VL-3B Q4_K_M for vision-based face picking.

## Qwen2.5-VL Image Tokenization

Measured on an 832x1216 image (default SDXL portrait output):

| Resolution | Token Grid | Total Tokens | Notes |
|------------|-----------|--------------|-------|
| 832x1216 | 25x37 | 925 | Default SDXL portrait |
| 1024x1024 | ~31x31 | ~961 | SDXL square |
| 1216x832 | ~37x25 | ~925 | SDXL landscape |

The vision encoder produces approximately one token per ~33 pixels. With system prompt (~20 tokens), image (925), and text prompt (~60), the total prompt is **~1,005 tokens** — only 25% of the 4,096 context window.

**`n_ctx=4096` is sufficient.** There is no benefit to increasing it for this workload. The `n_ctx_per_seq (4096) < n_ctx_train (128000)` warning from llama.cpp is safe to ignore.

## VLM VRAM Breakdown (Qwen2.5-VL-3B Q4_K_M, all on GPU)

| Component | Size |
|-----------|------|
| Model weights (Q4_K_M) | 1,833 MB |
| mmproj (vision encoder, f16) | 1,300 MB |
| KV cache (n_ctx=4096) | 144 MB |
| Compute buffer | 301 MB |
| **Total** | **~3,578 MB (3.5 GB)** |

KV cache scales linearly with context size:

| n_ctx | KV Cache | Total VLM |
|-------|----------|-----------|
| 4,096 | 144 MB | 3,578 MB |
| 8,192 | 288 MB | 3,722 MB |
| 16,384 | 576 MB | 4,010 MB |

## VRAM Budget: 4090 (24 GB)

| Component | VRAM |
|-----------|------|
| SDXL pipeline | ~19,200 MB |
| VLM (n_ctx=4096) | ~3,578 MB |
| **Total** | **~22,778 MB** |
| **Headroom** | **~1,798 MB** |

Tight but viable. Bumping n_ctx to 8192 costs only +144 MB; 16384 costs +432 MB — both still fit.

## VRAM Budget: 32 GB GPU (reference)

| Component | VRAM |
|-----------|------|
| SDXL pipeline | ~19,200 MB |
| VLM (n_ctx=4096) | ~3,578 MB |
| **Total** | **~22,778 MB** |
| **Headroom** | **~9,990 MB** |

Face swap worst case with VLM loaded: ~29.5 GB. Headroom: ~2.5 GB.

## Runpod SSH Sessions Cannot Access the GPU

Processes spawned via SSH on Runpod pods do not have GPU access (`cuInit` returns error 100 "no device"). The NVIDIA container runtime only injects GPU access for processes started by the container entrypoint. The running ComfyUI/handler processes (PID 1's children) have GPU access; SSH-spawned processes do not, even with correct `NVIDIA_VISIBLE_DEVICES` and `LD_LIBRARY_PATH` env vars set.

**Workaround:** To query GPU state from SSH, use the ComfyUI API:

```bash
curl -s http://localhost:8188/system_stats
```

This returns device info including VRAM usage, bypassing the need for `nvidia-smi`.
