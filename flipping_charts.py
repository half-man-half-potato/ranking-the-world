import pandas as pd
import plotly.graph_objects as go
from dash import Dash, html, dcc

# -------------------------------------
# Load & merge data
# -------------------------------------
df_data = pd.read_csv('data/data.csv')
df_metadata = pd.read_csv('data/metadata.csv')
df = df_data.merge(df_metadata, how='left', on='Indicator')

MAIN = "Budget"
SECONDARY = "Budget (% of GDP)"

THIN = "Budget (% of GDP)"
THICK = "Budget"

df_main = df[df["Indicator"] == MAIN].copy()
df_secondary = df[df["Indicator"] == SECONDARY].copy()

df_combined = df_main.merge(
    df_secondary[["Country", "Value"]],
    on="Country",
    suffixes=("_main", "_secondary"),
    how="left"
)

df_top10 = df_combined.nlargest(10, "Value_main").sort_values("Value_main")

# -------------------------------------
# FIGURE
# -------------------------------------
fig = go.Figure()

# Blue — main bars
fig.add_trace(
    go.Bar(
        y=df_top10["Country"],
        x=df_top10["Value_main"] if MAIN == THICK else df_top10["Value_secondary"],
        name=THICK,
        orientation="h",
        marker_color="steelblue",
        width=0.6
    )
)

# Spacer bar (invisible, just to center gray)
fig.add_trace(
    go.Bar(
        y=df_top10["Country"],
        x=[v/2 for v in df_top10["Value_main"]],  # half-width spacer
        name="spacer",
        orientation="h",
        marker_color="rgba(0,0,0,0)",
        width=0.6,
        hoverinfo="skip",
        showlegend=False
    )
)

# Gray — secondary bars (on top of spacer)
fig.add_trace(
    go.Bar(
        y=df_top10["Country"],
        x=df_top10["Value_secondary"] if MAIN == THICK else df_top10["Value_main"],
        name=THIN,
        orientation="h",
        marker_color="gray",
        width=0.2,
        xaxis="x2"
    )
)

# Layout
fig.update_layout(
    barmode="overlay",
    xaxis=dict(title=MAIN),
    xaxis2=dict(
        overlaying="x",
        side="top",
        title=SECONDARY
    ),
    yaxis=dict(title="", automargin=True),
    height=600
)

# -------------------------------------
# DASH APP
# -------------------------------------
app = Dash(__name__)

app.layout = html.Div([
    html.H3("Budget & Budget (% of GDP) – Top 10 Countries"),
    dcc.Graph(figure=fig)
])

if __name__ == "__main__":
    app.run(debug=True)
