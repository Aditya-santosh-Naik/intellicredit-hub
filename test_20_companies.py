"""
Comprehensive Test Suite: 20 real Indian companies through ALL systems.
Tests: Web Scrapers (News, Corporate, Litigation) + ML Verification.
"""
import json
import time
import sys
import os

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

from services.data_sources import get_news_data, get_corporate_data, get_litigation_data

# ── 20 Real Indian Companies to Test ──────────────────────────────────────────
TEST_COMPANIES = [
    "Reliance Industries",
    "Tata Consultancy Services",
    "Infosys",
    "HDFC Bank",
    "ICICI Bank",
    "Wipro",
    "Bharti Airtel",
    "State Bank of India",
    "Hindustan Unilever",
    "ITC Limited",
    "Larsen & Toubro",
    "Bajaj Finance",
    "Maruti Suzuki",
    "Asian Paints",
    "Sun Pharmaceutical",
    "Adani Enterprises",
    "Mahindra & Mahindra",
    "HCL Technologies",
    "Axis Bank",
    "UltraTech Cement",
]


def test_news_sentiment(companies):
    """Test GNews + VADER sentiment for all companies."""
    print("\n" + "=" * 70)
    print("  PHASE 1: NEWS SENTIMENT ANALYSIS (GNews + VADER)")
    print("=" * 70)

    results = []
    success = 0
    for i, company in enumerate(companies, 1):
        print(f"\n  [{i:02d}/20] {company}...", end=" ", flush=True)
        try:
            start = time.time()
            r = get_news_data(company)
            elapsed = time.time() - start

            sentiment = r['data'].get('sentiment', 'N/A')
            source = r['source_used']
            vader_score = r['data'].get('signals', {}).get('avg_vader_score', 'N/A')
            headlines = r['data'].get('signals', {}).get('recent_mentions', 0)

            results.append({
                "company": company, "sentiment": sentiment,
                "vader_score": vader_score, "headlines": headlines,
                "source": source, "time_s": round(elapsed, 1), "status": "OK"
            })
            success += 1
            print(f"{sentiment} (VADER: {vader_score}, {headlines} headlines, {elapsed:.1f}s) [{source}]")

        except Exception as e:
            results.append({"company": company, "status": "FAILED", "error": str(e)})
            print(f"FAILED: {e}")

        # Small delay to avoid rate limits
        time.sleep(1)

    print(f"\n  News Sentiment: {success}/20 successful")
    return results


def test_corporate_data(companies):
    """Test corporate data scraping for all companies."""
    print("\n" + "=" * 70)
    print("  PHASE 2: CORPORATE / PROMOTER DATA")
    print("=" * 70)

    results = []
    success = 0
    for i, company in enumerate(companies, 1):
        print(f"\n  [{i:02d}/20] {company}...", end=" ", flush=True)
        try:
            start = time.time()
            r = get_corporate_data(company)
            elapsed = time.time() - start

            source = r['source_used']
            pi = r['data'].get('promoter_intel', {})
            name = pi.get('company_name', 'N/A')
            pledged = pi.get('pledged_shares_pct', 'N/A')

            results.append({
                "company": company, "found_name": name,
                "pledged_pct": pledged, "source": source,
                "time_s": round(elapsed, 1), "status": "OK"
            })
            success += 1
            print(f"Found: '{name}' (Pledged: {pledged}%, {elapsed:.1f}s) [{source}]")

        except Exception as e:
            results.append({"company": company, "status": "FAILED", "error": str(e)})
            print(f"FAILED: {e}")

        time.sleep(0.5)

    print(f"\n  Corporate Data: {success}/20 successful")
    return results


def test_litigation_data(companies):
    """Test litigation data scraping for all companies."""
    print("\n" + "=" * 70)
    print("  PHASE 3: LITIGATION / LEGAL DATA (Indian Kanoon)")
    print("=" * 70)

    results = []
    success = 0
    for i, company in enumerate(companies, 1):
        print(f"\n  [{i:02d}/20] {company}...", end=" ", flush=True)
        try:
            start = time.time()
            r = get_litigation_data(company)
            elapsed = time.time() - start

            source = r['source_used']
            cases = r['data'].get('cases', [])
            total = r['data'].get('total_found', 0)
            flags = r['data'].get('regulatory_flags', [])

            results.append({
                "company": company, "cases_displayed": len(cases),
                "total_found": total, "reg_flags": len(flags),
                "source": source, "time_s": round(elapsed, 1), "status": "OK"
            })
            success += 1
            print(f"{total:,} total cases, {len(flags)} regulatory flags ({elapsed:.1f}s) [{source}]")

        except Exception as e:
            results.append({"company": company, "status": "FAILED", "error": str(e)})
            print(f"FAILED: {e}")

        time.sleep(0.5)

    print(f"\n  Litigation Data: {success}/20 successful")
    return results


