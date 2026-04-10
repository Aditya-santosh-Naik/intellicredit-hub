"""
IntelliCredit Hub — FastAPI Data Layer
Stores credit appraisal cases into local MongoDB (no auth required).
Run with:  uvicorn api:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime, timezone
import os, json
from difflib import SequenceMatcher
from pymongo import MongoClient
from bson import ObjectId
import uvicorn

# ── MongoDB connection (local, no API key) ──────────────────────────────────
MONGO_URI = "mongodb://localhost:27017/"
client = MongoClient(MONGO_URI)
db = client["intellicredit"]
cases_col = db["cases"]

# ── ML Artifacts ────────────────────────────────────────────────────────────
ML_DIR = os.path.join(os.path.dirname(__file__), "ml_model")
company_db = {"by_cin": {}, "by_pan": {}}
try:
    with open(os.path.join(ML_DIR, "company_db.json"), "r") as f:
        company_db = json.load(f)
        print(f"Loaded ML lookup DB: {len(company_db.get('by_cin', {}))} companies")
except Exception as e:
    print("Warning: Could not load company_db.json:", e)

# ── FastAPI app ─────────────────────────────────────────────────────────────
app = FastAPI(title="IntelliCredit API", version="1.0.0")

# Allow requests from the Flask app (port 5000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5000", "http://localhost:5000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ─────────────────────────────────────────────────────────────────
class FinancialMetric(BaseModel):
    metric: str
    value: Any
    status: Optional[str] = None

class FiveCsScore(BaseModel):
    name: str
    score: float

class SwotItem(BaseModel):
    category: str   # Strengths / Weaknesses / Opportunities / Threats
    items: List[str]

class McaVerifyPayload(BaseModel):
    company: str
    cin: str
    pan: str

class CasePayload(BaseModel):
    # Stage 1 — Entity & Loan
    company: str
    cin: Optional[str] = None
    pan: Optional[str] = None
    sector: Optional[str] = None
    loan_amount: Optional[float] = None
    annual_turnover: Optional[float] = None

    # Stage 3 — Financial Extraction
    financial_metrics: Optional[List[FinancialMetric]] = []

    # Stage 4 — AI Risk Analysis
    five_cs: Optional[List[FiveCsScore]] = []
    composite_score: Optional[float] = None
    fraud_flags: Optional[List[str]] = []
    swot: Optional[List[SwotItem]] = []
    research_items: Optional[List[str]] = []
    decision_chain: Optional[List[str]] = []
    ai_confidence: Optional[float] = None

    # Extra free-form data
    extra: Optional[Dict[str, Any]] = {}


# ── Routes ───────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    """Quick health-check endpoint."""
    return {"status": "ok", "db": db.name, "ml_db_loaded": len(company_db.get("by_cin", {})) > 0}


@app.post("/api/verify-mca")
def verify_mca(payload: McaVerifyPayload):
    """
    Verifies the CIN, PAN, and Company Name against the ML database (company_db.json).
    Returns verified=true if data is consistent, else verified=false with a reason.
    """
    cin = payload.cin.strip().upper()
    pan = payload.pan.strip().upper()
    name = payload.company.strip().upper()

    # Look up by CIN or PAN
    record = company_db.get("by_cin", {}).get(cin)
    if not record:
        record = company_db.get("by_pan", {}).get(pan)

    if not record:
        return {
            "verified": False,
            "reason": "CIN / PAN not found in MCA registry database."
        }

    # If found, cross-check details
    if record.get("cin") != cin:
        return {"verified": False, "reason": f"CIN mismatch with registered PAN {pan}"}
    if record.get("pan") != pan:
        return {"verified": False, "reason": f"PAN mismatch with registered CIN {cin}"}

    # Fuzzy match company name (allow minor typos)
    db_name = record.get("company", "").upper()
    similarity = SequenceMatcher(None, name, db_name).ratio()
    if similarity < 0.6:  # 60% similarity threshold
        # Allow checking if one is a substring of the other (e.g. "TATA MOTORS" vs "TATA MOTORS LTD")
        if name not in db_name and db_name not in name:
            return {
                "verified": False,
                "reason": f"Company Name mismatch. Registry shows: '{record.get('company')}'"
            }

    return {
        "verified": True,
        "company": record.get("company"),
        "cin": record.get("cin"),
        "pan": record.get("pan"),
        "sector": record.get("sector"),
        "reason": "Data matched successfully in ML registry."
    }


@app.post("/api/submit-case")
def submit_case(payload: CasePayload):
    """
    Receive the full credit appraisal data from the wizard and persist it
    to MongoDB (intellicredit.cases).
    """
    doc = payload.model_dump()
    doc["submitted_at"] = datetime.now(timezone.utc).isoformat()

    try:
        result = cases_col.insert_one(doc)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB error: {exc}")

    return {"ok": True, "id": str(result.inserted_id)}


@app.get("/api/cases")
def list_cases(limit: int = 50):
    """Return the most recently submitted cases (newest first)."""
    cursor = cases_col.find({}, {"_id": 1, "company": 1, "sector": 1,
                                  "loan_amount": 1, "composite_score": 1,
                                  "submitted_at": 1}) \
                       .sort("submitted_at", -1).limit(limit)
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results


@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    """Fetch a single case by its MongoDB ObjectId."""
    try:
        oid = ObjectId(case_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid case ID")
    doc = cases_col.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Case not found")
    doc["_id"] = str(doc["_id"])
    return doc


if __name__ == "__main__":
    print("IntelliCredit FastAPI running at http://127.0.0.1:8000")
    print("Docs:  http://127.0.0.1:8000/docs")
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
