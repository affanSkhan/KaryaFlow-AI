# KaryaFlow AI Architecture

KaryaFlow uses a layered procurement-verification architecture that keeps document intelligence, deterministic reconciliation, AI drafting, human approval, and auditability separate.

## System Architecture

```mermaid
flowchart LR
    U[Procurement User]

    subgraph UI[Web Application]
        APP[Verification Workspace]
        DOCS[Documents View]
        AUDIT[Audit Trail]
    end

    subgraph API[FastAPI Application]
        CASE[Case & Workflow API]
        INGEST[Document Ingestion]
        EXTRACT[Classifier + Structured Extraction]
        MATCH[Deterministic 3-Way Reconciliation]
        EVIDENCE[Evidence & Confidence Layer]
        ACTION[Recommendation + Human Approval]
        LOG[Audit Service]
    end

    subgraph DATA[Application Data]
        DB[(SQLite)]
        FILES[(Document Storage)]
    end

    subgraph AI[Optional AI Service]
        GEMINI[Gemini Grounded Drafting]
    end

    U --> APP
    APP --> CASE
    DOCS --> CASE
    AUDIT --> CASE

    CASE --> INGEST
    INGEST --> FILES
    INGEST --> EXTRACT
    EXTRACT --> DB
    EXTRACT --> MATCH
    MATCH --> EVIDENCE
    EVIDENCE --> ACTION
    ACTION --> LOG
    LOG --> DB
    ACTION -. verified facts only .-> GEMINI
    GEMINI -. drafted communication .-> ACTION

    MATCH -->|MATCH| ACTION
    MATCH -->|EXCEPTION| EVIDENCE
```

## End-to-End Product Flow

```mermaid
flowchart LR
    A[PO + Invoice + Delivery Challan] --> B[Upload & Validate]
    B --> C[Classify & Extract]
    C --> D[Normalize Procurement Data]
    D --> E[Deterministic 3-Way Match]
    E -->|Verified| F[Decision Ready]
    E -->|Exception| G[Explain with Evidence]
    G --> H[Recommend Action]
    H --> I[Human Approval]
    I --> J[Audit Timeline]
```

## Design Principles

1. **Deterministic critical logic.** Quantities, prices, and variance calculations are compared by explicit Python rules. The model is never the authority for arithmetic or reconciliation results.
2. **Evidence-first decisions.** Important findings stay linked to source filename, page, snippet, extracted value, and confidence metadata.
3. **Human-in-the-loop control.** KaryaFlow can recommend an action, but a person must explicitly approve it before it becomes an operational decision.
4. **Graceful AI dependency.** The core workflow works without an external model. Gemini is optional for grounded communication drafting.
5. **Focused product surface.** The application solves one procurement workflow end-to-end rather than acting as a generic document chatbot.

## Security Boundaries

- Maximum upload size: 10 MB per file.
- MVP accepts PDF/TXT documents.
- Uploaded filenames are reduced to their basename before storage.
- Business actions require explicit approval.
- External model calls receive verified facts rather than arbitrary tool instructions.
- Secrets are environment variables and are never committed.

## Deployment

The current deployment uses a single FastAPI web service on Render. The same application can be run locally or containerized using the included Docker configuration.
