import math
from typing import List, Dict, Any, Optional
import pandas as pd
import pydeck as pdk


class PydeckVisualizer:
    def __init__(self) -> None:
        # A small categorical palette (can expand as needed)
        self.palette = [
            [30, 144, 255, 180],   # DodgerBlue
            [255, 99, 132, 180],   # Pinkish Red
            [75, 192, 192, 180],   # Teal
            [255, 206, 86, 180],   # Yellow
            [153, 102, 255, 180],  # Purple
            [255, 159, 64, 180],   # Orange
            [34, 139, 34, 180],    # ForestGreen
            [220, 20, 60, 180],    # Crimson
        ]

    def _to_dataframe(self, records: List[Dict[str, Any]]) -> pd.DataFrame:
        df = pd.json_normalize(records) if records else pd.DataFrame()
        # Normalize expected columns
        lat_col = "p.latitude" if "p.latitude" in df.columns else "latitude" if "latitude" in df.columns else None
        lon_col = "p.longitude" if "p.longitude" in df.columns else "longitude" if "longitude" in df.columns else None
        loc_col = "p.location" if "p.location" in df.columns else "location" if "location" in df.columns else None
        cat_col = None
        # Try common category fields if present
        for candidate in ["c.description", "category", "type", "p.category"]:
            if candidate in df.columns:
                cat_col = candidate
                break
        # Build normalized frame
        out = pd.DataFrame()
        if lat_col and lon_col:
            out["latitude"] = df[lat_col]
            out["longitude"] = df[lon_col]
        else:
            out["latitude"] = pd.Series(dtype=float)
            out["longitude"] = pd.Series(dtype=float)
        out["location"] = df[loc_col] if loc_col in df.columns else ""
        if cat_col:
            out["category"] = df[cat_col].fillna("").astype(str)
        else:
            out["category"] = ""
        # Drop rows without coordinates
        out = out.dropna(subset=["latitude", "longitude"])
        return out

    def _get_category_colors(self, categories: List[str]) -> Dict[str, List[int]]:
        unique = list(dict.fromkeys([c or "" for c in categories]))
        mapping: Dict[str, List[int]] = {}
        for idx, cat in enumerate(unique):
            mapping[cat] = self.palette[idx % len(self.palette)]
        return mapping

    def _center(self, df: pd.DataFrame) -> Dict[str, float]:
        if df.empty:
            return {"lat": 0.0, "lon": 0.0}
        return {
            "lat": float(df["latitude"].mean()),
            "lon": float(df["longitude"].mean()),
        }

    def _extract_geojson_features(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a GeoJSON FeatureCollection from assorted record shapes.
        Accepted inputs per record (first found wins):
          - {"geojson": <Feature or Geometry>}
          - {"geometry": <Geometry>}
          - {"g": {"type": "...", "coordinates": [...]}}  # common alias
          - {"p.geometry": <Geometry>} from flattened records
        Properties included: location, category if present.
        """
        features: List[Dict[str, Any]] = []
        for rec in records or []:
            geom = None
            props: Dict[str, Any] = {}
            # Find geometry candidates
            if isinstance(rec.get("geojson"), dict):
                gj = rec["geojson"]
                if gj.get("type") in ("Feature", "FeatureCollection"):
                    # If Feature: use as-is; if FC, expand
                    if gj["type"] == "Feature":
                        geom = gj.get("geometry")
                        props.update(gj.get("properties") or {})
                    else:
                        for f in gj.get("features") or []:
                            if isinstance(f, dict) and f.get("type") == "Feature":
                                fprops = dict(f.get("properties") or {})
                                if "location" in rec:
                                    fprops.setdefault("location", rec.get("location"))
                                if "category" in rec:
                                    fprops.setdefault("category", rec.get("category"))
                                features.append({"type": "Feature", "geometry": f.get("geometry"), "properties": fprops})
                        continue
                else:
                    geom = gj
            if geom is None and isinstance(rec.get("geometry"), dict):
                geom = rec["geometry"]
            if geom is None and isinstance(rec.get("g"), dict):
                g = rec["g"]
                if isinstance(g.get("geometry"), dict):
                    geom = g.get("geometry")
                elif g.get("type") and g.get("coordinates") is not None:
                    geom = g
            if geom is None and isinstance(rec.get("p.geometry"), dict):
                geom = rec["p.geometry"]

            if geom is None:
                continue

            # Basic props
            if "location" in rec:
                props["location"] = rec.get("location")
            if "p.location" in rec:
                props["location"] = rec.get("p.location")
            if "category" in rec:
                props["category"] = rec.get("category")

            features.append({"type": "Feature", "geometry": geom, "properties": props})

        return {"type": "FeatureCollection", "features": features}

    def render_html(
        self,
        records: List[Dict[str, Any]],
        mode: str = "scatter",
        radius: int = 5000,
        elevation_scale: int = 100,
    ) -> str:
        """
        mode options:
        - scatter: colored by category, fixed radius
        - heatmap: density heatmap (ignores category)
        - hexagon: 3D hex layer with elevation
        - choropleth: GeoJSON polygons filled by property
        - arc: curved lines showing connections between points
        """
        df = self._to_dataframe(records)
        center = self._center(df)
        view_state = pdk.ViewState(
            longitude=center["lon"],
            latitude=center["lat"],
            zoom=6 if not df.empty else 2,
            pitch=0,
        )

        layers = []

        if mode == "scatter":
            color_map = self._get_category_colors(df["category"].tolist())
            # Map color for each row
            df = df.copy()
            df["_color"] = df["category"].map(lambda c: color_map.get(c or "", [30, 144, 255, 180]))
            layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    id="scatter-layer",
                    data=df,
                    get_position="[longitude, latitude]",
                    get_fill_color="_color",
                    radius_units="pixels",
                    radius_min_pixels=3,
                    radius_max_pixels=12,
                    get_radius=6,
                    pickable=True,
                    auto_highlight=True,
                )
            )

        elif mode == "heatmap":
            layers.append(
                pdk.Layer(
                    "HeatmapLayer",
                    id="heatmap-layer",
                    data=df,
                    get_position="[longitude, latitude]",
                    radius_pixels=30,
                    aggregation="MEAN",
                )
            )

        elif mode == "hexagon":
            layers.append(
                pdk.Layer(
                    "HexagonLayer",
                    id="hex-layer",
                    data=df,
                    get_position="[longitude, latitude]",
                    radius=radius,
                    elevation_scale=elevation_scale,
                    extruded=True,
                    pickable=True,
                )
            )

        elif mode == "choropleth":
            # Expect polygons in records; build FeatureCollection
            feature_collection = self._extract_geojson_features(records)
            if not feature_collection.get("features"):
                # Fallback informative layer if no polygons available
                layers.append(
                    pdk.Layer(
                        "TextLayer",
                        id="choropleth-empty",
                        data=[{"position": [center["lon"], center["lat"]], "text": "No polygon data available"}],
                        get_position="position",
                        get_text="text",
                        get_size=16,
                        get_color=[180, 0, 32],
                    )
                )
            else:
                layers.append(
                    pdk.Layer(
                        "GeoJsonLayer",
                        id="choropleth-layer",
                        data=feature_collection,
                        stroked=True,
                        filled=True,
                        extruded=False,
                        pickable=True,
                        get_fill_color="[properties.value ? Math.max(0, 255 - properties.value) : 30, 144, 255, 160]",
                        get_line_color=[40, 40, 40, 200],
                        line_width_min_pixels=1,
                    )
                )

        elif mode == "arc":
            # Arc layer for showing connections between points
            # Try to detect source/destination patterns in data
            arc_data = []
            
            # Check if data has explicit source/destination columns
            if "source_lat" in df.columns and "source_lon" in df.columns and \
               "dest_lat" in df.columns and "dest_lon" in df.columns:
                # Explicit arc data
                for _, row in df.iterrows():
                    arc_data.append({
                        "source": [float(row["source_lon"]), float(row["source_lat"])],
                        "target": [float(row["dest_lon"]), float(row["dest_lat"])],
                        "color": [30, 144, 255, 180]
                    })
            else:
                # Create arcs between consecutive points
                if len(df) > 1:
                    for i in range(len(df) - 1):
                        arc_data.append({
                            "source": [float(df.iloc[i]["longitude"]), float(df.iloc[i]["latitude"])],
                            "target": [float(df.iloc[i + 1]["longitude"]), float(df.iloc[i + 1]["latitude"])],
                            "color": [30, 144, 255, 180]
                        })
            
            if arc_data:
                layers.append(
                    pdk.Layer(
                        "ArcLayer",
                        id="arc-layer",
                        data=arc_data,
                        get_source_position="source",
                        get_target_position="target",
                        get_source_color="color",
                        get_target_color="color",
                        get_width=3,
                        pickable=True,
                        auto_highlight=True,
                    )
                )
                # Set pitch for better 3D view of arcs
                view_state.pitch = 30
            else:
                # No arc data, fallback to scatter
                layers.append(
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=df,
                        get_position="[longitude, latitude]",
                        get_fill_color="[30, 144, 255, 180]",
                        get_radius=radius,
                        pickable=True,
                        auto_highlight=True,
                    )
                )

        else:
            # Default to scatter if unknown
            layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    data=df,
                    get_position="[longitude, latitude]",
                    get_fill_color="[30, 144, 255, 180]",
                    get_radius=radius,
                    pickable=True,
                    auto_highlight=True,
                )
            )

        tooltip = {"text": "{location}"}
        deck = pdk.Deck(layers=layers, initial_view_state=view_state, tooltip=tooltip)
        # Return embeddable HTML
        html = deck.to_html(as_string=True, notebook_display=False)
        # Inject dynamic zoom scaling for Hexagon and tune Heatmap/Scatter if needed
        script = f"""
<script>
(function(){{
  function withDeck(glcb){{
    var tries = 0;
    var iv = setInterval(function(){{
      tries++;
      if (window.deckgl && window.deck) {{
        clearInterval(iv);
        glcb(window.deckgl);
      }}
      if (tries > 100) {{ clearInterval(iv); }}
    }}, 100);
  }}
  withDeck(function(deckgl){{
    var BASE_HEX_RADIUS = {int(radius)}; // meters baseline (from Python)
    function updateLayersByZoom(viewState){{
      var zoom = (viewState && viewState.zoom) || 6;
      var scale = Math.pow(2, 8 - zoom);
      var hexRadius = Math.max(2000, Math.round(BASE_HEX_RADIUS * scale));
      var layers = (deckgl.props.layers || []).map(function(layer){{
        if (!layer || !layer.id) return layer;
        if (layer.id === 'hex-layer') {{
          return new deck.HexagonLayer(Object.assign({{}}, layer.props, {{radius: hexRadius}}));
        }}
        if (layer.id === 'heatmap-layer') {{
          var heatRadius = Math.max(10, Math.round(30 * scale));
          return new deck.HeatmapLayer(Object.assign({{}}, layer.props, {{radiusPixels: heatRadius}}));
        }}
        if (layer.id === 'scatter-layer') {{
          // Keep scatter sized in pixels with min/max bounds; no change needed
          return layer;
        }}
        return layer;
      }});
      deckgl.setProps({{layers: layers}});
    }}
    deckgl.setProps({{onViewStateChange: function(ev){{ updateLayersByZoom(ev.viewState); }}}});
    // Initial adjust
    updateLayersByZoom(deckgl.viewState || {{}});
  }});
}})();
</script>
"""
        # Insert before closing body
        if "</body>" in html:
            html = html.replace("</body>", script + "\n</body>")
        else:
            html = html + script
        return html


