import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from datetime import datetime
import numpy as np
import sys
import os
from dash.exceptions import PreventUpdate
from plotly.subplots import make_subplots
from dotenv import load_dotenv
try:
    import google.generativeai as genai

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    generation_config = {
        "temperature": 0.9,
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": 2048,
    }

    safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
    ]
except ImportError:
    print(
        "Warning: google-generativeai package not installed. AI insights feature will not be available."
    )

app = Dash(__name__,
           external_stylesheets=[
               dbc.themes.FLATLY,
               'https://use.fontawesome.com/releases/v5.15.4/css/all.css'
           ],
           assets_folder='Assets',
           suppress_callback_exceptions=True,
           show_undo_redo=False)

COLORS = {
    'primary': '#007BFF',  # Blue
    'neutral': '#F8F9FA',  # Light Gray
    'text': '#343A40',  # Charcoal
    'secondary': '#20C997',  # Teal
    'accent': '#FD7E14',  # Orange
    'success': '#28A745',  # Green
    'danger': '#DC3545'  # Red
}

card_style = {'height': '200px', 'margin-bottom': '20px'}
card_header_style = {
    'backgroundColor': COLORS['primary'],
    'color': 'white',
    'fontWeight': 'bold',
    'height': '50px',
    'display': 'flex',
    'alignItems': 'center'
}
card_body_style = {
    'display': 'flex',
    'flexDirection': 'column',
    'justifyContent': 'space-between',
    'height': '150px',
    'padding': '20px'
}


def get_fiscal_year(date):
    """Convert a date to its fiscal year (July 1 to June 30)"""
    if date.month >= 7:
        return f"FY{date.year}-{date.year + 1}"
    else:
        return f"FY{date.year - 1}-{date.year}"


def get_fiscal_year_range(fiscal_year):
    """Convert fiscal year string to start and end dates"""
    try:
        # Extract years from format "FY2023-2024"
        year1 = int(fiscal_year.split('-')[0].replace('FY', ''))
        year2 = int(fiscal_year.split('-')[1])
        start_date = pd.Timestamp(f"{year1}-07-01")
        end_date = pd.Timestamp(f"{year2}-06-30")
        return start_date, end_date
    except Exception:
        return pd.Timestamp.now(), pd.Timestamp.now()


def calculate_money_moved(df, fiscal_year=None):
    """Calculate total money moved for a fiscal year"""
    if fiscal_year:
        start_date, end_date = get_fiscal_year_range(fiscal_year)
        filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        total = filtered_df['amount_usd'].sum() if not filtered_df.empty else 0
        return total

    return df['amount_usd'].sum() if not df.empty else 0


def calculate_counterfactual_mm(df, fiscal_year=None):
    """Calculate counterfactual money moved"""

    filtered_df = df[~df['portfolio'].isin([
        'One for the World Discretionary Fund',
        'One for the World Operating Costs'
    ])]

    filtered_df['counterfactual_amount'] = filtered_df[
        'amount_usd'] * filtered_df['counterfactuality']

    if fiscal_year:
        start_date, end_date = get_fiscal_year_range(fiscal_year)
        year_df = filtered_df[(filtered_df['date'] >= start_date)
                              & (filtered_df['date'] <= end_date)]
        return year_df['counterfactual_amount'].sum(
        ) if not year_df.empty else 0

    return filtered_df['counterfactual_amount'].sum(
    ) if not filtered_df.empty else 0


def calculate_arr_by_channel(df, fiscal_year=None):
    """Calculate Yearly Annualized Run Rate by channel for active donors"""
    if fiscal_year:
        start_date, end_date = get_fiscal_year_range(fiscal_year)
        df = df[(df['pledge_starts_at'] >= start_date)
                & (df['pledge_starts_at'] <= end_date)]

    active_pledges = df[df['pledge_status'] == 'Active donor'].copy()

    # Monthly amounts are already monthly, multiply by 12 for yearly
    active_pledges['annual_value'] = active_pledges['amount_usd'] * 12

    total_arr = active_pledges['annual_value'].sum()
    return total_arr


def calculate_pledge_attrition_rate(df):
    """Calculate pledge attrition rate"""
    cancelled_pledges = df[df['pledge_status'].isin(
        ['Payment failure', 'Churned donor'])].shape[0]
    total_pledges = df.shape[0]
    return (cancelled_pledges /
            total_pledges) * 100 if total_pledges > 0 else 0


def count_active_donors(df):
    """Count unique active donors"""
    return df[df['pledge_status'].isin(['Active donor',
                                        'One-Time'])]['donor_id'].nunique()


def count_active_pledges(df):
    """Count active pledges (currently paying)"""
    return df[df['pledge_status'] == 'Active donor']['pledge_id'].nunique()


def calculate_chapter_arr(df, fiscal_year=None):
    """Calculate monthly ARR by chapter type"""

    if fiscal_year:
        start_date, end_date = get_fiscal_year_range(fiscal_year)
        df = df[(df['pledge_starts_at'] >= start_date)
                & (df['pledge_starts_at'] <= end_date)]

    active_pledges = df[df['pledge_status'] == 'Active donor'].copy()

    # Just use the monthly amount directly
    active_pledges['monthly_value'] = active_pledges['amount_usd']

    # Multiply by 12 to get annual value
    active_pledges['annual_value'] = active_pledges['monthly_value'] * 12

    chapter_arr = active_pledges.groupby(
        'chapter_type')['annual_value'].sum().reset_index()

    if chapter_arr.empty:
        chapter_arr = pd.DataFrame({'chapter_type': [], 'annual_value': []})

    return chapter_arr


df_payments_converted = pd.DataFrame()
df_pledges_converted = pd.DataFrame()
counterfactual_df = pd.DataFrame()
available_fiscal_years = []
current_fiscal_year = "No Data"

# Load and clean data
try:
    # Load datasets
    Pledge = pd.read_csv('CSV/Pledge.csv')
    Payments = pd.read_csv('CSV/Payments.csv')

    # Clean data
    Pledge = Pledge.drop(Pledge.index[0], axis=0)

    # Convert dates
    Payments['date'] = pd.to_datetime(Payments['date'])
    Pledge['pledge_created_at'] = pd.to_datetime(Pledge['pledge_created_at'])
    Pledge['pledge_starts_at'] = pd.to_datetime(Pledge['pledge_starts_at'])
    Pledge['pledge_ended_at'] = pd.to_datetime(Pledge['pledge_ended_at'])

    # Define exchange rate functions
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

    def convert_payments_to_usd(payments_df, gbp, cad, aud, eur, sgd, chf):
        df = payments_df.copy()

        # Merge exchange rates
        df = df.merge(gbp, on='date', how='left')
        df = df.merge(cad, on='date', how='left')
        df = df.merge(aud, on='date', how='left')
        df = df.merge(eur, on='date', how='left')
        df = df.merge(sgd, on='date', how='left')
        df = df.merge(chf, on='date', how='left')

        # Convert to USD
        df['amount_usd'] = df.apply(
            lambda row: row['amount'] * row['DEXUSUK']
            if row['currency'] == 'GBP' else row['amount'] / row['DEXCAUS']
            if row['currency'] == 'CAD' else row['amount'] * row['DEXUSAL']
            if row['currency'] == 'AUD' else row['amount'] * row['DEXUSEU']
            if row['currency'] == 'EUR' else row['amount'] / row['DEXSIUS']
            if row['currency'] == 'SGD' else row['amount'] / row['DEXSZUS']
            if row['currency'] == 'CHF' else row['amount'],
            axis=1)

        # Drop exchange rate columns
        df.drop(columns=[
            'DEXUSUK', 'DEXCAUS', 'DEXUSAL', 'DEXUSEU', 'DEXSIUS', 'DEXSZUS'
        ],
                inplace=True)
        return df

    def convert_pledges_to_usd(pledge_df, gbp, cad, aud, eur, sgd, chf):
        df = pledge_df.copy()
        df['pledge_created_at'] = pd.to_datetime(df['pledge_created_at'])
        df.rename(columns={'pledge_created_at': 'date'}, inplace=True)

        # Merge exchange rates
        df = df.merge(gbp, on='date', how='left')
        df = df.merge(cad, on='date', how='left')
        df = df.merge(aud, on='date', how='left')
        df = df.merge(eur, on='date', how='left')
        df = df.merge(sgd, on='date', how='left')
        df = df.merge(chf, on='date', how='left')

        # Convert to USD
        df['amount_usd'] = df.apply(
            lambda row: row['contribution_amount'] * row['DEXUSUK']
            if row['currency'] == 'GBP' else row['contribution_amount'] / row[
                'DEXCAUS'] if row['currency'] == 'CAD' else row[
                    'contribution_amount'] * row['DEXUSAL']
            if row['currency'] == 'AUD' else row['contribution_amount'] * row[
                'DEXUSEU'] if row['currency'] == 'EUR' else row[
                    'contribution_amount'] / row['DEXSIUS']
            if row['currency'] == 'SGD' else row['contribution_amount'] / row[
                'DEXSZUS']
            if row['currency'] == 'CHF' else row['contribution_amount'],
            axis=1)

        # Drop exchange rate columns
        df.drop(columns=[
            'DEXUSUK', 'DEXCAUS', 'DEXUSAL', 'DEXUSEU', 'DEXSIUS', 'DEXSZUS'
        ],
                inplace=True)
        return df

    # Load exchange rates
    gbp_df, cad_df, aud_df, eur_df, sgd_df, chf_df = load_exchange_rates()

    # Convert to USD
    df_payments_converted = convert_payments_to_usd(Payments, gbp_df, cad_df,
                                                    aud_df, eur_df, sgd_df,
                                                    chf_df)
    df_pledges_converted = convert_pledges_to_usd(Pledge, gbp_df, cad_df,
                                                  aud_df, eur_df, sgd_df,
                                                  chf_df)

    # Segregate payments
    Anonymous = df_payments_converted[
        df_payments_converted['pledge_id'].isna()]
    Pledged_Payments = df_payments_converted[
        df_payments_converted['pledge_id'].notna()]

    # Rename the column back for merging purposes
    df_pledges_converted.rename(columns={'date': 'pledge_created_at'},
                                inplace=True)

    # Merge datasets
    Merged_INNER = pd.merge(df_pledges_converted,
                            df_payments_converted,
                            on='pledge_id',
                            how='inner')
    Merged_LEFT = pd.merge(df_pledges_converted,
                           Pledged_Payments,
                           on='pledge_id',
                           how='left')

    # Filter out discretionary fund and operating costs for counterfactual calculations
    counterfactual_df = df_payments_converted[
        ~df_payments_converted['portfolio'].isin([
            'One for the World Discretionary Fund',
            'One for the World Operating Costs'
        ])].copy()

    # Calculate counterfactual money moved
    counterfactual_df['counterfactual_moved'] = counterfactual_df[
        'amount_usd'] * counterfactual_df['counterfactuality']

    # Get available fiscal years from the payment data
    available_fiscal_years = sorted(
        list(
            set([
                get_fiscal_year(date) for date in df_payments_converted['date']
            ])))
    current_fiscal_year = available_fiscal_years[
        -1] if available_fiscal_years else "No Data"

    print("Data loading and processing completed successfully")

