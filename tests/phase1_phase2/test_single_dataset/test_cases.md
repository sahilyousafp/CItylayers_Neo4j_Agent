# Single Dataset Test Cases (CityLayers Only)

## Purpose
Establish baseline behavior with only CityLayers data source enabled.
Verify comment relevance scoring works with single dataset.

---

## Test Case 1.1: Basic Location Query

**Objective**: Verify standard location retrieval  
**Data Source**: CityLayers only  
**Query**: `"Show me beautiful places in Vienna"`

**Expected Results**:
- Response shows places from Neo4j database
- Places have Beauty category (category_id = 1)
- Locations displayed on map
- Console shows: "DEBUG: Applied comment relevance scoring to X records"

**Pass Criteria**:
- ✅ At least 1 place returned
- ✅ All places have valid lat/lon
- ✅ No errors in console

---

## Test Case 1.2: Comment Relevance - Beauty Query

**Objective**: Verify comments are contextually relevant to "beauty"  
**Data Source**: CityLayers only  
**Query**: `"What are the most beautiful locations?"`

**Expected Results**:
- Comments should mention:
  - Aesthetics (beautiful, stunning, gorgeous)
  - Architecture
  - Views/scenery
  - Visual appeal
- Comments should NOT just be from highest-rated places
- No rating numbers shown in comment display

**Pass Criteria**:
- ✅ At least 3/5 comments mention beauty-related keywords
- ✅ Comments are contextually relevant
- ✅ Relevance score applied (check console)

---

## Test Case 1.3: Comment Relevance - Safety Query

**Objective**: Verify comments match safety context  
**Data Source**: CityLayers only  
**Query**: `"Is this area safe?"`

**Expected Results**:
- Comments should mention:
  - Safety/security
  - Crime
  - Lighting
  - Police presence
  - Feeling secure/unsafe

**Pass Criteria**:
- ✅ At least 3/5 comments mention safety-related keywords
- ✅ Comments answer the safety question
- ✅ Not just generic positive reviews

---

## Test Case 1.4: Comment Relevance - Transport Query

**Objective**: Verify comments match transport/accessibility context  
**Data Source**: CityLayers only  
**Query**: `"How's the public transport in this area?"`

**Expected Results**:
- Comments should mention:
  - Transport/transit
  - Metro/train/bus
  - Accessibility
  - Walkability
  - Connections

**Pass Criteria**:
- ✅ At least 3/5 comments mention transport keywords
- ✅ Comments relevant to mobility/access
- ✅ Relevance scoring visible in console

---

## Test Case 1.5: Category Filter

**Objective**: Verify category filtering still works  
**Data Source**: CityLayers only  
**Steps**:
1. Select "Beauty" category from filter dropdown
2. Click "Filter" button
3. Ask query: `"Show me all locations"`

**Expected Results**:
- Only Beauty category places shown
- Map updates to show filtered results
- Response mentions Beauty category

**Pass Criteria**:
- ✅ All results have category_id = 1 (Beauty)
- ✅ Map markers filtered correctly
- ✅ Category filter persists

---

## Test Case 1.6: Large Result Set

**Objective**: Test performance with many results  
**Data Source**: CityLayers only  
**Query**: `"Show me all places in this region"` (with large map area)

**Expected Results**:
- Response within 10 seconds
- Aggregation limits applied (max 50 places in context)
- All places shown on map
- No crashes or timeouts

**Pass Criteria**:
- ✅ Response time < 10s
- ✅ No errors or crashes
- ✅ Map renders all points

---

## Test Case 1.7: Specific Location Query

**Objective**: Test single location retrieval  
**Data Source**: CityLayers only  
**Query**: `"Tell me about Stephansplatz"`

**Expected Results**:
- Single location details returned
- Quick facts table displayed
- Comments specific to Stephansplatz
- Description of what makes it special

**Pass Criteria**:
- ✅ Only Stephansplatz returned (or LIMIT 1 applied)
- ✅ Detailed information provided
- ✅ Comments are about Stephansplatz

---

## Notes

- This test suite establishes baseline before multi-dataset tests
- All tests should work exactly as before (regression check)
- Comment relevance is the NEW feature being validated
- Pay special attention to console logs for DEBUG messages
