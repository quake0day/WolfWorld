# Security

WolfWorld is an experimental MVP. The application separates records and objects by a trusted authenticated user ID, and the GPU service authenticates requests with a bearer token.

## Deployment boundaries

- Hosted identity headers must come from a trusted authentication gateway. A standalone deployment must strip client-supplied `oai-authenticated-user-*` headers, authenticate the request, inject its own identity and prevent direct origin bypass.
- The loopback-only development sign-in is for local work. It is not a production authentication system.
- GPU tokens are stored server-side in the application's D1 settings table and omitted from config responses. They are not application-level encrypted; protect database access and backups accordingly.
- Use HTTPS between the app and GPU worker. The included Compose configuration binds its HTTP port to `127.0.0.1` for reverse-proxy access.
- The worker URL validator rejects obvious local addresses and redirects; it is not a complete DNS/private-network isolation mechanism. Harden outbound network policy for an untrusted multi-user service.
- Video parsers, model dependencies, uploads and generated artifacts consume resources. Configure storage retention, request limits and infrastructure isolation for your deployment.

Do not treat this repository as a completed security audit. Publishing the source does not expose or transfer the original hosted site's data.

## Reporting a vulnerability

Use GitHub's **Security → Report a vulnerability** when available. If private reporting is unavailable, open an issue containing only a request for a private reporting channel; do not include credentials, private videos, exploit payloads or production data. The maintainer will arrange a private channel. No response-time guarantee is currently offered.
