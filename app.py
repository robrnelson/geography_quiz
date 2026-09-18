import streamlit as st
import streamlit.components.v1 as components
import requests
import random
import math
import os

# --- PAGE CONFIG ---
st.set_page_config(layout="wide")

# --- COMPONENT SETUP ---
# Adjust the path if your index.html is located elsewhere
parent_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(parent_dir, "frontend")
globe_component = components.declare_component("globe_component", path=frontend_dir)

# --- DATA LOADERS ---
@st.cache_data
def load_geo_data():
    url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"
    response = requests.get(url)
    data = response.json()
    
    names = []
    coastlines = {}
    
    for f in data["features"]:
        name = f["properties"]["ADMIN"]
        if name == "Antarctica": 
            continue
        names.append(name)
        
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

@st.cache_data
def load_cities():
    url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_populated_places_simple.geojson"
    response = requests.get(url)
    data = response.json()
    
    cities_dict = {}
    for f in data["features"]:
        props = f["properties"]
        name = props.get("name")
        country = props.get("adm0name")
        pop = props.get("pop_max", 0)
        
        if pop > 1000000: 
            coords = f["geometry"]["coordinates"]
            lon, lat = coords[0], coords[1]
            cities_dict[f"{name}, {country}"] = (lat, lon)
            
    return cities_dict

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 3958.8 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

country_names, country_coastlines = load_geo_data()
CITIES = load_cities()

# --- SESSION STATE INITIALIZATION ---
if "target_country" not in st.session_state:
    st.session_state.target_country = random.choice(country_names)
if "target_city" not in st.session_state:
    st.session_state.target_city = random.choice(list(CITIES.keys()))
if "score" not in st.session_state:
    st.session_state.score = 0
if "city_score" not in st.session_state:
    st.session_state.city_score = 0

if "selected_country" not in st.session_state:
    st.session_state.selected_country = None
if "last_correct_country" not in st.session_state:
    st.session_state.last_correct_country = None
if "pin_lat" not in st.session_state:
    st.session_state.pin_lat = None
if "pin_lon" not in st.session_state:
    st.session_state.pin_lon = None
if "actual_lat" not in st.session_state:
    st.session_state.actual_lat = None
if "actual_lon" not in st.session_state:
    st.session_state.actual_lon = None

if "message" not in st.session_state:
    st.session_state.message = ""
if "message_type" not in st.session_state:
    st.session_state.message_type = "info"
if "last_click_id" not in st.session_state:
    st.session_state.last_click_id = None

