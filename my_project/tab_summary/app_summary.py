import dash_bootstrap_components as dbc
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
import dash
import pandas as pd
from dash.exceptions import PreventUpdate
from app import app, cache, TIMEOUT
from my_project.tab_summary.charts_summary import world_map
from my_project.template_graphs import violin
from my_project.utils import generate_chart_name, title_with_tooltip
import plotly.graph_objects as go
from my_project.global_scheme import template, tight_margins
import requests
from my_project.extract_df import get_data


# @code_timer
def layout_summary():
    """Contents in the second tab 'Climate Summary'."""
    return html.Div(
        className="container-col",
        id="tab-two-container",
        children=[
            html.Div(
                className="container-col",
                id="tab2-sec1-container",
                children=[
                    dcc.Loading(
                        type="circle",
                        children=html.Div(
                            className="container-col",
                            id="location-info",
                            style={"padding": "12px"},
                        ),
                    ),
                    dcc.Loading(
                        type="circle",
                        children=html.Div(className="tab-two-section", id="world-map"),
                    ),
                    html.Div(
                        children=title_with_tooltip(
                            text="Download",
                            id_button="download-button-label",
                            tooltip_text="Use the following buttons to download either the Clima sourcefile or the EPW file",
                        ),
                    ),
                    dcc.Loading(
                        type="circle",
                        children=dbc.Row(
                            [
                                dbc.Col(
                                    dbc.Button(
                                        "Download EPW",
                                        color="primary",
                                        id="download-epw-button",
                                    ),
                                    width="auto",
                                ),
                                dbc.Col(
                                    dbc.Button(
                                        "Download Clima dataframe",
                                        color="primary",
                                        id="download-button",
                                    ),
                                    width="auto",
                                ),
                                dbc.Col(
                                    [
                                        dcc.Download(id="download-dataframe-csv"),
                                        dcc.Download(id="download-epw"),
                                    ],
                                    width=1,
                                ),
                            ],
                        ),
                    ),
                    html.Div(
                        children=title_with_tooltip(
                            text="Heating and Cooling Degree Days",
                            tooltip_text=None,
                            id_button="hdd-cdd-chart",
                        ),
                    ),
                    dbc.Alert(
                        "WARNING: Invalid Results! The CDD setpoint should be higher than the HDD setpoint!",
                        color="warning",
                        is_open=False,
                        id="warning-cdd-higher-hdd",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Label(
                                    "Heating degree day (HDD) setpoint (°C)",
                                ),
                                width=9,
                                md="auto",
                            ),
                            dbc.Col(
                                dbc.Input(
                                    id="input-hdd-set-point",
                                    type="number",
                                    value=10,
                                    style={"width": "4rem"},
                                ),
                                width=3,
                                md="auto",
                            ),
                            dbc.Col(
                                html.Label(
                                    "Cooling degree day (CDD) setpoint (°C)",
                                ),
                                width=9,
                                md="auto",
                            ),
                            dbc.Col(
                                dbc.Input(
                                    id="input-cdd-set-point",
                                    type="number",
                                    value=18,
                                    style={"width": "4rem"},
                                ),
                                width=3,
                                md="auto",
                            ),
                            dbc.Col(
                                dbc.Button(
                                    id="submit-set-points",
                                    children="Submit",
                                    color="primary",
                                ),
                                width=12,
                                md="auto",
                            ),
                        ],
                        align="center",
                        justify="around",
                    ),
                    dcc.Loading(
                        type="circle",
                        children=html.Div(id="degree-days-chart-wrapper"),
                    ),
                    html.Div(
                        children=title_with_tooltip(
                            text="Climate Profiles",
                            tooltip_text=None,
                            id_button="climate-profiles-chart",
                        ),
                    ),
                    dbc.Row(
                        id="graph-container",
                        className="container-row",
                        children=[
                            dbc.Col(id="temp-profile-graph", width=12, md=6, lg=3),
                            dbc.Col(id="humidity-profile-graph", width=12, md=6, lg=3),
                            dbc.Col(id="solar-radiation-graph", width=12, md=6, lg=3),
                            dbc.Col(id="wind-speed-graph", width=12, md=6, lg=3),
                        ],
                    ),
                ],
            ),
        ],
    )


@app.callback(
    Output("world-map", "children"),
    Input("df-store", "modified_timestamp"),
    State("meta-store", "data"),
)
@cache.memoize(timeout=TIMEOUT)
def update_map(ts, meta):
    """Update the contents of tab two. Passing in the general info (df, meta)."""
    map_world = dcc.Graph(
        id="gh_rad-profile-graph",
        config=generate_chart_name("map_summary", meta),
        figure=world_map(meta),
    )

    return map_world


