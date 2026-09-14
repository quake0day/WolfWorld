# Validation record

## English public edition — 2026-09-14

Validated on macOS with Node.js 23.10.0, pnpm 11.19.0, Python 3.14.4, NumPy 2.5.3, Pillow 12.3.0, and FFmpeg/FFprobe 7.1.1. The local FFmpeg installation required its existing compatible libvpx library path; no GPU was available. CI separately targets Node 24 and Python 3.11 on Linux.

| Check | Result | Evidence and boundary |
| --- | --- | --- |
| API integration suite | 9 passed | Actual SQLite migration and in-memory R2 adapter; remote inference mocked |
| Python worker suite | 6 passed | Real FFmpeg preprocessing and local authenticated HTTP service |
| TypeScript | Passed | `tsc --noEmit` |
| Production build | Passed | Client, SSR, RSC and Cloudflare Worker bundles built |
| New local D1 migration | Passed | Six SQL statements applied to a new local database |
| Worker download | Passed | Nine ZIP entries match the explicit source manifest byte for byte |
| Local documentation links | Passed | Markdown file targets and heading fragments checked |
| English text scan | Passed | No Chinese text remains in app, API or worker source |
| Browser sample smoke test | Passed | Local sign-in, visible butterfly, 177,132 original Gaussians, grid toggle, orientation/reset controls and GPU dialog |
| WebMCP read tool | Passed | Registered `list_world_scenes`; returned the empty local scene list |
| README banner | Visually checked | Original SVG rendered and inspected; conceptual illustration |

### Browser fix found during release checks

With Spark 2.1, loading only LoD splats left the base splat collection empty. The initial CPU bounding-box query and count therefore produced empty geometry and a camera too close to the scene. The viewer now retains the base splats (`nonLod: true`) alongside LoD, uses the base count, and rejects an empty bounding box. The sample now frames correctly and reports 177,132 original Gaussians.

The tradeoff is additional browser memory for the base representation. The count is source scene size, not the number of currently visible LoD splats. Large-scene memory benchmarking remains pending.

### Warnings and existing debt

- ESLint reports **27 errors and 3 warnings** in the imported application, mainly explicit `any` types, plus React hook and link/style findings. Lint is not clean and is not presented as a passing CI gate. Do not disable rules to hide this debt.
- Build reports a JavaScript chunk-size warning and limited static classification of dynamic routes. These do not prevent the Worker build.
- The browser logs a `THREE.Clock` deprecation warning. No rendering error was observed during the sample smoke test.
- Python 3.14 emits resource warnings for HTTP error responses in test code; all six tests pass.

## What the tests cover

The API suite checks identity/ownership, invalid uploads/settings, multipart integrity and idempotency, token omission, honest queued state without a GPU, mocked remote transfer/artifact persistence, transient failure, synchronization leases, cancellation/retry, and bounded R2 range reads.

The worker suite checks adapter command construction, basic Gaussian header validation, actual multi-video frame extraction, corrupt video rejection, duplicate/stationary input rejection, authenticated uploads and cancellation, SQLite persistence, and interrupted-job recovery.

## Still unverified

- WorldMirror CUDA inference, checkpoint compatibility at runtime, actual reconstruction fidelity and peak GPU memory.
- GPU Docker image build and deployment on real NVIDIA hardware.
- Full phone-video-to-model-to-browser end-to-end acceptance.
- Cross-browser/mobile interaction coverage, large artifact performance, real touch devices and multi-user load.
- Generative completion, collision meshes, alternate backends and long-sequence loop closure, which are not implemented.

A passing mocked artifact test does not establish that a physical scene was reconstructed. Use [GPU_ACCEPTANCE.md](GPU_ACCEPTANCE.md) to record a real capture-to-viewer result.

## Reproduce

```bash
pnpm install --frozen-lockfile
pnpm test
pnpm typecheck
pnpm build
python -m pip install -r worker/requirements.txt
python -m unittest discover -s worker -p 'test_*.py' -v
python scripts/package-worker.py --check
python scripts/check-docs.py
```

Install FFmpeg/FFprobe independently and ensure both execute successfully on `PATH`. GitHub Actions installs them on Linux; it does not download model weights or run GPU inference. The Actions badge links to actual run status rather than a static success claim.

## Original development record — 2026-09-10

The imported release recorded 9 API and 6 CPU worker tests, TypeScript and production build success. It explicitly did not perform GPU inference, Docker build or browser interaction testing. The current browser smoke results above are new checks for the English public edition.