except Exception as e:
    print(f"Error loading or processing data: {e}")
    # Keep the defaults for global variables

app.layout = html.Div(
    [
        html.Div([
            html.Div(
                [
                    html.Button(html.I(className="fas fa-bars"),
                                id="menu-button",
                                className="btn",
                                style={
                                    'background': 'transparent',
                                    'border': 'none',
                                    'color': COLORS['text'],
                                    'fontSize': '24px'
                                }),
                    html.Img(src='/assets/OFTW_Logo.png',
                             style={
                                 'height': '40px',
                                 'marginRight': '10px'
                             }),
                    html.Div([
                        html.H3("One for the World",
                                style={
                                    'margin': '0',
                                    'fontSize': '28px',
                                    'fontFamily': 'Poppins, sans-serif',
                                    'color': 'white',
                                    'fontWeight': '600',
                                    'letterSpacing': '0.5px'
                                }),
                        html.H5("Charity Dashboard",
                                style={
                                    'margin': '0',
                                    'fontFamily': 'Inter, sans-serif',
                                    'color': 'white',
                                    'fontWeight': '400',
                                    'letterSpacing': '0.3px'
                                })
                    ])
                ],
                style={
                    'display': 'flex',
                    'alignItems': 'center',
                    'gap': '15px',
                    'padding': '15px'
                }),
            dbc.Collapse(
                dbc.Nav(
                    [
                        dbc.NavItem(
                            dbc.NavLink("Overview of OFTW",
                                        href="#",
                                        id="nav-overview",
                                        active=False)),
                        dbc.NavItem(
                            dbc.NavLink("Analysis Methodology",
                                        href="#",
                                        id="nav-analysis",
                                        active=False)),
                        dbc.NavItem(
                            dbc.NavLink("Objective and Key Results",
                                        href="#",
                                        id="nav-objective",
                                        active=True)),
                        dbc.NavItem(
                            dbc.NavLink("Money Moved",
                                        href="#",
                                        id="nav-money",
                                        active=False)),
                        dbc.NavItem(
                            dbc.NavLink("Pledge Performance",
                                        href="#",
                                        id="nav-pledge",
                                        active=False)),
                        dbc.NavItem(
                            dbc.NavLink("Insights",
                                        href="#",
                                        id="nav-insights",
                                        active=False)),
                    ],
                    vertical="xl",
                    pills=True,
                    className="border-right flex-column",
                    style={
                        'backgroundColor': COLORS['neutral'],
                        'padding': '20px',
                        'borderRight': f'1px solid {COLORS["text"]}',
                        'height': '100%',
                        'flexDirection': 'column !important'
                    }),
                id="navbar-collapse",
                is_open=False,
            ),
        ],
                 style={
                     'backgroundColor': '#007bff',
                     'borderBottom': '1px solid #007bff'
                 }),
        html.Div(
            [
                html.Div(
                    [
                        # Overview Page
                        html.Div(
                            id="page-overview",
                            style={'display': 'none'},
                            children=[
                                # Title Section
                                html.H1("Overview of One for the World",
                                        style={
                                            'textAlign': 'center',
                                            'color': COLORS['primary'],
                                            'marginTop': '20px',
                                            'marginBottom': '40px',
                                            'fontSize': '2.5rem',
                                            'fontWeight': 'bold'
                                        }),
                                # Hero Section
                                html.Div(
                                    style={
                                        'background-image':
                                        'url("/assets/Child.jpg")',
                                        'background-size': 'cover',
                                        'background-position': 'center',
                                        'height': '500px',
                                        'display': 'flex',
                                        'alignItems': 'center',
                                        'justifyContent': 'center',
                                        'position': 'relative',
                                        'marginBottom': '40px'
                                    },
                                    children=[
                                        html.Div(
                                            style={
                                                'backgroundColor':
                                                'rgba(0,0,0,0.6)',
                                                'padding': '40px',
                                                'borderRadius': '10px',
                                                'textAlign': 'center',
                                                'color': 'white'
                                            },
                                            children=[
                                                html.
                                                H1("How can $2.15 a day be enough to live?",
                                                   style={
                                                       'fontSize': '3rem',
                                                       'marginBottom': '20px'
                                                   }),
                                                html.
                                                H3("Your 1% can make the difference between life and death",
                                                   style={
                                                       'fontSize': '1.5rem'
                                                   })
                                            ])
                                    ]),

                                # Key Stats Section
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardBody([
                                                html.H3(
                                                    "700 Million",
                                                    className="text-primary",
                                                    style={
                                                        'fontSize': '2.5rem'
                                                    }),
                                                html.
                                                P("People live on less than $2.15/day"
                                                  )
                                            ])
                                        ],
                                                 className="text-center mb-4")
                                    ],
                                            width=4),
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardBody([
                                                html.H3(
                                                    "14,500",
                                                    className="text-danger",
                                                    style={
                                                        'fontSize': '2.5rem'
                                                    }),
                                                html.
                                                P("Children die each day from preventable causes"
                                                  )
                                            ])
                                        ],
                                                 className="text-center mb-4")
                                    ],
                                            width=4),
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardBody([
                                                html.H3(
                                                    "1%",
                                                    className="text-success",
                                                    style={
                                                        'fontSize': '2.5rem'
                                                    }),
                                                html.
                                                P("Of your income can save lives"
                                                  )
                                            ])
                                        ],
                                                 className="text-center mb-4")
                                    ],
                                            width=4),
                                ]),

                                # Mission Section
                                html.Div([
                                    html.H2("Our Mission",
                                            style={
                                                'textAlign': 'center',
                                                'marginBottom': '30px'
                                            }),
                                    dbc.Row([
                                        dbc.Col([
                                            html.P(
                                                [
                                                    "One for the World's mission is to scale the effective giving movement that addresses extreme poverty. We aim to introduce young professionals to effective giving through our 1% Pledge, thereby helping scale this movement because early choices inspire lifelong impact. ",
                                                    html.Br(),
                                                    html.Br(),
                                                    "Through careful evaluation and partnerships with highly effective organizations, we ensure that every dollar pledged creates maximum impact in fighting extreme poverty. Our model combines evidence-based giving with the power of collective action, demonstrating that when we come together, even a small portion of our income can transform lives.",
                                                    html.Br(),
                                                    html.Br(),
                                                    "By focusing on proven interventions and cost-effective solutions, we work to break the cycle of poverty and create lasting change in communities worldwide. Our growing movement of committed donors proves that sustainable, impactful giving is not just possible – it's happening right now."
                                                ],
                                                style={
                                                    'fontSize': '1.2rem',
                                                    'lineHeight': '1.8'
                                                })
                                        ],
                                                width=8,
                                                className="mx-auto")
                                    ])
                                ],
                                         style={'marginBottom': '40px'}),

                                # Global Impact Section
                                dbc.Row([
                                    dbc.Col([
                                        html.Img(
                                            src=
                                            '/assets/total-population-living-in-extreme-poverty-by-world-region.png',
                                            style={
                                                'width': '100%',
                                                'marginBottom': '20px'
                                            }),
                                        html.
                                        H4("Population Living in Extreme Poverty by Region",
                                           style={'textAlign': 'center'})
                                    ],
                                            width=12)
                                ]),

                                # Call to Action
                                html.Div([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H2(
                                                "Ready to Make a Difference?",
                                                className="text-center mb-4"),
                                            html.
                                            P("Join thousands of others who have pledged 1% of their income to fight extreme poverty.",
                                              className="text-center mb-4",
                                              style={'fontSize': '1.2rem'}),
                                            html.Div([
                                                dbc.Button(
                                                    "Take the 1% Pledge",
                                                    color="primary",
                                                    size="lg",
                                                    href=
                                                    "https://1fortheworld.org/",
                                                    target="_blank",
                                                    className="mx-auto d-block",
                                                    style={
                                                        'fontSize': '1.5rem',
                                                        'padding': '15px 30px'
                                                    })
                                            ],
                                                     className="text-center")
                                        ])
                                    ],
                                             style={
                                                 'backgroundColor':
                                                 COLORS['neutral']
                                             })
                                ],
                                         style={
                                             'marginTop': '40px',
                                             'marginBottom': '40px'
                                         })
                            ]),

                        # Analysis Methodology Page
                        html.Div(
                            id="page-analysis",
                            style={'display': 'none'},
                            children=[
                                # Title
                                html.H2("Analysis Methodology",
                                        style={
                                            'color': COLORS['primary'],
                                            'marginBottom': '30px',
                                            'textAlign': 'center',
                                            'fontWeight': 'bold'
                                        }),

                                # Data Source Section
                                dbc.Card([
                                    dbc.CardHeader(
                                        [
                                            html.
                                            I(className="fas fa-database me-2"
                                              ), "Data Source"
                                        ],
                                        style={
                                            'backgroundColor':
                                            COLORS['primary'],
                                            'color': 'white',
                                            'fontSize': '1.2rem'
                                        }),
                                    dbc.CardBody([
                                        html.H5("Pledges Dataset",
                                                className="text-primary mb-3"),
                                        html.P([
                                            "Contains all donation pledges with key information including ",
                                            html.Strong(
                                                "donor_id, pledge_id, donor_chapter, pledge_status, "
                                            ), "and contribution details."
                                        ]),
                                        html.H5("Payments Dataset",
                                                className="text-primary mb-3"),
                                        html.P([
                                            "Records actual donations made, tracking ",
                                            html.Strong(
                                                "payment ID, donor_id, portfolio allocation, "
                                            ), "and counterfactuality scores."
                                        ])
                                    ])
                                ],
                                         className="mb-4"),

                                # Preprocessing Section
                                dbc.Card([
                                    dbc.CardHeader(
                                        [
                                            html.I(
                                                className="fas fa-cogs me-2"),
                                            "Preprocessing"
                                        ],
                                        style={
                                            'backgroundColor':
                                            COLORS['secondary'],
                                            'color': 'white',
                                            'fontSize': '1.2rem'
                                        }),
                                    dbc.CardBody([
                                        dbc.ListGroup([
                                            dbc.ListGroupItem([
                                                html.
                                                I(className=
                                                  "fas fa-check-circle text-success me-2"
                                                  ),
                                                "Data Cleaning: Removed anomalous dates and standardized formats"
                                            ]),
                                            dbc.ListGroupItem([
                                                html.
                                                I(className=
                                                  "fas fa-check-circle text-success me-2"
                                                  ),
                                                "Date Conversion: Transformed to pandas datetime objects"
                                            ]),
                                            dbc.ListGroupItem([
                                                html.
                                                I(className=
                                                  "fas fa-check-circle text-success me-2"
                                                  ),
                                                "Currency Normalization: Applied historical exchange rates"
                                            ])
                                        ])
                                    ])
                                ],
                                         className="mb-4"),

                                # Visualization Tools Section
                                dbc.Card([
                                    dbc.CardHeader(
                                        [
                                            html.
                                            I(className="fas fa-chart-bar me-2"
                                              ), "Visualization Tools"
                                        ],
                                        style={
                                            'backgroundColor':
                                            COLORS['accent'],
                                            'color': 'white',
                                            'fontSize': '1.2rem'
                                        }),
                                    dbc.CardBody([
                                        html.P([
                                            "Built using ",
                                            html.Strong("Plotly and Dash "),
                                            "for interactive visualizations, styled with Bootstrap and custom themes."
                                        ])
                                    ])
                                ],
                                         className="mb-4"),

                                # Key Metrics Section (Accordion)
                                html.H4(
                                    [
                                        html.
                                        I(className="fas fa-calculator me-2"),
                                        "Key Metrics"
                                    ],
                                    style={
                                        'color': COLORS['text'],
                                        'marginBottom': '20px'
                                    }),
                                dbc.Accordion([
                                    dbc.AccordionItem([
                                        html.
                                        P("Total and monthly donation volume from Payments dataset, excluding internal funds."
                                          ),
                                        html.Div([
                                            dbc.Badge("Primary KPI",
                                                      color="primary",
                                                      className="me-2"),
                                            dbc.Badge("Monthly Tracked",
                                                      color="info")
                                        ])
                                    ],
                                                      title="Money Moved (MM)"
                                                      ),
                                    dbc.AccordionItem([
                                        html.P([
                                            "Calculated as: amount × counterfactuality score. ",
                                            "Measures true donation impact."
                                        ]),
                                        dbc.Badge("Impact Metric",
                                                  color="success")
                                    ],
                                                      title=
                                                      "Counterfactual Money Moved"
                                                      ),
                                    dbc.AccordionItem(
                                        [
                                            html.
                                            P("Projected annual donation amount from active pledges."
                                              ),
                                            dbc.Badge("Growth Metric",
                                                      color="warning")
                                        ],
                                        title="ARR (Annualized Run Rate)"),
                                    dbc.AccordionItem([
                                        html.
                                        P("Proportion of canceled pledges and failed payments."
                                          ),
                                        dbc.Badge("Risk Metric",
                                                  color="danger")
                                    ],
                                                      title=
                                                      "Pledge Attrition Rate")
                                ],
                                              start_collapsed=True,
                                              className="mb-4"),

                                # Assumptions Section
                                dbc.Card([
                                    dbc.CardHeader(
                                        [
                                            html.I(className=
                                                   "fas fa-info-circle me-2"),
                                            "Assumptions"
                                        ],
                                        style={
                                            'backgroundColor': COLORS['text'],
                                            'color': 'white',
                                            'fontSize': '1.2rem'
                                        }),
                                    dbc.CardBody([
                                        dbc.ListGroup([
                                            dbc.ListGroupItem(
                                                "All analyses based on current data structures"
                                            ),
                                            dbc.ListGroupItem(
                                                "Missing values treated as unknown"
                                            ),
                                            dbc.ListGroupItem(
                                                "Exchange rates applied based on payment dates"
                                            )
                                        ],
                                                      flush=True)
                                    ])
                                ])
                            ]),

                        # Objective and Key Results Page
                        html.Div(
                            id="page-objective",
                            children=[
                                html.H2("Objective and Key Results",
                                        style={
                                            'color': COLORS['text'],
                                            'marginBottom': '20px'
                                        }),

                                # Fiscal Year Selector
                                html.Div(
                                    [
                                        html.Label("Select Fiscal Year:",
                                                   style={
                                                       'marginRight': '10px',
                                                       'fontWeight': 'bold'
                                                   }),
                                        dcc.Dropdown(
                                            id='fiscal-year-dropdown',
                                            options=[{
                                                'label':
                                                fy,
                                                'value':
                                                fy
                                            } for fy in available_fiscal_years
                                                     ],
                                            value=current_fiscal_year,
                                            style={'width': '200px'},
                                            clearable=False)
                                    ],
                                    style={
                                        'marginBottom': '20px',
                                        'display': 'flex',
                                        'alignItems': 'center'
                                    }),

                                # First row of KPIs (Money Moved, Counterfactual MM, Active ARR)
                                dbc.Row([
                                    # Money Moved KPI
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardHeader(
                                                "Money Moved (Yearly)",
                                                style=card_header_style),
                                            dbc.CardBody([
                                                html.Div(
                                                    id="money-moved-kpi",
                                                    style={
                                                        'fontSize': '2rem',
                                                        'fontWeight': 'bold',
                                                        'color':
                                                        COLORS['primary'],
                                                        'textAlign': 'center',
                                                        'margin': '10px 0'
                                                    }),
                                                                               html.Div([
                                                    html.Span(
                                                        "Target For 2025: $1.8M",
                                                        style={
                                                            'color':
                                                            COLORS['accent'],
                                                            'fontWeight':
                                                            'bold'
                                                        }),
                                                ],
                                                         style={
                                                             'textAlign':
                                                             'right'
                                                         })
                                            ],
                                                         style=card_body_style)
                                        ],
                                                 style=card_style)
                                    ],
                                            width=4),

                                    # Counterfactual MM
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardHeader(
                                                "Counterfactual Money Moved",
                                                style=card_header_style),
                                            dbc.CardBody([
                                                html.Div(
                                                    id="counterfactual-mm-kpi",
                                                    className="kpi-number"),
                                                html.Div([
                                                    html.Span(
                                                        "Target For 2025: $1.26M",
                                                        style={
                                                            'color':
                                                            COLORS['accent'],
                                                            'fontWeight':
                                                            'bold'
                                                        }),
                                                ],
                                                         style={
                                                             'textAlign':
                                                             'right'
                                                         })
                                            ],
                                                         style=card_body_style)
                                        ],
                                                 style=card_style)
                                    ],
                                            width=4),

                                    # Active ARR by Channel
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardHeader(
                                                "Active ARR Yearly",
                                                style=card_header_style),
                                            dbc.CardBody([
                                                html.Div(
                                                    id="active-arr-kpi",
                                                    className="kpi-number"),
                                                html.Div([
                                                    html.Span(
                                                        "Target For 2025: $1.2M",
                                                        style={
                                                            'color':
                                                            COLORS['accent'],
                                                            'fontWeight':
                                                            'bold'
                                                        }),
                                                ],
                                                         style={
                                                             'textAlign':
                                                             'right'
                                                         })
                                            ],
                                                         style=card_body_style)
                                        ],
                                                 style=card_style)
                                    ],
                                            width=4),
                                ]),

                                # Second row of KPIs
                                dbc.Row([
                                    # Pledge Attrition Rate
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardHeader(
                                                "Pledge Attrition Rate",
                                                style=card_header_style),
                                            dbc.CardBody([
                                                html.Div(
                                                    id="attrition-kpi",
                                                    className="kpi-number"),
                                                html.Div([
                                                    html.Span(
                                                        "Target For 2025: 18%",
                                                        style={
                                                            'color':
                                                            COLORS['accent'],
                                                            'fontWeight':
                                                            'bold'
                                                        }),
                                                ],
                                                         style={
                                                             'textAlign':
                                                             'right'
                                                         })
                                            ],
                                                         style=card_body_style)
                                        ],
                                                 style=card_style)
                                    ],
                                            width=4),

                                    # Total Active Donors
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardHeader(
                                                "Total Active Donors",
                                                style=card_header_style),
                                            dbc.CardBody([
                                                html.Div(
                                                    id="active-donors-kpi",
                                                    className="kpi-number"),
                                                html.Div([
                                                    html.Span(
                                                        "Target For 2025: 1,200",
                                                        style={
                                                            'color':
                                                            COLORS['accent'],
                                                            'fontWeight':
                                                            'bold'
                                                        }),
                                                ],
                                                         style={
                                                             'textAlign':
                                                             'right'
                                                         })
                                            ],
                                                         style=card_body_style)
                                        ],
                                                 style=card_style)
                                    ],
                                            width=4),

                                    # Total Active Pledges
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardHeader(
                                                "Total Active Pledges (Paying Now)",
                                                style=card_header_style),
                                            dbc.CardBody([
                                                html.Div(
                                                    id="active-pledges-kpi",
                                                    className="kpi-number"),
                                                html.Div([
                                                    html.Span(
                                                        "Target For 2025: 850",
                                                        style={
                                                            'color':
                                                            COLORS['accent'],
                                                            'fontWeight':
                                                            'bold'
                                                        }),
                                                ],
                                                         style={
                                                             'textAlign':
                                                             'right'
                                                         })
                                            ],
                                                         style=card_body_style)
                                        ],
                                                 style=card_style)
                                    ],
                                            width=4),
                                ]),

                                # Third row - Chapter ARR by Type Chart
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardHeader(
                                                "Chapter ARR by Chapter Type",
                                                style={
                                                    'backgroundColor':
                                                    COLORS['primary'],
                                                    'color':
                                                    'white',
                                                    'fontWeight':
                                                    'bold'
                                                }),
                                            dbc.CardBody([
                                                dcc.Graph(
                                                    id="chapter-arr-chart",
                                                    config={
                                                        'displayModeBar': False
                                                    }),
                                                html.Div(
                                                    [
                                                        html.Span(
                                                            "Target For 2025: $670,000",
                                                            style={
                                                                'color':
                                                                COLORS[
                                                                    'accent'],
                                                                'fontWeight':
                                                                'bold'
                                                            }),
                                                    ],
                                                    style={
                                                        'textAlign': 'right',
                                                        'marginTop': '10px'
                                                    })
                                            ])
                                        ],
                                                 className="mb-4")
                                    ],
                                            width=12),
                                ]),

                                # Money Moved Over Time Chart
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardHeader(
                                                "Money Moved Over Time",
                                                style={
                                                    'backgroundColor':
                                                    COLORS['primary'],
                                                    'color':
                                                    'white',
                                                    'fontWeight':
                                                    'bold'
                                                }),
                                            dbc.CardBody([
                                                dcc.Graph(
                                                    id="money-moved-chart",
                                                    config={
                                                        'displayModeBar': False
                                                    })
                                            ])
                                        ],
                                                 className="mb-4")
                                    ],
                                            width=12),
                                ]),
                            ]),

                        # Money Moved Page
                        html.Div(
                            id="page-money",
                            style={'display': 'none'},
                            children=[
                                html.H2("Money Moved Analysis",
                                        style={
                                            'color': COLORS['text'],
                                            'marginBottom': '20px',
                                            'textAlign': 'center'
                                        }),

                                # Fiscal Year Selector
                                html.Div(
                                    [
                                        html.Label("Select Fiscal Year:",
                                                   style={
                                                       'marginRight': '10px',
                                                       'fontWeight': 'bold'
                                                   }),
                                        dcc.Dropdown(
                                            id='mm-fiscal-year-dropdown',
                                            options=[{
                                                'label': fy,
                                                'value': fy
                                            } for fy in available_fiscal_years
                                                     ],
                                            value=current_fiscal_year,
                                            style={'width': '200px'},
                                            clearable=False)
                                    ],
                                    style={
                                        'marginBottom': '20px',
                                        'display': 'flex',
                                        'alignItems': 'center'
                                    }),

                                # Top KPI Cards Row
                                dbc.Row([
                                    dbc.Col(dbc.Card([
                                        dbc.CardHeader(
                                            "Total Money Moved",
                                            style=card_header_style),
                                        dbc.CardBody([
                                            html.Div(id="mm-total-kpi",
                                                     className="kpi-number"),
                                            html.Div(
                                                "YTD Performance",
                                                style={'textAlign': 'center'})
                                        ])
                                    ]),
                                            width=4),
                                    dbc.Col(dbc.Card([
                                        dbc.CardHeader(
                                            "Counterfactual Impact",
                                            style=card_header_style),
                                        dbc.CardBody([
                                            html.Div(
                                                id="mm-counterfactual-kpi",
                                                className="kpi-number"),
                                            html.Div(
                                                "Real World Impact",
                                                style={'textAlign': 'center'})
                                        ])
                                    ]),
                                            width=4),
                                    dbc.Col(dbc.Card([
                                        dbc.CardHeader(
                                            "Monthly Average",
                                            style=card_header_style),
                                        dbc.CardBody([
                                            html.Div(id="mm-monthly-avg-kpi",
                                                     className="kpi-number"),
                                            html.Div(
                                                "Avg Money Moved per Month",
                                                style={'textAlign': 'center'})
                                        ])
                                    ]),
                                            width=4),
                                ],
                                        className="mb-4"),

                                # Charts Section
                                dbc.Row([
                                    # Money Moved Over Time Chart
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardHeader(
                                                "Money Moved Trends",
                                                style=card_header_style),
                                            dbc.CardBody([
                                                dcc.Graph(id="mm-trends-chart")
                                            ])
                                        ])
                                    ],
                                            width=12,
                                            className="mb-4"),
                                ]),

                                # Platform and Source Breakdown
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardHeader(
                                                "Platform Distribution",
                                                style=card_header_style),
                                            dbc.CardBody([
                                                dcc.Graph(
                                                    id="mm-platform-chart")
                                            ])
                                        ])
                                    ],
                                            width=6),
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardHeader(
                                                "Chapter/Source Breakdown",
                                                style=card_header_style),
                                            dbc.CardBody([
                                                dcc.Graph(id="mm-source-chart")
                                            ])
                                        ])
                                    ],
                                            width=6),
                                ],
                                        className="mb-4"),

                                # Recurring vs One-Time and Heatmap
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardHeader(
                                                "Recurring vs One-Time Donations",
                                                style=card_header_style),
                                            dbc.CardBody([
                                                dcc.Graph(
                                                    id="mm-recurring-chart")
                                            ])
                                        ])
                                    ],
                                            width=6),
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardHeader(
                                                "Platform Performance Heatmap",
                                                style=card_header_style),
                                            dbc.CardBody([
                                                dcc.Graph(
                                                    id="mm-heatmap-chart")
                                            ])
                                        ])
                                    ],
                                            width=6),
                                ])
                            ]),

                        # Pledge Performance Page
                        html.Div(
                            id="page-pledge",
                            style={'display': 'none'},
                            children=[
                                html.H2("Pledge Performance Analysis",
                                        style={
                                            'color': COLORS['text'],
                                            'marginBottom': '20px',
                                            'textAlign': 'center'
                                        }),

                                # Fiscal Year Selector
                                html.Div(
                                    [
                                        html.Label("Select Fiscal Year:",
                                                   style={
                                                       'marginRight': '10px',
                                                       'fontWeight': 'bold'
                                                   }),
                                        dcc.Dropdown(
                                            id='pledge-fiscal-year-dropdown',
                                            options=[{
                                                'label': fy,
                                                'value': fy
                                            } for fy in available_fiscal_years
                                                     ],
                                            value=current_fiscal_year,
                                            style={'width': '200px'},
                                            clearable=False)
                                    ],
                                    style={
                                        'marginBottom': '20px',
                                        'display': 'flex',
                                        'alignItems': 'center'
                                    }),

                                # Add Month Range Slider
                                html.Div([
                                    html.Label("Select Month Range:",
                                               style={
                                                   'marginRight': '10px',
                                                   'fontWeight': 'bold',
                                                   'marginBottom': '10px',
                                                   'display': 'block'
                                               }),
                                    dcc.RangeSlider(
                                        id='pledge-month-slider',
                                        min=0,
                                        max=11,
                                        step=1,
                                        value=[0, 11],
                                        marks={
                                            i: {
                                                'label':
                                                (datetime(2000, i + 1,
                                                          1).strftime('%B'))
                                            }
                                            for i in range(12)
                                        })
                                ],
                                         style={
                                             'marginBottom': '30px',
                                             'padding': '0 20px'
                                         }),

                                # Top KPI Cards Row
                                dbc.Row(
                                    [
                                        # All Pledges KPI
                                        dbc.Col(dbc.Card([
                                            dbc.CardHeader(
                                                "Total Pledges (Active + Future)",
                                                style=card_header_style),
                                            dbc.CardBody([
                                                html.Div(
                                                    id="total-pledges-kpi",
                                                    className="kpi-number"),
                                                html.Div(
                                                    "Active + Future Pledges",
                                                    style={
                                                        'textAlign': 'center'
                                                    })
                                            ])
                                        ]),
                                                width=4),
                                        # Active Pledges KPI
                                        dbc.Col(dbc.Card([
                                            dbc.CardHeader(
                                                "Active Pledges",
                                                style=card_header_style),
                                            dbc.CardBody([
                                                html.Div(
                                                    id=
                                                    "active-pledges-count-kpi",
                                                    className="kpi-number"),
                                                html.Div("Currently Active",
                                                         style={
                                                             'textAlign':
                                                             'center'
                                                         })
                                            ])
                                        ]),
                                                width=4),
                                        # Future Pledges KPI
                                        dbc.Col(dbc.Card([
                                            dbc.CardHeader(
                                                "Future Pledges",
                                                style=card_header_style),
                                            dbc.CardBody([
                                                html.Div(
                                                    id="future-pledges-kpi",
                                                    className="kpi-number"),
                                                html.Div("Starting in Future",
                                                         style={
                                                             'textAlign':
                                                             'center'
                                                         })
                                            ])
                                        ]),
                                                width=4),
                                    ],
                                    className="mb-4"),

                                # ARR KPI Cards Row
                                dbc.Row(
                                    [
                                        # Total ARR KPI
                                        dbc.Col(dbc.Card([
                                            dbc.CardHeader(
                                                "Total ARR",
                                                style=card_header_style),
                                            dbc.CardBody([
                                                html.Div(
                                                    id="total-arr-kpi",
                                                    className="kpi-number"),
                                                html.Div("Active + Future ARR",
                                                         style={
                                                             'textAlign':
                                                             'center'
                                                         })
                                            ])
                                        ]),
                                                width=4),
                                        # Active ARR KPI
                                        dbc.Col(dbc.Card([
                                            dbc.CardHeader(
                                                "Active ARR",
                                                style=card_header_style),
                                            dbc.CardBody([
                                                html.Div(
                                                    id="active-arr-value-kpi",
                                                    className="kpi-number"),
                                                html.Div(
                                                    "Current Annual Value",
                                                    style={
                                                        'textAlign': 'center'
                                                    })
                                            ])
                                        ]),
                                                width=4),
                                        # Future ARR KPI
                                        dbc.Col(dbc.Card([
                                            dbc.CardHeader(
                                                "Future ARR",
                                                style=card_header_style),
                                            dbc.CardBody([
                                                html.Div(
                                                    id="future-arr-kpi",
                                                    className="kpi-number"),
                                                html.Div("Future Annual Value",
                                                         style={
                                                             'textAlign':
                                                             'center'
                                                         })
                                            ])
                                        ]),
                                                width=4),
                                    ],
                                    className="mb-4"),

                                # Charts Section
                                dbc.Row([
                                    # Pledge Trends Chart
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardHeader(
                                                "Pledge Volume Trends",
                                                style=card_header_style),
                                            dbc.CardBody([
                                                dcc.Graph(
                                                    id="pledge-trends-chart")
                                            ])
                                        ])
                                    ],
                                            width=12,
                                            className="mb-4"),
                                ]),

                                # ARR and Attrition Charts Row
                                dbc.Row(
                                    [
                                        # ARR Growth Chart
                                        dbc.Col([
                                            dbc.Card([
                                                dbc.CardHeader(
                                                    "ARR Growth Trends",
                                                    style=card_header_style),
                                                dbc.CardBody([
                                                    dcc.Graph(
                                                        id="arr-growth-chart")
                                                ])
                                            ])
                                        ],
                                                width=6),
                                        # Attrition Rate Chart
                                        dbc.Col([
                                            dbc.Card([
                                                dbc.CardHeader(
                                                    "Monthly Attrition Rate",
                                                    style=card_header_style),
                                                dbc.CardBody([
                                                    dcc.Graph(
                                                        id=
                                                        "attrition-trend-chart"
                                                    )
                                                ])
                                            ])
                                        ],
                                                width=6),
                                    ],
                                    className="mb-4"),

                                # Chapter Performance Charts Row
                                dbc.Row(
                                    [
                                        # Chapter Breakdown
                                        dbc.Col([
                                            dbc.Card([
                                                dbc.CardHeader(
                                                    "Performance by Chapter",
                                                    style=card_header_style),
                                                dbc.CardBody([
                                                    dcc.Graph(
                                                        id=
                                                        "chapter-performance-chart"
                                                    )
                                                ])
                                            ])
                                        ],
                                                width=12),
                                    ],
                                    className="mb-4"),
                            ]),

                        # Insights Page
                        html.Div(
                            id="page-insights",
                            style={'display': 'none'},
                            children=[
                                html.H2("AI-Powered Dashboard Insights",
                                        style={
                                            'color': COLORS['text'],
                                            'marginBottom': '20px',
                                            'textAlign': 'center'
                                        }),

                                # Question Input
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardBody([
                                                html.
                                                H4("Ask Questions About Your Data"
                                                   ),
                                                dbc.Textarea(
                                                    id='question-input',
                                                    placeholder=
                                                    "Ask a question about your dashboard data...",
                                                    style={
                                                        'height': '100px',
                                                        'marginBottom': '10px'
                                                    }),
                                                dbc.Button(
                                                    "Get Insights",
                                                    id='submit-question',
                                                    color='primary',
                                                    className='me-2')
                                            ])
                                        ])
                                    ],
                                            width=12)
                                ],
                                        className="mb-4"),

                                # Response Display
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardBody([
                                                html.H4("AI Analysis"),
                                                html.Div(id='ai-response',
                                                         style={
                                                             'whiteSpace': 'pre-wrap',
                                                             'fontFamily': 'Arial, sans-serif',
                                                             'lineHeight': '1.8',
                                                             'padding': '20px',
                                                             'backgroundColor': '#f8f9fa',
                                                             'borderRadius': '8px',
                                                             'fontSize': '15px',
                                                             'color': '#2c3e50',
                                                             'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                                                             'margin': '10px 0'
                                                         })
                                            ])
                                        ])
                                    ],
                                            width=12)
                                ]),

                                # Example Questions
                                html.Div([
                                    html.H5("Example Questions:",
                                            className="mt-3"),
                                    html.Ul([
                                        html.
                                        Li("What is our current attrition rate and how does it compare to our target?"
                                           ),
                                        html.
                                        Li("How has money moved changed over the available fiscal years?"
                                           ),
                                        html.
                                        Li("What are the key trends in donor engagement?"
                                           ),
                                        html.
                                        Li("Which chapters are performing best in terms of ARR?"
                                           ),
                                        html.
                                        Li("What insights can you provide about our pledge performance?"
                                           )
                                    ],
                                            style={'color': 'gray'})
                                ],
                                         id='example-questions')
                            ])
                    ],
                    style={
                        'padding': '30px',
                        'backgroundColor': 'white',
                        'height': '100%'
                    })
            ],
            style={
                'backgroundColor': 'white',
                'flexGrow': 1
            })
    ],
    style={
        'display': 'flex',
        'flexDirection': 'column',
        'height': '100vh'
    })

