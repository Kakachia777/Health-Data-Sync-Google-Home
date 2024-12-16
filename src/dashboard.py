import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Any

class HealthDashboard:
    def __init__(self, port: int = 8050):
        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.port = port
        self.setup_layout()
        self.setup_callbacks()
        
    def setup_layout(self):
        """Create the dashboard layout"""
        self.app.layout = dbc.Container([
            dbc.Row([
                dbc.Col(html.H1("Health Metrics Dashboard", className="text-center mb-4"), width=12)
            ]),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Weight Trend"),
                        dbc.CardBody(dcc.Graph(id='weight-graph'))
                    ])
                ], width=6),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Blood Pressure History"),
                        dbc.CardBody(dcc.Graph(id='bp-graph'))
                    ])
                ], width=6)
            ]),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Heart Rate Variability"),
                        dbc.CardBody(dcc.Graph(id='hr-graph'))
                    ])
                ], width=6),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Sleep Pattern"),
                        dbc.CardBody(dcc.Graph(id='sleep-graph'))
                    ])
                ], width=6)
            ], className="mt-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Health Alerts"),
                        dbc.CardBody(html.Div(id='alerts-div'))
                    ])
                ], width=12)
            ], className="mt-4"),
            
            dcc.Interval(
                id='interval-component',
                interval=60*1000,  # update every minute
                n_intervals=0
            )
        ], fluid=True)
        
    def setup_callbacks(self):
        """Set up dashboard callbacks"""
        @self.app.callback(
            [Output('weight-graph', 'figure'),
             Output('bp-graph', 'figure'),
             Output('hr-graph', 'figure'),
             Output('sleep-graph', 'figure'),
             Output('alerts-div', 'children')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_graphs(n):
            # Get the latest data (implement data fetching logic)
            weight_df = self.get_weight_data()
            bp_df = self.get_bp_data()
            hr_df = self.get_hr_data()
            sleep_df = self.get_sleep_data()
            alerts = self.get_alerts()
            
            # Create weight trend graph
            weight_fig = px.line(weight_df, x='timestamp', y='value',
                               title='Weight Trend Over Time')
            weight_fig.update_traces(mode='lines+markers')
            
            # Create blood pressure graph
            bp_fig = go.Figure()
            bp_fig.add_trace(go.Scatter(x=bp_df['timestamp'], y=bp_df['systolic'],
                                      name='Systolic', mode='lines+markers'))
            bp_fig.add_trace(go.Scatter(x=bp_df['timestamp'], y=bp_df['diastolic'],
                                      name='Diastolic', mode='lines+markers'))
            
            # Create heart rate variability graph
            hr_fig = px.line(hr_df, x='timestamp', y='value',
                            title='Heart Rate Variability')
            hr_fig.add_trace(go.Scatter(x=hr_df['timestamp'], y=hr_df['variability'],
                                      name='Variability', mode='lines'))
            
            # Create sleep pattern graph
            sleep_fig = px.bar(sleep_df, x='date', y='duration',
                             title='Sleep Duration',
                             color='quality')
            
            # Format alerts
            alerts_div = [
                dbc.Alert(alert, color='warning' if '⚠️' in alert else 'info')
                for alert in alerts
            ]
            
            return weight_fig, bp_fig, hr_fig, sleep_fig, alerts_div
            
    def get_weight_data(self) -> pd.DataFrame:
        """Placeholder for weight data retrieval"""
        # Implement actual data retrieval logic
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
        values = np.random.normal(75, 2, len(dates))
        return pd.DataFrame({'timestamp': dates, 'value': values})
        
    def get_bp_data(self) -> pd.DataFrame:
        """Placeholder for blood pressure data retrieval"""
        # Implement actual data retrieval logic
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
        systolic = np.random.normal(120, 5, len(dates))
        diastolic = np.random.normal(80, 5, len(dates))
        return pd.DataFrame({
            'timestamp': dates,
            'systolic': systolic,
            'diastolic': diastolic
        })
        
    def get_hr_data(self) -> pd.DataFrame:
        """Placeholder for heart rate data retrieval"""
        # Implement actual data retrieval logic
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='H')
        values = np.random.normal(70, 10, len(dates))
        variability = np.random.normal(10, 2, len(dates))
        return pd.DataFrame({
            'timestamp': dates,
            'value': values,
            'variability': variability
        })
        
    def get_sleep_data(self) -> pd.DataFrame:
        """Placeholder for sleep data retrieval"""
        # Implement actual data retrieval logic
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
        durations = np.random.normal(7, 1, len(dates))
        quality = np.random.choice(['Good', 'Fair', 'Poor'], len(dates))
        return pd.DataFrame({
            'date': dates,
            'duration': durations,
            'quality': quality
        })
        
    def get_alerts(self) -> List[str]:
        """Placeholder for alerts retrieval"""
        # Implement actual alerts retrieval logic
        return [
            "⚠️ Blood pressure trending high",
            "ℹ️ Sleep duration below target",
            "ℹ️ Weight trend stable"
        ]
        
    def run(self):
        """Run the dashboard server"""
        self.app.run_server(debug=True, port=self.port) 