from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "karyaflow.db"
UPLOAD_DIR = BASE_DIR / "uploads"
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="KaryaFlow AI", version="1.0.0", description="Evidence-first procurement operations copilot")

DOC_TYPES = {"purchase_order", "invoice", "delivery_challan"}
TYPE_LABELS = {"purchase_order": "Purchase Order", "invoice": "Invoice", "delivery_challan": "Delivery Challan"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            document_type TEXT NOT NULL,
            path TEXT NOT NULL,
            extracted_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(case_id) REFERENCES cases(id)
        );
        CREATE TABLE IF NOT EXISTS audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            event TEXT NOT NULL,
            detail TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(case_id) REFERENCES cases(id)
        );
        CREATE TABLE IF NOT EXISTS actions (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            approved_at TEXT,
            FOREIGN KEY(case_id) REFERENCES cases(id)
        );
        """
    )
    conn.commit()
    conn.close()


def audit(case_id: str, event: str, detail: str = "") -> None:
    conn = db()
    conn.execute("INSERT INTO audits(case_id,event,detail,created_at) VALUES (?,?,?,?)", (case_id, event, detail, now()))
    conn.execute("UPDATE cases SET updated_at=? WHERE id=?", (now(), case_id))
    conn.commit()
    conn.close()


def normalize_money(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?", str(v))
    return float(m.group(0).replace(",", "")) if m else None


def normalize_int(v: Any) -> int | None:
    if v is None:
        return None
    m = re.search(r"\d[\d,]*", str(v))
    return int(m.group(0).replace(",", "")) if m else None


def lines(text: str) -> list[str]:
    return [x.strip() for x in text.replace("\r", "").split("\n") if x.strip()]


def value_after(text: str, keys: list[str]) -> str | None:
    for line in lines(text):
        low = line.lower()
        for key in keys:
            if low.startswith(key.lower() + ":") or low.startswith(key.lower() + " "):
                return line.split(":", 1)[1].strip() if ":" in line else line[len(key):].strip(" -")
    return None


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf" and PdfReader:
        try:
            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            pass
    return path.read_text(encoding="utf-8", errors="ignore")


def classify_document(filename: str, text: str) -> str:
    hay = f"{filename}\n{text}".lower()
    if any(k in hay for k in ["delivery challan", "delivery note", "challan no"]):
        return "delivery_challan"
    if any(k in hay for k in ["invoice", "invoice no", "tax invoice"]):
        return "invoice"
    if any(k in hay for k in ["purchase order", "po number", "po no", "purchase order no"]):
        return "purchase_order"
    raise ValueError("Could not classify document as Purchase Order, Invoice, or Delivery Challan")


def parse_line_item(text: str) -> dict[str, Any]:
    # Supports the demo format and common simple invoice/PO tables.
    qty = normalize_int(re.search(r"(?:qty|quantity)\s*[:=]?\s*(\d[\d,]*)", text, re.I).group(1) if re.search(r"(?:qty|quantity)\s*[:=]?\s*(\d[\d,]*)", text, re.I) else None)
    price = normalize_money(re.search(r"(?:unit price|rate|price)\s*[:=]?\s*([₹$]?\s?[\d,]+(?:\.\d+)?)", text, re.I).group(1) if re.search(r"(?:unit price|rate|price)\s*[:=]?\s*([₹$]?\s?[\d,]+(?:\.\d+)?)", text, re.I) else None)
    desc = value_after(text, ["Item", "Description", "Product"]) or "Unspecified item"
    return {"description": desc, "quantity": qty or 0, "unit_price": price or 0.0}


def extract_structured(doc_type: str, text: str, filename: str) -> dict[str, Any]:
    # Intentionally deterministic for the core MVP; model augmentation can be added behind the same schema.
    vendor = value_after(text, ["Vendor", "Supplier", "Seller"]) or "Unknown Vendor"
    po_number = value_after(text, ["PO Number", "PO No", "Purchase Order No", "Reference PO"])
    invoice_number = value_after(text, ["Invoice Number", "Invoice No"])
    date = value_after(text, ["Date", "Invoice Date", "PO Date", "Delivery Date"]) or ""
    total = normalize_money(value_after(text, ["Total", "Grand Total", "Invoice Total"]))

    item_block = "\n".join(lines(text))
    item = parse_line_item(item_block)
    result: dict[str, Any] = {
        "document_type": doc_type,
        "document_label": TYPE_LABELS[doc_type],
        "filename": filename,
        "vendor": vendor,
        "po_number": po_number,
        "invoice_number": invoice_number,
        "date": date,
        "items": [item],
        "quantity": item["quantity"],
        "unit_price": item["unit_price"],
        "total": total,
        "raw_text": text[:12000],
    }
    return result


def evidence(document: dict[str, Any], field: str, value: Any) -> dict[str, Any]:
    raw = document.get("raw_text", "")
    needle = str(value)
    idx = raw.lower().find(needle.lower()) if needle else -1
    snippet = raw[max(0, idx - 90): idx + len(needle) + 120] if idx >= 0 else raw[:220]
    return {
        "document": document.get("filename"),
        "field": field,
        "value": value,
        "page": 1,
        "snippet": snippet.strip(),
        "confidence": 0.97 if idx >= 0 else 0.74,
    }


def reconcile(docs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    po, inv, challan = docs.get("purchase_order"), docs.get("invoice"), docs.get("delivery_challan")
    checks: list[dict[str, Any]] = []

    if not po or not inv or not challan:
        return {"status": "INCOMPLETE", "checks": [], "summary": "Upload all three documents before analysis.", "score": 0}

    checks.append({
        "key": "vendor",
        "label": "Vendor",
        "expected": po["vendor"],
        "actual": inv["vendor"],
        "status": "MATCH" if po["vendor"].strip().lower() == inv["vendor"].strip().lower() == challan["vendor"].strip().lower() else "MISMATCH",
        "evidence": [evidence(po, "vendor", po["vendor"]), evidence(inv, "vendor", inv["vendor"]), evidence(challan, "vendor", challan["vendor"])],
    })

    po_ref = po.get("po_number") or ""
    inv_ref = inv.get("po_number") or ""
    checks.append({
        "key": "po_reference",
        "label": "PO reference",
        "expected": po_ref or "—",
        "actual": inv_ref or "—",
        "status": "MATCH" if po_ref and inv_ref and po_ref.lower() == inv_ref.lower() else "MISMATCH",
        "evidence": [evidence(po, "po_number", po_ref or "PO"), evidence(inv, "po_number", inv_ref or "PO")],
    })

    ordered = po["quantity"]
    invoiced = inv["quantity"]
    delivered = challan["quantity"]
    checks.append({
        "key": "quantity",
        "label": "Quantity",
        "expected": ordered,
        "actual": {"invoice": invoiced, "delivery": delivered},
        "status": "MATCH" if ordered == invoiced == delivered else "MISMATCH",
        "variance": {"invoice": invoiced - ordered, "delivery": delivered - ordered},
        "evidence": [evidence(po, "quantity", ordered), evidence(inv, "quantity", invoiced), evidence(challan, "quantity", delivered)],
    })

    po_price, inv_price = float(po["unit_price"]), float(inv["unit_price"])
    price_delta = round(inv_price - po_price, 2)
    checks.append({
        "key": "unit_price",
        "label": "Unit price",
        "expected": po_price,
        "actual": inv_price,
        "status": "MATCH" if abs(price_delta) < 0.01 else "MISMATCH",
        "variance": price_delta,
        "evidence": [evidence(po, "unit_price", po_price), evidence(inv, "unit_price", inv_price)],
    })

    mismatch = sum(1 for c in checks if c["status"] == "MISMATCH")
    status = "MATCH" if mismatch == 0 else "EXCEPTION"
    if status == "MATCH":
        summary = "All critical procurement fields reconcile across PO, invoice, and delivery challan."
    elif checks[2]["status"] == "MISMATCH":
        summary = f"Quantity exception: ordered {ordered}, invoiced {invoiced}, delivered {delivered}."
    else:
        summary = f"{mismatch} reconciliation exception(s) require review before approval."
    return {"status": status, "checks": checks, "summary": summary, "score": round((len(checks) - mismatch) / len(checks) * 100)}


def recommended_action(result: dict[str, Any]) -> tuple[str, str]:
    if result["status"] == "MATCH":
        return "approve", "All critical fields reconcile. The transaction is ready for approval."
    quantity = next((c for c in result["checks"] if c["key"] == "quantity"), None)
    if quantity and quantity["status"] == "MISMATCH":
        inv = quantity["actual"]["invoice"]
        ordered = quantity["expected"]
        return "ask_vendor", f"Please clarify the quantity variance on the invoice. The PO authorizes {ordered} units, while the invoice shows {inv} units."
    return "escalate", "A procurement exception was detected and requires manual review before the transaction can proceed."


class CaseCreate(BaseModel):
    name: str = Field(default="Procurement verification", min_length=3, max_length=120)


class ActionCreate(BaseModel):
    action_type: str = Field(pattern="^(approve|ask_vendor|escalate)$")
    message: str = Field(min_length=1, max_length=5000)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "karyaflow-ai", "version": "1.0.0"}


@app.post("/api/cases")
def create_case(payload: CaseCreate) -> dict[str, Any]:
    case_id = str(uuid.uuid4())
    ts = now()
    conn = db()
    conn.execute("INSERT INTO cases(id,name,status,created_at,updated_at) VALUES (?,?,?,?,?)", (case_id, payload.name, "draft", ts, ts))
    conn.commit()
    conn.close()
    audit(case_id, "case_created", payload.name)
    return {"id": case_id, "name": payload.name, "status": "draft"}


@app.post("/api/cases/{case_id}/documents")
def upload_documents(case_id: str, files: list[UploadFile] = File(...)) -> dict[str, Any]:
    conn = db()
    case = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    if not case:
        conn.close()
        raise HTTPException(404, "Case not found")
    out = []
    for upload in files:
        filename = Path(upload.filename or "document").name
        if not filename.lower().endswith((".pdf", ".txt")):
            raise HTTPException(400, "Only PDF or TXT demo documents are supported")
        doc_id = str(uuid.uuid4())
        path = UPLOAD_DIR / f"{doc_id}_{filename}"
        content = upload.file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(413, "Maximum file size is 10 MB")
        path.write_bytes(content)
        text = extract_text(path)
        try:
            doc_type = classify_document(filename, text)
            structured = extract_structured(doc_type, text, filename)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        conn.execute("INSERT INTO documents(id,case_id,filename,document_type,path,extracted_json,created_at) VALUES (?,?,?,?,?,?,?)", (doc_id, case_id, filename, doc_type, str(path), json.dumps(structured), now()))
        out.append({"id": doc_id, "filename": filename, "document_type": doc_type, "label": TYPE_LABELS[doc_type]})
        audit(case_id, "document_uploaded", f"{filename} → {TYPE_LABELS[doc_type]}")
    conn.execute("UPDATE cases SET status='documents_ready',updated_at=? WHERE id=?", (now(), case_id))
    conn.commit()
    conn.close()
    return {"documents": out}


@app.post("/api/cases/{case_id}/analyze")
def analyze(case_id: str) -> dict[str, Any]:
    conn = db()
    rows = conn.execute("SELECT * FROM documents WHERE case_id=?", (case_id,)).fetchall()
    if not rows:
        conn.close()
        raise HTTPException(400, "Upload procurement documents first")
    docs = {row["document_type"]: json.loads(row["extracted_json"]) for row in rows}
    result = reconcile(docs)
    action, message = recommended_action(result)
    conn.execute("UPDATE cases SET status=?,updated_at=? WHERE id=?", (result["status"].lower(), now(), case_id))
    conn.commit()
    conn.close()
    audit(case_id, "analysis_completed", result["summary"])
    return {"case_id": case_id, "reconciliation": result, "recommendation": {"action": action, "message": message}, "documents": docs}


@app.get("/api/cases/{case_id}")
def get_case(case_id: str) -> dict[str, Any]:
    conn = db()
    case = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    if not case:
        conn.close()
        raise HTTPException(404, "Case not found")
    docs = conn.execute("SELECT id,filename,document_type,extracted_json,created_at FROM documents WHERE case_id=? ORDER BY created_at", (case_id,)).fetchall()
    acts = conn.execute("SELECT * FROM actions WHERE case_id=? ORDER BY created_at DESC", (case_id,)).fetchall()
    audits = conn.execute("SELECT * FROM audits WHERE case_id=? ORDER BY created_at DESC", (case_id,)).fetchall()
    conn.close()
    return {"case": dict(case), "documents": [{**dict(x), "extracted": json.loads(x["extracted_json"])} for x in docs], "actions": [dict(x) for x in acts], "audit": [dict(x) for x in audits]}


@app.post("/api/cases/{case_id}/actions")
def create_action(case_id: str, payload: ActionCreate) -> dict[str, Any]:
    action_id = str(uuid.uuid4())
    conn = db()
    if not conn.execute("SELECT 1 FROM cases WHERE id=?", (case_id,)).fetchone():
        conn.close(); raise HTTPException(404, "Case not found")
    conn.execute("INSERT INTO actions(id,case_id,action_type,message,status,created_at) VALUES (?,?,?,?,?,?)", (action_id, case_id, payload.action_type, payload.message, "pending", now()))
    conn.commit(); conn.close()
    audit(case_id, "action_created", payload.action_type)
    return {"id": action_id, "status": "pending"}


@app.post("/api/cases/{case_id}/actions/{action_id}/approve")
def approve_action(case_id: str, action_id: str) -> dict[str, Any]:
    conn = db()
    row = conn.execute("SELECT * FROM actions WHERE id=? AND case_id=?", (action_id, case_id)).fetchone()
    if not row:
        conn.close(); raise HTTPException(404, "Action not found")
    conn.execute("UPDATE actions SET status='approved',approved_at=? WHERE id=?", (now(), action_id))
    conn.commit(); conn.close()
    audit(case_id, "human_approved_action", row["action_type"])
    return {"id": action_id, "status": "approved"}


@app.get("/api/cases/{case_id}/audit")
def get_audit(case_id: str) -> dict[str, Any]:
    conn = db()
    rows = conn.execute("SELECT * FROM audits WHERE case_id=? ORDER BY created_at DESC", (case_id,)).fetchall()
    conn.close()
    return {"audit": [dict(x) for x in rows]}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
