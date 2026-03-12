FROM runpod/comfyui-faceswap-base:latest

WORKDIR /comfyui

# ---------------------------------------------------------------------------
# Bake all models into the image for fast cold start (NVMe instead of network volume)
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

# Copy application code
COPY handler.py /handler.py
COPY comfyui_character.py /comfyui_character.py

CMD ["python", "-u", "/handler.py"]
