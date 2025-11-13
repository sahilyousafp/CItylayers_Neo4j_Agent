import os
import json
from typing import Dict, Any, List, Tuple
from flask import Flask, render_template, request, jsonify, session
from datetime import timedelta
import pandas as pd

# Import agents
from agents import Neo4jAgent, VisualizationAgent


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
            "neo4j_agent": Neo4jAgent(),
            "viz_agent": VisualizationAgent(),
        }
    return SESSIONS[sid]


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat_endpoint():
    store = get_session_store()
    neo4j_agent: Neo4jAgent = store["neo4j_agent"]
    chat_history: List[Tuple[str, str]] = store["chat_history"]

    payload = request.get_json(silent=True) or {}
    question = (payload.get("message") or "").strip()
    if not question:
        return jsonify({"ok": False, "error": "Empty message"}), 400

    try:
        # Use Neo4j agent to process the query
        result = neo4j_agent.process(query=question, chat_history=chat_history)
        
        if not result["ok"]:
            return jsonify(result), 500
        
        answer = result["answer"]
        context_records = result["context_records"]
        
        # Store context for map visualization
        store["last_context_records"] = context_records

        # Persist history
        chat_history.append((question, answer))
        store["chat_history"] = chat_history

        # Render markdown to HTML for clients that want formatted output
        answer_html = _render_markdown_to_html(answer)
        return jsonify({"ok": True, "answer": answer, "answer_html": answer_html})
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
    mode = request.args.get("mode", "scatter").lower()
    
    try:
        html = viz_agent.process(records=records, mode=mode)
        return html
    except Exception as e:
        return f"<div style='padding:12px;color:#b00020;'>Error rendering visualization: {str(e)}</div>", 500


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



