import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import numpy as np

# Initialize the Dash app with Flatly Bootswatch theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

# Import your data
Pledge = pd.read_csv('CSV/Pledge.csv')
Payments = pd.read_csv('CSV/Payments.csv')

# Data preprocessing (your existing code)
Pledge = Pledge.drop(Pledge.index[0], axis=0)
Payments['date'] = pd.to_datetime(Payments['date'])
Pledge['pledge_created_at'] = pd.to_datetime(Pledge['pledge_created_at'])
Pledge['pledge_starts_at'] = pd.to_datetime(Pledge['pledge_starts_at'])
Pledge['pledge_ended_at'] = pd.to_datetime(Pledge['pledge_ended_at'])

# Load exchange rates and convert currencies (your existing functions)
def load_exchange_rates():
    gbp = pd.read_csv('ExchangeRate_CSV/DEXUSUK_exchange_rates.csv')
    cad = pd.read_csv('ExchangeRate_CSV/DEXCAUS_exchange_rates.csv')
    aud = pd.read_csv('ExchangeRate_CSV/DEXUSAL_exchange_rates.csv')
    eur = pd.read_csv('ExchangeRate_CSV/DEXUSEU_exchange_rates.csv')
    sgd = pd.read_csv('ExchangeRate_CSV/DEXSIUS_exchange_rates.csv')
    chf = pd.read_csv('ExchangeRate_CSV/DEXSZUS_exchange_rates.csv')
    
    for df in [gbp, cad, aud, eur, sgd, chf]:
        df.rename(columns={'DATE': 'date'}, inplace=True)
        df['date'] = pd.to_datetime(df['date'])
    
    return gbp, cad, aud, eur, sgd, chf

# Your existing conversion functions
def convert_payments_to_usd(payments_df, gbp, cad, aud, eur, sgd, chf):
    df = payments_df.copy()
    df = df.merge(gbp, on='date', how='left')
    df = df.merge(cad, on='date', how='left')
    df = df.merge(aud, on='date', how='left')
    df = df.merge(eur, on='date', how='left')
    df = df.merge(sgd, on='date', how='left')
    df = df.merge(chf, on='date', how='left')

    df['amount_usd'] = df.apply(
        lambda row: row['amount'] * row['DEXUSUK'] if row['currency'] == 'GBP' else
                    row['amount'] / row['DEXCAUS'] if row['currency'] == 'CAD' else
                    row['amount'] * row['DEXUSAL'] if row['currency'] == 'AUD' else
                    row['amount'] * row['DEXUSEU'] if row['currency'] == 'EUR' else
                    row['amount'] / row['DEXSIUS'] if row['currency'] == 'SGD' else
                    row['amount'] / row['DEXSZUS'] if row['currency'] == 'CHF' else
                    row['amount'], axis=1
    )

    df.drop(columns=['DEXUSUK', 'DEXCAUS', 'DEXUSAL', 'DEXUSEU', 'DEXSIUS', 'DEXSZUS'], inplace=True)
    return df

def convert_pledges_to_usd(pledge_df, gbp, cad, aud, eur, sgd, chf):
    df = pledge_df.copy()
    df['pledge_created_at'] = pd.to_datetime(df['pledge_created_at'])
    df.rename(columns={'pledge_created_at': 'date'}, inplace=True)
    
    df = df.merge(gbp, on='date', how='left')
    df = df.merge(cad, on='date', how='left')
    df = df.merge(aud, on='date', how='left')
    df = df.merge(eur, on='date', how='left')
    df = df.merge(sgd, on='date', how='left')
    df = df.merge(chf, on='date', how='left')

    df['amount_usd'] = df.apply(
        lambda row: row['contribution_amount'] * row['DEXUSUK'] if row['currency'] == 'GBP' else
                    row['contribution_amount'] / row['DEXCAUS'] if row['currency'] == 'CAD' else
                    row['contribution_amount'] * row['DEXUSAL'] if row['currency'] == 'AUD' else
                    row['contribution_amount'] * row['DEXUSEU'] if row['currency'] == 'EUR' else
                    row['contribution_amount'] / row['DEXSIUS'] if row['currency'] == 'SGD' else
                    row['contribution_amount'] / row['DEXSZUS'] if row['currency'] == 'CHF' else
                    row['contribution_amount'], axis=1
    )

    df.drop(columns=['DEXUSUK', 'DEXCAUS', 'DEXUSAL', 'DEXUSEU', 'DEXSIUS', 'DEXSZUS'], inplace=True)
    return df

