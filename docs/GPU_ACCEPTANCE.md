# GPU acceptance checklist

This is a reproducible validation plan for the WolfWorld worker and browser workflow. **All GPU and visual acceptance results below are pending.** CPU/API fixtures and the bundled sample scene do not establish that phone video reconstruction works on a particular GPU.

Use the [worker setup guide](../worker/README.md) to deploy. Perform the first run with one short video of a static room, then repeat with overlapping clips. Do not use synthetic test-pattern videos as evidence of geometric reconstruction quality.

## Record the environment

Copy this table into your test report and fill it with measurements:

| Field | Observed value |
| --- | --- |
| Test date and operator | Pending |
| WolfWorld commit | Pending |
| HY-World commit (`git rev-parse HEAD` in its checkout) | Pending; expected adapter revision: `df9988efb87bfc0f4947eb3889411cf957478b06` |
| OS, GPU model, GPU count, VRAM, NVIDIA driver | Pending |
| Native environment or Docker image ID | Pending |
| Python, PyTorch, CUDA, and extension versions | Pending |
| Browser version, device, operating system | Pending |
| Video IDs, durations, resolutions, codecs, file hashes | Pending |
| WorldMirror model/weight revision or local checkpoint identifier | Pending |
| Preset and selected keyframe count | Pending |
| Cold-start download time, model runtime, peak GPU memory | Pending |
| Gaussian count and artifact byte size | Pending |

Suggested environment evidence from the activated model environment:

```bash
nvidia-smi
python --version
python -m pip freeze
ffmpeg -version
ffprobe -version
python -c 'import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available())'
```

Capture `nvidia-smi` observations during inference if recording GPU memory; report the sampling interval and whether the result is a sampled observation or a framework-measured peak. Record model time separately from upload and first-run downloads. Do not turn one successful run into a general minimum-memory or performance claim.

## 1. Establish upstream model readiness

- [ ] Run an official WorldMirror reconstruction example in the environment that will run the worker.
- [ ] Confirm the model loads weights and finishes actual CUDA inference.
- [ ] Preserve the exact command, environment versions, model log, and resulting artifact size.
- [ ] Start the worker and call authenticated `/health`; confirm `service` is `wolfworld-worker` and `model_ready` is true.
- [ ] Record that `/health` alone does not load/execute the full model. Restart the worker after environment fixes because the health response is cached.

**Result:** Pending. **Evidence:** Pending.

## 2. Reconstruct one short phone video

Record approximately 10–30 seconds of a static, textured room in stable lighting. Move the phone slowly through space with overlapping views; include stable landmarks such as corners, furniture edges, and doorways. Keep people and pets out of the scene. Save the original video.

- [ ] Upload the video through WolfWorld and select Quick Preview (24-frame budget, target size 518).
- [ ] Keep the app open until transfer finishes and the worker begins processing.
- [ ] Record the job ID and follow its stages through completion or failure.
- [ ] Inspect `<data>/<job-id>/frames.json` for selected frames and warnings.
- [ ] Inspect `model.log` for evidence of actual model execution and any runtime errors.
- [ ] Verify `output/gaussians.ply` exists, is nonempty, and is at most 256 MiB.
- [ ] Download the artifact through the app and load it in the browser viewer.
- [ ] Compare captured landmarks against the source footage from several viewpoints. Record missing geometry, floaters, duplicated surfaces, or alignment failures.
- [ ] Check mouse/touch navigation and reset behavior on the target browsers/devices.

Job completion and valid header fields establish delivery of an artifact, not geometric accuracy. This qualitative room check does not establish metric scale. Quantitative accuracy requires reference measurements or ground-truth geometry, a defined alignment method, and an explicit error metric.

**Result:** Pending. **Evidence:** Pending.

## 3. Reconstruct two overlapping clips jointly

Use two clips of the same room with shared landmarks and camera translation. Record which source regions overlap.

- [ ] Create a new preview job with both videos.
- [ ] Confirm `frames.json` contains selected frames from both input IDs.
- [ ] Confirm one model invocation consumes the combined frame directory.
- [ ] Compare shared landmarks and room surfaces for continuity, orientation, relative scale, and duplicate geometry.
- [ ] Record whether a recognizable, navigable common scene was produced; do not classify a visually inconsistent result as a quality pass just because the job completed.

This checks the current joint-inference workflow. It does not validate arbitrary disjoint-video fusion, loop closure, or a separate global bundle-adjustment pipeline.

**Result:** Pending. **Evidence:** Pending.

## 4. Exercise lifecycle and recovery

- [ ] After GPU inference starts, close the browser tab. Verify worker execution continues. Reopen the app and confirm it synchronizes the status and retrieves the result.
- [ ] Separately close the app during transfer. Reopen and confirm synchronization resumes; browser-driven transfer is not expected to advance while no client is driving it.
- [ ] Cancel a queued job and verify it does not begin inference.
- [ ] Cancel a running test job and verify it reaches `cancelled`; allow an active FFmpeg operation to finish before checking preprocessing cancellation.
- [ ] Retry a cancelled/failed job and confirm a new job ID is used.
- [ ] During a disposable test job, restart the worker. Confirm previously queued/running jobs become `failed` and retry works.
- [ ] Confirm an invalid token returns `401` without executing a job.
- [ ] Verify a truncated or incorrectly sized upload part is rejected and resending a valid part succeeds.
- [ ] If an OOM or model failure occurs, retain the model log and confirm an actionable error reaches the app; record an unexercised OOM path as pending rather than forcing resource exhaustion on a shared GPU.

**Result:** Pending. **Evidence:** Pending.

## 5. Decide acceptance for the intended use

| Dimension | Required evidence | Result |
| --- | --- | --- |
| Installation | Successful environment/image setup and upstream CUDA example | Pending |
| Inference | Worker model log and artifact from the submitted phone video | Pending |
| Browser delivery | Downloaded artifact renders and navigation works on target devices | Pending |
| Multi-video quality | Shared observed landmarks form a usable common scene | Pending |
| Recovery | Recorded cancellation, retry, restart, and upload recovery behavior | Pending |
| Resource fit | Observed runtime, GPU memory, disk use, and artifact size for the chosen preset | Pending |

Include screenshots or a short screen recording of your actual reconstructed scene, the relevant job report, and redacted logs. Remove access tokens, private hostnames, and personal video content before sharing evidence publicly. Keep failures and remaining unknowns in the report alongside passes.
