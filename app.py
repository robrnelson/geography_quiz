import streamlit as st
import streamlit.components.v1 as components
import requests
import random
import os
import math

st.set_page_config(page_title="Geography Quiz", layout="wide")

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculates the distance in miles between two lat/lon points."""
    R = 3958.8 # Radius of Earth in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@st.cache_data
def load_cities():
    # Natural Earth 50m Populated Places dataset
    url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_populated_places_simple.geojson"
    response = requests.get(url)
    data = response.json()
    
    cities_dict = {}
    for f in data["features"]:
        props = f["properties"]
        name = props.get("name")
        country = props.get("adm0name")
        pop = props.get("pop_max", 0)
        
        # Filter for major cities to keep the game playable (e.g., > 1,000,000 people)
        # Lower this number to make the game drastically harder!
        if pop > 10000: 
            coords = f["geometry"]["coordinates"]
            # GeoJSON stores as [longitude, latitude], so we flip them for your logic
            lon, lat = coords[0], coords[1]
            
            # Formats as "Tokyo, Japan"
            cities_dict[f"{name}, {country}"] = (lat, lon)
            
    return cities_dict

# Replace the hardcoded dictionary with this function call:
CITIES = load_cities()

# Connect Python to HTML
parent_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(parent_dir, "frontend")
globe_component = components.declare_component("custom_globe", path=frontend_dir)

# Session State
if "last_click_id" not in st.session_state:
    st.session_state.last_click_id = None

if "last_correct_country" not in st.session_state:
    st.session_state.last_correct_country = None

# --- NEW DATA LOADER ---
@st.cache_data
def load_geo_data():
    url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"
    response = requests.get(url)
    data = response.json()
    
    names = []
    coastlines = {}
    
    for f in data["features"]:
        name = f["properties"]["ADMIN"]
        if name == "Antarctica": continue
        names.append(name)
        
        # Extract every single coordinate on this country's border/coastline
        geom = f["geometry"]
        vertices = []
        if geom["type"] == "Polygon":
            for ring in geom["coordinates"]:
                for lon, lat in ring:
                    vertices.append((lat, lon))
        elif geom["type"] == "MultiPolygon":
            for poly in geom["coordinates"]:
                for ring in poly:
                    for lon, lat in ring:
                        vertices.append((lat, lon))
                        
        coastlines[name] = vertices
        
    return names, coastlines

country_names, country_coastlines = load_geo_data()

# Session State
if "score" not in st.session_state:
    st.session_state.score = 0
if "target_country" not in st.session_state:
    st.session_state.target_country = random.choice(country_names)
if "message" not in st.session_state:
    st.session_state.message = ""
if "message_type" not in st.session_state:
    st.session_state.message_type = "info"
if "selected_country" not in st.session_state:
    st.session_state.selected_country = None
if "pin_lat" not in st.session_state:
    st.session_state.pin_lat = None
if "pin_lon" not in st.session_state:
    st.session_state.pin_lon = None
if "target_city" not in st.session_state:
    st.session_state.target_city = random.choice(list(CITIES.keys()))
if "city_score" not in st.session_state:
    st.session_state.city_score = 0
if "actual_lat" not in st.session_state:
    st.session_state.actual_lat = None
if "actual_lon" not in st.session_state:
    st.session_state.actual_lon = None

def reset_round():
    st.session_state.target_country = random.choice(country_names)
    st.session_state.target_city = random.choice(list(CITIES.keys()))
    st.session_state.selected_country = None
    st.session_state.last_correct_country = None
    st.session_state.pin_lat = None
    st.session_state.pin_lon = None
    st.session_state.actual_lat = None
    st.session_state.actual_lon = None
    st.session_state.message = ""

# UI Setup
st.title("Geography Quizes")

game_mode = st.selectbox("Choose Game Mode:", ["With Borders", "Without Borders", "City Mode"])
show_borders = (game_mode == "With Borders")

if game_mode == "City Mode":
    st.markdown(f"### 🎯 Drop a pin on: **{st.session_state.target_city}**")
    st.markdown(f"**Total Distance Score:** {st.session_state.city_score:,.0f} miles")
else:
    st.markdown(f"### 🎯 Find: **{st.session_state.target_country}**")
    st.markdown(f"**Score:** {st.session_state.score}")
    
if st.session_state.message:
    if st.session_state.message_type == "success":
        st.success(st.session_state.message)
    elif st.session_state.message_type == "error":
        st.error(st.session_state.message)
    elif st.session_state.message_type == "warning":
        st.warning(st.session_state.message)
else:
    st.info("👆 Click a country on the globe, then click Submit.")

col1, col2 = st.columns(2)
with col1:
    submit_clicked = st.button("Submit Guess", type="primary", use_container_width=True)
with col2:
    if st.button("Skip / Next Country", use_container_width=True):
        reset_round()
        st.rerun()

# Render Globe
click_data = globe_component(
    show_borders=show_borders, 
    pin_lat=st.session_state.pin_lat, 
    pin_lon=st.session_state.pin_lon,
    selected_country=st.session_state.selected_country,
    last_correct_country=st.session_state.last_correct_country,
    actual_lat=st.session_state.actual_lat, # NEW
    actual_lon=st.session_state.actual_lon, # NEW
    key="globe_view",
    default=None
)

# Click Logic (with Ghost-Click prevention & Coastline Magnet)
if click_data:
    current_click_id = click_data.get("click_id")

    st.session_state.actual_lat = None
    st.session_state.actual_lon = None

    if current_click_id and current_click_id != st.session_state.last_click_id:
        st.session_state.last_click_id = current_click_id
        
        click_lat = click_data.get("lat")
        click_lon = click_data.get("lon")
        raw_country = click_data.get("country")
        
        st.session_state.pin_lat = click_lat
        st.session_state.pin_lon = click_lon
        st.session_state.last_correct_country = None 
        
        # --- THE UNIVERSAL COASTLINE MAGNET ---
        snapped_country = None
        
        # Only trigger the magnet if they missed and clicked the ocean
        if not raw_country: 
            min_distance = float('inf')
            SNAP_RADIUS_MILES = 60 # Snaps to any coastline within 60 miles
            
            for name, vertices in country_coastlines.items():
                for v_lat, v_lon in vertices:
                    # Quick math filter: Skip checking if the coordinate is obviously too far away
                    lon_diff = abs(v_lon - click_lon)
                    if lon_diff > 180: # Handle the International Date Line
                        lon_diff = 360 - lon_diff
                        
                    if abs(v_lat - click_lat) > 2 or lon_diff > 2:
                        continue
                        
                    # If it's nearby, do the precise curve-of-the-earth calculation
                    dist = haversine_distance(click_lat, click_lon, v_lat, v_lon)
                    if dist < SNAP_RADIUS_MILES and dist < min_distance:
                        snapped_country = name
                        min_distance = dist
                        
        st.session_state.selected_country = snapped_country if snapped_country else raw_country
        # --------------------------------------

        if not st.session_state.selected_country:
            st.session_state.message = "🌊 You clicked the ocean! Please click a landmass."
            st.session_state.message_type = "warning"
        else:
            st.session_state.message = ""
            st.session_state.message_type = "info"
            
        st.rerun()

# Submission Logic
if submit_clicked:

    if game_mode == "City Mode":
        if st.session_state.pin_lat:
            # Calculate distance
            actual_coords = CITIES[st.session_state.target_city]
            dist = haversine_distance(st.session_state.pin_lat, st.session_state.pin_lon, actual_coords[0], actual_coords[1])
            
            st.session_state.city_score += dist
            
            if dist < 100:
                st.session_state.message = f"🎯 Incredible! You were only **{int(dist)} miles** away from {st.session_state.target_city}!"
                st.session_state.message_type = "success"
            else:
                st.session_state.message = f"📍 {st.session_state.target_city} is over there! You were **{int(dist):,} miles** away."
                st.session_state.message_type = "warning"
                
            # Send actual coords to frontend to draw the arc
            st.session_state.actual_lat = actual_coords[0]
            st.session_state.actual_lon = actual_coords[1]
            
            st.session_state.target_city = random.choice(list(CITIES.keys()))
            st.rerun()
        else:
            st.warning("Please drop a pin on the globe first!")
            
    else:
      if st.session_state.selected_country:
        if st.session_state.selected_country == st.session_state.target_country:
            st.session_state.score += 1
            st.session_state.message = f"🎯 **Correct!** That was indeed {st.session_state.selected_country}!"
            st.session_state.message_type = "success"
            st.session_state.last_correct_country = st.session_state.selected_country
            st.session_state.target_country = random.choice(country_names)
            st.session_state.selected_country = None
            st.session_state.pin_lat = None
            st.session_state.pin_lon = None
            st.rerun()
        else:
            st.session_state.message = f"❌ **Incorrect.** You selected {st.session_state.selected_country}. Try again!"
            st.session_state.message_type = "error"
            st.rerun()
      elif st.session_state.pin_lat:
        st.warning("You clicked outside a recognized country. Please click inside a valid border!")
      else:
        st.warning("Please click a country on the globe first before submitting!")