def test_ml_verification():
    """Test ML model verification with sample lookups."""
    print("\n" + "=" * 70)
    print("  PHASE 4: ML MODEL VERIFICATION")
    print("=" * 70)

    # Load the retrained model artifacts
    ml_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml_model")

    with open(os.path.join(ml_dir, "company_db.json"), "r") as f:
        db = json.load(f)

    with open(os.path.join(ml_dir, "model_metadata.json"), "r") as f:
        meta = json.load(f)

    print(f"\n  Model Stats:")
    print(f"    Companies in DB:    {meta['n_companies']}")
    print(f"    Sectors:            {meta['n_sectors']}")
    print(f"    Features:           {meta['n_features']}")
    print(f"    RF LOO Accuracy:    {meta['rf_loo_acc']*100:.1f}%")
    print(f"    RF In-sample Acc:   {meta['rf_in_sample']*100:.1f}%")
    print(f"    Anomalies Flagged:  {meta['n_anom']}")

    # Test random lookups from the DB
    all_companies = db.get("all", [])
    test_samples = all_companies[:10] + all_companies[-10:]  # First 10 + last 10

    success = 0
    total = len(test_samples)
    
    print(f"\n  Testing {total} lookup verifications:")
    for rec in test_samples:
        cin = rec.get("cin", "")
        pan = rec.get("pan", "")
        name = rec.get("company", "")

        # Test CIN lookup
        found_by_cin = db["by_cin"].get(cin)
        # Test PAN lookup
        found_by_pan = db["by_pan"].get(pan)

        cin_ok = found_by_cin is not None and found_by_cin.get("company") == name
        pan_ok = found_by_pan is not None and found_by_pan.get("company") == name

        if cin_ok and pan_ok:
            success += 1
            status = "PASS"
        elif cin_ok or pan_ok:
            success += 1
            status = "PARTIAL"
        else:
            status = "FAIL"

        print(f"    [{status}] {name[:40]:40s}  CIN:{cin[:10]}...  PAN:{pan}")

    print(f"\n  ML Verification: {success}/{total} lookups passed")
    return {"total": total, "passed": success}


def main():
    print("=" * 70)
    print("  INTELLICREDIT COMPREHENSIVE TEST SUITE")
    print("  20 Real Indian Companies x 3 Scrapers + ML Verification")
    print("=" * 70)

    # Phase 1: News
    news_results = test_news_sentiment(TEST_COMPANIES)

    # Phase 2: Corporate
    corp_results = test_corporate_data(TEST_COMPANIES)

    # Phase 3: Litigation
    lit_results = test_litigation_data(TEST_COMPANIES)

    # Phase 4: ML
    ml_results = test_ml_verification()

    # ── Summary ──
    print("\n\n" + "=" * 70)
    print("  FINAL SUMMARY")
    print("=" * 70)

    news_ok = sum(1 for r in news_results if r.get("status") == "OK")
    corp_ok = sum(1 for r in corp_results if r.get("status") == "OK")
    lit_ok = sum(1 for r in lit_results if r.get("status") == "OK")
    ml_ok = ml_results["passed"]

    print(f"\n  {'System':<35} {'Pass':<8} {'Total':<8} {'Rate'}")
    print(f"  {'-'*65}")
    print(f"  {'News Sentiment (GNews+VADER)':<35} {news_ok:<8} {'20':<8} {news_ok/20*100:.0f}%")
    print(f"  {'Corporate Data (Scraper)':<35} {corp_ok:<8} {'20':<8} {corp_ok/20*100:.0f}%")
    print(f"  {'Litigation Data (Indian Kanoon)':<35} {lit_ok:<8} {'20':<8} {lit_ok/20*100:.0f}%")
    print(f"  {'ML Verification (Lookup DB)':<35} {ml_ok:<8} {ml_results['total']:<8} {ml_ok/ml_results['total']*100:.0f}%")
    print(f"  {'-'*65}")
    total_pass = news_ok + corp_ok + lit_ok + ml_ok
    total_all = 20 + 20 + 20 + ml_results['total']
    print(f"  {'OVERALL':<35} {total_pass:<8} {total_all:<8} {total_pass/total_all*100:.0f}%")

    # Save detailed results
    report = {
        "news": news_results,
        "corporate": corp_results,
        "litigation": lit_results,
        "ml": ml_results,
        "summary": {
            "news_pass": news_ok, "corp_pass": corp_ok,
            "lit_pass": lit_ok, "ml_pass": ml_ok,
            "total_pass": total_pass, "total_tests": total_all,
        }
    }
    with open("test_results_20_companies.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n  Detailed results saved to: test_results_20_companies.json")
    print("=" * 70)


if __name__ == "__main__":
    main()
