# Testing Guide: Multi-Dataset LLM Integration & Comment Relevance

**Branch**: `feature/multi-dataset-llm-pdf-export`  
**Testing Phase**: Phases 1-2 Complete  
**Date**: 2026-02-07

---

## Quick Start Testing

### 1. Start the Application
```bash
cd "D:\CityLayers\Viz_Agent\Location Agent"
git checkout feature/multi-dataset-llm-pdf-export
python app.py
```

Access at: `http://localhost:5000`

### 2. Open Browser Console
- Press F12 (Developer Tools)
- Go to "Console" tab
- Monitor for DEBUG messages

### 3. Enable Data Sources
Click the data source buttons in the bottom-right panel:
- 🏙️ **CityLayers** (always start enabled)
- 🌤️ **Weather**
- 🚉 **Transport**
- 🌳 **Vegetation**

---

## Test Scenarios

### Scenario 1: Baseline - Single Dataset
**Setup**: Only CityLayers enabled  
**Query**: `"Show me beautiful places in Vienna"`

**Expected Behavior**:
- Response shows places from Neo4j database
- Comments displayed WITHOUT ratings
- Comments relate to beauty/aesthetics
- Console shows: `"DEBUG: Applied comment relevance scoring to X records"`

**Pass Criteria**: ✅ Comments are contextually relevant to "beauty"

---

### Scenario 2: Weather + CityLayers
**Setup**: Enable CityLayers + Weather  
**Query**: `"What's the weather like in this area?"`

**Expected Behavior**:
- Response includes temperature statistics
- Shows average, min, max temperature
- Wind speed and direction included
- Console shows:
  ```
  DEBUG: Aggregated context summary:
    - citylayers: X items
    - weather: Y items
  DEBUG: Processing multi-dataset query with 2 enabled sources
  ✅ Multi-dataset analysis complete
  ```

**Pass Criteria**: ✅ Weather data displayed in response

---

### Scenario 3: Transport + CityLayers (Cross-Dataset)
**Setup**: Enable CityLayers + Transport  
**Query**: `"Beautiful places near public transport"`

**Expected Behavior**:
- Response mentions both beauty places AND transport stations
- Cross-dataset insights (e.g., "5 beautiful locations near train stations")
- Transport station types listed (train, tram, bus)
- Console shows both datasets in aggregated context

**Pass Criteria**: ✅ Response connects beauty locations with transport data

---

### Scenario 4: Vegetation + CityLayers
**Setup**: Enable CityLayers + Vegetation  
**Query**: `"Parks with lots of trees"`

**Expected Behavior**:
- Response mentions parks from CityLayers
- Includes tree/vegetation statistics
- Shows species diversity count
- Lists most common tree species
- Console shows vegetation data summarized

**Pass Criteria**: ✅ Tree species and counts mentioned in response

---

### Scenario 5: All Datasets (Complex Query)
**Setup**: Enable ALL 4 sources  
**Query**: `"Green spaces with good transport and nice weather"`

**Expected Behavior**:
- LLM intelligently selects relevant datasets (CityLayers, Transport, Weather, Vegetation)
- Response doesn't overwhelm with irrelevant data
- Cross-references multiple datasets naturally
- Console shows all 4 sources enabled
- Response coherent and focused

**Pass Criteria**: ✅ LLM uses appropriate datasets, response is clear

---

### Scenario 6: Comment Relevance by Topic

#### Test 6a: Safety Comments
**Query**: `"Is this area safe?"`  
**Expected**: Comments mention safety, crime, security, lighting

#### Test 6b: Beauty Comments
**Query**: `"What are the most beautiful locations?"`  
**Expected**: Comments mention aesthetics, views, architecture, stunning

#### Test 6c: Transport Comments
**Query**: `"How's the public transport here?"`  
**Expected**: Comments mention accessibility, transit, metro, bus, walkability

**Pass Criteria**: ✅ Comments match query topic, NOT just highest-rated places

---

### Scenario 7: Edge Cases

#### Test 7a: No Datasets Enabled
**Query**: Any query with all sources disabled  
**Expected**: Error message or graceful handling

