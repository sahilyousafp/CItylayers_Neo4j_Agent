# Phase 2.6 Testing: Mapbox Reverse Geocoding

**Status**: Ready to test  
**Date**: 2026-02-07

---

## 🚀 Quick Test Steps

### 1. Application Status
- Application should be running on http://localhost:5000
- Open your browser and navigate to the URL
- Open Developer Tools (F12) and go to Console tab

### 2. Test Query
Submit this query in the chat:
```
Show me beautiful places
```

### 3. Expected Console Output
Look for these DEBUG messages:
```
DEBUG: Enriching X unique locations with Mapbox addresses
DEBUG: Geocoding Y new locations (batch)
DEBUG: Geocoded (48.XXXX, 16.XXXX) -> [Street Address, Postcode City, Austria]...
DEBUG: Successfully enriched Z records with precise addresses
```

### 4. Expected Response
Check if the LLM response shows **precise addresses** like:
```
Sample Locations:
1. Stephansplatz 3, 1010 Vienna, Austria - Category: Beauty, Grade: 9.2
   💬 Top Comments:
      1. "Absolutely stunning architecture!"
```

**NOT** generic locations like:
```
1. Vienna, Austria - Category: Beauty, Grade: 9.2
```

---

## ✅ Pass Criteria

Phase 2.6 is working if:
- [ ] Console shows "DEBUG: Geocoding" messages
- [ ] Response contains precise street addresses
- [ ] No "Vienna, Austria" generic names
- [ ] Response time < 5 seconds
- [ ] No errors in console

---

## 🧪 Additional Tests

### Test 2: Cache Hit (Repeat Query)
- Submit the same query again
- Should be INSTANT (< 1 second)
- Console should show "All X locations found in cache"

### Test 3: Different Area
- Zoom/pan map to different location
- Submit query: "What's in this area?"
- Should show different precise addresses

---

## 📝 Report Results

**Test 1: Initial Query**
- Status: [ ] PASS [ ] FAIL
- Precise addresses shown: [ ] YES [ ] NO
- Response time: ___ seconds

**Test 2: Cache Hit**
- Status: [ ] PASS [ ] FAIL
- Instant response: [ ] YES [ ] NO

**Test 3: Different Area**
- Status: [ ] PASS [ ] FAIL
- New addresses geocoded: [ ] YES [ ] NO

---

## 🐛 If Something Fails

**No precise addresses showing:**
- Check if MAPBOX_ACCESS_TOKEN is set in .env
- Look for WARN messages in console
- Verify lat/lon coordinates in database

**Application won't start:**
- Check for Python errors
- Verify all dependencies installed
- Check if port 5000 is already in use

**Console errors:**
- Copy full error message
- Check if it's a Mapbox API error
- Verify network connectivity

---

## ✅ Once Testing Complete

If tests pass:
1. Mark Phase 2.6 as complete ✅
2. Update plan.md
3. **Proceed to Phase 3: PDF Export Implementation**

If tests fail:
1. Document the failure
2. Share console errors
3. Debug and fix issues
