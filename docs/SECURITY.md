# Security notes

KaryaFlow is designed around a conservative automation boundary.

- Uploaded files are restricted to PDF/TXT in the hackathon MVP and capped at 10 MB.
- Filenames are sanitized to their basename before persistence.
- Critical calculations are deterministic and independently verifiable.
- Model output is advisory and cannot directly execute a procurement action.
- Human approval is required before an action is marked approved.
- Gemini requests, when configured, contain verified facts and explicit instructions not to invent facts.
- The Gemini API key is read from `GEMINI_API_KEY` and must never be committed.
- SQLite uses foreign-key constraints and WAL mode for local reliability.

## Production hardening roadmap

For a real deployment, add SSO/OIDC, tenant-level authorization, encrypted object storage, virus scanning, immutable audit storage, secret management, request rate limits, structured observability, database migrations, and a policy engine for organization-specific approval thresholds.
