import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, dash_table, Input, Output, ALL, State, callback_context
import numpy as np
from dash.exceptions import PreventUpdate


#########################################################################################################################################################
######################################################################### DATA ##########################################################################
#########################################################################################################################################################


# 2 denormalized source tables
df = pd.read_csv('data/data.csv')
df_metadata = pd.read_csv('data/metadata.csv')
ds_countries = pd.read_csv('data/countries.csv')["Country"]

###################################################
# at top (after reading df)
# convert strings to categorical (saves memory + speeds groupby/sort)
df["Indicator"] = df["Indicator"].astype("category")
df["Country"] = df["Country"].astype("category")

# Build per-indicator DataFrames and store as copies (sorted by Rank ascending)
"""
{
    "GDP":           <DataFrame of GDP rows sorted by Rank>,
    "Inflation":     <...>,
    ...
}
"""
indicator_dfs = {
    ind: df_ind.sort_values("Rank").reset_index(drop=True)
    for ind, df_ind in df.groupby("Indicator", observed=False)
}
###################################################

# framework for building rows / grids of charts
indicator_groups = {
    "People": ["Population", "Female population share", "Population ages 65+ share", "Density", "Life expectancy", "Urban population share", "Net migration", "International migrants"],
    "Economy": ["GDP, PPP", "GDP", "GDP per capita", "Budget", "Foreign direct investment, net", "Debt (% of GDP)", "Inflation", "Unemployment"],
    "Geography": ["Land area", "Surface area", "Agricultural land share", "Arable land share", "Forest area share"],
    "Science": ["Publications", "Patents, residents", "Patents, nonresidents", "High-technology exports", "R&D (% of GDP)"]
}

# default settings
mode = "top10"
selected_country = None

# will be used in the future to customize some charts, for now it is just a placeholder
chart_configs = {
    "Patents": {"type": "stacked", "secondary": "Budget (% of GDP)"},
}


#########################################################################################################################################################
###################################################################### FUNCTIONS ########################################################################
#########################################################################################################################################################


# returns data for charts based on parameters selected by the User (or the default parameters)
def return_chart_data(indicator_name, mode, selected_country):
    df_filtered = indicator_dfs[indicator_name].copy()

    if mode == "top10" or (mode == "country" and selected_country is None): # show top 10 countries (default) unless the User actually selects a country from the dropdown
        return df_filtered.nlargest(10, "Value").sort_values(by='Value', ascending=True)
    else: # when User actually selects a country from the dropdown (not just switches the radio button to show the dropdown)

        if selected_country not in df_filtered["Country"].values: # if the selected country has no data for the given indicator, ...
            return pd.DataFrame(columns=["Country", "Value", "Rank", "Country_with_rank"]) # ... show an empty box

        selected_country_rank = df_filtered.loc[df_filtered["Country"] == selected_country, "Rank"].iloc[0]
        countries_count = df_filtered["Rank"].max()

        # below is how I want to choose the "neighbors" for the selected country for different scenarios
        if selected_country_rank <= 10:
            return df_filtered.nlargest(10, "Value").sort_values(by='Value', ascending=True)
        elif selected_country_rank >= countries_count - 10:
            return df_filtered.nsmallest(10, "Value").sort_values(by='Value', ascending=True)
        else:
            df_neighbors = df_filtered[(df_filtered["Rank"] >= selected_country_rank - 5) & (df_filtered["Rank"] <= selected_country_rank + 4)]
            df_neighbors = df_neighbors.sort_values(by="Rank", ascending=True)
            return df_neighbors

