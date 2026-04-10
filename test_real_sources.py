"""Quick test of all three real data source scrapers."""
from services.data_sources import get_news_data, get_corporate_data, get_litigation_data

ENTITY = "Tata Motors"

print("=" * 60)
print(f"Testing real data sources for: {ENTITY}")
print("=" * 60)

# 1. News
print("\n[1] NEWS SENTIMENT")
r1 = get_news_data(ENTITY)
print(f"  Source:    {r1['source_used']}")
print(f"  Sentiment: {r1['data'].get('sentiment', 'N/A')}")
signals = r1['data'].get('signals', {})
print(f"  VADER avg: {signals.get('avg_vader_score', 'N/A')}")
print(f"  Headlines: {signals.get('recent_mentions', 0)}")
for h in signals.get('sample_headlines', []):
    print(f"    - {h[:80]}")
print(f"  Failures:  {len(r1['failures'])}")

# 2. Corporate
print("\n[2] CORPORATE / PROMOTER DATA")
r2 = get_corporate_data(ENTITY)
print(f"  Source:    {r2['source_used']}")
pi = r2['data'].get('promoter_intel', {})
print(f"  Company:   {pi.get('company_name', pi.get('key_promoters', 'N/A'))}")
print(f"  CIN:       {pi.get('cin', 'N/A')}")
print(f"  Status:    {pi.get('status', 'N/A')}")
print(f"  Pledged%:  {pi.get('pledged_shares_pct', 'N/A')}")
print(f"  Directors: {pi.get('key_promoters', [])}")
print(f"  Failures:  {len(r2['failures'])}")

# 3. Litigation
print("\n[3] LITIGATION / LEGAL DATA")
r3 = get_litigation_data(ENTITY)
print(f"  Source:    {r3['source_used']}")
cases = r3['data'].get('cases', [])
flags = r3['data'].get('regulatory_flags', [])
print(f"  Cases:     {len(cases)}")
print(f"  Reg Flags: {len(flags)}")
for c in cases[:3]:
    print(f"    - [{c.get('type', '?')}] {c.get('title', '?')[:70]}")
for f in flags[:3]:
    print(f"    ! {f}")
print(f"  Failures:  {len(r3['failures'])}")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)
