import logging
import re
import requests
from bs4 import BeautifulSoup
from utils.http_client import fetch_with_resilience, ResilientClientError

logger = logging.getLogger(__name__)

# ── NLTK / VADER setup ──────────────────────────────────────────────────────
try:
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()
except Exception:
    _vader = None
    logger.warning("VADER sentiment analyzer not available. Install nltk + download vader_lexicon.")

# ── GNews setup ──────────────────────────────────────────────────────────────
try:
    from gnews import GNews
except ImportError:
    GNews = None
    logger.warning("gnews package not installed.")

# Mock Base URL — used as the FINAL fallback if all real sources fail
MOCK_BASE_URL = "http://127.0.0.1:5000/mock"

# Shared headers to mimic a browser (avoids 403 blocks on scraping sites)
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


# ═══════════════════════════════════════════════════════════════════════════════
# 1.  NEWS SENTIMENT
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_news_gnews(entity_name):
    """
    Primary: Use the gnews package to fetch recent headlines, then score
    sentiment with VADER.  Returns {"sentiment": str, "signals": dict}.
    """
    if GNews is None or _vader is None:
        raise RuntimeError("gnews or VADER not available")

    gn = GNews(language='en', country='IN', max_results=10)
    articles = gn.get_news(entity_name)

    if not articles:
        raise RuntimeError(f"GNews returned 0 articles for '{entity_name}'")

    headlines = [a.get("title", "") for a in articles if a.get("title")]

    if not headlines:
        raise RuntimeError("GNews returned articles with no titles")

    # Score every headline with VADER
    scores = [_vader.polarity_scores(h)["compound"] for h in headlines]
    avg_score = sum(scores) / len(scores)

    if avg_score > 0.05:
        sentiment = "Positive"
        trend = "upward"
    elif avg_score < -0.05:
        sentiment = "Negative"
        trend = "downward"
    else:
        sentiment = "Neutral"
        trend = "stable"

    return {
        "sentiment": sentiment,
        "signals": {
            "trend": trend,
            "recent_mentions": len(headlines),
            "avg_vader_score": round(avg_score, 3),
            "sample_headlines": headlines[:3],
        }
    }


def _fetch_news_google_rss(entity_name):
    """
    Fallback: Scrape Google News RSS feed directly (no library needed).
    """
    if _vader is None:
        raise RuntimeError("VADER not available for sentiment scoring")

    url = f"https://news.google.com/rss/search?q={requests.utils.quote(entity_name)}&hl=en-IN&gl=IN&ceid=IN:en"
    resp = requests.get(url, headers=_HEADERS, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.content, "lxml-xml")
    items = soup.find_all("item", limit=10)

    if not items:
        raise RuntimeError("Google RSS returned 0 items")

    headlines = [item.find("title").text for item in items if item.find("title")]

    scores = [_vader.polarity_scores(h)["compound"] for h in headlines]
    avg_score = sum(scores) / len(scores) if scores else 0

    if avg_score > 0.05:
        sentiment = "Positive"
        trend = "upward"
    elif avg_score < -0.05:
        sentiment = "Negative"
        trend = "downward"
    else:
        sentiment = "Neutral"
        trend = "stable"

    return {
        "sentiment": sentiment,
        "signals": {
            "trend": trend,
            "recent_mentions": len(headlines),
            "avg_vader_score": round(avg_score, 3),
            "sample_headlines": headlines[:3],
        }
    }


