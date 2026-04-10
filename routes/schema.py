from flask import Blueprint, request, jsonify
from pymongo import MongoClient

schema_bp = Blueprint('schema', __name__)

# ── MongoDB connection (local, no API key) ──────────────────────────────────
MONGO_URI = "mongodb://localhost:27017/"
try:
    client = MongoClient(MONGO_URI)
    db = client["intellicredit"]
    schema_col = db["schema"]
    print("MongoDB Connected: intellicredit.schema")
except Exception as e:
    print("Warning: Could not connect to MongoDB:", e)

# Default schema definition if none exists in DB
DEFAULT_SCHEMA = [
    {"key": "revenue", "label": "Revenue", "type": "currency", "rule": "Positive revenue"},
    {"key": "ebitda", "label": "EBITDA", "type": "currency", "rule": "EBITDA ≤ Revenue"},
    {"key": "pat", "label": "PAT (Profit After Tax)", "type": "currency", "rule": "PAT ≤ EBITDA"},
    {"key": "debtEquity", "label": "Debt-Equity Ratio", "type": "ratio", "rule": "D/E ≤ 3.0"},
    {"key": "dscr", "label": "DSCR", "type": "ratio", "rule": "DSCR ≥ 1.0"},
    {"key": "interestCoverage", "label": "Interest Coverage", "type": "ratio", "rule": "ICR > 1.5"},
    {"key": "currentRatio", "label": "Current Ratio", "type": "ratio", "rule": "CR ≥ 1.0"}
]

@schema_bp.route('/api/schema', methods=['GET'])
def get_schema():
    """Retrieve the current dynamic extraction schema configuration."""
    try:
        doc = schema_col.find_one({"type": "extraction_schema"})
        if not doc:
            # Seed the default schema
            doc = {"type": "extraction_schema", "fields": DEFAULT_SCHEMA}
            schema_col.insert_one(doc)
            doc["_id"] = str(doc["_id"])
        else:
            doc["_id"] = str(doc["_id"])
        
        return jsonify({"ok": True, "schema": doc["fields"]}), 200
    except Exception as exc:
        return jsonify({"error": f"DB error: {exc}"}), 500

@schema_bp.route('/api/schema', methods=['POST'])
def update_schema():
    """Update or define the extraction schema configuration."""
    payload = request.get_json()
    if not payload or "fields" not in payload:
        return jsonify({"error": "Invalid payload. 'fields' array is required."}), 400
        
    try:
        result = schema_col.update_one(
            {"type": "extraction_schema"},
            {"$set": {"fields": payload["fields"]}},
            upsert=True
        )
        return jsonify({"ok": True, "message": "Schema updated successfully."}), 200
    except Exception as exc:
        return jsonify({"error": f"DB error: {exc}"}), 500
