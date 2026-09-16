import streamlit as st
import streamlit.components.v1 as components
import requests
import random
import os
import math

st.set_page_config(page_title="Geography Quiz", layout="wide")

# A dictionary of small countries/islands and their approximate Lat/Lon centers.
# Make sure the spelling matches your GeoJSON exactly!
SMALL_COUNTRIES = {
    "Fiji": (-17.7134, 178.0650),
    "Bahamas": (25.0343, -77.3963),
    "Vanuatu": (-15.3767, 166.9592),
    "Cyprus": (35.1264, 33.4299),
    "Luxembourg": (49.8153, 6.1296),
    "Jamaica": (18.1096, -77.2975),
    "Qatar": (25.3548, 51.1839),
    "Brunei": (4.5353, 114.7277),
    "Kuwait": (29.3117, 47.4818),
    "Falkland Islands": (-51.7963, -59.5236)
    # If you upgrade to the 50m dataset later, you can add "Vatican", "Monaco", etc. here!
}

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculates the distance in miles between two lat/lon points."""
    R = 3958.8 # Radius of Earth in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Connect Python to HTML
parent_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(parent_dir, "frontend")
globe_component = components.declare_component("custom_globe", path=frontend_dir)

# Session State
if "last_click_id" not in st.session_state:
    st.session_state.last_click_id = None

if "last_correct_country" not in st.session_state:
    st.session_state.last_correct_country = None

@st.cache_data
def get_country_names():
    # Natural Earth 1:50m admin-0 countries: much higher-detail borders
    # than the old folium demo dataset. Its country-name property is
    # "ADMIN" (not "name") - the JS side fetches this same file and must
    # use the same property, or clicked-country names won't match what
    # gets compared against target_country below.
    url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"
    response = requests.get(url)
    data = response.json()
    return [f["properties"]["ADMIN"] for f in data["features"] if f["properties"]["ADMIN"] != "Antarctica"]

country_names = get_country_names()


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

def reset_round():
    st.session_state.target_country = random.choice(country_names)
    st.session_state.selected_country = None
    st.session_state.pin_lat = None
    st.session_state.pin_lon = None
    st.session_state.message = ""

# UI Setup
st.title("Geography Quiz")

game_mode = st.selectbox("Choose Border Mode:", ["Without borders", "With white borders"])
show_borders = (game_mode == "With white borders")

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
    selected_country=st.session_state.selected_country, # <-- ADD THIS LINE
    last_correct_country=st.session_state.last_correct_country, # <-- Add this line!
    key="globe_view",
    default=None
)

# Click Logic (with Ghost-Click prevention & Forgiving Click)
if click_data:
    current_click_id = click_data.get("click_id")
    
    if current_click_id and current_click_id != st.session_state.last_click_id:
        st.session_state.last_click_id = current_click_id
        
        click_lat = click_data.get("lat")
        click_lon = click_data.get("lon")
        raw_country = click_data.get("country")
        
        st.session_state.pin_lat = click_lat
        st.session_state.pin_lon = click_lon
        st.session_state.last_correct_country = None # Clear previous highlight
        
        # --- THE FORGIVING CLICK (MAGNET EFFECT) ---
        snapped_country = None
        min_distance = float('inf')
        SNAP_RADIUS_MILES = 100 
        
        for name, coords in SMALL_COUNTRIES.items():
            dist = haversine_distance(click_lat, click_lon, coords[0], coords[1])
            if dist < SNAP_RADIUS_MILES and dist < min_distance:
                snapped_country = name
                min_distance = dist
                
        # If the click was close to a small island, override the raw click!
        if snapped_country:
            st.session_state.selected_country = snapped_country
        else:
            st.session_state.selected_country = raw_country
        # -------------------------------------------

        if not st.session_state.selected_country:
            st.session_state.message = "🌊 You clicked the ocean! Please click a landmass."
            st.session_state.message_type = "warning"
        else:
            st.session_state.message = ""
            st.session_state.message_type = "info"
            
        st.rerun()

# Submission Logic
if submit_clicked:
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