@app.callback(
    Output("location-info", "children"),
    Input("df-store", "modified_timestamp"),
    [State("df-store", "data"), State("meta-store", "data")],
)
@cache.memoize(timeout=TIMEOUT)
# @code_timer
def update_location_info(ts, df, meta):
    """Update the contents of tab two. Passing in the general info (df, meta)."""
    location = f"Location: {meta['city']}, {meta['country']}"
    lon = f"Longitude: {meta['lon']}"
    lat = f"Latitude: {meta['lat']}"
    elevation = f"Elevation above sea level: {meta['site_elevation']}"
    period = ""
    if meta["period"]:
        start, stop = meta["period"].split("-")
        period = f"This file is based on data collected between {start} and {stop}"

    r = requests.get(
        f"http://climateapi.scottpinkelman.com/api/v1/location/{meta['lat']}/{meta['lon']}"
    )

    climate_text = ""
    if r.status_code == 200:
        try:
            climate_zone = r.json()["return_values"][0]["koppen_geiger_zone"]
            zone_description = r.json()["return_values"][0]["zone_description"]

            climate_text = (
                f"Köppen–Geiger climate zone: {climate_zone}. {zone_description}."
            )
        except KeyError:
            pass

    # global horizontal irradiance
    df = pd.read_json(df, orient="split")
    total_solar_rad = f"Annual cumulative horizontal solar radiation: {df['glob_hor_rad'].sum() /1000} kWh/m2"
    total_diffuse_rad = f"Percentage of diffuse horizontal solar radiation: {round(df['dif_hor_rad'].sum()/df['glob_hor_rad'].sum()*100, 1)} %"
    average_yearly_tmp = f"Average yearly temperature: {df['DBT'].mean().round(1)} °C"
    hottest_yearly_tmp = (
        f"Hottest yearly temperature (99%): {df['DBT'].quantile(0.99).round(1)} °C"
    )
    coldest_yearly_tmp = (
        f"Coldest yearly temperature (1%): {df['DBT'].quantile(0.01).round(1)} °C"
    )

    location_info = dbc.Col(
        [
            dbc.Row(location, style={"fontWeight": "bold"}),
            dbc.Row(lon),
            dbc.Row(lat),
            dbc.Row(elevation),
            dbc.Row(period),
            dbc.Row(climate_text),
            dbc.Row(average_yearly_tmp),
            dbc.Row(hottest_yearly_tmp),
            dbc.Row(coldest_yearly_tmp),
            dbc.Row(total_solar_rad),
            dbc.Row(total_diffuse_rad),
        ],
    )

    return location_info


@app.callback(
    [
        Output("degree-days-chart-wrapper", "children"),
        Output("warning-cdd-higher-hdd", "is_open"),
    ],
    [
        Input("submit-set-points", "n_clicks_timestamp"),
    ],
    [
        State("df-store", "data"),
        State("meta-store", "data"),
        State("input-hdd-set-point", "value"),
        State("input-cdd-set-point", "value"),
        State("submit-set-points", "n_clicks"),
    ],
)
@cache.memoize(timeout=TIMEOUT)
# @code_timer
def degree_day_chart(ts_click, df, meta, hdd_value, cdd_value, n_clicks):
    """Update the contents of tab two. Passing in the general info (df, meta)."""

    ctx = dash.callback_context

    if (
        ctx.triggered[0]["prop_id"] == "submit-set-points.n_clicks_timestamp"
        or n_clicks is None
    ):

        hdd_setpoint = hdd_value
        cdd_setpoint = cdd_value

        warning_setpoint = False
        if cdd_setpoint < hdd_setpoint:
            warning_setpoint = True

        color_hdd = "red"
        color_cdd = "dodgerblue"

        df = pd.read_json(df, orient="split")

        hdd_array = []
        cdd_array = []
        months = df["month_names"].unique()

        for i in range(1, 13):
            query_month = "month=="

            # calculates HDD per month
            query = query_month + str(i) + " and DBT<=" + str(hdd_setpoint)
            a = df.query(query)["DBT"].sub(hdd_setpoint)
            hdd = a.sum(axis=0, skipna=True)
            hdd = hdd / 24
            hdd = int(hdd)
            hdd_array.append(hdd)

            # calculates CDD per month
            query = query_month + str(i) + " and DBT>=" + str(cdd_setpoint)
            a = df.query(query)["DBT"].sub(cdd_setpoint)
            cdd = a.sum(axis=0, skipna=True)
            cdd = cdd / 24
            cdd = int(cdd)
            cdd_array.append(cdd)

        trace1 = go.Bar(
            x=months,
            y=hdd_array,
            name="Heating Degree Days",
            marker_color=color_hdd,
            customdata=[abs(ele) for ele in hdd_array],
            hovertemplate=(
                " Heating Degree Days: <br>%{customdata} per month<br><extra></extra>"
            ),
        )
        trace2 = go.Bar(
            x=months,
            y=cdd_array,
            name="Cooling Degree Days",
            marker_color=color_cdd,
            customdata=cdd_array,
            hovertemplate=(
                "Cooling Degree Days: <br>%{customdata} per month<br><extra></extra>"
            ),
        )

        data = [trace2, trace1]

        fig = go.Figure(
            data=data,
        )
        fig.update_layout(
            barmode="relative",
            margin=tight_margins,
            template=template,
            dragmode=False,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1
            ),
        )

        fig.update_xaxes(showline=True, linewidth=1, linecolor="black", mirror=True)
        fig.update_yaxes(showline=True, linewidth=1, linecolor="black", mirror=True)

        chart = dcc.Graph(
            id="degree-days-chart",
            config=generate_chart_name("hdd_cdd_summary", meta),
            figure=fig,
        )

        return chart, warning_setpoint


