# ComfyUI FaceSwap SDXL — RunPod Serverless

Character generation with optional face swap, deployed as a RunPod serverless endpoint.

## Docker Image

```
runpod/comfyui-faceswap-sdxl:latest
```

All models are baked into the image for fast cold starts — no network volume required for inference.

## Deploy on RunPod

1. Create a new **Serverless Endpoint** on [runpod.io](https://www.runpod.io/)
2. Set the Docker image to `runpod/comfyui-faceswap-sdxl:latest`
3. Select a GPU with **at least 32 GB VRAM** (e.g. A100 40GB, A6000)
4. Optionally attach a network volume mounted at `/runpod-volume` if you want to persist generated images

## API Usage

### Request

```
POST https://api.runpod.ai/v2/{YOUR_ENDPOINT_ID}/runsync
Authorization: Bearer {YOUR_RUNPOD_API_KEY}
Content-Type: application/json
```

Use `/runsync` for synchronous requests (waits for the result). For async, use `/run` and poll `/status/{JOB_ID}`.

```json
{
  "input": {
    "prompt": "a confident woman in a business suit, professional lighting",
    "negative_prompt": "bad quality, blurry, deformed",
    "width": 832,
    "height": 1216,
    "steps": 35,
    "cfg": 2.0,
    "seed": 42,
    "image_url": "https://example.com/face.png",
    "face_description": "the woman on the left",
    "output": {
      "include_base64": true,
      "save_to_volume": false,
      "volume_path": "outputs"
    }
  }
}
```

### Parameters

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `prompt` | yes | — | Character description |
| `negative_prompt` | no | `""` | What to avoid |
| `width` | no | `832` | Image width |
| `height` | no | `1216` | Image height |
| `steps` | no | `35` | Sampling steps |
| `cfg` | no | `2.0` | CFG scale |
| `seed` | no | random | Reproducible seed |
| `image_url` | no | — | Face reference URL (enables face swap) |
| `face_description` | no | `""` | Which face to pick from reference |
| `output.include_base64` | no | `true` | Return base64 PNG |
| `output.save_to_volume` | no | `false` | Save to network volume |
| `output.volume_path` | no | `"outputs"` | Folder on `/runpod-volume/` |

### Modes

- **Text only:** Omit `image_url` — generates character from prompt using CyberRealistic XL
- **Face swap:** Provide `image_url` — generates character, then applies face from reference using IPAdapter + InstantID
- **Face picking:** Provide `face_description` alongside `image_url` — uses a vision model to pick the matching face from multi-face scenes instead of defaulting to the largest face

### Response

```json
{
  "delayTime": 102,
  "executionTime": 4019,
  "id": "sync-12e21de8-...",
  "output": {
    "duration_seconds": 3.42,
    "image_base64": "<base64-encoded PNG>",
    "image_path": "/runpod-volume/outputs/42_1773510473.png",
    "seed": 42,
    "status": "success"
  },
  "status": "COMPLETED"
}
```

### Resolution Presets

| Name | Dimensions |
|------|-----------|
| `portrait` | 832 x 1216 |
| `landscape` | 1216 x 832 |
| `square` | 1024 x 1024 |
| `small-portrait` | 640 x 960 |
| `small-landscape` | 960 x 640 |

## Models

All models are baked into the Docker image at build time for fast cold starts.

| Model | Purpose | Size |
|-------|---------|------|
| CyberRealistic XL v7 | Primary SDXL generation | ~6.5 GB |
| Juggernaut XI | InstantID face refinement | ~6.5 GB |
| CLIP-ViT-H-14 | Vision encoding for IPAdapter | ~3.9 GB |
| IPAdapter FaceID Plus v2 SDXL | Face identity transfer | ~0.8 GB |
| IPAdapter Plus Face SDXL | Face style transfer | ~0.8 GB |
| InstantID ControlNet + Adapter | Face structure preservation | ~1.7 GB |
| SAM ViT-B | Face segmentation masks | ~0.4 GB |
| InsightFace (antelopev2 + buffalo_l) | Face detection/recognition | ~0.3 GB |
| YOLOv8m Face | Face bounding box detection | ~0.05 GB |
| Qwen2.5-VL-3B Q4_K_M (GGUF) | Vision-based face picking | ~2.3 GB VRAM |

## GPU Requirements

- **Startup:** ~21.7 GB VRAM
- **Peak (face swap):** ~29.5 GB VRAM
- **Minimum GPU VRAM:** 32 GB

## Benchmark

A benchmark script is included to test endpoint performance.

```bash
pip install requests
export RUNPOD_API_KEY=your_key
```

The script uses the endpoint ID defined in `benchmark.py` — update the `ENDPOINT_ID` variable to match your endpoint before running.

```bash
# Text + face swap, multiple resolutions
python benchmark.py \
  --count 20 \
  --modes text,face \
  --resolutions portrait square \
  --face-url https://example.com/face.png \
  --seed 42

# Text-only
python benchmark.py \
  --count 10 \
  --modes text \
  --resolutions portrait

# Face swap only
python benchmark.py \
  --count 10 \
  --modes face \
  --resolutions portrait \
  --face-url https://example.com/face.png
```

Images are saved to `benchmark_results/<timestamp>/` alongside a `report.json` with full timing data. The first request runs sequentially to capture cold start time; remaining requests run concurrently.

| Flag | Default | Description |
|------|---------|-------------|
| `--count` | `10` | Total requests |
| `--modes` | `text` | Comma-separated: `text`, `face` |
| `--resolutions` | `portrait` | Space-separated: `portrait`, `landscape`, `square`, `small-portrait`, `small-landscape` |
| `--face-url` | — | Face image URL (required for `face` mode) |
| `--face-description` | — | Which face to pick from reference |
| `--steps` | `35` | Sampling steps |
| `--cfg` | `2.0` | CFG scale |
| `--seed` | random | Base seed (incremented per request) |
| `--concurrency` | `3` | Max parallel requests |
| `--output-dir` | `benchmark_results` | Output directory |
| `--timeout` | `600` | Per-job timeout (seconds) |
