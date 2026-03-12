#!/usr/bin/env python3
"""Benchmark script for ComfyUI FaceSwap on RunPod serverless."""

import argparse
import base64
import json
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("Missing dependency: pip install requests")
    sys.exit(1)

ENDPOINT_ID = "bblp777ptfep17"
API_BASE = f"https://api.runpod.ai/v2/{ENDPOINT_ID}"

RESOLUTIONS = {
    "portrait": (832, 1216),
    "landscape": (1216, 832),
    "square": (1024, 1024),
    "small-portrait": (640, 960),
    "small-landscape": (960, 640),
}

DEFAULT_PROMPTS = [
    "a confident woman in a business suit standing in a modern office, professional lighting",
    "a young man wearing a leather jacket leaning against a brick wall, cinematic",
    "an elderly woman with silver hair sitting in a garden, warm afternoon light",
    "a bearded man in a flannel shirt standing in a forest, moody atmosphere",
    "a woman in athletic wear jogging through a city park, dynamic pose",
]

DEFAULT_NEGATIVE = "bad quality, blurry, deformed, ugly, disfigured"


def get_api_key():
    key = os.environ.get("RUNPOD_API_KEY")
    if not key:
        print("Error: RUNPOD_API_KEY environment variable not set")
        sys.exit(1)
    return key


