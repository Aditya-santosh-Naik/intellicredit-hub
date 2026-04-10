from flask import Blueprint, jsonify
from pymongo import MongoClient
from datetime import datetime, timezone
from services.data_agent import DataIntelligenceAgent

analyzer_bp = Blueprint('analyzer', __name__)

MONGO_URI = "mongodb://localhost:27017/"
try:
    client = MongoClient(MONGO_URI)
    db = client["intellicredit"]
    cases_col = db["cases"]
except Exception as e:
    print("Warning: Could not connect to MongoDB:", e)

def _clamp(value, lo=0, hi=100):
    return max(lo, min(hi, value))

def build_triangulation(financials, intel):
    """Stage 7: Data Triangulation"""
    insights = []

    revenue = financials.get("revenue", 0)
    sentiment = intel.get("news_sentiment", "").lower()

    if revenue > 100000000 and "negative" in sentiment:
        insights.append({"flag": "Warning", "message": "High reported revenue contradicts negative market sentiment from news sources."})
    elif revenue > 0 and "positive" in sentiment:
        insights.append({"flag": "Positive", "message": "Reported revenue aligns well with positive market news signals."})

    ebitda = financials.get("ebitda", 0)
    if ebitda < 0 and intel.get("litigation_cases"):
        insights.append({"flag": "Critical", "message": "Negative EBITDA compounded by active litigation cases."})

    pat = financials.get("pat", 0)
    if revenue > 0 and pat is not None:
        margin = (pat / revenue) * 100
        if margin < 5:
            insights.append({"flag": "Warning", "message": f"Thin net profit margin of {margin:.1f}% signals operational stress."})
        elif margin > 15:
            insights.append({"flag": "Positive", "message": f"Healthy net profit margin of {margin:.1f}% indicates strong profitability."})

    if not insights:
        insights.append({"flag": "Neutral", "message": "Financial data shows standard alignment with secondary market intelligence."})

    return insights