def get_news_data(entity_name):
    """
    Waterfall:  GNews package  →  Google News RSS  →  Mock API
    """
    failures = []

    # ── Primary: GNews ──
    try:
        logger.info(f"[News] Trying GNews for '{entity_name}'")
        data = _fetch_news_gnews(entity_name)
        logger.info("[News] GNews succeeded")
        return {"data": data, "source_used": "GNews + VADER Sentiment", "failures": failures}
    except Exception as e:
        logger.warning(f"[News] GNews failed: {e}")
        failures.append({"source": "GNews + VADER Sentiment", "error": str(e)})

    # ── Fallback 1: Google News RSS ──
    try:
        logger.info(f"[News] Trying Google News RSS for '{entity_name}'")
        data = _fetch_news_google_rss(entity_name)
        logger.info("[News] Google News RSS succeeded")
        return {"data": data, "source_used": "Google News RSS + VADER", "failures": failures}
    except Exception as e:
        logger.warning(f"[News] Google News RSS failed: {e}")
        failures.append({"source": "Google News RSS + VADER", "error": str(e)})

    # ── Final Fallback: Mock API ──
    try:
        logger.info("[News] Falling back to Mock API")
        mock_sources = [
            {"name": "Mock News (Bing)",   "url": f"{MOCK_BASE_URL}/news/bing?entity={entity_name}"},
            {"name": "Mock News (Scrape)", "url": f"{MOCK_BASE_URL}/news/scrape?entity={entity_name}"},
        ]
        return _execute_mock_waterfall(mock_sources, "News Data (Mock Fallback)", failures)
    except Exception as e:
        failures.append({"source": "Mock News Fallback", "error": str(e)})

    return {"data": {}, "source_used": "None", "failures": failures}


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  CORPORATE / PROMOTER DATA
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_corporate_zaubacorp(entity_name):
    """
    Primary: Scrape Zaubacorp.com for company details —
    directors, CIN, charges, compliance status.
    """
    search_url = f"https://www.zaubacorp.com/company-list/company-{requests.utils.quote(entity_name)}.html"
    resp = requests.get(search_url, headers=_HEADERS, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.content, "lxml")

    # Find the first company link in the search results table
    result_table = soup.find("table", {"id": "table"})
    if not result_table:
        raise RuntimeError("No company results table found on Zaubacorp")

    rows = result_table.find_all("tr")[1:]  # skip header
    if not rows:
        raise RuntimeError(f"No companies found for '{entity_name}' on Zaubacorp")

    # Parse first match
    first_row = rows[0]
    cols = first_row.find_all("td")
    company_name = cols[0].text.strip() if len(cols) > 0 else entity_name
    cin = cols[1].text.strip() if len(cols) > 1 else "N/A"
    status = cols[2].text.strip() if len(cols) > 2 else "Unknown"

    # Try to get director info from the detail page
    directors = []
    detail_link = first_row.find("a")
    if detail_link and detail_link.get("href"):
        try:
            detail_url = detail_link["href"]
            if not detail_url.startswith("http"):
                detail_url = "https://www.zaubacorp.com" + detail_url
            detail_resp = requests.get(detail_url, headers=_HEADERS, timeout=10)
            detail_soup = BeautifulSoup(detail_resp.content, "lxml")

            # Look for director names in the page
            director_section = detail_soup.find_all("table")
            for tbl in director_section:
                header = tbl.find("th")
                if header and "director" in header.text.lower():
                    for row in tbl.find_all("tr")[1:5]:  # max 4 directors
                        tds = row.find_all("td")
                        if tds:
                            directors.append(tds[0].text.strip())
                    break
        except Exception as e:
            logger.warning(f"[Corporate] Could not fetch director details: {e}")

    return {
        "promoter_intel": {
            "company_name": company_name,
            "cin": cin,
            "status": status,
            "key_promoters": directors if directors else ["Data not available"],
            "pledged_shares_pct": 0.0,  # Zaubacorp doesn't provide pledging data
        }
    }


def _fetch_corporate_screener(entity_name):
    """
    Fallback: Scrape screener.in for basic company info and shareholding.
    """
    search_url = f"https://www.screener.in/api/company/search/?q={requests.utils.quote(entity_name)}"
    resp = requests.get(search_url, headers=_HEADERS, timeout=10)
    resp.raise_for_status()

    results = resp.json()
    if not results:
        raise RuntimeError(f"Screener found no results for '{entity_name}'")

    # Get the first match
    first = results[0]
    company_name = first.get("name", entity_name)
    company_url = first.get("url", "")

    promoter_intel = {
        "company_name": company_name,
        "key_promoters": ["Data from Screener.in"],
        "pledged_shares_pct": 0.0,
    }

    # Try to get shareholding from the company page
    if company_url:
        try:
            full_url = f"https://www.screener.in{company_url}"
            page_resp = requests.get(full_url, headers=_HEADERS, timeout=10)
            page_soup = BeautifulSoup(page_resp.content, "lxml")

            # Look for shareholding section
            shp_section = page_soup.find("div", {"id": "shareholding"})
            if shp_section:
                rows = shp_section.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if cells and "promoter" in cells[0].text.lower():
                        # Last cell is most recent quarter
                        pct_text = cells[-1].text.strip().replace("%", "")
                        try:
                            promoter_intel["promoter_holding_pct"] = float(pct_text)
                        except ValueError:
                            pass
                        break
        except Exception as e:
            logger.warning(f"[Corporate] Screener detail page failed: {e}")

    return {"promoter_intel": promoter_intel}