#### Test 7b: Large Result Set
**Query**: Broad query returning 200+ places  
**Expected**: 
- Response within 10 seconds
- Aggregation limits applied (max 50 CityLayers records shown)
- No crashes or timeouts

#### Test 7c: No External Data
**Query**: With Weather/Transport enabled but no data loaded yet  
**Expected**: Falls back to CityLayers only, no errors

---

## Console Monitoring

### Expected DEBUG Messages

✅ **Good signs to see**:
```
DEBUG: Aggregated context summary:
  - citylayers: 45 items
  - weather: 400 items
  - transport: 23 items
  
DEBUG: Applied comment relevance scoring to 45 records

DEBUG: Processing multi-dataset query with 3 enabled sources

✅ Multi-dataset analysis complete
```

❌ **Problems to watch for**:
```
ERROR in multi-dataset processing: ...
ReferenceError: ... is not defined
TypeError: Cannot read property '...' of undefined
```

---

## Regression Tests

Verify existing features still work:

- [ ] Category filtering (Beauty, Sound, Movement, etc.)
- [ ] Visualization modes:
  - [ ] Map View (markers)
  - [ ] Scatter Plot
  - [ ] Heatmap
  - [ ] Arc Network
  - [ ] Choropleth
- [ ] Search places (Mapbox geocoding)
- [ ] Draw region on map
- [ ] Theme switching (light/dark)
- [ ] Panel resizing
- [ ] Clear map button
- [ ] Refresh map button

---

## Performance Benchmarks

| Metric | Target | Acceptable | Unacceptable |
|--------|--------|------------|--------------|
| Query Response Time | < 5s | < 10s | > 15s |
| Comment Scoring Time | < 1s | < 2s | > 3s |
| Frontend Payload Size | < 500KB | < 1MB | > 2MB |
| Browser Memory Usage | < 200MB | < 500MB | > 1GB |

---

## Troubleshooting

### Issue: Comments not contextually relevant
**Check**: 
- Console shows "DEBUG: Applied comment relevance scoring"
- Try different query keywords
- Verify comments exist in database

### Issue: Multi-dataset response missing data
**Check**:
- Data source button is highlighted (enabled)
- External data loaded on map (check weather heatmap, transport markers visible)
- Console shows dataset in aggregated context

### Issue: Slow response times
**Check**:
- Large result set? (> 100 places)
- Multiple datasets enabled with large payloads
- Solution: Limit map view area, filter by category

### Issue: Frontend errors
**Check**:
- Browser console for JavaScript errors
- Network tab for failed requests
- Verify all JS files loaded

---

## Test Results Template

```
## Test Session: [Date]

### Environment
- Branch: feature/multi-dataset-llm-pdf-export
- Python: [version]
- Browser: [name/version]
- Database: [record count]

### Tests Run
- [ ] Scenario 1: Baseline ✅ PASS / ❌ FAIL
- [ ] Scenario 2: Weather ✅ PASS / ❌ FAIL
- [ ] Scenario 3: Transport ✅ PASS / ❌ FAIL
- [ ] Scenario 4: Vegetation ✅ PASS / ❌ FAIL
- [ ] Scenario 5: All Datasets ✅ PASS / ❌ FAIL
- [ ] Scenario 6: Comment Relevance ✅ PASS / ❌ FAIL
- [ ] Scenario 7: Edge Cases ✅ PASS / ❌ FAIL
- [ ] Regression Tests ✅ PASS / ❌ FAIL

### Issues Found
1. [Description]
   - Severity: Critical / Major / Minor
   - Steps to reproduce: ...
   - Expected: ...
   - Actual: ...

2. ...

### Performance Notes
- Average query time: [X]s
- Largest result set tested: [N] records
- Memory usage: [X]MB

### Recommendations
- [ ] Ready for merge
- [ ] Needs fixes before merge
- [ ] Continue to Phase 3 (PDF Export)
```

---

## Next Steps After Testing

1. **If tests pass**: 
   - Merge to master
   - OR continue to Phase 3 (PDF Export)

2. **If issues found**: 
   - Document in GitHub issues
   - Fix critical bugs
   - Re-test

3. **Gather feedback**:
   - Test with real user queries
   - Validate comment relevance accuracy
   - Assess cross-dataset analysis quality
