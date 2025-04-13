import pandas_datareader.data as web
import datetime
import pandas as pd

def get_historical_exchange_rates(start_date="2014-03-01", end_date="2025-02-28"):
    """
    Fetch historical exchange rates from FRED for multiple currencies against USD.
    Missing values (e.g. weekends) are filled using backfill (bfill).
    """
    
    currency_codes = {
        'GBP': 'DEXUSUK', 
        'CAD': 'DEXCAUS',  
        'AUD': 'DEXUSAL',  
        'EUR': 'DEXUSEU', 
        'SGD': 'DEXSIUS', 
        'CHF': 'DEXSZUS', 
    }

    for currency, fred_code in currency_codes.items():
        try:
           
            df = web.DataReader(fred_code, "fred", start_date, end_date)

            
            all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
            df_full = df.reindex(all_dates).bfill()

            
            df_full.reset_index(inplace=True)
            df_full.rename(columns={'index': 'DATE'}, inplace=True)
            df_full.to_csv(f"{fred_code}_exchange_rates.csv", index=False)

            print(f"{currency}: Data saved to {fred_code}_exchange_rates.csv")

        except Exception as e:
            print(f"Error fetching data for {currency} ({fred_code}):", e)

if __name__ == "__main__":
    get_historical_exchange_rates()