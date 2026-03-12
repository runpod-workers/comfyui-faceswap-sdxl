"""Download and bake all models into the Docker image at build time.

Used by Dockerfile: COPY download_models.py /tmp/ && RUN python /tmp/download_models.py
Reads MODELS_DIR from environment (default: /baked-models).
"""
import os
import shutil
import urllib.request

from huggingface_hub import hf_hub_download

MODELS_DIR = os.environ.get("MODELS_DIR", "/baked-models")


def dl(repo, filename, dest_subdir, dest_name=None, token=None):
    """Download a file from HuggingFace Hub and copy to dest."""
    dest_name = dest_name or filename.split("/")[-1]
    dest_dir = os.path.join(MODELS_DIR, dest_subdir)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, dest_name)
    print(f"  {repo}/{filename} -> {dest}")
    p = hf_hub_download(repo, filename, token=token)
    shutil.copy(p, dest)


def dl_url(url, dest_subdir, dest_name):
    """Download a file from a direct URL."""
    dest_dir = os.path.join(MODELS_DIR, dest_subdir)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, dest_name)
    print(f"  {url} -> {dest}")
    urllib.request.urlretrieve(url, dest)


hf_token = os.environ.get("HF_TOKEN", "")

# --- Checkpoints ---
print("Downloading checkpoints...")
dl("cyberdelia/CyberRealisticXL", "CyberRealisticXLPlay_V7.0_FP16.safetensors",
   "models/checkpoints", "cyberrealistic_xl_v7.safetensors")
dl("RunDiffusion/Juggernaut-XI-v11", "Juggernaut-XI-byRunDiffusion.safetensors",
   "models/checkpoints", token=hf_token)

# --- CLIP Vision ---
print("Downloading CLIP Vision...")
dl("laion/CLIP-ViT-H-14-laion2B-s32B-b79K", "open_clip_model.safetensors",
   "models/clip_vision", "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors")

# --- IPAdapter ---
print("Downloading IPAdapter models...")
dl("h94/IP-Adapter-FaceID", "ip-adapter-faceid-plusv2_sdxl.bin", "models/ipadapter")
dl("h94/IP-Adapter-FaceID", "ip-adapter-faceid-plusv2_sdxl_lora.safetensors", "models/loras")
dl("h94/IP-Adapter", "sdxl_models/ip-adapter-plus-face_sdxl_vit-h.safetensors",
   "models/ipadapter", "ip-adapter-plus-face_sdxl_vit-h.safetensors")

# --- InstantID ---
print("Downloading InstantID...")
dl("InstantX/InstantID", "ControlNetModel/diffusion_pytorch_model.safetensors",
   "models/controlnet", "diffusion_pytorch_model_instantid.safetensors")
dl("InstantX/InstantID", "ip-adapter.bin", "models/instantid")

# --- SAM ---
print("Downloading SAM...")
dl("ybelkada/segment-anything", "checkpoints/sam_vit_b_01ec64.pth",
   "models/sams", "sam_vit_b_01ec64.pth")

# --- InsightFace ---
print("Downloading InsightFace antelopev2...")
for f in ["1k3d68.onnx", "2d106det.onnx", "genderage.onnx", "glintr100.onnx", "scrfd_10g_bnkps.onnx"]:
    dl("lithiumice/insightface", f"models/antelopev2/{f}",
       "models/insightface/models/antelopev2", f)

print("Downloading InsightFace buffalo_l...")
for f in ["1k3d68.onnx", "2d106det.onnx", "det_10g.onnx", "genderage.onnx", "w600k_r50.onnx"]:
    dl("lithiumice/insightface", f"models/buffalo_l/{f}",
       "models/insightface/models/buffalo_l", f)

# --- YOLO face detector ---
print("Downloading YOLOv8m face detector...")
dl_url("https://huggingface.co/Bingsu/adetailer/resolve/main/face_yolov8m.pt",
       "models/ultralytics/bbox", "face_yolov8m.pt")

# --- Qwen2.5-VL-3B (vision model for face picking) ---
print("Downloading Qwen2.5-VL-3B (GGUF + mmproj)...")
dl("mradermacher/Qwen2.5-VL-3B-Instruct-GGUF", "Qwen2.5-VL-3B-Instruct.Q4_K_M.gguf", "llm")
dl("Mungert/Qwen2.5-VL-3B-Instruct-GGUF", "Qwen2.5-VL-3B-Instruct-mmproj-f16.gguf", "llm")

print("All models downloaded.")