def build_explainable_score(financials, intel, case_meta=None):
    """Stage 8: Explainable Risk Recommendation -- fully data-driven."""
    if case_meta is None:
        case_meta = {}

    loan_amount    = float(case_meta.get("loan_amount", 0) or 0)
    annual_turnover = float(case_meta.get("annual_turnover", 0) or 0)
    revenue        = float(financials.get("revenue", 0) or 0)
    ebitda         = float(financials.get("ebitda", 0) or 0)
    pat            = float(financials.get("pat", 0) or 0)
    dscr           = float(financials.get("dscr", 0) or 0)
    de_ratio       = float(financials.get("debtEquity", 0) or 0)
    current_ratio  = float(financials.get("currentRatio", 0) or 0)

    # -- Character (integrity / litigation / regulatory) --
    character = 80
    litigation_cases = intel.get("litigation_cases", [])
    regulatory_flags = intel.get("regulatory_flags", [])
    if litigation_cases:
        character -= min(25, len(litigation_cases) * 10)
    if regulatory_flags:
        character -= min(20, len(regulatory_flags) * 10)
    promoter_intel = intel.get("promoter_intel", {})
    pledged_pct = promoter_intel.get("pledged_shares_pct", 0) if isinstance(promoter_intel, dict) else 0
    if pledged_pct == 0:
        character += 5
    elif pledged_pct > 30:
        character -= 15

    # -- Capacity (ability to service debt from earnings) --
    capacity = 60
    if dscr > 0:
        if   dscr >= 2.0:  capacity = 95
        elif dscr >= 1.5:  capacity = 82
        elif dscr >= 1.25: capacity = 70
        elif dscr >= 1.0:  capacity = 55
        else:              capacity = 30
    elif ebitda > 0 and loan_amount > 0:
        proxy = ebitda / loan_amount
        if   proxy >= 0.30: capacity = 78
        elif proxy >= 0.15: capacity = 62
        elif proxy >= 0.05: capacity = 48
        else:               capacity = 35

    # -- Capital (leverage / equity cushion) --
    capital = 70
    if de_ratio > 0:
        if   de_ratio <= 0.5: capital = 95
        elif de_ratio <= 1.0: capital = 85
        elif de_ratio <= 1.5: capital = 75
        elif de_ratio <= 2.0: capital = 62
        elif de_ratio <= 3.0: capital = 48
        else:                 capital = 30
    elif revenue > 0 and loan_amount > 0:
        ltr = loan_amount / revenue
        if   ltr <= 0.2: capital = 88
        elif ltr <= 0.4: capital = 72
        elif ltr <= 0.6: capital = 58
        else:            capital = 42

    if annual_turnover > 0 and loan_amount > 0:
        ltt = loan_amount / annual_turnover
        if   ltt <= 0.1: capital = min(100, capital + 5)
        elif ltt <= 0.3: pass
        elif ltt <= 0.5: capital -= 5
        else:            capital -= 15

    # -- Collateral (current ratio / liquidity proxy) --
    collateral = 65
    if current_ratio > 0:
        if   current_ratio >= 2.0: collateral = 90
        elif current_ratio >= 1.5: collateral = 78
        elif current_ratio >= 1.0: collateral = 65
        else:                      collateral = 40
    elif loan_amount > 0 and annual_turnover > 0:
        if   annual_turnover >= loan_amount * 3:   collateral = 80
        elif annual_turnover >= loan_amount * 1.5: collateral = 68
        else:                                      collateral = 50

    # -- Conditions (sector / market sentiment) --
    conditions = 70
    sentiment_lower = intel.get("news_sentiment", "").lower()
    if   "positive" in sentiment_lower: conditions = 88
    elif "neutral"  in sentiment_lower: conditions = 72
    elif "negative" in sentiment_lower: conditions = 45

    if revenue > 0 and pat > 0:
        margin = (pat / revenue) * 100
        if margin > 15:  conditions = min(100, conditions + 8)
        elif margin < 3: conditions -= 10

    weights = {'character': 0.25, 'capacity': 0.25, 'capital': 0.20, 'collateral': 0.15, 'conditions': 0.15}
    composite = round(
        _clamp(character)  * weights['character'] +
        _clamp(capacity)   * weights['capacity']  +
        _clamp(capital)    * weights['capital']   +
        _clamp(collateral) * weights['collateral'] +
        _clamp(conditions) * weights['conditions']
    )

    recommendation = "Reject"
    reasoning = "High risk flagged across multiple parameters."
    if composite >= 75:
        recommendation = "Approve"
        reasoning = "Solid financials and clean governance support strong debt serviceability."
    elif composite >= 60:
        recommendation = "Approve with Conditions"
        reasoning = "Generally acceptable risk profile with minor concerns requiring covenants."
    elif composite >= 45:
        recommendation = "Review"
        reasoning = "Mixed signals -- manual underwriting and additional collateral review required."

    return {
        "five_cs": {
            "character":  _clamp(character),
            "capacity":   _clamp(capacity),
            "capital":    _clamp(capital),
            "collateral": _clamp(collateral),
            "conditions": _clamp(conditions),
        },
        "composite_score": composite,
        "recommendation":  recommendation,
        "reasoning":       reasoning
    }


