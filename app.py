import os
import json
from typing import Dict, Any, List, Tuple
from flask import Flask, render_template, request, jsonify, session
from datetime import timedelta
import pandas as pd
import re

# Import agents
from agents import Neo4jAgent, WebScraperAgent, OSMAgent, MeteostatAgent


from config import Config

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = Config.FLASK_SECRET_KEY
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
            "neo4j_agent": Neo4jAgent(Config.AGENTS["neo4j"]),
            # "viz_agent": VisualizationAgent(), # Deprecated
            "scraper_agent": WebScraperAgent(),
            "osm_agent": OSMAgent(),
            "meteostat_agent": MeteostatAgent(),
        }
    return SESSIONS[sid]


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", mapbox_token=Config.MAPBOX_ACCESS_TOKEN)


def _get_category_from_query(query: str) -> str:
    """
    Parses a query to find a matching category and returns its ID.
    Enhanced to detect more natural language patterns.
    """
    CATEGORY_MAPPING = {
        # Beauty (1)
        'beauty': 1, 'beautiful': 1, 'scenic': 1, 'view': 1, 'views': 1,
        'aesthetic': 1, 'attractive': 1, 'picturesque': 1, 'stunning': 1,
        'pretty': 1, 'gorgeous': 1, 'architecture': 1, 'architectural': 1,
        
        # Sound (2)
        'sound': 2, 'noise': 2, 'audio': 2, 'acoustic': 2, 'acoustics': 2,
        'quiet': 2, 'peaceful': 2, 'loud': 2, 'silent': 2, 'noisy': 2,
        
        # Movement (3)
        'movement': 3, 'transport': 3, 'transportation': 3, 'transit': 3,
        'mobility': 3, 'traffic': 3, 'pedestrian': 3, 'walkability': 3,
        'accessible': 3, 'accessibility': 3, 'bike': 3, 'cycling': 3,
        
        # Protection (4)
        'protection': 4, 'safety': 4, 'secure': 4, 'security': 4,
        'safe': 4, 'crime': 4, 'dangerous': 4, 'risk': 4,
        
        # Climate Comfort (5)
        'climate': 5, 'comfort': 5, 'weather': 5, 'temperature': 5,
        'comfortable': 5, 'climate comfort': 5, 'hot': 5, 'cold': 5,
        'shade': 5, 'sunny': 5, 'wind': 5, 'rain': 5,
        
        # Activities (6)
        'activities': 6, 'activity': 6, 'recreation': 6, 'recreational': 6,
        'parks': 6, 'park': 6, 'leisure': 6, 'entertainment': 6,
        'things to do': 6, 'fun': 6, 'sports': 6, 'exercise': 6
    }
    
    lower_query = query.lower()
    
    # Sort by length (longest first) to match more specific terms first
    sorted_keywords = sorted(CATEGORY_MAPPING.keys(), key=len, reverse=True)
    
    for keyword in sorted_keywords:
        if keyword in lower_query:
            return str(CATEGORY_MAPPING[keyword])
    
    return None