# Add CSS for KPI numbers
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>OFTW Dashboard</title>
        {%favicon%}
        {%css%}
        <style>
            .kpi-number {
                font-size: 2rem;
                font-weight: bold;
                color: #007BFF;
                text-align: center;
                margin: 10px 0;
            }

            @font-face {
                font-family: 'Poppins';
                src: url('https://fonts.googleapis.com/css2?family=Poppins:wght@600&display=swap');
                font-weight: 600;
                font-style: normal;
            }

            @font-face {
                font-family: 'Inter';
                src: url('https://fonts.googleapis.com/css2?family=Inter:wght@400&display=swap');
                font-weight: 400;
                font-style: normal;
            }
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


# Callbacks for the navigation menu
@app.callback(
    Output("navbar-collapse", "is_open"),
    Input("menu-button", "n_clicks"),
    State("navbar-collapse", "is_open"),
)
def toggle_navbar_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


# Callback to switch between pages
@app.callback([
    Output("page-overview", "style"),
    Output("page-analysis", "style"),
    Output("page-objective", "style"),
    Output("page-money", "style"),
    Output("page-pledge", "style"),
    Output("page-insights", "style"),
    Output("nav-overview", "active"),
    Output("nav-analysis", "active"),
    Output("nav-objective", "active"),
    Output("nav-money", "active"),
    Output("nav-pledge", "active"),
    Output("nav-insights", "active")
], [
    Input("nav-overview", "n_clicks"),
    Input("nav-analysis", "n_clicks"),
    Input("nav-objective", "n_clicks"),
    Input("nav-money", "n_clicks"),
    Input("nav-pledge", "n_clicks"),
    Input("nav-insights", "n_clicks")
])
def switch_page(overview_clicks, analysis_clicks, objective_clicks,
                money_clicks, pledge_clicks, insights_clicks):
    ctx = callback_context

    # Default to Objective and Key Results page if no click
    if not ctx.triggered:
        return [
            {
                'display': 'none'
            },  # overview
            {
                'display': 'none'
            },  # analysis
            {
                'display': 'block'
            },  # objective
            {
                'display': 'none'
            },  # money
            {
                'display': 'none'
            },  # pledge
            {
                'display': 'none'
            },  # insights
            False,
            False,
            True,
            False,
            False,
            False  # nav active states
        ]

    # Get the ID of the component that triggered the callback
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Set display and active states based on which nav item was clicked
    if button_id == "nav-overview":
        return [
            {
                'display': 'block'
            },  # overview
            {
                'display': 'none'
            },  # analysis
            {
                'display': 'none'
            },  # objective
            {
                'display': 'none'
            },  # money
            {
                'display': 'none'
            },  # pledge
            {
                'display': 'none'
            },  # insights
            True,
            False,
            False,
            False,
            False,
            False  # nav active states
        ]
    elif button_id == "nav-analysis":
        return [
            {
                'display': 'none'
            },  # overview
            {
                'display': 'block'
            },  # analysis
            {
                'display': 'none'
            },  # objective
            {
                'display': 'none'
            },  # money
            {
                'display': 'none'
            },  # pledge
            {
                'display': 'none'
            },  # insights
            False,
            True,
            False,
            False,
            False,
            False  # nav active states
        ]
    elif button_id == "nav-objective":
        return [
            {
                'display': 'none'
            },  # overview
            {
                'display': 'none'
            },  # analysis
            {
                'display': 'block'
            },  # objective
            {
                'display': 'none'
            },  # money
            {
                'display': 'none'
            },  # pledge
            {
                'display': 'none'
            },  # insights
            False,
            False,
            True,
            False,
            False,
            False  # nav active states
        ]
    elif button_id == "nav-money":
        return [
            {
                'display': 'none'
            },  # overview
            {
                'display': 'none'
            },  # analysis
            {
                'display': 'none'
            },  # objective
            {
                'display': 'block'
            },  # money
            {
                'display': 'none'
            },  # pledge
            {
                'display': 'none'
            },  # insights
            False,
            False,
            False,
            True,
            False,
            False  # nav active states
        ]
    elif button_id == "nav-pledge":
        return [
            {
                'display': 'none'
            },  # overview
            {
                'display': 'none'
            },  # analysis
            {
                'display': 'none'
            },  # objective
            {
                'display': 'none'
            },  # money
            {
                'display': 'block'
            },  # pledge
            {
                'display': 'none'
            },  # insights
            False,
            False,
            False,
            False,
            True,
            False  # nav active states
        ]
    elif button_id == "nav-insights":
        return [
            {
                'display': 'none'
            },  # overview
            {
                'display': 'none'
            },  # analysis
            {
                'display': 'none'
            },  # objective
            {
                'display': 'none'
            },  # money
            {
                'display': 'none'
            },  # pledge
            {
                'display': 'block'
            },  # insights
            False,
            False,
            False,
            False,
            False,
            True  # nav active states
        ]


