# Testing Guide - Location Agent
**Last Updated:** December 1, 2025

---

## 🚀 Quick Start

### Start the Application:
```bash
cd "D:\CityLayers\Viz_Agent\Location Agent"
python app.py
```

### Access:
```
http://localhost:5000
```

---

## 🧪 Test Scenarios

### Test 1: Basic Area Query
**Query:** "Show me places in Vienna"  
**Category:** All  
**Expected:**
```markdown
### 📍 Vienna City Center

Found 523 locations across all categories in this area.

**Category Breakdown:**
- 🚶 Movement: 156 locations
- 🎨 Beauty: 145 locations
- 🔊 Sound: 89 locations
- 🛡️ Protection: 67 locations
- 🌡️ Climate Comfort: 45 locations
- 🎯 Activities: 21 locations
```

**Verify:**
- ✅ Points appear immediately on map
- ✅ No browser refresh needed
- ✅ Category breakdown shown
- ✅ No technical terms (place_id, etc.)
- ✅ No "Click pins" messages

---

### Test 2: Category Filter - Beauty
**Query:** "Show me Beauty locations"  
**Category:** Beauty (dropdown)  
**Expected:**
```markdown
### 🏷️ Beauty Locations

Found 145 Beauty locations in Vienna City Center. Beauty locations represent
aesthetically pleasing places including historic architecture, scenic viewpoints,
and well-designed public spaces.
```

**Verify:**
- ✅ Only Beauty category markers shown
- ✅ Category description included
- ✅ Count matches filtered results
- ✅ Map updates automatically

---

### Test 3: Specific Location by Coordinates
**Query:** "Tell me about the location at latitude 48.2082 and longitude 16.3738"  
**Expected:**
```markdown
### 📍 [Location Name]

**Location:** Full address
**Category:** Beauty ⭐ Grade: 9.2/10
**Type:** Historic Architecture

[Detailed description...]

#### Key Features:
- Feature 1
- Feature 2
```

**Verify:**
- ✅ Specific location found
- ✅ Detailed information shown
- ✅ Grade displayed if available
- ✅ Formatted sections (Overview, Key Features)
- ✅ No error messages

---

### Test 4: Specific Location by Name
**Query:** "Tell me about Stephansplatz"  
**Expected:**
```markdown
### 📍 Stephansplatz

**Location:** Stephansplatz 3, 1010 Vienna, Austria
**Category:** Beauty ⭐ Grade: 9.2/10

[300-500 word description]

#### Key Features:
- Gothic cathedral architecture
- Bustling pedestrian zone
- Central meeting point
```

**Verify:**
- ✅ Location found by name
- ✅ Comprehensive description
- ✅ Multiple sections
- ✅ 300-500 words of content

---

### Test 5: Empty Results
**Query:** "Show me places in Antarctica"  
**Expected:**
```markdown
### 🔍 No Locations Found

No locations were found matching your query.

**Suggestions:**
- Try zooming out to see a wider area
- Remove or change category filters
- Search for a different location name
```

**Verify:**
- ✅ Helpful error message
- ✅ Suggestions provided
- ✅ No crashes or stack traces
- ✅ User-friendly language

---

### Test 6: Map Bounds Query
**Steps:**
1. Pan/zoom map to specific area
2. Click "Show me places here"

**Expected:**
- ✅ Query includes map bounds
- ✅ Only locations in visible area returned
- ✅ Markers update immediately
- ✅ Count matches visible markers

**Verify Console:**
```
DEBUG: Map bounds included in query
MATCH (p:places)
WHERE p.latitude >= 48.19 AND p.latitude <= 48.23
  AND p.longitude >= 16.34 AND p.longitude <= 16.42
```

---

### Test 7: Category Filter + Map Bounds
**Steps:**
1. Select "Movement" category
2. Pan to specific area
3. Query: "Show me places"

**Expected:**
- ✅ Only Movement locations in visible area
- ✅ Both filters applied
- ✅ Count reflects both filters

**Verify Console:**
```
WHERE p.latitude >= ... AND p.longitude >= ...
  AND c.category_id = 3
```

---

### Test 8: Dark Mode Toggle
**Steps:**
1. Click dark mode button
2. Verify map colors change
3. Toggle buildings on/off
4. Switch back to light mode

**Verify:**
- ✅ Map tiles change to dark
- ✅ Markers remain visible
- ✅ No color bleeding between modes
- ✅ Buildings toggle works immediately
- ✅ Clean transition

---

### Test 9: Building Toggle
**Steps:**
1. Click "Toggle Buildings" button
2. Buildings should appear
3. Click again
4. Buildings should disappear

**Verify:**
- ✅ Works on first click
- ✅ No need to double-click
- ✅ State resets after theme change
- ✅ Smooth appearance/disappearance

---

### Test 10: Heatmap with Grades
**Steps:**
1. Select category with grades (Beauty, Movement)
2. Query: "Show me places"
3. Check heatmap visualization

**Verify:**
- ✅ Heatmap appears
- ✅ Intensity matches grades
- ✅ High grades = hot colors
- ✅ Low grades = cool colors
- ✅ No errors in console

---

## 🐛 Debug Checklist

