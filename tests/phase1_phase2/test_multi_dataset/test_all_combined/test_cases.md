# All Datasets Combined Test Cases

## Purpose
Test complex cross-dataset queries with all 4 sources enabled simultaneously.
Verify LLM can intelligently select and integrate relevant datasets.

---

## Test Case 5.1: Complex Cross-Dataset Query

**Objective**: Test LLM with all data sources available  
**Data Sources**: ALL (CityLayers + Weather + Transport + Vegetation)  
**Query**: `"Green spaces with good transport and nice weather"`

**Expected Results**:
- LLM identifies relevant datasets: CityLayers (parks), Transport (access), Weather (conditions), Vegetation (greenery)
- Response integrates all three naturally
- Example: "Stadtpark features 245 trees, temperature 18°C, 3 metro stations within 500m"
- Console shows all 4 datasets in aggregated context

**Pass Criteria**:
- ✅ All relevant datasets mentioned
- ✅ Natural language integration
- ✅ Response coherent, not overwhelming
- ✅ Prioritizes relevant data

---

## Test Case 5.2: Dataset Prioritization

**Objective**: Verify LLM selects appropriate datasets  
**Data Sources**: ALL  
**Query**: `"What's the temperature?"`

**Expected Results**:
- LLM focuses primarily on Weather data
- May briefly mention CityLayers context (location names)
- Doesn't force-fit Transport or Vegetation unnecessarily
- Intelligent selection

**Pass Criteria**:
- ✅ Weather data primary in response
- ✅ Other datasets not forced
- ✅ Concise and relevant

---

## Test Case 5.3: Urban Quality Assessment

**Objective**: Test comprehensive urban analysis  
**Data Sources**: ALL  
**Query**: `"What makes this a good neighborhood?"`

**Expected Results**:
- Multi-faceted response considering:
  - Beauty/aesthetics (CityLayers)
  - Transport access (Transport)
  - Green spaces (Vegetation)
  - Climate comfort (Weather)
- Comments from multiple categories
- Holistic neighborhood picture

**Pass Criteria**:
- ✅ Multiple datasets contribute
- ✅ Balanced analysis
- ✅ Useful for policy decisions

---

## Test Case 5.4: Performance with All Datasets

**Objective**: Test response time with maximum data  
**Data Sources**: ALL  
**Query**: `"Analyze this area"` (broad query, large map area)

**Expected Results**:
- Response within 15 seconds (acceptable with all datasets)
- All data sources summarized appropriately
- No memory issues or crashes
- Aggregation limits working

**Pass Criteria**:
- ✅ Response < 15s
- ✅ No crashes/timeouts
- ✅ Data summarization effective
- ✅ Browser memory < 500MB

---

## Test Case 5.5: Sequential Dataset Enablement

**Objective**: Test enabling datasets one by one  
**Data Sources**: Start with CityLayers, add others sequentially  
**Steps**:
1. Query with only CityLayers
2. Enable Weather, query again
3. Enable Transport, query again
4. Enable Vegetation, query again
5. Same query each time: `"Describe this area"`

**Expected Results**:
- Response evolves with each dataset
- First: basic place info
- +Weather: adds temperature
- +Transport: adds accessibility
- +Vegetation: adds green infrastructure
- No errors at any step

**Pass Criteria**:
- ✅ Each addition enhances response
- ✅ No errors or conflicts
- ✅ Smooth integration

---

## Test Case 5.6: All Datasets + Category Filter

**Objective**: Test category filtering with multi-dataset  
**Data Sources**: ALL  
**Steps**:
1. Select "Beauty" category
2. Enable all 4 datasets
3. Query: `"Beautiful places with good conditions"`

**Expected Results**:
- Only Beauty category places shown
- Weather, Transport, Vegetation still provide context
- Example: "Beautiful Stephansplatz with 18°C weather and metro access"
- Category filter respected

**Pass Criteria**:
- ✅ Only Beauty places returned
- ✅ Other datasets add context
- ✅ Filter works with multi-dataset

---

## Test Case 5.7: Data Source Toggle Stress Test

**Objective**: Test rapidly toggling datasets on/off  
**Data Sources**: ALL (toggle rapidly)  
**Steps**:
1. Enable all 4 datasets
2. Rapidly click dataset buttons on/off
3. Send query during toggles
4. Verify stability

**Expected Results**:
- Application remains stable
- Query uses whatever datasets are enabled at send time
- No race conditions or errors
- Graceful handling

**Pass Criteria**:
- ✅ No crashes
- ✅ No console errors
- ✅ Correct datasets used

---

## Test Case 5.8: Policy-Relevant Query

**Objective**: Test real-world policymaker use case  
**Data Sources**: ALL  
**Query**: `"What infrastructure improvements would benefit this area?"`

**Expected Results**:
- Comprehensive analysis using all datasets:
  - Current amenities (CityLayers)
  - Transport gaps (Transport)
  - Green space needs (Vegetation)
  - Climate considerations (Weather)
- Actionable insights
- Suitable for policy report

**Pass Criteria**:
- ✅ Multi-dataset analysis
- ✅ Actionable recommendations
- ✅ Professional tone
- ✅ Useful for decision-making

---

## Notes

- This is the most complex testing scenario
- Tests LLM's ability to synthesize multiple data sources
- Critical for policymaker use case
- Should not be overwhelming or confusing
- Validates the entire Phase 1 implementation
