# Comment Relevance Test Cases

## Purpose
Comprehensive validation of the comment relevance scoring system (Phase 2).
Verify contextual ranking works across different query types and topics.

---

## Test Case 6.1: Beauty Keywords

**Query**: `"What are the most beautiful places?"`

**Expected Comment Keywords**:
- beautiful, stunning, gorgeous, pretty
- architecture, design, aesthetic
- views, scenery, picturesque
- charming, elegant, impressive

**Relevance Validation**:
- At least 4/5 comments should contain beauty-related keywords
- Comments ranked by relevance score (check console logs)
- No rating numbers shown

**Pass Criteria**: ✅ High relevance to beauty/aesthetics

---

## Test Case 6.2: Safety Keywords

**Query**: `"Is this area safe at night?"`

**Expected Comment Keywords**:
- safe, safety, secure, security
- crime, dangerous, risky
- lighting, well-lit, dark
- police, patrol
- feel safe, feel unsafe

**Relevance Validation**:
- At least 4/5 comments discuss safety
- Comments about actual safety, not just general reviews
- Context-appropriate (night-time concerns if mentioned)

**Pass Criteria**: ✅ Directly addresses safety concerns

---

## Test Case 6.3: Transport/Accessibility Keywords

**Query**: `"How accessible is this location by public transport?"`

**Expected Comment Keywords**:
- transport, transit, metro, train, bus, tram
- accessible, accessibility
- walkable, pedestrian
- connections, easy to reach
- stations nearby

**Relevance Validation**:
- At least 4/5 comments mention transportation
- Focus on accessibility and connections
- Mobility-related content

**Pass Criteria**: ✅ Comments about transport access

---

## Test Case 6.4: Noise/Sound Keywords

**Query**: `"How noisy is this area?"`

**Expected Comment Keywords**:
- noisy, noise, loud, quiet
- peaceful, serene, calm
- traffic noise, crowds
- sound, acoustic
- busy, hectic vs tranquil

**Relevance Validation**:
- At least 3/5 comments discuss sound/noise levels
- Actual descriptions of noise, not just ambiance
- Helpful for understanding soundscape

**Pass Criteria**: ✅ Relevant to noise/sound levels

---

## Test Case 6.5: Activity/Recreation Keywords

**Query**: `"What activities can I do here?"`

**Expected Comment Keywords**:
- activities, things to do
- park, recreation, sports
- walking, jogging, cycling
- cafes, restaurants, shopping
- events, entertainment

**Relevance Validation**:
- Comments describe specific activities
- Actionable information
- Variety of activity types

**Pass Criteria**: ✅ Describes possible activities

---

## Test Case 6.6: Weather/Climate Keywords

**Query**: `"Is there good shade in summer?"`

**Expected Comment Keywords**:
- shade, shaded, shady
- hot, sun, sunny
- cool, cooling
- trees, canopy
- summer, warm

**Relevance Validation**:
- Comments about shade/sun conditions
- Climate comfort relevant
- Seasonal considerations if mentioned

**Pass Criteria**: ✅ Addresses climate/shade

---

## Test Case 6.7: Mixed Keywords Test

**Query**: `"Beautiful parks that are safe and quiet"`

**Expected Comment Keywords**:
- Combination of:
  - Beauty: beautiful, nice, scenic
  - Safety: safe, secure
  - Sound: quiet, peaceful, calm
  - Green: park, green, trees

**Relevance Validation**:
- Comments touch on multiple topics
- Balanced across the three themes
- Most relevant comments rank higher

**Pass Criteria**: ✅ Multi-topic relevance

---

## Test Case 6.8: Generic Query (Baseline)

**Query**: `"Tell me about this area"`

**Expected Behavior**:
- Without specific keywords, relevance scoring is less important
- Comments should still be diverse
- Not dominated by single topic
- General insights about the area

**Pass Criteria**: ✅ Diverse comment selection

---

## Test Case 6.9: Keyword Not in Comments

**Query**: `"Are there any electric vehicle charging stations?"`

**Expected Behavior**:
- If no comments mention EV/charging, scores will be low
- May return comments about transport/accessibility as next best
- Graceful handling of no exact matches
- Response may say "no specific comments about EV charging"

**Pass Criteria**: ✅ Graceful handling, no errors

---

## Test Case 6.10: Console Log Validation

**Objective**: Verify comment scoring debug output

**Check Console for**:
```
DEBUG: Applied comment relevance scoring to X records
```

**Validation**:
- Message appears for every query
- X matches number of places with comments
- No errors during scoring process

**Pass Criteria**: ✅ Scoring executes without errors

---

## Scoring Algorithm Verification

### Check Scoring Logic:
1. **Keyword Extraction**:
   - Stop words removed (the, and, or, is, etc.)
   - Only words >2 characters
   - Case-insensitive matching

2. **Scoring Components**:
   - Base: 1.0 per keyword found
   - Bonus: +0.5 for keyword in first 50 chars
   - Bonus: +0.3 for long keywords (>4 chars)

3. **Normalization**:
   - Score divided by max possible (keywords × 1.8)
   - Result between 0.0 and 1.0

### Manual Validation Test:
**Query**: "beautiful architecture"  
**Keywords**: [beautiful, architecture]  
**Comment**: "Beautiful historic architecture in the city center"

**Expected Score Calculation**:
- "beautiful" found: 1.0
- "beautiful" in first 50 chars: +0.5
- "beautiful" >4 chars: +0.3
- "architecture" found: 1.0
- "architecture" >4 chars: +0.3
- Total: 3.1
- Max possible: 2 × 1.8 = 3.6
- **Score: 3.1/3.6 = 0.86**

---

## Pass/Fail Criteria Summary

**Overall Pass Requires**:
- ✅ At least 7/10 test cases pass
- ✅ Console logs show scoring applied
- ✅ No errors during comment processing
- ✅ Comments are more relevant than random selection
- ✅ No rating numbers displayed

**Critical Failures (Immediate Fail)**:
- ❌ Console errors during scoring
- ❌ Comments completely unrelated to query
- ❌ Scoring not applied (console log missing)
- ❌ Crashes or exceptions

---

## Notes

- Comment relevance is the main Phase 2 feature
- Algorithm uses simple keyword matching (not semantic embeddings)
- Future enhancement: Use sentence transformers for semantic similarity
- Current implementation is lightweight and fast
- Suitable for real-time query responses