### If Points Don't Appear:
```
1. Check console for errors
2. Verify data in Network tab
3. Check context_records count
4. Verify updateMarkers() called
5. Check map.invalidateSize()
```

### If Category Filter Fails:
```
1. Check generated Cypher in console
2. Verify WHERE clause includes category_id
3. Check category_filter parameter passed
4. Verify c:categories relationship exists
```

### If LLM Returns Raw Data:
```
1. Check QA_TEMPLATE formatting
2. Verify _prepare_context_summary() called
3. Check unwanted_patterns cleanup
4. Verify no JSON/dict in response
```

### If Coordinates Don't Work:
```
1. Check coordinate format (lat, lon)
2. Verify Cypher MATCH includes lat/lon
3. Check tolerance range (±0.001)
4. Verify p:places node has coordinates
```

---

## 📊 Performance Monitoring

### Query Times:
```
Fast: < 500ms
Normal: 500ms - 2s
Slow: > 2s
```

### Console Output:
```
⚡ GENERATED CYPHER:
[Cypher query shown]

📊 OUTPUT RECORDS: 156 records found

🤖 INPUT QUERY: Show me places in Vienna
```

### Watch For:
- ❌ Syntax errors in Cypher
- ❌ NoneType errors
- ❌ Timeout errors
- ❌ Empty results when data exists

---

## ✅ Acceptance Criteria

### Functionality:
- ✅ All query types work
- ✅ Map updates immediately
- ✅ Category filters applied
- ✅ Coordinates queries work
- ✅ Error handling graceful

### User Experience:
- ✅ Fast response times
- ✅ Informative answers
- ✅ No technical jargon
- ✅ Helpful error messages
- ✅ Smooth interactions

### Visual:
- ✅ Markers display correctly
- ✅ Dark mode works
- ✅ Buildings toggle works
- ✅ Heatmap shows grades
- ✅ Clean formatting

### Data Quality:
- ✅ Correct locations shown
- ✅ Categories accurate
- ✅ Grades displayed
- ✅ Counts match reality
- ✅ No duplicates

---

## 🔍 Common Issues

### Issue: "No data available"
**Cause:** Query returns 0 results  
**Check:**
- Map bounds too narrow
- Category filter too restrictive
- Spelling in location name
- Database connection

**Fix:**
- Zoom out map
- Remove filters
- Check spelling
- Verify Neo4j running

---

### Issue: Points show after refresh only
**Cause:** updateMarkers() not called  
**Check:**
- Response handling in app.js
- Map initialization timing
- Layer management

**Fix:**
```javascript
// After receiving data
updateMarkers(data.context_records);
map.invalidateSize();
```

---

### Issue: "Syntax error in Cypher"
**Cause:** Malformed query from LLM  
**Check:**
- Generated Cypher in console
- Dict/JSON extraction
- Markdown cleanup

**Fix:**
```python
# Ensure proper extraction
if isinstance(generated_cypher, dict):
    generated_cypher = generated_cypher['text']
generated_cypher = re.sub(r'```', '', generated_cypher)
```

---

### Issue: Category filter not working
**Cause:** WHERE clause in wrong position  
**Check:**
- Cypher query structure
- Category relationship exists
- Filter parameter passed

**Fix:**
```cypher
MATCH (p:places)
WHERE p.latitude >= ... AND c.category_id = 1  ← Must be here
OPTIONAL MATCH (p)<-[:ASSOCIATED_WITH]-(pg:place_grades)-[:OF_CATEGORY]->(c:categories)
```

---

## 📝 Test Log Template

```markdown
### Test Session: [Date]

**Environment:**
- OS: Windows
- Browser: Chrome/Edge
- Neo4j: Running
- Python: 3.x

**Tests Passed:**
- ✅ Test 1: Area query
- ✅ Test 2: Category filter
- ✅ Test 3: Coordinate query
- ✅ Test 4: Named location
- ✅ Test 5: Empty results
- ✅ Test 6: Map bounds
- ✅ Test 7: Combined filters
- ✅ Test 8: Dark mode
- ✅ Test 9: Buildings
- ✅ Test 10: Heatmap

**Issues Found:**
[None / List issues]

**Notes:**
[Any observations]

**Conclusion:**
✅ Ready for production / ❌ Needs fixes
```

---

## 🎯 Final Verification

Before marking as complete:

### Code Quality:
- ✅ No syntax errors
- ✅ No console warnings
- ✅ Proper error handling
- ✅ Clean code structure

### Functionality:
- ✅ All features working
- ✅ No regressions
- ✅ Edge cases handled
- ✅ Performance acceptable

### Documentation:
- ✅ All changes documented
- ✅ Examples provided
- ✅ Testing guide complete
- ✅ Known issues listed

### Deployment:
- ✅ Dependencies listed
- ✅ Configuration correct
- ✅ Environment variables set
- ✅ Ready to deploy

---

## 🚀 Ready to Launch!

If all tests pass:
1. ✅ Commit changes to version control
2. ✅ Tag release version
3. ✅ Deploy to production
4. ✅ Monitor for issues
5. ✅ Collect user feedback

**Good luck! 🎉**
