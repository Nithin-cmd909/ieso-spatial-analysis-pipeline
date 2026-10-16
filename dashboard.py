import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(layout="wide", page_title="IESO Nodal & Spatial Predictor")

@st.cache_data
def load_data():
    conn = sqlite3.connect('ieso_nodal_data.db')
    df = pd.read_sql_query("SELECT * FROM model_features", conn)
    conn.close()
    return df

st.title("Ontario IESO Nodal Pricing & Congestion Predictor")

with st.spinner("Loading Panel & Spatial Features..."):
    df = load_data()

# --- REGIONAL COORDINATE MAPPING 
# Map IESO node nomenclature / electrical zones to approximate coordinates for GIS visualization
ZONE_COORDS = {
    'TORONTO': (43.6532, -79.3832),
    'OTTAWA': (45.4215, -75.6972),
    'NIAGARA': (43.0896, -79.0849),
    'SUDBURY': (46.4917, -80.9930),
    'THUNDER BAY': (48.3809, -89.2477),
    'LONDON': (42.9849, -81.2453),
    'BRUCE': (44.3312, -81.5976),
    'KINGSTON': (44.2312, -76.4860)
}

@st.cache_data
def assign_synthetic_geo(nodes):
    np.random.seed(42)
    coords = {}
    zone_list = list(ZONE_COORDS.values())
    for node in nodes:
        base_lat, base_lon = zone_list[hash(node) % len(zone_list)]
        # Add slight jitter 
        coords[node] = (
            base_lat + np.random.uniform(-0.15, 0.15),
            base_lon + np.random.uniform(-0.15, 0.15)
        )
    return coords

geo_map = assign_synthetic_geo(df['Node'].unique())
df['lat'] = df['Node'].map(lambda x: geo_map[x][0])
df['lon'] = df['Node'].map(lambda x: geo_map[x][1])

# --- SIDEBAR CONTROLS 
st.sidebar.header("Grid Controls")
nodes = df['Node'].unique()
selected_node = st.sidebar.selectbox("Select Pricing Node", nodes, index=0)

available_dates = df['Date'].unique()
selected_date = st.sidebar.selectbox("Select Date for Spatial Snapshot", available_dates, index=len(available_dates)-1)
selected_hour = st.sidebar.slider("Select Hour (1 - 24)", min_value=1, max_value=24, value=12)


node_data = df[df['Node'] == selected_node]
snapshot_data = df[(df['Date'] == selected_date) & (df['Hour'] == selected_hour)]

# --- SECTION 1: TOP-LEVEL METRICS 
st.markdown(f"### Live Metrics: `{selected_node}`")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Avg Day-Ahead Price", f"${node_data['Energy_Price'].mean():.2f}")
col2.metric("Avg Real-Time Price", f"${node_data['RT_Energy_Price'].mean():.2f}")
col3.metric("Avg Spread (RT - DA)", f"${node_data['True_Price_Spread'].mean():.2f}")
col4.metric("Provincial Spatial Lag (Mean)", f"${node_data['Spatial_Lag_t_1'].mean():.2f}")

st.divider()

# --- SECTION 2: GIS SPATIAL GRID MAP
st.markdown(f"### 🗺️ Provincial Spatial Grid: Hour {selected_hour} on {selected_date}")
st.caption("Nodal divergence bubbles sized by absolute spread ($|RT - DA|$) and colored by price differential.")

try:
    # Updated for Plotly 6.0+ compatibility (using scatter_map instead of scatter_mapbox)
    fig_map = px.scatter_map(
        snapshot_data,
        lat="lat",
        lon="lon",
        hover_name="Node",
        hover_data={
            "Energy_Price": ":.2f",
            "RT_Energy_Price": ":.2f",
            "True_Price_Spread": ":.2f",
            "lat": False,
            "lon": False
        },
        color="True_Price_Spread",
        size=snapshot_data["True_Price_Spread"].abs() + 1,
        color_continuous_scale="RdBu_r",
        size_max=18,
        zoom=4.7,
        center={"lat": 46.2, "lon": -81.5},
        map_style="carto-positron" # Updated parameter name
    )
    fig_map.update_layout(margin={"r":0, "t":0, "l":0, "b":0})
    st.plotly_chart(fig_map, use_container_width=True)
except Exception as e:
    st.error(f"Map rendering failed: {e}")

st.divider()