# Load and convert data
gbp_df, cad_df, aud_df, eur_df, sgd_df, chf_df = load_exchange_rates()
df_payments_converted = convert_payments_to_usd(Payments, gbp_df, cad_df, aud_df, eur_df, sgd_df, chf_df)
df_pledges_converted = convert_pledges_to_usd(Pledge, gbp_df, cad_df, aud_df, eur_df, sgd_df, chf_df)

# Color scheme
COLORS = {
    'primary': '#007BFF',    # Blue
    'neutral': '#F8F9FA',    # Light Gray
    'text': '#343A40',       # Charcoal
    'secondary': '#20C997',  # Teal
    'accent': '#FD7E14',     # Orange
    'success': '#28A745',    # Green
    'danger': '#DC3545'      # Red
}

# Custom CSS for fonts
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>OFTW Dashboard</title>
        {%favicon%}
        {%css%}
        <link href="https://fonts.googleapis.com/css2?family=Abhaya+Libre:wght@500&display=swap" rel="stylesheet">
        <style>
            @import url('https://fonts.cdnfonts.com/css/gilroy-bold');
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Layout components
navbar = dbc.Navbar(
    dbc.Container(
        [
            html.A(
                dbc.Row(
                    [
                        dbc.Col(html.Img(src="Assets/OFTW_Logo.png", height="30px")),
                        dbc.Col(html.H4("One for the World", style={'font-family': 'Gilroy', 'color': COLORS['text']})),
                        dbc.Col(html.H4("Charity Dashboard", style={'font-family': 'Abhaya Libre Medium', 'color': COLORS['text']})),
                    ],
                    align="center",
                ),
                href="/",
            ),
            dbc.NavbarToggler(id="navbar-toggler"),
            dbc.Collapse(
                dbc.Nav(
                    [
                        dbc.NavItem(dbc.NavLink("Overview", href="/overview")),
                        dbc.NavItem(dbc.NavLink("Analysis Methodology", href="/methodology")),
                        dbc.NavItem(dbc.NavLink("Objective & Key Results", href="/objectives")),
                        dbc.NavItem(dbc.NavLink("Money Moved", href="/money-moved")),
                        dbc.NavItem(dbc.NavLink("Pledge Performance", href="/pledge-performance")),
                    ],
                    className="ms-auto",
                    navbar=True,
                ),
                id="navbar-collapse",
                navbar=True,
            ),
        ],
        fluid=True,
    ),
    color=COLORS['neutral'],
    dark=False,
)