def build_swot(financials, intel, case_meta=None):
    """Stage 9: SWOT Generation -- dynamic from actual case data."""
    if case_meta is None:
        case_meta = {}

    swot = {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}

    loan_amount    = float(case_meta.get("loan_amount", 0) or 0)
    annual_turnover = float(case_meta.get("annual_turnover", 0) or 0)
    revenue        = float(financials.get("revenue", 0) or 0)
    ebitda         = float(financials.get("ebitda", 0) or 0)
    pat            = float(financials.get("pat", 0) or 0)
    dscr           = float(financials.get("dscr", 0) or 0)
    de_ratio       = float(financials.get("debtEquity", 0) or 0)
    current_ratio  = float(financials.get("currentRatio", 0) or 0)

    # Strengths
    if dscr >= 1.25:
        swot['strengths'].append(f"Healthy Debt Service Coverage Ratio ({dscr:.2f}x) indicating strong repayment capacity")
    if revenue >= 500000000:
        swot['strengths'].append(f"Large revenue base of Rs.{revenue/10000000:.1f} Cr demonstrates scale of operations")
    if 0 < de_ratio < 1.5:
        swot['strengths'].append(f"Conservative leverage with D/E ratio of {de_ratio:.2f}x")
    if current_ratio >= 1.5:
        swot['strengths'].append(f"Strong liquidity position (Current Ratio: {current_ratio:.2f}x)")
    if revenue > 0 and pat > 0 and (pat / revenue) > 0.10:
        swot['strengths'].append(f"High net profit margin of {(pat/revenue)*100:.1f}%")
    if not intel.get("litigation_cases"):
        swot['strengths'].append("Clean litigation history with no active legal disputes")

    # Weaknesses
    if de_ratio > 2.0:
        swot['weaknesses'].append(f"High leverage with D/E of {de_ratio:.2f}x increases financial risk")
    if 0 < dscr < 1.0:
        swot['weaknesses'].append(f"DSCR of {dscr:.2f}x is below threshold -- potential repayment stress")
    litigation_cases = intel.get("litigation_cases", [])
    if litigation_cases:
        swot['weaknesses'].append(f"Active litigation exposure ({len(litigation_cases)} case/s)")
    if ebitda > 0 and revenue > 0 and (ebitda / revenue) < 0.10:
        swot['weaknesses'].append(f"Thin EBITDA margin of {(ebitda/revenue)*100:.1f}% signals operational pressure")
    if 0 < current_ratio < 1.0:
        swot['weaknesses'].append("Current ratio below 1.0 indicates short-term liquidity concerns")
    if annual_turnover > 0 and loan_amount > annual_turnover * 0.5:
        swot['weaknesses'].append("Loan request exceeds 50% of annual turnover -- high exposure ratio")

    # Opportunities
    if "positive" in intel.get("news_sentiment", "").lower():
        swot['opportunities'].append("Positive market sentiment supports sector growth outlook")
    else:
        swot['opportunities'].append("Potential for market share expansion in current sector dynamics")
    if revenue > 0 and ebitda > 0:
        swot['opportunities'].append("Operational profitability base supports capacity for growth investments")
    if annual_turnover > 0 and loan_amount < annual_turnover * 0.2:
        swot['opportunities'].append("Low loan-to-turnover ratio leaves room for future debt capacity")

    # Threats
    if intel.get("regulatory_flags"):
        swot['threats'].append("Active regulatory flags requiring compliance monitoring")
    if "negative" in intel.get("news_sentiment", "").lower():
        swot['threats'].append("Negative market sentiment poses risks to demand outlook")
    if de_ratio > 3.0:
        swot['threats'].append("Extreme leverage levels risk covenant breaches and credit events")
    if not swot['threats']:
        swot['threats'].append("Macroeconomic headwinds and interest rate sensitivity remain key watchpoints")

    # Fail-safes
    for key in swot:
        if not swot[key]:
            swot[key].append("Standard operational matrix -- no significant signals detected")

    return swot


@analyzer_bp.route('/api/cases/<case_id>/analyze', methods=['POST'])
def analyze_case(case_id):
    """
    Executes Stages 6 (Intelligence), 7 (Triangulation),
    8 (Explainable Scoring), and 9 (SWOT Generation)
    """
    try:
        doc = cases_col.find_one({"case_id": case_id})
        if not doc:
            return jsonify({"error": "Case not found"}), 404

        company_name = doc.get("company", "Unknown Entity")
        financials   = doc.get("financial_metrics", {})
        case_meta    = {
            "loan_amount":     doc.get("loan_amount", 0),
            "annual_turnover": doc.get("annual_turnover", 0),
            "sector":          doc.get("sector", ""),
        }

        # Run Intelligence Agent
        agent = DataIntelligenceAgent(company_name)
        intel = agent.execute()

        # Data Triangulation
        triangulation = build_triangulation(financials, intel)

        # Explainable Score -- now receives case meta for richer inputs
        scoring = build_explainable_score(financials, intel, case_meta)

        # SWOT -- now receives case meta
        swot = build_swot(financials, intel, case_meta)

        # Update DB
        payload = {
            "intelligence":    intel,
            "triangulation":   triangulation,
            "scoring":         scoring,
            "swot":            swot,
            "composite_score": scoring["composite_score"],
            "status":          "ANALYZED",
            "analyzed_at":     datetime.now(timezone.utc).isoformat(),
            "updated_at":      datetime.now(timezone.utc).isoformat()
        }

        cases_col.update_one({"case_id": case_id}, {"$set": payload})

        return jsonify({"ok": True, "analysis": payload}), 200

    except Exception as e:
        return jsonify({"error": f"Analysis failed: {e}"}), 500
