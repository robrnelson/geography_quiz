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
# 1. Minimal CSS to hide the Streamlit header, tighten padding around every
# element (Streamlit gives each st.write/st.button its own vertical margin
# by default - this is most of the wasted space on a short mobile screen,
# not the elements' own heights), and shrink the button/selectbox font a
# touch so more of the screen goes to the globe.
st.markdown("""
    <style>
    header[data-testid="stHeader"] {
        display: none !important;
    }
    .block-container {
        padding-top: 0.75rem !important;
        padding-bottom: 0rem !important;
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
    }
    /* every element Streamlit renders gets wrapped in a div with this
       testid, regardless of nesting depth - a more version-stable target
       than guessing at the exact DOM structure. Streamlit gives each one a
       default top margin; shrinking it is most of the wasted vertical
       space on a short mobile screen, not the elements' own heights. */
    div[data-testid="stElementContainer"] {
        margin-bottom: 0.25rem !important;
    }
    div[data-testid="stButton"] > button {
        padding-top: 0.25rem !important;
        padding-bottom: 0.25rem !important;
        font-size: 0.9rem !important;
    }
    /* Streamlit stacks st.columns vertically by default below a mobile
       breakpoint, which is exactly what we don't want here - override its
       responsive behavior to force the two button columns to always stay
       side by side, regardless of screen width. */
    div[data-testid="stHorizontalBlock"] {
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 0.5rem !important;
    }
    div[data-testid="stColumn"] {
        width: 50% !important;
        flex: 1 1 0 !important;
        min-width: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 2. Game Mode Dropdown
game_mode = st.selectbox(
    "Mode:", 
    ["With Borders", "Without Borders", "City Mode"], 
    label_visibility="collapsed"
)
show_borders = (game_mode == "With Borders")

# 3/4. Score + target combined onto a single line (was two separate
# st.write calls, each carrying its own margin) - a flex row with the
# target on the left and score on the right uses the width of the
# screen instead of stacking, saving a full line of vertical space.
if game_mode == "City Mode":
    target_html = f"🎯 Drop pin on: <b>{st.session_state.target_city}</b>"
    score_html = f"<b>{st.session_state.city_score:,.0f}</b> mi"
else:
    target_html = f"🎯 Find: <b>{st.session_state.target_country}</b>"
    score_html = f"<b>{st.session_state.score}</b>"

st.markdown(
    f"""
    <div style="display:flex; justify-content:space-between; align-items:baseline;
                font-size:0.95rem; margin-bottom:0.25rem;">
        <span>{target_html}</span>
        <span>Score: {score_html}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# 5. Buttons side by side instead of stacked - each takes half the row.
# gap="small" trims the default spacing Streamlit puts between columns,
# which matters more than it sounds like on a narrow phone screen.
btn_col1, btn_col2 = st.columns(2, gap="small")
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