# Define the layout
app.layout = html.Div([
    navbar,
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# Callback for page routing
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/objectives':
        return objectives_layout
    elif pathname == '/money-moved':
        return html.H1('Money Moved Page - Coming Soon')
    elif pathname == '/pledge-performance':
        return html.H1('Pledge Performance Page - Coming Soon')
    elif pathname == '/methodology':
        return html.H1('Analysis Methodology Page - Coming Soon')
    else:
        return html.H1('Overview Page - Coming Soon')

# Helper functions for calculating metrics
def calculate_money_moved(df, start_date, end_date):
    mask = (df['date'] >= start_date) & (df['date'] <= end_date)
    return df[mask]['amount_usd'].sum()

def calculate_counterfactual_mm(df):
    # Exclude specific portfolios
    excluded_portfolios = ["One for the World Discretionary Fund", "One for the World Operating Costs"]
    filtered_df = df[~df['portfolio'].isin(excluded_portfolios)]
    return (filtered_df['amount_usd'] * filtered_df['counterfactuality']).sum()

def calculate_active_arr(df):
    active_pledges = df[df['pledge_status'] == 'Active donor']
    
    # Convert to annual values based on frequency
    def annualize_amount(row):
        if row['frequency'] == 'monthly':
            return row['amount_usd'] * 12
        elif row['frequency'] == 'quarterly':
            return row['amount_usd'] * 4
        else:  # annual
            return row['amount_usd']
    
    active_pledges['annual_amount'] = active_pledges.apply(annualize_amount, axis=1)
    return active_pledges.groupby('donor_chapter')['annual_amount'].sum()

def calculate_attrition_rate(df):
    """
    Calculate pledge attrition rate as percentage of cancelled/failed pledges
    Returns percentage value (e.g., 18.5 for 18.5%)
    """
    # Count total pledges that were ever active (excluding pledged but never started)
    total_relevant_pledges = len(df[df['pledge_status'].isin(['Active donor', 'Payment failure', 'Churned donor'])])
    
    # Count pledges that failed or churned
    failed_pledges = len(df[df['pledge_status'].isin(['Payment failure', 'Churned donor'])])
    
    # Calculate percentage
    if total_relevant_pledges > 0:
        return (failed_pledges / total_relevant_pledges) * 100
    return 0

def calculate_active_donors(df):
    return len(df[df['pledge_status'].isin(['Active donor', 'one-time'])]['donor_id'].unique())

def calculate_active_pledges(df):
    return len(df[df['pledge_status'] == 'Active donor']['pledge_id'].unique())

def calculate_chapter_arr(df):
    active_pledges = df[df['pledge_status'].isin(['Active donor', 'Pledged donor'])]
    return active_pledges.groupby('chapter_type')['amount_usd'].sum()

# Create metric cards
def create_metric_card(title, value, target, color):
    # Format value based on type
    if "%" in title:
        value_text = f"{value:.1f}%"
        target_text = f"Target 2025: {target}%"
    elif title in ["Active Donors", "Active Pledges"]:  # Integer values without dollar signs
        value_text = f"{value:,.0f}"
        target_text = f"Target 2025: {target:,.0f}"
    else:  # Monetary values
        value_text = f"${value:,.0f}"
        target_text = f"Target 2025: ${target:,.0f}"
        
    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H6(title, className="card-title", style={'color': COLORS['text']}),
                    html.H3(value_text, style={'color': color}),
                    html.P(target_text, style={'color': COLORS['text']})
                ]
            )
        ],
        className="mb-4",
        style={'background-color': COLORS['neutral']}
    )

# Get min and max years from the data for the slider
min_year = min(df_payments_converted['date'].dt.year)
max_year = max(df_payments_converted['date'].dt.year)

# Helper function to get fiscal year dates
def get_fiscal_year_dates(fiscal_year):
    start_date = datetime(fiscal_year - 1, 7, 1)
    end_date = datetime(fiscal_year, 6, 30)
    return start_date, end_date

# Get current fiscal year
current_date = datetime.now()
current_fiscal_year = current_date.year if current_date.month >= 7 else current_date.year - 1

# Get initial fiscal year dates
initial_start_date, initial_end_date = get_fiscal_year_dates(current_fiscal_year)

# Calculate initial metrics with proper dates
money_moved = calculate_money_moved(df_payments_converted, initial_start_date, initial_end_date)
fiscal_year_payments = df_payments_converted[
    (df_payments_converted['date'] >= initial_start_date) & 
    (df_payments_converted['date'] <= initial_end_date)
]
counterfactual_mm = calculate_counterfactual_mm(fiscal_year_payments)

fiscal_year_pledges = df_pledges_converted[
    (df_pledges_converted['date'] >= initial_start_date) & 
    (df_pledges_converted['date'] <= initial_end_date)
]
active_arr = calculate_active_arr(fiscal_year_pledges)
attrition_rate = calculate_attrition_rate(fiscal_year_pledges)
active_donors = calculate_active_donors(fiscal_year_pledges)
active_pledges = calculate_active_pledges(fiscal_year_pledges)
chapter_arr = calculate_chapter_arr(fiscal_year_pledges)

# Create visualizations
def create_arr_by_channel_chart(arr_data):
    fig = go.Figure(data=[
        go.Bar(
            x=arr_data.index,
            y=arr_data.values,
            marker_color=COLORS['primary']
        )
    ])
    fig.update_layout(
        title="Active Annualized Run Rate by Channel",
        xaxis_title="Channel",
        yaxis_title="ARR (USD)",
        template="plotly_white"
    )
    return fig

