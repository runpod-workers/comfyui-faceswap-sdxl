<!-- Do not edit or remove this section -->
This document exists for non-obvious, error-prone shortcomings in the codebase, the model, or the tooling that an agent cannot figure out by reading the code alone. No architecture overviews, file trees, build commands, or standard behavior. When you encounter something that belongs here, first consider whether a code change could eliminate it and suggest that to the user. Only document it here if it can't be reasonably fixed.

---

## Qwen2.5-VL face picker uses HF transformers, not llama-cpp-python

The previous llama-cpp-python/GGUF path crashed in `libmtmd`'s `clip_image_batch_encode` on multi-face inputs (`GGML_ASSERT` buffer-bounds check at `ggml-backend.cpp:1668`). The crash was data-dependent and not fixable by tuning `n_ctx`/`n_batch` alone, so the picker was migrated to `Qwen2_5_VLForConditionalGeneration` from `transformers`. Don't reintroduce llama-cpp-python for VLM use.

## VRAM budget (32 GB)

SDXL pipeline: ~19.2 GB. Qwen2.5-VL-3B in nf4 4-bit via bitsandbytes (HF transformers, loaded at startup): ~3 GB. Face swap worst case with VLM loaded: ~29.5–30 GB on a 32 GB GPU, leaving ~2–2.5 GB headroom — same envelope as the prior Q4_K_M GGUF. Don't switch to bf16/fp16 (~6 GB) without a bigger GPU; the worst case spills past 32 GB. The previous UI-TARS 7B (~6.7 GB) caused OOM during face swap — that's why we switched to Qwen2.5-VL-3B.

## bitsandbytes 4-bit quirks

Don't call `.to("cuda")` on a `BitsAndBytesConfig`-loaded model — bnb manages device placement during `from_pretrained` via `device_map`. Calling `.to(...)` raises `ValueError: .to is not supported for 4-bit models`. Use `device_map="cuda:0"` at load time and don't move the model afterward.