# generate a bar chart
def create_bar_chart(indicator_name, mode, selected_country):
    df_chart = return_chart_data(indicator_name, mode, selected_country).sort_values(by='Rank', ascending=False)

    if len(df_chart) == 0:
        bg_color="whitesmoke"
    else:
        bg_color="white"

    # x-axis range
    x_max = df_metadata.loc[df_metadata["Indicator"] == indicator_name, "Max_value"].iloc[0]
    x_min = df_metadata.loc[df_metadata["Indicator"] == indicator_name, "Min_value"].iloc[0]

    # dynamic decimals
    max_val = df_chart["Value"].max()
    if max_val <= 100:
        texttemplate = "%{text:,.1f}"
    else:
        texttemplate = "%{text:,.0f}"

    cond = df_chart["Value"] / x_max > 0.75 # todo: improve later

    group = df_metadata.loc[df_metadata["Indicator"] == indicator_name, "Group"].iloc[0]
    if group == "Economy":
        df_chart["bar_color"] = np.where(df_chart["Country"] == selected_country, "goldenrod", "khaki")
    elif group == "People":
        df_chart["bar_color"] = np.where(df_chart["Country"] == selected_country, "gray", "silver")
    elif group == "Geography":
        df_chart["bar_color"] = np.where(df_chart["Country"] == selected_country, "seagreen", "lightgreen")
    else:
        df_chart["bar_color"] = np.where(df_chart["Country"] == selected_country, "steelblue", "lightblue")

    df_chart["annotation_color"] = np.where((df_chart["Country"] == selected_country) & cond, "white", "dimgray")

    # do not display the default 'outside' labels for the bars with the biggest values (because they will be partially or fully hidden / outside the chart)
    df_chart["text_position"] = np.where(cond, 'none', 'outside')  # todo: replace with pandas?

    # ... instead show annotations (below) that will replace and mimic the hidden labels, using these coordinates:
    df_chart["text_x"] = np.where(cond, df_chart["Value"] / x_max - 0.06, np.nan) # manual offset of 0.06 to math the style (distance to the bar edge) to the default labels

    fig = px.bar(
        data_frame=df_chart,
        x="Value",
        y="Country",
        text="Value",
        title=None,
        # category_orders={"Country": df_chart["Country"].tolist()}
    )

    fig.update_traces(
        marker_color=df_chart["bar_color"],
        texttemplate=texttemplate,
        textposition=df_chart["text_position"],
        textfont=dict(size=8, color='dimgray', family='Arial'),
        hoverinfo="skip",
        hovertemplate=None,
        marker_line_width=0
    )

    fig.update_layout(
        plot_bgcolor=bg_color,
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(l=0, r=0, t=0, b=0),
        yaxis=dict(showticklabels=False, automargin=False, fixedrange=True),
        xaxis=None,
        width=90,
        height=160,
    )

    fig.update_xaxes(
        showticklabels=False,
        showgrid=False,
        zeroline=False,
        range=[x_min, x_max]
    )

    # annotations to replace and mimic the hidden bar labels
    for i, row in df_chart.reset_index(drop=True).iterrows(): # todo: understand iterrows() and double counter better

        # note: don't show the annotation if text_x = np.nan (because it would be translated into 0 and displayed on the left)
        if pd.isna(row["text_x"]):
            continue

        fig.add_annotation(
            x=row["text_x"],
            xref="paper", # note: RELATIVE COORDINATES (0..1) instead of x-axis VALUES
            y=i,
            yref="y",
            text = f"{row['Value']:,.1f}" if max_val <= 100 else f"{row['Value']:,.0f}",
            font=dict(size=8, color=row["annotation_color"]), # todo: make it 20% "less black" to address the optical illusion
            # when the font of the labels that overlap the bars appear to be bigger than the ones outside the bars
            # because of the background color difference (text over a darker background appears to bigger/bolder, but it isn't)
            xanchor="right",
            showarrow=False,
        )

    return fig


# will be used in the future to customize some charts, for now it is just a placeholder
def create_chart(indicator_name, mode, selected_country):
    cfg = chart_configs.get(indicator_name)

    if cfg is None:
        return create_bar_chart(indicator_name, mode, selected_country) # default simple bar chart

    # todo: placeholder
    if cfg.get("type") == "dual":
        # secondary_name = cfg.get("secondary")
        # ...
        return create_bar_chart(indicator_name, mode, selected_country)

    # todo: placeholder
    if cfg.get("type") == "stacked":
        # todo
        return create_bar_chart(indicator_name, mode, selected_country)

    # fallback
    return create_bar_chart(indicator_name, mode, selected_country)


# a single-column table that replaces the bar chart y-axis labels (so that I can customize their appearance, particularly align them to left)
def create_countries_list(indicator_name, mode, selected_country):

    df_chart = return_chart_data(indicator_name, mode, selected_country).sort_values(by='Rank', ascending=True)

    return dash_table.DataTable(
        id={"type": "countries-table", "indicator": indicator_name},

        # Use the real column name directly
        data=df_chart[["Country_with_rank"]].to_dict("records"),

        # Column id MUST match the key in each row dict
        # Column name must exist, but can be empty
        columns=[{"id": "Country_with_rank", "name": ""}],

        style_table={"width": "90px"},
        style_cell={"textAlign": "left", "fontSize": "10px"},
        style_header={"display": "none"},
        style_data={"border": "none"},
        css=[
            {"selector": ".show-hide", "rule": "display: none"},
            {"selector": ".dash-spreadsheet tr", "rule": "height: 16px;"}
        ],
    )