def get_corporate_data(entity_name):
    """
    Waterfall:  Zaubacorp  →  Screener.in  →  Mock API
    """
    failures = []

    # ── Primary: Zaubacorp ──
    try:
        logger.info(f"[Corporate] Trying Zaubacorp for '{entity_name}'")
        data = _fetch_corporate_zaubacorp(entity_name)
        logger.info("[Corporate] Zaubacorp succeeded")
        return {"data": data, "source_used": "Zaubacorp (MCA Registry Scraper)", "failures": failures}
    except Exception as e:
        logger.warning(f"[Corporate] Zaubacorp failed: {e}")
        failures.append({"source": "Zaubacorp (MCA Registry Scraper)", "error": str(e)})

    # ── Fallback 1: Screener.in ──
    try:
        logger.info(f"[Corporate] Trying Screener.in for '{entity_name}'")
        data = _fetch_corporate_screener(entity_name)
        logger.info("[Corporate] Screener.in succeeded")
        return {"data": data, "source_used": "Screener.in (Financial Data Scraper)", "failures": failures}
    except Exception as e:
        logger.warning(f"[Corporate] Screener.in failed: {e}")
        failures.append({"source": "Screener.in (Financial Data Scraper)", "error": str(e)})

    # ── Final Fallback: Mock API ──
    try:
        logger.info("[Corporate] Falling back to Mock API")
        mock_sources = [
            {"name": "Mock MCA",     "url": f"{MOCK_BASE_URL}/mca?entity={entity_name}"},
            {"name": "Mock Filings", "url": f"{MOCK_BASE_URL}/filings?entity={entity_name}"},
        ]
        return _execute_mock_waterfall(mock_sources, "Corporate Data (Mock Fallback)", failures)
    except Exception as e:
        failures.append({"source": "Mock Corporate Fallback", "error": str(e)})

    return {"data": {}, "source_used": "None", "failures": failures}


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  LITIGATION / LEGAL DATA
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_litigation_indiankanoon(entity_name):
    """
    Primary: Scrape Indian Kanoon search results for the entity name.
    Returns case count, case titles, and court names.
    Indian Kanoon uses /docfragment/ links inside a div.results-list container.
    """
    search_url = f"https://indiankanoon.org/search/?formInput={requests.utils.quote(entity_name)}"
    resp = requests.get(search_url, headers=_HEADERS, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.content, "lxml")

    cases = []
    regulatory_flags = []

    # Indian Kanoon puts case links as <a href="/docfragment/ID/?formInput=...">Title</a>
    case_links = soup.find_all("a", href=lambda h: h and "/docfragment/" in h)

    if not case_links:
        # Try total count from results header (e.g. "1 - 10 of 89881")
        results_header = soup.find("div", class_="results-header")
        header_text = results_header.get_text() if results_header else ""
        logger.info(f"[Litigation] No docfragment links found. Header: {header_text[:80]}")
        return {"cases": [], "regulatory_flags": [], "total_found": 0}

    # Also try to extract total count from "1 - 10 of NNNNN" text
    total_found = len(case_links)
    results_header = soup.find("div", class_="results-header")
    if results_header:
        header_text = results_header.get_text()
        count_match = re.search(r"of\s+([\d,]+)", header_text)
        if count_match:
            total_found = int(count_match.group(1).replace(",", ""))

    for link in case_links[:10]:  # Limit to 10 results
        title = link.text.strip()
        if not title or len(title) < 5:
            continue

        # Extract doc ID from href like /docfragment/1070490/?formInput=...
        href = link.get("href", "")
        doc_id_match = re.search(r"/docfragment/(\d+)/", href)
        case_id = doc_id_match.group(1) if doc_id_match else "N/A"

        # Try to find court name: Indian Kanoon often includes court in the
        # parent element or as a sibling span with class doc_author
        parent = link.find_parent()
        court = "Indian Court"
        if parent:
            author_span = parent.find_next_sibling("span", class_="doc_author")
            if not author_span:
                author_span = parent.find("span", class_="doc_author")
            if author_span:
                court = author_span.text.strip()[:60]
            else:
                # Extract court from title patterns like "... on 2 January, 2019"
                # The court is typically mentioned before "on DATE"
                title_parts = title.split(" vs ")
                if len(title_parts) > 1:
                    court = "Mentioned in case title"

        # Detect case type from title keywords
        title_lower = title.lower()
        if any(kw in title_lower for kw in ["criminal", "fraud", "cheat", "money laundering"]):
            case_type = "Criminal"
        elif any(kw in title_lower for kw in ["winding up", "insolvency", "nclt", "liquidation"]):
            case_type = "Insolvency"
        elif any(kw in title_lower for kw in ["sebi", "rbi", "regulatory", "penalty"]):
            case_type = "Regulatory"
            regulatory_flags.append(f"Regulatory case: {title[:80]}")
        elif any(kw in title_lower for kw in ["tax", "income tax", "excise", "customs", "gst"]):
            case_type = "Tax"
        else:
            case_type = "Civil"

        cases.append({
            "case_id": case_id,
            "title": title[:120],
            "court": court,
            "type": case_type,
            "status": "Found in records"
        })

    return {
        "cases": cases,
        "regulatory_flags": regulatory_flags,
        "total_found": total_found
    }


