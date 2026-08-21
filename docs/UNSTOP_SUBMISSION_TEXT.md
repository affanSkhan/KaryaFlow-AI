# Unstop Round 2 Submission Copy

## Project title

KaryaFlow AI - Evidence-First Procurement Verification

## One-line description

KaryaFlow AI turns a Purchase Order, Invoice, and Delivery Challan into a verified three-way match, evidence-backed exception explanation, recommended action, human approval, and audit trail.

## Problem statement

Procurement teams repeatedly compare purchase orders, invoices, and delivery challans before transactions can move downstream. The process is repetitive, exception-prone, and difficult to audit when decisions are made from document text alone.

## Proposed solution

KaryaFlow AI provides an end-to-end procurement verification workflow. It extracts structured fields from the three source documents, performs deterministic reconciliation for critical quantities and prices, links results back to source evidence, recommends a next action, and requires explicit human approval before the business action is considered complete.

## Key features

- Multi-document PO / Invoice / Delivery Challan workflow
- Structured procurement extraction
- Deterministic three-way reconciliation
- Field-level source evidence and confidence
- Quantity / reference / price exception detection
- Ask Vendor / Approve / Escalate workflow
- Human approval gate
- Audit timeline
- Optional grounded Gemini drafting
- Responsive enterprise-style UI

## Technology stack

Python, FastAPI, SQLite, HTML/CSS/JavaScript, deterministic reconciliation rules, optional Gemini API, Docker, Render.

## Innovation / uniqueness

KaryaFlow is designed around a trust boundary: AI extracts and drafts, while deterministic rules own critical comparisons and humans own business approval. Every important exception can be inspected against source evidence, and every approval is recorded.

## Expected impact

KaryaFlow aims to reduce repetitive manual cross-checking, surface procurement exceptions earlier, make operational decisions easier to explain, and create a reusable pattern for evidence-backed workflow automation.

## Demo scenario

ABC Manufacturing / PO-1042 / Steel Bolt M10:
- PO: 100 units
- Invoice: 120 units
- Delivery: 100 units
- Recommended action: Ask Vendor

## Links

GitHub: https://github.com/affanSkhan/KaryaFlow-AI
Live demo: https://karyaflow-ai.onrender.com
Demo video: [PASTE FINAL PUBLIC VIDEO LINK]
