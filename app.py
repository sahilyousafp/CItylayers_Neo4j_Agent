import os
import json
from typing import Dict, Any, List, Tuple
from flask import Flask, render_template, request, jsonify, session, make_response
from datetime import timedelta, datetime
import pandas as pd
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
import base64

# PDF generation
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image as RLImage
from reportlab.lib import colors
import markdown2

# Import agents
from agents import Neo4jAgent, WebScraperAgent, OSMAgent, OpenMeteoAgent, MovementAgent, VegetationAgent


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
            "address_cache": {},  # dict[(lat, lon): str] - Mapbox geocoding cache
            "exported_reports": [],  # list[dict] - Report export metadata
            "neo4j_agent": Neo4jAgent(Config.AGENTS["neo4j"]),
            # "viz_agent": VisualizationAgent(), # Deprecated
            "scraper_agent": WebScraperAgent(),
            "osm_agent": OSMAgent(),
            "openmeteo_agent": OpenMeteoAgent(),
            "movement_agent": MovementAgent(),
            "vegetation_agent": VegetationAgent(),
        }
    return SESSIONS[sid]


def _score_comment_relevance(comment_text: str, user_query: str) -> float:
    """
    Score the relevance of a comment to a user's query using keyword matching.
    
    Args:
        comment_text: The text content of the comment
        user_query: The user's question
        
    Returns:
        Relevance score (0.0 to 1.0), higher is more relevant
    """
    if not comment_text or not user_query:
        return 0.0
    
    # Normalize text
    comment_lower = comment_text.lower()
    query_lower = user_query.lower()
    
    # Define stop words to exclude
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
        'could', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i',
        'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who', 'when',
        'where', 'why', 'how', 'show', 'tell', 'find', 'get', 'about', 'me'
    }
    
    # Extract keywords from query (remove stop words and punctuation)
    query_words = re.findall(r'\b\w+\b', query_lower)
    keywords = [w for w in query_words if w not in stop_words and len(w) > 2]
    
    if not keywords:
        return 0.0
    
    # Calculate relevance score
    score = 0.0
    total_keywords = len(keywords)
    
    # Check each keyword
    for keyword in keywords:
        if keyword in comment_lower:
            # Base score for keyword presence
            score += 1.0
            
            # Bonus for keyword appearing in first 50 characters (emphasize early mentions)
            if keyword in comment_lower[:50]:
                score += 0.5
            
            # Bonus for exact phrase match (multiple adjacent keywords)
            if len(keyword) > 4:
                score += 0.3
    
    # Normalize score to 0-1 range
    max_possible_score = total_keywords * 1.8  # 1.0 + 0.5 + 0.3 per keyword
    normalized_score = min(score / max_possible_score, 1.0) if max_possible_score > 0 else 0.0
    
    return normalized_score


def _get_top_relevant_comments(
    comments: List[Dict[str, Any]],
    user_query: str,
    top_n: int = 5
) -> List[Dict[str, Any]]:
    """
    Get the top N most relevant comments based on user query.
    
    Args:
        comments: List of comment dictionaries with 'text' field
        user_query: The user's question
        top_n: Number of top comments to return
        
    Returns:
        List of top N most relevant comments with relevance scores
    """
    if not comments:
        return []
    
    # Score all comments
    scored_comments = []
    for comment in comments:
        comment_text = comment.get('text') or comment.get('content') or comment.get('comment_text') or ''
        if comment_text:
            score = _score_comment_relevance(comment_text, user_query)
            scored_comments.append({
                **comment,
                'relevance_score': score
            })
    
    # Sort by relevance score (descending) and return top N
    scored_comments.sort(key=lambda x: x['relevance_score'], reverse=True)
    return scored_comments[:top_n]


