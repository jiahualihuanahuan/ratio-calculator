import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# ---------------------------------------------------------
# 1. App Configuration & Setup
# ---------------------------------------------------------
st.set_page_config(
    page_title="Asset Ratio Tracker",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Asset Price Ratio Explorer")
st.markdown("Track, compare, and analyze the historical price ratio between any two assets.")

# ---------------------------------------------------------
# 2. Presets & Session State
# ---------------------------------------------------------
PRESET_PAIRS = {
    "Gold / Silver": ("GC=F", "SI=F"),
    "Bitcoin / Ethereum": ("BTC-USD", "ETH-USD"),
    "S&P 500 / Gold": ("^GSPC", "GC=F"),
    "Nasdaq 100 / S&P 500": ("QQQ", "SPY"),
    "Copper / Gold": ("HG=F", "GC=F"),
    "WTI Crude / Natural Gas": ("CL=F", "NG=F"),
}

if "ticker_a" not in st.session_state:
    st.session_state.ticker_a = "GC=F"
if "ticker_b" not in st.session_state:
    st.session_state.ticker_b = "SI=F"

def set_preset(pair_name):
    t_a, t_b = PRESET_PAIRS[pair_name]
    st.session_state.ticker_a = t_a
    st.session_state.ticker_b = t_b

# Preset Buttons UI
st.subheader("Popular Pairs")
cols = st.columns(len(PRESET_PAIRS))
for i, (label, _) in enumerate(PRESET_PAIRS.items()):
    with cols[i]:
        if st.button(label, use_container_width=True):
            set_preset(label)
            st.rerun()

st.markdown("---")

# ---------------------------------------------------------
# 3. Sidebar Configuration
# ---------------------------------------------------------
st.sidebar.header("Configuration")

ticker_a = st.sidebar.text_input(
    "Asset A (Numerator)",
    value=st.session_state.ticker_a,
    help="Yahoo Finance ticker symbol (e.g., GC=F, SPY, BTC-USD)",
).strip().upper()

ticker_b = st.sidebar.text_input(
    "Asset B (Denominator)",
    value=st.session_state.ticker_b,
    help="Yahoo Finance ticker symbol (e.g., SI=F, GLD, ETH-USD)",
).strip().upper()

# Keep session state synced with manual input
st.session_state.ticker_a = ticker_a
st.session_state.ticker_b = ticker_b

use_max_history = st.sidebar.checkbox(
    "Use maximum available history",
    value=True,
    help="Compare both assets across their shared historical overlap.",
)

default_start = datetime.date.today() - datetime.timedelta(days=5 * 365)
start_date = st.sidebar.date_input("Start Date", value=default_start, disabled=use_max_history)
end_date = st.sidebar.date_input("End Date", value=datetime.date.today(), disabled=use_max_history)

sma_window = st.sidebar.slider("Moving Average Window (Days)", min_value=10, max_value=200, value=50, step=5)

# ---------------------------------------------------------
# 4. Data Fetching Logic
# ---------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def load_data(symbols, start, end, is_max):
    """
    Fetches adjusted close prices for a list of symbols. 
    Handles yfinance MultiIndex structures safely.
    """
    if is_max:
        df = yf.download(symbols, period="max", auto_adjust=True, progress=False)
    else:
        # Make the end date inclusive
        end_inclusive = end + datetime.timedelta(days=1)
        df = yf.download(symbols, start=start, end=end_inclusive, auto_adjust=True, progress=False)

    if df.empty:
        return pd.DataFrame()

    # Handle MultiIndex columns (standard when downloading multiple tickers)
    if isinstance(df.columns, pd.MultiIndex):
        # Extract just the 'Close' grouping
        if "Close" in df.columns.get_level_values(0):
            df_close = df["Close"]
        else:
            df_close = df.xs("Close", axis=1, level=0)
    else:
        # Fallback if only 1 ticker successfully downloads or API changes
        df_close = df[["Close"]] if "Close" in df.columns else df

    # Strip timezone data to prevent joining/alignment errors (critical for futures/crypto)
    if isinstance(df_close.index, pd.DatetimeIndex) and df_close.index.tz is not None:
        df_close.index = df_close.index.tz_localize(None)

    return df_close

# ---------------------------------------------------------
# 5. Main Execution Flow
# ---------------------------------------------------------
if not ticker_a or not ticker_b:
    st.warning("Please enter valid ticker symbols for both assets.")
    st.stop()

if ticker_a == ticker_b:
    st.warning("Please select two different assets to compute a ratio.")
    st.stop()

try:
    with st.spinner(f"Fetching market data for {ticker_a} and {ticker_b}..."):
        raw_data = load_data([ticker_a, ticker_b], start_date, end_date, use_max_history)

    # Clean data: drop rows where BOTH are missing, then drop rows where ANY are missing
    data = raw_data.dropna(axis=1, how="all").dropna()

    # Validation
    if data.empty or ticker_a not in data.columns or ticker_b not in data.columns:
        st.error(
            f"Insufficient or missing market data for **{ticker_a}** and **{ticker_b}**. "
            "Please check that both symbols exist on Yahoo Finance and share overlapping trading dates."
        )
        st.stop()

    st.caption(
        f"Displaying **{ticker_a} / {ticker_b}** across **{len(data):,}** common trading days "
        f"({data.index.min().strftime('%Y-%m-%d')} to {data.index.max().strftime('%Y-%m-%d')})."
    )

    # Metrics Calculations
    ratio = data[ticker_a] / data[ticker_b]
    sma = ratio.rolling(window=sma_window).mean()
    mean_val = float(ratio.mean())
    std_val = float(ratio.std())
    
    current_val = float(ratio.iloc[-1])
    prev_val = float(ratio.iloc[-2]) if len(ratio) > 1 else current_val
    delta_pct = ((current_val - prev_val) / prev_val) * 100

    # ---------------------------------------------------------
    # 6. UI: Metric Cards
    # ---------------------------------------------------------
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Ratio", f"{current_val:.3f}", f"{delta_pct:+.2f}%")
    m2.metric("Historical Mean", f"{mean_val:.3f}")
    m3.metric(f"{sma_window}-Day SMA", f"{sma.iloc[-1]:.3f}" if pd.notna(sma.iloc[-1]) else "N/A")
    m4.metric("Standard Deviation (1σ)", f"{std_val:.3f}")

    # ---------------------------------------------------------
    # 7. UI: Plotly Chart
    # ---------------------------------------------------------
    fig = go.Figure()

    # Main Ratio Line
    fig.add_trace(
        go.Scatter(
            x=ratio.index, y=ratio,
            mode="lines",
            name=f"{ticker_a} / {ticker_b} Ratio",
            line=dict(color="#1f77b4", width=2),
        )
    )

    # Moving Average
    fig.add_trace(
        go.Scatter(
            x=sma.index, y=sma,
            mode="lines",
            name=f"{sma_window}-Day SMA",
            line=dict(color="#ff7f0e", width=1.5, dash="dash"),
        )
    )

    # Mean and Std Dev Lines
    fig.add_hline(
        y=mean_val, line_dash="dot", line_color="#d62728",
        annotation_text=f"Mean: {mean_val:.2f}", annotation_position="bottom right",
    )
    fig.add_hline(
        y=mean_val + std_val, line_dash="dot", line_color="#2ca02c",
        annotation_text=f"+1σ: {(mean_val + std_val):.2f}", annotation_position="top right",
    )
    fig.add_hline(
        y=mean_val - std_val, line_dash="dot", line_color="#2ca02c",
        annotation_text=f"-1σ: {(mean_val - std_val):.2f}", annotation_position="bottom right",
    )

    fig.update_layout(
        title=f"<b>Historical Ratio:</b> {ticker_a} vs. {ticker_b}",
        xaxis_title="Date",
        yaxis_title="Ratio",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
    )

    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------
    # 8. UI: Data Table Expander
    # ---------------------------------------------------------
    with st.expander("View Raw Data Table"):
        table_df = data[[ticker_a, ticker_b]].copy()
        table_df["Ratio"] = ratio
        table_df[f"SMA_{sma_window}"] = sma
        
        # Display the dataframe with the most recent dates at the top
        st.dataframe(table_df.sort_index(ascending=False), use_container_width=True)

except Exception as e:
    st.error(f"Error processing market data: {str(e)}")