@app.callback(
    Output("temp-profile-graph", "children"),
    [Input("global-local-radio-input", "value")],
    [State("df-store", "data"), State("meta-store", "data")],
)
@cache.memoize(timeout=TIMEOUT)
# @code_timer
def update_violin_tdb(global_local, df, meta):
    df = pd.read_json(df, orient="split")

    return dcc.Graph(
        id="tdb-profile-graph",
        className="violin-container",
        config=generate_chart_name("tdb_summary", meta),
        figure=violin(df, "DBT", global_local),
    )


@app.callback(
    Output("wind-speed-graph", "children"),
    [Input("global-local-radio-input", "value")],
    [State("df-store", "data"), State("meta-store", "data")],
)
@cache.memoize(timeout=TIMEOUT)
# @code_timer
def update_tab_wind(global_local, df, meta):
    """Update the contents of tab two. Passing in the general info (df, meta)."""
    df = pd.read_json(df, orient="split")

    return dcc.Graph(
        id="wind-profile-graph",
        className="violin-container",
        config=generate_chart_name("wind_summary", meta),
        figure=violin(df, "wind_speed", global_local),
    )


@app.callback(
    Output("humidity-profile-graph", "children"),
    [Input("global-local-radio-input", "value")],
    [State("df-store", "data"), State("meta-store", "data")],
)
@cache.memoize(timeout=TIMEOUT)
# @code_timer
def update_tab_rh(global_local, df, meta):
    """Update the contents of tab two. Passing in the general info (df, meta)."""
    df = pd.read_json(df, orient="split")

    return dcc.Graph(
        id="rh-profile-graph",
        className="violin-container",
        config=generate_chart_name("rh_summary", meta),
        figure=violin(df, "RH", global_local),
    )


@app.callback(
    Output("solar-radiation-graph", "children"),
    [Input("global-local-radio-input", "value")],
    [State("df-store", "data"), State("meta-store", "data")],
)
@cache.memoize(timeout=TIMEOUT)
# @code_timer
def update_tab_gh_rad(global_local, df, meta):
    """Update the contents of tab two. Passing in the general info (df, meta)."""
    df = pd.read_json(df, orient="split")

    return dcc.Graph(
        id="gh_rad-profile-graph",
        className="violin-container",
        config=generate_chart_name("solar_summary", meta),
        figure=violin(df, "glob_hor_rad", global_local),
    )


@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("download-button", "n_clicks"),
    [State("df-store", "data"), State("meta-store", "data")],
    prevent_initial_call=True,
)
# @code_timer
def download_clima_dataframe(n_clicks, df, meta):
    if n_clicks is None:
        raise PreventUpdate
    elif df is not None:
        df = pd.read_json(df, orient="split")
        return dcc.send_data_frame(
            df.to_csv, f"df_{meta['city']}_{meta['country']}_Clima.csv"
        )
    else:
        print("df not loaded yet")


@app.callback(
    Output("download-epw", "data"),
    Input("download-epw-button", "n_clicks"),
    [State("meta-store", "data")],
    prevent_initial_call=True,
)
# @code_timer
def download_clima_dataframe(n_clicks, meta):
    if n_clicks is None:
        raise PreventUpdate
    elif meta is not None:
        lines = get_data(meta["url"])
        return dict(
            content="\n".join(lines), filename=f"{meta['city']}_{meta['country']}.epw"
        )
    else:
        raise PreventUpdate