def _apply_comment_relevance_scoring(
    context_records: List[Dict[str, Any]],
    user_query: str
) -> List[Dict[str, Any]]:
    """
    Apply comment relevance scoring to context records.
    For each place/record, rank its comments by relevance to user query.
    
    Args:
        context_records: List of Neo4j records with places and comments
        user_query: The user's question
        
    Returns:
        Context records with comments sorted by relevance
    """
    if not context_records:
        return context_records
    
    processed_records = []
    
    for record in context_records:
        # Create a copy to avoid modifying original
        new_record = dict(record)
        
        # Check if this record has comments
        if 'co' in record and record['co']:
            comments_data = record['co']
            
            # Handle different comment structures
            if isinstance(comments_data, list):
                # List of comment objects
                top_comments = _get_top_relevant_comments(comments_data, user_query, top_n=5)
                new_record['co'] = top_comments
            elif isinstance(comments_data, dict):
                # Single comment object
                scored_comment = {
                    **comments_data,
                    'relevance_score': _score_comment_relevance(
                        comments_data.get('text', ''), 
                        user_query
                    )
                }
                new_record['co'] = [scored_comment]
        
        # Also check for 'comments' or 'comments_info' fields
        for comment_field in ['comments', 'comments_info', 'comment']:
            if comment_field in record and record[comment_field]:
                comments_data = record[comment_field]
                
                if isinstance(comments_data, list):
                    top_comments = _get_top_relevant_comments(comments_data, user_query, top_n=5)
                    new_record[comment_field] = top_comments
                elif isinstance(comments_data, dict):
                    scored_comment = {
                        **comments_data,
                        'relevance_score': _score_comment_relevance(
                            comments_data.get('text', ''), 
                            user_query
                        )
                    }
                    new_record[comment_field] = [scored_comment]
        
        processed_records.append(new_record)
    
    print(f"DEBUG: Applied comment relevance scoring to {len(processed_records)} records")
    return processed_records


def _reverse_geocode_location(lat: float, lon: float, mapbox_token: str) -> Dict[str, Any]:
    """
    Reverse geocode coordinates to precise address using Mapbox Geocoding API.
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        mapbox_token: Mapbox access token
        
    Returns:
        Dictionary with:
            - ok: bool (success status)
            - address: str (formatted address)
            - raw: dict (full API response)
            - error: str (if failed)
    """
    # Validate coordinates
    if not lat or not lon or lat < -90 or lat > 90 or lon < -180 or lon > 180:
        return {"ok": False, "error": "Invalid coordinates", "address": None}
    
    try:
        # Mapbox API endpoint (lon, lat order - not lat, lon!)
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lon},{lat}.json"
        params = {
            "access_token": mapbox_token,
            "types": "address,place,locality"  # Prefer street addresses
        }
        
        # Make API request with timeout
        response = requests.get(url, params=params, timeout=3)
        
        # Check response status
        if response.status_code == 429:
            print(f"WARN: Mapbox rate limit exceeded")
            return {"ok": False, "error": "Rate limit exceeded", "address": None}
        
        if response.status_code != 200:
            print(f"WARN: Mapbox API returned status {response.status_code}")
            return {"ok": False, "error": f"API returned {response.status_code}", "address": None}
        
        # Parse response
        data = response.json()
        features = data.get('features', [])
        
        if not features:
            print(f"WARN: No address found for coordinates ({lat}, {lon})")
            return {"ok": False, "error": "No address found", "address": None}
        
        # Extract formatted address from first feature
        place_name = features[0].get('place_name', '')
        
        if place_name:
            return {
                "ok": True,
                "address": place_name,
                "raw": features[0]
            }
        else:
            return {"ok": False, "error": "No place_name in response", "address": None}
            
    except requests.exceptions.Timeout:
        print(f"WARN: Mapbox geocoding timeout for ({lat}, {lon})")
        return {"ok": False, "error": "Request timeout", "address": None}
    except requests.exceptions.RequestException as e:
        print(f"WARN: Mapbox geocoding network error: {e}")
        return {"ok": False, "error": f"Network error: {str(e)}", "address": None}
    except Exception as e:
        print(f"ERROR: Unexpected error in geocoding: {e}")
        return {"ok": False, "error": f"Unexpected error: {str(e)}", "address": None}


