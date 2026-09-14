# Contributing to WolfWorld

WolfWorld is an experimental integration project. Useful contributions include reproducible GPU results, reliable synchronization, capture diagnostics, browser compatibility, and clearer documentation.

## Get started

1. Follow the [web setup](README.md#quick-start) and [worker setup](worker/README.md).
2. Create a branch for one focused change.
3. Keep model behavior, API contracts and presentation changes clear in your pull request.
4. Run the existing checks appropriate to your change.

```bash
pnpm test
pnpm typecheck
pnpm build
python -m unittest discover -s worker -p 'test_*.py' -v
```

Run `pnpm lint` to inspect lint findings; the initial imported application has existing lint debt documented in [TESTING.md](docs/TESTING.md). Avoid adding new findings, and do not disable rules globally to hide failures.

## Pull requests

Describe the problem, the resulting behavior, and the checks you ran. Use concrete before/after examples for behavior changes. Keep English UI strings and docs consistent. Preserve third-party notices and use the pinned pnpm version and lockfile.

For a model adapter, report the upstream revision, hardware, environment, capture characteristics and actual output. A mock response or successful health check is not a model evaluation. Do not upload private videos, credentials, model weights, generated caches or production database copies.

Changes in `worker/` should rebuild `public/downloads/wolfworld-worker.zip` with `python scripts/package-worker.py`. This deterministic packager includes only worker source, setup files, documentation, tests and the application license. Verify it with `python scripts/package-worker.py --check`.

## Bug reports and research results

Include your operating system, Node/Python versions, commit, reproduction steps and a redacted error. For visual problems, report browser/device, format and scene size. Share footage only when you have the rights and permission to do so. Record CPU tests separately from GPU inference and rendering-quality measurements.

Use [GPU_ACCEPTANCE.md](docs/GPU_ACCEPTANCE.md) for end-to-end results. Planned backend integrations belong in an issue before a large implementation.

## Security reports

See [SECURITY.md](SECURITY.md). Keep tokens and private captures out of public issues.
