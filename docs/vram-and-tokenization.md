# Qwen2.5-VL Image Tokenization

## Measured Token Counts

Measured by running Qwen2.5-VL-3B with an 832x1216 image (default SDXL portrait output). The vision encoder reported:

```
image_tokens->nx = 25
image_tokens->ny = 37
```

**925 image tokens** for a single 832x1216 image (~33 pixels per token).

| Resolution | Token Grid | Total Tokens | Notes |
|------------|-----------|--------------|-------|
| 832x1216 | 25x37 | 925 | Measured |
| 1024x1024 | ~31x31 | ~961 | Extrapolated |
| 1216x832 | ~37x25 | ~925 | Extrapolated |

## Total Prompt Size

With system prompt (~20 tokens), image (925), and text prompt (~60), the total is **~1,005 tokens** — only 25% of the 4,096 context window.

**`n_ctx=4096` is sufficient.** The `n_ctx_per_seq (4096) < n_ctx_train (128000)` warning from llama.cpp is safe to ignore.

## KV Cache Cost Per Context Size

The KV cache is where tokens consume VRAM. Calculated from model metadata (36 layers, n_embd_k/v_gqa = 256, f16):

| n_ctx | KV Cache |
|-------|----------|
| 4,096 | 144 MB |
| 8,192 | 288 MB |
| 16,384 | 576 MB |

Since the actual prompt is ~1,005 tokens, **n_ctx=4096 wastes ~3,091 token slots (108 MB)** of pre-allocated KV cache that will never be used. Lowering n_ctx to 2048 would save 72 MB but leaves little margin. 4096 is a reasonable default.

## Runpod SSH Limitation

GPU benchmarks via SSH on Runpod pods are not possible — `cuInit` returns error 100 "no device". The NVIDIA container runtime only grants GPU access to processes started by the container entrypoint. Use `curl -s http://localhost:8188/system_stats` to query GPU state instead.