# --- UI SETUP ---
# 1. CSS Injection to remove dead space and force side-by-side mobile buttons
st.markdown("""
    <style>
    /* Remove massive empty space at the top of the app */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
    }
    /* Force all Streamlit columns to NEVER stack vertically on phones */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
    }
    /* Allow columns to shrink to fit side-by-side */
    [data-testid="column"] {
        min-width: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 2. Top Row: Game Mode & Score (Side-by-Side)
top_col1, top_col2 = st.columns([2, 1], vertical_alignment="center")
with top_col1:
    game_mode = st.selectbox(
        "Mode:", 
        ["With Borders", "Without Borders", "City Mode"], 
        label_visibility="collapsed"
    )
with top_col2:
    if game_mode == "City Mode":
        st.write(f"**Score:** {st.session_state.city_score:,.0f} mi")
    else:
        st.write(f"**Score:** {st.session_state.score}")

show_borders = (game_mode == "With Borders")

# 3. Middle Row: The Target (Using standard text instead of bulky headers)
if game_mode == "City Mode":
    st.write(f"🎯 Drop pin on: **{st.session_state.target_city}**")
else:
    st.write(f"🎯 Find: **{st.session_state.target_country}**")

# 4. Bottom Row: Action Buttons
btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    submit_clicked = st.button("Submit Guess", use_container_width=True, type="primary")
with btn_col2:
    skip_clicked = st.button("Skip", use_container_width=True)



if st.session_state.message:
    if st.session_state.message_type == "success":
        st.success(st.session_state.message)
    elif st.session_state.message_type == "warning":
        st.warning(st.session_state.message)
    else:
        st.info(st.session_state.message)

# --- GLOBE COMPONENT RENDER ---
click_data = globe_component(
    show_borders=show_borders, 
    pin_lat=st.session_state.pin_lat, 
    pin_lon=st.session_state.pin_lon,
    selected_country=st.session_state.selected_country,
    last_correct_country=st.session_state.last_correct_country,
    actual_lat=st.session_state.actual_lat,
    actual_lon=st.session_state.actual_lon,
    key="globe_view",
    default=None
)

# --- CLICK LOGIC ---
if click_data:
    current_click_id = click_data.get("click_id")
    
    if current_click_id and current_click_id != st.session_state.last_click_id:
        st.session_state.last_click_id = current_click_id
        
        click_lat = click_data.get("lat")
        click_lon = click_data.get("lon")
        raw_country = click_data.get("country")
        
        st.session_state.pin_lat = click_lat
        st.session_state.pin_lon = click_lon
        
        # Clear previous highlights/arcs on new click
        st.session_state.last_correct_country = None 
        st.session_state.actual_lat = None
        st.session_state.actual_lon = None
        
        snapped_country = None
        
        # Coastline Magnet Effect
        if not raw_country: 
            min_distance = float('inf')
            SNAP_RADIUS_MILES = 60 
            
            for name, vertices in country_coastlines.items():
                for v_lat, v_lon in vertices:
                    lon_diff = abs(v_lon - click_lon)
                    if lon_diff > 180:
                        lon_diff = 360 - lon_diff
                        
                    if abs(v_lat - click_lat) > 2 or lon_diff > 2:
                        continue
                        
                    dist = haversine_distance(click_lat, click_lon, v_lat, v_lon)
                    if dist < SNAP_RADIUS_MILES and dist < min_distance:
                        snapped_country = name
                        min_distance = dist
                        
        st.session_state.selected_country = snapped_country if snapped_country else raw_country

        if not st.session_state.selected_country and game_mode != "City Mode":
            st.session_state.message = "🌊 You clicked the ocean! Please click a landmass."
            st.session_state.message_type = "warning"
        else:
            st.session_state.message = ""
            st.session_state.message_type = "info"
            
        st.rerun()

# --- SUBMISSION & SKIP LOGIC ---
if submit_clicked:
    if game_mode == "City Mode":
        if st.session_state.pin_lat:
            actual_coords = CITIES[st.session_state.target_city]
            dist = haversine_distance(st.session_state.pin_lat, st.session_state.pin_lon, actual_coords[0], actual_coords[1])
            
            st.session_state.city_score += dist
            
            if dist < 100:
                st.session_state.message = f"🎯 Incredible! You were only **{int(dist)} miles** away from {st.session_state.target_city}!"
                st.session_state.message_type = "success"
            else:
                st.session_state.message = f"📍 {st.session_state.target_city} is over there! You were **{int(dist):,} miles** away."
                st.session_state.message_type = "warning"
                
            st.session_state.actual_lat = actual_coords[0]
            st.session_state.actual_lon = actual_coords[1]
            st.session_state.target_city = random.choice(list(CITIES.keys()))
            st.rerun()
        else:
            st.session_state.message = "Please drop a pin on the globe first!"
            st.session_state.message_type = "warning"
            st.rerun()
            
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
            else:
                st.session_state.message = f"❌ Incorrect. You clicked {st.session_state.selected_country}."
                st.session_state.message_type = "warning"
            st.rerun()
        else:
            st.session_state.message = "Please select a country first!"
            st.session_state.message_type = "warning"
            st.rerun()

elif skip_clicked:
    # Pick a new target
    if game_mode == "City Mode":
        st.session_state.target_city = random.choice(list(CITIES.keys()))
    else:
        st.session_state.target_country = random.choice(country_names)
        
    # Clear all messages so nothing displays
    st.session_state.message = ""
    
    # Reset all map selections
    st.session_state.selected_country = None
    st.session_state.last_correct_country = None
    st.session_state.pin_lat = None
    st.session_state.pin_lon = None
    st.session_state.actual_lat = None
    st.session_state.actual_lon = None
    
    st.rerun()
