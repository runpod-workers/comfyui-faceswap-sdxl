# Base image: all deps + baked models for ComfyUI SDXL face swap pipeline
# ---------------------------------------------------------------------------
# Single-stage build. Previously had a builder stage to compile
# llama-cpp-python with CUDA; replaced with HF transformers Qwen2.5-VL after
# the GGML buffer scheduler crashed on multi-face inputs.
# ---------------------------------------------------------------------------
FROM runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04

# System deps for OpenCV / image processing (SSH already in base image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libxcb1 libx11-6 libxext6 libsm6 \
    && rm -rf /var/lib/apt/lists/*

# Install ComfyUI + clone custom nodes (single layer, remove .git dirs)
RUN git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git /comfyui \
    && cd /comfyui/custom_nodes \
    && git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Impact-Pack \
    && git clone --depth 1 https://github.com/ltdrdata/comfyui-impact-subpack \
    && git clone --depth 1 https://github.com/cubiq/ComfyUI_IPAdapter_plus \
    && git clone --depth 1 https://github.com/cubiq/ComfyUI_InstantID \
    && find /comfyui -name ".git" -type d -exec rm -rf {} + 2>/dev/null || true

WORKDIR /comfyui

# Install all pip deps in fewer layers, clean cache after each
RUN pip install -r requirements.txt \
    && cd custom_nodes/ComfyUI-Impact-Pack && pip install -r requirements.txt && python install.py \
    && cd /comfyui/custom_nodes/comfyui-impact-subpack && [ -f requirements.txt ] && pip install -r requirements.txt || true \
    && cd /comfyui/custom_nodes/ComfyUI_IPAdapter_plus && [ -f requirements.txt ] && pip install -r requirements.txt || true \
    && cd /comfyui/custom_nodes/ComfyUI_InstantID && [ -f requirements.txt ] && pip install -r requirements.txt || true \
    && pip cache purge && rm -rf /root/.cache/pip

# Pin insightface + onnxruntime-gpu LAST
# Must uninstall CPU onnxruntime first — it shadows the GPU version's CUDAExecutionProvider
RUN pip uninstall -y onnxruntime onnxruntime-gpu 2>/dev/null; \
    pip install insightface==0.7.3 onnxruntime-gpu runpod nest_asyncio huggingface_hub \
    && pip cache purge && rm -rf /root/.cache/pip

# transformers >= 4.49 is required for Qwen2.5-VL (Qwen2_5_VLForConditionalGeneration).
# bitsandbytes lets us load Qwen in 4-bit nf4 to keep VLM VRAM ~3 GB (fits 32 GB pipeline).
RUN pip install "transformers>=4.49.0" accelerate bitsandbytes \
    && pip cache purge && rm -rf /root/.cache/pip

# Validate critical deps at build time
RUN python -c "\
import insightface; assert insightface.__version__ == '0.7.3', f'insightface={insightface.__version__}'; \
import onnxruntime; provs = onnxruntime.get_available_providers(); \
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig; \
import bitsandbytes; \
print(f'insightface OK, onnxruntime providers: {provs}, transformers + bitsandbytes OK')"

# ---------------------------------------------------------------------------
# Bake all models into the image (download + cleanup in ONE layer)
# ---------------------------------------------------------------------------
ENV MODELS_DIR=/baked-models
ENV HF_HOME=/tmp/hf_cache

ARG HF_TOKEN=""
COPY download_models.py /tmp/download_models.py
RUN HF_TOKEN=${HF_TOKEN} python /tmp/download_models.py \
    && rm /tmp/download_models.py \
    && rm -rf /tmp/hf_cache /root/.cache/huggingface /root/.cache/pip \
    && mkdir -p /baked-models/comfyui && echo "v5" > /baked-models/comfyui/.install_complete

# Redirect HuggingFace cache to network volume for any runtime downloads
ENV HF_HOME=/runpod-volume/hf_cache
