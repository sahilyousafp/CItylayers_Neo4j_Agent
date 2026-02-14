# Nested/Follow-up Questions Feature

## Overview
Added the ability to ask follow-up questions to filter and analyze data already displayed on the map. When you run a query, the system now shows 4 contextual filter questions that help you drill down into the results.

## Features

### 1. **Suggested Filter Questions**
After any query returns results, you'll see 4 suggested questions to help filter through the data:

**Example suggestions:**
- "Which ones are highly rated?"
- "Show me the top 5"
- "Which have grade above 80?"
- "What are the differences between them?"

### 2. **Contextual Suggestions**
The suggestions are smart and adapt to your data:

- **Grade-based**: If results have low average grades, suggests "Which ones are highly rated?"
- **Top N**: If many results (>5), suggests "Show me the top 5"
- **Category-specific**: If multiple categories exist, suggests filtering by one
- **Comparative**: If multiple results, suggests comparison questions

### 3. **One-Click Filtering**
Simply click any suggested question to immediately:
- Filter the existing results
- Show refined data on map
- Get a new answer focused on the filtered subset

### 4. **Enhanced Follow-up Detection**
The system recognizes follow-up questions using keywords:
- "which ones", "which one"
- "how many of them/these"
- "among them/these"
- "from these/those"
- "of them/these/those"
- "the best", "the top"
- "show me only", "filter by"

### 5. **Grade-aware Filtering**
Follow-up queries now understand grade filtering:
- "highly rated" → grade >= 70
- "above X" or "over X" → grade > X
- "best" or "top" → grade >= 80
- "low grade" → grade <= 30

## Implementation Details

### Backend Changes (`app.py`)

#### New Function: `_generate_suggested_filter_questions()`
```python
def _generate_suggested_filter_questions(records, category_filter=None):
    # Analyzes current data
    # Extracts grades and categories
    # Returns 4 contextual suggestions
```

**Logic:**
1. Extracts grades from `pg.grade` field
2. Extracts categories from `c.type` field
3. Calculates avg_grade, max_grade
4. Generates 4 contextual suggestions based on data characteristics

#### Enhanced Follow-up Filtering
- Updated filter prompt to include grade filtering instructions
- Fixed context extraction to show actual grades from `pg.grade`
- Returns place_id array for precise filtering

#### API Response
Added `suggested_questions` field to `/chat` endpoint response:
```json
{
  "ok": true,
  "answer": "...",
  "answer_html": "...",
  "context": [...],
  "suggested_questions": [
    "Which ones are highly rated?",
    "Show me the top 5",
    "Which have grade above 80?",
    "What are the differences between them?"
  ]
}
```

### Frontend Changes

#### HTML (`templates/index.html`)
Added suggestions container between chat window and form:
```html
<div id="suggestedQuestions" class="suggested-questions" style="display: none;">
    <div class="suggestions-label">💡 Filter these results:</div>
    <div id="suggestionsContainer" class="suggestions-container"></div>
</div>
```

#### CSS (`static/css/styles.css`)
Added styling for suggestions:
- Clean, modern button design
- Hover effects with transform
- Smooth slide-down animation
- Responsive layout

#### JavaScript (`static/js/app.js`)
Added two new functions:

**`displaySuggestedQuestions(questions)`**
- Takes array of question strings
- Creates clickable buttons
- Adds click handlers
- Shows suggestions container

**`hideSuggestedQuestions()`**
- Hides suggestions container
- Called on error or new query

## Usage Examples

### Example 1: Basic Query + Filter
```
User: "Show me beauty spots in Vienna"
System: Returns 50 beauty locations
Suggestions:
  1. Which ones are highly rated?
  2. Show me the top 5
  3. Which have grade above 80?
  4. What are the differences between them?

User clicks: "Which ones are highly rated?"
System: Filters to 15 locations with grade >= 70
```

### Example 2: Multi-category Results
```
User: "Places in this area"
System: Returns mixed categories (Beauty, Movement, Activities)
Suggestions:
  1. Which ones are highly rated?
  2. Show me the top 5
  3. Filter by Beauty only
  4. What are the differences between them?

User clicks: "Filter by Beauty only"
System: Shows only Beauty category locations
```

### Example 3: Natural Language Follow-up
```
User: "Show me all restaurants"
System: Returns 100 restaurants

User types: "which ones are above 80"
System: Automatically detects follow-up
         Filters existing 100 restaurants
         Returns only those with grade > 80
```

## Technical Architecture

### Data Flow
```
1. User sends query
   ↓
2. Backend processes query → Neo4j
   ↓
3. Results returned (context_records)
   ↓
4. _generate_suggested_filter_questions() analyzes data
   ↓
5. Suggestions added to response
   ↓
6. Frontend displays suggestions as buttons
   ↓
7. User clicks suggestion
   ↓
8. New query sent with follow-up flag
   ↓
9. Backend filters existing data (no new Neo4j query)
   ↓
10. Filtered results displayed
```

### Follow-up Detection Flow
```
1. User sends: "which ones are highly rated?"
   ↓
2. _is_follow_up_query() checks indicators
   ↓
3. Retrieves last_context_records from session
   ↓
4. LLM filters records based on criteria
   ↓
5. Returns matched place_ids
   ↓
6. Filters context_records to matched IDs only
   ↓
7. Generates answer for filtered subset
   ↓
8. New suggestions generated for filtered data
```

## Benefits

1. **Faster Exploration**: No need to type complex filter queries
2. **Guided Discovery**: Suggestions guide users to interesting subsets
3. **Reduced Load**: Follow-ups filter in-memory, no database queries
4. **Better UX**: Visual, clickable interface vs typing
5. **Smart Context**: Suggestions adapt to data characteristics

## Future Enhancements

Potential improvements:
- Custom suggestion preferences
- More suggestion templates
- Suggestion history/undo
- Multi-level follow-ups (filter → filter → filter)
- Export filtered results separately

## Testing

### Test Scenarios

1. **Basic filtering**
   - Query: "Show me movement spots"
   - Click: "Which ones are highly rated?"
   - Expected: Only high-grade movement spots

2. **Top N filtering**
   - Query: "Places in Vienna"
   - Click: "Show me the top 5"
   - Expected: 5 highest-graded places

3. **Grade threshold**
   - Query: "Beauty locations"
   - Click: "Which have grade above 80?"
   - Expected: Only beauty spots with grade > 80

4. **Natural language follow-up**
   - Query: "All restaurants"
   - Type: "the best ones"
   - Expected: Highest-graded restaurants

5. **Multiple follow-ups**
   - Query: "Places here"
   - Click: "Filter by Beauty only"
   - Click: "Show me the top 5"
   - Expected: Top 5 beauty spots
