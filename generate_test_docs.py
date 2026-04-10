import pandas as pd
import os

docs = {
    'test_alm.xlsx': ['Asset Liability Management', 'ALM gap', 'Liquidity Risk'],
    'test_shareholding.xlsx': ['Shareholding Pattern', 'Promoter Holding', 'Equity Shares'],
    'test_borrowing.xlsx': ['Lender', 'Outstanding Debt', 'Credit Facility', 'Term Loan'],
    'test_annual.xlsx': ['Balance Sheet', 'Profit and Loss', 'Annual Report'],
    'test_portfolio.xlsx': ['NPA', 'DPD', 'Portfolio Aging', 'Gross NPA']
}

for filename, keywords in docs.items():
    df = pd.DataFrame({'Data': keywords})
    df.to_excel(filename, index=False)
    print(f"Created {filename}")
