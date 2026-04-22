<!-- Do not edit or remove this section -->
This document exists for non-obvious, error-prone shortcomings in the codebase, the model, or the tooling that an agent cannot figure out by reading the code alone. No architecture overviews, file trees, build commands, or standard behavior. When you encounter something that belongs here, first consider whether a code change could eliminate it and suggest that to the user. Only document it here if it can't be reasonably fixed.

---

## llama-cpp-python has no prebuilt wheels for CUDA 12.8

No `--extra-index-url` wheel exists for cu128 (official wheels only cover cu121–cu125). Must build from source with `CUDACXX=/usr/local/cuda/bin/nvcc CMAKE_ARGS="-DGGML_CUDA=on"`. Without these env vars, `pip install llama-cpp-python` silently succeeds but falls back to CPU-only — no error, just all layers placed on CPU. See llama-cpp-python issues #2068 and #2079.

## Qwen2.5-VL needs a separate mmproj file for vision

The language model GGUF alone (from mradermacher) does NOT support image input — it silently falls back to text-only. You need the mmproj (vision encoder) from `Mungert/Qwen2.5-VL-3B-Instruct-GGUF` (`Qwen2.5-VL-3B-Instruct-mmproj-f16.gguf`, ~1.3 GB). Must use `Qwen25VLChatHandler` (not `Llava16ChatHandler`) — the Llava handler produces empty/garbage responses with Qwen2.5-VL models.

## VRAM budget (32 GB)

SDXL pipeline: ~19.2 GB. Face swap worst case: ~29.5 GB. The Qwen2.5-VL-3B Q4_K_M VLM (~2.3 GB) is loaded on-demand in `_pick_face_with_vision` and unloaded immediately after — keeping it resident caused GGML_ASSERT aborts in `clip_image_batch_encode` because the vision encoder's graph allocator had no room alongside the resident SDXL models. Q3_K_M and smaller quants produce empty/broken vision responses — Q4_K_M is the minimum viable quant. The previous UI-TARS 7B (~6.7 GB) caused OOM during face swap — that's why we switched to Qwen2.5-VL-3B.
