"""
Generate ~350 additional realistic Indian company entries to expand the ML dataset.
Produces valid CIN and PAN numbers following actual Indian government formats.
"""
import random
import string
import pandas as pd
import os

# ── Indian CIN Format: L/U + 5-digit NIC + 2-char State + 4-digit Year + 3-char CompanyType + 6-digit Serial
# Example: L65920MH1994PLC080618

STATES = ['AN','AP','AR','AS','BR','CG','CH','DD','DL','DN','GA','GJ','HP','HR','JH',
          'JK','KA','KL','LA','LD','MH','ML','MN','MP','MZ','NL','OD','PB','PY','RJ',
          'SK','TN','TR','TS','UK','UP','WB']

COMPANY_TYPES = ['PLC','PVT','FTC','OPC','NPL','GAP']

# PAN Format: 3 letters + entity type + 1 letter + 4 digits + 1 letter
# Entity types: P=Person, C=Company, H=HUF, A=AOP, B=BOI, F=Firm, T=Trust, L=Local, J=AJP, G=Govt
PAN_ENTITIES = ['C', 'A', 'F', 'T', 'H']  # For companies mostly C

# ── NIC codes (National Industrial Classification) used in CIN
NIC_CODES = {
    'Banking & Financial Services': ['65920','65191','64200','65110','64190','65100','64910','65210'],
    'IT & Technology':             ['62011','62020','62090','63111','58200','62012','63120','62091'],
    'Automotive':                  ['29101','29102','29200','29300','30100','30400','29103','29201'],
    'Pharmaceuticals':             ['21001','21002','21003','21009','46460','21004','21005','21006'],
    'Oil & Gas / Energy':          ['06100','06200','35101','35102','19100','35103','35201','19201'],
    'Telecom':                     ['61100','61200','61300','61900','26300','61400','26301','61201'],
    'Steel & Metals':              ['24101','24102','24200','24310','07100','24103','24201','24311'],
    'FMCG':                        ['10501','10502','10610','20231','20232','10601','10503','20233'],
    'Consumer & Retail':           ['47110','47190','47300','47410','47610','47111','47191','47301'],
    'Healthcare':                  ['86101','86102','86200','86900','32501','86103','86201','86901'],
    'Infrastructure & Logistics':  ['42110','42120','42210','49100','49200','42111','42121','49101'],
    'Insurance':                   ['65120','65200','65201','66120','66210','65121','65202','66121'],
    'Real Estate':                 ['41001','41002','68100','68200','41009','41003','68101','68201'],
    'Cement & Construction':       ['23941','23942','43210','43220','43290','23943','43211','43221'],
    'Chemicals':                   ['20110','20120','20130','20210','20220','20111','20121','20131'],
    'Media & Entertainment':       ['59110','59120','59130','59200','60100','59111','59121','59131'],
    'Aviation':                    ['51101','51102','51200','30300','33160','51103','51201','30301'],
    'Diversified Conglomerate':    ['70100','70200','46900','47190','64200','70101','70201','46901'],
    'Agri & Food Processing':      ['01110','01120','10100','10200','10300','01111','01121','10101'],
    'Capital Goods':               ['28110','28120','28130','28200','28210','28111','28121','28131'],
    'NBFC / Fintech':              ['64920','64990','66190','66290','64300','64921','64991','66191'],
}

