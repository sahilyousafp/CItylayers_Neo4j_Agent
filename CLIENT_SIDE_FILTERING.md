# Client-Side Follow-up Filtering System

## Overview
Redesigned follow-up query system to filter map points client-side based on successive queries. This allows for progressive filtering where each follow-up query narrows down the already displayed results without requiring new database queries.

## How It Works

### User Flow

1. **Initial Query** (e.g., "Show me movement points in this area")
   - Queries Neo4j database
   - Returns all matching points
   - Displays on map
   - Stores as `originalFullDataset`

2. **Follow-up Filter** (e.g., "Show points rated 80 or above")
   - Detects as client-side filter
   - Filters EXISTING map points
   - Removes points with grade < 80
   - Updates map display instantly

3. **Additional Follow-up** (e.g., "Show me the top 5")
   - Filters the ALREADY FILTERED points
   - Sorts by grade DESC
   - Keeps only top 5
   - Updates map again

4. **Reset Triggers**
   - Zoom change > 25%
   - Category filter button clicked
   - New initial query submitted

### Visual Flow

```
Initial Query
   ↓
[100 Movement Points] ←── Stored in originalFullDataset
   ↓
"Show rated 80+"
   ↓
[30 Movement Points] ←── Filtered client-side
   ↓
"Show top 5"
   ↓
[5 Movement Points] ←── Further filtered
   ↓
(Zoom out 30%)
   ↓
[100 Movement Points] ←── Auto-reset
```

## Implementation Details

### State Variables (`app.js`)

```javascript
let originalFullDataset = []; // All points from last database query
let activeFilters = [];        // Stack of active filters
let lastZoomLevel = null;      // Track zoom for reset detection
let zoomResetThreshold = 0.25; // 25% zoom change triggers reset
```

### Key Functions

#### `isClientSideFilter(query)`
Detects if a query should trigger client-side filtering.

**Keywords detected:**
- Grade: 'rated', 'grade', 'above', 'below', 'over', 'under'
- Ranking: 'top ', 'best', 'worst', 'highest', 'lowest'
- Filtering: 'show me the', 'filter', 'only', 'just'
- Pronouns: 'which ones', 'among', 'from these'

**Returns:** `true` if client-side filter, `false` for new query

#### `parseFilterCriteria(query)`
Extracts filter criteria from natural language.

**Supported filters:**
- `gradeMin`: Minimum grade threshold
- `gradeMax`: Maximum grade threshold  
- `topN`: Top N items by grade

**Examples:**
```javascript
"above 80" → { gradeMin: 80 }
"top 5" → { topN: 5 }
"highly rated" → { gradeMin: 70 }
"best" → { gradeMin: 80 }
```

#### `applyClientSideFilter(features, criteria)`
Applies filter criteria to feature array.

**Process:**
1. Filters by gradeMin if specified
2. Filters by gradeMax if specified
3. Sorts by grade DESC and takes topN if specified
4. Returns filtered array

#### `hasZoomChangedSignificantly()`
Checks if zoom changed by more than 25%.

**Formula:**
```javascript
zoomChange = Math.abs(currentZoom - lastZoomLevel) / lastZoomLevel
return zoomChange > 0.25
```

#### `resetFilteringState()`
Resets all filters and restores original dataset.

**Actions:**
- Clears `activeFilters` array
- Restores `mapState.features` from `originalFullDataset`
- Updates `lastZoomLevel`
- Shows notification in chat

### Modified Functions

#### `sendMessage(message)`
Enhanced to detect and handle client-side filters:

```javascript
if (isClientSideFilter(message) && originalFullDataset.length > 0) {
    // Parse criteria
    const criteria = parseFilterCriteria(message);
    
    // Apply filter to CURRENT features (allows stacking)
    mapState.features = applyClientSideFilter(mapState.features, criteria);
    
    // Track filter
    activeFilters.push({ query: message, criteria });
    
    // Show result message
    // Update visualization
    return; // Don't send to backend
}

// Otherwise, normal backend query
```

#### `refreshMapData()`
Now stores original dataset:

```javascript
originalFullDataset = data.features || [];
mapState.features = [...originalFullDataset];
activeFilters = [];
lastZoomLevel = map.getZoom();
```

#### `map.on('moveend')`
Added zoom change detection:

```javascript
if (hasZoomChangedSignificantly() && activeFilters.length > 0) {
    resetFilteringState();
    // Update visualization
    // Show notification
}
```

#### Category Filter Button
Added reset on click:

```javascript
applyFilterBtn.addEventListener('click', () => {
    resetFilteringState(); // Reset filters before new query
    // Then run new query
});
```

## Supported Query Patterns

### Grade Filtering

| Query | Criteria | Result |
|-------|----------|--------|
| "above 80" | `gradeMin: 80` | Points with grade > 80 |
| "below 50" | `gradeMax: 50` | Points with grade < 50 |
| "highly rated" | `gradeMin: 70` | Points with grade ≥ 70 |
| "best" | `gradeMin: 80` | Points with grade ≥ 80 |
| "rated 75 or above" | `gradeMin: 75` | Points with grade ≥ 75 |

### Top N Filtering

| Query | Criteria | Result |
|-------|----------|--------|
| "top 5" | `topN: 5` | Top 5 by grade |
| "top 10" | `topN: 10` | Top 10 by grade |
| "top 3" | `topN: 3` | Top 3 by grade |
| "best 5" | `topN: 5` | Top 5 by grade |

### Combined Filtering

Filters stack sequentially:

```
"Show movement in Vienna" 
→ 100 points

"Above 70" 
→ 40 points (filtered from 100)

"Top 10"
→ 10 points (filtered from 40)
```

