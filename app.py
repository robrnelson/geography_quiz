import streamlit as st
import plotly.express as px
import requests
import random
import pandas as pd

# Page config
st.set_page_config(page_title="3D Globe Quiz", layout="wide")

# 1. Load Country Data
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json"
    response = requests.get(url)
    data = response.json()
    
    # Filter out Antarctica
    data["features"] = [f for f in data["features"] if f["properties"]["name"] != "Antarctica"]
    
    # Build dataframe for Plotly
    countries = [{"name": f["properties"]["name"]} for f in data["features"]]
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

# 4. Create the 3D Orthographic Globe using Plotly
df["val"] = 1  # Uniform placeholder value for coloring
fig = px.choropleth(
    df,
    geojson=geojson_data,
    locations="name",
    featureidkey="properties.name",
    color="val",
    color_continuous_scale=[[0, "rgb(30, 60, 100)"], [1, "rgb(35, 70, 110)"]]
)

# Style it to look like a clean blue marble globe with no borders or labels
fig.update_geos(
    projection_type="orthographic",
    showocean=True,
    oceancolor="rgb(10, 25, 45)",
    showland=True,
    landcolor="rgb(30, 50, 75)",
    showcountries=False,  # No country borders
    showcoastlines=False, # No coastlines
    showlakes=False,
    showrivers=False,
    bgcolor="rgba(0,0,0,0)"
)

fig.update_layout(
    height=650,
    margin={"r":0, "t":0, "l":0, "b":0},
    coloraxis_showscale=False
)

# 5. Render Globe and Capture Clicks
event = st.plotly_chart(
    fig, 
    on_select="rerun", 
    selection_mode="points", 
    use_container_width=True
)

# 6. Process Clicks
if event and "selection" in event and "points" in event["selection"]:
    points = event["selection"]["points"]
    if points:
        clicked_country = points[0].get("location")
        
        if clicked_country:
            if clicked_country == st.session_state.target_country:
                st.session_state.score += 1
                st.session_state.message = f"✅ **Correct!** That was {clicked_country}."
                next_country()
                st.rerun()
            else:
                st.session_state.message = f"❌ **Incorrect.** You clicked on {clicked_country}. Try again!"
                st.rerun()