# Callbacks for KPIs and Charts
@app.callback(Output("money-moved-kpi", "children"),
              [Input("fiscal-year-dropdown", "value")])
def update_money_moved(fiscal_year):
    if not fiscal_year:
        return "No data"

    total_amount = calculate_money_moved(df_payments_converted, fiscal_year)
    return f"${total_amount:,.2f}"


@app.callback(Output("counterfactual-mm-kpi", "children"),
              [Input("fiscal-year-dropdown", "value")])
def update_counterfactual_mm(fiscal_year):
    if not fiscal_year:
        return "No data"

    total_cf = calculate_counterfactual_mm(counterfactual_df, fiscal_year)
    return f"${total_cf:,.2f}"


@app.callback(Output("active-arr-kpi", "children"),
              [Input("fiscal-year-dropdown", "value")])
def update_active_arr(fiscal_year):
    if not fiscal_year:
        return "No data"

    # Get fiscal year date range
    start_date, end_date = get_fiscal_year_range(fiscal_year)

    # Filter pledges for the fiscal year and get active donors
    active_pledges = df_pledges_converted[
        (df_pledges_converted['pledge_status'] == 'Active donor')
        & (df_pledges_converted['pledge_starts_at'] >= start_date) &
        (df_pledges_converted['pledge_starts_at'] <= end_date)].copy()

    # Calculate yearly value (monthly amount * 12)
    active_pledges['annual_value'] = active_pledges['amount_usd'] * 12

    # Sum up total ARR
    total_arr = active_pledges['annual_value'].sum()

    return f"${total_arr:,.2f}"


