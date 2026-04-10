import time
from flask import Blueprint, jsonify, request

mock_bp = Blueprint('mock', __name__)

# Mock counter to simulate eventual success after failures
mock_state = {
    'news_google': 0,
    'news_bing': 0,
    'mca': 0
}

@mock_bp.route('/mock/news/google')
def mock_news_google():
    """Simulate complete strict failure (500) always to trigger fallback."""
    return jsonify({"error": "Internal Server Error"}), 500

@mock_bp.route('/mock/news/bing')
def mock_news_bing():
    """Simulate a rate limit (429) always, to test wait logic."""
    # To prevent actual 30s wait during manual test, we'll simulate 503 instead for fast exponential backoff
    mock_state['news_bing'] += 1
    if mock_state['news_bing'] < 3:
        return jsonify({"error": "Service Unavailable - Try Again"}), 503
    
    return jsonify({
        "sentiment": "Neutral",
        "signals": {"trend": "stable", "recent_mentions": 12}
    }), 200

@mock_bp.route('/mock/news/scrape')
def mock_news_scrape():
    """Fallback 3 always succeeds."""
    return jsonify({
        "sentiment": "Positive",
        "signals": {"trend": "upward", "recent_mentions": 4}
    }), 200


@mock_bp.route('/mock/mca')
def mock_mca():
    """Simulate invalid JSON response."""
    # Returns malformed JSON string that fails `response.json()`
    # but could be "cleaned" by replacing ```json wrappers.
    return "```json\n{'promoter_intel': {'status': 'active'}\n```", 200

@mock_bp.route('/mock/filings')
def mock_filings():
    """Fallback 1 for corporate data succeeds."""
    return jsonify({
        "promoter_intel": {
            "key_promoters": ["Alice", "Bob"],
            "pledged_shares_pct": 0.0
        }
    }), 200


@mock_bp.route('/mock/ecourts')
def mock_ecourts():
    """Simulates a timeout or 404 (we will simulate 404 so it immediately falls back)."""
    return jsonify({"error": "Not Found"}), 404

@mock_bp.route('/mock/legaldb')
def mock_legaldb():
    return jsonify({
        "cases": [
            {"case_id": "L-101", "status": "Pending", "type": "Civil"},
            {"case_id": "L-101", "status": "Pending", "type": "Civil"} # Duplicate to test duplicate removal
        ],
        "regulatory_flags": ["Delayed Filing"]
    }), 200
