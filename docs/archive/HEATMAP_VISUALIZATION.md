# Heatmap Visualization Guide

## Overview
The heatmap visualization displays location data using color gradients based on grade values (1-100 scale). This provides an intuitive way to identify high and low-performing areas at a glance.

## Features

### 1. Grade-Based Coloring
- **Scale**: 1-100 (grades stored as 1-10 internally, displayed as 10-100)
- **Color Scheme**:
  - **10-30**: Dark Blue → Royal Blue (Very Low)
  - **30-50**: Royal Blue → Sky Blue (Low)
  - **50-70**: Sky Blue → Yellow (Medium)
  - **70-85**: Yellow → Orange (Good)
  - **85-100**: Orange → Crimson (Very Good)
  - **100**: Crimson (Excellent)

### 2. Dynamic Legend
The legend automatically adapts to your data:
- Shows only relevant grade ranges present in the data
- Displays Min, Avg, and Max statistics
- Updates when switching categories or filtering data

### 3. Visualization Parameters
```javascript
radiusPixels: 100      // Broader radius for smooth transitions
intensity: 1.2         // Balanced color intensity
threshold: 0.03        // Gradient detail level
aggregation: 'MEAN'    // Averages overlapping points
```

### 4. Overlay on 3D Buildings
The heatmap renders on top of 3D buildings for clear visibility.

## Usage

### Viewing the Heatmap
1. Click the heatmap icon in the visualization options
2. Select a category from the filter dropdown
3. Click "Filter" to apply
4. Zoom in/out to see the gradient adjust

### Interpreting Colors
- **Cool colors (Blue)**: Low grades, areas needing improvement
- **Warm colors (Yellow/Orange)**: Good to very good grades
- **Hot colors (Red/Crimson)**: Excellent grades

### Best Practices
- Use heatmap for **overall area assessment**
- Zoom out to see **regional patterns**
- Zoom in for **localized details**
- Compare different categories by switching filters

## Technical Details

### Data Processing
1. Filters locations by selected category
2. Extracts grade values (handles multiple field names)
3. Calculates statistics (min, avg, max)
4. Normalizes grades to 0-1 range for weighting
5. Applies mean aggregation for overlapping points

### Performance
- Efficient rendering with deck.gl HeatmapLayer
- Dynamic updates only when zooming (not panning)
- Optimized for large datasets

## Troubleshooting

### No heatmap visible
- Check that locations have valid grade values
- Ensure category filter matches your data
- Verify you're in heatmap view mode (icon should be highlighted)

### Colors look wrong
- Legend shows the actual data range - if all your data is 70-90, only those colors appear
- This is intentional - ensures accurate representation

### Legend shows "No Data"
- No locations match the current category filter
- Try selecting a different category or "All Categories"

## Related Documentation
- See `static/js/app.js` - `createHeatmapLayer()` function
- Color schemes defined in `CATEGORY_COLORS` constant
- Visualization modes handled in `updateDeckLayers()` function