def submit_job(session, api_key, payload):
    """Submit an async job and return the job id."""
    resp = session.post(
        f"{API_BASE}/run",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"input": payload},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def poll_job(session, api_key, job_id, poll_interval=2, timeout=600):
    """Poll until job completes or times out."""
    start = time.time()
    while time.time() - start < timeout:
        resp = session.get(
            f"{API_BASE}/status/{job_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        if status == "COMPLETED":
            return data.get("output")
        if status in ("FAILED", "CANCELLED", "TIMED_OUT"):
            return {"status": "error", "detail": f"Job {status}: {data}"}
        time.sleep(poll_interval)
    return {"status": "error", "detail": f"Polling timeout after {timeout}s"}


def run_single(session, api_key, payload, index, output_dir, poll_interval=2, timeout=600):
    """Submit, poll, and save result for a single request."""
    mode = "faceswap" if payload.get("image_url") else "text"
    res_label = f"{payload['width']}x{payload['height']}"

    t0 = time.time()
    try:
        job_id = submit_job(session, api_key, payload)
    except Exception as e:
        return {
            "index": index,
            "mode": mode,
            "resolution": res_label,
            "status": "error",
            "error": f"Submit failed: {e}",
            "total_seconds": round(time.time() - t0, 2),
        }

    result = poll_job(session, api_key, job_id, poll_interval=poll_interval, timeout=timeout)
    total = time.time() - t0

    entry = {
        "index": index,
        "job_id": job_id,
        "mode": mode,
        "resolution": res_label,
        "total_seconds": round(total, 2),
        "prompt": payload.get("prompt", "")[:80],
    }

    if isinstance(result, dict) and result.get("status") == "success":
        entry["status"] = "success"
        entry["generation_seconds"] = result.get("duration_seconds")
        entry["seed"] = result.get("seed")

        # Save image with descriptive name
        b64 = result.get("image_base64")
        if b64 and output_dir:
            seed = result.get("seed", "unknown")
            steps = payload.get("steps", 35)
            cfg = payload.get("cfg", 2.0)
            fname = (
                f"{index:03d}_{mode}_{res_label}_steps{steps}_cfg{cfg}_seed{seed}.png"
            )
            img_path = output_dir / fname
            img_path.write_bytes(base64.b64decode(b64))
            entry["image_path"] = str(img_path)
    else:
        entry["status"] = "error"
        entry["detail"] = (
            result.get("detail") if isinstance(result, dict) else str(result)
        )

    return entry


def build_payloads(args):
    """Build the list of request payloads from CLI args."""
    resolutions = []
    for name in args.resolutions:
        if name not in RESOLUTIONS:
            print(f"Unknown resolution: {name}. Available: {', '.join(RESOLUTIONS)}")
            sys.exit(1)
        resolutions.append((name, *RESOLUTIONS[name]))

    modes = args.modes.split(",")
    for m in modes:
        if m not in ("text", "face"):
            print(f"Unknown mode: {m}. Use 'text' and/or 'face'")
            sys.exit(1)

    payloads = []
    prompts = DEFAULT_PROMPTS
    prompt_idx = 0

    while len(payloads) < args.count:
        for _name, w, h in resolutions:
            for mode in modes:
                if len(payloads) >= args.count:
                    break
                prompt = prompts[prompt_idx % len(prompts)]
                p = {
                    "prompt": prompt,
                    "negative_prompt": DEFAULT_NEGATIVE,
                    "width": w,
                    "height": h,
                    "steps": args.steps,
                    "cfg": args.cfg,
                    "output": {"include_base64": True},
                }
                if mode == "face":
                    if not args.face_url:
                        print("Error: --face-url required for 'face' mode")
                        sys.exit(1)
                    p["image_url"] = args.face_url
                    if args.face_description:
                        p["face_description"] = args.face_description
                if args.seed is not None:
                    p["seed"] = args.seed + len(payloads)
                payloads.append(p)
            prompt_idx += 1

    return payloads


def print_breakdown(results):
    """Print per-resolution/mode breakdown."""
    groups = defaultdict(list)
    for r in results:
        key = f"{r['mode']} @ {r['resolution']}"
        groups[key].append(r)

    print(f"\n{'─'*70}")
    print(f"{'Combo':<30} {'N':>3} {'OK':>3} {'Avg Gen':>9} {'Avg Total':>11} {'Min':>7} {'Max':>7}")
    print(f"{'─'*70}")

    for key in sorted(groups):
        entries = groups[key]
        successes = [e for e in entries if e.get("status") == "success"]
        gen_times = [e["generation_seconds"] for e in successes if e.get("generation_seconds")]
        total_times = [e["total_seconds"] for e in successes]

        avg_gen = f"{sum(gen_times)/len(gen_times):.1f}s" if gen_times else "n/a"
        avg_total = f"{sum(total_times)/len(total_times):.1f}s" if total_times else "n/a"
        min_total = f"{min(total_times):.1f}s" if total_times else "n/a"
        max_total = f"{max(total_times):.1f}s" if total_times else "n/a"

        print(
            f"{key:<30} {len(entries):>3} {len(successes):>3} "
            f"{avg_gen:>9} {avg_total:>11} {min_total:>7} {max_total:>7}"
        )

    print(f"{'─'*70}")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark ComfyUI FaceSwap on RunPod",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # 20 requests across text + face swap, multiple resolutions
  %(prog)s --count 20 --modes text,face --resolutions portrait square \\
    --face-url https://files.catbox.moe/az73pf.png --seed 42

  # 10 text-only portrait requests
  %(prog)s --count 10 --modes text --resolutions portrait

  # 5 face swap only, reproducible
  %(prog)s --count 5 --modes face --resolutions portrait \\
    --face-url https://files.catbox.moe/az73pf.png --seed 100
""",
    )
    parser.add_argument(
        "--count", type=int, default=10, help="Total requests (default: 10)"
    )
    parser.add_argument(
        "--modes", default="text", help="Comma-separated: text, face (default: text)"
    )
    parser.add_argument(
        "--resolutions",
        nargs="+",
        default=["portrait"],
        help=f"Presets (default: portrait). Available: {', '.join(RESOLUTIONS)}",
    )
    parser.add_argument("--face-url", help="URL to face image for face swap mode")
    parser.add_argument("--face-description", help="Which face to pick from reference")
    parser.add_argument("--steps", type=int, default=35, help="Sampling steps (default: 35)")
    parser.add_argument("--cfg", type=float, default=2.0, help="CFG scale (default: 2.0)")
    parser.add_argument("--seed", type=int, help="Base seed (incremented per request)")
    parser.add_argument(
        "--concurrency", type=int, default=3, help="Max concurrent requests (default: 3)"
    )
    parser.add_argument(
        "--output-dir", default="benchmark_results", help="Output directory (default: benchmark_results)"
    )
    parser.add_argument(
        "--timeout", type=int, default=600, help="Per-job timeout in seconds (default: 600)"
    )

    args = parser.parse_args()
    api_key = get_api_key()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    payloads = build_payloads(args)

    print(f"Benchmark: {len(payloads)} requests")
    print(f"  modes:       {args.modes}")
    print(f"  resolutions: {', '.join(args.resolutions)}")
    print(f"  concurrency: {args.concurrency}")
    print(f"  output:      {output_dir}")
    print()

    session = requests.Session()
    results = []
    t_start = time.time()

    # --- First request: sequential to capture cold start ---
    print(">>> Request 1 (cold start — sequential)")
    entry = run_single(
        session, api_key, payloads[0], 0, output_dir, timeout=args.timeout
    )
    results.append(entry)
    cold_start_time = entry["total_seconds"]
    status = entry.get("status", "error")
    gen = entry.get("generation_seconds")
    gen_str = f", gen={gen:.1f}s" if isinstance(gen, (int, float)) else ""
    print(
        f"  [1/{len(payloads)}] {status} | {entry['mode']} {entry['resolution']} "
        f"| total={cold_start_time:.1f}s{gen_str} (COLD START)\n"
    )

    # --- Remaining requests: concurrent ---
    if len(payloads) > 1:
        print(f">>> Requests 2-{len(payloads)} (warm — concurrency={args.concurrency})")
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = {}
            for i, payload in enumerate(payloads[1:], start=1):
                f = pool.submit(
                    run_single, session, api_key, payload, i, output_dir, timeout=args.timeout
                )
                futures[f] = i

            for f in as_completed(futures):
                entry = f.result()
                results.append(entry)
                idx = entry["index"]
                status = entry.get("status", "error")
                secs = entry.get("total_seconds", 0)
                gen = entry.get("generation_seconds")
                gen_str = f", gen={gen:.1f}s" if isinstance(gen, (int, float)) else ""
                print(
                    f"  [{idx+1}/{len(payloads)}] {status} | {entry['mode']} "
                    f"{entry['resolution']} | total={secs:.1f}s{gen_str}"
                )

    total_time = time.time() - t_start
    results.sort(key=lambda r: r["index"])

    # --- Summary ---
    successes = [r for r in results if r.get("status") == "success"]
    failures = [r for r in results if r.get("status") != "success"]
    # Warm results exclude the first (cold start) request
    warm_results = [r for r in results[1:] if r.get("status") == "success"]
    gen_times = [r["generation_seconds"] for r in successes if r.get("generation_seconds")]
    warm_gen = [r["generation_seconds"] for r in warm_results if r.get("generation_seconds")]
    warm_total = [r["total_seconds"] for r in warm_results]

    print(f"\n{'='*70}")
    print(f"BENCHMARK RESULTS")
    print(f"{'='*70}")
    print(f"Total requests:    {len(results)}")
    print(f"Successes:         {len(successes)}")
    print(f"Failures:          {len(failures)}")
    print(f"Wall time:         {total_time:.1f}s")
    print(f"Cold start total:  {cold_start_time:.1f}s")

    if warm_gen:
        print(f"\nWarm generation time (server-side, excludes cold start):")
        print(f"  avg: {sum(warm_gen)/len(warm_gen):.1f}s")
        print(f"  min: {min(warm_gen):.1f}s")
        print(f"  max: {max(warm_gen):.1f}s")

    if warm_total:
        print(f"\nWarm total time (submit → result, excludes cold start):")
        print(f"  avg: {sum(warm_total)/len(warm_total):.1f}s")
        print(f"  min: {min(warm_total):.1f}s")
        print(f"  max: {max(warm_total):.1f}s")

    # Per resolution/mode breakdown
    print_breakdown(results)

    if failures:
        print(f"\nFailures:")
        for r in failures:
            print(f"  [{r['index']}] {r.get('detail', r.get('error', 'unknown'))}")

    # Save report
    report = {
        "timestamp": timestamp,
        "config": {
            "count": args.count,
            "modes": args.modes,
            "resolutions": args.resolutions,
            "steps": args.steps,
            "cfg": args.cfg,
            "concurrency": args.concurrency,
            "face_url": args.face_url,
            "seed": args.seed,
        },
        "summary": {
            "total": len(results),
            "successes": len(successes),
            "failures": len(failures),
            "wall_time_seconds": round(total_time, 2),
            "cold_start_seconds": cold_start_time,
            "warm_avg_generation_seconds": (
                round(sum(warm_gen) / len(warm_gen), 2) if warm_gen else None
            ),
            "warm_avg_total_seconds": (
                round(sum(warm_total) / len(warm_total), 2) if warm_total else None
            ),
        },
        "results": results,
    }
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved: {report_path}")
    print(f"Images saved: {output_dir}")


if __name__ == "__main__":
    main()