# ── Company name templates per sector
COMPANY_NAMES = {
    'Banking & Financial Services': [
        '{city} Co-operative Bank Ltd', '{name} Financial Services Ltd', '{name} Bank Ltd',
        '{city} Urban Co-operative Bank Ltd', '{name} Gramin Bank Ltd', '{name} Rural Finance Ltd',
        '{name} Capital Finance Ltd', '{city} Microfinance Ltd', '{name} Banking Corporation Ltd',
        '{city} Credit Co-operative Society Ltd', '{name} Payment Solutions Ltd',
        '{name} Savings & Loans Ltd', '{city} Commercial Bank Ltd',
    ],
    'IT & Technology': [
        '{name} Technologies Ltd', '{name} Infotech Pvt Ltd', '{name} Software Solutions Ltd',
        '{name} Digital Services Ltd', '{name} Systems Pvt Ltd', '{name} IT Solutions Ltd',
        '{name} Cyber Systems Ltd', '{name} Tech Innovations Ltd', '{name} Cloud Solutions Ltd',
        '{name} Data Analytics Ltd', '{name} AI Technologies Ltd', '{name} Webworks Pvt Ltd',
    ],
    'Automotive': [
        '{name} Auto Components Ltd', '{name} Motors Ltd', '{name} Automotive Ltd',
        '{name} Vehicles Pvt Ltd', '{name} Auto Pvt Ltd', '{name} Engineering Motors Ltd',
        '{name} Commercial Vehicles Ltd', '{name} Auto Systems Ltd', '{name} EV Solutions Ltd',
    ],
    'Pharmaceuticals': [
        '{name} Pharma Ltd', '{name} Laboratories Ltd', '{name} Life Sciences Ltd',
        '{name} Biotech Ltd', '{name} Healthcare Pharma Ltd', '{name} Drug Manufacturing Ltd',
        '{name} Therapeutics Ltd', '{name} Pharmaceutical Industries Ltd',
    ],
    'Oil & Gas / Energy': [
        '{name} Energy Ltd', '{name} Petroleum Ltd', '{name} Power Ltd',
        '{name} Oil & Gas Ltd', '{name} Renewable Energy Ltd', '{name} Solar Power Ltd',
        '{name} Gas Distribution Ltd', '{name} Wind Energy Ltd',
    ],
    'Telecom': [
        '{name} Telecommunications Ltd', '{name} Telecom Services Ltd', '{name} Networks Ltd',
        '{name} Communications Ltd', '{name} Broadband Ltd', '{name} Wireless Solutions Ltd',
    ],
    'Steel & Metals': [
        '{name} Steel Ltd', '{name} Alloys Ltd', '{name} Metals Ltd',
        '{name} Iron & Steel Ltd', '{name} Foundry Ltd', '{name} Aluminium Ltd',
        '{name} Metal Industries Ltd', '{name} Steelworks Ltd',
    ],
    'FMCG': [
        '{name} Consumer Products Ltd', '{name} Foods Ltd', '{name} Personal Care Ltd',
        '{name} Home Products Ltd', '{name} FMCG Ltd', '{name} Nutrition Ltd',
        '{name} Essentials Ltd', '{name} Daily Needs Ltd',
    ],
    'Consumer & Retail': [
        '{name} Retail Ltd', '{name} Lifestyle Ltd', '{name} Fashion Ltd',
        '{name} Consumer Goods Ltd', '{name} Brands Ltd', '{name} Retail Stores Ltd',
        '{name} E-Commerce Ltd', '{name} Supermart Ltd',
    ],
    'Healthcare': [
        '{name} Hospitals Ltd', '{name} Medicals Ltd', '{name} Health Services Ltd',
        '{name} Medicare Ltd', '{name} Diagnostic Services Ltd', '{name} Clinics Ltd',
    ],
    'Infrastructure & Logistics': [
        '{name} Infrastructure Ltd', '{name} Logistics Ltd', '{name} Projects Ltd',
        '{name} Transport Ltd', '{name} Highways Ltd', '{name} Shipping Ltd',
        '{name} Port Services Ltd', '{name} Cargo Ltd',
    ],
    'Insurance': [
        '{name} Insurance Ltd', '{name} General Insurance Ltd', '{name} Life Insurance Ltd',
        '{name} Assurance Ltd', '{name} Reinsurance Ltd',
    ],
    'Real Estate': [
        '{name} Realty Ltd', '{name} Properties Ltd', '{name} Developers Ltd',
        '{name} Housing Ltd', '{name} Constructions Ltd', '{name} Real Estates Ltd',
    ],
    'Cement & Construction': [
        '{name} Cements Ltd', '{name} Construction Ltd', '{name} Building Materials Ltd',
        '{name} Infrastructure & Construction Ltd', '{name} Concrete Products Ltd',
    ],
    'Chemicals': [
        '{name} Chemicals Ltd', '{name} Chemical Industries Ltd', '{name} Petrochemicals Ltd',
        '{name} Specialty Chemicals Ltd', '{name} Agrochemicals Ltd',
    ],
    'Media & Entertainment': [
        '{name} Media Ltd', '{name} Entertainment Ltd', '{name} Broadcasting Ltd',
        '{name} Film Productions Ltd', '{name} Digital Media Ltd',
    ],
    'Aviation': [
        '{name} Airlines Ltd', '{name} Aviation Ltd', '{name} Air Services Ltd',
        '{name} Aerospace Ltd', '{name} Air Cargo Ltd',
    ],
    'Diversified Conglomerate': [
        '{name} Group Holdings Ltd', '{name} Enterprises Ltd', '{name} Industries Ltd',
        '{name} Conglomerate Ltd', '{name} Ventures Ltd', '{name} Holdings Ltd',
    ],
    'Agri & Food Processing': [
        '{name} Agro Industries Ltd', '{name} Foods Processing Ltd', '{name} Dairy Ltd',
        '{name} Agricultural Products Ltd', '{name} Organic Foods Ltd',
    ],
    'Capital Goods': [
        '{name} Heavy Engineering Ltd', '{name} Machinery Ltd', '{name} Equipment Ltd',
        '{name} Industrial Solutions Ltd', '{name} Manufacturing Ltd',
    ],
    'NBFC / Fintech': [
        '{name} Fintech Ltd', '{name} Finance Pvt Ltd', '{name} Lending Ltd',
        '{name} Credit Solutions Ltd', '{name} Digital Finance Ltd',
        '{name} Fincorp Ltd', '{name} Capital Pvt Ltd',
    ],
}

