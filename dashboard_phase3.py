import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
import os

st.set_page_config(page_title="AI-SMC Paper Trading", layout="wide")

st.title("🎯 AI-SMC Phase 3: Paper Trading Dashboard")

JOURNAL_FILE = "paper_trading_journal_phase3.json"

if not os.path.exists(JOURNAL_FILE):
    st.warning(f"Journal file not found: {JOURNAL_FILE}. Please run phase3_paper_trading.py first.")
    st.stop()

with open(JOURNAL_FILE, "r") as f:
    try:
        data = json.load(f)
    except Exception as e:
        st.error(f"Error loading journal: {e}")
        st.stop()

metrics = data.get("metrics", {})
trades = data.get("trades", [])

# Display Metrics
st.header("📊 Performance Metrics")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Win Rate", f"{metrics.get('win_rate', 0):.2f}%")
col2.metric("Total P&L", f"${metrics.get('total_pnl', 0):.2f}")
col3.metric("Profit Factor", f"{metrics.get('profit_factor', 0):.2f}")
col4.metric("ROI", f"{metrics.get('roi', 0):.2f}%")

col5, col6, col7, col8 = st.columns(4)
col5.metric("Total Trades", metrics.get("total_trades", 0))
col6.metric("Winning", metrics.get("winning_trades", 0))
col7.metric("Losing", metrics.get("losing_trades", 0))
col8.metric("Max Drawdown", f"{metrics.get('max_drawdown', 0):.2f}%")

# Equity Curve
st.header("📈 Equity Curve")
if trades:
    df = pd.DataFrame(trades)
    df['cumulative_pnl'] = pd.to_numeric(df['pnl'].replace('[\$,]', '', regex=True), errors='coerce').fillna(0).cumsum()
    df['equity'] = data.get('initial_capital', 10000) + df['cumulative_pnl']
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['exit_time'] if 'exit_time' in df else df.index, y=df['equity'], mode='lines+markers', name='Equity'))
    fig.update_layout(title='Account Equity Over Time', xaxis_title='Time', yaxis_title='Equity ($)')
    st.plotly_chart(fig, use_container_width=True)

# Display Trades
st.header("📝 Trade History")
if trades:
    df_disp = pd.DataFrame(trades)
    st.dataframe(df_disp, use_container_width=True)
else:
    st.info("No trades found.")

st.sidebar.markdown("### Data Refresh")
if st.sidebar.button("🔄 Refresh"):
    st.rerun()

st.sidebar.info(f"Last updated: {data.get('timestamp', 'Unknown')}")
