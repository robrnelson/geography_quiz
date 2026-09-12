import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import requests
import random
import pandas as pd

# Page config
st.set_page_config(page_title="3D Globe Quiz", layout="wide")

# 1. Load Country Data & Compute Centroids for Pins
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json"
    response = requests.get(url)
    data = response.json()
    
    # Filter out Antarctica
    data["features"] = [f for f in data["features"] if f["properties"]["name"] != "Antarctica"]
    
    countries = []
    for f in data["features"]:
        name = f["properties"]["name"]
        geom = f["geometry"]
        
        # Helper to extract coordinates and compute a center point
        lons, lats = [], []
        def parse_coords(coords):
            if isinstance(coords[0], (list, tuple)):
                for sub in coords:
                    parse_coords(sub)
            else:
                lons.append(coords[0])
                lats.append(coords[1])
        parse_coords(geom["coordinates"])
        
        lat = sum(lats) / len(lats) if lats else 0
        lon = sum(lons) / len(lons) if lons else 0
        countries.append({"name": name, "lat": lat, "lon": lon})
        
    return pd.DataFrame(countries), data

df, geojson_data = load_data()
country_names = df["name"].tolist()

# 2. Initialize Session State
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

def reset_selection_and_target():
    st.session_state.target_country = random.choice(country_names)
    st.session_state.selected_country = None

# 3. UI Header & Game Mode Dropdown
st.title("🌍 3D Blue Marble Geography Quiz")

game_mode = st.selectbox(
    "Choose Border Mode:", 
    ["Without borders", "With white borders"]
)
show_borders = (game_mode == "With white borders")

st.markdown(f"### 🎯 Find: **{st.session_state.target_country}**")
st.markdown(f"**Score:** {st.session_state.score}")

# Display dynamic feedback boxes
if st.session_state.message:
    if st.session_state.message_type == "success":
        st.success(st.session_state.message)
    elif st.session_state.message_type == "error":
        st.error(st.session_state.message)
else:
    st.info("📍 Click a country on the globe, then click Submit.")

# Action Buttons
col1, col2 = st.columns(2)
with col1:
    submit_clicked = st.button("Submit Guess", type="primary", use_container_width=True)
with col2:
    if st.button("Skip / Next Country", use_container_width=True):
        st.session_state.message = ""
        st.session_state.message_type = "info"
        reset_selection_and_target()
        st.rerun()

# 4. Create the 3D Orthographic Globe using Plotly
df["val"] = 1  
fig = px.choropleth(
    df,
    geojson=geojson_data,
    locations="name",
    featureidkey="properties.name",
    color="val",
    color_continuous_scale=[[0, "rgb(30, 60, 100)"], [1, "rgb(35, 70, 110)"]],
    hover_name=None,
    hover_data={"val": False, "name": False}
)

# Disable hover tooltips completely
fig.update_traces(
    hoverinfo="none", 
    hovertemplate=None,
    marker_line_width=1 if show_borders else 0,
    marker_line_color="white" if show_borders else "rgba(0,0,0,0)"
)

# If in "Without borders" mode and a country is selected, drop a pin on it
if not show_borders and st.session_state.selected_country:
    selected_row = df[df["name"] == st.session_state.selected_country]
    if not selected_row.empty:
        fig.add_trace(go.Scattergeo(
            lat=selected_row["lat"],
            lon=selected_row["lon"],
            mode="markers",
            marker=dict(size=10, color="red", symbol="circle"),
            hoverinfo="none"
        ))

# Style globe with dynamic border settings
fig.update_geos(
    projection_type="orthographic",
    showocean=True,
    oceancolor="rgb(10, 25, 45)",
    showland=True,
    landcolor="rgb(30, 50, 75)",
    showcountries=show_borders,
    countrycolor="white",
    showcoastlines=show_borders,
    coastlinecolor="white",
    showlakes=False,
    showrivers=False,
    bgcolor="rgba(0,0,0,0)"
)

fig.update_layout(
    height=600,
    margin={"r":0, "t":0, "l":0, "b":0},
    coloraxis_showscale=False,
    showlegend=False
)

# 5. Render Globe and Capture Clicks
event = st.plotly_chart(
    fig, 
    on_select="rerun", 
    selection_mode="points", 
    use_container_width=True,
    key="globe_view"
)

# 6. Handle Selection Updates from Map Interaction
if event and "selection" in event and "points" in event["selection"]:
    points = event["selection"]["points"]
    if points:
        clicked = points[0].get("location")
        if clicked and clicked != st.session_state.selected_country:
            st.session_state.selected_country = clicked
            st.session_state.message = ""
            st.session_state.message_type = "info"
            st.rerun()

# 7. Process Submission Logic
if submit_clicked:
    if st.session_state.selected_country:
        if st.session_state.selected_country == st.session_state.target_country:
            st.session_state.score += 1
            st.session_state.message = f"🎉 **Correct!** That was indeed {st.session_state.selected_country}!"
            st.session_state.message_type = "success"
            reset_selection_and_target()
            st.rerun()
        else:
            st.session_state.message = f"❌ **Incorrect.** You selected {st.session_state.selected_country}. Try again!"
            st.session_state.message_type = "error"
            st.rerun()
    else:
        st.warning("Please click a country on the globe first before submitting!")
