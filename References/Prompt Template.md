# Windsurf Development Prompt: Neo4j Geo-Chat Application

## Project Overview
Create a Flask-based web application that combines a conversational AI interface with an interactive map. The system queries a Neo4j graph database about geographical locations and visualizes results in real-time.

---

## Core Requirements

### 1. Backend Architecture (Python/Flask)

**Agent-Based Chat System:**
- Create a `ChatAgent` class that manages:
  - Neo4j database connections
  - Gemini AI model interactions via LangChain
  - Conversation history and context management
  - Query result parsing and formatting
  
**Key Components:**
```python
# Expected structure:
class ChatAgent:
    def __init__(self):
        self.graph = Neo4jGraph(...)
        self.llm = ChatGoogleGenerativeAI(...)
        self.conversation_history = []
        
    def process_query(self, user_input, map_context=None):
        # Process natural language queries
        # Consider map selections/regions if provided
        # Return: {answer, locations, cypher_query}
        
    def extract_locations(self, neo4j_results):
        # Parse results into map-ready format
        # Return: [{id, name, lat, lng, properties}]
```

**Flask API Endpoints:**
- `POST /api/chat` - Send message, receive AI response + location data
- `POST /api/query-map-selection` - Query about selected map region/markers
- `GET /api/conversation-history` - Retrieve chat history
- `POST /api/reset` - Clear conversation context
- `GET /api/health` - Database connection status

### 2. Frontend Architecture (HTML/CSS/JavaScript)

**Layout:**
```
┌─────────────────────────────────────────┐
│          Header/Title Bar               │
├──────────────────┬──────────────────────┤
│                  │                      │
│   Chat Panel     │   Interactive Map    │
│   (Left 40%)     │   (Right 60%)        │
│                  │                      │
│  ┌────────────┐  │  ┌────────────────┐ │
│  │  Messages  │  │  │   Leaflet/     │ │
│  │  (scrolls) │  │  │   Mapbox Map   │ │
│  │            │  │  │                │ │
│  └────────────┘  │  │  • Markers     │ │
│  ┌────────────┐  │  │  • Polygons    │ │
│  │Input + Send│  │  │  • Selection   │ │
│  └────────────┘  │  └────────────────┘ │
└──────────────────┴──────────────────────┘
```

**Map Integration:**
- Use Leaflet.js or Mapbox GL JS
- Features needed:
  - Display location markers from Neo4j results
  - Clickable markers showing place details
  - Drawing tools for region selection (rectangle, polygon, circle)
  - Click-to-query: "Tell me about this area"
  - Highlight selected/relevant locations during conversation
  - Clustering for many markers

**Chat Interface:**
- Message bubbles (user vs assistant)
- Typing indicators
- Display location links that highlight map markers
- Show Cypher queries in expandable sections (optional)
- Auto-scroll to latest message
- Timestamp display

### 3. Integration Features

**Bidirectional Communication:**
- **Chat → Map:** When AI returns locations, automatically display them on map
- **Map → Chat:** When user selects region or clicks marker, populate chat with context
  - Example: User draws rectangle → "Tell me about places in the selected area"
  - Example: User clicks marker → Show place details in chat

**Smart Context Handling:**
```javascript
// When user selects map region:
const mapContext = {
    type: 'region',
    bounds: [[lat1, lng1], [lat2, lng2]],
    markerIds: selectedMarkerIds
};

// Send with next chat message:
sendMessage(userInput, mapContext);
```

---

## Technical Specifications

### Backend Stack
- **Framework:** Flask 3.x
- **Database:** Neo4j (credentials provided in original code)
- **AI:** LangChain + Google Gemini Flash
- **Additional Libraries:**
  - `flask-cors` for frontend communication
  - `flask-socketio` (optional, for real-time updates)
  - `python-dotenv` for environment variables

### Frontend Stack
- **Map Library:** Leaflet.js (recommended) or Mapbox GL JS
- **Map Drawing:** Leaflet.draw plugin
- **Styling:** Tailwind CSS or Bootstrap 5
- **HTTP Client:** Fetch API or Axios

