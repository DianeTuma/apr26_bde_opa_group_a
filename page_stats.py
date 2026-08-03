# import streamlit as st
# import requests

# st.title("📊 Historical Analytics & Performance")
# st.subheader("Analyze market trends and KPIs extracted from the PostgreSQL database")

# st.markdown("---")

# # 1. User Inputs aligned with your API query parameters
# # Your API limits days between 1 and 30 (ge=1, le=30)
# days = st.slider("🗓️ Select Timeframe (Past Days):", min_value=1, max_value=30, value=7)

# st.markdown("---")

# # 2. Trigger the API Request
# if st.button("📈 Compute Financial Metrics"):
#     api_url = f"http://127.0.0.1:8000/stats?days={days}"
    
#     try:
#         with st.spinner("Querying PostgreSQL and calculating KPIs..."):
#             response = requests.get(api_url)
        
#         if response.status_code == 200:
#             metrics = response.json()
            
#             # Safety check if database was empty for that period
#             if metrics.get("status") == "No data available":
#                 st.warning(f"No market data found in the database for the last {days} days.")
#             else:
#                 st.success(f"Analysis successfully completed for the past {days} days!")
                
#                 # --- ROW 1: Prices & Performance ---
#                 col1, col2, col3 = st.columns(3)
                
#                 with col1:
#                     st.metric(
#                         label="Highest Price (Max)", 
#                         value=f"${metrics['max_price']:.2f}"
#                     )
#                 with col2:
#                     st.metric(
#                         label="Lowest Price (Min)", 
#                         value=f"${metrics['min_price']:.2f}"
#                     )
#                 with col3:
#                     # Displays performance with a clean green/red delta arrow
#                     perf = metrics['performance_pct']
#                     st.metric(
#                         label="Period Performance", 
#                         value=f"{perf:+.2f}%",
#                         delta=f"{perf:.2f}%"
#                     )
                
#                 st.markdown("---")
                
#                 # --- ROW 2: Advanced Indicators ---
#                 col4, col5, col6 = st.columns(3)
                
#                 with col4:
#                     st.metric(
#                         label="VWAP (Volume Weighted Avg)", 
#                         value=f"${metrics['vwap']:.2f}",
#                         help="Reflects the true average execution price based on trade volume."
#                     )
#                 with col5:
#                     st.metric(
#                         label="Market Sentiment", 
#                         value=f"{metrics['green_candles_pct']:.1f}% Green",
#                         help="Percentage of candles that closed higher than they opened."
#                     )
#                 with col6:
#                     st.metric(
#                         label="Average Volatility", 
#                         value=f"{metrics['average_volatility_pct']:.2f}%",
#                         help="Average price amplitude (High vs Low) per candle."
#                     )
                
#                 # Optional: Show the raw JSON below for evaluation defense
#                 with st.expander(" View Raw JSON Response from API"):
#                     st.json(metrics)
                    
#         elif response.status_code == 404:
#             st.warning(f" API Response: {response.json().get('detail', 'No data found')}")
#         else:
#             st.error(f"Error {response.status_code}: {response.text}")
            
#     except requests.exceptions.ConnectionError:
#         st.warning("Unable to contact the API server. Is FastAPI running on port 8000?")

import streamlit as st
import requests
import pandas as pd

st.title("📊 Historical Analytics & Performance")
st.subheader("Analyze market trends and charts extracted from historical data")

st.markdown("---")

days = st.slider("🗓️ Select Timeframe (Past Days):", min_value=1, max_value=30, value=7)

st.markdown("---")

if st.button("📈 Compute Financial Metrics & Charts"):
    api_url = f"http://api:8000/stats?days={days}"
    
    try:
        with st.spinner("Querying database and generating charts..."):
            response = requests.get(api_url)
        
        if response.status_code == 200:
            metrics = response.json()
            
            if metrics.get("status") == "No data available":
                st.warning(f"No market data found in the database for the last {days} days.")
            else:
                st.success(f"Analysis successfully completed!")
                
                # --- ROW 1: st.metric Cards ---
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(label="Highest Price (Max)", value=f"${metrics['max_price']:.2f}")
                with col2:
                    st.metric(label="Lowest Price (Min)", value=f"${metrics['min_price']:.2f}")
                with col3:
                    perf = metrics['performance_pct']
                    st.metric(label="Period Performance", value=f"{perf:+.2f}%", delta=f"{perf:.2f}%")
                
                st.markdown("---")
                
                # --- ROW 2: The Time-Series Chart ---
                if "history" in metrics and metrics["history"]:
                    st.markdown("### 📈 Price Evolution Over Time")
                    
                    # Reconstruct the DataFrame from the API history field
                    df_chart = pd.DataFrame(metrics["history"])
                    
                    # Convert timestamp into human-readable date format
                    df_chart['Date'] = pd.to_datetime(df_chart['timestamp_open'], unit='ms')
                    df_chart = df_chart.sort_values(by='Date')
                    
                    # Plot the line chart mapping Date vs Price
                    st.line_chart(df_chart, x="Date", y="price", use_container_width=True)
                    
                    st.markdown("---")
                
                # --- ROW 3: Advanced Indicators ---
                col4, col5, col6 = st.columns(3)
                with col4:
                    st.metric(label="VWAP", value=f"${metrics['vwap']:.2f}", help="Volume Weighted Avg Price")
                with col5:
                    st.metric(label="Market Sentiment", value=f"{metrics['green_candles_pct']:.1f}% Green")
                with col6:
                    st.metric(label="Average Volatility", value=f"{metrics['average_volatility_pct']:.2f}%")
                    
        elif response.status_code == 404:
            st.warning(f"API Response: {response.json().get('detail')}")
        else:
            st.error(f"Error {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        st.warning("Unable to contact the API server. Is FastAPI running?")