## Reset Behavior

### Automatic Reset Triggers

#### 1. Significant Zoom Change
- **Threshold:** 25% change in zoom level
- **Reason:** Large zoom changes indicate user exploring different area
- **Behavior:** 
  - Restores all original points
  - Shows notification: "🔄 Filters reset due to zoom change"
  - Clears `activeFilters` stack

#### 2. Category Filter Button
- **Trigger:** User selects category and clicks "Filter" button
- **Reason:** New database query will replace current data
- **Behavior:**
  - Calls `resetFilteringState()`
  - Clears filters before loading new category data

### Manual Reset (Not Implemented Yet)
Could add a "Clear Filters" button to manually reset without zoom change.

## User Notifications

### Enhanced Filter Response

After applying a filter, the system shows a detailed response including:

#### 1. Summary Section
```
📍 Filtered Results
30 locations (filtered from 100)
Grade ≥ 80
```

#### 2. Statistics Table
```
Categories:     Movement, Beauty
Average Grade:  85.3/100
Grade Range:    80.0 - 95.5
```

#### 3. Top Locations Table
Shows up to 10 highest-graded locations with:
- Rank number
- Location name (hoverable)
- Category
- Grade (color-coded)
  - Green (≥80)
  - Blue (70-79)
  - Orange (50-69)
  - Red (<50)

#### 4. Tip Message
```
💡 Tip: You can continue filtering these results, or zoom out / change category to reset.
```

### Example Full Response
```html
📍 Filtered Results
30 locations (filtered from 100)
Grade ≥ 80

Categories:     Movement
Average Grade:  86.2/100
Grade Range:    80.5 - 94.3

Top 10 Locations:
#  Location                   Category   Grade
1  Stephansplatz              Movement   94.3
2  Karlsplatz                 Movement   92.1
3  Westbahnhof               Movement   89.7
...and 20 more locations

💡 Tip: You can continue filtering these results, or zoom out / change category to reset.
```

### No Results Response
```
No locations match your filter criteria.
Try adjusting your filter or zoom out to reset.
```

### Auto-Reset
```
🔄 Filters reset due to zoom change. Showing all original locations.
```

## Example Workflows

### Workflow 1: Progressive Filtering
```
1. User zooms to Vienna center
2. Query: "Show me all movement points"
   → System: Queries DB, shows 150 points
   
3. Query: "Which ones are highly rated?"
   → System: Filters client-side, shows 45 points with grade ≥ 70
   → Message: "Filtered to 45 locations (from 150)"
   
4. Query: "Show me the top 10"
   → System: Filters client-side, shows 10 points
   → Message: "Filtered to 10 locations (from 45)"
   
5. User zooms out 40%
   → System: Auto-resets, shows all 150 points again
   → Message: "🔄 Filters reset due to zoom change"
```

### Workflow 2: Category Switch Reset
```
1. Query: "Show beauty spots"
   → 80 beauty locations shown
   
2. Query: "Above 85"
   → 20 beauty locations shown (filtered)
   
3. User selects "Movement" category and clicks "Filter"
   → System: Resets filters
   → System: Queries DB for Movement category
   → New set of movement locations shown
```

## Technical Considerations

### Memory Efficiency
- `originalFullDataset` stores full dataset once
- Filters don't duplicate data, just reference filtering
- Automatic cleanup on new queries

### Performance
- Client-side filtering is instant (no network delay)
- JavaScript array operations are O(n) where n = number of points
- Typically <100ms for datasets of 1000 points

### Limitations
1. **Can only filter displayed data** - Can't bring back points that weren't in original query
2. **Grade-only filtering** - Currently only supports grade-based criteria
3. **No category mixing** - Can't filter by category client-side (that would need backend)

## Future Enhancements

### Potential Additions
1. **Filter by comments**: "Show ones with good comments"
2. **Location-based**: "Show ones near me"
3. **Category filtering**: "Only beauty spots" (if mixed categories in results)
4. **Manual reset button**: Clear all filters explicitly
5. **Filter history**: Undo/redo filter operations
6. **Filter visualization**: Show active filters as chips
7. **Save filter presets**: "My favorite filters"

### Code Extensions
```javascript
// Add comment filtering
if (criteria.commentFilter) {
    filtered = filtered.filter(f => 
        f.comments && f.comments.some(c => 
            c.text.toLowerCase().includes(criteria.commentFilter)
        )
    );
}

// Add distance filtering
if (criteria.maxDistance) {
    const userLocation = map.getCenter();
    filtered = filtered.filter(f => 
        calculateDistance(userLocation, [f.lat, f.lon]) < criteria.maxDistance
    );
}
```

## Debugging

### Console Logs
```javascript
console.log('Detected client-side filter query:', message);
console.log('Filter criteria:', criteria);
console.log('Filter state reset - showing all original points');
console.log('Significant zoom change detected - resetting filters');
console.log('Category filter button clicked - resetting filters');
```

### State Inspection
In browser console:
```javascript
// Check current state
originalFullDataset.length  // Should match initial query count
mapState.features.length     // Current filtered count
activeFilters                // Stack of applied filters
lastZoomLevel                // Last tracked zoom level
```

## Summary

The client-side filtering system provides:
- ✅ **Progressive filtering** - Stack multiple filters
- ✅ **Instant results** - No network delay
- ✅ **Smart reset** - Auto-detect when to reset
- ✅ **Natural language** - Parse filter criteria from queries
- ✅ **Grade-aware** - Filter by quality thresholds
- ✅ **Top N support** - Show best/worst items
- ✅ **User feedback** - Clear messages about what's happening

This creates a smooth, exploratory experience where users can quickly drill down into their data without waiting for database queries.