### Data Flow Example
```
1. User: "Show me cafes in Barcelona"
   ↓
2. Flask processes query through ChatAgent
   ↓
3. Neo4j Cypher: MATCH (p:Place) WHERE p.type='cafe' AND p.city='Barcelona'
   ↓
4. Response: {
       answer: "Found 15 cafes in Barcelona...",
       locations: [{place_id, name, lat, lng, ...}],
       cypher: "MATCH..."
   }
   ↓
5. Frontend: Display answer + plot 15 markers on map
   ↓
6. User clicks marker on map
   ↓
7. Auto-populate chat: "Tell me more about [Cafe Name]"
```

---

## Implementation Steps

### Phase 1: Backend Agent
1. Refactor existing code into `ChatAgent` class
2. Add method to handle map context in queries
3. Implement location extraction from Neo4j results
4. Create Flask app with API routes
5. Add error handling and logging

### Phase 2: Frontend Shell
1. Create HTML layout with split panels
2. Integrate Leaflet.js map
3. Build chat UI components
4. Implement basic message sending/receiving

### Phase 3: Integration
1. Connect chat API to frontend
2. Implement location plotting on map
3. Add map selection → chat query feature
4. Add marker click → chat context feature
5. Style and polish UI

### Phase 4: Enhancements
1. Add conversation history persistence
2. Implement map layer controls (satellite, terrain)
3. Add export chat/results feature
4. Optimize for mobile responsiveness
5. Add loading states and animations

---

## Example API Response Format

```json
{
  "success": true,
  "answer": "I found 8 museums in Madrid. The most popular is the Prado Museum.",
  "locations": [
    {
      "place_id": "ChIJ...",
      "name": "Prado Museum",
      "latitude": 40.4138,
      "longitude": -3.6921,
      "type": "museum",
      "properties": {
        "rating": 4.8,
        "visitors": "3M/year"
      }
    }
  ],
  "cypher_query": "MATCH (p:Place) WHERE p.type='museum' AND p.city='Madrid' RETURN p",
  "conversation_id": "uuid-123"
}
```

---

## Environment Variables (.env)

```
NEO4J_URL=neo4j+s://02f54a39.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=U9WSV67C8evx4nWCk48n3M0o7dX79T2XQ3cU1OJfP9c
GEMINI_API_KEY=your_gemini_api_key_here
FLASK_SECRET_KEY=your_secret_key
FLASK_ENV=development
```

---

## UI/UX Guidelines

**Chat Panel:**
- Clean, minimalist design
- Clear distinction between user/AI messages
- Location mentions should be clickable (highlight on map)
- Show "thinking..." animation during queries

**Map Panel:**
- Default center: User's region or last queried location
- Zoom controls
- Search box for quick location lookup
- Legend showing marker types/colors
- "Ask about this area" button when region selected

**Responsive Behavior:**
- Desktop: Side-by-side layout (40/60 split)
- Tablet: Tabs to switch between chat/map
- Mobile: Stack vertically with sticky map button

---

## Security Considerations

- Never expose Neo4j credentials in frontend code
- Validate all user inputs on backend
- Sanitize Cypher queries to prevent injection
- Rate limit API endpoints
- Use HTTPS in production

---

## Testing Requirements

- Test with various query types (location names, regions, attributes)
- Test map selection → query flow
- Test with 100+ markers (clustering)
- Test conversation context retention
- Test error scenarios (DB down, invalid queries)

---

## Deliverables

1. `app.py` - Main Flask application
2. `chat_agent.py` - Agent class with Neo4j/LangChain logic
3. `templates/index.html` - Main web interface
4. `static/js/main.js` - Frontend JavaScript
5. `static/css/style.css` - Custom styles
6. `requirements.txt` - Python dependencies
7. `.env.example` - Environment variable template
8. `README.md` - Setup and usage instructions

---

## Success Criteria

✅ User can ask natural language questions about places
✅ Map displays query results automatically
✅ User can select map regions and query about them
✅ Conversation maintains context across multiple turns
✅ Clicking map markers provides relevant information
✅ UI is responsive and intuitive
✅ System handles errors gracefully

---

## Getting Started Command

```bash
# After generating code:
pip install -r requirements.txt
python app.py
# Navigate to http://localhost:5000
```

---

**Note to Windsurf:** Please implement this as a production-ready application with clean code organization, comprehensive error handling, and user-friendly design. Prioritize the core chat + map integration first, then add enhancements.