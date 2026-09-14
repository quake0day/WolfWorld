# WolfWorld GPU Worker

**Turn overlapping phone videos into a Gaussian scene with WorldMirror 2.0.**

This service receives videos from the WolfWorld web application, extracts keyframes with FFmpeg, runs the real WorldMirror reconstruction pipeline, and serves the resulting `gaussians.ply`. The model runs on your GPU server; the web application stores uploads, coordinates jobs, and displays the scene.

> **Validation status:** CPU preprocessing and HTTP service tests exist and run without model weights. NVIDIA inference, GPU memory requirements, reconstruction quality, and the supplied Docker image still require validation on GPU hardware. A green health check is a dependency check, not an inference result.

## Requirements

| Component | Requirement |
| --- | --- |
| GPU host | Linux with an NVIDIA GPU and a compatible driver; the supplied image uses PyTorch 2.7.1 with CUDA 12.8 |
| Model environment | A working [HY-World 2.0 World Reconstruction installation](https://github.com/Tencent-Hunyuan/HY-World-2.0), including its Python, CUDA, and compiled-extension dependencies |
| Model revision | Adapter and Dockerfile target `df9988efb87bfc0f4947eb3889411cf957478b06` |
| Video tools | `ffmpeg` and `ffprobe` available on `PATH` |
| Network | Access to upstream dependencies and model weights for installation/first inference; an HTTPS hostname reachable by the web application's backend |
| Storage | Space for source videos, candidate images, selected frames, model weights, logs, and outputs |
| Access token | A private random token of at least 24 characters; the web app accepts up to 256 characters |

GPU capacity depends on frame count, resolution, and the model implementation. Start with the 24-frame preview preset and measure actual peak memory on your hardware. This repository does not yet establish a minimum VRAM requirement.

The worker uses World Reconstruction only. HY-Pano, the world-generation pipeline, and an OpenAI API key are not required by this adapter. Upstream code and model weights retain their own licenses and terms; see [third-party notices](https://github.com/quake0day/WolfWorld/blob/main/docs/THIRD_PARTY.md).

## Option A: use an existing WorldMirror environment

1. Install and validate WorldMirror using the upstream project's World Reconstruction instructions. Use the revision listed above when checking compatibility with this adapter. Run an upstream reconstruction example successfully before starting the service.
2. Activate that same Python environment, then run these commands from this `worker/` directory:

```bash
python -m pip install -r requirements.txt
export WORLDMIRROR_REPO=/absolute/path/to/HY-World-2.0
export WOLFWORLD_DATA=/absolute/path/to/wolfworld-data
export WOLFWORLD_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python server.py --host 127.0.0.1 --port 8788
```

The local `requirements.txt` installs only the worker's NumPy and Pillow dependencies. It does **not** install WorldMirror, PyTorch, CUDA extensions, or FFmpeg.

Save the generated token in your secret manager and enter the same token in WolfWorld's GPU connection dialog. Keep the service running with your preferred process supervisor. Set the variables in that supervisor's environment when deploying persistently.

Native Python startup reads environment variables directly; it does **not** automatically load `.env`. `--data` and `--repo` override their corresponding environment variables. The CLI defaults to `0.0.0.0:8788`; the command above binds to loopback for use behind a reverse proxy.

### Environment reference

| Variable | Meaning | Default if unset |
| --- | --- | --- |
| `WOLFWORLD_TOKEN` | Shared bearer token required for every worker endpoint | None; startup fails without at least 24 characters |
| `WORLDMIRROR_REPO` | Absolute path to the HY-World 2.0 checkout | `/opt/HY-World-2.0` |
| `WOLFWORLD_DATA` | Persistent worker job directory | `./data`, relative to the startup directory |

## Option B: Docker Compose

Install Docker with GPU support and NVIDIA Container Toolkit on the GPU host first. From this directory:

```bash
cp .env.example .env
python -c 'import secrets; print(secrets.token_urlsafe(32))'
# Replace WOLFWORLD_TOKEN in .env with the generated value.
# Keep WORLDMIRROR_REPO=/opt/HY-World-2.0 and WOLFWORLD_DATA=/data.
docker compose build
docker compose up -d
docker compose logs -f gpu
```

The supplied Dockerfile pins the upstream source revision, `cupy-cuda12x==13.6.0`, `gsplat==1.5.3`, and `flash-attn==2.8.3`. Other dependencies follow the checked-out upstream requirements. These pins describe the build configuration; the image has not yet been built or exercised on a GPU in this project's validation record.

Compose binds port 8788 to host loopback, stores job data in `./data`, and persists Hugging Face downloads in the `model-cache` volume. It requests all available GPUs, but this worker still runs only **one job at a time per service process**; it does not implement a multi-GPU scheduler.

Use `docker compose down` to stop the deployment. Keep the data directory and model-cache volume if you want to retain jobs and downloaded weights.

## Connect the web application

1. Publish the worker through an HTTPS reverse proxy or tunnel, forwarding `/health` and `/jobs/*` to `http://127.0.0.1:8788`.
2. Preserve the `Authorization` and `Content-Length` headers. Allow requests of at least 8 MiB and downloads up to 256 MiB. Allow at least 180 seconds for uploads and 120 seconds for the first dependency health check. Avoid buffering entire source videos at the proxy.
3. In WolfWorld, open the GPU connection dialog and enter the HTTPS base URL and the shared token. The web app requires a hostname: raw IP addresses, localhost, `.local`, and `.internal` addresses are rejected.
4. Save and check the connection. Upload overlapping videos of one static scene and begin with Quick Preview.

The browser submits the token when saving the connection; subsequent worker requests use the token stored on the web backend. The configuration-read API does not return the saved token. The GPU worker does not need to authenticate through the website or fetch protected browser URLs: the backend forwards video bytes to it.

**Keep the web app open until video transfer finishes and the GPU job starts.** Upload/dispatch progress is driven by the browser's synchronization requests. Once the worker has queued or started the model job, computation continues independently of the browser. Reopening the app resumes synchronization and retrieves the completed artifact.

### Health check

With the worker running and `WOLFWORLD_TOKEN` available in the calling shell:

```bash
curl --fail --silent --show-error \
  -H "Authorization: Bearer ${WOLFWORLD_TOKEN}" \
  http://127.0.0.1:8788/health
```

| Response field | What it establishes |
| --- | --- |
| `service` | Must equal `wolfworld-worker` |
| `gpu_available` | `nvidia-smi` completed successfully |
| `model_installed` | The configured checkout contains `hyworld2/worldrecon/pipeline.py` |
| `ffmpeg` | Both `ffmpeg` and `ffprobe` were found on `PATH` |
| `model_ready` | The preceding checks passed, the model pipeline imported, and `torch.cuda.is_available()` was true |

The health result is cached for the lifetime of the worker process. Restart after repairing dependencies or changing GPU availability. Health does not download/load all weights, execute the model, establish sufficient VRAM, or assess output quality. A first inference may still fail.

## Reconstruction behavior and limits

| Setting | Current implementation |
| --- | --- |
| Video inputs | 1–12 files per job; `.mp4`, `.mov`, `.m4v`, or `.webm` |
| File/duration limit | Up to 2 GiB per video; duration greater than zero and at most 30 minutes; actual codec support depends on FFmpeg |
| Transfer | 8 MiB parts, with a smaller final part; exact lengths checked; failed parts may be resent |
| Quick Preview | At most 24 selected frames; model target size 518 |
| Balanced | At most 48 selected frames; model target size 700 |
| Detail | At most 96 selected frames; model target size 952 |
| Queue | At most five jobs in `uploading`, `queued`, or `running` states; one execution slot per worker process |
| Model execution | BF16 enabled; upstream Gaussian compression requested with `--compress_gs_max_points 1000000` |
| Runtime limits | 30 seconds for probing each video; 10 minutes for each FFmpeg extraction; 2 hours for the model process |
| Artifact | `output/gaussians.ply`, nonempty and no larger than 256 MiB |

Frame budgets are divided approximately equally between the input videos. The preprocessor samples candidates across each clip, with a sampling-rate cap of 5 fps and image width capped at 1280 pixels. It filters similar frames using grayscale image difference, estimates sharpness with Laplacian variance, and selects frames with temporal coverage. These are image heuristics, not geometric overlap or parallax verification. A low-sharpness clip may produce a warning and retain frames when too few sharp candidates are available.

All selected frames are passed to one WorldMirror reconstruction. Overlapping views are essential. The current adapter does not perform a separate global SfM/bundle-adjustment verification, long-sequence loop closure, dynamic-object masking, or generative completion of unseen regions. It does not optimize the result in a separate gsplat training stage.

The worker checks for selected Gaussian header properties and a positive vertex count before exposing an artifact. This catches ordinary point-cloud PLY files, but it is not a full validation of the PLY payload or reconstruction accuracy. The one-million-Gaussian setting is passed to the upstream pipeline rather than independently enforced by this service.

Progress values represent stages, not a continuous model completion estimate. Cancellation is checked between clips and during model-process polling. A running FFmpeg subprocess may finish before cancellation takes effect.

### Persistent data

```text
WOLFWORLD_DATA/
├── jobs.sqlite                 # Job state
└── <job-id>/
    ├── inputs/                 # Uploaded videos and temporary parts
    ├── frames/                 # Selected JPEG keyframes
    ├── frames.json             # Frame selection and preprocessing warnings
    ├── model.log               # Model subprocess stdout/stderr
    └── output/
        └── gaussians.ply       # Completed scene
```

The completed job report also records the Gaussian count and output byte size. Temporary candidate directories or upload files can remain after an interrupted operation. There is no automatic retention policy or deletion API; plan storage cleanup deliberately and keep SQLite metadata consistent with retained artifacts.

On startup, jobs previously marked `running` or `queued` become `failed`, because GPU computation cannot resume from the recorded job state. Uploading jobs retain their state. Retrying a failed/cancelled reconstruction requires a new job ID; the web app's Retry action creates one.

## HTTP API

Every endpoint requires `Authorization: Bearer <WOLFWORLD_TOKEN>`. Identifiers use lowercase UUID strings. The worker's JSON request bodies must be nonempty and smaller than 32 KiB.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Cached GPU and dependency diagnostics |
| `POST` | `/jobs` | Create an idempotent job from `id`, `frames`, `resolution`, and `inputs` |
| `PUT` | `/jobs/:id/inputs/:inputId/parts/:partNumber` | Upload a 1-based part with exact `Content-Length` |
| `POST` | `/jobs/:id/inputs/:inputId/complete` | Validate and assemble all parts for a video |
| `PUT` | `/jobs/:id/inputs/:inputId` | Alternative whole-file upload with exact `Content-Length` |
| `POST` | `/jobs/:id/start` | Queue a job after every source video is received |
| `GET` | `/jobs/:id` | Read status, stage, progress, errors, and the completed report |
| `POST` | `/jobs/:id/cancel` | Cancel an unfinished job |
| `GET` | `/jobs/:id/artifact` | Download a completed Gaussian PLY |

Example creation body:

```json
{
  "id": "8e9b15a5-4873-4d9a-8c63-bf58f32083ed",
  "frames": 24,
  "resolution": 518,
  "inputs": [
    {
      "id": "66fbe54d-a019-4b50-9380-d8067a2b83ef",
      "name": "room.mp4",
      "size": 1234567
    }
  ]
}
```

Use a freshly generated job/video UUID and the actual video size. Repeating `/jobs` with the same ID is accepted only when inputs and model settings match. The API accepts any combination of the three supported frame budgets and three resolutions; the web UI pairs them into the presets above.

## CPU tests

From `worker/`, with FFmpeg/FFprobe installed:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s . -p 'test_*.py' -v
```

From the repository root, use `python -m unittest discover -s worker -p 'test_*.py' -v` instead. The tests exercise real FFmpeg preprocessing using generated moving test patterns, reject corrupt/static footage, check Gaussian header validation and adapter arguments, and exercise authenticated uploads, cancellation, persistence, and restart handling. They do not execute WorldMirror inference. See the [validation record](https://github.com/quake0day/WolfWorld/blob/main/docs/TESTING.md) for the recorded results.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Worker exits before listening | Ensure `WOLFWORLD_TOKEN` is present and at least 24 characters long; native startup does not load `.env` |
| `401` from the worker | The bearer token must match exactly; verify the proxy forwards `Authorization` |
| Connection rejected by the app | Use a reachable HTTPS hostname and the correct base path; verify the backend can reach it |
| `model_ready: false` | Check `nvidia-smi`, the repo path, FFmpeg/FFprobe, and pipeline imports in the same Python environment; restart after fixes |
| Health succeeds, first job fails | Inspect `<data>/<job-id>/model.log`; health does not verify downloaded weights, VRAM capacity, or runtime CUDA kernels |
| GPU out of memory | Use Quick Preview; measure memory with a small capture first. Fewer clips alone does not reduce the preset's total frame budget |
| Upload stalls or returns length errors | Check the proxy body limit, upload timeout, forwarded `Content-Length`, and storage capacity; keep the app open through dispatch |
| Too few distinct frames | Record with slow camera movement and visible static details; a stationary/duplicate clip is rejected by preprocessing |
| Misaligned, incomplete, or distorted scene | Increase overlap, add camera translation, reduce motion blur and moving objects, and inspect the source views; quality is not guaranteed by job completion |
| Queue remains full | Up to five uploading/queued/running jobs count toward the limit; cancel abandoned jobs |
| Job fails after service restart | This is intentional interrupted-job handling; retry to create a new job |
| PLY rejected or artifact too large | Inspect the model output/log. The app requires a Gaussian PLY up to 256 MiB, not a plain point cloud |

For a reproducible first GPU run, use the [GPU acceptance checklist](https://github.com/quake0day/WolfWorld/blob/main/docs/GPU_ACCEPTANCE.md). Record observed outcomes and attach evidence before claiming inference or reconstruction quality is validated.