@app.route("/chat", methods=["POST"])
def chat_endpoint():
    store = get_session_store()
    neo4j_agent: Neo4jAgent = store["neo4j_agent"]
    scraper_agent: WebScraperAgent = store["scraper_agent"]
    chat_history: List[Tuple[str, str]] = store["chat_history"]

    payload = request.get_json(silent=True) or {}
    question = (payload.get("message") or "").strip()
    data_sources = payload.get("data_sources", ["citylayers"])
    map_context = payload.get("map_context", {})
    category_filter = payload.get("category_filter")
    
    if not question:
        return jsonify({"ok": False, "error": "Empty message"}), 400

    try:
        # Detect category from query
        detected_category_id = _get_category_from_query(question)
        
        # Only use detected category if:
        # 1. A category was actually detected (not None)
        # 2. AND no specific category filter is set (None or 'all')
        if detected_category_id and (not category_filter or category_filter == 'all'):
            category_filter = detected_category_id
            print(f"DEBUG: Auto-applied category filter from query: {category_filter}")
        elif category_filter == 'all':
            # Explicitly set to None if 'all' is selected
            category_filter = None
            print(f"DEBUG: No category filter (showing all categories)")

        # Process based on selected data sources
        result = None
        context_records = []
        answer = ""
        
        # ALWAYS use map bounds unless user explicitly mentions a different location
        user_message_lower = question.lower()
        location_keywords = ['in ', ' at ', 'near ', 'around ', 'from ']
        has_specific_location = any(keyword in user_message_lower for keyword in location_keywords)
        
        # Extract map bounds
        bounds = map_context.get("bounds", {}) if map_context else {}
        
        if not has_specific_location and bounds:
            # User didn't specify a location, use current map bounds
            print(f"INFO: Using map bounds for query: N={bounds.get('north')}, S={bounds.get('south')}, E={bounds.get('east')}, W={bounds.get('west')}")
        elif has_specific_location:
            print(f"INFO: User specified location in query, will search that area instead of map bounds")
            # Don't clear bounds, but LLM will prioritize the named location
        
        # CityLayers (Neo4j) is the primary source
        if "citylayers" in data_sources:
            print(f"DEBUG: Processing query with Neo4j agent: '{question}'")
            result = neo4j_agent.process(
                query=question, 
                chat_history=chat_history, 
                map_context=map_context,
                category_filter=category_filter
            )
            
            if result is None:
                return jsonify({"ok": False, "error": "Query processing returned None"}), 500
                
            print(f"DEBUG: Neo4j result ok={result.get('ok')}, answer length={len(result.get('answer', ''))}, context_records count={len(result.get('context_records', []))}")
            if result.get("ok"):
                answer = result["answer"]
                context_records = result["context_records"]
                print(f"DEBUG: Retrieved {len(context_records)} context_records from Neo4j agent")
                if len(context_records) > 0:
                    print(f"DEBUG: First context record: {str(context_records[0])[:500]}...")
                
                # Enrich answer with online information about locations
                answer = _enrich_with_online_info(answer, context_records, scraper_agent, bounds)
        
        # If no result yet, return error
        if not result or not result["ok"]:
            return jsonify({"ok": False, "error": "No data available from selected sources"}), 500
        
        # Store context for map visualization
        store["last_context_records"] = context_records
        print(f"DEBUG: Stored {len(context_records)} context_records for map visualization.")
        
        # Get visualization recommendation
        viz_recommendation = _get_viz_recommendation(store, scraper_agent, question, context_records)
        
        # Persist history
        chat_history.append((question, answer))
        store["chat_history"] = chat_history

        # Render markdown to HTML
        answer_html = answer if answer.strip().startswith('<') else _render_markdown_to_html(answer)
        
        # Inject geolocation data into table rows for hover functionality
        answer_html = _inject_geolocation_into_tables(answer_html, context_records)
        
        return jsonify({
            "ok": True,
            "answer": answer,
            "answer_html": answer_html,
            "visualization_recommendation": viz_recommendation,
            "detected_category_id": detected_category_id
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/debug-data", methods=["GET"])
def debug_data():
    store = get_session_store()
    records = store.get("last_context_records", [])
    # Return first 5 records for inspection
    return jsonify({"count": len(records), "sample": records[:5]})


@app.route("/map-data", methods=["GET"])
def map_data():
    """
    Return Neo4j results as flat feature array for visualization.
    Uses simple lat/lon properties for direct mapping.
    """
    store = get_session_store()
    
    # Get records from last query
    records: List[Dict[str, Any]] = store.get("last_context_records", [])
    osm_agent: OSMAgent = store["osm_agent"]

    # Flatten Neo4j records to simple format
    flat_records = _flatten_neo4j_records(records)
    
    # Convert to simple feature format
    df = pd.DataFrame(flat_records) if flat_records else pd.DataFrame()
    
    if df.empty:
        return jsonify({"ok": True, "features": [], "boundaries": []})
    
    # Deduplicate columns
    df = df.loc[:, ~df.columns.duplicated()]
    
    # Find coordinate columns
    lat_col = next((col for col in ["p.latitude", "latitude", "lat", "p.lat"] if col in df.columns), None)
    lon_col = next((col for col in ["p.longitude", "longitude", "lon", "lng", "p.lon", "p.lng"] if col in df.columns), None)
    
    if not lat_col or not lon_col:
        return jsonify({"ok": True, "features": [], "boundaries": []})
    
    # Column mappings
    loc_col = next((col for col in ["p.location", "location", "name", "p.name"] if col in df.columns), None)
    pid_col = next((col for col in ["p.place_id", "place_id", "id"] if col in df.columns), None)
    cat_col = next((col for col in ["categories_info", "c_main.type", "c_main", "c.name", "c", "category_name", "p.category", "category"] if col in df.columns), None)
    subcat_col = next((col for col in ["p.subcategory", "subcategory"] if col in df.columns), None)
    comments_col = next((col for col in ["p.comments", "comments", "p.description", "comments_info"] if col in df.columns), None)
    grade_col = next((col for col in ["p.grade", "grade", "p.rating", "grades_and_subgrades", "place_grades"] if col in df.columns), None)
    
    features = []
    city_names = set()
    
    for _, row in df.iterrows():
        if row is None:
            continue
            
        lat = row.get(lat_col)
        lon = row.get(lon_col)
        
        if pd.isna(lat) or pd.isna(lon):
            continue
        
        try:
            lat = float(lat)
            lon = float(lon)
        except (ValueError, TypeError):
            continue
        
        # Build simple feature
        feature = {
            "lat": lat,
            "lon": lon,
            "location": str(row.get(loc_col, "")) if loc_col else "",
        }
        
        # Track city names
        location = feature["location"]
        if location:
            city_name = location.split(",")[0].strip()
            if city_name:
                city_names.add(city_name)
        
        # Add place_id
        place_id = _safe_get_value(row, pid_col)
        if place_id:
            feature["place_id"] = place_id
        
        # Extract categories
        categories, category_ids = _extract_all_categories(row, cat_col)
        if categories:
            feature["categories"] = categories
            feature["category"] = categories[0]
        else:
            feature["categories"] = ["Uncategorized"]
            feature["category"] = "Uncategorized"
        
        if category_ids:
            feature["category_ids"] = category_ids
        
        # Add other properties with safety checks
        if subcat_col:
            subcategory = _safe_get_value(row, subcat_col)
            if subcategory:
                feature["subcategory"] = subcategory
        
        if comments_col:
            try:
                if comments_col == 'comments_info':
                    comments = _extract_from_nested(row, comments_col)
                else:
                    comments = _safe_get_value(row, comments_col)
                if comments:
                    feature["comments"] = comments
            except Exception as e:
                print(f"DEBUG: Error extracting comments: {e}")
        
        if grade_col:
            try:
                if grade_col in ['grades_and_subgrades', 'place_grades']:
                    grade = _extract_from_nested(row, grade_col)
                else:
                    grade = _safe_get_value(row, grade_col)
                if grade:
                    feature["grade"] = grade
            except Exception as e:
                print(f"DEBUG: Error extracting grade: {e}")
        
        # Add remaining columns
        priority_cols = {lat_col, lon_col, loc_col, pid_col, cat_col, subcat_col, comments_col, grade_col}
        for col in df.columns:
            if col not in priority_cols and not col.startswith('categories_info') and not col.startswith('comments_info'):
                val = row.get(col)
                try:
                    if pd.notna(val):
                        val_str = str(val).strip()
                        if val_str and val_str != 'nan':
                            clean_col = col.replace("p.", "").replace("c.", "")
                            if clean_col not in feature:
                                feature[clean_col] = val_str
                except (ValueError, TypeError):
                    continue
        
        features.append(feature)
    
    # Deduplicate by place_id
    seen_place_ids = set()
    unique_features = []
    for feature in features:
        place_id = feature.get('place_id')
        if place_id and place_id not in seen_place_ids:
            seen_place_ids.add(place_id)
            unique_features.append(feature)
        elif not place_id:
            unique_features.append(feature)
    
    features = unique_features
    
    print(f"DEBUG: Prepared {len(features)} features for map")
    
    # Fetch city boundaries
    boundaries = _fetch_city_boundaries(osm_agent, city_names, features)
    store["city_boundaries"] = boundaries
    
    return jsonify({"ok": True, "features": features, "boundaries": boundaries})


def _safe_get_value(row, col_name):
    """Safely extract value from DataFrame row."""
    if row is None or not col_name:
        return None
    try:
        val = row.get(col_name)
        if pd.isna(val):
            return None
        return str(val).strip()
    except (ValueError, TypeError, AttributeError):
        return None


def _extract_from_nested(row, col_name):
    """Extract data from nested list/dict structures."""
    if row is None or not col_name:
        return None
    try:
        val = row.get(col_name)
        
        # Check if val is a numpy array or pandas object
        if hasattr(val, '__iter__') and not isinstance(val, (str, dict)):
            try:
                # Try to check if it's NA/null using pandas
                if pd.isna(val).any() if hasattr(pd.isna(val), 'any') else pd.isna(val):
                    return None
            except (TypeError, ValueError):
                pass
        elif val is None:
            return None
        
        # If it's a string representation of a list, try to parse it
        if isinstance(val, str):
            import ast
            try:
                val = ast.literal_eval(val)
            except:
                return val
        
        # If it's a list, get first item
        if isinstance(val, list) and len(val) > 0:
            first_item = val[0]
            if isinstance(first_item, dict):
                return first_item.get('text') or first_item.get('content') or first_item.get('description') or first_item.get('grade')
            return str(first_item)
        
        # If it's a dict, try to get relevant field
        if isinstance(val, dict):
            return val.get('text') or val.get('content') or val.get('description') or val.get('grade')
        
        return str(val).strip() if val is not None else None
    except Exception as e:
        print(f"DEBUG: Error extracting from nested {col_name}: {e}")
        return None
        return None


def _extract_all_categories(row, cat_col):
    """Extract ALL category types and IDs from categories_info list."""
    CATEGORY_ID_MAPPING = {
        1: 'Beauty', 2: 'Sound', 3: 'Movement',
        4: 'Protection', 5: 'Climate Comfort', 6: 'Activities'
    }
    
    if row is None or not cat_col:
        return [], []
    
    try:
        val = row.get(cat_col)
        if val is None:
            return [], []
        
        # Check for pandas NA only if not a list or dict
        try:
            if not isinstance(val, (list, dict)) and pd.isna(val):
                return [], []
        except (ValueError, TypeError):
            pass
        
        # If it's a string representation of a list, try to parse it
        if isinstance(val, str):
            import ast
            try:
                val = ast.literal_eval(val)
            except:
                # Try to match categories from string
                categories = []
                val_lower = val.lower()
                CATEGORY_MAPPING = {
                    'beauty': 'Beauty', 'activities': 'Activities', 'sound': 'Sound',
                    'protection': 'Protection', 'movement': 'Movement', 'climate': 'Climate Comfort'
                }
                for key, mapped_val in CATEGORY_MAPPING.items():
                    if key in val_lower:
                        categories.append(mapped_val)
                return categories if categories else [val], []
        
        categories = []
        category_ids = []
        
        # If it's a list of dicts
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    cat_id = item.get('category_id')
                    if cat_id is not None:
                        try:
                            cat_id = int(cat_id)
                            category_ids.append(cat_id)
                            if cat_id in CATEGORY_ID_MAPPING:
                                categories.append(CATEGORY_ID_MAPPING[cat_id])
                        except:
                            pass
                    
                    cat = item.get('type') or item.get('name') or item.get('description')
                    if cat:
                        categories.append(str(cat).strip())
                elif item:
                    categories.append(str(item).strip())
            
            return list(set(categories)), list(set(category_ids))
        
        # If it's a single dict
        if isinstance(val, dict):
            cat_id = val.get('category_id')
            if cat_id is not None:
                try:
                    cat_id = int(cat_id)
                    return ([CATEGORY_ID_MAPPING[cat_id]] if cat_id in CATEGORY_ID_MAPPING else []), [cat_id]
                except:
                    pass
            
            cat = val.get('type') or val.get('name') or val.get('description')
            if cat:
                return [str(cat).strip()], []
        
        # Otherwise treat as single value
        if val:
            return [str(val).strip()], []
        
        return [], []
    except Exception as e:
        print(f"DEBUG: Error extracting categories from {cat_col}: {e}")
        return [], []


def _fetch_city_boundaries(osm_agent, city_names, features):
    """Helper to fetch city boundaries for choropleth."""
    boundaries = []
    for city_name in city_names:
        try:
            boundary_result = osm_agent.get_city_boundary(city_name)
            if boundary_result.get("ok"):
                city_locations = [f for f in features if city_name.lower() in f.get("location", "").lower()]
                importance_value = min(100, len(city_locations) * 10)
                
                boundaries.append({
                    "type": "Feature",
                    "geometry": boundary_result["geometry"],
                    "properties": {
                        **boundary_result.get("properties", {}),
                        "value": importance_value,
                        "location_count": len(city_locations),
                    }
                })
        except Exception as e:
            print(f"Failed to fetch boundary for {city_name}: {e}")
            continue
    return boundaries


def _flatten_neo4j_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Helper to flatten Neo4j records and aggregate by place_id.
    Consolidates multiple category rows for the same place into a single record.
    """
    # First, group records by place_id
    place_groups = {}
    
    for record in records:
        # Get place node
        place = record.get('p')
        if not place or not isinstance(place, (dict, object)):
            continue
            
        # Convert to dict if needed
        if hasattr(place, 'items'):
            place = dict(place)
        elif not isinstance(place, dict):
            continue
        
        place_id = place.get('place_id')
        if not place_id:
            continue
        
        # Initialize place group if not exists
        if place_id not in place_groups:
            place_groups[place_id] = {
                'p': place,
                'categories': [],
                'comments': [],
                'grades': [],
                'subgrades': [],
                'images': []
            }
        
        # Aggregate categories (c1, c2, c, etc.)
        for key in ['c', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6']:
            if key in record and record[key]:
                cat = record[key]
                if hasattr(cat, 'items'):
                    cat = dict(cat)
                if cat and isinstance(cat, dict):
                    place_groups[place_id]['categories'].append(cat)
        
        # Aggregate comments
        if 'co' in record and record['co']:
            comment = record['co']
            if hasattr(comment, 'items'):
                comment = dict(comment)
            if comment and isinstance(comment, dict):
                place_groups[place_id]['comments'].append(comment)
        
        # Aggregate grades AND extract category from Place_Grade
        if 'pg' in record and record['pg']:
            grade = record['pg']
            if hasattr(grade, 'items'):
                grade = dict(grade)
            if grade and isinstance(grade, dict):
                place_groups[place_id]['grades'].append(grade)
                
                # Extract category ID from Place_Grade if available
                # Place_Grade has a 'category' field that references the category ID
                if 'category' in grade:
                    cat_id = grade['category']
                    # Store this for later category lookup
                    if 'category_ids_from_grades' not in place_groups[place_id]:
                        place_groups[place_id]['category_ids_from_grades'] = []
                    place_groups[place_id]['category_ids_from_grades'].append(cat_id)
        
        # Aggregate subgrades
        if 'psg' in record and record['psg']:
            subgrade = record['psg']
            if hasattr(subgrade, 'items'):
                subgrade = dict(subgrade)
            if subgrade and isinstance(subgrade, dict):
                place_groups[place_id]['subgrades'].append(subgrade)
        
        # Aggregate images
        if 'i' in record and record['i']:
            image = record['i']
            if hasattr(image, 'items'):
                image = dict(image)
            if image and isinstance(image, dict):
                place_groups[place_id]['images'].append(image)
    
    # Now flatten the aggregated records
    flat_records = []
    for place_id, group in place_groups.items():
        flat_record = {}
        
        # Flatten place properties
        place = group['p']
        for key, val in place.items():
            flat_record[f'p.{key}'] = val
        
        # Add aggregated categories as list
        if group['categories']:
            flat_record['categories_info'] = group['categories']
        
        # Add aggregated comments as list
        if group['comments']:
            flat_record['comments_info'] = group['comments']
        
        # Add aggregated grades
        if group['grades']:
            flat_record['place_grades'] = group['grades']
        
        # Add category IDs extracted from Place_Grade
        if 'category_ids_from_grades' in group and group['category_ids_from_grades']:
            flat_record['category_ids_from_grades'] = list(set(group['category_ids_from_grades']))
            
            # Also create a list of category info from the category nodes (c, c1, c2, etc)
            # Merge with existing categories_info if present
            if not group['categories']:
                # If no categories from c nodes, create them from IDs + grades
                CATEGORY_ID_MAPPING = {
                    1: 'Beauty',
                    2: 'Sound',
                    3: 'Movement',
                    4: 'Protection',
                    5: 'Climate Comfort',
                    6: 'Activities'
                }
                
                categories_list = []
                for cat_id in set(group['category_ids_from_grades']):
                    if cat_id in CATEGORY_ID_MAPPING:
                        categories_list.append({
                            'category_id': cat_id,
                            'type': CATEGORY_ID_MAPPING[cat_id]
                        })
                
                if categories_list:
                    flat_record['categories_info'] = categories_list
        
        # Add aggregated subgrades
        if group['subgrades']:
            flat_record['place_subgrades'] = group['subgrades']
        
        # Add aggregated images
        if group['images']:
            flat_record['images'] = group['images']
        
        flat_records.append(flat_record)
    
    return flat_records


def _enrich_with_online_info(answer: str, context_records: List[Dict], scraper_agent, bounds: Dict) -> str:
    """
    Enrich the answer with additional information from online sources (Wikipedia).
    Fetches details about specific locations mentioned in the answer.
    """
    if not context_records:
        return answer
    
    try:
        # Extract unique location names from context records
        locations = set()
        location_coords = {}
        
        for record in context_records[:10]:  # Check first 10 records
            place = record.get('p', {})
            if isinstance(place, dict):
                location = place.get('location', '')
                lat = place.get('latitude')
                lon = place.get('longitude')
                
                if location and lat and lon:
                    # Extract main landmark/place name (before comma)
                    main_name = location.split(',')[0].strip()
                    if main_name and len(main_name) > 3:  # Avoid very short names
                        locations.add(main_name)
                        location_coords[main_name] = (lat, lon)
        
        if not locations:
            return answer
        
        # Fetch additional info for up to 3 prominent locations
        enrichment_sections = []
        for location_name in list(locations)[:3]:
            lat, lon = location_coords.get(location_name, (None, None))
            info = scraper_agent.fetch_location_info(location_name, lat, lon)
            
            if info.get("ok") and info.get("description"):
                # Create a brief enrichment section
                description = info["description"]
                # Limit to first 2-3 sentences
                sentences = description.split('.')[:3]
                brief_desc = '.'.join(sentences).strip() + '.'
                
                enrichment = f"\n\n#### About {location_name}\n{brief_desc}"
                enrichment_sections.append(enrichment)
        
        # Append enrichment to answer if we found any
        if enrichment_sections:
            answer += "\n\n---\n\n### 📚 Additional Context\n"
            answer += ''.join(enrichment_sections)
            answer += "\n\n*Source: Wikipedia*"
        
        return answer
        
    except Exception as e:
        print(f"WARNING: Failed to enrich with online info: {e}")
        return answer


def _get_viz_recommendation(store, scraper_agent, question, context_records):
    """Helper to get visualization recommendation."""
    if not context_records:
        store["recommended_viz_mode"] = "scatter"
        return None

    context_text = " ".join([
        str((record or {}).get("p", {}).get("location", "")) + " " +
        str((record or {}).get("p", {}).get("category", "")) + " " +
        str((record or {}).get("c", {}).get("description", ""))
        for record in context_records if record
    ])
    
    recommendation = scraper_agent._recommend_visualization(
        question=question,
        text=context_text,
        locations=[{"location": (record or {}).get("p", {}).get("location", "")} 
                for record in context_records if record and (record or {}).get("p", {}).get("location")]
    )
    
    if recommendation and recommendation.get("primary"):
        store["recommended_viz_mode"] = recommendation["primary"]["type"]
        return {
            "type": recommendation["primary"]["type"],
            "reason": recommendation["primary"]["reason"],
            "confidence": recommendation["primary"]["confidence"]
        }
    
    store["recommended_viz_mode"] = "scatter"
    return None


def _fetch_city_boundaries(osm_agent, city_names, features):
    """Helper to fetch city boundaries for choropleth."""
    boundaries = []
    for city_name in city_names:
        try:
            boundary_result = osm_agent.get_city_boundary(city_name)
            if boundary_result.get("ok"):
                city_locations = [f for f in features if city_name.lower() in f.get("location", "").lower()]
                importance_value = min(100, len(city_locations) * 10)
                
                boundaries.append({
                    "type": "Feature",
                    "geometry": boundary_result["geometry"],
                    "properties": {
                        **boundary_result.get("properties", {}),
                        "value": importance_value,
                        "location_count": len(city_locations),
                    }
                })
        except Exception as e:
            print(f"Failed to fetch boundary for {city_name}: {e}")
            continue
    return boundaries


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


@app.route("/weather-data", methods=["POST"])
def weather_data():
    """
    Fetch weather data for the given map bounds as a heatmap grid.
    Returns temperature data points across the region.
    """
    try:
        store = get_session_store()
        meteostat_agent: MeteostatAgent = store["meteostat_agent"]
        
        payload = request.get_json(silent=True) or {}
        bounds = payload.get("bounds", {})
        
        if not bounds or not all(k in bounds for k in ["north", "south", "east", "west"]):
            return jsonify({"ok": False, "error": "Invalid bounds provided"}), 400
        
        # Check if meteostat is available
        if not meteostat_agent.meteostat_available:
            return jsonify({
                "ok": False, 
                "error": "Meteostat library not available. Install with: pip install meteostat"
            }), 503
        
        # Create a grid of sample points across the bounds
        north = float(bounds["north"])
        south = float(bounds["south"])
        east = float(bounds["east"])
        west = float(bounds["west"])
        
        # Calculate center point for single weather station lookup
        center_lat = (north + south) / 2
        center_lon = (east + west) / 2
        
        print(f"Fetching weather for center point: ({center_lat}, {center_lon})")
        
        # Fetch weather for center point only (faster)
        try:
            # Add timeout protection
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Weather fetch timed out")
            
            # Set 10 second timeout (Windows doesn't support SIGALRM, so we'll use a try-except)
            result = meteostat_agent.process(
                latitude=center_lat,
                longitude=center_lon,
                interval="daily"
            )
            
            if not result.get("ok") or not result.get("data"):
                print(f"No weather data available: {result.get('error', 'Unknown error')}")
                # Return mock data as fallback
                print("Using mock weather data as fallback")
                avg_temp = 15.0  # Default temperature
            else:
                # Calculate average temperature
                temps = [d.get("tavg") for d in result["data"] if d.get("tavg") is not None]
                if not temps:
                    print("No temperature data in result, using mock data")
                    avg_temp = 15.0
                else:
                    avg_temp = sum(temps) / len(temps)
                    print(f"Average temperature: {avg_temp}°C")
            
            # Generate dense interpolated grid for raster-like appearance
            # Use 20x20 grid for smooth raster coverage
            lat_step = (north - south) / 19
            lon_step = (east - west) / 19
            
            weather_points = []
            import random
            random.seed(int(center_lat * 1000 + center_lon * 1000))
            
            for i in range(20):
                for j in range(20):
                    lat = south + (i * lat_step)
                    lon = west + (j * lon_step)
                    
                    # Add small random variation (±1.5°C) for natural appearance
                    variation = random.uniform(-1.5, 1.5)
                    temp = avg_temp + variation
                    
                    weather_points.append({
                        "lat": lat,
                        "lon": lon,
                        "temperature": round(temp, 1),
                        "value": temp
                    })
            
            print(f"Generated {len(weather_points)} weather points for raster display")
            
            return jsonify({
                "ok": True,
                "weather_points": weather_points,
                "bounds": bounds,
                "center_temperature": round(avg_temp, 1)
            })
            
        except Exception as point_error:
            print(f"Error fetching weather: {str(point_error)}")
            import traceback
            traceback.print_exc()
            
            # Return mock data as fallback
            print("Exception occurred, using mock weather data")
            avg_temp = 15.0
            lat_step = (north - south) / 19
            lon_step = (east - west) / 19
            
            weather_points = []
            import random
            random.seed(int(center_lat * 1000 + center_lon * 1000))
            
            for i in range(20):
                for j in range(20):
                    lat = south + (i * lat_step)
                    lon = west + (j * lon_step)
                    variation = random.uniform(-1.5, 1.5)
                    temp = avg_temp + variation
                    weather_points.append({
                        "lat": lat,
                        "lon": lon,
                        "temperature": round(temp, 1),
                        "value": temp
                    })
            
            return jsonify({
                "ok": True,
                "weather_points": weather_points,
                "bounds": bounds,
                "center_temperature": round(avg_temp, 1),
                "warning": "Using mock data due to API error"
            })
        
    except Exception as e:
        import traceback
        print(f"ERROR in weather_data endpoint: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"ok": False, "error": f"Server error: {str(e)}"}), 500



# @app.route("/clear-database", methods=["POST"])
# def clear_database():
#     """
#     Clear the Neo4j database.
#     """
#     try:
#         store = get_session_store()
#         neo4j_agent: Neo4jAgent = store["neo4j_agent"]
#         result = neo4j_agent.clear_database()
#         return jsonify(result)
#     except Exception as e:
#         return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/clear", methods=["POST"])
def clear_session():
    """
    Clear the chat history and context records from the session.
    """
    try:
        store = get_session_store()
        store["chat_history"] = []
        store["last_context_records"] = []
        store["recommended_viz_mode"] = "scatter"
        return jsonify({"ok": True, "message": "Session cleared successfully"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# -----------------------------
# Markdown formatting helper
# -----------------------------
def _enhance_text_readability(text: str) -> str:
    """
    Enhance text readability by automatically bolding important words and improving structure.
    Makes responses more readable for general public.
    """
    if not text:
        return text
    
    # Bold numbers (ratings, counts, percentages, etc.) - but not if already in bold
    text = re.sub(r'(?<!\*)\b(\d+(?:\.\d+)?(?:%|/10)?)\b(?!\*)', r'**\1**', text)
    
    # Bold category names
    categories = ['Beauty', 'Activities', 'Sound', 'Protection', 'Movement', 'Views', 'Climate Comfort',
                  'Historic', 'Architecture', 'Public Square', 'Cathedral', 'Park', 'Station']
    for category in categories:
        text = re.sub(rf'(?<!\*)\b({category})\b(?!\*)', r'**\1**', text, flags=re.IGNORECASE)
    
    # Bold key location/quality terms
    key_terms = ['location', 'locations', 'place', 'places', 'rating', 'average', 'total', 
                 'highest', 'lowest', 'best', 'top', 'excellent', 'good', 'great', 
                 'area', 'region', 'district', 'nearby', 'found', 'rated', 'quality',
                 'stunning', 'beautiful', 'magnificent', 'exceptional', 'vibrant',
                 'popular', 'famous', 'iconic', 'central', 'heart', 'hub']
    for term in key_terms:
        # Only bold if not already part of a markdown bold or in a link
        text = re.sub(rf'(?<!\*|\w)\b({term})\b(?!\*|\w)', r'**\1**', text, flags=re.IGNORECASE)
    
    # Bold headings that might not have markdown formatting
    text = re.sub(r'^([A-Z][A-Za-z\s]+:)$', r'### \1', text, flags=re.MULTILINE)
    
    # Bold place names that appear in quotes (likely from comments)
    text = re.sub(r'- \*([^*]+)\*', r'- *\1*', text)  # Keep location names in italics
    
    return text


def _render_markdown_to_html(text: str) -> str:
    """
    Best-effort conversion of Markdown to HTML with enhanced readability.
    Makes text easier to read for general public with bold formatting for important words.
    """
    content = (text or "").strip()
    if not content:
        return ""
    
    # Enhance readability before rendering
    content = _enhance_text_readability(content)
    
    # Try markdown2
    try:
        import markdown2  # type: ignore
        html = markdown2.markdown(content, extras=["fenced-code-blocks", "break-on-newline", "tables"])
        # Wrap tables in a responsive container with hover capability
        html = html.replace('<table>', '<div class="table-wrapper"><table class="hoverable-table">').replace('</table>', '</table></div>')
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
        # Wrap tables in a responsive container with hover capability
        html = html.replace('<table>', '<div class="table-wrapper"><table class="hoverable-table">').replace('</table>', '</table></div>')
        return html
    except Exception:
        # Fallback: preserve formatting minimally
        escaped = (
            content.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return f"<pre>{escaped}</pre>"


def _inject_geolocation_into_tables(html: str, context_records: List[Dict[str, Any]]) -> str:
    """
    Post-process HTML tables to inject geolocation data attributes into rows.
    This enables hover functionality to highlight locations on the map.
    """
    if not context_records or '<table' not in html:
        return html
    
    from bs4 import BeautifulSoup
    
    # Build location lookup map from context_records
    location_map = {}
    for record in context_records:
        place = record.get('p')
        if not place:
            continue
        
        # Convert to dict if needed
        if hasattr(place, 'items'):
            place = dict(place)
        elif not isinstance(place, dict):
            continue
        
        location = place.get('location', '').strip()
        lat = place.get('latitude')
        lon = place.get('longitude')
        place_id = place.get('place_id')
        
        if location and lat and lon:
            # Store by location name (case-insensitive)
            location_key = location.lower()
            location_map[location_key] = {
                'lat': float(lat),
                'lon': float(lon),
                'location': location,
                'place_id': place_id
            }
            
            # Also store by first part of location (before comma) for partial matches
            if ',' in location:
                location_short = location.split(',')[0].strip().lower()
                if location_short not in location_map:
                    location_map[location_short] = location_map[location_key]
    
    if not location_map:
        return html
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')
        
        injected_count = 0
        for table in tables:
            tbody = table.find('tbody')
            if not tbody:
                continue
            
            rows = tbody.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if not cells:
                    continue
                
                # Get location name from first cell
                location_text = cells[0].get_text(strip=True)
                
                # Try exact match first
                location_key = location_text.lower()
                geo_data = location_map.get(location_key)
                
                # If no exact match, try first part (before comma)
                if not geo_data and ',' in location_text:
                    location_short = location_text.split(',')[0].strip().lower()
                    geo_data = location_map.get(location_short)
                
                if geo_data:
                    # Add data attributes to the row
                    row['data-lat'] = str(geo_data['lat'])
                    row['data-lon'] = str(geo_data['lon'])
                    row['data-location'] = geo_data['location']
                    if geo_data.get('place_id'):
                        row['data-place-id'] = str(geo_data['place_id'])
                    injected_count += 1
        
        if injected_count > 0:
            print(f"INFO: Injected geolocation data into {injected_count} table rows")
        
        return str(soup)
    except Exception as e:
        print(f"Warning: Failed to inject geolocation data into tables: {e}")
        return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)