# generate 1 row of boxes for indicators (without left-hand header with the group name)
def generate_row(indicator_names, mode, selected_country):
    n_boxes = len(indicator_names)

    return html.Div(  # 1 row (a grid)
        children=[
            html.Div(  # 1 box (a flex)
                children=[
                    html.Div( # UoM (unit of measure)
                        df_metadata[df_metadata["Indicator"] == indicator_name]["UoM"].drop_duplicates(),
                        style={
                            "position": "absolute",
                            "top": "16px",
                            "left": "0px",
                            "width": "180px",
                            "zIndex": "20",
                            "fontSize": "11px",
                            "color": "dimgray",
                            "textAlign": "center",
                        }
                    ),
                    html.Div([ # source | year | countries count
                        html.Div(df_metadata[df_metadata["Indicator"] == indicator_name]["Source"].drop_duplicates(), style={"color": "darkgray", "marginRight": "3px"}),
                        html.Div("|", style={"color": "gray", "marginRight": "3px"}),
                        html.Div(df_metadata[df_metadata["Indicator"] == indicator_name]["Year"].drop_duplicates(), style={"color": "darkgray", "marginRight": "3px"}),
                        html.Div("|", style={"color": "gray", "marginRight": "3px"}),
                        html.Div(f"{len(indicator_dfs[indicator_name]["Country"])}", style={"color": "darkgray", "marginRight": "2px"}), #todo: move to csv
                        html.Div("countries", style={"color": "darkgray"}),
                        ], style={
                            "display": "flex",
                            "flexDirection": "row",
                            "alignItems": "center",
                            "fontSize": "9px",
                            "position": "absolute",
                            "top": "194px",
                        }
                    ),





                    html.Div(  # box title
                        indicator_name,
                        style={"marginBottom": "0px", "marginTop": "2px", "fontSize": "11px", "fontWeight": "bold"}
                    ),





                    html.Div(  # 1 box (a flex)
                        children=[
                            create_countries_list(indicator_name, mode, selected_country),
                            html.Div(  # box body with chart
                                dcc.Graph(
                                    id={"type": "chart", "indicator": indicator_name},
                                    figure=create_chart(indicator_name, mode, selected_country),
                                    config={"displayModeBar": False},
                                    style={"height": "160px", "width": "90px", "marginBottom": "15px",
                                           "marginTop": "16px"},
                                ),
                            )
                        ],
                        style={
                            "display": "flex",
                            "flexDirection": "row",
                            # "alignItems": "center",
                            "backgroundColor": "whitesmoke",
                            # "border": "1px solid gainsboro",
                            "borderRadius": "5px",
                        }
                    )
                ],
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "alignItems": "center",
                    "backgroundColor": "whitesmoke",
                    "border": "1px solid gainsboro",
                    "borderRadius": "5px",
                    "position": "relative" # note: anchor for the "absolute" children inside
                }
            )
            for indicator_name in indicator_names
        ],
        style={
            "display": "grid",
            "gridTemplateColumns": f"repeat({n_boxes}, 190px)",
            "gap": "7px",
            "justifyContent": "start",
            "marginBottom": "7px"
        }
    )


# generate the layout of rows (a list of rows' Divs) with added left-hand group headers in each row
def group_bg_color(group_name, alpha=1.0):
    if group_name == "Economy":
        return f"rgba(240, 230, 140, {alpha})"   # khaki
    elif group_name == "People":
        return f"rgba(192, 192, 192, {alpha})"   # silver
    elif group_name == "Geography":
        return f"rgba(144, 238, 144, {alpha})"   # lightgreen
    else:
        return f"rgba(173, 216, 230, {alpha})"   # lightblue

grid_rows = []
for group_name, indicators in indicator_groups.items():
    row_div = html.Div(  # 1 full row (a flex; left-hand group header + indicator boxes)
        children=[
            html.Div(  # left-hand group header
                group_name,
                style={
                    "width": "120px",
                    "height": "207px",
                    "lineHeight": "207px",
                    "textAlign": "center",
                    "fontWeight": "bold",
                    "backgroundColor": group_bg_color(group_name, alpha=.5),
                    "fontSize": "14px",
                    "color": "rgba(51, 51, 51, 1)",
                    "borderRadius": "8px",
                    "marginRight": "15px"
                }
            ),
            generate_row(indicators, mode, selected_country)  # indicator boxes
        ],
        style={
            "display": "flex",
            "alignItems": "flex-start",
            "marginBottom": "0px"
        }
    )
    grid_rows.append(row_div)


