/**
 * ============================================================================
 * CITY LAYERS - MAP VISUALIZATION APPLICATION
 * ============================================================================
 * 
 * A web application for visualizing location data with multiple visualization
 * modes including heatmaps, scatter plots, and choropleth maps.
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
    const dataPanel = document.getElementById("dataPanel");
    const temperaturePanel = dataPanel?.querySelector("#weatherTab");
    const temperatureValue = dataPanel?.querySelector(".temperature-value");
    const temperatureHoverInfo = dataPanel?.querySelector(".temperature-hover-info");
    const popupModeBtn = document.getElementById("popupModeBtn");
    const windSpeedEl = document.getElementById("windSpeed");
    const windDirectionEl = document.getElementById("windDirection");

    // ========================================================================
    // STATE VARIABLES
    // ========================================================================

    let currentVizMode = "mapbox"; // Current visualization mode
    let cityLayersEnabled = true; // Data source toggle
    let weatherEnabled = false; // Weather heatmap toggle
    let transportEnabled = false; // Transport data toggle
    let vegetationEnabled = false; // Vegetation data toggle
    let transportFilters = { train: true, tram: true, bus: true }; // Transport type filters
    let activeSpeciesFilters = new Set(); // Active species filters (empty = show all)
    let isResizing = false; // Panel resize state
    let isTiltActive = false; // 3D tilt state
    let searchMarker = null; // Active search marker
    let drawnRegionBounds = null; // Polygon selection bounds
    let weatherHeatmapData = []; // Weather data points
    let transportStations = []; // Transport station data
    let vegetationData = []; // Vegetation/tree data
    let popupModeActive = false; // Popup mode state
    let weatherPopups = []; // Array to store created popups

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
     * Convert wind direction in degrees to cardinal direction
     * @param {number} degrees - Wind direction in degrees (0-360)
     * @returns {string} Cardinal direction (N, NE, E, SE, S, SW, W, NW)
     */
    function degreesToCardinal(degrees) {
        if (degrees === null || degrees === undefined) return 'N/A';
        
        const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
        const index = Math.round(((degrees % 360) / 45)) % 8;
        return directions[index];
    }
    
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

    let currentTheme = 'light'; // Default to light mode

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
    
    // Apply customization on initial load
    map.on('load', () => {

        customizeMapLayers();
    });

    // Theme Toggle Logic
    function toggleTheme() {
        const checkbox = document.getElementById('themeToggleCheckbox');
        currentTheme = checkbox.checked ? 'dark' : 'light';
        const newStyle = currentTheme === 'light' ? LIGHT_STYLE : DARK_STYLE;
        

        
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

            
            // Restore view
            map.jumpTo({
                center: [center.lng, center.lat],
                zoom: zoom,
                pitch: pitch,
                bearing: bearing
            });
            
            // Update compass after restoring bearing
            updateCompassRotation();
            
            // Reapply custom layers (3D buildings, etc.)
            customizeMapLayers();
            
            // Re-apply building visibility state after style change
            if (map.getLayer('add-3d-buildings')) {
                map.setLayoutProperty('add-3d-buildings', 'visibility', buildingsVisible ? 'visible' : 'none');
            }
            
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
        // Wait for style to be fully loaded
        if (!map.isStyleLoaded()) {
            map.once('idle', customizeMapLayers);
            return;
        }
        
        // 1. Color water and greenspace for light mode
        if (currentTheme === 'light') {
            // Color water blue
            if (map.getLayer('water')) {
                map.setPaintProperty('water', 'fill-color', '#a8d5ff');
            }
            if (map.getLayer('waterway')) {
                map.setPaintProperty('waterway', 'line-color', '#a8d5ff');
            }
            
            // Color parks/greenspace green
            if (map.getLayer('landuse')) {
                map.setPaintProperty('landuse', 'fill-color', [
                    'match',
                    ['get', 'class'],
                    'park', '#c8e6c9',
                    'pitch', '#a5d6a7',
                    'grass', '#c8e6c9',
                    'wood', '#81c784',
                    'forest', '#66bb6a',
                    'transparent'
                ]);
            }
        }
        
        // 2. Add 3D Buildings
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
                    'minzoom': 15,
                    'paint': {
                        'fill-extrusion-color': [
                            'interpolate',
                            ['linear'],
                            ['get', 'height'],
                            0, currentTheme === 'light' ? '#e0e0e0' : '#444',
                            50, currentTheme === 'light' ? '#c0c0c0' : '#555',
                            100, currentTheme === 'light' ? '#a0a0a0' : '#666'
                        ],
                        'fill-extrusion-height': [
                            'interpolate',
                            ['linear'],
                            ['zoom'],
                            15,
                            0,
                            15.05,
                            ['get', 'height']
                        ],
                        'fill-extrusion-base': [
                            'interpolate',
                            ['linear'],
                            ['zoom'],
                            15,
                            0,
                            15.05,
                            ['get', 'min_height']
                        ],
                        'fill-extrusion-opacity': 0.8
                    }
                },
                labelLayerId
            );
            
            // Apply current visibility state
            map.setLayoutProperty('add-3d-buildings', 'visibility', buildingsVisible ? 'visible' : 'none');
        } else {
            // Update existing layer color based on theme
            map.setPaintProperty('add-3d-buildings', 'fill-extrusion-color', [
                'interpolate',
                ['linear'],
                ['get', 'height'],
                0, currentTheme === 'light' ? '#e0e0e0' : '#444',
                50, currentTheme === 'light' ? '#c0c0c0' : '#555',
                100, currentTheme === 'light' ? '#a0a0a0' : '#666'
            ]);
            
            // Re-apply visibility state
            map.setLayoutProperty('add-3d-buildings', 'visibility', buildingsVisible ? 'visible' : 'none');
        }

        // 2. Keep default water and greenery from base styles
        // Light mode: natural water (blue) and parks (green) from streets-v12
        // Dark mode: muted colors from dark-v11
        // No customization needed - let Mapbox styles handle it naturally

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

    // Add map mousemove handler for weather temperature tracking
    map.on('mousemove', (e) => {
        if (weatherEnabled && weatherHeatmapData.length > 0 && temperatureHoverInfo) {
            const { lng, lat } = e.lngLat;
            
            // Find nearest weather point to cursor
            let nearestPoint = null;
            let minDistance = Infinity;
            
            weatherHeatmapData.forEach(point => {
                const dx = point.lon - lng;
                const dy = point.lat - lat;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance < minDistance) {
                    minDistance = distance;
                    nearestPoint = point;
                }
            });
            
            if (nearestPoint) {
                temperatureHoverInfo.textContent = `${nearestPoint.temperature.toFixed(1)}°C`;
                
                // Update wind speed and direction
                if (windSpeedEl && windDirectionEl) {
                    windSpeedEl.textContent = nearestPoint.windSpeed !== undefined && nearestPoint.windSpeed !== null 
                        ? nearestPoint.windSpeed.toFixed(1) + ' m/s' 
                        : 'N/A';
                    windDirectionEl.textContent = nearestPoint.windDirection !== undefined && nearestPoint.windDirection !== null 
                        ? degreesToCardinal(nearestPoint.windDirection) + ' (' + nearestPoint.windDirection.toFixed(0) + '°)'
                        : 'N/A';
                }
            }
        }
    });
    
    // Reset temperature display when mouse leaves map
    map.on('mouseout', () => {
        if (temperatureHoverInfo && weatherEnabled && weatherHeatmapData.length > 0) {
            const avgTemp = (weatherHeatmapData.reduce((sum, p) => sum + p.temperature, 0) / weatherHeatmapData.length).toFixed(1);
            temperatureHoverInfo.textContent = `Avg: ${avgTemp}°C`;
            
            // Reset wind data to average
            if (windSpeedEl && windDirectionEl && weatherHeatmapData.length > 0) {
                const avgWindSpeed = weatherHeatmapData.reduce((sum, p) => sum + (p.windSpeed || 0), 0) / weatherHeatmapData.length;
                const avgWindDirection = weatherHeatmapData.reduce((sum, p) => sum + (p.windDirection || 0), 0) / weatherHeatmapData.length;
                
                const hasWindData = weatherHeatmapData.some(p => p.windSpeed !== undefined && p.windSpeed !== null);
                
                windSpeedEl.textContent = hasWindData ? avgWindSpeed.toFixed(1) + ' m/s' : 'N/A';
                windDirectionEl.textContent = hasWindData ? degreesToCardinal(avgWindDirection) + ' (' + avgWindDirection.toFixed(0) + '°)' : 'N/A';
            }
        }
    });

    // ========================================================================
    // WEATHER DETAILS PANEL
    // ========================================================================
    
    // Popup mode button event handler
    if (popupModeBtn) {
        popupModeBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent triggering parent click
            
            // Check if weather tab is active
            const weatherTab = document.getElementById('weatherTab');
            const isWeatherTabActive = weatherTab && weatherTab.classList.contains('active');
            
            if (!isWeatherTabActive) {
                // Don't allow popup mode if not on weather tab
                return;
            }
            
            popupModeActive = !popupModeActive;
            popupModeBtn.classList.toggle('active', popupModeActive);
            
            if (popupModeActive) {
                map.getCanvas().style.cursor = 'crosshair';
            } else {
                map.getCanvas().style.cursor = '';
                // Clear all weather popups when toggled off
                // Use a copy of the array to avoid issues during iteration
                const popupsToRemove = [...weatherPopups];
                popupsToRemove.forEach(popup => {
                    try {
                        if (popup && popup.isOpen()) {
                            popup.remove();
                        }
                    } catch (e) {
                        // Silently ignore errors from already-removed popups
                    }
                });
                weatherPopups = [];
            }
        });
    }
    
    // Map click handler for popup mode
    map.on('click', (e) => {
        // Check if weather tab is active
        const weatherTab = document.getElementById('weatherTab');
        const isWeatherTabActive = weatherTab && weatherTab.classList.contains('active');
        
        if (popupModeActive && weatherEnabled && weatherHeatmapData.length > 0 && isWeatherTabActive) {
            const { lng, lat } = e.lngLat;
            
            // Find nearest weather point to get data
            let nearestPoint = null;
            let minDistance = Infinity;
            
            weatherHeatmapData.forEach(point => {
                const dx = point.lon - lng;
                const dy = point.lat - lat;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance < minDistance) {
                    minDistance = distance;
                    nearestPoint = point;
                }
            });
            
            if (nearestPoint) {
                // Create compact popup with weather information at click location
                const popup = new mapboxgl.Popup({
                    closeButton: true,
                    closeOnClick: false,
                    className: 'weather-popup',
                    offset: 10
                })
                    .setLngLat([lng, lat])  // Use click location, not nearest point
                    .setHTML(`
                        <div style="font-family: 'Space Grotesk', sans-serif; padding: 6px; font-size: 11px;">
                            <div style="display: flex; flex-direction: column; gap: 3px;">
                                <div style="display: flex; justify-content: space-between; gap: 12px;">
                                    <span style="opacity: 0.7;">Temp:</span>
                                    <strong>${nearestPoint.temperature.toFixed(1)}°C</strong>
                                </div>
                                <div style="display: flex; justify-content: space-between; gap: 12px;">
                                    <span style="opacity: 0.7;">Wind:</span>
                                    <strong>${nearestPoint.windSpeed !== undefined && nearestPoint.windSpeed !== null ? nearestPoint.windSpeed.toFixed(1) + ' m/s' : 'N/A'}</strong>
                                </div>
                                <div style="display: flex; justify-content: space-between; gap: 12px;">
                                    <span style="opacity: 0.7;">Dir:</span>
                                    <strong>${nearestPoint.windDirection !== undefined && nearestPoint.windDirection !== null ? degreesToCardinal(nearestPoint.windDirection) : 'N/A'}</strong>
                                </div>
                            </div>
                        </div>
                    `)
                    .addTo(map);
                
                // Store popup reference
                weatherPopups.push(popup);
                
                // Remove popup from array when closed manually
                popup.on('close', () => {
                    const index = weatherPopups.indexOf(popup);
                    if (index > -1) {
                        weatherPopups.splice(index, 1);
                    }
                });
            }
        }
    });
    
    // Open weather details panel
    // AccuWeather link click handler - only on info button
    const accuweatherLink = document.getElementById('accuweatherLink');
    if (accuweatherLink) {
        accuweatherLink.addEventListener('click', (e) => {
            e.preventDefault();
            
            if (weatherEnabled && weatherHeatmapData.length > 0) {
                // Get map center coordinates
                const center = map.getCenter();
                // Open AccuWeather with coordinates
                const url = `https://www.accuweather.com/en/search-locations?query=${center.lat},${center.lng}`;
                window.open(url, '_blank');
            }
        });
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
        updateCompassRotation();
    });

    /**
     * Update compass rotation based on map bearing
     */
    function updateCompassRotation() {
        const compassOverlay = document.getElementById('compassOverlay');
        if (compassOverlay) {
            const bearing = map.getBearing();
            const svg = compassOverlay.querySelector('svg');
            if (svg) {
                svg.style.transform = `rotate(${-bearing}deg)`;
            }
        }
    }

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

        // Update compass rotation to show true north
        updateCompassRotation();

        // Update heatmap and choropleth visualizations on zoom change to update labels
        if ((currentVizMode === 'heatmap' || currentVizMode === 'chloropleth') && mapState.features.length > 0) {
            updateDeckLayers();
        }
        
        // Update vegetation data when map moves if vegetation is enabled
        if (vegetationEnabled) {
            fetchVegetationData();
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
        
        // Weather is enabled but no heatmap - just track cursor for temperature display
        // Temperature panel will update via map mousemove event handler
        
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
            // Mapbox mode - no deck layers for locations, just markers
            // But still show weather if enabled
            if (!weatherEnabled || weatherHeatmapData.length === 0) {
                updateOverlay("Map View", []);
            }
            renderMapboxMarkers();
        }
        
        // Add transport stations layer if enabled
        if (transportEnabled && transportStations.length > 0) {
            // Filter stations based on active filters
            const filteredStations = transportStations.filter(station => 
                transportFilters[station.type] === true
            );
            
            if (filteredStations.length > 0) {
                const transportLayer = new deck.IconLayer({
                    id: 'transport-stations',
                    data: filteredStations,
                    getPosition: d => [d.lon, d.lat],
                    getIcon: d => ({
                        url: getTransportIconDataUrl(d.type),
                        width: 128,
                        height: 128,
                        anchorY: 128
                    }),
                    getSize: 32,
                    sizeScale: 1,
                    pickable: true,
                    onClick: info => {
                        if (info.object) {
                            const station = info.object;

                            
                            // Create styled popup
                            const html = `<div style="font-family: 'Space Grotesk', sans-serif; padding: 5px;">
                                <strong>${station.name}</strong><br>
                                <small>${station.type}</small><br>
                                ${station.operator ? `Operator: <b>${station.operator}</b>` : ''}
                            </div>`;
                            
                            new mapboxgl.Popup({ 
                                closeButton: true,
                                closeOnClick: true,
                                className: 'custom-popup'
                            })
                                .setLngLat(info.coordinate)
                                .setHTML(html)
                                .addTo(map);
                        }
                    }
                });
                layers.push(transportLayer);
            }
        }
        
        // Add vegetation layer if enabled - using scatter plot
        if (vegetationEnabled && vegetationData.length > 0) {
            layers.push(createVegetationScatterLayer());
        }

        deckOverlay.setProps({ layers });

        // Toggle overlay visibility
        if (currentVizMode === 'mapbox' && (!weatherEnabled || weatherHeatmapData.length === 0)) {
            overlayPanel.classList.add('hidden');
        } else {
            overlayPanel.classList.remove('hidden');
        }
    }

    // ========================================================================
    // TAB VISIBILITY MANAGEMENT
    // ========================================================================
    
    /**
     * Update tab visibility based on enabled data sources
     */
    function updateTabVisibility() {
        const transportTab = document.querySelector('.data-tab[data-tab="transport"]');
        const weatherTab = document.querySelector('.data-tab[data-tab="weather"]');
        const treesTab = document.querySelector('.data-tab[data-tab="trees"]');
        
        // Show/hide tabs based on data source state
        if (transportTab) {
            transportTab.style.display = transportEnabled ? 'flex' : 'none';
        }
        if (weatherTab) {
            weatherTab.style.display = weatherEnabled ? 'flex' : 'none';
        }
        if (treesTab) {
            treesTab.style.display = vegetationEnabled ? 'flex' : 'none';
        }
        
        // If current active tab becomes hidden, switch to first visible tab
        const activeTab = document.querySelector('.data-tab.active');
        if (activeTab && activeTab.style.display === 'none') {
            const firstVisibleTab = document.querySelector('.data-tab[style*="flex"]');
            if (firstVisibleTab) {
                const tabName = firstVisibleTab.dataset.tab;
                document.querySelectorAll('.data-tab').forEach(t => t.classList.remove('active'));
                firstVisibleTab.classList.add('active');
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                document.getElementById(tabName + 'Tab').classList.add('active');
                
                // Update popup button state
                if (popupModeBtn) {
                    if (tabName === 'weather') {
                        popupModeBtn.classList.remove('disabled');
                    } else {
                        popupModeBtn.classList.add('disabled');
                    }
                }
            }
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
        


        const layers = [];
        const zoom = map.getZoom();
        
        // Define color scale based on actual rendered heatmap colors (using 100 scale for legend)
        // RED = Low grades (poor), BLUE = High grades (excellent)
        const colorStops = [
            { grade: 10, color: [220, 50, 50, 217], label: "Very Low" },         // Red
            { grade: 30, color: [255, 120, 50, 217], label: "Low" },             // Orange
            { grade: 50, color: [255, 200, 50, 217], label: "Medium" },          // Yellow
            { grade: 70, color: [100, 220, 200, 217], label: "Good" },           // Cyan
            { grade: 85, color: [50, 150, 255, 217], label: "Very Good" },       // Light Blue
            { grade: 100, color: [0, 50, 150, 217], label: "Excellent" }         // Deep Navy Blue
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
                [220, 50, 50],         // Red (low grade ~1-2)
                [255, 120, 50],        // Orange (low-mid ~2-3)
                [255, 200, 50],        // Yellow (mid ~4-5)
                [150, 230, 100],       // Yellow-Green (mid-high ~5-6)
                [100, 220, 200],       // Cyan (high ~7-8)
                [50, 150, 255],        // Light Blue (very high ~8-9)
                [0, 80, 200],          // Deep Blue (excellent ~9-10)
                [0, 50, 150]           // Navy Blue (perfect ~10)
            ],
            opacity: 0.5,
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
                
                // If weather is enabled, open weather details panel
                if (weatherEnabled) {
                    openWeatherDetails({
                        name: f.location || `Location at ${f.lat.toFixed(4)}, ${f.lon.toFixed(4)}`,
                        lat: f.lat,
                        lon: f.lon
                    });
                } else {
                    // Otherwise, send chat message
                    const query = `Tell me about the location at latitude ${f.lat} and longitude ${f.lon}`;
                    sendMessage(query);
                }
            });

            const marker = new mapboxgl.Marker({ element: el, anchor: 'bottom' })
                .setLngLat([f.lon, f.lat])
                .addTo(map);

            mapboxMarkers.push(marker);
        });


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
        const needsStyleChange = (mode === 'mapbox' && prevMode !== 'mapbox') || 
                                 (mode !== 'mapbox' && prevMode === 'mapbox');
        
        if (needsStyleChange) {
            const themeStyle = currentTheme === 'light' ? LIGHT_STYLE : DARK_STYLE;
            map.setStyle(themeStyle);
            
            // Restore layers after style loads
            map.once('style.load', () => {
                customizeMapLayers();
                updateDeckLayers();
                if (mode === 'mapbox') {
                    renderMapboxMarkers();
                }
            });
        }

        // If switching away from mapbox, clear markers
        if (mode !== 'mapbox') {
            mapboxMarkers.forEach(m => m.remove());
            mapboxMarkers = [];
        } else if (!needsStyleChange) {
            // If switching TO mapbox without style change, render markers
            renderMapboxMarkers();
        }

        // Update deck layers if style doesn't change
        if (!needsStyleChange) {
            updateDeckLayers();
        }
        
        // Update location count display
        updateLocationCountDisplay();
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
                    
                    // Build array of enabled data sources
                    const enabledSources = [];
                    if (cityLayersEnabled) enabledSources.push("citylayers");
                    if (weatherEnabled) enabledSources.push("weather");
                    if (transportEnabled) enabledSources.push("transport");
                    if (vegetationEnabled) enabledSources.push("vegetation");

                    // Collect external dataset data to send to LLM
                    const externalDatasets = {};
                    if (weatherEnabled && weatherHeatmapData.length > 0) {
                        externalDatasets.weather = weatherHeatmapData;
                    }
                    if (transportEnabled && transportStations.length > 0) {
                        externalDatasets.transport = transportStations;
                    }
                    if (vegetationEnabled && vegetationData.length > 0) {
                        externalDatasets.vegetation = vegetationData;
                    }

                    const res = await fetch("/chat", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            message: queryMessage,
                            data_sources: enabledSources,
                            external_datasets: externalDatasets,
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
        if (!temperatureValue || !temperatureHoverInfo) return;
        
        if (weatherEnabled && weatherHeatmapData.length > 0) {
            // Calculate average temperature
            const avgTemp = (weatherHeatmapData.reduce((sum, p) => sum + p.temperature, 0) / weatherHeatmapData.length).toFixed(1);
            
            // temperatureHoverInfo = large hover temperature (starts as avg)
            temperatureHoverInfo.textContent = `${avgTemp}°C`;
            
            // temperatureValue = small average label
            temperatureValue.textContent = `Avg: ${avgTemp}°C`;
            
            // Calculate and display average wind data
            if (windSpeedEl && windDirectionEl) {
                const avgWindSpeed = weatherHeatmapData.reduce((sum, p) => sum + (p.windSpeed || 0), 0) / weatherHeatmapData.length;
                const avgWindDirection = weatherHeatmapData.reduce((sum, p) => sum + (p.windDirection || 0), 0) / weatherHeatmapData.length;
                
                // Check if we have valid wind data (not just zeros from defaults)
                const hasWindData = weatherHeatmapData.some(p => p.windSpeed !== undefined && p.windSpeed !== null);
                
                windSpeedEl.textContent = hasWindData ? avgWindSpeed.toFixed(1) + ' m/s' : 'N/A';
                windDirectionEl.textContent = hasWindData ? degreesToCardinal(avgWindDirection) + ' (' + avgWindDirection.toFixed(0) + '°)' : 'N/A';
            }
        } else {
            // Reset when weather is disabled
            temperatureHoverInfo.textContent = '--°C';
            temperatureValue.textContent = 'Avg: --°C';
            if (windSpeedEl && windDirectionEl) {
                windSpeedEl.textContent = '-- m/s';
                windDirectionEl.textContent = '--°';
            }
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

            // Build array of enabled data sources
            const enabledSources = [];
            if (cityLayersEnabled) enabledSources.push("citylayers");
            if (weatherEnabled) enabledSources.push("weather");
            if (transportEnabled) enabledSources.push("transport");
            if (vegetationEnabled) enabledSources.push("vegetation");

            // Collect external dataset data to send to LLM
            const externalDatasets = {};
            if (weatherEnabled && weatherHeatmapData.length > 0) {
                externalDatasets.weather = weatherHeatmapData;
            }
            if (transportEnabled && transportStations.length > 0) {
                externalDatasets.transport = transportStations;
            }
            if (vegetationEnabled && vegetationData.length > 0) {
                externalDatasets.vegetation = vegetationData;
            }

            const res = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message,
                    data_sources: enabledSources,
                    external_datasets: externalDatasets,
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
                    if (['scatter', 'heatmap', 'chloropleth'].includes(rec)) {
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
        "Processing your question...",
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
        
        // Add export button for assistant messages (not errors or pending)
        if (role === "assistant") {
            const exportBtn = document.createElement("button");
            exportBtn.className = "message-export-btn";
            exportBtn.innerHTML = '📄 Download Report'; // Text instead of just icon
            exportBtn.title = "Export this conversation as PDF";
            exportBtn.onclick = (e) => {
                e.preventDefault();
                exportPdfReport(exportBtn);
            };
            div.appendChild(exportBtn);
        }
        
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
            
            // Update tab visibility
            updateTabVisibility();
            
            // Show/hide data panel and switch to weather tab
            if (dataPanel) {
                if (weatherEnabled || transportEnabled || vegetationEnabled) {
                    dataPanel.classList.remove('hidden');
                    if (weatherEnabled) {
                        // Switch to weather tab
                        document.querySelectorAll('.data-tab').forEach(t => t.classList.remove('active'));
                        document.querySelector('.data-tab[data-tab="weather"]').classList.add('active');
                        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                        document.getElementById('weatherTab').classList.add('active');
                        
                        // Update popup button state
                        if (popupModeBtn) {
                            popupModeBtn.classList.remove('disabled');
                        }
                    }
                } else {
                    dataPanel.classList.add('hidden');
                }
            }
            

            
            if (weatherEnabled) {
                fetchWeatherData();
            } else {
                weatherHeatmapData = [];
                updateDeckLayers();
                updateTemperaturePanel();
            }
        });
    }
    
    // Transport data source toggle
    const sourceTransport = document.getElementById('source-transport');
    if (sourceTransport) {
        sourceTransport.addEventListener('click', () => {
            transportEnabled = !transportEnabled;
            sourceTransport.classList.toggle('active', transportEnabled);
            
            // Update tab visibility
            updateTabVisibility();
            
            // Show/hide data panel and switch to transport tab
            if (dataPanel) {
                if (transportEnabled || weatherEnabled || vegetationEnabled) {
                    dataPanel.classList.remove('hidden');
                    if (transportEnabled) {
                        // Switch to transport tab
                        document.querySelectorAll('.data-tab').forEach(t => t.classList.remove('active'));
                        document.querySelector('.data-tab[data-tab="transport"]').classList.add('active');
                        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                        document.getElementById('transportTab').classList.add('active');
                        
                        // Update popup button state
                        if (popupModeBtn) {
                            popupModeBtn.classList.add('disabled');
                        }
                    }
                } else {
                    dataPanel.classList.add('hidden');
                }
            }
            

            
            if (transportEnabled) {
                fetchTransportData();
            } else {
                transportStations = [];
                updateDeckLayers();
            }
        });
    }
    
    // Transport legend filter toggles
    const transportLegendItems = document.querySelectorAll('.transport-legend-item');
    transportLegendItems.forEach(item => {
        item.addEventListener('click', () => {
            const type = item.dataset.type;
            if (type && type in transportFilters) {
                transportFilters[type] = !transportFilters[type];
                item.classList.toggle('active', transportFilters[type]);
                updateDeckLayers();
            }
        });
    });
    
    // Vegetation data source toggle
    const sourceVegetation = document.getElementById('source-vegetation');
    if (sourceVegetation) {
        sourceVegetation.addEventListener('click', () => {
            vegetationEnabled = !vegetationEnabled;
            sourceVegetation.classList.toggle('active', vegetationEnabled);
            
            // Update tab visibility
            updateTabVisibility();

            
            if (vegetationEnabled) {
                fetchVegetationData();
                // Show data panel and switch to trees tab
                const dataPanel = document.getElementById('dataPanel');
                if (dataPanel) {
                    dataPanel.classList.remove('hidden');
                    document.querySelectorAll('.data-tab').forEach(t => t.classList.remove('active'));
                    document.querySelector('.data-tab[data-tab="trees"]').classList.add('active');
                    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                    document.getElementById('treesTab').classList.add('active');
                    
                    // Update popup button state
                    if (popupModeBtn) {
                        popupModeBtn.classList.add('disabled');
                    }
                }
            } else {
                vegetationData = [];
                // Remove Mapbox tree layer
                if (map.getLayer('3d-trees')) {
                    map.removeLayer('3d-trees');
                }
                if (map.getSource('trees-data')) {
                    map.removeSource('trees-data');
                }
                updateTreesPanel();
                
                // Hide panel if no other data sources are enabled
                const dataPanel = document.getElementById('dataPanel');
                if (dataPanel && !weatherEnabled && !transportEnabled) {
                    dataPanel.classList.add('hidden');
                }
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
    
    /**
     * Fetch public transport data for the current map bounds
     */
    async function fetchTransportData() {
        try {
            const bounds = map.getBounds();
            const boundsObj = {
                north: bounds.getNorth(),
                south: bounds.getSouth(),
                east: bounds.getEast(),
                west: bounds.getWest()
            };
            

            
            const res = await fetch("/transport-data", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ bounds: boundsObj })
            });
            
            const data = await res.json();

            
            if (data.ok && data.stations) {
                transportStations = data.stations;

                updateDeckLayers();
                updateLocationCountDisplay();
            } else {
                console.error('Failed to fetch transport data:', data.error);
                transportEnabled = false;
                const sourceTransport = document.getElementById('source-transport');
                if (sourceTransport) sourceTransport.classList.remove('active');
            }
        } catch (e) {
            console.error('Error fetching transport data:', e);
            transportEnabled = false;
            const sourceTransport = document.getElementById('source-transport');
            if (sourceTransport) sourceTransport.classList.remove('active');
        }
    }
    
    /**
     * Create vegetation scatter plot layer
     * Displays trees with opacity and actual foliage radius
     */
    function createVegetationScatterLayer() {
        // Filter by selected species
        const filteredData = vegetationData.filter(tree => {
            if (activeSpeciesFilters.size === 0) return true;
            return !activeSpeciesFilters.has(tree.common_name || tree.species || 'Unknown');
        });
        
        return new deck.ScatterplotLayer({
            id: 'vegetation-layer',
            data: filteredData,
            pickable: true,
            opacity: 0.3,
            stroked: true,
            filled: true,
            radiusUnits: 'meters',
            radiusMinPixels: 2,
            radiusMaxPixels: 100,
            lineWidthMinPixels: 0.5,
            getPosition: d => [d.lon, d.lat],
            getRadius: d => (d.crown_diameter || 5) / 2,  // Use foliage radius
            getFillColor: d => {
                // Darker, brighter greens based on species
                const speciesColors = {
                    'Acer': [0, 180, 0, 120],        // Bright green
                    'Tilia': [0, 200, 50, 120],      // Bright lime
                    'Platanus': [0, 160, 80, 120],   // Bright sea green
                    'Quercus': [0, 140, 0, 120],     // Deep green
                    'Unknown': [50, 180, 50, 120]    // Balanced green
                };
                const genus = d.species ? d.species.split(' ')[0] : 'Unknown';
                return speciesColors[genus] || speciesColors['Unknown'];
            },
            getLineColor: [255, 255, 255, 50],
            onClick: (info) => {
                if (info.object) {
                    const tree = info.object;
                    const treeName = tree.common_name || tree.species || 'Unknown Species';
                    // Only use scientific name (species) for FloraVeg link
                    // Remove anything in parentheses (common name) - e.g., "Gleditsia triacanthos (Lederhülsenbaum)" -> "Gleditsia triacanthos"
                    const scientificName = tree.species ? tree.species.replace(/\s*\([^)]*\)/g, '').replace(/\s+/g, ' ').trim() : null;
                    
                    // Only show info button if we have a valid scientific name
                    const infoButton = scientificName && scientificName !== 'Unknown Species'
                        ? `<div style="position: absolute; bottom: 5px; right: 5px;">
                            <a href="https://floraveg.eu/taxon/overview/${scientificName.replace(/ /g, '%20')}" 
                               target="_blank" 
                               style="display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 50%; font-size: 12px; font-weight: bold; font-style: italic; transition: background 0.2s;"
                               onmouseover="this.style.background='#45a049'" 
                               onmouseout="this.style.background='#4CAF50'"
                               title="View detailed botanical information and images on FloraVeg.EU">
                                i
                            </a>
                        </div>`
                        : '';
                    
                    const html = `<div style="font-family: 'Space Grotesk', sans-serif; padding: 8px 5px 5px 5px; position: relative;">
                        <strong>${treeName}</strong><br>
                        ${tree.height ? `Height: <b>${tree.height}m</b><br>` : ''}
                        ${tree.crown_diameter ? `Crown: <b>${tree.crown_diameter}m</b><br>` : ''}
                        ${tree.planting_year ? `Planted: <b>${tree.planting_year}</b>` : ''}
                        ${infoButton}
                    </div>`;
                    
                    new mapboxgl.Popup({ 
                        closeButton: true,
                        closeOnClick: true,
                        className: 'custom-popup tree-popup'
                    })
                        .setLngLat([tree.lon, tree.lat])
                        .setHTML(html)
                        .addTo(map);
                }
            }
        });
    }
    
    /**
     * Fetch vegetation data for the current map bounds
     */
    async function fetchVegetationData() {
        try {
            const bounds = map.getBounds();
            const boundsObj = {
                north: bounds.getNorth(),
                south: bounds.getSouth(),
                east: bounds.getEast(),
                west: bounds.getWest()
            };
            

            
            const res = await fetch("/vegetation-data", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ bounds: boundsObj })
            });
            
            const data = await res.json();

            
            if (data.ok && data.trees) {
                vegetationData = data.trees;  // No limit - show all trees

                updateLocationCountDisplay();
                updateTreesPanel(data);
                updateDeckLayers();  // Re-render with scatter plot
            } else {
                console.error('Failed to fetch vegetation data:', data.error);
                vegetationEnabled = false;
                const sourceVegetation = document.getElementById('source-vegetation');
                if (sourceVegetation) sourceVegetation.classList.remove('active');
            }
        } catch (e) {
            console.error('Error fetching vegetation data:', e);
            vegetationEnabled = false;
            const sourceVegetation = document.getElementById('source-vegetation');
            if (sourceVegetation) sourceVegetation.classList.remove('active');
        }
    }
    
    /**
     * Generate transport icon as data URL based on type
     * @param {string} type - Transport type (train, tram, bus)
     * @returns {string} Data URL of the SVG icon
     */
    function getTransportIconDataUrl(type) {
        let svgPath = '';
        let color = '';
        
        switch (type) {
            case 'train':
                color = '#007bff';
                svgPath = 'M12 2c-4 0-8 .5-8 4v9.5C4 17.43 5.57 19 7.5 19L6 20.5v.5h2l2-2h4l2 2h2v-.5L16.5 19c1.93 0 3.5-1.57 3.5-3.5V6c0-3.5-4-4-8-4zM7.5 17c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm3.5-7H6V6h5v4zm2 0V6h5v4h-5zm3.5 7c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z';
                break;
            case 'tram':
                color = '#ffc107';
                svgPath = 'M12 2c-4 0-8 .5-8 4v9.5C4 17.43 5.57 19 7.5 19L6 20.5v.5h2l2-2h4l2 2h2v-.5L16.5 19c1.93 0 3.5-1.57 3.5-3.5V6c0-3.5-4-4-8-4zm5.5 3H14V3.5h3.5V5zM10 3.5V5H6.5V3.5H10zM7.5 17c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm1-5.5v-6h7v6h-7zm8 5.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z';
                break;
            case 'bus':
                color = '#28a745';
                svgPath = 'M4 16c0 .88.39 1.67 1 2.22V20c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h8v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1.78c.61-.55 1-1.34 1-2.22V6c0-3.5-3.58-4-8-4s-8 .5-8 4v10zm3.5 1c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm9 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm1.5-6H6V6h12v5z';
                break;
            default:
                color = '#6c757d';
                svgPath = 'M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z';
        }
        
        const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 24 24">
            <path fill="${color}" d="${svgPath}"/>
        </svg>`;
        
        return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
    }

    /**
     * Update the trees panel with vegetation data statistics
     */
    function updateTreesPanel(data = null) {
        const totalTreesCount = document.getElementById('totalTreesCount');
        const shadedAreaCount = document.getElementById('shadedAreaCount');
        const speciesFilterList = document.getElementById('speciesFilterList');
        
        if (!data || !data.trees || data.trees.length === 0) {
            if (totalTreesCount) totalTreesCount.textContent = '--';
            if (shadedAreaCount) shadedAreaCount.textContent = '--';
            if (speciesFilterList) speciesFilterList.innerHTML = '';
            return;
        }
        
        // Update total trees count
        if (totalTreesCount) {
            totalTreesCount.textContent = data.trees.length.toLocaleString();
        }
        
        // Calculate shaded area (approximate based on tree canopy)
        const totalShadedArea = data.trees.reduce((sum, tree) => {
            const radius = (tree.crown_diameter || 5) / 2;
            return sum + (Math.PI * radius * radius);
        }, 0);
        
        if (shadedAreaCount) {
            if (totalShadedArea >= 10000) {
                shadedAreaCount.textContent = (totalShadedArea / 10000).toFixed(2) + ' ha';
            } else {
                shadedAreaCount.textContent = totalShadedArea.toLocaleString(undefined, {maximumFractionDigits: 0}) + ' m²';
            }
        }
        
        // Build species filter list
        if (speciesFilterList) {
            // Count trees by common name
            const speciesCounts = {};
            data.trees.forEach(tree => {
                const commonName = tree.common_name || tree.species || 'Unknown';
                speciesCounts[commonName] = (speciesCounts[commonName] || 0) + 1;
            });
            
            // Sort by count
            const sortedSpecies = Object.entries(speciesCounts)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10); // Show top 10 species
            
            // Build HTML
            speciesFilterList.innerHTML = sortedSpecies.map(([species, count]) => `
                <div class="species-filter-item active" data-species="${species}" onclick="toggleSpeciesFilter('${species}')">
                    <span class="species-name">${species}</span>
                    <span class="species-count">${count}</span>
                </div>
            `).join('');
        }
    }
    
    /**
     * Toggle species filter
     */
    window.toggleSpeciesFilter = function(species) {
        const filterElement = document.querySelector(`.species-filter-item[data-species="${species}"]`);
        if (!filterElement) return;
        
        if (activeSpeciesFilters.has(species)) {
            // Remove filter (show this species)
            activeSpeciesFilters.delete(species);
            filterElement.classList.add('active');
        } else {
            // Add filter (hide this species)
            activeSpeciesFilters.add(species);
            filterElement.classList.remove('active');
        }
        
        // Re-render layers
        updateDeckLayers();
    };
    
    /**
     * Calculate approximate area of bounds in square meters
     */
    function calculateBoundsArea(bounds) {
        const R = 6371000; // Earth's radius in meters
        const lat1 = bounds.getSouth() * Math.PI / 180;
        const lat2 = bounds.getNorth() * Math.PI / 180;
        const lng1 = bounds.getWest() * Math.PI / 180;
        const lng2 = bounds.getEast() * Math.PI / 180;
        
        const latDiff = lat2 - lat1;
        const lngDiff = lng2 - lng1;
        const avgLat = (lat1 + lat2) / 2;
        
        const height = R * latDiff;
        const width = R * lngDiff * Math.cos(avgLat);
        
        return Math.abs(height * width);
    }

    
    // ========================================================================
    // LOCATION INFO HEADER
    // ========================================================================
    
    /**
     * Show location info header with details
     * @param {string} name - Location name
     * @param {string} category - Category name
     * @param {number} grade - Grade value
     */

    
    // Tab switching logic
    const dataTabs = document.querySelectorAll('.data-tab');
    dataTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            
            // Update active tab
            dataTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // Update active content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(tabName + 'Tab').classList.add('active');
            
            // Update popup button state based on tab
            if (popupModeBtn) {
                if (tabName === 'weather') {
                    popupModeBtn.classList.remove('disabled');
                } else {
                    popupModeBtn.classList.add('disabled');
                }
            }
            
            // Disable popup mode when switching away from weather tab
            if (tabName !== 'weather' && popupModeActive) {
                popupModeActive = false;
                if (popupModeBtn) {
                    popupModeBtn.classList.remove('active');
                }
                map.getCanvas().style.cursor = '';
                // Clear all weather popups
                const popupsToRemove = [...weatherPopups];
                popupsToRemove.forEach(popup => {
                    try {
                        if (popup && popup.isOpen()) {
                            popup.remove();
                        }
                    } catch (e) {
                        // Silently ignore errors
                    }
                });
                weatherPopups = [];
            }
        });
    });
    
    // Initialize category filter with predefined categories
    initializeCategoryFilter();
    
    // Initialize tab visibility (hide all tabs initially since no data sources are enabled)
    updateTabVisibility();

    // Initial Data Load
    refreshMapData();

    // ========================================================================
    // PDF EXPORT FUNCTIONALITY
    // ========================================================================

    /**
     * Capture map screenshot as base64 PNG
     */
    function captureMapScreenshot() {
        try {
            const canvas = map.getCanvas();
            return canvas.toDataURL('image/png');
        } catch (error) {
            console.error('Failed to capture map screenshot:', error);
            return null;
        }
    }

    /**
     * Calculate statistics from current context
     */
    function calculateStatistics() {
        if (!lastContextRecords || lastContextRecords.length === 0) {
            console.log('DEBUG: No context records available for statistics');
            return {
                total_locations: 0,
                average_rating: 0,
                top_rated: 'N/A',
                category_breakdown: {}
            };
        }
        
        console.log(`DEBUG: Calculating statistics from ${lastContextRecords.length} records`);

        let totalRating = 0;
        let ratingCount = 0;
        let topRated = { name: 'N/A', rating: 0 };
        const categoryBreakdown = {};

        lastContextRecords.forEach(record => {
            // Count by category
            const category = record.c || 'Unknown';
            categoryBreakdown[category] = (categoryBreakdown[category] || 0) + 1;

            // Calculate average rating
            if (record.pg) {
                const rating = parseFloat(record.pg);
                if (!isNaN(rating)) {
                    totalRating += rating;
                    ratingCount++;

                    // Track top rated
                    if (rating > topRated.rating) {
                        topRated = {
                            name: record.p?.name || 'Unknown',
                            rating: rating
                        };
                    }
                }
            }
        });

        return {
            total_locations: lastContextRecords.length,
            average_rating: ratingCount > 0 ? (totalRating / ratingCount).toFixed(1) : 0,
            top_rated: `${topRated.name} (${topRated.rating})`,
            category_breakdown: categoryBreakdown
        };
    }

    /**
     * Get conversation history for PDF
     */
    function getConversationHistory() {
        const messages = chatWindow.querySelectorAll('.user, .assistant:not(.pending):not(.error)');
        const conversation = [];

        messages.forEach(msg => {
            if (msg.classList.contains('user')) {
                conversation.push({
                    role: 'user',
                    content: msg.textContent.trim()
                });
            } else if (msg.classList.contains('assistant')) {
                conversation.push({
                    role: 'assistant',
                    content: msg.textContent.trim()
                });
            }
        });

        return conversation.slice(-10); // Last 10 messages
    }

    /**
     * Get enabled data sources
     */
    function getEnabledDataSources() {
        const sources = [];
        document.querySelectorAll('.data-source-btn.active').forEach(btn => {
            sources.push(btn.dataset.source);
        });
        return sources;
    }

    /**
     * Format locations for PDF
     */
    function formatLocationsForPDF() {
        if (!lastContextRecords || lastContextRecords.length === 0) {
            return [];
        }

        return lastContextRecords.slice(0, 10).map(record => ({
            name: record.p?.name || 'Unknown',
            address: record.precise_address || record.p?.location || 'Address not available',
            category: record.c || 'Unknown',
            rating: record.pg ? parseFloat(record.pg).toFixed(1) : 'N/A',
            comments: Array.isArray(record.co) ? record.co.slice(0, 3) : []
        }));
    }

    /**
     * Export PDF report
     */
    async function exportPdfReport(buttonElement) {
        // Disable button during export
        const originalText = buttonElement.innerHTML;
        buttonElement.disabled = true;
        buttonElement.innerHTML = '⏳ Generating...';

        try {
            // Capture map screenshot
            const mapScreenshot = captureMapScreenshot();
            if (!mapScreenshot) {
                throw new Error('Failed to capture map screenshot');
            }

            // Collect data
            const statistics = calculateStatistics();
            const conversation = getConversationHistory();
            const dataSources = getEnabledDataSources();
            const locations = formatLocationsForPDF();

            // Prepare export payload
            const exportPayload = {
                conversation: conversation,
                map_screenshot: mapScreenshot,
                locations: locations,
                statistics: statistics,
                data_sources: dataSources,
                timestamp: new Date().toISOString()
            };

            // Send to backend
            const response = await fetch('/export-pdf', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(exportPayload)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to generate PDF');
            }

            // Get PDF blob
            const blob = await response.blob();
            
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `city_layers_report_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.pdf`;
            document.body.appendChild(a);
            a.click();
            
            // Cleanup
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            // Show success message
            appendMessage('system', '✅ PDF report exported successfully!');

        } catch (error) {
            console.error('PDF export failed:', error);
            appendMessage('system', `❌ PDF export failed: ${error.message}`);
        } finally {
            // Re-enable button
            buttonElement.disabled = false;
            buttonElement.innerHTML = originalText;
        }
    }

    // ========================================================================
    // END OF PDF EXPORT FUNCTIONALITY
    // ========================================================================

})();
