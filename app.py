import os
import json
from typing import Dict, Any, List, Tuple
from flask import Flask, render_template, request, jsonify, session
from datetime import timedelta
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_core.prompts import PromptTemplate
from viz.pydeck_viz import PydeckVisualizer


app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")
app.permanent_session_lifetime = timedelta(hours=6)


def connect() -> Neo4jGraph:
    return Neo4jGraph(
        url=os.environ.get("NEO4J_URI", "neo4j+s://02f54a39.databases.neo4j.io"),
        username=os.environ.get("NEO4J_USERNAME", "neo4j"),
        password=os.environ.get("NEO4J_PASSWORD", "U9WSV67C8evx4nWCk48n3M0o7dX79T2XQ3cU1OJfP9c"),
    )


def init_model() -> ChatGoogleGenerativeAI:
    # Requires GOOGLE_API_KEY in environment for authentication
    return ChatGoogleGenerativeAI(
        model=os.environ.get("GOOGLE_MODEL", "gemini-flash-latest"),
        # google_api_key=os.environ.get("GOOGLE_API_KEY", "AIzaSyBd5uEUL-_yjzrnfAxrIzQvjNmqCR5M9kc"),
        temperature=0,
        convert_system_message_to_human=True,
    )


def build_chain() -> GraphCypherQAChain:
    qa_template = """You are a helpful assistant answering questions about places in a database.

Question: {question}

Database results:
{context}

Provide a clear, concise answer based on the results. Extract specific information requested.

Answer:"""
    qa_prompt = PromptTemplate(
        input_variables=["question", "context"],
        template=qa_template,
    )
    return GraphCypherQAChain.from_llm(
        llm=init_model(),
        graph=connect(),
        qa_prompt=qa_prompt,
        allow_dangerous_requests=True,
        verbose=True,
        return_intermediate_steps=True,
    )


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
            "chain": build_chain(),
        }
    return SESSIONS[sid]


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat_endpoint():
    store = get_session_store()
    chain: GraphCypherQAChain = store["chain"]
    chat_history: List[Tuple[str, str]] = store["chat_history"]

    payload = request.get_json(silent=True) or {}
    question = (payload.get("message") or "").strip()
    if not question:
        return jsonify({"ok": False, "error": "Empty message"}), 400

    # Enhance question with short history context
    if chat_history:
        context_text = "\n".join(
            [f"Previous Q: {q}\nPrevious A: {a}" for q, a in chat_history[-2:]]
        )
        enhanced_question = f"{context_text}\n\nCurrent question: {question}"
    else:
        enhanced_question = question

    try:
        result = chain.invoke({"query": enhanced_question})
        answer = result.get("result", "")

        # Capture context for map visualization
        last_context_records: List[Dict[str, Any]] = store.get("last_context_records", [])
        intermediate_steps = result.get("intermediate_steps", [])
        for step in intermediate_steps:
            context_records = step.get("context")
            if context_records:
                last_context_records = context_records
        store["last_context_records"] = last_context_records

        # If AI doesn't know, format some useful result summary
        if "don't know" in answer.lower():
            answer = format_results(last_context_records)

        # Persist history
        chat_history.append((question, answer))
        store["chat_history"] = chat_history

        # Render markdown to HTML for clients that want formatted output
        answer_html = _render_markdown_to_html(answer)
        return jsonify({"ok": True, "answer": answer, "answer_html": answer_html})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


def format_results(context: List[Dict[str, Any]]) -> str:
    if not context:
        return "No results found."
    output_lines: List[str] = [f"Found {len(context)} results:"]
    count = 0
    for record in context:
        count += 1
        if "p" in record:
            place = record["p"]
            location = place.get("location", "Unknown")
            lat = place.get("latitude")
            lon = place.get("longitude")
            pid = place.get("place_id")
            output_lines.append(f"{count}. {location} (ID: {pid}, Coords: {lat}, {lon})")
        if count >= 10:
            break
    if len(context) > 10:
        output_lines.append(f"... and {len(context) - 10} more")
    return "\n".join(output_lines)


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

    if not lat_col or not lon_col:
        return jsonify({"ok": True, "features": []})

    features = []
    for _, row in df.iterrows():
        lat = row.get(lat_col)
        lon = row.get(lon_col)
        if pd.isna(lat) or pd.isna(lon):
            continue
        features.append(
            {
                "lat": float(lat),
                "lon": float(lon),
                "location": str(row.get(loc_col, "")) if loc_col else "",
            }
        )
    return jsonify({"ok": True, "features": features})


@app.route("/pydeck", methods=["GET"])
def pydeck_view():
    store = get_session_store()
    records = store.get("last_context_records", [])
    mode = request.args.get("mode", "scatter").lower()
    try:
        viz = PydeckVisualizer()
        html = viz.render_html(records, mode=mode)
        # Return raw HTML for embedding
        return html
    except Exception as e:
        return f"<div style='padding:12px;color:#b00020;'>Error rendering pydeck: {str(e)}</div>", 500


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
        return markdown2.markdown(content, extras=["fenced-code-blocks", "break-on-newline"])
    except Exception:
        pass
    # Try python-markdown
    try:
        import markdown  # type: ignore
        return markdown.markdown(
            content,
            extensions=["extra", "sane_lists", "nl2br", "fenced_code"],
            output_format="html5",
        )
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



