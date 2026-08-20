# KaryaFlow AI Architecture

## Product flow

```text
PO / Invoice / Delivery Challan
            |
            v
      Upload + validation
            |
            v
      Document classifier
            |
            v
     Structured extraction
            |
            v
   Normalized procurement data
            |
            v
   Deterministic 3-way match
            |
      +-----+------+
      |            |
    MATCH       EXCEPTION
      |            |
   Approve      Explain
                   |
                   v
          Recommended action
                   |
                   v
            Human approval
                   |
                   v
              Audit log
```

## Design principles

1. **Deterministic critical logic.** Quantities and prices are compared by Python rules. The model is never the authority for arithmetic.
2. **Evidence-first output.** Every critical field stores source filename, page, snippet, and confidence metadata.
3. **Human-in-the-loop.** KaryaFlow prepares an action; a person explicitly approves it.
4. **Graceful degradation.** The core workflow works without an external model. Gemini adds grounded communication drafting when configured.
5. **Small-surface MVP.** The product focuses on one procurement workflow that can be demonstrated end-to-end.

## Security boundaries

- Maximum upload size: 10 MB per file.
- Accepted types: PDF/TXT in the MVP.
- Filenames are reduced to their basename before storage.
- Business actions require explicit approval.
- External model calls receive verified facts rather than arbitrary tool instructions.
- Secrets are environment variables, never committed.
