import streamlit as st

# Title and introduction
st.title("🪙 Welcome to Crypto Bot Trading Platform")
st.subheader("Your machine Learning assited  Bot for live market predictions and historical analytics")

st.markdown("---")

# Displaying a beautiful, glowing Bitcoin/Crypto illustration
crypto_image_url = "https://images.unsplash.com/photo-1621761191319-c6fb62004040?q=80&w=600&auto=format&fit=crop"

st.image(
    crypto_image_url, 
    caption="Empowering your financial decisions with Machine Learning.",
    use_container_width=True
)

st.markdown("---")

# Quick guide for the user
st.markdown("""
### Quick Start Guide:
1. **🔮 Live Prediction Tab:** Enter real-time market metrics to get an instant **BUY** or **SELL** decision from our trained ML model.
2. **📊 Historical Stats Tab:** Analyze past performances, average prices, and estimate your future **predicted earnings**.
""")