def create_chapter_arr_chart(chapter_data):
    fig = go.Figure(data=[
        go.Pie(
            labels=chapter_data.index,
            values=chapter_data.values,
            hole=0.4,
            marker_colors=[COLORS['primary'], COLORS['secondary'], COLORS['accent']]
        )
    ])
    fig.update_layout(
        title="Chapter ARR by Type",
        template="plotly_white"
    )
    return fig

# Create the objectives layout
objectives_layout = dbc.Container([
    html.H2("Objective & Key Results", className="my-4", style={'color': COLORS['text']}),
    
    # Fiscal Year Slider
    dbc.Row([
        dbc.Col([
            html.H6("Select Fiscal Year", style={'color': COLORS['text']}),
            dcc.Slider(
                id='fiscal-year-slider',
                min=min_year,
                max=max_year + 1,
                value=current_fiscal_year,
                marks={year: f'FY {year}' for year in range(min_year, max_year + 2)},
                step=1
            ),
        ], width=12, className="mb-4")
    ]),
    
    # First row - Main KPIs
    dbc.Row([
        dbc.Col(html.Div(id='money-moved-card'), width=4),
        dbc.Col(html.Div(id='counterfactual-mm-card'), width=4),
        dbc.Col(html.Div(id='active-arr-card'), width=4),
    ]),
    
    # Second row - Additional KPIs
    dbc.Row([
        dbc.Col(html.Div(id='attrition-rate-card'), width=4),
        dbc.Col(html.Div(id='active-donors-card'), width=4),
        dbc.Col(html.Div(id='active-pledges-card'), width=4),
    ]),
    
    # Third row - Charts
    dbc.Row([
        dbc.Col(dcc.Graph(id='arr-channel-chart'), width=6),
        dbc.Col(dcc.Graph(id='chapter-arr-chart'), width=6),
    ], className="mt-4"),
    
], fluid=True)

# Add callbacks to update all components based on fiscal year
@app.callback(
    [
        Output('money-moved-card', 'children'),
        Output('counterfactual-mm-card', 'children'),
        Output('active-arr-card', 'children'),
        Output('attrition-rate-card', 'children'),
        Output('active-donors-card', 'children'),
        Output('active-pledges-card', 'children'),
        Output('arr-channel-chart', 'figure'),
        Output('chapter-arr-chart', 'figure')
    ],
    Input('fiscal-year-slider', 'value')
)
def update_metrics(selected_fiscal_year):
    # Get fiscal year date range
    start_date, end_date = get_fiscal_year_dates(selected_fiscal_year)
    
    # Calculate metrics for selected fiscal year
    money_moved = calculate_money_moved(df_payments_converted, start_date, end_date)
    
    # Filter payments for counterfactual calculation
    fiscal_year_payments = df_payments_converted[
        (df_payments_converted['date'] >= start_date) & 
        (df_payments_converted['date'] <= end_date)
    ]
    counterfactual_mm = calculate_counterfactual_mm(fiscal_year_payments)
    
    # Filter pledges for the fiscal year
    fiscal_year_pledges = df_pledges_converted[
        (df_pledges_converted['date'] >= start_date) & 
        (df_pledges_converted['date'] <= end_date)
    ]
    
    active_arr = calculate_active_arr(fiscal_year_pledges)
    attrition_rate = calculate_attrition_rate(fiscal_year_pledges)
    active_donors = calculate_active_donors(fiscal_year_pledges)
    active_pledges = calculate_active_pledges(fiscal_year_pledges)
    chapter_arr = calculate_chapter_arr(fiscal_year_pledges)
    
    # Create cards
    cards = [
        create_metric_card("Money Moved (FYTD)", money_moved, 1800000, COLORS['primary']),
        create_metric_card("Counterfactual Money Moved", counterfactual_mm, 1260000, COLORS['secondary']),
        create_metric_card("Active ARR", active_arr.sum(), 1200000, COLORS['accent']),
        create_metric_card("Pledge Attrition Rate (%)", attrition_rate, 18, 
                         COLORS['danger'] if attrition_rate > 18 else COLORS['success']),
        create_metric_card("Active Donors", active_donors, 1200, COLORS['primary']),
        create_metric_card("Active Pledges", active_pledges, 850, COLORS['secondary']),
        create_arr_by_channel_chart(active_arr),
        create_chapter_arr_chart(chapter_arr)
    ]
    
    return cards

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
