from flask import Blueprint, request, jsonify
from difflib import SequenceMatcher
import os
import json

verification_bp = Blueprint('verification', __name__)

# ── ML Artifacts ────────────────────────────────────────────────────────────
# Point to root ml_model directory instead of relative to `api.py`
ML_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml_model")
company_db = {"by_cin": {}, "by_pan": {}}

try:
    with open(os.path.join(ML_DIR, "company_db.json"), "r") as f:
        company_db = json.load(f)
        print(f"Loaded ML lookup DB in Flask: {len(company_db.get('by_cin', {}))} companies")
except Exception as e:
    print("Warning: Could not load company_db.json in Flask:", e)

@verification_bp.route('/api/verify-mca', methods=['POST'])
def verify_mca():
    """
    Verifies the CIN, PAN, and Company Name against the ML database (company_db.json).
    Returns verified=true if data is consistent, else verified=false with a reason.
    """
    payload = request.get_json()
    if not payload:
        return jsonify({"verified": False, "reason": "No JSON payload provided"}), 400
        
    cin = payload.get('cin', '').strip().upper()
    pan = payload.get('pan', '').strip().upper()
    name = payload.get('company', '').strip().upper()

    # Look up by CIN or PAN
    record = company_db.get("by_cin", {}).get(cin)
    if not record:
        record = company_db.get("by_pan", {}).get(pan)

    if not record:
        return jsonify({
            "verified": False,
            "reason": "CIN / PAN not found in MCA registry database."
        })

    # If found, cross-check details
    if record.get("cin") != cin:
        return jsonify({"verified": False, "reason": f"CIN mismatch with registered PAN {pan}"})
    if record.get("pan") != pan:
        return jsonify({"verified": False, "reason": f"PAN mismatch with registered CIN {cin}"})

    # Fuzzy match company name (allow minor typos)
    db_name = record.get("company", "").upper()
    similarity = SequenceMatcher(None, name, db_name).ratio()
    if similarity < 0.6:  # 60% similarity threshold
        # Allow checking if one is a substring of the other (e.g. "TATA MOTORS" vs "TATA MOTORS LTD")
        if name not in db_name and db_name not in name:
            return jsonify({
                "verified": False,
                "reason": f"Company Name mismatch. Registry shows: '{record.get('company')}'"
            })

    return jsonify({
        "verified": True,
        "company": record.get("company"),
        "cin": record.get("cin"),
        "pan": record.get("pan"),
        "sector": record.get("sector"),
        "reason": "Data matched successfully in ML registry."
    }), 200