@app.callback(Output("attrition-kpi", "children"),
              [Input("fiscal-year-dropdown", "value")])
def update_attrition_rate(fiscal_year):
    if not fiscal_year:
        return "No data"

    start_date, end_date = get_fiscal_year_range(fiscal_year)
    filtered_pledges = df_pledges_converted[
        (df_pledges_converted['pledge_starts_at'] >= start_date)
        & (df_pledges_converted['pledge_starts_at'] <= end_date)]
    attrition_rate = calculate_pledge_attrition_rate(filtered_pledges)
    return f"{attrition_rate:.1f}%"


@app.callback(Output("active-donors-kpi", "children"),
              [Input("fiscal-year-dropdown", "value")])
def update_active_donors(fiscal_year):
    if not fiscal_year:
        return "No data"

    start_date, end_date = get_fiscal_year_range(fiscal_year)
    filtered_pledges = df_pledges_converted[
        (df_pledges_converted['pledge_starts_at'] >= start_date)
        & (df_pledges_converted['pledge_starts_at'] <= end_date)]
    active_donors_count = count_active_donors(filtered_pledges)
    return f"{active_donors_count:,}"


@app.callback(Output("active-pledges-kpi", "children"),
              [Input("fiscal-year-dropdown", "value")])
def update_active_pledges(fiscal_year):
    if not fiscal_year:
        return "No data"

    start_date, end_date = get_fiscal_year_range(fiscal_year)
    filtered_pledges = df_pledges_converted[
        (df_pledges_converted['pledge_starts_at'] >= start_date)
        & (df_pledges_converted['pledge_starts_at'] <= end_date)]
    active_pledges_count = count_active_pledges(filtered_pledges)
    return f"{active_pledges_count:,}"


