import streamlit as st
import requests
import os
import pandas as pd
from openai import OpenAI

# =========================
# CONFIGURATION
# =========================
WEATHER_API_KEY = "b2feaafb8b09d872b76e4c0ccdd90878"

# Initialize AI Client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "your_actual_key_here"),
    base_url="https://vjioo4r1vyvcozuj.us-east-2.aws.endpoints.huggingface.cloud/v1",
)

# =========================
# FUNCTIONS
# =========================

def get_coords(location_name):
    url = f"https://nominatim.openstreetmap.org/search?q={location_name},Kenya&format=json"
    try:
        response = requests.get(url, headers={'User-Agent': 'Shamba_App_2026'}).json()
        if response:
            return float(response[0]['lat']), float(response[0]['lon'])
    except Exception: return None, None
    return None, None

def get_soil_type(lat, lon):
    url = f"https://api.cropmanage.ucanr.edu/v2/soil-web.json?lat={lat}&lng={lon}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        return data.get("Texture", "Loamy Soil")
    except Exception: return "Loamy Soil"

# =========================
# STREAMLIT PAGE SETUP
# =========================
st.set_page_config(page_title="shamba", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #e8f5e9; }
    
    .massive-logo {
        font-family: 'Arial Black', Impact, sans-serif !important;
        color: #1b5e20 !important;
        font-size: 160px !important; 
        font-weight: 900 !important;
        letter-spacing: -8px !important;
        margin-top: -50px !important;
        margin-bottom: -20px !important;
        line-height: 0.8 !important;
        text-shadow: 6px 6px 0px #b2d8b2 !important;
        display: block !important;
    }

    .shamba-sub {
        color: #2e7d32;
        font-size: 24px;
        font-weight: 500;
        margin-bottom: 40px;
    }

    .action-card {
        background-color: #ffffff;
        padding: 40px;
        border-radius: 20px;
        border-left: 15px solid #1b5e20;
        box-shadow: 0 12px 24px rgba(0,0,0,0.1);
        color: #1b3022;
        font-size: 19px;
    }

    .stButton>button {
        background-color: #1b5e20;
        color: white;
        width: 100%;
        border-radius: 12px;
        height: 4em;
        font-weight: bold;
        font-size: 26px;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="massive-logo">shamba</div>', unsafe_allow_html=True)
st.markdown('<p class="shamba-sub"></p>', unsafe_allow_html=True)

# USER INPUT
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        location = st.text_input("Village or Town", "Nakuru")
        crop = st.selectbox("Crop Growing", ["Beans", "Maize", "Tomatoes", "Coffee", "Wheat"])
    with col2:
        irrigation = st.radio("Irrigation", ["Rain-fed", "Irrigated"], horizontal=True)
        weeks = st.number_input("Weeks Since Planting", 0, 52, 5)

# SESSION STATE
if 'advice' not in st.session_state: st.session_state.advice = None

# GENERATE
if st.button("Generate My 7-Day Plan"):
    with st.spinner("Analyzing farm data for Kenyan conditions..."):
        lat, lon = get_coords(location)
        if lat is not None:
            soil = get_soil_type(lat, lon)
            w_res = requests.get(f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric").json()
            forecast = w_res["list"]
            rain = sum(item.get("rain", {}).get("3h", 0) for item in forecast)
            
            # --- REALISTIC KENYAN PROMPT ---
            prompt = (
                f"You are a local Kenyan Agronomist helping a small-scale farmer. "
                f"Give a 7-day action plan for {crop} in {location}. "
                f"Soil: {soil}, Forecasted Rain: {rain}mm. "
                "CRITICAL INSTRUCTIONS: "
                "1. Only suggest low-cost, realistic tools and methods available in rural Kenya. "
                "2. Suggest using manure, compost, mulching with dry grass, and wood ash where appropriate. "
                "3. If rain is low, suggest water-saving methods like 'Zai pits' or bottle irrigation. "
                "4. Avoid suggesting expensive laboratory tests or heavy machinery. "
                "Format every point as: "
                "**STEP [X]:** [Clear action] \n"
                "**WHY IT MATTERS:** [Explanation]. "
                "No general advice, no intro, no conclusions."
            )
            
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=900
            )
            st.session_state.advice = response.choices[0].message.content
            st.session_state.soil = soil
            st.session_state.rain = rain
            st.session_state.temp = forecast[0]['main']['temp']
            st.session_state.hum = sum(item["main"]["humidity"] for item in forecast) / len(forecast)
            st.session_state.lat, st.session_state.lon = lat, lon

# OUTPUT
if st.session_state.advice:
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Soil", st.session_state.soil)
    m2.metric("Rain", f"{st.session_state.rain:.1f} mm")
    m3.metric("Humidity", f"{st.session_state.hum:.0f}%")
    m4.metric("Temp", f"{st.session_state.temp}°C")

    st.markdown('<p style="font-size: 32px; font-weight: bold; color: #1b5e20; margin-top:20px;">Your Expert Plan</p>', unsafe_allow_html=True)
    
    if st.button("Tafsiri kwa Kiswahili (Translate)"):
        with st.spinner("Inatafsiri..."):
            tr_res = client.chat.completions.create(
                model="openai/gpt-oss-120b", 
                messages=[{"role": "user", "content": f"Translate this perfectly into simple Kenyan Swahili that a local farmer would understand: {st.session_state.advice}"}]
            )
            st.markdown(f'<div class="action-card">{tr_res.choices[0].message.content.replace("**", "<b>").replace("\n", "<br>")}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="action-card">{st.session_state.advice.replace("**", "<b>").replace("\n", "<br>")}</div>', unsafe_allow_html=True)
    
    st.map(pd.DataFrame({'lat': [st.session_state.lat], 'lon': [st.session_state.lon]}))