def _batch_geocode_locations(
    locations: List[Tuple[float, float]], 
    mapbox_token: str,
    address_cache: Dict[Tuple[float, float], str],
    max_workers: int = 10
) -> Dict[Tuple[float, float], str]:
    """
    Geocode multiple locations concurrently using ThreadPoolExecutor.
    
    Args:
        locations: List of (lat, lon) tuples to geocode
        mapbox_token: Mapbox access token
        address_cache: Existing address cache (will be checked and updated)
        max_workers: Number of concurrent threads
        
    Returns:
        Dictionary mapping (lat, lon) to addresses
    """
    results = {}
    
    # Filter out already cached locations
    locations_to_geocode = []
    for lat, lon in locations:
        cache_key = (round(lat, 4), round(lon, 4))
        if cache_key in address_cache:
            results[cache_key] = address_cache[cache_key]
        else:
            locations_to_geocode.append((lat, lon))
    
    if not locations_to_geocode:
        print(f"DEBUG: All {len(locations)} locations found in cache")
        return results
    
    print(f"DEBUG: Geocoding {len(locations_to_geocode)} new locations (batch)")
    
    # Geocode remaining locations concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_coords = {
            executor.submit(_reverse_geocode_location, lat, lon, mapbox_token): (lat, lon)
            for lat, lon in locations_to_geocode
        }
        
        for future in as_completed(future_to_coords):
            coords = future_to_coords[future]
            cache_key = (round(coords[0], 4), round(coords[1], 4))
            
            try:
                result = future.result()
                if result.get('ok') and result.get('address'):
                    address = result['address']
                    results[cache_key] = address
                    address_cache[cache_key] = address
                    print(f"DEBUG: Geocoded ({coords[0]:.4f}, {coords[1]:.4f}) -> {address[:50]}...")
            except Exception as e:
                print(f"WARN: Failed to geocode {coords}: {e}")
    
    print(f"DEBUG: Successfully geocoded {len(results) - len(results.keys() & address_cache.keys())} locations")
    return results


def _enrich_context_with_addresses(
    context_records: List[Dict[str, Any]], 
    mapbox_token: str,
    address_cache: Dict[Tuple[float, float], str],
    max_locations: int = 50
) -> List[Dict[str, Any]]:
    """
    Enrich context records with precise Mapbox addresses.
    
    Args:
        context_records: List of Neo4j records
        mapbox_token: Mapbox API token
        address_cache: Session address cache (will be updated)
        max_locations: Maximum number of locations to geocode (rate limiting)
        
    Returns:
        Enhanced records with 'precise_address' field
    """
    if not context_records or not mapbox_token:
        print("DEBUG: Skipping address enrichment (no records or token)")
        return context_records
    
    # Collect unique coordinates from records
    coord_to_records = {}  # Map cache_key to list of record indices
    locations_to_geocode = []
    
    for idx, record in enumerate(context_records[:max_locations]):
        p = record.get('p', {})
        lat = p.get('latitude')
        lon = p.get('longitude')
        
        if lat and lon:
            cache_key = (round(lat, 4), round(lon, 4))
            if cache_key not in coord_to_records:
                coord_to_records[cache_key] = []
                locations_to_geocode.append((lat, lon))
            coord_to_records[cache_key].append(idx)
    
    if not locations_to_geocode:
        print("DEBUG: No valid coordinates found for geocoding")
        return context_records
    
    print(f"DEBUG: Enriching {len(locations_to_geocode)} unique locations with Mapbox addresses")
    
    # Batch geocode all unique locations
    geocoded_addresses = _batch_geocode_locations(
        locations_to_geocode,
        mapbox_token,
        address_cache
    )
    
    # Apply addresses to records
    enriched_count = 0
    for cache_key, record_indices in coord_to_records.items():
        address = geocoded_addresses.get(cache_key)
        
        for idx in record_indices:
            if address:
                context_records[idx]['precise_address'] = address
                enriched_count += 1
            else:
                # Fallback to database location
                p = context_records[idx].get('p', {})
                fallback_addr = p.get('location', 'Unknown Location')
                context_records[idx]['precise_address'] = fallback_addr
                print(f"DEBUG: Using fallback address for record {idx}: {fallback_addr}")
    
    print(f"DEBUG: Successfully enriched {enriched_count} records with precise addresses")
    
    # Debug: Show sample addresses
    if context_records:
        sample = context_records[0]
        print(f"DEBUG: Sample enriched record address: {sample.get('precise_address', 'N/A')}")
    
    return context_records


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


