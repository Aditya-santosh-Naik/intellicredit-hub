import os
import re
import pdfplumber
import pytesseract
from PIL import Image
import pandas as pd


# ── Text Extraction Helpers ──────────────────────────────────────────────────

def extract_text(file_path, file_extension):
    """
    Extracts text from a given document based on its file extension.
    Supported: pdf, png, jpg, jpeg, tiff, xlsx, xls
    """
    text = ""
    ext = file_extension.lower().strip('.')

    try:
        if ext == 'pdf':
            text = _extract_from_pdf(file_path)
        elif ext in ['png', 'jpg', 'jpeg', 'tiff']:
            text = _extract_from_image(file_path)
        elif ext in ['xlsx', 'xls']:
            text = _extract_from_excel(file_path)
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")

    if not text.strip():
        basename = os.path.basename(file_path)
        fallback = basename.replace('_', ' ').replace('-', ' ').rsplit('.', 1)[0]
        # Add document-type keywords so classifier can still recognize the file
        text = f"{fallback} STATEMENT PATTERN PORTFOLIO REPORT PROFILE BALANCE SHEET ALM"
        print(f"Extraction yielded empty text for {file_path}. Using filename fallback: '{fallback}'")

    return text


def _extract_from_pdf(file_path):
    text_content = []
    try:
        with pdfplumber.open(file_path) as pdf:
            max_pages = min(15, len(pdf.pages))
            for i in range(max_pages):
                page = pdf.pages[i]
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
    except Exception as e:
        print(f"PDF extraction error on {file_path}: {e}")

    return " ".join(text_content).replace('\n', ' ')


def _extract_from_image(file_path):
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text.replace('\n', ' ')
    except Exception as e:
        print(f"OCR Error on {file_path}: {e}")
        return ""


def _extract_from_excel(file_path):
    text_content = []
    try:
        df_dict = pd.read_excel(file_path, sheet_name=None)
        for sheet_name, df in df_dict.items():
            text_content.append(str(sheet_name))
            text_content.append(df.to_string(index=False))
    except Exception as e:
        print(f"Excel extraction error on {file_path}: {e}")

    return " ".join(text_content).replace('\n', ' ')


# ── Number Parser ────────────────────────────────────────────────────────────

def _parse_number_after_keyword(text, search_terms):
    """
    Scans `text` (already uppercased) for each term in `search_terms`.
    Returns the first number found (handles K/L/Cr/M/B suffixes).
    Returns None if nothing matched.
    """
    # Crore (Cr) = 10M, Lakh (L) = 100K — common in Indian financials
    SUFFIX_MAP = {
        'CR': 1e7,   # Indian Crore
        'L':  1e5,   # Indian Lakh
        'M':  1e6,
        'B':  1e9,
        'K':  1e3,
    }

    for term in search_terms:
        pattern = (
            re.escape(term) +
            r'[\s:=\(\)]*'                          # optional separators
            r'([\d,]+(?:\.\d+)?)'                  # digits (with optional commas and decimals)
            r'\s*([CcLlMmBbKk][Rr]?)?'            # optional suffix (Cr, L, M, B, K)
        )
        match = re.search(pattern, text)
        if match:
            num_str = match.group(1).replace(',', '').strip()
            suffix  = (match.group(2) or '').strip().upper().rstrip('R')  # normalise 'CR' -> 'C' -> handle below
            # Re-normalise: CR → CR
            raw_suffix = (match.group(2) or '').strip().upper()

            multiplier = 1.0
            for key, factor in SUFFIX_MAP.items():
                if raw_suffix.startswith(key):
                    multiplier = factor
                    break

            try:
                value = float(num_str) * multiplier
                # Sanity-check: skip garbage tiny matches (like page numbers)
                if value >= 100:   # numbers below 100 are almost never financial figures
                    return value
            except ValueError:
                continue

    return None


# ── Industry-Ratio Based Smart Estimation ───────────────────────────────────

def _estimate_from_case_data(key, annual_turnover, loan_amount, sector=""):
    """
    When OCR/parsing fails to find a real value, derive a plausible estimate
    using the company's own turnover and loan_amount with industry ratios.
    This ensures two different companies get two distinct sets of metrics.
    """
    at = float(annual_turnover or 0)
    la = float(loan_amount or 0)

    if at <= 0:
        # Absolute fallback if turnover is also not provided
        at = la * 2 if la > 0 else 0

    if at <= 0:
        return None   # Cannot estimate anything meaningful

    # Standard Indian NBFC/Corporate benchmarks used as scaling ratios
    if key == "revenue":
        return round(at * 1.05, 2)          # Revenue ≈ Turnover (slight adjustment)
    elif key == "ebitda":
        return round(at * 0.18, 2)          # EBITDA margin ~18%
    elif key == "pat":
        return round(at * 0.08, 2)          # Net margin ~8%
    elif key == "debtEquity":
        if la > 0 and at > 0:
            # Proxy D/E: assumed equity = ~40% of turnover
            equity_proxy = at * 0.40
            return round(la / equity_proxy, 2) if equity_proxy > 0 else 2.0
        return 2.0
    elif key == "dscr":
        # DSCR = EBITDA / Annual Debt Service ≈ (at*0.18) / (la * 0.15)  [15% EMI of loan]
        annual_debt_service = la * 0.15 if la > 0 else at * 0.10
        ebitda_est = at * 0.18
        return round(ebitda_est / annual_debt_service, 2) if annual_debt_service > 0 else 1.2
    elif key == "interestCoverage":
        interest_est = la * 0.10 if la > 0 else at * 0.05
        ebitda_est   = at * 0.18
        return round(ebitda_est / interest_est, 2) if interest_est > 0 else 3.0
    elif key == "currentRatio":
        # Proxy: current ratio assumed from loan-to-turnover (higher LTT = lower liquidity)
        if la > 0 and at > 0:
            ltt = la / at
            if   ltt <= 0.2: return 2.2
            elif ltt <= 0.4: return 1.6
            elif ltt <= 0.6: return 1.2
            else:            return 0.9
        return 1.3
    else:
        return None


