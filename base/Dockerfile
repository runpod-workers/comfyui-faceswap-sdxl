# Base image: all deps + baked models for ComfyUI face swap pipeline
FROM runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04

# System deps for OpenCV / image processing (SSH already in base image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libxcb1 libx11-6 libxext6 libsm6 \
    && rm -rf /var/lib/apt/lists/*

# Install ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /comfyui
WORKDIR /comfyui
RUN pip install -r requirements.txt

# Clone custom nodes + install their deps
RUN cd custom_nodes && \
    git clone https://github.com/ltdrdata/ComfyUI-Impact-Pack && \
    git clone https://github.com/ltdrdata/comfyui-impact-subpack && \
    git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus && \
    git clone https://github.com/cubiq/ComfyUI_InstantID
RUN cd custom_nodes/ComfyUI-Impact-Pack && pip install -r requirements.txt && python install.py
RUN cd custom_nodes/comfyui-impact-subpack && [ -f requirements.txt ] && pip install -r requirements.txt || true
RUN cd custom_nodes/ComfyUI_IPAdapter_plus && [ -f requirements.txt ] && pip install -r requirements.txt || true
RUN cd custom_nodes/ComfyUI_InstantID && [ -f requirements.txt ] && pip install -r requirements.txt || true

# Pin insightface + onnxruntime-gpu LAST
# Must uninstall CPU onnxruntime first — it shadows the GPU version's CUDAExecutionProvider
RUN pip uninstall -y onnxruntime onnxruntime-gpu 2>/dev/null; \
    pip install insightface==0.7.3 onnxruntime-gpu runpod nest_asyncio

# llama-cpp-python with CUDA for Qwen2.5-VL vision model (face picker)
# No prebuilt wheels for CUDA 12.8 — must build from source
RUN CUDACXX=/usr/local/cuda/bin/nvcc CMAKE_ARGS="-DGGML_CUDA=on" \
    pip install llama-cpp-python --no-cache-dir

# Validate critical deps at build time
RUN python -c "\
import insightface; assert insightface.__version__ == '0.7.3', f'insightface={insightface.__version__}'; \
import onnxruntime; provs = onnxruntime.get_available_providers(); \
print(f'insightface OK, onnxruntime providers: {provs}')"

# Install huggingface_hub for model downloads at build time
RUN pip install huggingface_hub

# ---------------------------------------------------------------------------
# Bake all models into the image for fast cold start
# ---------------------------------------------------------------------------
ENV MODELS_DIR=/baked-models
ENV HF_HOME=/tmp/hf_cache

ARG HF_TOKEN=""
COPY download_models.py /tmp/download_models.py
RUN HF_TOKEN=${HF_TOKEN} python /tmp/download_models.py && rm /tmp/download_models.py

# Write sentinel so _download_models() is skipped at runtime
RUN mkdir -p /baked-models/comfyui && echo "v5" > /baked-models/comfyui/.install_complete

# Clean HF cache to reduce image size
RUN rm -rf /tmp/hf_cache /root/.cache/huggingface

# Redirect HuggingFace cache to network volume for any runtime downloads
ENV HF_HOME=/runpod-volume/hf_cache
