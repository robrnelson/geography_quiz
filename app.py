import streamlit as st
import streamlit.components.v1 as components
import requests
import random

st.set_page_config(page_title="Blue Marble Quiz", layout="wide")

# Tell Streamlit to just look in the folder named "frontend" in the same directory
globe_component = components.declare_component("blue_marble", path="frontend")
# Connect Python to the HTML/JS Frontend
parent_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(parent_dir, "frontend")

# --- ADD THIS DEBUGGING BLOCK ---
if not os.path.exists(frontend_dir):
    st.error(f"🚨 Python cannot find the frontend folder! It is looking here: {frontend_dir}")
    st.stop()
elif not os.path.exists(os.path.join(frontend_dir, "index.html")):
    st.error(f"🚨 Python found the folder, but `index.html` is missing inside: {frontend_dir}")
    st.stop()
# --------------------------------

globe_component = components.declare_component("blue_marble", path=frontend_dir)
# 2. Load Country List for Targets
@st.cache_data
def get_country_names():
    url = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json"
    response = requests.get(url)
    data = response.json()
    return [f["properties"]["name"] for f in data["features"] if f["properties"]["name"] != "Antarctica"]

country_names = get_country_names()

# 3. Initialize Session State
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

def reset_selection():
    st.session_state.target_country = random.choice(country_names)
    st.session_state.selected_country = None
    st.session_state.pin_lat = None
    st.session_state.pin_lon = None

# 4. UI Layout
st.title("🌍 3D Blue Marble Geography Quiz")

game_mode = st.selectbox("Choose Border Mode:", ["Without borders", "With white borders"])
show_borders = (game_mode == "With white borders")

st.markdown(f"### 🎯 Find: **{st.session_state.target_country}**")
st.markdown(f"**Score:** {st.session_state.score}")

if st.session_state.message:
    if st.session_state.message_type == "success":
        st.success(st.session_state.message)
    elif st.session_state.message_type == "error":
        st.error(st.session_state.message)
else:
    st.info("👆 Click a country on the globe, then click Submit.")

# Action Buttons
col1, col2 = st.columns(2)
with col1:
    submit_clicked = st.button("Submit Guess", type="primary", use_container_width=True)
with col2:
    if st.button("Skip / Next Country", use_container_width=True):
        st.session_state.message = ""
        st.session_state.message_type = "info"
        reset_selection()
        st.rerun()

# 5. Render Globe and Capture Clicks
click_data = globe_component(
    show_borders=show_borders, 
    pin_lat=st.session_state.pin_lat, 
    pin_lon=st.session_state.pin_lon,
    key="globe_view",
    default=None  # <-- ADD THIS LINE
)
# 6. Handle Selection Updates from the Map
if click_data:
    # If the exact click location has changed, update our state
    if click_data.get("lat") != st.session_state.pin_lat or click_data.get("lon") != st.session_state.pin_lon:
        st.session_state.pin_lat = click_data["lat"]
        st.session_state.pin_lon = click_data["lon"]
        st.session_state.selected_country = click_data.get("country")
        st.session_state.message = ""
        st.session_state.message_type = "info"
        
        # Warn them if they clicked the ocean
        if not st.session_state.selected_country:
            st.warning("You clicked the ocean! Please click a landmass.")
            
        st.rerun()

# 7. Process Submission Logic
if submit_clicked:
    if st.session_state.selected_country:
        if st.session_state.selected_country == st.session_state.target_country:
            st.session_state.score += 1
            st.session_state.message = f"🎯 **Correct!** That was indeed {st.session_state.selected_country}!"
            st.session_state.message_type = "success"
            reset_selection()
            st.rerun()
        else:
            st.session_state.message = f"❌ **Incorrect.** You selected {st.session_state.selected_country}. Try again!"
            st.session_state.message_type = "error"
            st.rerun()
    elif st.session_state.pin_lat:
        st.warning("You clicked outside a recognized country. Please click inside a valid border!")
    else:
        st.warning("Please click a country on the globe first before submitting!")
