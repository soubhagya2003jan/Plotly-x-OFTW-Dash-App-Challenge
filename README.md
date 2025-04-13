# OFTW Dashboard
![OFTW_Logo2](https://github.com/user-attachments/assets/1c7e5d59-76a2-4802-bd48-2920c54359ff)
A Plotly Dash dashboard for One for the World (OFTW) that visualizes key metrics and performance indicators.

## Description

The OFTW Dashboard is an interactive tool built with Plotly Dash that helps visualize key metrics and performance indicators for One for the World (OFTW). This dashboard allows users to explore data on donations, pledges, and the overall impact of the organization’s campaigns. The aim is to provide insights that aid in the organization's strategic decision-making and performance tracking of OFTW.

## Features

This Dashboard Includes Several Pages
- Overview of OFTW metrics
- Analysis Methodology
- Objective & Key Results
- Money Moved Analysis
- Pledge Performance Tracking

## Setup
1. Install dependencies:
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
To The IP Adress In The Terminal
```
## Demo
![OverView](https://github.com/user-attachments/assets/b74d34e3-4c48-44ac-9ef6-a848d2b3cd7f)
![Analysis   Methodology](https://github.com/user-attachments/assets/b54d8a2a-0280-44e9-b275-04d5dced8c23)
![Website_Navigation](https://github.com/user-attachments/assets/1fc1df33-6a3e-4ac8-8b61-896a12cd3e2a)
![Ai Insights (2)](https://github.com/user-attachments/assets/207abaa9-f0ec-408c-bfa5-6acf74212494)
![Objective   Key Metrics](https://github.com/user-attachments/assets/4087fdc1-4aa1-414e-b32d-79cb3c430a79)
![MoneyMoved](https://github.com/user-attachments/assets/482c1b16-bc68-4dd3-9605-306e688b9971)
![Pledge_Performance](https://github.com/user-attachments/assets/244acd7a-45c9-4b1b-b256-74f63c0c0337)


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
