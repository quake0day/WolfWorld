# API reference

The browser calls same-origin `/api/*` endpoints. These require an identity supplied by the trusted authentication layer; a GitHub token is unrelated. Do not send the GPU token in browser API requests except when saving it through `/api/config`.

## Web API

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/config` | Worker URL and configured flags; token omitted |
| PUT | `/api/config` | Save `{url, token}`; an omitted/empty token retains the previous one |
| POST | `/api/config/check` | Check the saved worker's authenticated health endpoint |
| GET | `/api/media` | List up to 100 completed uploads owned by this user |
| POST | `/api/uploads` | Create `{name, size, kind}`; return ID and chunk size |
| PUT | `/api/uploads/:id/parts/:n` | Upload a numbered binary part with exact `Content-Length` |
| POST | `/api/uploads/:id/complete` | Validate all parts and finalize the upload; idempotent |
| GET | `/api/uploads/:id/file` | Stream a completed owner-scoped upload |
| DELETE | `/api/uploads/:id` | Remove an unreferenced upload; job-linked sources are retained |
| GET | `/api/jobs` | List up to 100 owned jobs |
| POST | `/api/jobs` | Create `{name, media, preset}` |
| GET | `/api/jobs/:id` | Read one owned job |
| POST | `/api/jobs/:id/sync` | Advance input transfer or synchronize worker state and output |
| POST | `/api/jobs/:id/cancel` | Request cancellation |
| POST | `/api/jobs/:id/retry` | Create a new job from a failed/cancelled job's inputs |
| GET | `/api/jobs/:id/artifact` | Download completed `gaussians.ply` |

Job creation accepts a name of 1–160 characters, 1–12 distinct ready video IDs, and `preview`, `balanced`, or `detail` as the preset. A new-job request checks the owner's active-job count. Retries use a separate path; do not treat the five-job check as a comprehensive scheduler quota.

### Example browser calls

Run this only within your authenticated local or deployed workspace:

```javascript
const config = await fetch('/api/config').then(r => r.json());
// { url: 'https://gpu.example.com', configured: true, tokenConfigured: true }

const response = await fetch('/api/jobs', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'Studio walkthrough',
    media: ['REPLACE_WITH_UPLOADED_VIDEO_ID'],
    preset: 'preview'
  })
});
const job = await response.json();
```

Uploads are binary parts of 8 MiB except the final part. The browser's upload helper retries a failed part up to three attempts, then attempts to abort the failed upload. It does not restore a file selection after a page reload. Worker input transfer is tracked separately and resumes through job synchronization.

### Errors

Errors use `{ "error": "English message" }`. Common codes include 400 (invalid fields/parts), 401 (missing identity), 404 (missing or inaccessible resource), 409 (state conflict), 413 (size limit), 502 (upstream worker error), and 503 (storage or temporary operation failure). Ownership violations are generally returned as 404. A job can retain an error while still being recoverable; inspect `status` rather than treating every message as terminal failure.

## GPU service API

The separate worker does not use the web app's identity headers. Every endpoint requires:

```http
Authorization: Bearer <WOLFWORLD_TOKEN>
```

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/health` | GPU, FFmpeg and import prerequisites; not model inference |
| POST | `/jobs` | Idempotent setup with UUID, frames, resolution and input manifest |
| PUT | `/jobs/:id/inputs/:inputId/parts/:n` | Store a validated input chunk |
| POST | `/jobs/:id/inputs/:inputId/complete` | Assemble and check input length |
| POST | `/jobs/:id/start` | Queue processing after all inputs arrive |
| GET | `/jobs/:id` | Read current status, stage, error and report |
| POST | `/jobs/:id/cancel` | Cancel queued or running work |
| GET | `/jobs/:id/artifact` | Stream the completed Gaussian PLY |

The [worker guide](../worker/README.md#http-api) documents payloads, persistence and reverse-proxy requirements. Endpoints are for app-to-worker communication; browsers do not need direct access to the GPU service.