def _fetch_litigation_google_search(entity_name):
    """
    Fallback: Search Google for litigation news about the entity.
    Uses Google's public search results page.
    """
    query = f"{entity_name} lawsuit court case India"
    search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=5"
    resp = requests.get(search_url, headers=_HEADERS, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.content, "lxml")

    # Extract search result titles
    results = soup.find_all("h3")
    cases = []
    regulatory_flags = []

    for h3 in results[:5]:
        title = h3.text.strip()
        if not title:
            continue

        title_lower = title.lower()
        if any(kw in title_lower for kw in ["sebi", "rbi", "penalty", "regulatory"]):
            regulatory_flags.append(f"Regulatory mention: {title[:80]}")

        cases.append({
            "case_id": f"G-{len(cases)+1}",
            "title": title[:120],
            "court": "Via Google Search",
            "type": "Reference",
            "status": "News reference"
        })

    return {
        "cases": cases,
        "regulatory_flags": regulatory_flags,
        "total_found": len(cases)
    }


def get_litigation_data(entity_name):
    """
    Waterfall:  Indian Kanoon  →  Google Search  →  Mock API
    """
    failures = []

    # ── Primary: Indian Kanoon ──
    try:
        logger.info(f"[Litigation] Trying Indian Kanoon for '{entity_name}'")
        data = _fetch_litigation_indiankanoon(entity_name)
        logger.info(f"[Litigation] Indian Kanoon succeeded — {data.get('total_found', 0)} cases found")
        return {"data": data, "source_used": "Indian Kanoon (Court Records Scraper)", "failures": failures}
    except Exception as e:
        logger.warning(f"[Litigation] Indian Kanoon failed: {e}")
        failures.append({"source": "Indian Kanoon (Court Records Scraper)", "error": str(e)})

    # ── Fallback 1: Google Search ──
    try:
        logger.info(f"[Litigation] Trying Google Search for '{entity_name}'")
        data = _fetch_litigation_google_search(entity_name)
        logger.info("[Litigation] Google Search succeeded")
        return {"data": data, "source_used": "Google Search (Litigation News)", "failures": failures}
    except Exception as e:
        logger.warning(f"[Litigation] Google Search failed: {e}")
        failures.append({"source": "Google Search (Litigation News)", "error": str(e)})

    # ── Final Fallback: Mock API ──
    try:
        logger.info("[Litigation] Falling back to Mock API")
        mock_sources = [
            {"name": "Mock eCourts",  "url": f"{MOCK_BASE_URL}/ecourts?entity={entity_name}"},
            {"name": "Mock LegalDB",  "url": f"{MOCK_BASE_URL}/legaldb?entity={entity_name}"},
        ]
        return _execute_mock_waterfall(mock_sources, "Litigation Data (Mock Fallback)", failures)
    except Exception as e:
        failures.append({"source": "Mock Litigation Fallback", "error": str(e)})

    return {"data": {}, "source_used": "None", "failures": failures}


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK WATERFALL HELPER (reused by all 3 categories as final fallback)
# ═══════════════════════════════════════════════════════════════════════════════

def _execute_mock_waterfall(sources_list, domain_name, existing_failures=None):
    """
    Executes an API call using a waterfall fallback strategy against mock endpoints.
    Returns: {"data": dict, "source_used": str, "failures": list}
    """
    failures = existing_failures if existing_failures is not None else []

    for source in sources_list:
        logger.info(f"Attempting mock source: {source['name']} for {domain_name}")
        try:
            data = fetch_with_resilience(url=source['url'])
            logger.info(f"Success using {source['name']}")
            return {
                "data": data,
                "source_used": source['name'],
                "failures": failures
            }
        except ResilientClientError as e:
            logger.error(f"Mock source {source['name']} failed: {e}")
            failures.append({"source": source['name'], "error": str(e)})

    logger.critical(f"ALL sources failed for {domain_name}. Returning empty dataset.")
    return {
        "data": {},
        "source_used": "None",
        "failures": failures
    }
