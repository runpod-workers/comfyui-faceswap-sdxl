# VRAM Budget & Image Tokenization Analysis

## Qwen2.5-VL Image Tokenization (measured)

Measured by running the VLM on a Runpod 4090 pod (CPU fallback — see "Runpod SSH" section below). The tokenization output is valid regardless of CPU/GPU since it comes from the vision encoder.

An 832x1216 image (default SDXL portrait output):

| Resolution | Token Grid | Total Tokens | Notes |
|------------|-----------|--------------|-------|
| 832x1216 | 25x37 | 925 | Default SDXL portrait (measured) |
| 1024x1024 | ~31x31 | ~961 | SDXL square (extrapolated) |
| 1216x832 | ~37x25 | ~925 | SDXL landscape (extrapolated) |

The vision encoder produces approximately one token per ~33 pixels. With system prompt (~20 tokens), image (925), and text prompt (~60), the total prompt is **~1,005 tokens** — only 25% of the 4,096 context window.

**`n_ctx=4096` is sufficient.** There is no benefit to increasing it for this workload. The `n_ctx_per_seq (4096) < n_ctx_train (128000)` warning from llama.cpp is safe to ignore.

## VLM VRAM Breakdown (calculated, not measured)

Calculated from model metadata, file sizes, and llama.cpp verbose output. These are theoretical estimates — real GPU VRAM usage was not measured due to the Runpod SSH GPU access limitation.

| Component | Size | Source |
|-----------|------|--------|
| Model weights (Q4_K_M) | 1,833 MB | File size (1.79 GiB) |
| mmproj (vision encoder, f16) | 1,300 MB | File size (~1.3 GiB) |
| KV cache (n_ctx=4096) | 144 MB | llama.cpp output + formula |
| Compute buffer | 301 MB | llama.cpp output |
| **Total VLM only** | **~3,578 MB (3.5 GB)** | |

KV cache scales linearly with context size:

| n_ctx | KV Cache | Total VLM |
|-------|----------|-----------|
| 4,096 | 144 MB | 3,578 MB |
| 8,192 | 288 MB | 3,722 MB |
| 16,384 | 576 MB | 4,010 MB |

## Full Pipeline VRAM: Does NOT Fit on 4090

The full faceswap pipeline loads all models simultaneously (nothing is unloaded between steps):

1. **SDXL generation**: CyberRealistic model + CLIP + VAE + IPAdapter FaceID + IPAdapter Plus + CLIP Vision + InsightFace (~19.2 GB)
2. **VLM face picking**: Qwen2.5-VL-3B Q4_K_M + mmproj (~3.5 GB)
3. **Face swap**: Juggernaut model + InstantID + ControlNet + InsightFace + SAM + YOLO detector (additional VRAM)

Worst case with everything loaded: **~29.5 GB**. This only fits on a 32 GB GPU with ~2.5 GB headroom.

| GPU | VRAM | Fits? | Headroom |
|-----|------|-------|----------|
| 4090 | 24 GB | **NO** | -5.5 GB over budget |
| 32 GB (e.g. V100, A100) | 32 GB | YES | ~2.5 GB |

To fit on a 4090, the pipeline would need model offloading between stages (e.g., unload VLM before face swap, or swap SDXL models to CPU). This is not currently implemented.

## Runpod SSH Sessions Cannot Access the GPU

Processes spawned via SSH on Runpod pods do not have GPU access (`cuInit` returns error 100 "no device"). The NVIDIA container runtime only injects GPU access for processes started by the container entrypoint. The running ComfyUI/handler processes (PID 1's children) have GPU access; SSH-spawned processes do not, even with correct `NVIDIA_VISIBLE_DEVICES` and `LD_LIBRARY_PATH` env vars set.

This means you cannot run standalone GPU benchmarks or VRAM measurement scripts via SSH. The llama-cpp-python model silently falls back to CPU-only with all layers on CPU.

**Workaround:** To query GPU state from SSH, use the ComfyUI API:

```bash
curl -s http://localhost:8188/system_stats
```

This returns device info including VRAM usage, bypassing the need for `nvidia-smi`.
