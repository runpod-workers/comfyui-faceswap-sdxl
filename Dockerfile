# ComfyUI SDXL Face Swap — single optimized image
# ---------------------------------------------------------------------------
# Stage 1: compile llama-cpp-python with CUDA (needs nvcc from devel image)
# ---------------------------------------------------------------------------
FROM runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04 AS builder

RUN CUDACXX=/usr/local/cuda/bin/nvcc CMAKE_ARGS="-DGGML_CUDA=on" \
    pip install llama-cpp-python --no-cache-dir \
    && pip cache purge \
    && rm -rf /root/.cache/pip /root/.cache/cmake /tmp/cmake* /tmp/pip*

# ---------------------------------------------------------------------------
# Stage 2: runtime image (same base, but fresh — no build artifacts in layers)
# ---------------------------------------------------------------------------
FROM runpod/pytorch:2.8.0-py3.11-cuda12.8.1-cudnn-devel-ubuntu22.04

# Copy compiled llama-cpp-python from builder
COPY --from=builder /usr/local/lib/python3.11/dist-packages/llama_cpp /usr/local/lib/python3.11/dist-packages/llama_cpp
COPY --from=builder /usr/local/lib/python3.11/dist-packages/llama_cpp_python* /usr/local/lib/python3.11/dist-packages/

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

# Validate critical deps at build time (llama_cpp needs libcuda.so.1 — runtime only)
RUN python -c "\
import insightface; assert insightface.__version__ == '0.7.3', f'insightface={insightface.__version__}'; \
import onnxruntime; provs = onnxruntime.get_available_providers(); \
print(f'insightface OK, onnxruntime providers: {provs}'); \
import importlib.util; assert importlib.util.find_spec('llama_cpp'), 'llama_cpp not found'; \
print('llama_cpp package found (GPU import validated at runtime)')"

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

# Runtime dep for llama-cpp-python (not copied from builder stage)
RUN pip install diskcache --no-cache-dir

# Copy application code
COPY handler.py /handler.py
COPY comfyui_character.py /comfyui_character.py

CMD ["python", "-u", "/handler.py"]
