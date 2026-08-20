# KaryaFlow AI

**From documents to decisions.**

KaryaFlow AI is an evidence-first procurement operations copilot for small and mid-sized businesses. It turns a Purchase Order, Invoice, and Delivery Challan into a verified three-way match, explains exceptions with source evidence, recommends the next action, and records the human decision in an audit trail.

## Round 2 scope
- Multi-document procurement workflow
- PO / Invoice / Delivery Challan extraction
- Deterministic three-way reconciliation
- Field-level evidence and confidence
- Exception explanation
- Approve / Ask Vendor / Escalate actions
- Human approval gate
- Audit timeline
- Grounded Gemini vendor-draft endpoint with deterministic fallback
- Demo-ready transaction data
- Docker + Render deployment configuration

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000.

For the optional grounded Gemini draft endpoint, set `GEMINI_API_KEY`. Without it, the main procurement workflow remains fully functional.

## API
- `GET /api/health`
- `GET /api/ai/status`
- `POST /api/ai/draft`
- `POST /api/cases`
- `POST /api/cases/{case_id}/documents`
- `POST /api/cases/{case_id}/analyze`
- `GET /api/cases/{case_id}`
- `POST /api/cases/{case_id}/actions`
- `POST /api/cases/{case_id}/actions/{action_id}/approve`
- `GET /api/cases/{case_id}/audit`

## Architecture

```text
Browser UI
   |
FastAPI
   |
   +-- Document Store / SQLite
   +-- Parser + Structured Extractor
   +-- Reconciliation Engine (deterministic)
   +-- Evidence Engine
   +-- Grounded Gemini Draft Service (optional)
   +-- Human Approval Gate
   +-- Audit Log
```

Critical financial comparisons are calculated in deterministic Python. Gemini is isolated to drafting/explanation work and receives verified facts rather than authority to change reconciliation results.

## Demo flow
1. Click **Launch demo**.
2. KaryaFlow generates a realistic PO, invoice, and delivery-challan transaction in-browser.
3. Verify the vendor, PO reference, quantity, and price checks.
4. Inspect the quantity exception: PO = 100, invoice = 120, delivery = 100.
5. Open **Evidence** to show the source snippet behind the mismatched field.
6. Review **Ask Vendor** recommendation.
7. Approve the generated action through the human approval gate.
8. Open **Audit trail** to show the complete decision history.

## Deployment

A `render.yaml` blueprint is included for a single-service deployment. The Dockerfile and `docker-compose.yml` support local/container deployment.

## License
MIT
