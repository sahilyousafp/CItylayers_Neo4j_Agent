# Transport + CityLayers Test Cases

## Purpose
Verify multi-dataset integration with Transport (public transit) data.
Test cross-dataset analysis connecting places with transport access.

---

## Test Case 3.1: Transport Data Retrieval

**Objective**: Verify transport stations are fetched and displayed  
**Data Sources**: CityLayers + Transport  
**Steps**:
1. Enable Transport data source
2. Wait for transport markers to appear
3. Query: `"Where are the train stations?"`

**Expected Results**:
- Transport stations listed in response
- Station types shown (train, tram, bus)
- Stations visible as markers on map
- Console shows:
  ```
  DEBUG: Aggregated context summary:
    - citylayers: X items
    - transport: Y items
  ```

**Pass Criteria**:
- ✅ Transport stations in response
- ✅ Station types categorized
- ✅ Markers visible on map

---

## Test Case 3.2: Cross-Dataset Query - Accessibility

**Objective**: Test cross-dataset analysis for transport access  
**Data Sources**: CityLayers + Transport  
**Query**: `"Beautiful places near public transport"`

**Expected Results**:
- Response mentions both beauty locations AND transport stations
- Cross-references distances/proximity
- Example: "Stephansplatz has excellent transport access with 3 stations nearby"
- Intelligent connection between datasets

**Pass Criteria**:
- ✅ Both places and transport mentioned
- ✅ Proximity/access discussed
- ✅ Natural language connection

---

## Test Case 3.3: Movement Category + Transport

**Objective**: Test Movement category with transport data  
**Data Sources**: CityLayers + Transport  
**Steps**:
1. Select "Movement" category filter
2. Enable Transport
3. Query: `"Show mobility options in this area"`

**Expected Results**:
- Movement category places shown
- Transport stations included
- Cross-dataset analysis of mobility infrastructure
- Comments about accessibility prioritized

**Pass Criteria**:
- ✅ Movement places and transport stations both shown
- ✅ Comprehensive mobility picture
- ✅ Comments relevant to transport/accessibility

---

## Test Case 3.4: Transport Station Types

**Objective**: Verify different station types are distinguished  
**Data Sources**: CityLayers + Transport  
**Query**: `"What types of public transport are available?"`

**Expected Results**:
- Response lists train, tram, bus stations separately
- Counts for each type
- Example: "12 train stations, 18 tram stops, 25 bus stops"

**Pass Criteria**:
- ✅ Station types categorized
- ✅ Counts accurate
- ✅ All three types recognized

---

## Test Case 3.5: Comment Relevance - Transport Focus

**Objective**: Verify transport-related comments prioritized  
**Data Sources**: CityLayers + Transport  
**Query**: `"How's the accessibility here?"`

**Expected Results**:
- Comments mentioning:
  - Metro/train/bus access
  - Walkability
  - Transit connections
  - Ease of getting around
- Transport station data included

**Pass Criteria**:
- ✅ At least 3/5 comments mention transport
- ✅ Comments relevant to accessibility
- ✅ Transport stations complement response

---

## Test Case 3.6: Transport Visualization Filtering

**Objective**: Test transport type filtering  
**Data Sources**: CityLayers + Transport  
**Steps**:
1. Enable Transport
2. Open Transport tab in data panel
3. Click Train icon to toggle off trains
4. Verify map updates

**Expected Results**:
- Train stations hidden on map
- Tram and bus still visible
- Query responses still include all transport data
- Filter only affects visualization

**Pass Criteria**:
- ✅ Train markers hidden
- ✅ Other types still visible
- ✅ LLM still has access to all data

---

## Test Case 3.7: Large Transport Dataset

**Objective**: Test performance with many transport stations  
**Data Sources**: CityLayers + Transport  
**Query**: `"Show all locations and transport"` (large area)

**Expected Results**:
- Transport data limited to 30 stations in LLM context
- All stations visible on map
- Response time acceptable
- Aggregation by type in LLM context

**Pass Criteria**:
- ✅ Response < 10s
- ✅ Transport data summarized for LLM
- ✅ Map shows all stations

---

## Notes

- Transport data from OSM/Overpass API
- Fetched based on map viewport bounds
- Categorized as train, tram, bus
- Maximum 5km search radius
- Icons color-coded by type on map
