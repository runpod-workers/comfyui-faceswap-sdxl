FROM runpod/comfyui-faceswap-base:latest

WORKDIR /comfyui

# Copy application code (base image has all deps + models baked in)
COPY handler.py /handler.py
COPY comfyui_character.py /comfyui_character.py

CMD ["python", "-u", "/handler.py"]
