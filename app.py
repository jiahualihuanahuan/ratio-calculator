import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# ---------------------------------------------------------
# App Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Asset Ratio Tracker",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Asset Price Ratio Explorer")
st.markdown("Track, compare, and analyze the historical price ratio between any two assets.")

# ---------------------------------------------------------
# Preset Pairs Definition
# ---------------------------------------------------------
PRESET_PAIRS = {
    "Gold / Silver": ("GC=F", "SI=F"),
    "Bitcoin / Ethereum": ("BTC-USD", "ETH-USD"),
    "S&P 500 / Gold": ("^GSPC", "GC=F"),
    "Nasdaq 100 / S&P 500": ("QQQ", "SPY"),
    "Copper / Gold": ("HG=F", "GC=F"),
    "WTI Crude / Natural Gas": ("CL=F", "NG=F"),
}

# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
if "ticker_a" not in st.session_state:
    st.session_state.ticker_a = "GC=F"
if "ticker_b" not in st.session_state:
    st.session_state.ticker_b = "SI=F"


def set_preset(pair_name):
    t_a, t_b = PRESET_PAIRS[pair_name]
    st.session_state.ticker_a = t_a
    st.session_state.ticker_b = t_b


# ---------------------------------------------------------
# Preset Buttons
# ---------------------------------------------------------
st.subheader("Popular Pairs")
cols = st.columns(len(PRESET_PAIRS))

for i, (label, _) in enumerate(PRESET_PAIRS.items()):
    with cols[i]:
        if st.button(label, use_container_width=True):
            set_preset(label)
            st.rerun()

st.markdown("---")

# ---------------------------------------------------------
# Sidebar Controls
# ---------------------------------------------------------
st.sidebar.header("Configuration")

ticker_a = st.sidebar.text_input(
    "Asset A (Numerator)",
    value=st.session_state.ticker_a,
    help="Yahoo Finance ticker symbol (e.g., GC=F, SPY, BTC-USD)",
).upper()

ticker_b = st.sidebar.text_input(
    "Asset B (Denominator)",
    value=st.session_state.ticker_b,
    help="Yahoo Finance ticker symbol (e.g., SI=F, GLD, ETH-USD)",
).upper()

# Sync inputs back to session state
st.session_state.ticker_a = ticker_a
st.session_state.ticker_b = ticker_b

# Date range selection
use_max_history = st.sidebar.checkbox("Use maximum available history", value=True, help="Compare both assets across their shared historical overlap instead of a fixed date range.")

default_start = datetime.date.today() - datetime.timedelta(days=5 * 365)
start_date = st.sidebar.date_input(
    "Start Date",
    value=default_start,
    disabled=use_max_history,
    help="Only used when maximum history is disabled.",
)
end_date = st.sidebar.date_input(
    "End Date",
    value=datetime.date.today(),
    disabled=use_max_history,
    help="Only used when maximum history is disabled.",
)

# Moving Average parameter
sma_window = st.sidebar.slider("Moving Average Window (Days)", min_value=10, max_value=200, value=50, step=5)


# ---------------------------------------------------------
# Data Fetching & Processing
# ---------------------------------------------------------
def normalize_close_frame(frame):
    if frame is None or frame.empty:
        return frame

    if isinstance(frame.columns, pd.MultiIndex):
        if "Close" in frame.columns.get_level_values(0):
            df = frame.xs("Close", level=0, axis=1)
            df.columns = [str(col) for col in df.columns]
            return df

    return frame


def normalize_symbol_series(raw, ticker):
    if raw is None or raw.empty:
        return pd.Series(dtype=float)

    df = normalize_close_frame(raw)

    if isinstance(df, pd.Series):
        series = df.copy()
        series.name = ticker
        return series

    if ticker in df.columns:
        series = df[ticker].copy()
        series.name = ticker
        return series

    if len(df.columns) == 1:
        series = df.iloc[:, 0].copy()
        series.name = ticker
        return series

    normalized = df.rename(columns={list(df.columns)[0]: ticker})
    series = normalized.iloc[:, 0].copy()
    series.name = ticker
    return series


