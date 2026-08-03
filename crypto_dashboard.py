import streamlit as st

# Define the pages of your application (Adding the Home Page first)
home_page = st.Page("page_home.py", title="Home", icon="🏠")
predict_page = st.Page("page_prediction.py", title="Live Prediction", icon="🔮")
stats_page = st.Page("page_stats.py", title="Historical Stats", icon="📊")

# Create the navigation sidebar menu
pg = st.navigation([home_page, predict_page, stats_page])

# Run the selected page
pg.run()