# --- SECTION 3: TIME SERIES & SPATIAL DYNAMICS 
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### Price Divergence Time Series")
    fig_line = px.line(
        node_data,
        x='Date',
        y=['Energy_Price', 'RT_Energy_Price'],
        labels={'value': 'Price ($/MWh)', 'Date': 'Date'},
        color_discrete_map={'Energy_Price': '#1f77b4', 'RT_Energy_Price': '#d62728'}
    )
    st.plotly_chart(fig_line, use_container_width=True)

with col_right:
    st.markdown("### Spatial Spillover vs Local Price Spread")
    fig_scatter = px.scatter(
        node_data,
        x='Spatial_Lag_t_1',
        y='True_Price_Spread',
        color='temp_c',
        color_continuous_scale='Turbo',
        labels={'Spatial_Lag_t_1': 'Spatial Lag (Provincial Momentum, t-1)', 'True_Price_Spread': 'Target Spread (RT - DA)'}
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

# --- SECTION 4: DATA AUDIT 
st.markdown("### Data Inspection")

tab_node, tab_snapshot = st.tabs([
    f" Historical Series: {selected_node}", 
    f" Provincial Snapshot: {selected_date} Hour {selected_hour}"
])

with tab_node:
    st.caption(f"Continuous 30-day chronological record for node `{selected_node}` ({len(node_data)} total records).")
    st.dataframe(node_data, use_container_width=True)

with tab_snapshot:
    st.caption(f"Cross-sectional provincial grid slice across all active nodes at Hour {selected_hour} on {selected_date} ({len(snapshot_data)} nodes).")
    st.dataframe(snapshot_data, use_container_width=True)

# - SECTION 5: ML PREDICTION ENGINE 
st.markdown("---")
st.header(" ML Model Evaluation & Arbitrage Signals")

from sklearn.metrics import accuracy_score

# Load prediction data from SQLite
@st.cache_data
def load_predictions():
    conn = sqlite3.connect('ieso_nodal_data.db')
    preds_df = pd.read_sql_query("SELECT * FROM model_directional_predictions", conn)
    conn.close()
    return preds_df

preds_df = load_predictions()

# Interactive Threshold Slider
st.subheader("Signal Execution Threshold")
st.markdown("Filter out low-confidence predictions to increase realized trading accuracy.")
conf_threshold = st.slider("Minimum Confidence Probability", min_value=0.50, max_value=0.70, value=0.60, step=0.01)

# Calculate dynamic metrics based on the slider
confident_trades = preds_df[(preds_df['Long_Spread_Probability'] >= conf_threshold) | (preds_df['Long_Spread_Probability'] <= (1 - conf_threshold))]

if len(confident_trades) > 0:
    realized_acc = accuracy_score(confident_trades['Spread_Direction'], confident_trades['Predicted_Direction'])
    coverage = len(confident_trades) / len(preds_df)
else:
    realized_acc = 0
    coverage = 0

col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Realized Accuracy", f"{realized_acc:.2%}", f"At {conf_threshold*100:.0f}% Threshold")
col_m2.metric("Trade Coverage", f"{coverage:.1%}", "Of total possible volume")
col_m3.metric("Baseline AUC-ROC", "0.5414")

# Filter predictions for the currently selected snapshot
pred_slice = preds_df[(preds_df['Date'] == selected_date) & (preds_df['Hour'] == selected_hour)]
pred_slice = pred_slice[(pred_slice['Long_Spread_Probability'] >= conf_threshold) | (pred_slice['Long_Spread_Probability'] <= (1 - conf_threshold))]

if not pred_slice.empty:
    st.subheader(f"High-Confidence Trade Recommendations for {selected_date} Hour {selected_hour}")
    
    buy_da_count = (pred_slice['Predicted_Direction'] == 1).sum()
    sell_da_count = (pred_slice['Predicted_Direction'] == 0).sum()
    
    st.info(f"Executing trades across {len(pred_slice)} nodes: **{buy_da_count} Long RT (Buy DA)** | **{sell_da_count} Short RT (Sell DA)**")
    
    display_cols = ['Node', 'True_Price_Spread', 'Predicted_Direction', 'Long_Spread_Probability']
    st.dataframe(
        pred_slice[display_cols].sort_values('Long_Spread_Probability', ascending=False),
        use_container_width=True
    )
else:
    st.warning(f"No signals met the {conf_threshold*100:.0f}% confidence threshold for {selected_date} Hour {selected_hour}.")
    