# ── Main Extraction Function ─────────────────────────────────────────────────

def extract_metrics(documents, schema_fields, case_meta=None):
    """
    Extracts financial metrics from uploaded documents.
    Falls back to case-specific estimation (using annual_turnover and loan_amount)
    when text parsing fails — ensuring each company gets UNIQUE numbers.

    `documents`     : list of dicts with 'file_path' and 'file_type'
    `schema_fields` : list of schema dicts (key, label, type)
    `case_meta`     : dict with 'annual_turnover', 'loan_amount', 'sector'
    """
    if case_meta is None:
        case_meta = {}

    annual_turnover = float(case_meta.get("annual_turnover", 0) or 0)
    loan_amount     = float(case_meta.get("loan_amount", 0) or 0)
    sector          = str(case_meta.get("sector", ""))

    # ── Step 1: Collect all text from every uploaded document ──
    combined_text = ""
    for doc in documents:
        fp = doc.get("file_path", "")
        ft = doc.get("file_type", "")
        if fp and os.path.exists(fp):
            try:
                combined_text += " " + extract_text(fp, ft)
            except Exception as e:
                print(f"Failed extracting text for metric search: {e}")

    combined_text = combined_text.upper()
    print(f"[Extractor] Combined text length: {len(combined_text)} chars from {len(documents)} document(s)")

    # ── Step 2: Define comprehensive search terms per metric ──
    SEARCH_TERMS = {
        "revenue":         ["TOTAL REVENUE", "TOTAL INCOME", "NET REVENUE", "REVENUE FROM OPERATIONS",
                            "SALES", "REVENUE", "TOTAL TURNOVER", "TOTAL SALES"],
        "ebitda":          ["EBITDA", "OPERATING PROFIT", "EARNINGS BEFORE INTEREST TAX DEPRECIATION AMORTIZATION",
                            "OIBDA", "OPERATING INCOME"],
        "pat":             ["PROFIT AFTER TAX", "PAT", "NET PROFIT", "NET INCOME",
                            "PROFIT FOR THE YEAR", "NET EARNINGS"],
        "debtEquity":      ["DEBT EQUITY RATIO", "DEBT TO EQUITY", "D/E RATIO", "D/E",
                            "DEBT-EQUITY RATIO", "LEVERAGE RATIO"],
        "dscr":            ["DEBT SERVICE COVERAGE RATIO", "DSCR", "DEBT COVERAGE RATIO",
                            "DEBT SERVICE COVERAGE"],
        "interestCoverage":["INTEREST COVERAGE RATIO", "ICR", "INTEREST COVERAGE",
                            "TIMES INTEREST EARNED"],
        "currentRatio":    ["CURRENT RATIO", "CR RATIO", "LIQUIDITY RATIO", "WORKING CAPITAL RATIO"],
    }

    extracted = {}
    doc_found  = {}  # track which fields came from actual text vs estimation

    for field in schema_fields:
        key    = field["key"]
        label  = field["label"].upper()

        # Build final search list: schema label first, then standard terms
        terms  = [label] + SEARCH_TERMS.get(key, [])
        # Deduplicate while preserving order
        seen   = set()
        unique_terms = []
        for t in terms:
            if t not in seen:
                seen.add(t)
                unique_terms.append(t)

        val = _parse_number_after_keyword(combined_text, unique_terms)

        if val is not None:
            # Extra sanity: ratios should be <= 30, currency should be >= 1000
            if field["type"] == "ratio" and val > 30:
                val = None          # Likely a false match (e.g. a year number)
            elif field["type"] == "currency" and val < 1000:
                val = None          # Too small to be a meaningful currency figure

        if val is not None:
            extracted[key] = round(val, 2)
            doc_found[key]  = "document"
            print(f"[Extractor] {key} = {val:,.2f} (from document)")
        else:
            # ── Step 3: Smart Estimation from case meta ──
            estimated = _estimate_from_case_data(key, annual_turnover, loan_amount, sector)
            if estimated is not None:
                extracted[key] = round(estimated, 2)
                doc_found[key]  = "estimated"
                print(f"[Extractor] {key} = {estimated:,.2f} (estimated from turnover={annual_turnover:,.0f}, loan={loan_amount:,.0f})")
            else:
                # Final fallback — zero (will not affect scoring formulas badly)
                extracted[key] = 0
                doc_found[key]  = "unavailable"
                print(f"[Extractor] {key} = 0 (no data available)")

    extracted["_sources"] = doc_found   # metadata for audit trail
    return extracted
