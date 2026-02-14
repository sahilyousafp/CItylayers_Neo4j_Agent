# Vegetation + CityLayers Test Cases

## Purpose
Verify multi-dataset integration with Vegetation (trees/green spaces) data.
Test species diversity analysis and green infrastructure insights.

---

## Test Case 4.1: Vegetation Data Retrieval

**Objective**: Verify tree data is fetched and displayed  
**Data Sources**: CityLayers + Vegetation  
**Steps**:
1. Enable Vegetation data source
2. Wait for tree markers to appear
3. Query: `"What trees are in this area?"`

**Expected Results**:
- Tree species listed in response
- Species diversity count shown
- Top 5-10 most common species
- Console shows vegetation data summarized

**Pass Criteria**:
- ✅ Species names in response
- ✅ Diversity count displayed
- ✅ Tree markers visible on map

---

## Test Case 4.2: Parks with Vegetation Analysis

**Objective**: Test cross-dataset analysis of parks and trees  
**Data Sources**: CityLayers + Vegetation  
**Query**: `"Parks with lots of trees"`

**Expected Results**:
- Parks from CityLayers shown
- Tree counts and species for those areas
- Example: "Stadtpark has 245 trees with 18 different species"
- Natural connection between park locations and vegetation data

**Pass Criteria**:
- ✅ Both parks and tree data mentioned
- ✅ Cross-referenced by location
- ✅ Species diversity highlighted

---

## Test Case 4.3: Species Diversity Query

**Objective**: Test vegetation-focused query  
**Data Sources**: CityLayers + Vegetation  
**Query**: `"What's the biodiversity like here?"`

**Expected Results**:
- Species diversity statistics
- List of tree species
- Total tree count
- Top species by abundance
- May reference green space places from CityLayers

**Pass Criteria**:
- ✅ Diversity metrics shown
- ✅ Species list provided
- ✅ Counts accurate

---

## Test Case 4.4: Activities Category + Vegetation

**Objective**: Test Activities category with green space data  
**Data Sources**: CityLayers + Vegetation  
**Steps**:
1. Select "Activities" category filter
2. Enable Vegetation
3. Query: `"Green spaces for outdoor activities"`

**Expected Results**:
- Activity places (parks, recreation) shown
- Tree/vegetation data for those locations
- Comments about outdoor activities prioritized
- Example: "5 parks with mature tree canopy ideal for picnics"

**Pass Criteria**:
- ✅ Both activity places and vegetation shown
- ✅ Relevant comments selected
- ✅ Natural language integration

---

## Test Case 4.5: Comment Relevance - Nature Focus

**Objective**: Verify nature-related comments prioritized  
**Data Sources**: CityLayers + Vegetation  
**Query**: `"Where are the greenest areas?"`

**Expected Results**:
- Comments mentioning:
  - Trees, nature, green spaces
  - Parks, gardens
  - Fresh air, shade
  - Natural beauty
- Vegetation stats complement comments

**Pass Criteria**:
- ✅ At least 3/5 comments mention nature
- ✅ Tree data supports the response
- ✅ Contextually relevant

---

## Test Case 4.6: Vegetation Visualization

**Objective**: Verify tree markers display correctly  
**Data Sources**: CityLayers + Vegetation  
**Steps**:
1. Enable Vegetation
2. Zoom to area with trees
3. Verify tree icons appear
4. Hover/click for species info

**Expected Results**:
- Tree markers visible as green icons
- Clustered appropriately at different zoom levels
- Species info accessible
- No performance issues with many trees

**Pass Criteria**:
- ✅ Trees render correctly
- ✅ Clustering works
- ✅ Species info available
- ✅ Smooth performance

---

## Test Case 4.7: Large Vegetation Dataset

**Objective**: Test performance with many trees  
**Data Sources**: CityLayers + Vegetation  
**Query**: `"Show all green spaces"` (area with 500+ trees)

**Expected Results**:
- Vegetation summarized for LLM (top species, totals)
- All trees visible on map
- Response within 10 seconds
- Species grouped and counted

**Pass Criteria**:
- ✅ Response < 10s
- ✅ Summary not overwhelming
- ✅ Map renders all trees

---

## Notes

- Vegetation data from Vienna Open Data (or similar)
- Includes species, location, trunk diameter, etc.
- Aggregated by species for LLM efficiency
- Useful for urban forestry and green infrastructure analysis
