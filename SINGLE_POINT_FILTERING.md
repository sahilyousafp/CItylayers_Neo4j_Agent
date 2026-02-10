# Single Point Location Filtering

## Problem

When querying about a specific single location (e.g., "tell me about Stephansplatz" or "show me just this point"), the system was defaulting to showing ALL points in that category within the zone, instead of filtering to just that one point.

## Root Cause

Single-point queries were not recognized as client-side filters, so they were sent to the backend as new queries. The backend interpreted these as location-based searches and returned all points in the current category within the visible bounds.

## Solution

Enhanced the client-side filtering system to detect and handle location-specific queries:

### 1. Enhanced Filter Detection

Added location-specific keywords to `isClientSideFilter()`:

```javascript
const filterKeywords = [
    // ... existing keywords ...
    'this point', 'this location', 'this place',
    'that point', 'that location', 'that place',
    'tell me about', 'what about', 'show me just'
];
```

**Triggers:**
- "tell me about Stephansplatz"
- "what about this location"
- "show me just Karlsplatz"
- "this point called X"
- "that location named Y"

### 2. Location Name Extraction

Enhanced `parseFilterCriteria()` to extract location names from queries:

```javascript
// Pattern matching examples:
"show me Stephansplatz" → locationName: "Stephansplatz"
"tell me about Karlsplatz Station" → locationName: "Karlsplatz Station"
"what about the Opera House" → locationName: "Opera House"
```

**Extraction Patterns:**
1. `show me [location]`
2. `tell me about [location]`
3. `what about [location]`
4. `show just [location]`
5. `this/that point/location/place [called/named] [location]`

**Cleaning:**
- Removes articles: "the", "a", "an"
- Removes prepositions: "at", "in", "on"
- Trims whitespace
- Requires at least 3 characters

### 3. Location-Based Filtering

Enhanced `applyClientSideFilter()` to filter by location name:

```javascript
if (criteria.locationName) {
    const searchTerm = criteria.locationName.toLowerCase();
    filtered = filtered.filter(f => {
        const location = (f.location || f.name || '').toLowerCase();
        return location.includes(searchTerm);
    });
}
```

**Matching:**
- Case-insensitive substring match
- Checks both `f.location` and `f.name` fields
- Partial matching supported (e.g., "Stephans" matches "Stephansplatz")

### 4. Enhanced Response Display

Updated `generateFilterResponseMessage()` to show location criteria:

```
📍 Filtered Results
1 location (filtered from 100)
Location: Stephansplatz • Grade ≥ 80
```

## Examples

### Example 1: Query About Specific Location
```
User: "Show me movement points"
→ Backend returns 100 movement points

User: "Tell me about Stephansplatz"
→ Client-side filter: locationName = "Stephansplatz"
→ Filters from 100 → 1 point
→ Shows details about Stephansplatz only
```

### Example 2: Combine Location + Grade Filter
```
User: "Show me movement points"
→ Backend returns 100 movement points

User: "Tell me about Stephansplatz"
→ Filters to 1 point (Stephansplatz)

User: "Is it rated above 80?"
→ Filters from 1 point with grade filter
→ Either shows the point (if grade ≥ 80) or "No matches"
```

### Example 3: Location Then Top N
```
User: "Show me all beauty points"
→ Backend returns 150 beauty points

User: "Show me just Karlsplatz"
→ Filters to points with "Karlsplatz" in name
→ Might find "Karlsplatz Station", "Karlsplatz Plaza", etc.

User: "Top 1"
→ Shows highest-graded Karlsplatz location
```

## Query Patterns Supported

### Direct Location Queries
- ✅ "Tell me about Stephansplatz"
- ✅ "What about Karlsplatz Station"
- ✅ "Show me just the Opera House"
- ✅ "Show me Westbahnhof"

### Demonstrative Queries
- ✅ "This point"
- ✅ "That location"
- ✅ "This place called X"
- ✅ "That location named Y"

### Combined Queries
- ✅ "Show me Stephansplatz rated above 80"
- ✅ "Tell me about the top location"
- ✅ "What about the best point here"

## Behavior

### Progressive Filtering
Location filters stack with other filters:

```
100 points
  ↓ "above 80"
30 points
  ↓ "tell me about Stephansplatz"
1 point (Stephansplatz with grade ≥ 80)
```

### Partial Matching
Substring matching allows flexible queries:

```
Query: "Stephans"
Matches: "Stephansplatz", "Stephansdom", etc.

Query: "Train Station"
Matches: "Westbahnhof Train Station", "Central Train Station", etc.
```

### Multiple Matches
If multiple locations match, all are shown:

```
Query: "Karlsplatz"
Matches:
- Karlsplatz Station
- Karlsplatz Plaza
- Karlsplatz U-Bahn
(All 3 points displayed)
```

### No Matches
If location not found in current set:

```
📍 Filtered Results
No locations match your filter criteria.
Try adjusting your filter or zoom out to reset.
```

## Reset Behavior

Location filters are cleared when:
1. **Zoom changes** by >25%
2. **Category filter** button clicked
3. **Explicit reset** query (e.g., "reset", "show all")

## Benefits

1. ✅ **No Backend Overload**: Single-point queries handled client-side
2. ✅ **Instant Response**: No network delay for location filtering
3. ✅ **Progressive Filtering**: Location filters stack with grade/top-N filters
4. ✅ **Flexible Matching**: Partial substring matching for convenience
5. ✅ **Contextual**: Works on currently displayed points, not all data
6. ✅ **Consistent**: Same reset behavior as other client-side filters

## Technical Details

### Location Name Sources
```javascript
const location = f.location || f.name || 'Unknown'
```

Priority:
1. `f.location` (from Neo4j `p.location` field)
2. `f.name` (from Neo4j `p.name` field)
3. Fallback: 'Unknown'

### Case-Insensitive Matching
```javascript
const searchTerm = criteria.locationName.toLowerCase();
const location = (f.location || f.name || '').toLowerCase();
return location.includes(searchTerm);
```

Both search term and location name converted to lowercase for comparison.

### Criteria Display Order
```
Location: [name] • Grade ≥ [min] • Grade ≤ [max] • Top [N]
```

Location shown first when present, followed by other filters with bullet separators.

## Edge Cases Handled

### Empty Location Name
If extraction yields empty or <3 characters, location filter is ignored.

### Location Not in Current Dataset
If no points match the location, returns "No locations match" message.

### Location + No Other Filters
Works standalone - location filter can be the only criterion.

### Special Characters in Location Names
Location names with special characters (e.g., "St. Stephen's") are handled correctly.

## Debugging

Console logging added for troubleshooting:

```javascript
console.log(`Location filter "${criteria.locationName}": ${filtered.length} matches`);
```

Shows in browser console:
```
Location filter "Stephansplatz": 1 matches
Location filter "Karlsplatz": 3 matches
Location filter "Station": 15 matches
```

## Future Enhancements

Potential improvements:
- Fuzzy matching for misspellings
- Autocomplete suggestions while typing
- Click-on-map to select specific point
- "Near me" or proximity-based filtering
- Category + location combined queries to backend
