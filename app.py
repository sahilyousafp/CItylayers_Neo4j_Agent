import os
import json
from typing import Dict, Any, List, Tuple
from flask import Flask, render_template, request, jsonify, session
from datetime import timedelta
import pandas as pd

# Import agents
from agents import Neo4jAgent, VisualizationAgent, WebScraperAgent, OSMAgent, MeteostatAgent


app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")
app.permanent_session_lifetime = timedelta(hours=6)


# Simple in-memory store keyed by session sid
SESSIONS: Dict[str, Dict[str, Any]] = {}


def get_session_store() -> Dict[str, Any]:
    session.permanent = True
    sid = session.get("sid")
    if not sid:
        sid = os.urandom(16).hex()
        session["sid"] = sid
    if sid not in SESSIONS:
        SESSIONS[sid] = {
            "chat_history": [],  # list[tuple[str, str]]
            "last_context_records": [],  # list[dict]
            "osm_boundaries": [],  # list[dict] - OSM boundary features
            "neo4j_agent": Neo4jAgent(),
            "viz_agent": VisualizationAgent(),
            "scraper_agent": WebScraperAgent(),
            "osm_agent": OSMAgent(),
            "meteostat_agent": MeteostatAgent(),
        }
    return SESSIONS[sid]


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat_endpoint():
    store = get_session_store()
    neo4j_agent: Neo4jAgent = store["neo4j_agent"]
    osm_agent: OSMAgent = store["osm_agent"]
    meteostat_agent: MeteostatAgent = store["meteostat_agent"]
    scraper_agent: WebScraperAgent = store["scraper_agent"]
    chat_history: List[Tuple[str, str]] = store["chat_history"]

    payload = request.get_json(silent=True) or {}
    question = (payload.get("message") or "").strip()
    data_sources = payload.get("data_sources", ["citylayers"])
    
    if not question:
        return jsonify({"ok": False, "error": "Empty message"}), 400

    try:
        # Process based on selected data sources
        result = None
        context_records = []
        answer = ""
        
        # CityLayers (Neo4j) is the primary source
        if "citylayers" in data_sources:
            result = neo4j_agent.process(query=question, chat_history=chat_history)
            if result["ok"]:
                answer = result["answer"]
                context_records = result["context_records"]
        
        # Add OSM data if selected
        if "osm" in data_sources and context_records:
            # Get bounding box from existing records
            lats = [float(r.get("p", {}).get("latitude", 0)) for r in context_records if r.get("p", {}).get("latitude")]
            lons = [float(r.get("p", {}).get("longitude", 0)) for r in context_records if r.get("p", {}).get("longitude")]
            
            if lats and lons:
                bbox = (min(lats), min(lons), max(lats), max(lons))
                osm_result = osm_agent.process(bbox=bbox, feature_type="amenity")
                if osm_result.get("ok"):
                    answer += f"\n\n**OSM Data**: Found {osm_result.get('count', 0)} features in the area."
        
        # Add weather data if selected
        if "meteostat" in data_sources and context_records:
            # Get first location for weather data
            for record in context_records:
                p = record.get("p", {})
                lat = p.get("latitude")
                lon = p.get("longitude")
                if lat and lon:
                    weather_result = meteostat_agent.process(
                        latitude=float(lat),
                        longitude=float(lon),
                        interval="daily"
                    )
                    if weather_result.get("ok") and weather_result.get("data"):
                        latest = weather_result["data"][-1]
                        temp = latest.get("tavg", "N/A")
                        answer += f"\n\n**Weather Data**: Temperature: {temp}°C"
                    break
        
        # If no result yet, return error
        if not result or not result["ok"]:
            return jsonify({"ok": False, "error": "No data available from selected sources"}), 500
        
        answer = result["answer"]
        context_records = result["context_records"]
        
        # Store context for map visualization
        store["last_context_records"] = context_records
        
        # Use WebScraperAgent to analyze question and recommend visualization
        # (without actually scraping - just use the recommendation logic)
        if context_records:
            # Extract text from context for analysis
            context_text = " ".join([
                str(record.get("p", {}).get("location", "")) + " " +
                str(record.get("p", {}).get("category", "")) + " " +
                str(record.get("c", {}).get("description", ""))
                for record in context_records
            ])
            
            # Get visualization recommendation
            recommendation = scraper_agent._recommend_visualization(
                question=question,
                text=context_text,
                locations=[{"location": record.get("p", {}).get("location", "")} 
                          for record in context_records if record.get("p", {}).get("location")]
            )
            
            # Store the recommended visualization mode
            store["recommended_viz_mode"] = recommendation["primary"]["type"] if recommendation.get("primary") else "scatter"
            
            # Add recommendation to response
            viz_recommendation = {
                "type": recommendation["primary"]["type"],
                "reason": recommendation["primary"]["reason"],
                "confidence": recommendation["primary"]["confidence"]
            } if recommendation.get("primary") else None
        else:
            store["recommended_viz_mode"] = "scatter"
            viz_recommendation = None

        # Persist history
        chat_history.append((question, answer))
        store["chat_history"] = chat_history

        # Render markdown to HTML for clients that want formatted output
        answer_html = _render_markdown_to_html(answer)
        
        return jsonify({
            "ok": True,
            "answer": answer,
            "answer_html": answer_html,
            "visualization_recommendation": viz_recommendation
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/map-data", methods=["GET"])
def map_data():
    store = get_session_store()
    records: List[Dict[str, Any]] = store.get("last_context_records", [])

    # Normalize to the expected shape for client rendering
    df = pd.json_normalize(records) if records else pd.DataFrame()
    # Prefer 'p.latitude' etc if present; else try direct columns
    lat_col = "p.latitude" if "p.latitude" in df.columns else "latitude" if "latitude" in df.columns else None
    lon_col = "p.longitude" if "p.longitude" in df.columns else "longitude" if "longitude" in df.columns else None
    loc_col = "p.location" if "p.location" in df.columns else "location" if "location" in df.columns else None
    pid_col = "p.place_id" if "p.place_id" in df.columns else "place_id" if "place_id" in df.columns else None
    cat_col = "c.description" if "c.description" in df.columns else "category" if "category" in df.columns else "p.category" if "p.category" in df.columns else None

    if not lat_col or not lon_col:
        return jsonify({"ok": True, "features": []})

    features = []
    for _, row in df.iterrows():
        lat = row.get(lat_col)
        lon = row.get(lon_col)
        if pd.isna(lat) or pd.isna(lon):
            continue
        
        # Collect all available information
        feature = {
            "lat": float(lat),
            "lon": float(lon),
            "location": str(row.get(loc_col, "")) if loc_col else "",
        }
        
        # Add optional fields if available
        if pid_col and not pd.isna(row.get(pid_col)):
            feature["place_id"] = str(row.get(pid_col))
        if cat_col and not pd.isna(row.get(cat_col)):
            feature["category"] = str(row.get(cat_col))
            
        # Add any other fields from the row that might be useful
        for col in df.columns:
            if col not in [lat_col, lon_col, loc_col, pid_col, cat_col]:
                val = row.get(col)
                if not pd.isna(val) and str(val).strip():
                    # Clean up nested column names
                    clean_col = col.replace("p.", "").replace("c.", "")
                    if clean_col not in feature:
                        feature[clean_col] = str(val)
        
        features.append(feature)
    return jsonify({"ok": True, "features": features})


@app.route("/pydeck", methods=["GET"])
def pydeck_view():
    store = get_session_store()
    viz_agent: VisualizationAgent = store["viz_agent"]
    records = store.get("last_context_records", [])
    osm_boundaries = store.get("osm_boundaries", [])
    
    # Use recommended mode if no mode specified, otherwise use provided mode
    mode = request.args.get("mode")
    if not mode:
        mode = store.get("recommended_viz_mode", "scatter")
    mode = mode.lower()
    
    try:
        # If choropleth mode and OSM boundaries are available, merge them with records
        if mode == "choropleth" and osm_boundaries:
            # Convert records to include geometry from OSM boundaries
            enhanced_records = []
            for record in records:
                # Try to match record location with OSM boundary
                # For now, just add OSM boundaries as additional records
                enhanced_records.append(record)
            
            # Add OSM boundaries as choropleth-compatible records
            for boundary in osm_boundaries:
                enhanced_records.append({
                    "geojson": boundary,
                    "location": boundary.get("properties", {}).get("name", "Unknown"),
                    "value": 1  # Default value for coloring
                })
            
            html = viz_agent.process(records=enhanced_records, mode=mode)
        else:
            html = viz_agent.process(records=records, mode=mode)
        return html
    except Exception as e:
        return f"<div style='padding:12px;color:#b00020;'>Error rendering visualization: {str(e)}</div>", 500


@app.route("/scrape-and-visualize", methods=["POST"])
def scrape_and_visualize():
    """
    Scrape websites and recommend visualization based on question.
    """
    store = get_session_store()
    scraper_agent: WebScraperAgent = store["scraper_agent"]
    
    payload = request.get_json(silent=True) or {}
    urls = payload.get("urls", [])
    question = payload.get("question", "")
    
    if not urls:
        return jsonify({"ok": False, "error": "No URLs provided"}), 400
    
    try:
        result = scraper_agent.process(
            urls=urls,
            question=question,
            extract_locations=True
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/osm-data", methods=["POST"])
def osm_data():
    """
    Fetch OSM data for a location or bounding box.
    """
    store = get_session_store()
    osm_agent: OSMAgent = store["osm_agent"]
    
    payload = request.get_json(silent=True) or {}
    location_name = payload.get("location")
    bbox = payload.get("bbox")  # [min_lat, min_lon, max_lat, max_lon]
    center = payload.get("center")  # [lat, lon]
    radius = payload.get("radius", 5000)
    feature_type = payload.get("feature_type", "amenity")
    feature_value = payload.get("feature_value")
    tags = payload.get("tags")
    
    try:
        if location_name:
            # Query by location name
            result = osm_agent.query_by_location_name(
                location_name=location_name,
                feature_type=feature_type,
                feature_value=feature_value
            )
        elif bbox or center:
            # Query by bbox or center
            if bbox:
                bbox = tuple(bbox)
            if center:
                center = tuple(center)
            result = osm_agent.process(
                bbox=bbox,
                center=center,
                radius=radius,
                feature_type=feature_type,
                feature_value=feature_value,
                tags=tags
            )
        else:
            return jsonify({"ok": False, "error": "Must provide location, bbox, or center"}), 400
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/osm-layer", methods=["GET"])
def osm_layer():
    """
    Get OSM layer data for current map view.
    Uses last context records to determine area of interest.
    """
    store = get_session_store()
    osm_agent: OSMAgent = store["osm_agent"]
    records = store.get("last_context_records", [])
    
    # Extract feature type from query params
    feature_type = request.args.get("feature_type", "amenity")
    feature_value = request.args.get("feature_value")
    
    if not records:
        return jsonify({"ok": False, "error": "No location data available"}), 400
    
    try:
        # Calculate bounding box from records
        lats = []
        lons = []
        
        for record in records:
            p = record.get("p", {})
            lat = p.get("latitude")
            lon = p.get("longitude")
            if lat and lon:
                lats.append(float(lat))
                lons.append(float(lon))
        
        if not lats or not lons:
            return jsonify({"ok": False, "error": "No coordinates found in records"}), 400
        
        # Add padding to bbox (10%)
        lat_range = max(lats) - min(lats)
        lon_range = max(lons) - min(lons)
        padding_lat = lat_range * 0.1 if lat_range > 0 else 0.01
        padding_lon = lon_range * 0.1 if lon_range > 0 else 0.01
        
        bbox = (
            min(lats) - padding_lat,
            min(lons) - padding_lon,
            max(lats) + padding_lat,
            max(lons) + padding_lon
        )
        
        # Fetch OSM data
        result = osm_agent.process(
            bbox=bbox,
            feature_type=feature_type,
            feature_value=feature_value
        )
        
        # Store boundaries in session if this is a boundary query
        if feature_type == "boundary" and result.get("ok"):
            store["osm_boundaries"] = result.get("features", [])
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/weather-data", methods=["POST"])
def weather_data():
    """
    Fetch weather data for a location.
    """
    store = get_session_store()
    meteostat_agent: MeteostatAgent = store["meteostat_agent"]
    
    payload = request.get_json(silent=True) or {}
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    interval = payload.get("interval", "daily")
    
    if latitude is None or longitude is None:
        return jsonify({"ok": False, "error": "Latitude and longitude required"}), 400
    
    try:
        result = meteostat_agent.process(
            latitude=float(latitude),
            longitude=float(longitude),
            start_date=start_date,
            end_date=end_date,
            interval=interval
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/climate-normals", methods=["POST"])
def climate_normals():
    """
    Get climate normals for a location.
    """
    store = get_session_store()
    meteostat_agent: MeteostatAgent = store["meteostat_agent"]
    
    payload = request.get_json(silent=True) or {}
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    
    if latitude is None or longitude is None:
        return jsonify({"ok": False, "error": "Latitude and longitude required"}), 400
    
    try:
        result = meteostat_agent.get_climate_normals(
            latitude=float(latitude),
            longitude=float(longitude)
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# -----------------------------
# Markdown formatting helper
# -----------------------------
def _render_markdown_to_html(text: str) -> str:
    """
    Best-effort conversion of Markdown to HTML.
    Tries markdown2 first, then markdown (python-markdown). Falls back to plain text with <pre>.
    """
    content = (text or "").strip()
    if not content:
        return ""
    # Try markdown2
    try:
        import markdown2  # type: ignore
        html = markdown2.markdown(content, extras=["fenced-code-blocks", "break-on-newline", "tables"])
        # Wrap tables in a responsive container
        html = html.replace('<table>', '<div class="table-wrapper"><table>').replace('</table>', '</table></div>')
        return html
    except Exception:
        pass
    # Try python-markdown
    try:
        import markdown  # type: ignore
        html = markdown.markdown(
            content,
            extensions=["extra", "sane_lists", "nl2br", "fenced_code", "tables"],
            output_format="html5",
        )
        # Wrap tables in a responsive container
        html = html.replace('<table>', '<div class="table-wrapper"><table>').replace('</table>', '</table></div>')
        return html
    except Exception:
        # Fallback: preserve formatting minimally
        escaped = (
            content.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return f"<pre>{escaped}</pre>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)



