import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

money_moved_layout = html.Div([
    html.H2(" Money Moved", className="text-center my-4"),

    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H4("Total Money Moved", className="card-title"),
                html.H2("$8.2M", className="text-success")
            ])
        ], color="light", className="shadow-sm rounded-3 p-2")),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H4("Counterfactual Money Moved", className="card-title"),
                html.H2("$7.3M", className="text-primary")
            ])
        ], color="light", className="shadow-sm rounded-3 p-2")),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H4("Average Gift Size (USD)", className="card-title"),
                html.H2("$124", className="text-secondary")
            ])
        ], color="light", className="shadow-sm rounded-3 p-2"))
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            html.H5("Money Moved Over Time", className="mb-2"),
            dcc.Graph(id='money-moved-time-chart')
        ])
    ]),

    dbc.Row([
        dbc.Col([
            html.H5("Breakdown by Platform", className="mt-4"),
            dcc.Graph(id='money-platform-bar')
        ], md=6),

        dbc.Col([
            html.H5("Breakdown by Channel", className="mt-4"),
            dcc.Graph(id='money-channel-bar')
        ], md=6)
    ])
])

if __name__ == '__main__':
    app.layout = money_moved_layout
    app.run(debug=True)
