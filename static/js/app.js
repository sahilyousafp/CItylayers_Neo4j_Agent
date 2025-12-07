/**
 * ============================================================================
 * CITY LAYERS - MAP VISUALIZATION APPLICATION
 * ============================================================================
 * 
 * A web application for visualizing location data with multiple visualization
 * modes including heatmaps, scatter plots, arc connections, and choropleth maps.
 * 
 * Key Features:
 * - Interactive map with Mapbox GL JS
 * - Multiple visualization modes using deck.gl
 * - Category-based filtering
 * - Grade-based heatmap visualization (1-100 scale)
 * - Chat interface for querying location data
 * - Region selection with polygon drawing
 * - 3D building visualization
 * - Theme switching (light/dark mode)
 * 
 * @version 2.0.0
 * @date 2025-12-01
 * ============================================================================
 */

(function () {
    'use strict';

    // ========================================================================
    // DOM ELEMENT REFERENCES
    // ========================================================================
    
    const chatForm = document.getElementById("chatForm");
    const chatInput = document.getElementById("chatInput");
    const chatWindow = document.getElementById("chatWindow");
    const scrollBottomBtn = document.getElementById("scrollBottomBtn");
    const sourceCityLayers = document.getElementById("source-citylayers");
    const sourceWeather = document.getElementById("source-weather");
    const expandBtn = document.getElementById("expandBtn");
    const leftContainer = document.querySelector(".left-container");
    const resizeHandle = document.querySelector(".resize-handle");
    const refreshMapBtn = document.getElementById("refreshMapBtn");
    const clearMapBtn = document.getElementById("clearMapBtn");
    const tiltMapBtn = document.getElementById("tiltMapBtn");
    const overlayPanel = document.getElementById("map-overlay-panel");
    const overlayCategory = document.getElementById("overlay-category");
    const overlayLegend = document.getElementById("overlay-legend");
    const placeSearchInput = document.getElementById("placeSearchInput");
    const searchResults = document.getElementById("searchResults");
    const clearSearchBtn = document.getElementById("clearSearchBtn");
    const categorySelect = document.getElementById("categorySelect");
    const temperaturePanel = document.getElementById("temperaturePanel");
    const temperatureValue = temperaturePanel?.querySelector(".temperature-value");
    const temperatureHoverInfo = temperaturePanel?.querySelector(".temperature-hover-info");

    // ========================================================================
    // STATE VARIABLES
    // ========================================================================

    let currentVizMode = "mapbox"; // Current visualization mode
    let cityLayersEnabled = true; // Data source toggle
    let weatherEnabled = false; // Weather heatmap toggle
    let isResizing = false; // Panel resize state
    let isTiltActive = false; // 3D tilt state
    let searchMarker = null; // Active search marker
    let drawnRegionBounds = null; // Polygon selection bounds
    let weatherHeatmapData = []; // Weather data points

    // ========================================================================
    // CATEGORY CONFIGURATION
    // ========================================================================
    
    const PREDEFINED_CATEGORIES = ['Beauty', 'Activities', 'Sound', 'Protection', 'Movement', 'Views', 'Climate Comfort'];
    
    const CATEGORY_ID_MAPPING = {
        1: 'Beauty',
        2: 'Sound',
        3: 'Movement',
        4: 'Protection',
        5: 'Climate Comfort',
        6: 'Activities'
    };
    
    const CATEGORY_NAME_TO_ID = Object.fromEntries(
        Object.entries(CATEGORY_ID_MAPPING).map(([k, v]) => [v, parseInt(k)])
    );

    let currentCategory = 'all'; // Active category filter
    let allCategories = new Map(); // Category counts
    
    // ========================================================================
    // HELPER FUNCTIONS
    // ========================================================================
    
    /**
     * Get the current active bounds (drawn region or viewport)
     * @returns {Object} Bounds object with north, south, east, west
     */
    function getActiveBounds() {
        if (drawnRegionBounds) {
            return drawnRegionBounds;
        } else {
            // Use current map viewport bounds
            const bounds = map.getBounds();
            return {
                north: bounds.getNorth(),
                south: bounds.getSouth(),
                east: bounds.getEast(),
                west: bounds.getWest()
            };
        }
    }

    // ========================================================================
    // COLOR SCHEMES
    // ========================================================================
    
    /**
     * Category color mapping for visualizations
     */
    const CATEGORY_COLORS = {
        'Beauty': [255, 105, 180],          // Pink
        'Activities': [255, 165, 0],        // Orange
        'Sound': [138, 43, 226],            // Purple
        'Protection': [220, 20, 60],        // Crimson
        'Movement': [30, 144, 255],         // Dodger Blue
        'Views': [50, 205, 50],             // Lime Green
        'Climate Comfort': [64, 224, 208],  // Turquoise
        'Uncategorized': [128, 128, 128]    // Gray
    };

    /**
     * Category-specific visualization configurations
     * Note: Protection category uses inverse weighting (low grade = high priority)
     */
    const CATEGORY_VISUALIZATION_CONFIG = {
        'Protection': {
            getWeight: d => {
                const grade = d.grade ? parseFloat(d.grade) : 5;
                return Math.max(0.1, (11 - grade) / 10);
            },
            colorRange: [
                [255, 255, 204], // Light Yellow
                [255, 237, 160],
                [254, 178, 76],
                [253, 141, 60],
                [227, 26, 28],   // Red
                [189, 0, 38]     // Dark Red
            ]
        },
        'default': {
            // Standard weighting: High grade = High weight
            getWeight: d => {
                const grade = d.grade ? parseFloat(d.grade) : 5;
                return Math.max(0.1, grade / 10);
            },
            // Standard Green-Red gradient (Red=Low, Green=High)
            colorRange: [
                [231, 76, 60],      // Red - Low grade
                [230, 126, 34],
                [241, 196, 15],
                [52, 152, 219],
                [46, 204, 113],     // Green - High grade
                [0, 255, 0]         // Bright Green - Very High
            ]
        }
    };

    // Mapbox access token
    mapboxgl.accessToken = window.MAPBOX_TOKEN;

    // Persistent map state - Default to Vienna, Austria
    let mapState = {
        center: [48.2082, 16.3738], // Vienna coordinates [lat, lon]
        zoom: 12,
        pitch: 0,
        bearing: 0,
        features: [],
        boundaries: [], // For chloropleth
        shouldUpdateData: false,
        isDrawingMode: false
    };

    // Standard Mapbox Styles
    const LIGHT_STYLE = 'mapbox://styles/mapbox/light-v11';
    const DARK_STYLE = 'mapbox://styles/mapbox/dark-v11';

    let currentTheme = 'light'; // 'light' or 'dark'

    // Initialize Mapbox Map with Light Style
    const map = new mapboxgl.Map({
        container: 'map',
        style: LIGHT_STYLE,
        center: [mapState.center[1], mapState.center[0]], // [lon, lat]
        zoom: mapState.zoom,
        pitch: mapState.pitch,
        bearing: mapState.bearing,
        projection: 'mercator', // Force 2D plan view
        antialias: true
    });

    // Theme Toggle Logic
    function toggleTheme() {
        const checkbox = document.getElementById('themeToggleCheckbox');
        currentTheme = checkbox.checked ? 'dark' : 'light';
        const newStyle = currentTheme === 'light' ? LIGHT_STYLE : DARK_STYLE;
        
        console.log(`Switching to ${currentTheme} theme`);
        
        // Save current state
        const center = map.getCenter();
        const zoom = map.getZoom();
        const pitch = map.getPitch();
        const bearing = map.getBearing();
        
        // Remove all deck.gl layers before style change
        if (deckOverlay) {
            deckOverlay.setProps({ layers: [] });
        }
        
        // Remove all Mapbox markers
        mapboxMarkers.forEach(m => m.remove());
        mapboxMarkers = [];

        map.setStyle(newStyle);
        
        // Restore state after style loads
        map.once('style.load', () => {
            console.log(`${currentTheme} theme loaded`);
            
            // Restore view
            map.jumpTo({
                center: [center.lng, center.lat],
                zoom: zoom,
                pitch: pitch,
                bearing: bearing
            });
            
            // Reapply custom layers (3D buildings, etc.)
            customizeMapLayers();
            
            // Restore deck.gl visualization
            updateDeckLayers();
            
            // Restore markers if in mapbox mode
            if (currentVizMode === 'mapbox') {
                renderMapboxMarkers();
            }
        });
    }
    
    // Expose toggle function globally if needed, or attach listener later
    window.toggleTheme = toggleTheme;

    let buildingsVisible = true; // Track building visibility

    // Customize Map Layers (3D Buildings & POI Filtering)
    function customizeMapLayers() {
        // 1. Add 3D Buildings
        if (!map.getLayer('add-3d-buildings')) {
            const layers = map.getStyle().layers;
            const labelLayerId = layers.find(
                (layer) => layer.type === 'symbol' && layer.layout['text-field']
            )?.id;

            map.addLayer(
                {
                    'id': 'add-3d-buildings',
                    'source': 'composite',
                    'source-layer': 'building',
                    'filter': ['==', 'extrude', 'true'],
                    'type': 'fill-extrusion',
                    'minzoom': 13,
                    'paint': {
                        'fill-extrusion-color': currentTheme === 'light' ? '#aaa' : '#555',
                        'fill-extrusion-height': [
                            'interpolate',
                            ['linear'],
                            ['zoom'],
                            13,
                            0,
                            13.05,
                            ['get', 'height']
                        ],
                        'fill-extrusion-base': [
                            'interpolate',
                            ['linear'],
                            ['zoom'],
                            13,
                            0,
                            13.05,
                            ['get', 'min_height']
                        ],
                        'fill-extrusion-opacity': 0.6
                    }
                },
                labelLayerId
            );
            
            // Apply current visibility state
            map.setLayoutProperty('add-3d-buildings', 'visibility', buildingsVisible ? 'visible' : 'none');
        } else {
            // Update existing layer color based on theme
            map.setPaintProperty('add-3d-buildings', 'fill-extrusion-color', currentTheme === 'light' ? '#aaa' : '#555');
            
            // Re-apply visibility state
            map.setLayoutProperty('add-3d-buildings', 'visibility', buildingsVisible ? 'visible' : 'none');
        }

        // 2. Customize water and greenery colors
        if (currentTheme === 'light') {
            // Muted water color
            if (map.getLayer('water')) {
                map.setPaintProperty('water', 'fill-color', '#b8d4e3');
            }
            // Muted park/greenery colors
            if (map.getLayer('landuse')) {
                map.setPaintProperty('landuse', 'fill-color', [
                    'match',
                    ['get', 'class'],
                    'park', '#c8e6c9',
                    'pitch', '#d4e8d4',
                    'grass', '#d4e8d4',
                    'wood', '#b8d4b8',
                    'scrub', '#c8dcc8',
                    '#ddd' // default
                ]);
            }
        } else {
            // Explicit dark mode colors (shades of grey)
            if (map.getLayer('water')) {
                map.setPaintProperty('water', 'fill-color', '#2c2c2c'); // Dark grey for water
            }
            if (map.getLayer('landuse')) {
                map.setPaintProperty('landuse', 'fill-color', [
                    'match',
                    ['get', 'class'],
                    'park', '#3a3a3a', // Darker grey for parks
                    'pitch', '#3a3a3a',
                    'grass', '#3a3a3a',
                    'wood', '#2a2a2a',
                    'scrub', '#303030',
                    '#222222' // default dark grey
                ]);
            }
        }

        // 3. Filter POIs to hide commercial infrastructures
        if (map.getLayer('poi-label')) {
            // Exclude commercial categories
            const commercialCategories = [
                'shop',
                'food_and_drink',
                'commercial_service',
                'lodging',
                'grocery',
                'clothing_store',
                'alcohol_shop',
                'restaurant',
                'bar',
                'cafe',
                'fast_food',
                'laundry',
                'bank',
                'atm'
            ];
            
            map.setFilter('poi-label', [
                '!',
                ['match', ['get', 'class'], commercialCategories, true, false]
            ]);
        }
    }

    // Toggle Buildings Visibility
    function toggleBuildings() {
        const checkbox = document.getElementById('buildingsToggleCheckbox');
        buildingsVisible = checkbox.checked;
        
        console.log(`Buildings ${buildingsVisible ? 'enabled' : 'disabled'}`);
        
        if (map.getLayer('add-3d-buildings')) {
            map.setLayoutProperty(
                'add-3d-buildings',
                'visibility',
                buildingsVisible ? 'visible' : 'none'
            );
        } else {
            console.warn('Buildings layer not found, will be applied on next style load');
        }
    }
    
    window.toggleBuildings = toggleBuildings;

    // Initialize deck.gl
    const deckOverlay = new deck.MapboxOverlay({
        interleaved: false,
        layers: []
    });
    map.addControl(deckOverlay);

    // Helper to add 3D buildings
    function add3DBuildingsLayer() {
        if (map.getLayer('add-3d-buildings')) return;

        const layers = map.getStyle().layers;
        const labelLayerId = layers.find(
            (layer) => layer.type === 'symbol' && layer.layout['text-field']
        )?.id;

        map.addLayer(
            {
                'id': 'add-3d-buildings',
                'source': 'composite',
                'source-layer': 'building',
                'filter': ['==', 'extrude', 'true'],
                'type': 'fill-extrusion',
                'minzoom': 13,
                'paint': {
                    'fill-extrusion-color': '#aaa',
                    'fill-extrusion-height': [
                        'interpolate',
                        ['linear'],
                        ['zoom'],
                        13,
                        0,
                        13.05,
                        ['get', 'height']
                    ],
                    'fill-extrusion-base': [
                        'interpolate',
                        ['linear'],
                        ['zoom'],
                        13,
                        0,
                        13.05,
                        ['get', 'min_height']
                    ],
                    'fill-extrusion-opacity': 0.6
                }
            },
            labelLayerId
        );
    }

    // ========================================================================
    // MAP EVENT HANDLERS
    // ========================================================================
    
    /**
     * Handle map style load events
     * Applies custom layers and updates visualizations
     */
    map.on('style.load', () => {
        customizeMapLayers();
        updateDeckLayers();
    });

    /**
     * Initialize map and drawing controls
     */
    map.on('load', () => {
        initDrawControl();
    });

    /**
     * Update visualizations on map movement/zoom
     * Heatmap and choropleth update dynamically with zoom level
     */
    map.on('moveend', function () {
        const center = map.getCenter();
        mapState.center = [center.lat, center.lng];
        mapState.zoom = map.getZoom();
        mapState.pitch = map.getPitch();
        mapState.bearing = map.getBearing();

        // Update heatmap and choropleth visualizations on zoom change to update labels
        if ((currentVizMode === 'heatmap' || currentVizMode === 'chloropleth') && mapState.features.length > 0) {
            updateDeckLayers();
        }
    });

    // ========================================================================
    // DECK.GL VISUALIZATION LAYERS
    // ========================================================================
    
    /**
     * Update deck.gl visualization layers based on current mode
     * Handles all visualization types: scatter, heatmap, arc, choropleth
     */
    function updateDeckLayers() {
        const layers = [];
        
        // Add weather heatmap layer if weather is enabled
        if (weatherEnabled && weatherHeatmapData.length > 0) {
            layers.push(createWeatherHeatmapLayer());
        }
        
        // Filter data by active category
        const data = mapState.features.filter(f => {
            // Check if feature has category_ids
            if (f.category_ids && f.category_ids.length > 0) {
                return f.category_ids.includes(parseInt(currentCategory));
            }

            // Fallback for backward compatibility (if no IDs)
            const categories = f.categories || (f.category ? [f.category] : ['Uncategorized']);
            const targetCategoryName = CATEGORY_ID_MAPPING[parseInt(currentCategory)];

            if (!targetCategoryName) return false;

            return categories.some(cat => {
                const category = cat || 'Uncategorized';
                return category.toLowerCase() === targetCategoryName.toLowerCase();
            });
        });

        // Disable picking if we are in drawing mode to prevent interference
        const isDrawing = mapState.isDrawingMode;

        if (currentVizMode === 'scatter') {
            layers.push(createScatterLayer(data, isDrawing));
            
            // Dynamic legend for scatterplot
            const categoryCounts = data.reduce((counts, d) => {
                const category = d.category || 'Uncategorized';
                counts[category] = (counts[category] || 0) + 1;
                return counts;
            }, {});

            const sortedCategories = Object.entries(categoryCounts).sort((a, b) => b[1] - a[1]);
            const topCategories = sortedCategories.slice(0, 5);
            
            let legendItems = topCategories.map(([category, count]) => ({
                color: `rgb(${CATEGORY_COLORS[category].join(', ')})`,
                label: `${category} (${count})`
            }));

            if (sortedCategories.length > 5) {
                legendItems.push({
                    color: 'rgb(128, 128, 128)',
                    label: 'Other'
                });
            }
            
            updateOverlay("Locations by Category", legendItems);
        }
        else if (currentVizMode === 'heatmap') {
            const heatmapResult = createHeatmapLayer(data, isDrawing);
            layers.push(...heatmapResult.layers);
            
            // Use dynamic legend from heatmap function
            if (heatmapResult.legend) {
                updateOverlay(heatmapResult.legend.title, heatmapResult.legend.items);
            }
        }
        else if (currentVizMode === 'arc') {
            layers.push(...createArcLayers(data, isDrawing));
            updateOverlay("High-Grade Network (≥7)", [
                { color: "rgb(255, 105, 180)", label: "Beauty" },
                { color: "rgb(255, 165, 0)", label: "Activities" },
                { color: "rgb(138, 43, 226)", label: "Sound" },
                { color: "rgb(220, 20, 60)", label: "Protection" },
                { color: "rgb(30, 144, 255)", label: "Movement" },
                { color: "rgb(50, 205, 50)", label: "Views" },
                { color: "rgb(64, 224, 208)", label: "Climate Comfort" }
            ]);
        }
        else if (currentVizMode === 'chloropleth') {
            layers.push(...createChoroplethLayers(data, isDrawing));
            const zoom = map.getZoom();
            const zoomDesc = zoom < 9 ? 'Region' : zoom < 12 ? 'City' : zoom < 15 ? 'Neighborhood' : 'Street';
            updateOverlay(`${zoomDesc} Analysis (Zoom ${Math.round(zoom)})`, [
                { color: "rgb(46, 204, 113)", label: "Excellent (8-10)" },
                { color: "rgb(52, 152, 219)", label: "Good (6-8)" },
                { color: "rgb(241, 196, 15)", label: "Average (4-6)" },
                { color: "rgb(230, 126, 34)", label: "Below Avg (2-4)" },
                { color: "rgb(231, 76, 60)", label: "Poor (0-2)" }
            ]);
        }
        else {
            // Mapbox mode - no deck layers, just markers (handled separately)
            updateOverlay("Map View", []);
            renderMapboxMarkers();
        }

        deckOverlay.setProps({ layers });

        // Toggle overlay visibility
        if (currentVizMode === 'mapbox') {
            overlayPanel.classList.add('hidden');
        } else {
            overlayPanel.classList.remove('hidden');
        }
    }

    // ========================================================================
    // VISUALIZATION LAYER CREATORS
    // ========================================================================
    
    /**
     * Create scatter plot layer
     * @param {Array} data - Location data points
     * @param {boolean} isDrawing - Whether user is in drawing mode
     * @returns {deck.ScatterplotLayer} Scatter plot visualization layer
     */
    function createScatterLayer(data, isDrawing) {
        return new deck.ScatterplotLayer({
            id: 'scatter-layer',
            data: data,
            pickable: !isDrawing,
            opacity: 0.9,
            stroked: false,
            filled: true,
            radiusScale: 6,
            radiusMinPixels: 6,
            radiusMaxPixels: 30,
            lineWidthMinPixels: 0,
            getPosition: d => [d.lon, d.lat],
            getFillColor: d => {
                const category = d.category || 'Uncategorized';
                return CATEGORY_COLORS[category] || CATEGORY_COLORS['Uncategorized'];
            },
            getLineColor: [0, 0, 0, 0],
            onClick: info => showPopup(info)
        });
    }

    /**
     * Create grade-based heatmap layer with dynamic legend
     * @param {Array} data - Location data points with grades
     * @param {boolean} isDrawing - Whether user is in drawing mode
     * @returns {Object} Object containing layers array and legend configuration
     * 
     * Features:
     * - Grade-based color intensity (1-100 scale)
     * - Dynamic legend based on actual data range
     * - Mean aggregation for overlapping points
     * - Broader radius for smoother transitions
     */
    function createHeatmapLayer(data, isDrawing) {
        // Filter data based on current category
        let filteredData = data;
        if (currentCategory !== 'all') {
            filteredData = data.filter(d => {
                // Check ID first
                if (d.category_ids && d.category_ids.length > 0) {
                    return d.category_ids.includes(parseInt(currentCategory));
                }

                // Fallback
                const targetCategoryName = CATEGORY_ID_MAPPING[parseInt(currentCategory)];
                if (!targetCategoryName) return false;

                const categories = d.categories || (d.category ? [d.category] : ['Uncategorized']);
                return categories.some(c => (c || 'Uncategorized').toLowerCase() === targetCategoryName.toLowerCase());
            });
        }
        
        // Further filter to only include places with valid grades
        filteredData = filteredData.filter(d => {
            const gradeValue = d.grade || d['p.grade'] || d['place_grades'];
            const grade = parseFloat(gradeValue);
            return !isNaN(grade) && grade > 0;
        });

        if (!filteredData || filteredData.length === 0) {
            console.warn('No data with valid grades for heatmap');
            return {
                layers: [new deck.ScatterplotLayer({ id: 'empty-heatmap', data: [] })],
                legend: {
                    title: "Grade-Based Heatmap",
                    items: [{ color: "rgb(128, 128, 128)", label: "No Data" }]
                }
            };
        }
        
        // Calculate grade statistics for dynamic legend (convert to 100 scale)
        const grades = filteredData.map(d => {
            const gradeValue = d.grade || d['p.grade'] || d['place_grades'];
            return parseFloat(gradeValue);
        }).filter(g => !isNaN(g));
        
        const minGrade = Math.min(...grades);
        const maxGrade = Math.max(...grades);
        const avgGrade = grades.reduce((a, b) => a + b, 0) / grades.length;
        
        // Convert to 100 scale for display
        const minGrade100 = minGrade * 10;
        const maxGrade100 = maxGrade * 10;
        const avgGrade100 = avgGrade * 10;
        
        console.log(`Heatmap: Using ${filteredData.length} places with grades from ${minGrade.toFixed(1)} to ${maxGrade.toFixed(1)} (avg: ${avgGrade.toFixed(1)})`);

        const layers = [];
        const zoom = map.getZoom();
        
        // Define color scale based on actual data range (using 100 scale for legend)
        const colorStops = [
            { grade: 10, color: [26, 35, 126, 200], label: "Very Low" },
            { grade: 30, color: [65, 105, 225, 200], label: "Low" },
            { grade: 50, color: [0, 191, 255, 200], label: "Medium" },
            { grade: 70, color: [255, 255, 0, 200], label: "Good" },
            { grade: 85, color: [255, 140, 0, 200], label: "Very Good" },
            { grade: 100, color: [220, 20, 60, 200], label: "Excellent" }
        ];
        
        // Build dynamic legend based on actual grade range
        const legendItems = [];
        colorStops.forEach((stop, index) => {
            // Only show legend items that fall within or near the actual data range
            if (stop.grade >= minGrade100 - 10 && stop.grade <= maxGrade100 + 10) {
                const nextStop = colorStops[index + 1];
                let label;
                
                if (nextStop) {
                    label = `${stop.grade.toFixed(0)} - ${nextStop.grade.toFixed(0)} (${stop.label})`;
                } else {
                    label = `${stop.grade.toFixed(0)}+ (${stop.label})`;
                }
                
                legendItems.push({
                    color: `rgba(${stop.color[0]}, ${stop.color[1]}, ${stop.color[2]}, ${stop.color[3] / 255})`,
                    label: label
                });
            }
        });
        
        // Add data statistics to legend
        const categoryName = currentCategory !== 'all' ? CATEGORY_ID_MAPPING[parseInt(currentCategory)] : 'All Categories';
        const legendTitle = `${categoryName} Heatmap (${filteredData.length} locations)`;
        
        // Use HeatmapLayer from deck.gl aggregation layers
        const {HeatmapLayer, TextLayer} = deck;
        
        layers.push(new HeatmapLayer({
            id: 'heatmap-layer',
            data: filteredData,
            pickable: false,
            getPosition: d => [d.lon, d.lat],
            getWeight: d => {
                // Weight based purely on grade value (1-10 scale)
                const gradeValue = d.grade || d['p.grade'] || d['place_grades'];
                const grade = parseFloat(gradeValue);
                
                if (isNaN(grade)) return 0.1;
                // Normalize to 0-1 range (assuming 1-10 scale)
                // Higher grade = higher weight = hotter color
                return Math.max(0.1, grade / 10);
            },
            radiusPixels: 100,
            intensity: 1.2,
            threshold: 0.03,
            colorRange: [
                [255, 100, 100, 200],   // Bright Red (Low grade)
                [255, 150, 50, 200],    // Bright Orange
                [255, 220, 80, 200],    // Bright Yellow
                [150, 255, 100, 200],   // Bright Green
                [100, 200, 255, 200],   // Bright Sky Blue
                [100, 150, 255, 200]    // Bright Blue (High grade)
            ],
            opacity: 0.85,
            aggregation: 'MEAN'
        }));

        return {
            layers: layers,
            legend: {
                title: legendTitle,
                items: [
                    { color: `rgba(128, 128, 128, 0.6)`, label: `Min: ${minGrade100.toFixed(0)} | Avg: ${avgGrade100.toFixed(0)} | Max: ${maxGrade100.toFixed(0)}` },
                    ...legendItems
                ]
            }
        };
    }

    /**
     * Create weather heatmap layer showing temperature data using H3 hexagons
     * @returns {deck.H3HexagonLayer} Weather hexagon visualization layer
     */
    function createWeatherHeatmapLayer() {
        // Convert weather points to H3 hexagons
        const hexMap = new Map();
        
        weatherHeatmapData.forEach(point => {
            try {
                const hex = h3.latLngToCell(point.lat, point.lon, 7); // Resolution 7 for good coverage
                
                if (!hexMap.has(hex)) {
                    hexMap.set(hex, {
                        hex: hex,
                        temperatures: []
                    });
                }
                hexMap.get(hex).temperatures.push(point.temperature);
            } catch (e) {
                console.warn('H3 conversion error:', e);
            }
        });
        
        // Calculate average temperature per hex
        const hexData = Array.from(hexMap.values()).map(item => ({
            hex: item.hex,
            temperature: item.temperatures.reduce((a, b) => a + b, 0) / item.temperatures.length
        }));
        
        return new deck.H3HexagonLayer({
            id: 'weather-hexagons',
            data: hexData,
            pickable: true,
            wireframe: false,
            filled: true,
            extruded: false,
            getHexagon: d => d.hex,
            getFillColor: d => {
                const temp = d.temperature;
                // Blue (cold) to Red (hot) gradient
                if (temp < 0) return [0, 50, 255, 200];          // Deep Blue (freezing)
                if (temp < 5) return [50, 150, 255, 200];        // Blue (very cold)
                if (temp < 10) return [100, 200, 255, 200];      // Light Blue (cold)
                if (temp < 15) return [150, 230, 200, 200];      // Cyan (cool)
                if (temp < 20) return [200, 255, 150, 200];      // Light Green (mild)
                if (temp < 25) return [255, 255, 100, 200];      // Yellow (warm)
                if (temp < 30) return [255, 180, 50, 200];       // Orange (hot)
                return [255, 50, 50, 200];                       // Red (very hot)
            },
            getElevation: 0,
            elevationScale: 0,
            opacity: 0.7,
            onHover: info => handleWeatherHover(info)
        });
    }

    /**
     * Handle hover over weather heatmap to show local temperature
     */
    function handleWeatherHover(info) {
        if (!info || !temperatureHoverInfo) return;
        
        if (info.object && info.object.temperature) {
            // Show temperature of the hexagon being hovered
            temperatureHoverInfo.textContent = `Local: ${info.object.temperature.toFixed(1)}°C`;
        } else if (info.coordinate && weatherHeatmapData.length > 0) {
            // Fallback: find nearest weather point if not hovering directly on hexagon
            const [lon, lat] = info.coordinate;
            let nearestPoint = null;
            let minDistance = Infinity;
            
            weatherHeatmapData.forEach(point => {
                const dx = point.lon - lon;
                const dy = point.lat - lat;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance < minDistance) {
                    minDistance = distance;
                    nearestPoint = point;
                }
            });
            
            if (nearestPoint) {
                temperatureHoverInfo.textContent = `Local: ${nearestPoint.temperature}°C`;
            }
        } else {
            temperatureHoverInfo.textContent = 'Hover over map for local temp';
        }
    }

    function createArcLayers(data, isDrawing) {
        const layers = [];
        
        // Filter only high-grade locations (grade >= 7)
        const highGradeData = data.filter(d => {
            const grade = d.grade ? parseFloat(d.grade) : 0;
            return grade >= 7;
        });

        if (highGradeData.length < 2) {
            console.warn('Not enough high-grade locations for graph visualization');
            return [new deck.ScatterplotLayer({ id: 'empty-graph', data: [] })];
        }

        // Build graph connections: connect each location to its 3 nearest neighbors
        const connections = [];
        
        highGradeData.forEach((source, idx) => {
            // Calculate distances to all other points
            const distances = highGradeData
                .map((target, targetIdx) => {
                    if (idx === targetIdx) return null;
                    
                    const dx = target.lon - source.lon;
                    const dy = target.lat - source.lat;
                    const distance = Math.sqrt(dx * dx + dy * dy);
                    
                    return { target, targetIdx, distance };
                })
                .filter(d => d !== null)
                .sort((a, b) => a.distance - b.distance)
                .slice(0, 3); // Connect to 3 nearest neighbors
            
            // Create connections
            distances.forEach(({ target }) => {
                // Get primary category for color
                const sourceCat = getCategoryName(source);
                const targetCat = getCategoryName(target);
                const category = sourceCat; // Use source category for color
                
                const avgGrade = ((parseFloat(source.grade) || 7) + (parseFloat(target.grade) || 7)) / 2;
                
                connections.push({
                    source: [source.lon, source.lat],
                    target: [target.lon, target.lat],
                    category: category,
                    avgGrade: avgGrade,
                    sourceData: source,
                    targetData: target
                });
            });
        });

        // Helper function to get category name
        function getCategoryName(point) {
            if (point.category_ids && point.category_ids.length > 0) {
                return CATEGORY_ID_MAPPING[point.category_ids[0]] || 'Uncategorized';
            }
            const categories = point.categories || (point.category ? [point.category] : ['Uncategorized']);
            return categories[0] || 'Uncategorized';
        }

        // Create line layer for connections colored by category
        layers.push(
            new deck.LineLayer({
                id: 'graph-connections',
                data: connections,
                getSourcePosition: d => d.source,
                getTargetPosition: d => d.target,
                getColor: d => {
                    const color = CATEGORY_COLORS[d.category] || CATEGORY_COLORS['Uncategorized'];
                    return [...color, 180]; // Add alpha
                },
                getWidth: d => d.avgGrade / 2, // Width based on average grade
                widthMinPixels: 2,
                widthMaxPixels: 8,
                pickable: !isDrawing,
                onClick: info => {
                    if (info.object) {
                        const d = info.object;
                        new mapboxgl.Popup()
                            .setLngLat(info.coordinate)
                            .setHTML(`
                                <div style="font-family: 'Space Grotesk', sans-serif; padding: 5px;">
                                    <strong>Connection</strong><br>
                                    <b>Category:</b> ${d.category}<br>
                                    <b>Avg Grade:</b> ${d.avgGrade.toFixed(1)}
                                </div>
                            `)
                            .addTo(map);
                    }
                }
            })
        );

        // Create nodes layer with larger points colored by category
        layers.push(
            new deck.ScatterplotLayer({
                id: 'graph-nodes',
                data: highGradeData,
                getPosition: d => [d.lon, d.lat],
                getFillColor: d => {
                    const category = getCategoryName(d);
                    return CATEGORY_COLORS[category] || CATEGORY_COLORS['Uncategorized'];
                },
                getRadius: d => {
                    const grade = parseFloat(d.grade) || 7;
                    return grade * 10; // Size based on grade
                },
                radiusMinPixels: 5,
                radiusMaxPixels: 15,
                lineWidthMinPixels: 2,
                stroked: true,
                getLineColor: [255, 255, 255],
                pickable: !isDrawing,
                onClick: info => showPopup(info)
            })
        );

        return layers;
    }

    function createChoroplethLayers(data, isDrawing) {
        const layers = [];
        const zoom = map.getZoom();

        // Determine H3 resolution based on zoom level
        // Zoom 5-8: resolution 5 (large hexagons for country/region view)
        // Zoom 9-11: resolution 7 (medium hexagons for city view)
        // Zoom 12-14: resolution 9 (small hexagons for neighborhood view)
        // Zoom 15+: resolution 11 (very small hexagons for street view)
        let h3Resolution;
        if (zoom < 9) {
            h3Resolution = 5;
        } else if (zoom < 12) {
            h3Resolution = 7;
        } else if (zoom < 15) {
            h3Resolution = 9;
        } else {
            h3Resolution = 11;
        }

        // Group data points into H3 hexagons
        const hexagonData = new Map();

        data.forEach(point => {
            if (!point.lat || !point.lon) return;

            // Get H3 index for this point
            const h3Index = h3.latLngToCell(point.lat, point.lon, h3Resolution);

            if (!hexagonData.has(h3Index)) {
                hexagonData.set(h3Index, {
                    points: [],
                    totalGrade: 0,
                    count: 0,
                    categories: new Set()
                });
            }

            const hexData = hexagonData.get(h3Index);
            hexData.points.push(point);
            hexData.count++;
            const categories = point.categories || (point.category ? [point.category] : ['Uncategorized']);
            categories.forEach(cat => {
                hexData.categories.add(cat || 'Uncategorized');
            });

            // Add grade if available
            const grade = point.grade ? parseFloat(point.grade) : 5;
            hexData.totalGrade += grade;
        });

        // Convert hexagon data to GeoJSON features
        const hexFeatures = [];
        hexagonData.forEach((hexData, h3Index) => {
            const boundary = h3.cellToBoundary(h3Index, true); // true for GeoJSON format
            const avgGrade = hexData.totalGrade / hexData.count;

            hexFeatures.push({
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: [boundary]
                },
                properties: {
                    h3Index: h3Index,
                    count: hexData.count,
                    avgGrade: avgGrade,
                    categories: Array.from(hexData.categories),
                    density: hexData.count // For color mapping
                }
            });
        });

        const hexagonGeoJson = {
            type: 'FeatureCollection',
            features: hexFeatures
        };

        // Create the hexagon layer
        if (hexFeatures.length > 0) {
            layers.push(
                new deck.GeoJsonLayer({
                    id: 'hexagon-layer',
                    data: hexagonGeoJson,
                    pickable: !isDrawing,
                    stroked: true,
                    filled: true,
                    extruded: false,
                    lineWidthScale: 1,
                    lineWidthMinPixels: 1,
                    getFillColor: d => {
                        const density = d.properties.count;
                        const avgGrade = d.properties.avgGrade;

                        // Color based on average grade
                        if (avgGrade >= 8) return [46, 204, 113, 180];      // Green - Excellent
                        if (avgGrade >= 6) return [52, 152, 219, 180];      // Blue - Good
                        if (avgGrade >= 4) return [241, 196, 15, 180];      // Yellow - Average
                        if (avgGrade >= 2) return [230, 126, 34, 180];      // Orange - Below Average
                        return [231, 76, 60, 180];                           // Red - Poor
                    },
                    getLineColor: [255, 255, 255, 100],
                    getLineWidth: 2,
                    updateTriggers: {
                        getFillColor: [data, h3Resolution]
                    },
                    onClick: info => {
                        if (info.object) {
                            const props = info.object.properties;
                            const categoriesStr = props.categories.join(', ');
                            new mapboxgl.Popup()
                                .setLngLat(info.coordinate)
                                .setHTML(`
                                    <div style="font-family: 'Space Grotesk', sans-serif; padding: 5px;">
                                        <strong>Region Summary</strong><br>
                                        <b>Locations:</b> ${props.count}<br>
                                        <b>Avg Grade:</b> ${props.avgGrade.toFixed(1)}<br>
                                        <b>Categories:</b> ${categoriesStr}
                                    </div>
                                `)
                                .addTo(map);
                        }
                    }
                })
            );
        }

        // Fallback to scatter if no hexagons
        if (hexFeatures.length === 0 && data.length > 0) {
            layers.push(
                new deck.ScatterplotLayer({
                    id: 'chloropleth-fallback',
                    data: data,
                    getPosition: d => [d.lon, d.lat],
                    getFillColor: [200, 200, 200],
                    getRadius: 100,
                    pickable: !isDrawing
                })
            );
        }

        return layers;
    }

    function updateOverlay(category, items) {
        overlayCategory.textContent = category;
        overlayLegend.innerHTML = '';
        items.forEach(item => {
            const div = document.createElement('div');
            div.className = 'legend-item';
            div.innerHTML = `<div class="legend-color" style="background-color: ${item.color}"></div><span>${item.label}</span>`;
            overlayLegend.appendChild(div);
        });
    }

    function showPopup(info) {
        if (!info.object) return;
        const d = info.object.properties || info.object; // Handle GeoJSON or raw data
        const lat = d.lat || (info.coordinate ? info.coordinate[1] : 0);
        const lon = d.lon || (info.coordinate ? info.coordinate[0] : 0);

        const location = d.location || "Unknown Location";

        new mapboxgl.Popup()
            .setLngLat([lon, lat])
            .setHTML(`
                <div style="font-family: 'Space Grotesk', sans-serif; padding: 5px;">
                    <strong>${location}</strong><br>
                    ${d.categories && d.categories.length > 0 ? `<small>${d.categories.join(', ')}</small><br>` : (d.category ? `<small>${d.category}</small><br>` : '')}
                    ${d.grade ? `Grade: <b>${d.grade}</b>` : ''}
                </div>
            `)
            .addTo(map);
    }

    // ---------------------------------------------------------
    // Mapbox Markers (Legacy Mode -> Now Interactive Tags)
    // ---------------------------------------------------------
    let mapboxMarkers = [];
    function renderMapboxMarkers() {
        // Clear existing
        mapboxMarkers.forEach(m => m.remove());
        mapboxMarkers = [];

        if (currentVizMode !== 'mapbox') {
            return;
        }

        // Filter features by active category
        const featuresToRender = mapState.features.filter(f => {
            // Check ID first
            if (f.category_ids && f.category_ids.length > 0) {
                return f.category_ids.includes(parseInt(currentCategory));
            }

            // Fallback to name matching
            const targetCategoryName = CATEGORY_ID_MAPPING[parseInt(currentCategory)];
            if (!targetCategoryName) return false;

            const categories = f.categories || (f.category ? [f.category] : ['Uncategorized']);
            return categories.some(cat => {
                const category = cat || 'Uncategorized';
                return category.toLowerCase() === targetCategoryName.toLowerCase();
            });
        });

        console.log('Rendering mapbox markers:', {
            totalFeatures: mapState.features.length,
            activeCategory: currentCategory,
            filteredFeatures: featuresToRender.length
        });

        featuresToRender.forEach((f, index) => {
            if (!f.lat || !f.lon) {
                console.warn(`Feature ${index} missing coordinates:`, f);
                return;
            }

            // Create a DOM element for the marker - minimal pin icon
            const el = document.createElement('div');
            el.className = 'location-tag';
            
            // Minimal SVG pin icon
            el.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="#00bcd4" style="filter: drop-shadow(0 1px 2px rgba(0,0,0,0.2));"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"></path></svg>`;
            
            el.title = f.location || 'Unknown location';

            // Add click listener
            el.addEventListener('click', (e) => {
                e.stopPropagation();
                const query = `Tell me about the location at latitude ${f.lat} and longitude ${f.lon}`;
                sendMessage(query);
            });

            const marker = new mapboxgl.Marker({ element: el, anchor: 'bottom' })
                .setLngLat([f.lon, f.lat])
                .addTo(map);

            mapboxMarkers.push(marker);
        });

        console.log(`Created ${mapboxMarkers.length} markers on map`);
    }

    // ---------------------------------------------------------
    // UI & Interaction
    // ---------------------------------------------------------

    // Tilt Toggle
    if (tiltMapBtn) {
        tiltMapBtn.addEventListener('click', () => {
            isTiltActive = !isTiltActive;
            if (isTiltActive) {
                map.easeTo({ pitch: 60, duration: 1000 });
                tiltMapBtn.classList.add('active');
            } else {
                map.easeTo({ pitch: 0, duration: 1000 });
                tiltMapBtn.classList.remove('active');
            }
        });
    }

    // Viz Mode Switching
    document.querySelectorAll(".vischoice").forEach((option) => {
        option.addEventListener("click", (e) => {
            const mode = option.getAttribute("data-mode");
            if (mode) {
                setVizMode(mode);
            }
        });
    });

    function setVizMode(mode) {
        const prevMode = currentVizMode;
        currentVizMode = mode;

        document.querySelectorAll(".vischoice").forEach((el) => {
            el.classList.remove("selected");
        });
        const activeEl = document.querySelector(`[data-mode="${mode}"]`);
        if (activeEl) {
            activeEl.classList.add("selected");
        }

        // Switch Map Style - respect current theme
        if (mode === 'mapbox') {
            if (prevMode !== 'mapbox') {
                // Return to theme-appropriate style for mapbox mode
                const themeStyle = currentTheme === 'light' ? LIGHT_STYLE : DARK_STYLE;
                map.setStyle(themeStyle);
            }
        } else {
            // For visualization modes, use current theme's dark style for better layer visibility
            // Only switch if we weren't already in a visualization mode (optimization)
            if (prevMode === 'mapbox') {
                map.setStyle(DARK_STYLE);
            }
        }

        // If switching away from mapbox, clear markers
        if (mode !== 'mapbox') {
            mapboxMarkers.forEach(m => m.remove());
            mapboxMarkers = [];
        } else {
            // If switching TO mapbox, render markers
            renderMapboxMarkers();
        }

        // Note: updateDeckLayers will be called by style.load if style changes.
        // If style doesn't change (e.g. scatter -> heatmap), we call it here.
        if ((mode === 'mapbox' && prevMode === 'mapbox') || (mode !== 'mapbox' && prevMode !== 'mapbox')) {
            updateDeckLayers();
        }
    }

    // ==============================
    // Category Filter Functions
    // ==============================
    function initializeCategoryFilter() {
        // Initialize dropdown
        if (!categorySelect) return;

        categorySelect.innerHTML = ''; // Clear existing options

        // Add "All Categories" option first
        const allOption = document.createElement('option');
        allOption.value = 'all';
        allOption.textContent = 'All Categories';
        categorySelect.appendChild(allOption);

        // Use IDs for values
        Object.entries(CATEGORY_ID_MAPPING).forEach(([id, name]) => {
            allCategories.set(name, 0); // Initialize with 0 count

            const option = document.createElement('option');
            option.value = id; // Use ID as value
            option.textContent = name;
            categorySelect.appendChild(option);
        });

        // Set default category to 'all' (no filter)
        currentCategory = 'all';
        categorySelect.value = 'all';

        // Add event listener for category select to toggle filter button visibility
        const applyFilterBtn = document.getElementById('applyFilterBtn');
        
        // Function to toggle filter button visibility
        const toggleFilterButton = () => {
            if (applyFilterBtn) {
                if (categorySelect.value === 'all') {
                    applyFilterBtn.style.display = 'none';
                } else {
                    applyFilterBtn.style.display = 'block';
                }
            }
        };
        
        // Initial toggle - hide button since default is 'all'
        toggleFilterButton();
        
        // Add change listener to category select
        categorySelect.addEventListener('change', toggleFilterButton);

        // Add event listener for filter button
        if (applyFilterBtn) {
            applyFilterBtn.addEventListener('click', async () => {
                const selectedCategory = categorySelect.value;
                currentCategory = selectedCategory;

                // Build a query message based on selected category
                let queryMessage = '';
                let displayMessage = ''; // Message to show in chat
                
                if (selectedCategory === 'all') {
                    queryMessage = `Show me all locations`;
                    displayMessage = `🔍 Filter: All Categories`;
                } else {
                    const categoryName = CATEGORY_ID_MAPPING[parseInt(selectedCategory)];
                    queryMessage = `Show me all ${categoryName} locations`;
                    displayMessage = `🔍 Filter: ${categoryName} locations`;
                }
                
                // Always add bounds context (either drawn polygon or current viewport)
                const activeBounds = getActiveBounds();
                queryMessage += ` in the region bounded by North: ${activeBounds.north.toFixed(4)}, South: ${activeBounds.south.toFixed(4)}, East: ${activeBounds.east.toFixed(4)}, West: ${activeBounds.west.toFixed(4)}`;
                
                // Show the filter action in chat
                appendMessage("user", displayMessage);
                appendMessage("assistant pending", "...");
                
                // Show loading state
                applyFilterBtn.disabled = true;
                applyFilterBtn.textContent = 'Loading...';
                
                try {
                    await fetch("/clear-database", { method: "POST" });
                    
                    // Make API call to get filtered data
                    const mapContext = {
                        bounds: activeBounds
                    };
                    
                    const res = await fetch("/chat", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            message: queryMessage,
                            data_sources: cityLayersEnabled ? ["citylayers"] : [],
                            map_context: mapContext,
                            category_filter: selectedCategory !== 'all' ? selectedCategory : null
                        }),
                    });
                    
                    const data = await res.json();
                    
                    // Clear loading animation and remove pending message
                    clearLoadingAnimation();
                    const pending = chatWindow.querySelector(".assistant.pending");
                    if (pending) pending.remove();
                    
                    if (data.ok) {
                        // Display the answer in chat
                        if (data.answer_html) {
                            appendMessageHTML("assistant", data.answer_html);
                        } else if (data.answer) {
                            // Parse markdown and render as HTML
                            const htmlContent = marked.parse(data.answer);
                            appendMessageHTML("assistant", htmlContent);
                        }
                        
                        // Refresh map data to get the new filtered results
                        await refreshMapData();
                        
                        // Force map and markers to refresh
                        setTimeout(() => {
                            map.resize();
                            if (currentVizMode === 'mapbox') {
                                renderMapboxMarkers();
                            }
                            updateDeckLayers();
                        }, 100);
                        
                        // Show success feedback
                        console.log('Filter applied successfully');
                    } else {
                        console.error('Filter error:', data.error);
                        appendMessage("assistant error", data.error || "Failed to apply filter");
                    }
                } catch (e) {
                    console.error('Filter request failed:', e);
                    
                    // Clear loading animation and remove pending message
                    clearLoadingAnimation();
                    const pending = chatWindow.querySelector(".assistant.pending");
                    if (pending) pending.remove();
                    
                    appendMessage("assistant error", "Failed to apply filter. Please try again.");
                } finally {
                    // Reset button state
                    applyFilterBtn.disabled = false;
                    applyFilterBtn.textContent = 'Filter';
                }
            });
        }

        // Update category on change (for real-time preview if needed, or remove this)
        categorySelect.addEventListener('change', (e) => {
            // Just store the value, don't apply until button is clicked
            // Optionally, you can auto-apply on change by uncommenting below:
            // currentCategory = e.target.value;
            // if (currentVizMode === 'mapbox') {
            //     renderMapboxMarkers();
            // }
            // updateDeckLayers();
            // updateLocationCountDisplay();
        });
    }

    function updateCategoryFilter() {
        // Count features by category (matching predefined categories)
        const categoryCounts = new Map();
        PREDEFINED_CATEGORIES.forEach(cat => categoryCounts.set(cat, 0));

        // Also count total
        let totalCount = mapState.features.length;

        mapState.features.forEach(f => {
            // Count by ID if available
            if (f.category_ids && f.category_ids.length > 0) {
                f.category_ids.forEach(id => {
                    const name = CATEGORY_ID_MAPPING[id];
                    if (name && categoryCounts.has(name)) {
                        categoryCounts.set(name, categoryCounts.get(name) + 1);
                    }
                });
            } else {
                // Fallback to string matching
                const categories = f.categories || (f.category ? [f.category] : ['Uncategorized']);
                categories.forEach(cat => {
                    const category = cat || 'Uncategorized';
                    const matchedCategory = PREDEFINED_CATEGORIES.find(
                        predefCat => predefCat.toLowerCase() === category.toLowerCase()
                    );
                    if (matchedCategory) {
                        categoryCounts.set(matchedCategory, categoryCounts.get(matchedCategory) + 1);
                    }
                });
            }
        });

        // Update dropdown options text (just the name, no count)
        // And update the external count display
        updateLocationCountDisplay();
    }

    function updateLocationCountDisplay() {
        const countDisplay = document.getElementById('locationCount');
        const countValue = countDisplay?.querySelector('.location-count-value');
        const headerElement = countDisplay?.querySelector('.location-count-header');
        if (!countValue || !headerElement) return;

        // Count visible/filtered features
        let count = 0;
        
        if (currentCategory === 'all') {
            count = mapState.features.length;
        } else {
            // Count features matching the current category filter
            const categoryId = parseInt(currentCategory);
            mapState.features.forEach(f => {
                if (f.category_ids && f.category_ids.includes(categoryId)) {
                    count++;
                }
            });
        }
        
        // Update location count only
        headerElement.textContent = 'Locations on Map';
        countValue.textContent = count;
        
        // Update temperature panel separately
        updateTemperaturePanel();
    }

    /**
     * Update the temperature panel with current weather data
     */
    function updateTemperaturePanel() {
        if (!temperaturePanel) return;
        
        if (weatherEnabled && weatherHeatmapData.length > 0) {
            // Show panel
            temperaturePanel.classList.remove('hidden');
            
            // Calculate average temperature
            const avgTemp = (weatherHeatmapData.reduce((sum, p) => sum + p.temperature, 0) / weatherHeatmapData.length).toFixed(1);
            
            if (temperatureValue) {
                temperatureValue.textContent = `${avgTemp}°C`;
            }
            
            if (temperatureHoverInfo) {
                temperatureHoverInfo.textContent = 'Hover over map for local temp';
            }
        } else {
            // Hide panel when weather is disabled
            temperaturePanel.classList.add('hidden');
        }
    }

    function clearAllCategoryFilters() {
        if (categorySelect && categorySelect.options.length > 0) {
            currentCategory = categorySelect.options[0].value;
            categorySelect.value = currentCategory;
        }

        if (currentVizMode === 'mapbox') {
            renderMapboxMarkers();
        }
        updateDeckLayers();
        updateLocationCountDisplay();
    }



    // Data Fetching
    async function refreshMapData() {
        try {
            const res = await fetch("/map-data");
            const data = await res.json();
            if (data.ok) {
                mapState.features = data.features || [];
                mapState.boundaries = data.boundaries || [];

                console.log('Map data refreshed:', {
                    featureCount: mapState.features.length,
                    categories: [...new Set(mapState.features.map(f => f.category || 'Uncategorized'))]
                });
                
                // Detailed log of the first feature
                if (mapState.features.length > 0) {
                    console.log('First feature:', mapState.features[0]);
                }

                // Update category filter
                updateCategoryFilter();

                // Fit bounds if we have data
                if (mapState.features.length > 0) {
                    const bounds = new mapboxgl.LngLatBounds();
                    mapState.features.forEach(f => {
                        if (f.lat && f.lon) {
                            bounds.extend([f.lon, f.lat]);
                        }
                    });
                    map.fitBounds(bounds, { padding: 50, maxZoom: 15 });
                }

                // Always update visualization layers
                updateDeckLayers();

                // CRITICAL: Always render markers if in mapbox mode
                // This ensures markers appear after every data refresh
                if (currentVizMode === 'mapbox') {
                    renderMapboxMarkers();
                }
                
                // Force a map resize/render to ensure visibility
                setTimeout(() => {
                    map.resize();
                    if (currentVizMode === 'mapbox') {
                        renderMapboxMarkers();
                    }
                }, 100);
                
                // Update location count display
                updateLocationCountDisplay();
            } else {
                console.error('Map data error:', data);
            }
        } catch (e) {
            console.error("Error fetching map data:", e);
        }
    }

    if (refreshMapBtn) {
        refreshMapBtn.addEventListener("click", () => {
            refreshMapBtn.classList.add('active');
            refreshMapData().then(() => {
                setTimeout(() => refreshMapBtn.classList.remove('active'), 300);
            });
        });
    }

    if (clearMapBtn) {
        clearMapBtn.addEventListener("click", async () => {
            if (confirm("Clear all locations?")) {
                await fetch("/clear", { method: "POST" });
                mapState.features = [];
                mapState.boundaries = [];
                updateDeckLayers();
                mapboxMarkers.forEach(m => m.remove());
                mapboxMarkers = [];
                chatWindow.innerHTML = '<div class="system">Ask questions about places in the database.</div>';
            }
        });
    }

    // Chat Handling
    async function sendMessage(message) {
        appendMessage("user", message);
        appendMessage("assistant pending", "...");
        try {
            const activeBounds = getActiveBounds();
            const mapContext = {
                bounds: activeBounds,
                center: map.getCenter(),
                zoom: map.getZoom()
            };

            const res = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message,
                    data_sources: cityLayersEnabled ? ["citylayers"] : [],
                    map_context: mapContext,
                    category_filter: currentCategory !== 'all' ? currentCategory : null
                }),
            });
            const data = await res.json();
            
            // Clear loading animation and remove pending message
            clearLoadingAnimation();
            const pending = chatWindow.querySelector(".assistant.pending");
            if (pending) pending.remove();

            if (data.ok) {
                if (data.answer_html) {
                    appendMessageHTML("assistant", data.answer_html);
                } else if (data.answer) {
                    // Parse markdown and render as HTML
                    const htmlContent = marked.parse(data.answer);
                    appendMessageHTML("assistant", htmlContent);
                }

                // Auto-select category if detected
                if (data.detected_category_id) {
                    categorySelect.value = data.detected_category_id;
                    currentCategory = data.detected_category_id;
                    
                    // Update filter button visibility (show it since a category was detected)
                    const applyFilterBtn = document.getElementById('applyFilterBtn');
                    if (applyFilterBtn) {
                        applyFilterBtn.style.display = 'block';
                    }
                    
                    // Auto-enable weather heatmap if Climate Comfort (category 5) is detected
                    if (data.detected_category_id === '5' || data.detected_category_id === 5) {
                        if (!weatherEnabled) {
                            weatherEnabled = true;
                            if (sourceWeather) {
                                sourceWeather.classList.add('active');
                            }
                            fetchWeatherData();
                        }
                    }
                }

                await refreshMapData();

                // Handle visualization recommendation
                if (data.visualization_recommendation) {
                    const rec = data.visualization_recommendation.type;
                    if (['scatter', 'heatmap', 'arc', 'chloropleth'].includes(rec)) {
                        setVizMode(rec);
                    }
                } else if (drawnRegionBounds && mapState.features.length > 0) {
                    // Auto-switch to heatmap for region queries if no recommendation
                    setVizMode('heatmap');
                }
                
                // ALWAYS ensure markers are rendered if in mapbox mode
                // This fixes the issue where markers only appear after refresh
                if (currentVizMode === 'mapbox') {
                    renderMapboxMarkers();
                }
            } else {
                appendMessage("assistant error", data.error || "Error");
            }
        } catch (e) {
            clearLoadingAnimation();
            const pending = chatWindow.querySelector(".assistant.pending");
            if (pending) pending.remove();
            appendMessage("assistant error", String(e));
        }
    }

    // Loading messages that rotate
    const LOADING_MESSAGES = [
        "Exploring the map...",
        "Searching for locations...",
        "Analyzing location data...",
        "Processing your query...",
        "Finding the best results..."
    ];

    let loadingMessageInterval = null;

    // Helper functions for chat UI
    function appendMessage(role, text) {
        const div = document.createElement("div");
        div.className = role;
        
        // If it's a loading/pending message, create animated version
        if (role.includes('pending')) {
            let currentMessageIndex = 0;
            
            // Create loading structure
            const loadingContainer = document.createElement("span");
            loadingContainer.className = "loading-text";
            
            const messageSpan = document.createElement("span");
            messageSpan.className = "loading-message";
            messageSpan.textContent = LOADING_MESSAGES[0];
            
            const dotsContainer = document.createElement("span");
            dotsContainer.className = "loading-dots";
            dotsContainer.innerHTML = '<span></span><span></span><span></span>';
            
            loadingContainer.appendChild(messageSpan);
            loadingContainer.appendChild(dotsContainer);
            div.appendChild(loadingContainer);
            
            // Rotate through messages
            loadingMessageInterval = setInterval(() => {
                currentMessageIndex = (currentMessageIndex + 1) % LOADING_MESSAGES.length;
                messageSpan.textContent = LOADING_MESSAGES[currentMessageIndex];
            }, 4000); // Change message every 4 seconds
            
        } else {
            div.textContent = text;
        }
        
        chatWindow.appendChild(div);
        scrollToBottom();
        
        return div;
    }

    function clearLoadingAnimation() {
        if (loadingMessageInterval) {
            clearInterval(loadingMessageInterval);
            loadingMessageInterval = null;
        }
    }

    function appendMessageHTML(role, html) {
        const div = document.createElement("div");
        div.className = role;
        div.innerHTML = html;
        chatWindow.appendChild(div);
        
        // Add hover functionality to table rows
        setupTableHoverHighlight(div);
        
        scrollToBottom();
    }

    /**
     * Setup hover highlighting for table rows
     * When hovering over a table row with location data, highlight it on the map
     */
    function setupTableHoverHighlight(container) {
        const tables = container.querySelectorAll('table.hoverable-table');
        
        tables.forEach(table => {
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                row.addEventListener('mouseenter', function() {
                    // First try to get geolocation from data attributes (injected from database)
                    const lat = this.getAttribute('data-lat');
                    const lon = this.getAttribute('data-lon');
                    const location = this.getAttribute('data-location');
                    
                    if (lat && lon) {
                        // Use geolocation data directly from database
                        const feature = {
                            lat: parseFloat(lat),
                            lon: parseFloat(lon),
                            location: location || 'Location'
                        };
                        highlightLocationOnMap(feature);
                        this.style.backgroundColor = '#e3f2fd';
                        this.style.cursor = 'pointer';
                    } else {
                        // Fallback: try to match by location name
                        const cells = this.querySelectorAll('td');
                        if (cells.length === 0) return;
                        
                        const locationName = cells[0].textContent.trim();
                        
                        // Find matching feature in mapState
                        const feature = mapState.features.find(f => 
                            f.location && f.location.toLowerCase() === locationName.toLowerCase()
                        );
                        
                        if (feature && feature.lat && feature.lon) {
                            highlightLocationOnMap(feature);
                            this.style.backgroundColor = '#e3f2fd';
                            this.style.cursor = 'pointer';
                        }
                    }
                });
                
                row.addEventListener('mouseleave', function() {
                    removeMapHighlight();
                    this.style.backgroundColor = '';
                    this.style.cursor = '';
                });
                
                // Click to zoom to location
                row.addEventListener('click', function() {
                    // First try to get geolocation from data attributes
                    const lat = this.getAttribute('data-lat');
                    const lon = this.getAttribute('data-lon');
                    
                    if (lat && lon) {
                        // Use geolocation data directly from database
                        map.flyTo({
                            center: [parseFloat(lon), parseFloat(lat)],
                            zoom: 16,
                            duration: 1500
                        });
                    } else {
                        // Fallback: try to match by location name
                        const cells = this.querySelectorAll('td');
                        if (cells.length === 0) return;
                        
                        const locationName = cells[0].textContent.trim();
                        const feature = mapState.features.find(f => 
                            f.location && f.location.toLowerCase() === locationName.toLowerCase()
                        );
                        
                        if (feature && feature.lat && feature.lon) {
                            map.flyTo({
                                center: [feature.lon, feature.lat],
                                zoom: 16,
                                duration: 1500
                            });
                        }
                    }
                });
            });
        });
    }

    let highlightMarker = null;

    /**
     * Highlight a location on the map with a temporary marker
     */
    function highlightLocationOnMap(feature) {
        // Remove existing highlight
        removeMapHighlight();
        
        // Create a pulsing highlight marker
        const el = document.createElement('div');
        el.className = 'highlight-marker';
        el.innerHTML = `
            <div class="pulse-ring"></div>
            <div class="highlight-pin"></div>
        `;
        
        highlightMarker = new mapboxgl.Marker({
            element: el,
            anchor: 'bottom'
        })
        .setLngLat([feature.lon, feature.lat])
        .addTo(map);
        
        // Pan to location if not visible
        const bounds = map.getBounds();
        if (!bounds.contains([feature.lon, feature.lat])) {
            map.panTo([feature.lon, feature.lat], { duration: 500 });
        }
    }

    /**
     * Remove highlight marker from map
     */
    function removeMapHighlight() {
        if (highlightMarker) {
            highlightMarker.remove();
            highlightMarker = null;
        }
    }

    function scrollToBottom() {
        chatWindow.scrollTo({ top: chatWindow.scrollHeight, behavior: "smooth" });
    }

    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const msg = chatInput.value.trim();
        if (!msg) return;
        chatInput.value = "";
        sendMessage(msg);
    });

    // Panel Resizing Logic
    if (resizeHandle) {
        let resizeTimeout = null;

        resizeHandle.addEventListener("mousedown", (e) => {
            isResizing = true;
            leftContainer.classList.add('resizing');
            document.body.style.cursor = "ew-resize";
            e.preventDefault();
        });

        document.addEventListener("mousemove", (e) => {
            if (!isResizing) return;

            const newWidth = e.clientX;
            if (newWidth > 200 && newWidth < window.innerWidth * 0.6) {
                leftContainer.style.width = newWidth + "px";

                // Debounce map resize to prevent excessive redraws
                if (resizeTimeout) {
                    cancelAnimationFrame(resizeTimeout);
                }
                resizeTimeout = requestAnimationFrame(() => {
                    map.resize();
                });
            }
        });

        document.addEventListener("mouseup", () => {
            if (isResizing) {
                isResizing = false;
                leftContainer.classList.remove('resizing');
                document.body.style.cursor = "";
                // Final resize after mouse up
                setTimeout(() => {
                    map.resize();
                }, 50);
            }
        });
    }

    if (expandBtn) {
        expandBtn.addEventListener("click", () => {
            leftContainer.classList.toggle("collapsed");
            expandBtn.textContent = leftContainer.classList.contains("collapsed") ? "▶" : "◀";
        });
    }

    // Draw Control (Mapbox Draw)
    let draw;
    function initDrawControl() {
        draw = new MapboxDraw({
            displayControlsDefault: false,
            controls: { polygon: true, trash: true }
        });
        map.addControl(draw, 'top-right');

        // Listen for mode changes to toggle UI and deck picking
        map.on('draw.modechange', (e) => {
            const mode = e.mode;
            const drawBtn = document.getElementById("drawRectangleBtn");

            if (mode === 'draw_polygon') {
                mapState.isDrawingMode = true;
                if (drawBtn) drawBtn.classList.add('active');
                // Update deck layers to disable picking
                updateDeckLayers();
            } else if (mode === 'simple_select' || mode === 'static') {
                mapState.isDrawingMode = false;
                if (drawBtn) drawBtn.classList.remove('active');
                // Restore deck picking
                updateDeckLayers();
            }
        });

        map.on('draw.create', (e) => {
            const data = draw.getAll();
            if (data.features.length > 0) {
                const coords = data.features[0].geometry.coordinates[0];
                // Calculate bounds
                const lats = coords.map(c => c[1]);
                const lngs = coords.map(c => c[0]);
                const region = {
                    north: Math.max(...lats),
                    south: Math.min(...lats),
                    east: Math.max(...lngs),
                    west: Math.min(...lngs)
                };
                
                // Store the drawn region bounds
                drawnRegionBounds = region;

                // Build query that respects current category filter
                const categorySelect = document.getElementById('categorySelect');
                const selectedCat = categorySelect ? categorySelect.value : currentCategory;
                
                let query = `Show me all locations in the region bounded by North: ${region.north.toFixed(4)}, South: ${region.south.toFixed(4)}, East: ${region.east.toFixed(4)}, West: ${region.west.toFixed(4)}`;
                
                // Add category context from dropdown
                if (selectedCat && selectedCat !== 'all') {
                    const categoryName = CATEGORY_ID_MAPPING[parseInt(selectedCat)];
                    if (categoryName) {
                        query += ` for the ${categoryName} category`;
                    }
                }
                
                query += '. Provide a brief overview of what\'s in this area.';
                
                // Send message and ensure visualization updates
                sendMessage(query).then(() => {
                    // Force visualization update after data is loaded
                    if (mapState.features.length > 0 && currentVizMode !== 'mapbox') {
                        updateDeckLayers();
                    }
                });

                // Reset draw after a delay
                setTimeout(() => {
                    draw.deleteAll();
                    draw.changeMode('simple_select');
                }, 2000);
            }
        });
        
        // Clear drawn region bounds when polygon is deleted
        map.on('draw.delete', () => {
            drawnRegionBounds = null;
        });
    }

    const drawBtn = document.getElementById("drawRectangleBtn");
    if (drawBtn) {
        drawBtn.addEventListener("click", () => {
            if (draw) {
                // Toggle drawing mode
                if (mapState.isDrawingMode) {
                    draw.changeMode('simple_select');
                } else {
                    draw.changeMode('draw_polygon');
                }
            }
        });
    }

    // ==============================
    // Place Search Functionality
    // ==============================
    let searchTimeout = null;

    // Debounced search function
    function searchPlaces(query) {
        if (!query || query.trim().length < 3) {
            searchResults.classList.remove('visible');
            return;
        }

        // Show loading state
        searchResults.innerHTML = '<div class="search-loading">Searching...</div>';
        searchResults.classList.add('visible');

        // Use Mapbox Geocoding API
        const accessToken = mapboxgl.accessToken;
        const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}.json?access_token=${accessToken}&limit=5`;

        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.features && data.features.length > 0) {
                    displaySearchResults(data.features);
                } else {
                    searchResults.innerHTML = '<div class="search-no-results">No results found</div>';
                }
            })
            .catch(error => {
                console.error('Search error:', error);
                searchResults.innerHTML = '<div class="search-no-results">Search failed. Please try again.</div>';
            });
    }

    // Display search results
    function displaySearchResults(features) {
        searchResults.innerHTML = '';

        features.forEach(feature => {
            const item = document.createElement('div');
            item.className = 'search-result-item';

            const name = document.createElement('div');
            name.className = 'search-result-name';
            name.textContent = feature.text || feature.place_name;

            const address = document.createElement('div');
            address.className = 'search-result-address';
            address.textContent = feature.place_name;

            item.appendChild(name);
            item.appendChild(address);

            item.addEventListener('click', () => {
                selectSearchResult(feature);
            });

            searchResults.appendChild(item);
        });
    }

    // Handle search result selection
    function selectSearchResult(feature) {
        const [lng, lat] = feature.center;

        // Remove previous search marker if exists
        if (searchMarker) {
            searchMarker.remove();
        }

        // Add marker at the selected location
        searchMarker = new mapboxgl.Marker({ color: '#FF6B6B' })
            .setLngLat([lng, lat])
            .setPopup(new mapboxgl.Popup().setHTML(`<strong>${feature.text || feature.place_name}</strong><br>${feature.place_name}`))
            .addTo(map);

        // Fly to the location
        map.flyTo({
            center: [lng, lat],
            zoom: 14,
            duration: 1500
        });

        // Clear search
        placeSearchInput.value = '';
        searchResults.classList.remove('visible');
        clearSearchBtn.classList.remove('visible');

        // Show popup
        searchMarker.togglePopup();
    }

    // Search input event listener
    if (placeSearchInput) {
        placeSearchInput.addEventListener('input', (e) => {
            const query = e.target.value;

            // Show/hide clear button
            if (query.length > 0) {
                clearSearchBtn.classList.add('visible');
            } else {
                clearSearchBtn.classList.remove('visible');
            }

            // Debounce search
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                searchPlaces(query);
            }, 300);
        });

        // Handle Enter key
        placeSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                clearTimeout(searchTimeout);
                searchPlaces(e.target.value);
            }
        });
    }

    // Clear search button
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', () => {
            placeSearchInput.value = '';
            searchResults.classList.remove('visible');
            clearSearchBtn.classList.remove('visible');
            placeSearchInput.focus();
        });
    }

    // Close search results when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-container')) {
            searchResults.classList.remove('visible');
        }
    });

    // ========================================================================
    // DATA SOURCE TOGGLES
    // ========================================================================
    
    // CityLayers data source toggle
    if (sourceCityLayers) {
        sourceCityLayers.addEventListener('click', () => {
            cityLayersEnabled = !cityLayersEnabled;
            sourceCityLayers.classList.toggle('active', cityLayersEnabled);
            
            // Update visualization
            if (cityLayersEnabled) {
                refreshMapData();
            } else {
                // Clear location data but keep weather if enabled
                mapState.features = [];
                mapState.boundaries = [];
                if (currentVizMode === 'mapbox') {
                    mapboxMarkers.forEach(m => m.remove());
                    mapboxMarkers = [];
                }
                updateDeckLayers();
                updateLocationCountDisplay();
            }
        });
    }
    
    // Weather data source toggle
    if (sourceWeather) {
        sourceWeather.addEventListener('click', () => {
            weatherEnabled = !weatherEnabled;
            sourceWeather.classList.toggle('active', weatherEnabled);
            
            if (weatherEnabled) {
                fetchWeatherData();
            } else {
                weatherHeatmapData = [];
                updateDeckLayers();
            }
        });
    }

    /**
     * Fetch weather data for the current map bounds
     */
    async function fetchWeatherData() {
        try {
            const bounds = map.getBounds();
            const boundsObj = {
                north: bounds.getNorth(),
                south: bounds.getSouth(),
                east: bounds.getEast(),
                west: bounds.getWest()
            };
            
            console.log('Fetching weather data for bounds:', boundsObj);
            
            const res = await fetch("/weather-data", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ bounds: boundsObj })
            });
            
            // Check if response is JSON
            const contentType = res.headers.get("content-type");
            if (!contentType || !contentType.includes("application/json")) {
                console.error('Server returned non-JSON response:', await res.text());
                weatherEnabled = false;
                if (sourceWeather) sourceWeather.classList.remove('active');
                return;
            }
            
            const data = await res.json();
            if (data.ok && data.weather_points) {
                weatherHeatmapData = data.weather_points;
                console.log(`Fetched ${weatherHeatmapData.length} weather points`);
                
                if (data.warnings && data.warnings.length > 0) {
                    console.warn('Weather data warnings:', data.warnings);
                }
                
                updateDeckLayers();
                
                // Update location count panel with weather info
                updateLocationCountDisplay();
            } else {
                console.error('Failed to fetch weather data:', data.error);
                weatherEnabled = false;
                if (sourceWeather) sourceWeather.classList.remove('active');
            }
        } catch (e) {
            console.error('Error fetching weather data:', e);
            weatherEnabled = false;
            if (sourceWeather) sourceWeather.classList.remove('active');
        }
    }

    // Initialize category filter with predefined categories
    initializeCategoryFilter();

    // Initial Data Load
    refreshMapData();

})();
