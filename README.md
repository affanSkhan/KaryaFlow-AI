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
- Optional Gemini-powered action drafting
- Demo-ready sample documents

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000.

For AI-assisted extraction/action drafting, set `GEMINI_API_KEY`. Without it, the deterministic demo pipeline still runs end-to-end using the included sample documents.

## API
- `GET /api/health`
- `POST /api/cases`
- `POST /api/cases/{case_id}/documents`
- `POST /api/cases/{case_id}/analyze`
- `GET /api/cases/{case_id}`
- `POST /api/cases/{case_id}/actions`
- `GET /api/cases/{case_id}/audit`

## Architecture

```text
Browser UI
   |
FastAPI
   |
   +-- Document Store / SQLite
   +-- Parser + Extractor
   +-- Reconciliation Engine (deterministic)
   +-- Evidence Engine
   +-- Action Generator (Gemini optional)
   +-- Audit Log
```

Critical financial comparisons are calculated in deterministic Python. The model is used for extraction, explanation, and drafting rather than for inventing reconciliation results.

## Demo flow
1. Create a case or use the seeded demo case.
2. Upload PO, Invoice, and Delivery Challan.
3. Click **Analyze**.
4. Review the match summary and highlighted exception.
5. Open evidence for the mismatched field.
6. Choose **Ask Vendor** or **Escalate**.
7. Approve the action and inspect the audit timeline.

## License
MIT