# Name fragments for generating unique company names
FIRST_NAMES = [
    'Aarav','Aditi','Akshay','Anand','Arjun','Ashwin','Bharat','Chandra','Devi','Dhruv',
    'Esha','Gaurav','Hari','Indra','Jai','Kiran','Lakshmi','Manish','Neel','Om',
    'Priya','Raj','Sanjay','Tarun','Uma','Vivek','Yash','Zara','Abhi','Bala',
    'Chetan','Deepak','Ekta','Farhan','Gopal','Harsh','Isha','Jatin','Kavya','Lalit',
    'Mohan','Nikhil','Paresh','Rahul','Suresh','Tanvi','Varun','Kunal','Amit','Sachin',
    'Vikram','Rohan','Neha','Pooja','Swati','Rekha','Surya','Anil','Rohit','Manoj',
    'Naveen','Siddharth','Ajay','Ravi','Krishna','Shankar','Dev','Pranav','Aditya','Karthik',
]

CITY_NAMES = [
    'Mumbai','Delhi','Bangalore','Hyderabad','Chennai','Kolkata','Pune','Ahmedabad',
    'Jaipur','Lucknow','Surat','Kanpur','Nagpur','Indore','Patna','Bhopal','Vadodara',
    'Coimbatore','Thiruvananthapuram','Gurgaon','Noida','Chandigarh','Kochi','Visakhapatnam',
    'Mysore','Rajkot','Jodhpur','Udaipur','Nashik','Ludhiana','Amritsar','Agra',
]

used_cins = set()
used_pans = set()
used_names = set()

def generate_cin(sector, state=None, listing=None):
    """Generate a valid-format Indian CIN number."""
    while True:
        l_u = listing if listing else random.choice(['L','U','U','U'])  # More unlisted
        nic = random.choice(NIC_CODES.get(sector, ['99999']))
        st = state if state else random.choice(STATES)
        year = random.randint(1985, 2023)
        ctype = random.choice(COMPANY_TYPES)
        serial = random.randint(100000, 999999)
        cin = f"{l_u}{nic}{st}{year}{ctype}{serial:06d}"
        if cin not in used_cins:
            used_cins.add(cin)
            return cin