@app.callback(Output("chapter-arr-chart", "figure"),
              [Input("fiscal-year-dropdown", "value")])
def update_chapter_arr_chart(fiscal_year):
    try:
        chapter_arr_data = calculate_chapter_arr(df_pledges_converted,
                                                 fiscal_year)

        if chapter_arr_data.empty:
            fig = go.Figure()
            fig.update_layout(title_text='No chapter data available',
                              plot_bgcolor='white',
                              height=400)
            return fig

        # Sort by annual value
        chapter_arr_data = chapter_arr_data.sort_values('annual_value',
                                                        ascending=False)

        # Create the bar chart
        fig = px.bar(chapter_arr_data,
                     x='chapter_type',
                     y='annual_value',
                     title="Chapter ARR by Type",
                     labels={
                         'chapter_type': 'Chapter Type',
                         'annual_value': 'Annual Value (USD)'
                     },
                     color_discrete_sequence=[COLORS['primary']])

        # Update layout
        fig.update_layout(plot_bgcolor='white',
                          margin=dict(l=40, r=40, t=40, b=40),
                          yaxis_tickprefix='$',
                          yaxis_tickformat=',.0f',
                          showlegend=False,
                          height=400)

        # Add a target line at $670,000
        fig.add_shape(type="line",
                      line=dict(dash="dash", color=COLORS['accent']),
                      y0=670000,
                      y1=670000,
                      x0=-0.5,
                      x1=len(chapter_arr_data) - 0.5)

        return fig

    except Exception as e:
        print(f"Error in chapter ARR chart: {e}")
        fig = go.Figure()
        fig.update_layout(title_text='Error loading chart',
                          plot_bgcolor='white',
                          height=400)
        return fig


@app.callback(Output("money-moved-chart", "figure"),
              [Input("fiscal-year-dropdown", "value")])
def update_money_moved_chart(fiscal_year):
    if not fiscal_year:
        # Return empty figure with same structure
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.update_layout(title_text='Money Moved by Month (No Data)',
                          plot_bgcolor='white',
                          paper_bgcolor='white',
                          height=400)
        return fig

    try:
        # Get fiscal year date range
        start_date, end_date = get_fiscal_year_range(fiscal_year)

        # Filter data for the selected fiscal year
        filtered_data = df_payments_converted[
            (df_payments_converted['date'] >= start_date)
            & (df_payments_converted['date'] <= end_date)].copy()

        if filtered_data.empty:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.update_layout(
                title_text=f'No data available for {fiscal_year}',
                plot_bgcolor='white',
                paper_bgcolor='white',
                height=400)
            return fig

        # Group by month
        filtered_data['month'] = filtered_data['date'].dt.to_period('M')
        monthly_data = filtered_data.groupby(
            'month')['amount_usd'].sum().reset_index()
        monthly_data['month'] = monthly_data['month'].dt.to_timestamp()

        # Calculate cumulative sum
        monthly_data['cumulative'] = monthly_data['amount_usd'].cumsum()

        # Create figure with two y-axes
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Add monthly bars
        fig.add_trace(
            go.Bar(x=monthly_data['month'],
                   y=monthly_data['amount_usd'],
                   name="Monthly Money Moved",
                   marker_color=COLORS['primary']),
            secondary_y=False,
        )

        # Add cumulative line
        fig.add_trace(
            go.Scatter(x=monthly_data['month'],
                       y=monthly_data['cumulative'],
                       name="Cumulative Money Moved",
                       line=dict(color=COLORS['accent'], width=3),
                       mode='lines+markers'),
            secondary_y=True,
        )

        # Update layout
        fig.update_layout(title_text='Money Moved by Month',
                          plot_bgcolor='white',
                          paper_bgcolor='white',
                          hovermode="x unified",
                          legend=dict(orientation="h",
                                      yanchor="bottom",
                                      y=1.02,
                                      xanchor="center",
                                      x=0.5),
                          height=400,
                          margin=dict(l=40, r=40, t=80, b=40))

        # Update y-axes with grid
        fig.update_yaxes(title_text="Monthly Money Moved (USD)",
                         secondary_y=False,
                         tickprefix='$',
                         tickformat=',.0f',
                         gridcolor='lightgray',
                         gridwidth=1,
                         showgrid=True,
                         zeroline=True,
                         zerolinecolor='lightgray',
                         zerolinewidth=1)

        fig.update_yaxes(title_text="Cumulative Money Moved (USD)",
                         secondary_y=True,
                         tickprefix='$',
                         tickformat=',.0f',
                         gridcolor='lightgray',
                         gridwidth=1,
                         showgrid=True)

        # Update x-axis with grid
        fig.update_xaxes(title_text="Month",
                         gridcolor='lightgray',
                         gridwidth=1,
                         showgrid=True)

        return fig

    except Exception as e:
        print(f"Error in money moved chart: {e}")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.update_layout(title_text='Error loading chart',
                          plot_bgcolor='white',
                          paper_bgcolor='white',
                          height=400)
        return fig


# Money Moved Page Callbacks
@app.callback([
    Output("mm-total-kpi", "children"),
    Output("mm-counterfactual-kpi", "children"),
    Output("mm-monthly-avg-kpi", "children")
], [Input("mm-fiscal-year-dropdown", "value")])
def update_mm_kpis(fiscal_year):
    if not fiscal_year:
        return "No data", "No data", "No data"

    # Calculate Total Money Moved
    total_mm = calculate_money_moved(df_payments_converted, fiscal_year)

    # Calculate Counterfactual Money Moved
    counterfactual_mm = calculate_counterfactual_mm(df_payments_converted,
                                                    fiscal_year)

    # Calculate Monthly Average
    start_date, end_date = get_fiscal_year_range(fiscal_year)
    months_diff = (end_date.year - start_date.year) * 12 + (
        end_date.month - start_date.month) + 1
    monthly_avg = total_mm / months_diff if months_diff > 0 else 0

    return f"${total_mm:,.2f}", f"${counterfactual_mm:,.2f}", f"${monthly_avg:,.2f}"


