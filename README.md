# OFTW Dashboard

A Plotly Dash dashboard for One for the World (OFTW) that visualizes key metrics and performance indicators.

## Features

- Overview of OFTW metrics
- Analysis Methodology
- Objective & Key Results
- Money Moved Analysis
- Pledge Performance Tracking

## Setup

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Dashboard

1. Ensure all CSV files are in their correct locations:
   - Pledge data: `CSV/Pledge.csv`
   - Payments data: `CSV/Payments.csv`
   - Exchange rate data in `ExchangeRate_CSV/` directory

2. Run the dashboard:
```bash
python OFTWDashboard.py
```

3. Open your browser and navigate to:
```
http://127.0.0.1:8050/
```

## Directory Structure

```
.
├── CSV/
│   ├── Pledge.csv
│   └── Payments.csv
├── ExchangeRate_CSV/
│   ├── DEXUSUK_exchange_rates.csv
│   ├── DEXCAUS_exchange_rates.csv
│   ├── DEXUSAL_exchange_rates.csv
│   ├── DEXUSEU_exchange_rates.csv
│   ├── DEXSIUS_exchange_rates.csv
│   └── DEXSZUS_exchange_rates.csv
├── Assets/
│   └── OFTW_Logo.png
├── OFTWDashboard.py
├── requirements.txt
└── README.md
```

## Features Implemented

1. Objective & Key Results Page:
   - Money Moved (Monthly + Total FYTD)
   - Counterfactual Money Moved
   - Active Annualized Run Rate by Channel
   - Pledge Attrition Rate
   - Total Number of Active Donors
   - Total Number of Active Pledges
   - Chapter ARR by Type

## Color Scheme

- Primary (Blue): #007BFF
- Neutral (Gray): #F8F9FA
- Text (Charcoal): #343A40
- Secondary (Teal): #20C997
- Accent (Orange): #FD7E14
- Success (Green): #28A745
- Danger (Red): #DC3545 
