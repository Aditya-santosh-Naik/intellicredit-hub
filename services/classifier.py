import spacy

# Load spaCy model
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    print("Downloading spaCy model en_core_web_sm...")
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load('en_core_web_sm')

CATEGORIES = {
    'ALM Statement': ['ASSET LIABILITY MANAGEMENT', 'ALM GAP', 'LIQUIDITY RISK', 'MATURITY PROFILE', 'INTEREST RATE RISK', 'ALM STATEMENT'],
    'Shareholding Pattern': ['SHAREHOLDING PATTERN', 'PROMOTER HOLDING', 'PUBLIC SHAREHOLDING', 'EQUITY SHARES', 'SHAREHOLDER', 'HOLDING PERCENTAGE'],
    'Borrowing Profile': ['LENDER', 'OUTSTANDING DEBT', 'CREDIT FACILITY', 'TERM LOAN', 'BORROWING', 'FACILITY AMOUNT', 'SANCTION LETTER', 'BORROWING PROFILE'],
    'Annual Report': ['BALANCE SHEET', 'PROFIT AND LOSS', 'CASH FLOW', 'ANNUAL REPORT', 'AUDITORS REPORT', 'FINANCIAL STATEMENT'],
    'Portfolio Performance': ['NPA', 'DPD', 'PORTFOLIO AGING', 'GROSS NPA', 'NET NPA', 'COLLECTION EFFICIENCY', 'NON-PERFORMING ASSETS', 'PORTFOLIO PERFORMANCE']
}

def classify_document(text):
    """
    Classifies a document based on extracted text using keyword matching and NLP.
    Returns: {"classification": str, "confidence": float}
    """
    if not text.strip():
        return {"classification": "Unknown", "confidence": 0.0}

    # Basic normalization without stripping everything (spaCy can be heavy for huge texts, so we process first 500k chars to prevent memory issues)
    text = text[:500000]
    normalized_text = text.upper()

    category_scores = {category: 0 for category in CATEGORIES}
    
    # We will use simple substring counting for speed and reliability
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            count = normalized_text.count(keyword)
            # Give higher weight to multi-word phrases instead of single letters
            weight = len(keyword.split()) 
            category_scores[category] += (count * weight)

    total_score = sum(category_scores.values())

    if total_score == 0:
        return {"classification": "Unknown", "confidence": 0.1}

    # Calculate probabilities
    best_category = max(category_scores, key=category_scores.get)
    best_score = category_scores[best_category]
    
    # Confidence calculation formula
    base_confidence = 0.5
    confidence_score = base_confidence + (best_score / (best_score + 10)) * 0.5  # Asymptotic to 1.0

    return {
        "classification": best_category,
        "confidence": round(min(confidence_score, 0.99), 2)
    }
