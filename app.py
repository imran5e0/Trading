import streamlit as st
import pandas as pd
from datetime import datetime
from nsepython import nse_optionchain_scrapper
import plotly.express as px

st.set_page_config(page_title="Options Trading Assistant", layout="wide")
st.title("📈 Options Trading Assistant (NIFTY / BANKNIFTY / STOCKS)")

SYMBOL = st.selectbox("Choose Index or Stock", ["NIFTY", "BANKNIFTY", "RELIANCE", "INFY", "SBIN"])

if "history" not in st.session_state:
    st.session_state.history = []

@st.cache_data(ttl=300)
def fetch_data(symbol):
    data = nse_optionchain_scrapper(symbol.upper())
    return data, datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def extract_metrics(data, expiry_filter=None):
    calls, puts = [], []
    all_expiries = set()
    
    for record in data["records"]["data"]:
        expiry = record.get("expiryDate")
        if expiry_filter and expiry != expiry_filter:
            continue
        all_expiries.add(expiry)
        strike = record.get("strikePrice")
        if "CE" in record:
            ce = record["CE"]
            ce["strikePrice"] = strike
            ce["expiryDate"] = expiry
            calls.append(ce)
        if "PE" in record:
            pe = record["PE"]
            pe["strikePrice"] = strike
            pe["expiryDate"] = expiry
            puts.append(pe)

    df_calls = pd.DataFrame(calls)
    df_puts = pd.DataFrame(puts)

    max_pain = df_calls.groupby('strikePrice')['openInterest'].sum().idxmax()
    pcr = df_puts['openInterest'].sum() / df_calls['openInterest'].sum()

    support = df_puts.groupby("strikePrice")["openInterest"].sum().idxmax()
    resistance = df_calls.groupby("strikePrice")["openInterest"].sum().idxmax()

    return df_calls, df_puts, max_pain, round(pcr, 2), sorted(all_expiries), support, resistance

try:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()

    raw_data, time_fetched = fetch_data(SYMBOL)

    _, _, _, _, all_expiries, _, _ = extract_metrics(raw_data)
    selected_expiry = st.selectbox("Select Expiry Date", all_expiries)

    df_calls, df_puts, max_pain, pcr, _, support, resistance = extract_metrics(raw_data, selected_expiry)

    st.session_state.history.append({"time": time_fetched, "max_pain": max_pain, "pcr": pcr})

    st.info(f"📅 Data last updated: **{time_fetched}** | 📆 Expiry: **{selected_expiry}**")

    st.subheader("📌 Key Indicators")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Max Pain", max_pain)
    col2.metric("PCR", pcr)
    col3.metric("Support (Max Put OI)", support)
    col4.metric("Resistance (Max Call OI)", resistance)

    if len(st.session_state.history) > 1:
        st.subheader("📉 Historical Trend")
        df_hist = pd.DataFrame(st.session_state.history)
        fig = px.line(df_hist, x="time", y=["max_pain", "pcr"], markers=True, title="Trend of Max Pain & PCR")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("🔺 Calls (CE)")
    st.dataframe(df_calls[['strikePrice', 'openInterest', 'changeinOpenInterest', 'impliedVolatility']].head(10))

    st.subheader("🔻 Puts (PE)")
    st.dataframe(df_puts[['strikePrice', 'openInterest', 'changeinOpenInterest', 'impliedVolatility']].head(10))

    st.subheader("📣 Strategy Suggestion")
    if pcr < 0.8:
        st.success("🔻 Bearish Market\n✅ Strategy: Buy Put, Bear Put Spread, Short Call")
    elif pcr > 1.2:
        st.success("🔺 Bullish Market\n✅ Strategy: Buy Call, Bull Call Spread, Short Put")
    else:
        st.warning("🔄 Neutral Market\n✅ Strategy: Straddle, Strangle, Iron Condor")

except Exception as e:
    st.error(f"❌ Error fetching data: {str(e)}")
