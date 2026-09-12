# Globe Quiz

Click-the-country geography game: a name pops up, you find that country on a
rotating globe and click inside its borders.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Needs internet access on first run (and once per session, cached afterward)
to download the world country border data used to draw the globe and check
clicks.

## How it works

- The globe is a Plotly `Choropleth` trace in `orthographic` projection —
  that's what gives the 3D rotatable globe look. Every country is painted
  the same green and the ocean the same blue, and borders/labels are
  turned off, so it reads as a plain globe rather than a labeled atlas.
- **Drag** the globe with your mouse to rotate it and find the target
  country from any angle.
- Click detection doesn't need manual point-in-polygon math: Plotly's
  choropleth click event already reports which country polygon (by
  ISO-3 code) was under the cursor, so we just compare that to the
  target country.
- A wrong click tells you what you actually clicked, so you can
  triangulate toward the right spot. Ocean clicks are called out
  separately. Correct answers flash gold and immediately load the next
  country. Score, accuracy, and streaks are tracked in the sidebar, and
  a "Restart game" button resets everything.

## Notes / tweaks

- Country list comes from a public GeoJSON
  (`johan/world.geo.json`). A handful of disputed territories without a
  standard ISO-3 code (e.g. some breakaway regions) are drawn on the map
  but never used as quiz targets, to avoid ambiguous answers.
- If `streamlit-plotly-events` throws an error on newer Streamlit
  versions, downgrade Streamlit to something in the `1.28–1.35` range
  as pinned in `requirements.txt` — that component hasn't been updated
  for the newest Streamlit component APIs.
- Want harder mode? Change `LAND_COLOR`/`OCEAN_COLOR` in `app.py`, or
  strip the wrong-answer country name out of the message if you don't
  want any hints at all.
