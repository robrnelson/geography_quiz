import streamlit as st
import pydeck as pdk
import requests
import random

# Page config
st.set_page_config(page_title="3D Globe Quiz", layout="wide")

# 1. Load Country Data (No Geopandas needed!)
@st.cache_data
def load_data():
    # Grab the world geojson directly
    url = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json"
    response = requests.get(url)
    data = response.json()
    
    # Filter out Antarctica
    data["features"] = [f for f in data["features"] if f["properties"]["name"] != "Antarctica"]
    return data

geojson_data = load_data()
country_names = [f["properties"]["name"] for f in geojson_data["features"]]

# 2. Initialize Session State
if "score" not in st.session_state:
    st.session_state.score = 0
if "target_country" not in st.session_state:
    st.session_state.target_country = random.choice(country_names)
if "message" not in st.session_state:
    st.session_state.message = ""
if "last_selection_names" not in st.session_state:
    st.session_state.last_selection_names = []

def next_country():
    st.session_state.target_country = random.choice(country_names)
    st.session_state.message = ""

# 3. UI Header
st.title("🌍 3D Blue Marble Geography Quiz")
st.markdown(f"### 🎯 Find: **{st.session_state.target_country}**")
st.markdown(f"**Score:** {st.session_state.score}")
st.write(st.session_state.message)

if st.button("Skip / Next Country"):
    next_country()
    st.rerun()

# 4. Setup PyDeck Layers

# Wrap a single equirectangular Earth image around the globe
# This avoids the WebGL tearing caused by XYZ tile layers on 3D spheres
globe_layer = pdk.Layer(
    "BitmapLayer",
    image="https://upload.wikimedia.org/wikipedia/commons/c/c4/Earthmap1000x500compac.jpg",
    bounds=[-180, -90, 180, 90],
    pickable=False
)

# Invisible GeoJSON layer on top to capture clicks and highlight countries
geojson_layer = pdk.Layer(
    "GeoJsonLayer",
    id="countries",
    data=geojson_data,
    opacity=1,
    stroked=False,
    filled=True,
    extruded=False,
    # 0 alpha means entirely transparent until hovered
    get_fill_color=[255, 255, 255, 0],  
    pickable=True,
    auto_highlight=True,
    # Flashes a transparent white over the country when hovered
    highlight_color=[255, 255, 255, 60] 
)

# 5. Create the 3D Globe View
view = pdk.View(type="_GlobeView", controller=True)

deck = pdk.Deck(
    views=[view],
    initial_view_state=pdk.ViewState(
        longitude=0,
        latitude=0,
        zoom=1,
        min_zoom=0,
        max_zoom=10
    ),
    # Swap out the tile layer for the new globe layer
    layers=[globe_layer, geojson_layer],
    map_provider=None, 
)

# 6. Render and capture clicks
# Note: Streamlit 1.35+ is required for the on_select parameter
deck_event = st.pydeck_chart(deck, on_select="rerun", selection_mode="single-object", height=600)

# 7. Process clicks
# Extract the names of currently selected countries (should be 0 or 1)
current_selection_names = []
if deck_event and deck_event.selection.objects.get("countries"):
    current_selection_names = [f["properties"]["name"] for f in deck_event.selection.objects["countries"]]

# Compare with last selection to avoid the "ghost click" rerun bug
if current_selection_names != st.session_state.last_selection_names:
    st.session_state.last_selection_names = current_selection_names
    
    # If they actually clicked a country (and didn't just deselect)
    if current_selection_names:
        clicked_country = current_selection_names[0]
        
        if clicked_country == st.session_state.target_country:
            st.session_state.score += 1
            st.session_state.message = f"✅ **Correct!** That was {clicked_country}."
            next_country()
            st.rerun()
        else:
            st.session_state.message = f"❌ **Incorrect.** You clicked on {clicked_country}. Try again!"
            st.rerun()