def generate_pan():
    """Generate a valid-format Indian PAN number."""
    while True:
        first3 = ''.join(random.choices(string.ascii_uppercase, k=3))
        entity = random.choice(PAN_ENTITIES)
        mid = random.choice(string.ascii_uppercase)
        digits = random.randint(1000, 9999)
        last = random.choice(string.ascii_uppercase)
        pan = f"{first3}{entity}{mid}{digits}{last}"
        if pan not in used_pans:
            used_pans.add(pan)
            return pan

def generate_company_name(sector):
    """Generate a unique company name for the given sector."""
    templates = COMPANY_NAMES.get(sector, ['{name} Industries Ltd'])
    for _ in range(100):
        template = random.choice(templates)
        name = random.choice(FIRST_NAMES)
        city = random.choice(CITY_NAMES)
        company = template.format(name=name, city=city)
        if company not in used_names:
            used_names.add(company)
            return company
    # Ultimate fallback
    suffix = random.randint(100, 999)
    company = f"{random.choice(FIRST_NAMES)} {sector.split()[0]} {suffix} Ltd"
    used_names.add(company)
    return company


def main():
    sectors = list(NIC_CODES.keys())
    
    # Load existing dataset
    existing_path = r"D:/clg projects/New folder/indian_companies_dataset.xlsx"
    if os.path.exists(existing_path):
        existing_df = pd.read_excel(existing_path)
        existing_df.columns = existing_df.columns.str.strip()
        print(f"Loaded existing dataset: {len(existing_df)} companies")
        # Mark existing CINs and PANs to avoid duplicates
        for cin in existing_df["CIN Number"].dropna():
            used_cins.add(str(cin).strip().upper())
        for pan in existing_df["PAN Number"].dropna():
            used_pans.add(str(pan).strip().upper())
        for name in existing_df["Company Name"].dropna():
            used_names.add(str(name).strip())
    else:
        existing_df = pd.DataFrame()
        print("No existing dataset found, creating from scratch")

    # Target: ~500 total → need ~350 new
    target_new = 500 - len(existing_df)
    if target_new <= 0:
        print("Already have 500+ entries!")
        return

    # Distribute across sectors (ensure each sector gets enough entries)
    per_sector_base = target_new // len(sectors)
    remainder = target_new % len(sectors)

    new_entries = []
    for i, sector in enumerate(sectors):
        count = per_sector_base + (1 if i < remainder else 0)
        for _ in range(count):
            # Pick a random state (weighted towards major business states)
            major_states = ['MH','DL','KA','TN','GJ','HR','UP','AP','TS','WB','RJ','PB','KL']
            state = random.choice(major_states + STATES)  # Double chance for major states
            
            entry = {
                'Company Name': generate_company_name(sector),
                'CIN Number': generate_cin(sector, state),
                'PAN Number': generate_pan(),
                'Sector': sector,
            }
            new_entries.append(entry)

    new_df = pd.DataFrame(new_entries)
    
    # Merge with existing
    if not existing_df.empty:
        # Keep only the 4 core columns (drop S.No or any extras)
        core_cols = ['Company Name', 'CIN Number', 'PAN Number', 'Sector']
        existing_core = existing_df[core_cols].copy()
        combined_df = pd.concat([existing_core, new_df], ignore_index=True)
    else:
        combined_df = new_df

    # Save
    output_path = r"D:/clg projects/New folder/indian_companies_dataset.xlsx"
    combined_df.to_excel(output_path, index=False)
    
    print(f"\n{'='*60}")
    print(f"Dataset Generation Complete!")
    print(f"{'='*60}")
    print(f"  Existing entries:  {len(existing_df)}")
    print(f"  New entries:       {len(new_entries)}")
    print(f"  Total entries:     {len(combined_df)}")
    print(f"  Sectors covered:   {combined_df['Sector'].nunique()}")
    print(f"  Saved to: {output_path}")
    print(f"\nSector distribution:")
    for sector, count in combined_df['Sector'].value_counts().sort_index().items():
        print(f"    {sector}: {count}")


if __name__ == "__main__":
    main()
