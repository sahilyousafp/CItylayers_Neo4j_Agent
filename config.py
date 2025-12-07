import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Neo4j
    NEO4J_URI = os.environ.get("NEO4J_URI", "neo4j+s://02f54a39.databases.neo4j.io")
    NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")

    # LLM Configuration
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")  # "ollama" or "google"
    
    # Ollama
    OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
    
    # Google Gemini (legacy)
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
    GOOGLE_MODEL = os.environ.get("GOOGLE_MODEL", "gemini-flash-latest")

    # Flask
    FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

    # Mapbox
    MAPBOX_ACCESS_TOKEN = os.environ.get("MAPBOX_ACCESS_TOKEN")

    # Agent Configuration
    # You can add more specific agent configs here
    AGENTS = {
        "neo4j": {
            "uri": NEO4J_URI,
            "username": NEO4J_USERNAME,
            "password": NEO4J_PASSWORD,
            "llm_provider": LLM_PROVIDER,
            "ollama_base_url": OLLAMA_BASE_URL,
            "ollama_model": OLLAMA_MODEL,
            "google_model": GOOGLE_MODEL
        },
        "scraper": {
            # Add scraper config if needed
        },
        "osm": {
            # Add OSM config if needed
        }
    }