@app.callback([
    Output("mm-trends-chart", "figure"),
    Output("mm-platform-chart", "figure"),
    Output("mm-source-chart", "figure"),
    Output("mm-recurring-chart", "figure"),
    Output("mm-heatmap-chart", "figure")
], [Input("mm-fiscal-year-dropdown", "value")])
def update_mm_breakdown_charts(fiscal_year):
    if not fiscal_year:
        empty_fig = go.Figure()
        empty_fig.update_layout(title="No data available",
                                plot_bgcolor='white',
                                paper_bgcolor='white')
        return empty_fig, empty_fig, empty_fig, empty_fig, empty_fig

    start_date, end_date = get_fiscal_year_range(fiscal_year)

    try:
        # Filter data for selected fiscal year
        filtered_payments = df_payments_converted[
            (df_payments_converted['date'] >= start_date)
            & (df_payments_converted['date'] <= end_date)].copy()

        # 1. Platform Distribution (using df_payments_converted)
        platform_data = filtered_payments.groupby(
            'payment_platform')['amount_usd'].sum().reset_index()
        platform_fig = px.pie(
            platform_data,
            values='amount_usd',
            names='payment_platform',
            title="Money Moved by Platform",
            color_discrete_sequence=px.colors.qualitative.Set3)
        platform_fig.update_traces(textinfo='percent+label')
        platform_fig.update_layout(showlegend=True,
                                   legend_title="Payment Platform",
                                   plot_bgcolor='white',
                                   paper_bgcolor='white')

        # 2. Chapter/Source Breakdown (using Merged_INNER)
        filtered_merged = Merged_INNER[(Merged_INNER['date'] >= start_date) & (
            Merged_INNER['date'] <= end_date)].copy()

        chapter_data = filtered_merged.groupby(
            'chapter_type')['amount_usd_y'].sum().reset_index()
        chapter_data = chapter_data.sort_values('amount_usd_y', ascending=True)
        source_fig = px.bar(chapter_data,
                            x='amount_usd_y',
                            y='chapter_type',
                            orientation='h',
                            title="Money Moved by Chapter Type",
                            color_discrete_sequence=[COLORS['primary']])
        source_fig.update_layout(xaxis_title="Amount (USD)",
                                 yaxis_title="Chapter Type",
                                 plot_bgcolor='white',
                                 paper_bgcolor='white')
        source_fig.update_xaxes(tickprefix="$",
                                tickformat=",",
                                gridcolor='lightgray',
                                gridwidth=1,
                                showgrid=True)
        source_fig.update_yaxes(gridcolor='lightgray',
                                gridwidth=1,
                                showgrid=True)

        # 3. Recurring vs One-Time (using Merged_INNER)
        filtered_merged['payment_type'] = filtered_merged['frequency'].map(
            lambda x: 'One-Time' if x == 'One-Time' else 'Recurring')
        recurrence_data = filtered_merged.groupby(
            'payment_type')['amount_usd_y'].sum().reset_index()
        recurring_fig = px.pie(
            recurrence_data,
            values='amount_usd_y',
            names='payment_type',
            title="Recurring vs One-Time Donations",
            color_discrete_sequence=px.colors.qualitative.Set2)
        recurring_fig.update_traces(textinfo='percent+label')
        recurring_fig.update_layout(showlegend=True,
                                    legend_title="Payment Type",
                                    plot_bgcolor='white',
                                    paper_bgcolor='white')

        # 4. Platform Performance Heatmap (using df_payments_converted)
        df_heatmap = filtered_payments.copy()
        df_heatmap['month'] = df_heatmap['date'].dt.strftime('%Y-%m')
        heatmap_data = df_heatmap.pivot_table(values='amount_usd',
                                              index='month',
                                              columns='payment_platform',
                                              aggfunc='sum').fillna(0)

        heatmap_fig = px.imshow(heatmap_data,
                                title="Platform Performance Over Time",
                                color_continuous_scale="RdYlBu",
                                aspect="auto")
        heatmap_fig.update_layout(xaxis_title="Payment Platform",
                                  yaxis_title="Month",
                                  plot_bgcolor='white',
                                  paper_bgcolor='white')

        # 5. Money Moved Trends
        df = filtered_payments.copy()
        df['month'] = df['date'].dt.to_period('M')
        monthly_total = df.groupby('month')['amount_usd'].sum().reset_index()
        monthly_total['month'] = monthly_total['month'].dt.to_timestamp()
        monthly_total['cumulative'] = monthly_total['amount_usd'].cumsum()

        trends_fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Total Money Moved Bars
        trends_fig.add_trace(go.Bar(x=monthly_total['month'],
                                    y=monthly_total['amount_usd'],
                                    name="Monthly Total",
                                    marker_color=COLORS['primary']),
                             secondary_y=False)

        # Cumulative Line
        trends_fig.add_trace(go.Scatter(x=monthly_total['month'],
                                        y=monthly_total['cumulative'],
                                        name="Cumulative Total",
                                        line=dict(color=COLORS['accent'],
                                                  width=3)),
                             secondary_y=True)

        trends_fig.update_layout(title="Money Moved Trends",
                                 height=400,
                                 hovermode="x unified",
                                 showlegend=True,
                                 plot_bgcolor='white',
                                 paper_bgcolor='white',
                                 xaxis_title="Month",
                                 yaxis_title="Monthly Total (USD)",
                                 yaxis2_title="Cumulative Total (USD)")

        # Update axes formatting
        trends_fig.update_xaxes(gridcolor='lightgray',
                                gridwidth=1,
                                showgrid=True)
        trends_fig.update_yaxes(tickprefix="$",
                                tickformat=",",
                                gridcolor='lightgray',
                                gridwidth=1,
                                showgrid=True,
                                secondary_y=False)
        trends_fig.update_yaxes(tickprefix="$",
                                tickformat=",",
                                gridcolor='lightgray',
                                gridwidth=1,
                                showgrid=True,
                                secondary_y=True)

        return trends_fig, platform_fig, source_fig, recurring_fig, heatmap_fig

    except Exception as e:
        print(f"Error in update_mm_breakdown_charts: {e}")
        empty_fig = go.Figure()
        empty_fig.update_layout(title=f"Error: {str(e)}",
                                plot_bgcolor='white',
                                paper_bgcolor='white')
        return empty_fig, empty_fig, empty_fig, empty_fig, empty_fig


# Add new callbacks for Pledge Performance page
@app.callback([
    Output("total-pledges-kpi", "children"),
    Output("active-pledges-count-kpi", "children"),
    Output("future-pledges-kpi", "children"),
    Output("total-arr-kpi", "children"),
    Output("active-arr-value-kpi", "children"),
    Output("future-arr-kpi", "children")
], [
    Input("pledge-fiscal-year-dropdown", "value"),
    Input("pledge-month-slider", "value")
])
def update_pledge_kpis(fiscal_year, month_range):
    if not fiscal_year:
        return "No data", "No data", "No data", "No data", "No data", "No data"

    try:
        # Get fiscal year range
        start_date, end_date = get_fiscal_year_range(fiscal_year)

        # Get selected month range (0-based to 1-based)
        start_month, end_month = [m + 1 for m in month_range]

        # Create copy of pledges data
        pledges = df_pledges_converted.copy()

        # First filter by fiscal year
        mask_fiscal_year = (pledges['pledge_starts_at'] >= start_date) & \
                          (pledges['pledge_starts_at'] <= end_date)
        pledges = pledges[mask_fiscal_year]

        # Convert dates to fiscal months (Jul=1, Jun=12)
        pledges['fiscal_month'] = pledges['pledge_starts_at'].apply(
            lambda x: (x.month - 6) % 12 + 1 if x.month >= 7 else x.month + 6)

        # Apply month range filter
        mask_months = (pledges['fiscal_month'] >= start_month) & \
                     (pledges['fiscal_month'] <= end_month)
        pledges = pledges[mask_months]

        # Calculate pledge counts
        total_pledges = pledges[pledges['pledge_status'].isin(
            ['Active donor', 'Pledged donor'])].shape[0]

        active_pledges = pledges[pledges['pledge_status'] ==
                                 'Active donor'].shape[0]

        future_pledges = pledges[pledges['pledge_status'] ==
                                 'Pledged donor'].shape[0]

        # Calculate ARR values
        def calculate_arr(df, status):
            df_filtered = df[df['pledge_status'] == status].copy()
            df_filtered['multiplier'] = df_filtered['frequency'].map({
                'monthly':
                12,
                'quarterly':
                4,
                'annually':
                1,
                'One-Time':
                1
            }).fillna(1)
            return (df_filtered['amount_usd'] *
                    df_filtered['multiplier']).sum()

        active_arr = calculate_arr(pledges, 'Active donor')
        future_arr = calculate_arr(pledges, 'Pledged donor')
        total_arr = active_arr + future_arr

        # Format output values
        return (f"{total_pledges:,}", f"{active_pledges:,}",
                f"{future_pledges:,}", f"${total_arr:,.2f}",
                f"${active_arr:,.2f}", f"${future_arr:,.2f}")

    except Exception as e:
        print(f"Error in update_pledge_kpis: {e}")
        return "Error", "Error", "Error", "Error", "Error", "Error"


