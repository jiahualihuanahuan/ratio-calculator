# 📈 Asset Price Ratio Explorer

A Streamlit web application that tracks, compares, and analyzes the historical price ratio between any two financial assets. By pulling historical data directly from Yahoo Finance, this tool helps investors and analysts visualize relationships between equities, commodities, cryptocurrencies, and indices.

## Features

* **Custom Asset Pairing:** Input any two valid Yahoo Finance ticker symbols (e.g., `AAPL` and `MSFT`) to instantly generate their historical price ratio.
* **Popular Presets:** Quick-access buttons for widely tracked ratios like Gold / Silver, Bitcoin / Ethereum, and S&P 500 / Gold.
* **Interactive Charting:** Fully interactive Plotly charts featuring zoom, pan, and hover tooltips.
* **Statistical Overlays:** Automatically calculates and displays the historical mean, ±1 Standard Deviation (1σ) bands, and a customizable Simple Moving Average (SMA).
* **Flexible Timeframes:** Toggle between the maximum overlapping historical data or define custom start and end dates.
* **Raw Data Access:** Expandable data table to view and inspect the underlying daily prices and calculated metrics.

## Installation

### 1. Prerequisites
Ensure you have Python 3.8 or higher installed on your system. 

### 2. Install Dependencies
You will need to install the required Python libraries. You can do this using `pip`:

```bash
pip install streamlit pandas plotly yfinance
