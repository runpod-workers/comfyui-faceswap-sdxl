# ComfyUI FaceSwap — RunPod Serverless

Character generation with optional face swap, deployed as a RunPod serverless endpoint.

## Endpoint

- **ID:** `bblp777ptfep17`
- **API:** `https://api.runpod.ai/v2/bblp777ptfep17`
- **Build:** Automatic on push to `main`

## Request Format

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
    "face_description": "",
    "output": {
      "include_base64": true,
      "save_to_volume": false,
      "volume_path": "outputs"
    }
  }
}
```

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
- **Face picking:** When `face_description` is provided alongside `image_url`, uses Qwen2.5-VL-3B vision model to pick the matching face from multi-face scenes instead of defaulting to the largest face

## Models

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

All models are baked into the Docker image at build time for fast cold starts. Total VRAM at startup: ~21.7 GB. Peak during face swap: ~29.5 GB on a 32 GB GPU (~3 GB headroom).

## Benchmark

### Prerequisites

```bash
pip install requests
export RUNPOD_API_KEY=your_key
```

### Quick Start

```bash
# 20 requests: text + face swap, portrait + square, seed for reproducibility
python benchmark.py \
  --count 20 \
  --modes text,face \
  --resolutions portrait square \
  --face-url https://files.catbox.moe/az73pf.png \
  --seed 42
```

### Benchmark Configs

#### Full benchmark (text + face swap, all resolutions)
```bash
python benchmark.py \
  --count 20 \
  --modes text,face \
  --resolutions portrait square landscape \
  --face-url https://files.catbox.moe/az73pf.png \
  --seed 42 \
  --concurrency 3
```

#### Text-only performance test
```bash
python benchmark.py \
  --count 10 \
  --modes text \
  --resolutions portrait square \
  --seed 100
```

#### Face swap quality validation
```bash
python benchmark.py \
  --count 10 \
  --modes face \
  --resolutions portrait \
  --face-url https://files.catbox.moe/az73pf.png \
  --seed 200
```

#### High-res stress test
```bash
python benchmark.py \
  --count 10 \
  --modes text,face \
  --resolutions portrait landscape square \
  --face-url https://files.catbox.moe/az73pf.png \
  --concurrency 5 \
  --seed 300
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--count` | `10` | Total requests |
| `--modes` | `text` | Comma-separated: `text`, `face` |
| `--resolutions` | `portrait` | Space-separated presets (see below) |
| `--face-url` | — | Face image URL (required for `face` mode) |
| `--face-description` | — | Which face to pick from reference |
| `--steps` | `35` | Sampling steps |
| `--cfg` | `2.0` | CFG scale |
| `--seed` | random | Base seed (incremented per request) |
| `--concurrency` | `3` | Max parallel requests |
| `--output-dir` | `benchmark_results` | Where to save images + report |
| `--timeout` | `600` | Per-job timeout (seconds) |

### Resolution Presets

| Name | Dimensions |
|------|-----------|
| `portrait` | 832 x 1216 |
| `landscape` | 1216 x 832 |
| `square` | 1024 x 1024 |
| `small-portrait` | 640 x 960 |
| `small-landscape` | 960 x 640 |

### Output

Images are saved to `benchmark_results/<timestamp>/` with filenames like:
```
003_faceswap_1024x1024_steps35_cfg2.0_seed45.png
```

A `report.json` with full timing data is saved alongside the images.

The first request runs sequentially to capture cold start time. Remaining requests run concurrently. The summary shows per-resolution/mode breakdowns.
