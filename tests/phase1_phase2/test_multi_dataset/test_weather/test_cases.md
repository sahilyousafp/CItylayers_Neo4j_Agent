# Weather + CityLayers Test Cases

## Purpose
Verify multi-dataset integration with Weather data source.
Test cross-dataset analysis and weather statistics display.

---

## Test Case 2.1: Weather Data Retrieval

**Objective**: Verify weather data is fetched and displayed  
**Data Sources**: CityLayers + Weather  
**Steps**:
1. Enable Weather data source (click weather button)
2. Wait for weather heatmap to load
3. Query: `"What's the weather like here?"`

**Expected Results**:
- Response includes temperature statistics
- Shows average, min, max temperature
- Wind speed and direction included
- Console shows:
  ```
  DEBUG: Aggregated context summary:
    - citylayers: X items
    - weather: Y items (400+ interpolated points)
  DEBUG: Processing multi-dataset query with 2 enabled sources
  ✅ Multi-dataset analysis complete
  ```

**Pass Criteria**:
- ✅ Weather statistics in response
- ✅ Temperature values realistic (°C)
- ✅ Both datasets shown in aggregated context

---

## Test Case 2.2: Cross-Dataset Query - Weather & Places

**Objective**: Test intelligent cross-dataset analysis  
**Data Sources**: CityLayers + Weather  
**Query**: `"Show me parks with good weather"`

**Expected Results**:
- Response mentions both parks (from CityLayers) and weather conditions
- LLM connects the two data sources naturally
- Example: "5 parks found with average temperature of 18°C"
- Weather stats included in response

**Pass Criteria**:
- ✅ Both parks and weather mentioned
- ✅ Natural language connection between datasets
- ✅ No awkward data dumps

---

## Test Case 2.3: Weather-Only Query

**Objective**: Test LLM can answer weather-only questions  
**Data Sources**: CityLayers + Weather  
**Query**: `"How warm is it?"`

**Expected Results**:
- Response focuses on weather data
- Temperature summary provided
- May mention CityLayers data if relevant, but not required
- Console shows weather data accessed

**Pass Criteria**:
- ✅ Temperature information displayed
- ✅ LLM correctly identifies weather as primary dataset
- ✅ Response is concise and relevant

---

## Test Case 2.4: Weather Context for Comments

**Objective**: Test if comments about weather/climate are prioritized  
**Data Sources**: CityLayers + Weather  
**Query**: `"Are there places with good shade?"`

**Expected Results**:
- Comments mentioning shade, sun, heat, coolness prioritized
- Weather data included if available
- Cross-reference between climate comfort category and weather

**Pass Criteria**:
- ✅ Comments relevant to climate/shade
- ✅ Weather stats complement the response
- ✅ Climate Comfort category places shown

---

## Test Case 2.5: Weather Heatmap Visualization

**Objective**: Verify weather data displays correctly on map  
**Data Sources**: CityLayers + Weather  
**Steps**:
1. Enable Weather data source
2. Verify weather heatmap appears
3. Hover over different areas
4. Check temperature panel updates

**Expected Results**:
- Weather heatmap visible on map
- Smooth temperature gradient
- Temperature panel shows hover value
- Average temperature displayed

**Pass Criteria**:
- ✅ Heatmap renders correctly
- ✅ Temperature values update on hover
- ✅ Panel shows wind speed/direction
- ✅ No visual glitches

---

## Test Case 2.6: Weather + Large CityLayers Dataset

**Objective**: Test performance with both datasets at scale  
**Data Sources**: CityLayers + Weather  
**Query**: `"Show all locations"` (with large map area)

**Expected Results**:
- Both datasets aggregated efficiently
- Weather summarized (not all 400 points sent to LLM)
- Response within 10 seconds
- No memory issues

**Pass Criteria**:
- ✅ Response time < 10s
- ✅ Weather data summarized (avg, min, max)
- ✅ No crashes or timeouts

---

## Test Case 2.7: Weather Data Toggle

**Objective**: Test enabling/disabling weather source  
**Data Sources**: CityLayers + Weather (toggle)  
**Steps**:
1. Enable Weather
2. Ask query: `"What's the temperature?"`
3. Disable Weather
4. Ask same query

**Expected Results**:
- With Weather: Temperature data shown
- Without Weather: Falls back to CityLayers only, or "no weather data available"
- Console shows datasets changing

**Pass Criteria**:
- ✅ Weather data only sent when enabled
- ✅ Graceful handling when disabled
- ✅ No errors on toggle

---

## Notes

- Weather data is interpolated grid (20x20 points)
- Based on Open-Meteo API center point
- Small random variation applied for natural appearance
- Aggregation summarizes to avg/min/max for LLM efficiency
