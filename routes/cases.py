from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
from services.extractor import extract_metrics

cases_bp = Blueprint('cases', __name__)

# ── MongoDB connection (local, no API key) ──────────────────────────────────
MONGO_URI = "mongodb://localhost:27017/"
try:
    client = MongoClient(MONGO_URI)
    db = client["intellicredit"]
    cases_col = db["cases"]
    print("MongoDB Connected: intellicredit.cases")
except Exception as e:
    print("Warning: Could not connect to MongoDB:", e)

def generate_case_id():
    last_case = cases_col.find_one({}, sort=[("case_id", -1)])
    if not last_case or "case_id" not in last_case:
        return "LC-000001"
    
    last_id = last_case["case_id"]
    try:
        num = int(last_id.split("-")[1])
        return f"LC-{num+1:06d}"
    except:
        return f"LC-{ObjectId().hex[-6:].upper()}"

@cases_bp.route('/api/cases', methods=['POST'])
def create_case():
    """
    Create a new case (Stage 1).
    Generates a unique LC-XXXXXX case_id and sets status to ENTITY_COMPLETED.
    """
    payload = request.get_json()
    if not payload:
        return jsonify({"error": "No JSON payload provided"}), 400
        
    case_id = generate_case_id()
    payload["case_id"] = case_id
    payload["status"] = "ENTITY_COMPLETED"
    payload["created_at"] = datetime.now(timezone.utc).isoformat()
    payload["updated_at"] = payload["created_at"]
    payload["documents"] = [] # Initialize empty docs array

    try:
        result = cases_col.insert_one(payload)
        return jsonify({"ok": True, "case_id": case_id, "_id": str(result.inserted_id)}), 201
    except Exception as exc:
        return jsonify({"error": f"DB error: {exc}"}), 500

@cases_bp.route('/api/cases/<case_id>', methods=['PATCH'])
def update_case(case_id):
    """
    Incrementally update a case by case_id.
    """
    payload = request.get_json()
    if not payload:
        return jsonify({"error": "No JSON payload provided"}), 400
        
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    try:
        result = cases_col.update_one({"case_id": case_id}, {"$set": payload})
        if result.matched_count == 0:
            return jsonify({"error": "Case not found"}), 404
        return jsonify({"ok": True, "case_id": case_id}), 200
    except Exception as exc:
        return jsonify({"error": f"DB error: {exc}"}), 500


@cases_bp.route('/api/cases', methods=['GET'])
def list_cases():
    """Return the most recently created cases (newest first)."""
    limit_str = request.args.get('limit', '50')
    try:
        limit = int(limit_str)
    except ValueError:
        limit = 50
        
    try:
        cursor = cases_col.find({}, {
            "_id": 1, "case_id": 1, "company": 1, "sector": 1,
            "loan_amount": 1, "composite_score": 1,
            "status": 1, "created_at": 1, "updated_at": 1
        }).sort("created_at", -1).limit(limit)
        
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return jsonify(results), 200
    except Exception as e:
         return jsonify({"error": f"Failed to list cases: {e}"}), 500


@cases_bp.route('/api/cases/<case_id>/extract', methods=['POST'])
def extract_case_metrics(case_id):
    """
    Execute Stage 5 Financial Data Extraction.
    Reads documents attached to the case, pulls the dynamic schema,
    and extracts structured metrics using NLP text parsing with
    case-specific smart estimation as fallback.
    """
    try:
        doc = cases_col.find_one({"case_id": case_id})
        if not doc:
            return jsonify({"error": "Case not found"}), 404

        docs = doc.get("documents", [])

        # Build case meta for smart estimation fallback
        case_meta = {
            "loan_amount":     doc.get("loan_amount", 0),
            "annual_turnover": doc.get("annual_turnover", 0),
            "sector":          doc.get("sector", ""),
        }

        # Load schema
        schema_doc = db["schema"].find_one({"type": "extraction_schema"})
        schema_fields = schema_doc.get("fields", []) if schema_doc else []

        if not schema_fields:
            # Default schema if DB empty
            schema_fields = [
                {"key": "revenue",         "label": "Revenue",             "type": "currency"},
                {"key": "ebitda",          "label": "EBITDA",              "type": "currency"},
                {"key": "pat",             "label": "PAT",                 "type": "currency"},
                {"key": "debtEquity",      "label": "Debt-Equity Ratio",   "type": "ratio"},
                {"key": "dscr",            "label": "DSCR",                "type": "ratio"},
                {"key": "interestCoverage","label": "Interest Coverage",   "type": "ratio"},
                {"key": "currentRatio",    "label": "Current Ratio",       "type": "ratio"},
            ]

        # Run extraction — pass case_meta for smart estimation fallback
        metrics = extract_metrics(docs, schema_fields, case_meta=case_meta)

        # Remove internal audit field before saving (optional — save it for transparency)
        sources = metrics.pop("_sources", {})

        cases_col.update_one(
            {"case_id": case_id},
            {
                "$set": {
                    "financial_metrics":         metrics,
                    "financial_metrics_sources": sources,
                    "updated_at":               datetime.now(timezone.utc).isoformat(),
                    "status":                   "FINANCIALS_EXTRACTED"
                }
            }
        )

        return jsonify({"ok": True, "financial_metrics": metrics, "sources": sources}), 200

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": f"Extraction failed: {e}"}), 500



@cases_bp.route('/api/cases/<case_id>', methods=['GET'])
def get_case(case_id):
    """Fetch a single case by its string case_id."""
    doc = cases_col.find_one({"case_id": case_id})
    if not doc:
        return jsonify({"error": "Case not found"}), 404
        
    doc["_id"] = str(doc["_id"])
    return jsonify(doc), 200