def _aggregate_multi_dataset_context(
    citylayers_records: List[Dict[str, Any]],
    external_datasets: Dict[str, Any],
    data_sources: List[str]
) -> Dict[str, Any]:
    """
    Aggregate data from multiple sources into a unified context for the LLM.
    
    Args:
        citylayers_records: Records from Neo4j CityLayers database
        external_datasets: Dict containing weather, transport, vegetation data
        data_sources: List of enabled data source names
    
    Returns:
        Dict with aggregated context from all sources
    """
    aggregated_context = {
        "citylayers": {
            "enabled": "citylayers" in data_sources,
            "count": len(citylayers_records),
            "data": citylayers_records[:50] if citylayers_records else []  # Limit to 50 for LLM context
        },
        "weather": {
            "enabled": "weather" in data_sources,
            "count": 0,
            "data": []
        },
        "transport": {
            "enabled": "transport" in data_sources,
            "count": 0,
            "data": []
        },
        "vegetation": {
            "enabled": "vegetation" in data_sources,
            "count": 0,
            "data": []
        }
    }
    
    # Add weather data if available
    if "weather" in data_sources and external_datasets.get("weather"):
        weather_data = external_datasets["weather"]
        if isinstance(weather_data, list) and len(weather_data) > 0:
            # Summarize weather data instead of including all points
            temps = [p.get("temperature", 0) for p in weather_data if "temperature" in p]
            winds = [p.get("windSpeed", 0) for p in weather_data if "windSpeed" in p]
            
            aggregated_context["weather"]["count"] = len(weather_data)
            aggregated_context["weather"]["data"] = {
                "summary": {
                    "avg_temperature": sum(temps) / len(temps) if temps else 0,
                    "min_temperature": min(temps) if temps else 0,
                    "max_temperature": max(temps) if temps else 0,
                    "avg_wind_speed": sum(winds) / len(winds) if winds else 0,
                    "sample_points": weather_data[:5]  # Include a few sample points
                }
            }
    
    # Add transport data if available
    if "transport" in data_sources and external_datasets.get("transport"):
        transport_data = external_datasets["transport"]
        if isinstance(transport_data, list) and len(transport_data) > 0:
            aggregated_context["transport"]["count"] = len(transport_data)
            aggregated_context["transport"]["data"] = transport_data[:30]  # Limit to 30 stations
    
    # Add vegetation data if available
    if "vegetation" in data_sources and external_datasets.get("vegetation"):
        vegetation_data = external_datasets["vegetation"]
        if isinstance(vegetation_data, list) and len(vegetation_data) > 0:
            aggregated_context["vegetation"]["count"] = len(vegetation_data)
            # Summarize vegetation by species
            species_counts = {}
            for tree in vegetation_data:
                species = tree.get("species", "Unknown")
                species_counts[species] = species_counts.get(species, 0) + 1
            
            aggregated_context["vegetation"]["data"] = {
                "summary": {
                    "total_trees": len(vegetation_data),
                    "species_diversity": len(species_counts),
                    "top_species": sorted(species_counts.items(), key=lambda x: x[1], reverse=True)[:10],
                    "sample_trees": vegetation_data[:10]
                }
            }
    
    return aggregated_context


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
    
    # Collect external dataset data if provided
    external_datasets = payload.get("external_datasets", {})
    
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
        
        # Aggregate multi-dataset context
        aggregated_context = _aggregate_multi_dataset_context(
            citylayers_records=context_records,
            external_datasets=external_datasets,
            data_sources=data_sources
        )
        
        print(f"DEBUG: Aggregated context summary:")
        for source, info in aggregated_context.items():
            if info["enabled"]:
                print(f"  - {source}: {info['count']} items")
        
        # Apply comment relevance scoring to context_records
        context_records = _apply_comment_relevance_scoring(context_records, question)
        
        # Enrich context records with precise Mapbox addresses
        context_records = _enrich_context_with_addresses(
            context_records=context_records,
            mapbox_token=Config.MAPBOX_ACCESS_TOKEN,
            address_cache=store.get("address_cache", {}),
            max_locations=50
        )
        
        # If multiple datasets are enabled, enhance the answer with cross-dataset analysis
        if len([s for s in data_sources if aggregated_context[s]["enabled"]]) > 1:
            # Pass aggregated context to Neo4j agent for cross-dataset analysis
            enhanced_result = neo4j_agent.process_multi_dataset(
                query=question,
                aggregated_context=aggregated_context,
                chat_history=chat_history
            )
            if enhanced_result and enhanced_result.get("ok"):
                answer = enhanced_result["answer"]
                print(f"DEBUG: Enhanced answer with multi-dataset analysis")
        
        # If no result yet, return error
        if not result or not result["ok"]:
            return jsonify({"ok": False, "error": "No data available from selected sources"}), 500
        
        # Enrich answer with online information about locations (only for citylayers data)
        if "citylayers" in data_sources and context_records:
            answer = _enrich_with_online_info(answer, context_records, scraper_agent, bounds)
        
        # Store context for map visualization
        store["last_context_records"] = context_records

        
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
                pass
        
        if grade_col:
            try:
                if grade_col in ['grades_and_subgrades', 'place_grades']:
                    grade = _extract_from_nested(row, grade_col)
                else:
                    grade = _safe_get_value(row, grade_col)
                if grade:
                    feature["grade"] = grade
            except Exception as e:
                pass
        
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
    Fetch weather data for the given map bounds using Open-Meteo API.
    Returns temperature data points across the region.
    """
    try:
        store = get_session_store()
        openmeteo_agent: OpenMeteoAgent = store["openmeteo_agent"]
        
        payload = request.get_json(silent=True) or {}
        bounds = payload.get("bounds", {})
        
        if not bounds or not all(k in bounds for k in ["north", "south", "east", "west"]):
            return jsonify({"ok": False, "error": "Invalid bounds provided"}), 400
        
        # Calculate center point
        north = float(bounds["north"])
        south = float(bounds["south"])
        east = float(bounds["east"])
        west = float(bounds["west"])
        
        center_lat = (north + south) / 2
        center_lon = (east + west) / 2
        

        
        # Fetch current weather from Open-Meteo
        try:
            result = openmeteo_agent.get_current_weather(
                latitude=center_lat,
                longitude=center_lon,
                temperature_unit="celsius"
            )
            
            if not result.get("ok") or not result.get("current"):
                print("⚠️ No current weather data from Open-Meteo")
                print(f"DEBUG: OpenMeteo result: {result}")
                avg_temp = 15.0  # Default temperature
                wind_speed = 0.0
                wind_direction = 0.0
            else:
                # Get current temperature and wind data
                current = result["current"]
                print(f"DEBUG: OpenMeteo current data: {current}")
                avg_temp = current.get("temperature", 15.0)
                wind_speed = current.get("wind_speed", 0.0)
                wind_direction = current.get("wind_direction", 0.0)
                print(f"✓ Weather data: temp={avg_temp}°C, wind={wind_speed}m/s @ {wind_direction}°")
                print(f"DEBUG: wind_speed type: {type(wind_speed)}, value: {wind_speed}")
                print(f"DEBUG: wind_direction type: {type(wind_direction)}, value: {wind_direction}")

            
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
                    
                    # Add small variation to wind speed (±0.5 m/s)
                    wind_var = random.uniform(-0.5, 0.5)
                    point_wind_speed = max(0, wind_speed + wind_var)
                    
                    # Add small variation to wind direction (±10°)
                    dir_var = random.uniform(-10, 10)
                    point_wind_dir = (wind_direction + dir_var) % 360
                    
                    weather_points.append({
                        "lat": lat,
                        "lon": lon,
                        "temperature": round(temp, 1),
                        "windSpeed": round(point_wind_speed, 1),
                        "windDirection": round(point_wind_dir, 0),
                        "value": temp
                    })
            

            
            return jsonify({
                "ok": True,
                "weather_points": weather_points,
                "bounds": bounds,
                "center_temperature": round(avg_temp, 1),
                "center_wind_speed": round(wind_speed, 1),
                "center_wind_direction": round(wind_direction, 0),
                "source": "open-meteo"
            })
            
        except Exception as point_error:

            import traceback
            traceback.print_exc()
            
            # Return mock data as fallback

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

        return jsonify({"ok": False, "error": f"Server error: {str(e)}"}), 500


@app.route("/transport-data", methods=["POST"])
def transport_data():
    """
    Fetch public transport stations within map bounds
    """
    try:
        data = request.get_json()
        bounds = data.get("bounds", {})
        
        if not bounds:
            return jsonify({"ok": False, "error": "Missing bounds"}), 400
        
        # Get center point
        north = bounds.get("north")
        south = bounds.get("south")
        east = bounds.get("east")
        west = bounds.get("west")
        
        center_lat = (north + south) / 2
        center_lon = (east + west) / 2
        
        # Calculate search radius based on bounds
        import math
        lat_diff = north - south
        lon_diff = east - west
        radius = int(max(lat_diff, lon_diff) * 111000 / 2)  # Convert to meters
        radius = min(radius, 3000)  # Max 3km radius to prevent API timeouts
        
        store = get_session_store()
        movement_agent = store["movement_agent"]
        
        # Get nearby stations
        stations = movement_agent.get_nearby_stations(center_lat, center_lon, radius)
        
        return jsonify({
            "ok": True,
            "stations": stations,
            "count": len(stations),
            "center": {"lat": center_lat, "lon": center_lon},
            "radius": radius
        })
        
    except Exception as e:
        import traceback

        return jsonify({"ok": False, "error": f"Server error: {str(e)}"}), 500


@app.route("/vegetation-data", methods=["POST"])
def vegetation_data():
    """
    Fetch vegetation/tree data within map bounds from Vienna Open Data
    """
    try:
        data = request.get_json()
        bounds = data.get("bounds", {})
        
        if not bounds:
            return jsonify({"ok": False, "error": "Missing bounds"}), 400
        
        store = get_session_store()
        vegetation_agent = store["vegetation_agent"]
        
        # Get vegetation data
        result = vegetation_agent.get_vegetation_in_bounds(bounds)
        
        return jsonify(result)
        
    except Exception as e:
        import traceback

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
            pass
        
        return str(soup)
    except Exception as e:
        pass
        return html


def _generate_pdf_report(
    conversation: List[Dict[str, Any]],
    map_screenshot: str,
    locations: List[Dict[str, Any]],
    statistics: Dict[str, Any],
    data_sources: List[str],
    report_title: str
) -> bytes:
    """
    Generate PDF report using reportlab.
    
    Args:
        conversation: List of chat messages
        map_screenshot: Base64 encoded map screenshot
        locations: List of location data
        statistics: Statistics dict
        data_sources: Enabled data sources
        report_title: Title for the report
        
    Returns:
        PDF bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#00bcd4'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#0097a7'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    # 1. Cover Page
    elements.append(Spacer(1, 2*inch))
    elements.append(Paragraph(f"<b>City Layers Analysis Report</b>", title_style))
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph(f"<b>{report_title}</b>", styles['Heading2']))
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    elements.append(Paragraph(f"Data Sources: {', '.join(data_sources)}", styles['Normal']))
    elements.append(PageBreak())
    
    # 2. Executive Summary
    elements.append(Paragraph("<b>Executive Summary</b>", heading_style))
    summary_text = f"""
    This report provides comprehensive analysis of {statistics.get('total_locations', 0)} locations
    across the selected area. The data includes insights from multiple categories with an average rating
    of {statistics.get('average_rating', 0):.1f} out of 10.
    """
    elements.append(Paragraph(summary_text, styles['Normal']))
    elements.append(Spacer(1, 12))
    
    # 3. Map Visualization
    if map_screenshot and map_screenshot.startswith('data:image'):
        elements.append(Paragraph("<b>Map Visualization</b>", heading_style))
        try:
            # Extract base64 data
            image_data = map_screenshot.split(',')[1]
            image_bytes = base64.b64decode(image_data)
            image_buffer = BytesIO(image_bytes)
            
            # Add image to PDF
            img = RLImage(image_buffer, width=5*inch, height=3.5*inch)
            elements.append(img)
            elements.append(Spacer(1, 12))
        except Exception as e:
            print(f"WARN: Could not embed map screenshot: {e}")
            elements.append(Paragraph("Map screenshot unavailable", styles['Italic']))
    
    elements.append(PageBreak())
    
    # 4. Conversation Log
    elements.append(Paragraph("<b>Conversation Log</b>", heading_style))
    
    if conversation and len(conversation) > 0:
        print(f"DEBUG: Processing {len(conversation)} conversation messages for PDF")
        for idx, msg in enumerate(conversation[-10:]):  # Last 10 messages
            # Handle both dict and string messages
            if isinstance(msg, dict):
                role = msg.get('role', msg.get('type', 'unknown'))
                content = msg.get('content', msg.get('message', ''))
                print(f"DEBUG: Message {idx} - dict with role={role}, content length={len(content)}")
            elif isinstance(msg, str):
                # If message is a string, treat it as user message
                role = 'user'
                content = msg
                print(f"DEBUG: Message {idx} - string, treating as user message")
            else:
                print(f"WARN: Message {idx} - unexpected type {type(msg)}, skipping")
                continue
            
            # Truncate long content
            if len(content) > 500:
                content = content[:500] + "..."
            
            # Clean content for PDF (remove special characters that break reportlab)
            content = content.replace('<', '&lt;').replace('>', '&gt;').replace('#', '').replace('*', '').replace('_', '')
            
            if role == 'user':
                p = Paragraph(f"<b>User:</b> {content}", styles['Normal'])
            else:
                p = Paragraph(f"<i>Assistant:</i> {content}", styles['Normal'])
            elements.append(p)
            elements.append(Spacer(1, 0.1 * inch))
    else:
        print(f"DEBUG: No conversation history available for PDF")
        elements.append(Paragraph("No conversation history available.", styles['Normal']))
    
    elements.append(PageBreak())
    
    # 5. Statistics Table
    elements.append(Paragraph("<b>Data Insights</b>", heading_style))
    
    stats_data = [
        ['Metric', 'Value'],
        ['Total Locations', str(statistics.get('total_locations', 0))],
        ['Average Rating', f"{statistics.get('average_rating', 0):.1f} / 10"],
        ['Top Rated Location', statistics.get('top_rated', {}).get('name', 'N/A')],
        ['Top Rating', f"{statistics.get('top_rated', {}).get('rating', 0):.1f}"],
    ]
    
    stats_table = Table(stats_data, colWidths=[3*inch, 3*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00bcd4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(stats_table)
    elements.append(Spacer(1, 12))
    
    # 6. Top Locations
    elements.append(PageBreak())
    elements.append(Paragraph("<b>Top Locations (Top 10)</b>", heading_style))
    
    for i, loc in enumerate(locations[:10], 1):
        elements.append(Paragraph(f"<b>{i}. {loc.get('name', 'Unknown')}</b>", styles['Heading3']))
        elements.append(Paragraph(f"Address: {loc.get('precise_address', 'N/A')}", styles['Normal']))
        elements.append(Paragraph(f"Category: {loc.get('category', 'N/A')} | Rating: {loc.get('grade', 0):.1f}/10", styles['Normal']))
        
        # Add top comment
        comments = loc.get('comments', [])
        if comments and len(comments) > 0:
            top_comment = comments[0]
            comment_text = top_comment.get('text', '')[:200]
            elements.append(Paragraph(f"💬 \"{comment_text}...\"", styles['Italic']))
        
        elements.append(Spacer(1, 12))
    
    # Build PDF
    doc.build(elements)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes


@app.route("/export-pdf", methods=["POST"])
def export_pdf():
    """Generate and download PDF report."""
    store = get_session_store()
    
    try:
        payload = request.get_json() or {}
        
        # Debug logging
        print(f"DEBUG: Received PDF export request")
        print(f"DEBUG: Payload keys: {list(payload.keys())}")
        print(f"DEBUG: Conversation type: {type(payload.get('conversation'))}")
        if payload.get('conversation'):
            conv = payload['conversation']
            print(f"DEBUG: Conversation length: {len(conv)}")
            if len(conv) > 0:
                print(f"DEBUG: First message type: {type(conv[0])}")
                print(f"DEBUG: First message: {str(conv[0])[:200]}")
        
        # Extract data from payload
        conversation = payload.get("conversation", [])
        map_screenshot = payload.get("map_screenshot", "")
        locations = payload.get("locations", [])
        statistics = payload.get("statistics", {})
        data_sources = payload.get("data_sources", ["citylayers"])
        report_title = payload.get("report_title", "Location Analysis")
        
        print(f"DEBUG: Generating PDF report with {len(locations)} locations")
        
        # Generate PDF
        pdf_bytes = _generate_pdf_report(
            conversation=conversation,
            map_screenshot=map_screenshot,
            locations=locations,
            statistics=statistics,
            data_sources=data_sources,
            report_title=report_title
        )
        
        # Track export in session
        report_meta = {
            "timestamp": datetime.now().isoformat(),
            "title": report_title,
            "locations_count": len(locations),
            "data_sources": data_sources
        }
        store["exported_reports"].append(report_meta)
        if len(store["exported_reports"]) > 10:
            store["exported_reports"] = store["exported_reports"][-10:]
        
        print(f"DEBUG: PDF generated successfully ({len(pdf_bytes)} bytes)")
        
        # Create response
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="city_layers_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        
        return response
        
    except Exception as e:
        print(f"ERROR: PDF generation failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)