#########################################################################################################################################################
###################################################################### APP LAYOUT #######################################################################
#########################################################################################################################################################


app = Dash(__name__)
app.title = "Top 10"

app.layout = html.Div([

    # html.Div(  # background
    #     style={
    #         "position": "absolute",
    #         "left": "0px",
    #         "top": "0px",
    #         "width": "95vw",
    #         "height": "95vh",
    #         "backgroundColor": "whitesmoke",
    #         "zIndex": 0
    #     }
    # ),

    html.Div(
        children=[
            html.Div(  # title header
                "Ranking the World: compare countries across selected indicators",
                style={
                    "height": "36px",
                    "lineHeight": "36px", # aligns vertically to center
                    "textAlign": "Left",
                    "backgroundColor": "dimgray",
                    "fontSize": "18px",
                    # "fontWeight": "bold",
                    "color": "white",
                    "paddingLeft": "10px",
                    "paddingRight": "190px"
                }
            ),
            dcc.RadioItems(
                id="mode",
                options=[
                    {"label": "Top 10 countries", "value": "top10"},
                    {"label": "Select a country", "value": "country"}
                ],
                value="top10",
                inline=True,
                style={
                    "height": "36px",
                    "lineHeight": "36px",
                    "color": "white",
                    "marginRight": "10px"
                }
            ),
            html.Div(
                dcc.Dropdown(
                    id="country-dropdown",
                    options=[{"label": c, "value": c} for c in ds_countries],
                    placeholder="Select a country",
                    clearable=True
                ),
                id="dropdown-container",
                style={"width": "200px", "display": "none"}  # hidden by default
            ),
        ],
        style={
            "display": "flex",
            "flexDirection": "row",
            "backgroundColor": "dimgray",
            "height": "36px",
            "width": "1712px",
            "position": "absolute",
            "left": "0px",
            "top": "0px",
        }
    ),

    html.Div(  # Grid container with rows
        children=grid_rows,
        style={
            "position": "relative",
            "top": "36px",
            "width": "95vw",
            "height": "calc(95vh - 50px)",
            "boxSizing": "border-box",
            "overflowY": "auto"
        }
    )
])


#########################################################################################################################################################
####################################################################### CALLBACKS #######################################################################
#########################################################################################################################################################


# Show/hide dropdown depending on radio selection
@app.callback(
    Output("dropdown-container", "style"),
    Input("mode", "value")
)
def toggle_dropdown(mode):
    if mode == "country":
        return {"width": "200px", "display": "block"}
    return {"display": "none"}


@app.callback(
    Output({"type": "chart", "indicator": ALL}, "figure"),
    Output({"type": "countries-table", "indicator": ALL}, "data"),
    Output({"type": "countries-table", "indicator": ALL}, "style_data_conditional"),
    Input("mode", "value"),
    Input("country-dropdown", "value"),
    State({"type": "chart", "indicator": ALL}, "id"),
    State({"type": "countries-table", "indicator": ALL}, "id")
)
def update_all(mode, country, chart_ids, table_ids):
    # chart_figures, table_data_list, table_styles_list
    current_mode = "country" if (mode == "country" and country) else "top10"

    chart_figures = []
    table_data_list = []
    table_styles_list = []

    # --- UPDATE CHARTS ----------------------------------------------------
    for comp_id in chart_ids:
        indicator_name = comp_id["indicator"]

        fig = create_chart(indicator_name, current_mode, country)
        chart_figures.append(fig)

    # --- UPDATE TABLES ----------------------------------------------------
    for comp_id in table_ids:
        indicator_name = comp_id["indicator"]

        df_chart = return_chart_data(indicator_name, current_mode, country)
        df_chart = df_chart.sort_values(by="Rank", ascending=True)

        table_data = df_chart[["Country_with_rank"]].to_dict("records")
        table_data_list.append(table_data)

        if country:
            style = [
                {
                    "if": {"filter_query": '{{Country_with_rank}} contains "{}"'.format(country)},
                    "fontWeight": "bold",
                    "color": "black"
                }
            ]
        else:
            style = []

        table_styles_list.append(style)

    return chart_figures, table_data_list, table_styles_list


if __name__ == "__main__":
    app.run(debug=True)