@app.callback([
    Output("pledge-trends-chart", "figure"),
    Output("arr-growth-chart", "figure"),
    Output("attrition-trend-chart", "figure"),
    Output("chapter-performance-chart", "figure")
], [
    Input("pledge-fiscal-year-dropdown", "value"),
    Input("pledge-month-slider", "value")
])
def update_pledge_charts(fiscal_year, month_range):
    if not fiscal_year:
        empty_fig = go.Figure()
        empty_fig.update_layout(title="No data available")
        return empty_fig, empty_fig, empty_fig, empty_fig

    try:
        start_date, end_date = get_fiscal_year_range(fiscal_year)

        # Get the selected month range
        start_month, end_month = month_range
        start_month += 1  # Convert to 1-based month numbers
        end_month += 1

        # Handle fiscal year spanning across calendar years
        filtered_pledges = df_pledges_converted.copy()

        # First filter by fiscal year
        mask_fiscal_year = (filtered_pledges['pledge_starts_at'] >= start_date) & \
                          (filtered_pledges['pledge_starts_at'] <= end_date)

        filtered_pledges = filtered_pledges[mask_fiscal_year]

        # Adjust months for fiscal year (July = 1, June = 12)
        filtered_pledges['fiscal_month'] = filtered_pledges[
            'pledge_starts_at'].apply(lambda x: (x.month - 6) % 12 + 1
                                      if x.month >= 7 else x.month + 6)

        # Apply month range filter
        mask_months = (filtered_pledges['fiscal_month'] >= start_month) & \
                     (filtered_pledges['fiscal_month'] <= end_month)

        filtered_pledges = filtered_pledges[mask_months]

        # 1. Pledge Trends Chart
        filtered_pledges.loc[:, 'month'] = filtered_pledges[
            'pledge_starts_at'].dt.to_period('M')
        pledge_trends = filtered_pledges.groupby(
            ['month', 'pledge_status']).size().unstack(fill_value=0)
        pledge_trends.index = pledge_trends.index.astype(str)

        pledge_fig = go.Figure()
        for status in ['Active donor', 'Pledged donor']:
            if status in pledge_trends.columns:
                pledge_fig.add_trace(
                    go.Scatter(x=pledge_trends.index,
                               y=pledge_trends[status],
                               name=status,
                               stackgroup='one'))

        pledge_fig.update_layout(title="Monthly Pledge Volume by Status",
                                 xaxis_title="Month",
                                 yaxis_title="Number of Pledges",
                                 showlegend=True,
                                 plot_bgcolor='white',
                                 paper_bgcolor='white')
        pledge_fig.update_xaxes(showgrid=True,
                                gridwidth=1,
                                gridcolor='LightGray')
        pledge_fig.update_yaxes(showgrid=True,
                                gridwidth=1,
                                gridcolor='LightGray')

        # 2. ARR Growth Chart
        freq_map = {
            'monthly': 12,
            'quarterly': 4,
            'annually': 1,
            'One-Time': 1
        }
        filtered_pledges.loc[:,
                             'multiplier'] = filtered_pledges['frequency'].map(
                                 freq_map).fillna(1)
        filtered_pledges.loc[:, 'annual_value'] = filtered_pledges[
            'amount_usd'] * filtered_pledges['multiplier']

        arr_trends = filtered_pledges.groupby(
            ['month',
             'pledge_status'])['annual_value'].sum().unstack(fill_value=0)
        arr_trends.index = arr_trends.index.astype(str)

        arr_fig = go.Figure()
        for status in ['Active donor', 'Pledged donor']:
            if status in arr_trends.columns:
                arr_fig.add_trace(
                    go.Scatter(x=arr_trends.index,
                               y=arr_trends[status],
                               name=status,
                               stackgroup='one',
                               fill='tonexty'))

        arr_fig.update_layout(title="Monthly ARR Growth",
                              xaxis_title="Month",
                              yaxis_title="Annual Recurring Revenue (USD)",
                              showlegend=True,
                              plot_bgcolor='white',
                              paper_bgcolor='white')
        arr_fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
        arr_fig.update_yaxes(showgrid=True,
                             gridwidth=1,
                             gridcolor='LightGray',
                             tickprefix="$",
                             tickformat=",")

        # 3. Attrition Rate Chart
        monthly_status = filtered_pledges.groupby(
            'month')['pledge_status'].value_counts().unstack(fill_value=0)
        monthly_status.index = monthly_status.index.astype(str)

        total_pledges = monthly_status.sum(axis=1)
        churned_pledges = monthly_status.get(
            'Churned donor', 0) + monthly_status.get('Payment failure', 0)
        attrition_rate = (churned_pledges / total_pledges * 100).fillna(0)

        attrition_fig = go.Figure()
        attrition_fig.add_trace(
            go.Scatter(x=attrition_rate.index,
                       y=attrition_rate.values,
                       mode='lines+markers'))

        attrition_fig.update_layout(title="Monthly Attrition Rate",
                                    xaxis_title="Month",
                                    yaxis_title="Attrition Rate (%)",
                                    showlegend=False,
                                    plot_bgcolor='white',
                                    paper_bgcolor='white')
        attrition_fig.update_xaxes(showgrid=True,
                                   gridwidth=1,
                                   gridcolor='LightGray')
        attrition_fig.update_yaxes(showgrid=True,
                                   gridwidth=1,
                                   gridcolor='LightGray',
                                   ticksuffix="%")

        # 4. Chapter Performance Chart
        chapter_perf = filtered_pledges.groupby(['month',
                                                 'chapter_type']).agg({
                                                     'pledge_id':
                                                     'count',
                                                     'annual_value':
                                                     'sum'
                                                 }).reset_index()
        chapter_perf = chapter_perf.sort_values(['month', 'annual_value'],
                                                ascending=[True, True])

        chapter_fig = go.Figure()

        for chapter in chapter_perf['chapter_type'].unique():
            chapter_data = chapter_perf[chapter_perf['chapter_type'] ==
                                        chapter]
            chapter_fig.add_trace(
                go.Scatter(x=chapter_data['month'].astype(str),
                           y=chapter_data['annual_value'],
                           name=chapter,
                           mode='lines+markers'))

        chapter_fig.update_layout(title="Monthly Chapter Performance",
                                  xaxis_title="Month",
                                  yaxis_title="Annual Value (USD)",
                                  showlegend=True,
                                  legend_title="Chapter Type",
                                  hovermode="x unified",
                                  plot_bgcolor='white',
                                  paper_bgcolor='white')
        chapter_fig.update_xaxes(showgrid=True,
                                 gridwidth=1,
                                 gridcolor='LightGray')
        chapter_fig.update_yaxes(showgrid=True,
                                 gridwidth=1,
                                 gridcolor='LightGray',
                                 tickprefix="$",
                                 tickformat=",")

        return pledge_fig, arr_fig, attrition_fig, chapter_fig

    except Exception as e:
        print(f"Error in update_pledge_charts: {e}")
        empty_fig = go.Figure()
        empty_fig.update_layout(title=f"Error: {str(e)}")
        return empty_fig, empty_fig, empty_fig, empty_fig


# Add this function before the callback
def prepare_dashboard_context(df_payments, df_pledges, fiscal_year=None):
    """Prepare comprehensive context about the dashboard data for AI analysis"""
    try:
        # Get fiscal year range
        if fiscal_year:
            start_date, end_date = get_fiscal_year_range(fiscal_year)
            filtered_payments = df_payments[(df_payments['date'] >= start_date) & 
                                         (df_payments['date'] <= end_date)]
            filtered_pledges = df_pledges[(df_pledges['pledge_starts_at'] >= start_date) & 
                                        (df_pledges['pledge_starts_at'] <= end_date)]
        else:
            filtered_payments = df_payments
            filtered_pledges = df_pledges

        # Objective & Key Metrics
        key_metrics = {
            'total_money_moved': calculate_money_moved(filtered_payments, fiscal_year),
            'counterfactual_mm': calculate_counterfactual_mm(filtered_payments, fiscal_year),
            'active_arr': calculate_arr_by_channel(filtered_pledges, fiscal_year),
            'attrition_rate': calculate_pledge_attrition_rate(filtered_pledges),
            'active_donors': count_active_donors(filtered_pledges),
            'active_pledges': count_active_pledges(filtered_pledges)
        }

        # Money Moved Analysis
        money_moved = {
            'total_mm': calculate_money_moved(filtered_payments, fiscal_year),
            'monthly_avg': key_metrics['total_money_moved'] / 12 if fiscal_year else 0,
            'platform_distribution': filtered_payments.groupby('payment_platform')['amount_usd'].sum().to_dict(),
            'recurring_vs_onetime': filtered_pledges.groupby('frequency')['amount_usd'].sum().to_dict()
        }

        # Pledge Performance
        pledge_metrics = {
            'total_pledges': filtered_pledges[filtered_pledges['pledge_status'].isin(['Active donor', 'Pledged donor'])].shape[0],
            'active_pledges': filtered_pledges[filtered_pledges['pledge_status'] == 'Active donor'].shape[0],
            'future_pledges': filtered_pledges[filtered_pledges['pledge_status'] == 'Pledged donor'].shape[0],
            'chapter_performance': filtered_pledges.groupby('chapter_type')['amount_usd'].sum().to_dict()
        }

        return f"""
        Dashboard Context for {fiscal_year if fiscal_year else 'All Time'}:

        Key Metrics:
        - Total Money Moved: ${key_metrics['total_money_moved']:,.2f}
        - Counterfactual Money Moved: ${key_metrics['counterfactual_mm']:,.2f}
        - Active ARR: ${key_metrics['active_arr']:,.2f}
        - Attrition Rate: {key_metrics['attrition_rate']:.1f}%
        - Active Donors: {key_metrics['active_donors']}
        - Active Pledges: {key_metrics['active_pledges']}

        Money Moved Analysis:
        - Total Money Moved: ${money_moved['total_mm']:,.2f}
        - Monthly Average: ${money_moved['monthly_avg']:,.2f}
        - Platform Distribution: {money_moved['platform_distribution']}
        - Payment Types: {money_moved['recurring_vs_onetime']}

        Pledge Performance:
        - Total Pledges: {pledge_metrics['total_pledges']}
        - Active Pledges: {pledge_metrics['active_pledges']}
        - Future Pledges: {pledge_metrics['future_pledges']}
        - Chapter Performance: {pledge_metrics['chapter_performance']}

        Available Fiscal Years: {', '.join(available_fiscal_years)}
        """
    except Exception as e:
        return f"Error preparing context: {str(e)}"


# Update the AI Insights callback
@app.callback(
    Output('ai-response', 'children'), [Input('submit-question', 'n_clicks')],
    [State('question-input', 'value'),
     State("fiscal-year-dropdown", "value")]
)
def get_ai_insights(n_clicks, question, current_fiscal_year):
    if not n_clicks or not question:
        return "Ask a question to get insights..."

    try:
        # Prepare context about the dashboard data
        dashboard_context = prepare_dashboard_context(df_payments_converted,
                                                      df_pledges_converted,
                                                      current_fiscal_year)

        # Construct the prompt with context
        prompt = f"""
        You are an AI analyst for the One for the World (OFTW) charity dashboard. 
        Use the following context to answer questions about the dashboard data:

        {dashboard_context}

        Question: {question}

        Please provide a clear, concise analysis based on the available data. 
        If you need specific data that's not available in the context, please mention that.
        """

        # Generate response using the model
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        # Add specific instructions for financial analysis
        enhanced_prompt = f"""
        {prompt}

        Please analyze the data and provide:
        1. Key observations about the metrics
        2. Comparison with targets where available
        3. Actionable insights based on the trends

        Format the response in a clear, structured way.
        """

        response = model.generate_content(enhanced_prompt)

        # Check if response was blocked
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            return f"Response was blocked due to safety concerns: {response.prompt_feedback.block_reason}"

        # Return the response text with formatting
        if response.text:
            formatted_text = response.text.replace('**', '').replace('*', '•')  # Convert markdown to bullet points
            formatted_text = formatted_text.replace('<br><br>', '\n\n')  # Convert double breaks to newlines
            formatted_text = formatted_text.replace('<br>', '\n')  # Convert single breaks to newlines
            return formatted_text
        else:
            return "No response generated. Please try rephrasing your question."

    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            return "Error: Unable to access the AI model. Please check your API key and ensure you have access to the Gemini API."
        elif "403" in error_msg:
            return "Error: Authentication failed. Please check your API key."
        else:
            return f"Error: {error_msg}"


def analyze_dashboard_metrics(question, df_payments, df_pledges, fiscal_year):
    """Analyzes dashboard metrics and answers a given question using prepared context."""
    context = prepare_dashboard_context(df_payments, df_pledges, fiscal_year)
    # Implement your logic here to analyze the context and answer the question.
    # You can use libraries like spaCy or transformers for NLP tasks.
    # This is a placeholder, replace with actual analysis.
    return f"Analysis for question '{question}' based on context:\n{context}"



if __name__ == '__main__':
    app.run(host="0.0.0.0",port=8080,debug=False)