@st.cache_data(ttl=3600)
def fetch_data(t_a, t_b, start=None, end=None, use_max_history=True):
    if use_max_history:
        left = yf.download(t_a, period="max", progress=False, auto_adjust=False)
        right = yf.download(t_b, period="max", progress=False, auto_adjust=False)
    else:
        left = yf.download(t_a, start=start, end=end + datetime.timedelta(days=1), progress=False, auto_adjust=False)
        right = yf.download(t_b, start=start, end=end + datetime.timedelta(days=1), progress=False, auto_adjust=False)

    series_a = normalize_symbol_series(left, t_a)
    series_b = normalize_symbol_series(right, t_b)

    if series_a.empty or series_b.empty:
        raise ValueError(f"No market data returned for {t_a} or {t_b} from Yahoo Finance.")

    aligned = pd.concat([series_a, series_b], axis=1).dropna()
    if aligned.empty:
        raise ValueError(f"{t_a} and {t_b} do not share a common market-data period.")

    return aligned[[t_a, t_b]]


if not ticker_a or not ticker_b:
    st.warning("Please enter valid ticker symbols for both assets.")
    st.stop()

if ticker_a == ticker_b:
    st.warning("Please select two different assets to compute a meaningful ratio.")
    st.stop()

try:
    with st.spinner("Fetching market data..."):
        data = fetch_data(ticker_a, ticker_b, start_date, end_date, use_max_history)

    if data.empty or ticker_a not in data.columns or ticker_b not in data.columns:
        st.error("Unable to load data for the specified tickers or date range. Please verify ticker symbols.")
        st.stop()

    st.caption(
        f"Comparing {ticker_a} vs {ticker_b} over the shared period from {data.index.min().date()} to {data.index.max().date()}"
    )

    # Calculate metrics
    ratio = data[ticker_a] / data[ticker_b]
    sma = ratio.rolling(window=sma_window).mean()
    mean_val = ratio.mean()
    std_val = ratio.std()
    current_val = ratio.iloc[-1]
    prev_val = ratio.iloc[-2] if len(ratio) > 1 else current_val
    delta = current_val - prev_val
    delta_pct = (delta / prev_val) * 100

    # ---------------------------------------------------------
    # Key Metric Cards
    # ---------------------------------------------------------
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Ratio", f"{current_val:.3f}", f"{delta_pct:+.2f}%")
    m2.metric("Period Average", f"{mean_val:.3f}")
    m3.metric(f"{sma_window}-Day SMA", f"{sma.iloc[-1]:.3f}" if not sma.empty else "N/A")
    m4.metric("Standard Deviation", f"{std_val:.3f}")

    # ---------------------------------------------------------
    # Plotly Interactive Chart
    # ---------------------------------------------------------
    fig = go.Figure()

    # Ratio line
    fig.add_trace(
        go.Scatter(
            x=ratio.index,
            y=ratio,
            mode="lines",
            name=f"{ticker_a} / {ticker_b}",
            line=dict(color="#1f77b4", width=2),
        )
    )

    # Moving average
    fig.add_trace(
        go.Scatter(
            x=sma.index,
            y=sma,
            mode="lines",
            name=f"{sma_window}-Day SMA",
            line=dict(color="#ff7f0e", width=1.5, dash="dash"),
        )
    )

    # Mean line
    fig.add_hline(
        y=mean_val,
        line_dash="dot",
        line_color="#d62728",
        annotation_text=f"Mean: {mean_val:.2f}",
        annotation_position="bottom right",
    )

    # Upper and lower standard deviation bands (+/- 1 Std Dev)
    fig.add_hline(
        y=mean_val + std_val,
        line_dash="dot",
        line_color="#2ca02c",
        annotation_text=f"+1σ: {(mean_val + std_val):.2f}",
        annotation_position="top right",
    )
    fig.add_hline(
        y=mean_val - std_val,
        line_dash="dot",
        line_color="#2ca02c",
        annotation_text=f"-1σ: {(mean_val - std_val):.2f}",
        annotation_position="bottom right",
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
    # Raw Data Table
    # ---------------------------------------------------------
    with st.expander("View Raw Data"):
        table_df = data.copy()
        table_df["Ratio"] = ratio
        table_df[f"SMA_{sma_window}"] = sma
        st.dataframe(table_df.sort_index(ascending=False), use_container_width=True)

except Exception as e:
    st.error(f"An error occurred while fetching or calculating data: {e}")