import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
from shapely.geometry import Point
import random

# Page config
st.set_page_config(page_title="Globe Quiz", layout="wide")

# 1. Load Country Data (Cached for performance)
@st.cache_data
def load_data():
    # Load world countries geojson
    url = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json"
    world = gpd.read_file(url)
    # Filter out Antarctica for the quiz (optional)
    world = world[world.name != "Antarctica"]
    return world

world = load_data()

# 2. Initialize Session State
if "score" not in st.session_state:
    st.session_state.score = 0
if "target_country" not in st.session_state:
    st.session_state.target_country = random.choice(world.name.tolist())
if "message" not in st.session_state:
    st.session_state.message = ""

def next_country():
    st.session_state.target_country = random.choice(world.name.tolist())
    st.session_state.message = ""

# 3. UI Header
st.title("🌍 Blue Marble Geography Quiz")
st.markdown(f"### 🎯 Find: **{st.session_state.target_country}**")
st.markdown(f"**Score:** {st.session_state.score}")
st.write(st.session_state.message)

if st.button("Skip / Next Country"):
    next_country()
    st.rerun()

# 4. Setup the Map (Label-free satellite imagery)
# Using Esri World Imagery for the "blue marble" aesthetic without borders or labels
tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
attr = "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"

m = folium.Map(
    location=[20, 0], 
    zoom_start=2, 
    tiles=tiles, 
    attr=attr,
    min_zoom=2,
    max_bounds=True
)

# 5. Render Map and Capture Clicks
# returned_objects=["last_clicked"] ensures it only reruns when the map is actually clicked
map_data = st_folium(m, height=600, width=1000, returned_objects=["last_clicked"])

# 6. Process Clicks
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lng = map_data["last_clicked"]["lng"]
    
    # Create a Shapely Point from the click coordinates (Longitude first!)
    click_point = Point(lng, lat)
    
    # Check if the point intersects with the target country's geometry
    target_geom = world[world.name == st.session_state.target_country].geometry.values[0]
    
    if target_geom.contains(click_point):
        st.session_state.score += 1
        st.session_state.message = f"✅ **Correct!** That was {st.session_state.target_country}."
        next_country()
        st.rerun()
    else:
        # Optional: Figure out what country they actually clicked on
        clicked_country = None
        for idx, row in world.iterrows():
            if row.geometry.contains(click_point):
                clicked_country = row['name']
                break
                
        if clicked_country:
            st.session_state.message = f"❌ **Incorrect.** You clicked on {clicked_country}. Try again!"
        else:
            st.session_state.message = "❌ **Incorrect.** You clicked in the ocean. Try again!"
        
        st.rerun()
