# Grade Filtering Fix - Summary

## Problem
Queries like "Show me movement rated high" and "Show points graded above 80" were not returning any results.

## Root Causes Identified

### 1. **Cypher Query Generation** 
The LLM generating Cypher queries didn't have instructions for handling grade filtering.

### 2. **Grade Data Extraction**
The grade extraction from nested `place_grades` structure wasn't properly handling the data format.

### 3. **Zoom Behavior**
Unrelated but fixed: Map was automatically zooming out when showing query results.

## Changes Made

### 1. Enhanced Cypher Generation Template (`agents/neo4j_agent.py`)

Added comprehensive grade filtering instructions:
- **Keywords detected**: "high", "best", "top", "above", "over", "greater than", "rated", "grade", "low", "worst", "below", "under", "less than"
- **Numeric threshold mapping**:
  * "above 80" → `pg.grade > 80`
  * "at least 70" → `pg.grade >= 70`
  * "below 50" → `pg.grade < 50`
  * "high" or "highly rated" → `pg.grade >= 70`
  * "best" or "top" → `pg.grade >= 80`
  * "low" → `pg.grade <= 30`

- **Query patterns**:
  ```cypher
  # With category filter
  MATCH (p:places)<-[:ASSOCIATED_WITH]-(pg:place_grades)-[:OF_CATEGORY]->(c:categories)
  WHERE p.latitude >= south AND p.latitude <= north
    AND p.longitude >= west AND p.longitude <= east
    AND c.category_id = X
    AND pg.grade >= 70
  OPTIONAL MATCH (co:comments)-[:ABOUT]->(p)
  RETURN DISTINCT p, c, pg, co
  ORDER BY pg.grade DESC
  
  # Without category filter
  MATCH (p:places)<-[:ASSOCIATED_WITH]-(pg:place_grades)
  WHERE p.latitude >= south AND p.latitude <= north
    AND p.longitude >= west AND p.longitude <= east
    AND pg.grade >= 80
  OPTIONAL MATCH (pg)-[:OF_CATEGORY]->(c:categories)
  OPTIONAL MATCH (co:comments)-[:ABOUT]->(p)
  RETURN DISTINCT p, c, pg, co
  ORDER BY pg.grade DESC
  ```

### 2. Improved Grade Extraction (`app.py`)

Enhanced `map_data()` endpoint to properly extract grades from nested structures:
- Checks for `place_grades` list
- Extracts `grade` or `value` field from grade objects
- Converts to float for proper numerical handling
- Added error logging for debugging

**Before:**
```python
grade = _extract_from_nested(row, grade_col)
if grade:
    feature["grade"] = grade
```

**After:**
```python
grades_data = row.get(grade_col)
if isinstance(grades_data, list) and len(grades_data) > 0:
    grade_obj = grades_data[0]
    if isinstance(grade_obj, dict):
        grade_value = grade_obj.get('grade') or grade_obj.get('value')
        if grade_value:
            feature["grade"] = float(grade_value)
```

### 3. Fixed Zoom Behavior (`static/js/app.js`)

Removed automatic `fitBounds()` call that was zooming the map to show all results:
- **Before**: Map zoomed to fit all data points on every query
- **After**: Map maintains current zoom level, showing results within visible bounds

## Testing

### Test Queries
1. **"Show me movement rated high"**
   - Should return Movement category locations with grade >= 70
   
2. **"Show points graded above 80"**
   - Should return all locations with grade > 80
   
3. **"Best beauty spots"**
   - Should return Beauty category locations with grade >= 80, sorted by grade DESC
   
4. **"Movement places with grade over 75"**
   - Should return Movement category with grade > 75

### Debug Output
When you run a query, check the terminal/console for:
```
⚡ GENERATED CYPHER:
<the actual Cypher query generated>
```

This will help verify the LLM is correctly generating grade filters.

## Grade Scale
- **Scale**: 0-100
- **Storage**: `pg.grade` property in `place_grades` nodes
- **High**: >= 70
- **Best/Top**: >= 80
- **Low**: <= 30
- **Worst**: <= 20

## Expected Behavior

### Query: "Show me movement rated high"
1. System detects category: Movement (ID: 3)
2. System detects grade filter: "rated high" → grade >= 70
3. Generates Cypher with both filters
4. Returns Movement locations with grade >= 70
5. Displays points on map within current view bounds

### Query: "Show points graded above 80"
1. No category detected (all categories)
2. System detects grade filter: "above 80" → grade > 80
3. Generates Cypher with grade filter only
4. Returns all locations with grade > 80
5. Displays points on map within current view bounds
