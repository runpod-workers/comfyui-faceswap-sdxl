# Qwen2.5-VL Image Tokenization

## Backend

The face picker uses `Qwen2_5_VLForConditionalGeneration` from `transformers` (bf16). The earlier llama-cpp-python/GGUF backend was removed because it crashed with `GGML_ASSERT` in `libmtmd`'s `clip_image_batch_encode` on multi-face inputs (data-dependent buffer-bounds violation in the GGML scheduler).

## Image Token Budget

Qwen2.5-VL packs ~33 pixels into one vision token. For an 832x1216 SDXL portrait the encoder produces a 25x37 grid (~925 image tokens). With ~80 tokens of system+user text on top, a single picker call needs ~1,005 tokens — well under the 32k native context.

| Resolution | Token Grid | Total Tokens |
|------------|-----------|--------------|
| 832x1216   | 25x37     | 925          |
| 1024x1024  | ~31x31    | ~961         |
| 1216x832   | ~37x25    | ~925         |

Transformers handles the buffer arithmetic internally, so there is no `n_ctx`/`n_batch` tuning to do here.

## VRAM

Loaded in nf4 4-bit via `bitsandbytes` (`BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4")`): ~3 GB total. Loaded at startup. See `CLAUDE.md` for the full pipeline budget.

## Runpod SSH Limitation

GPU benchmarks via SSH on Runpod pods are not possible — `cuInit` returns error 100 "no device". The NVIDIA container runtime only grants GPU access to processes started by the container entrypoint. Use `curl -s http://localhost:8188/system_stats` to query GPU state instead.
