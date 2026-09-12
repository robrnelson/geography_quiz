import streamlit as st
import streamlit.components.v1 as components
from geopy.distance import geodesic
import os

st.set_page_config(page_title="Blue Marble Quiz", layout="wide")

# 1. Connect Python to the HTML/JS Frontend
parent_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(parent_dir, "frontend")
globe_component = components.declare_component("blue_marble", path=frontend_dir)

# 2. Set Up the Game State
st.title("🌍 MapTap Clone: Blue Marble Edition")

# A simple target (You can expand this into a daily list later)
target = {"name": "The Great Pyramid of Giza", "lat": 29.9792, "lon": 31.1342}

st.markdown(f"### 🎯 Find: **{target['name']}**")

# 3. Render the Globe and Capture Clicks
# This component returns the dictionary {lat, lon} sent from JavaScript
click_data = globe_component(key="globe_view")

# 4. Scoring Logic (MapTap Style)
if click_data:
    click_lat = click_data["lat"]
    click_lon = click_data["lon"]
    
    # Calculate precise distance over the curve of the Earth
    distance_km = geodesic((click_lat, click_lon), (target["lat"], target["lon"])).km
    
    # Simple scoring algorithm: Max 5000 points, lose 1 point per km off
    score = max(0, int(5000 - distance_km))
    
    st.divider()
    if distance_km < 100:
        st.success(f"**Incredible!** You were only {distance_km:.0f} km away. Score: {score}/5000")
    else:
        st.warning(f"**Not quite.** You were {distance_km:.0f} km away. Score: {score}/5000")
        
    st.info(f"📍 Your tap: {click_lat:.2f}, {click_lon:.2f} | Target: {target['lat']:.2f}, {target['lon']:.2f}")
