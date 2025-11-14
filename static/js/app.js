/* Minimal client to handle chat and map rendering */
(function () {
    const chatForm = document.getElementById("chatForm");
    const chatInput = document.getElementById("chatInput");
    const chatWindow = document.getElementById("chatWindow");
    const scrollBottomBtn = document.getElementById("scrollBottomBtn");
    const sourceCityLayers = document.getElementById("source-citylayers");
    const expandBtn = document.getElementById("expandBtn");
    const leftContainer = document.querySelector(".left-container");
    const resizeHandle = document.querySelector(".resize-handle");
    let currentVizMode = "pydeck-heatmap";
    let cityLayersEnabled = true;
    let isResizing = false;
    
    // Persistent map state
    let mapState = {
        center: [20, 0],
        zoom: 2,
        features: [],
        shouldUpdateData: false
    };

    // Handle panel resizing with smooth drag
    if (resizeHandle) {
        let animationFrameId = null;
        
        resizeHandle.addEventListener("mousedown", (e) => {
            isResizing = true;
            document.body.style.cursor = "ew-resize";
            document.body.style.userSelect = "none";
            leftContainer.style.transition = "none";
            resizeHandle.style.backgroundColor = "rgba(1, 71, 81, 0.5)";
            
            // Prevent iframe from capturing mouse events during resize
            const mapContainer = document.getElementById("map");
            const iframe = mapContainer ? mapContainer.querySelector("iframe") : null;
            if (iframe) {
                iframe.style.pointerEvents = "none";
            }
            
            e.preventDefault();
        });

        document.addEventListener("mousemove", (e) => {
            if (!isResizing) return;
            
            if (animationFrameId) {
                cancelAnimationFrame(animationFrameId);
            }
            
            animationFrameId = requestAnimationFrame(() => {
                const newWidth = e.clientX;
                const minWidth = window.innerWidth * 0.2;  // 20% minimum
                const maxWidth = window.innerWidth * 0.6;  // 60% maximum
                
                if (newWidth >= minWidth && newWidth <= maxWidth) {
                    leftContainer.style.width = newWidth + "px";
                } else if (newWidth < minWidth) {
                    leftContainer.style.width = minWidth + "px";
                } else if (newWidth > maxWidth) {
                    leftContainer.style.width = maxWidth + "px";
                }
            });
        });

        document.addEventListener("mouseup", () => {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = "";
                document.body.style.userSelect = "";
                leftContainer.style.transition = "";
                resizeHandle.style.backgroundColor = "";
                
                // Re-enable iframe pointer events
                const mapContainer = document.getElementById("map");
                const iframe = mapContainer ? mapContainer.querySelector("iframe") : null;
                if (iframe) {
                    iframe.style.pointerEvents = "";
                }
                
                if (animationFrameId) {
                    cancelAnimationFrame(animationFrameId);
                    animationFrameId = null;
                }
            }
        });
    }

    // Handle window resize to keep panel within bounds
    window.addEventListener('resize', () => {
        if (leftContainer && !leftContainer.classList.contains('collapsed')) {
            const currentWidth = leftContainer.offsetWidth;
            const minWidth = window.innerWidth * 0.2;
            const maxWidth = window.innerWidth * 0.6;
            
            if (currentWidth < minWidth) {
                leftContainer.style.width = minWidth + "px";
            } else if (currentWidth > maxWidth) {
                leftContainer.style.width = maxWidth + "px";
            }
        }
    });

    // Get active data sources
    function getActiveDataSources() {
        const sources = [];
        if (cityLayersEnabled) sources.push("citylayers");
        return sources;
    }

    // Handle expand button - toggle collapse
    if (expandBtn) {
        expandBtn.addEventListener("click", () => {
            if (leftContainer.classList.contains("collapsed")) {
                leftContainer.classList.remove("collapsed");
                expandBtn.textContent = "◀";
            } else {
                leftContainer.classList.add("collapsed");
                expandBtn.textContent = "▶";
            }
        });
    }

    // Handle data source button clicks
    function setupDataSourceToggles() {
        if (sourceCityLayers) {
            sourceCityLayers.addEventListener("click", () => {
                cityLayersEnabled = !cityLayersEnabled;
                sourceCityLayers.classList.toggle("active");
                updateStatusIndicators();
                console.log("Active data sources:", getActiveDataSources());
            });
        }
    }

    // Update status indicators
    function updateStatusIndicators() {
        const buttons = [
            { btn: sourceCityLayers, enabled: cityLayersEnabled }
        ];

        buttons.forEach(({ btn, enabled }) => {
            if (btn) {
                const status = btn.querySelector('.source-status');
                if (status) {
                    status.textContent = enabled ? '●' : '○';
                    status.title = enabled ? 'Active' : 'Available';
                }
            }
        });
    }

    // Initialize data source toggles
    setupDataSourceToggles();
    
    // Draw rectangle button handler
    const drawRectangleBtn = document.getElementById("drawRectangleBtn");
    let isDrawingMode = false;
    
    if (drawRectangleBtn) {
        drawRectangleBtn.addEventListener("click", () => {
            // Only works in leaflet mode
            if (currentVizMode !== "leaflet") {
                setVizMode("leaflet");
                setTimeout(() => {
                    activateDrawMode();
                }, 500);
            } else {
                activateDrawMode();
            }
        });
    }
    
    function activateDrawMode() {
        if (!map || !drawControl) {
            ensureLeaflet();
            setTimeout(activateDrawMode, 100);
            return;
        }
        
        isDrawingMode = !isDrawingMode;
        
        if (isDrawingMode) {
            drawRectangleBtn.classList.add("active");
            // Trigger rectangle drawing
            new L.Draw.Rectangle(map, drawControl.options.draw.rectangle).enable();
        } else {
            drawRectangleBtn.classList.remove("active");
        }
    }

    // Global function to query about a location from map
    window.queryLocation = function(location, lat, lon) {
        const query = `Tell me about ${location} at coordinates (${lat.toFixed(6)}, ${lon.toFixed(6)})`;
        
        // Expand left panel if collapsed
        if (leftContainer.classList.contains("collapsed")) {
            leftContainer.classList.remove("collapsed");
            expandBtn.textContent = "◀";
        }
        
        // Directly send the message without populating input
        sendMessage(query);
    };
    
    // Global function to query about a region from map
    window.queryRegion = function() {
        if (!selectedRegion) {
            alert("Please select a region first by drawing a rectangle on the map.");
            return;
        }
        
        const query = `Tell me about locations in the region bounded by North: ${selectedRegion.north.toFixed(4)}°, South: ${selectedRegion.south.toFixed(4)}°, East: ${selectedRegion.east.toFixed(4)}°, West: ${selectedRegion.west.toFixed(4)}°`;
        
        // Expand left panel if collapsed
        if (leftContainer.classList.contains("collapsed")) {
            leftContainer.classList.remove("collapsed");
            expandBtn.textContent = "◀";
        }
        
        // Directly send the message without populating input
        sendMessage(query);
    };

    // Leaflet Map
    // We maintain Leaflet objects; PyDeck HTML will replace the container content
    let map = null;
    let markersLayer = null;
    let drawnItems = null;
    let drawControl = null;
    let selectedRegion = null;
    
    function ensureLeaflet() {
        if (map) return;
        map = L.map("map", {
            center: mapState.center,
            zoom: mapState.zoom,
        });
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "&copy; OpenStreetMap contributors",
        }).addTo(map);
        markersLayer = L.layerGroup().addTo(map);
        
        // Track map movements to persist state
        map.on('moveend', function() {
            mapState.center = [map.getCenter().lat, map.getCenter().lng];
            mapState.zoom = map.getZoom();
        });
        
        // Initialize drawing layer
        drawnItems = new L.FeatureGroup();
        map.addLayer(drawnItems);
        
        // Add draw controls (hidden by default, controlled by custom button)
        drawControl = new L.Control.Draw({
            position: 'topright',
            draw: {
                polyline: false,
                polygon: false,
                circle: false,
                marker: false,
                circlemarker: false,
                rectangle: {
                    shapeOptions: {
                        color: '#014751',
                        weight: 3,
                        fillOpacity: 0.1
                    }
                }
            },
            edit: {
                featureGroup: drawnItems,
                remove: true
            }
        });
        // Don't add the control to map - we'll use custom button
        // map.addControl(drawControl);
        
        // Handle rectangle drawn
        map.on(L.Draw.Event.CREATED, function (event) {
            const layer = event.layer;
            drawnItems.clearLayers();
            drawnItems.addLayer(layer);
            
            // Deactivate drawing mode
            isDrawingMode = false;
            if (drawRectangleBtn) {
                drawRectangleBtn.classList.remove("active");
            }
            
            const bounds = layer.getBounds();
            selectedRegion = {
                north: bounds.getNorth(),
                south: bounds.getSouth(),
                east: bounds.getEast(),
                west: bounds.getWest()
            };
            
            // Show popup with query button
            let popupContent = `<div style="font-family: 'Space Grotesk', sans-serif; max-width: 300px;">`;
            popupContent += `<strong style="font-size: 14px; color: #014751; display: block; margin-bottom: 8px;">📐 Selected Region</strong>`;
            popupContent += `<div style="font-size: 11px; color: #666; margin-bottom: 10px;">`;
            popupContent += `<div><strong>North:</strong> ${selectedRegion.north.toFixed(6)}°</div>`;
            popupContent += `<div><strong>South:</strong> ${selectedRegion.south.toFixed(6)}°</div>`;
            popupContent += `<div><strong>East:</strong> ${selectedRegion.east.toFixed(6)}°</div>`;
            popupContent += `<div><strong>West:</strong> ${selectedRegion.west.toFixed(6)}°</div>`;
            popupContent += `</div>`;
            popupContent += `<button onclick="window.queryRegion()" 
                style="margin-top: 8px; padding: 8px 16px; background: #014751; color: white; border: none; 
                border-radius: 6px; cursor: pointer; font-size: 13px; width: 100%; font-weight: 500;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                🗺️ Ask about this region
            </button>`;
            popupContent += `</div>`;
            
            layer.bindPopup(popupContent).openPopup();
        });
        
        // Handle layer deletion
        map.on(L.Draw.Event.DELETED, function (event) {
            selectedRegion = null;
        });
    }

    function isNearBottom() {
        const threshold = 80; // px
        return chatWindow.scrollHeight - chatWindow.scrollTop - chatWindow.clientHeight < threshold;
    }
    function scrollToBottom(smooth = true) {
        chatWindow.scrollTo({ top: chatWindow.scrollHeight, behavior: smooth ? "smooth" : "auto" });
    }
    function updateScrollButtonVisibility() {
        if (isNearBottom()) {
            scrollBottomBtn.classList.add("d-none");
        } else {
            scrollBottomBtn.classList.remove("d-none");
        }
    }
    function appendMessage(role, text) {
        const shouldAutoScroll = isNearBottom();
        const div = document.createElement("div");
        div.className = role;
        div.textContent = text;
        chatWindow.appendChild(div);
        if (shouldAutoScroll) {
            scrollToBottom(true);
        } else {
            updateScrollButtonVisibility();
        }
    }
    function appendMessageHTML(role, html) {
        const shouldAutoScroll = isNearBottom();
        const div = document.createElement("div");
        div.className = role;
        
        // Count lines in the HTML content
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        const textContent = tempDiv.textContent || tempDiv.innerText || '';
        const lineCount = textContent.split('\n').length;
        
        // If more than 10 lines, make it collapsible
        if (lineCount > 10) {
            div.classList.add('collapsible-message', 'collapsed');
            
            const content = document.createElement('div');
            content.className = 'collapsible-content';
            content.innerHTML = html;
            
            const toggleBtn = document.createElement('button');
            toggleBtn.className = 'collapse-toggle-btn';
            toggleBtn.innerHTML = `▼ Expand (${lineCount} lines)`;
            
            toggleBtn.addEventListener('click', function() {
                if (div.classList.contains('collapsed')) {
                    div.classList.remove('collapsed');
                    toggleBtn.innerHTML = `▲ Collapse (${lineCount} lines)`;
                } else {
                    div.classList.add('collapsed');
                    toggleBtn.innerHTML = `▼ Expand (${lineCount} lines)`;
                }
            });
            
            div.appendChild(content);
            div.appendChild(toggleBtn);
        } else {
            div.innerHTML = html;
        }
        
        chatWindow.appendChild(div);
        if (shouldAutoScroll) {
            scrollToBottom(true);
        } else {
            updateScrollButtonVisibility();
        }
    }

    async function sendMessage(message) {
        appendMessage("user", message);
        appendMessage("assistant pending", "...");
        try {
            const res = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    message,
                    data_sources: getActiveDataSources()
                }),
            });
            const data = await res.json();
            // Remove pending
            const pending = chatWindow.querySelector(".assistant.pending");
            if (pending) pending.remove();
            if (data.ok) {
                // Flag that new data should be fetched on next map refresh
                mapState.shouldUpdateData = true;
                
                // Always render as HTML if available, otherwise render as text
                if (data.answer_html) {
                    appendMessageHTML("assistant", data.answer_html);
                } else if (data.answer) {
                    appendMessage("assistant", data.answer);
                }
                
                // If there's a visualization recommendation, handle it
                if (data.visualization_recommendation) {
                    const recommendedType = data.visualization_recommendation.type;
                    const vizMode = `pydeck-${recommendedType}`;
                    
                    // Show simple message
                    appendMessage("system", `Visualized in: ${recommendedType.toUpperCase()}`);
                    setTimeout(() => {
                        setVizMode(vizMode);
                    }, 500);
                }
            } else {
                appendMessage("assistant error", data.error || "Error");
            }
        } catch (e) {
            const pending = chatWindow.querySelector(".assistant.pending");
            if (pending) pending.remove();
            appendMessage("assistant error", String(e));
        }
    }

    async function refreshMapLeaflet() {
        const mapContainer = document.getElementById("map");
        // If map container has iframe, clear it and recreate map div
        if (mapContainer.querySelector("iframe")) {
            if (map) {
                // Save current state before destroying
                mapState.center = [map.getCenter().lat, map.getCenter().lng];
                mapState.zoom = map.getZoom();
                map.remove();
                map = null;
                markersLayer = null;
                drawnItems = null;
                drawControl = null;
                selectedRegion = null;
            }
            mapContainer.innerHTML = '<div id="map" class="mappanel"></div>';
            // Update reference to new map div
            const newMapDiv = mapContainer.querySelector("#map");
            if (newMapDiv) {
                newMapDiv.id = "leaflet-map-container";
                map = L.map(newMapDiv, {
                    center: mapState.center,
                    zoom: mapState.zoom,
                });
                L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
                    attribution: "&copy; OpenStreetMap contributors",
                }).addTo(map);
                markersLayer = L.layerGroup().addTo(map);
                
                // Track map movements
                map.on('moveend', function() {
                    mapState.center = [map.getCenter().lat, map.getCenter().lng];
                    mapState.zoom = map.getZoom();
                });
                
                // Reinitialize drawing controls
                drawnItems = new L.FeatureGroup();
                map.addLayer(drawnItems);
                
                drawControl = new L.Control.Draw({
                    position: 'topright',
                    draw: {
                        polyline: false,
                        polygon: false,
                        circle: false,
                        marker: false,
                        circlemarker: false,
                        rectangle: {
                            shapeOptions: {
                                color: '#014751',
                                weight: 3,
                                fillOpacity: 0.1
                            }
                        }
                    },
                    edit: {
                        featureGroup: drawnItems,
                        remove: true
                    }
                });
                // Don't add the control to map - we'll use custom button
                // map.addControl(drawControl);
                
                // Handle rectangle drawn
                map.on(L.Draw.Event.CREATED, function (event) {
                    const layer = event.layer;
                    drawnItems.clearLayers();
                    drawnItems.addLayer(layer);
                    
                    // Deactivate drawing mode
                    isDrawingMode = false;
                    if (drawRectangleBtn) {
                        drawRectangleBtn.classList.remove("active");
                    }
                    
                    const bounds = layer.getBounds();
                    selectedRegion = {
                        north: bounds.getNorth(),
                        south: bounds.getSouth(),
                        east: bounds.getEast(),
                        west: bounds.getWest()
                    };
                    
                    // Show popup with query button
                    let popupContent = `<div style="font-family: 'Space Grotesk', sans-serif; max-width: 300px;">`;
                    popupContent += `<strong style="font-size: 14px; color: #014751; display: block; margin-bottom: 8px;">📐 Selected Region</strong>`;
                    popupContent += `<div style="font-size: 11px; color: #666; margin-bottom: 10px;">`;
                    popupContent += `<div><strong>North:</strong> ${selectedRegion.north.toFixed(6)}°</div>`;
                    popupContent += `<div><strong>South:</strong> ${selectedRegion.south.toFixed(6)}°</div>`;
                    popupContent += `<div><strong>East:</strong> ${selectedRegion.east.toFixed(6)}°</div>`;
                    popupContent += `<div><strong>West:</strong> ${selectedRegion.west.toFixed(6)}°</div>`;
                    popupContent += `</div>`;
                    popupContent += `<button onclick="window.queryRegion()" 
                        style="margin-top: 8px; padding: 8px 16px; background: #014751; color: white; border: none; 
                        border-radius: 6px; cursor: pointer; font-size: 13px; width: 100%; font-weight: 500;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        🗺️ Ask about this region
                    </button>`;
                    popupContent += `</div>`;
                    
                    layer.bindPopup(popupContent).openPopup();
                });
                
                // Handle layer deletion
                map.on(L.Draw.Event.DELETED, function (event) {
                    selectedRegion = null;
                });
            }
        } else {
            ensureLeaflet();
        }
        
        try {
            // Only fetch new data if flagged to update
            let isNewData = mapState.shouldUpdateData;
            if (isNewData) {
                const res = await fetch("/map-data");
                const data = await res.json();
                if (data.ok) {
                    mapState.features = data.features || [];
                }
                mapState.shouldUpdateData = false;
            }
            
            const features = mapState.features;
            markersLayer.clearLayers();
            if (features.length === 0) {
                return;
            }
            
            const bounds = [];
            features.forEach((f) => {
                const lat = f.lat;
                const lon = f.lon;
                const location = f.location || "Unknown Location";
                
                // Build comprehensive popup content with all available information
                let popupContent = `<div style="font-family: 'Space Grotesk', sans-serif; max-width: 340px; line-height: 1.6;">`;
                
                // Header with location name
                popupContent += `<div style="background: linear-gradient(135deg, #014751 0%, #026270 100%); 
                    padding: 12px; margin: -10px -10px 12px -10px; border-radius: 8px 8px 0 0;">`;
                popupContent += `<strong style="font-size: 17px; color: white; display: block; text-shadow: 0 1px 2px rgba(0,0,0,0.2);">
                    📍 ${location}</strong>`;
                popupContent += `</div>`;
                
                // Grade/Rating section (if available) - show prominently
                if (f.grade) {
                    popupContent += `<div style="background: #fff3cd; padding: 8px 10px; border-radius: 6px; margin-bottom: 10px; 
                        border-left: 3px solid #ffc107;">`;
                    popupContent += `<div style="font-size: 13px; color: #856404;">`;
                    popupContent += `<strong>⭐ Grade:</strong> <span style="font-size: 15px; font-weight: 700;">${f.grade}</span>`;
                    popupContent += `</div></div>`;
                }
                
                // Category & Subcategory section
                if (f.category || f.subcategory) {
                    popupContent += `<div style="background: #e7f3ff; padding: 8px 10px; border-radius: 6px; margin-bottom: 10px; 
                        border-left: 3px solid #2196F3;">`;
                    popupContent += `<div style="font-size: 11px; color: #014751; font-weight: 600; margin-bottom: 4px;">📂 CLASSIFICATION</div>`;
                    if (f.category) {
                        popupContent += `<div style="font-size: 12px; color: #333; margin-bottom: 2px;">`;
                        popupContent += `<strong>Category:</strong> ${f.category}</div>`;
                    }
                    if (f.subcategory) {
                        popupContent += `<div style="font-size: 12px; color: #333;">`;
                        popupContent += `<strong>Subcategory:</strong> ${f.subcategory}</div>`;
                    }
                    popupContent += `</div>`;
                }
                
                // Comments/Description section
                if (f.comments) {
                    popupContent += `<div style="background: #f0f8f0; padding: 8px 10px; border-radius: 6px; margin-bottom: 10px; 
                        border-left: 3px solid #4CAF50;">`;
                    popupContent += `<div style="font-size: 11px; color: #014751; font-weight: 600; margin-bottom: 4px;">💬 COMMENTS</div>`;
                    const commentText = String(f.comments);
                    const displayComment = commentText.length > 80 ? commentText.substring(0, 77) + '...' : commentText;
                    popupContent += `<div style="font-size: 12px; color: #333; font-style: italic;">${displayComment}</div>`;
                    popupContent += `</div>`;
                }
                
                // Coordinates section
                popupContent += `<div style="background: #f8f9fa; padding: 8px 10px; border-radius: 6px; margin-bottom: 10px; 
                    border-left: 3px solid #014751;">`;
                popupContent += `<div style="font-size: 11px; color: #014751; font-weight: 600; margin-bottom: 4px;">📍 COORDINATES</div>`;
                popupContent += `<div style="font-size: 12px; color: #333; font-family: 'Courier New', monospace;">`;
                popupContent += `Lat: ${lat.toFixed(6)}<br>Lon: ${lon.toFixed(6)}</div>`;
                popupContent += `</div>`;
                
                // Other information section (excluding the priority fields already shown)
                const priorityFields = ['lat', 'lon', 'location', 'category', 'subcategory', 'comments', 'grade', 'rating'];
                const infoFields = Object.keys(f).filter(key => 
                    !priorityFields.includes(key) && f[key] && String(f[key]).trim()
                );
                
                if (infoFields.length > 0) {
                    popupContent += `<div style="background: white; padding: 10px; border-radius: 6px; margin-bottom: 10px; 
                        border: 1px solid #e0e0e0;">`;
                    popupContent += `<div style="font-size: 11px; color: #014751; font-weight: 600; margin-bottom: 8px;">📋 ADDITIONAL INFO</div>`;
                    
                    infoFields.forEach(key => {
                        const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                        let icon = '📝';
                        if (key.includes('id')) icon = '🔑';
                        else if (key.includes('type')) icon = '🏷️';
                        else if (key.includes('description')) icon = '📄';
                        else if (key.includes('address')) icon = '🏠';
                        else if (key.includes('phone')) icon = '📞';
                        else if (key.includes('email')) icon = '📧';
                        else if (key.includes('website') || key.includes('url')) icon = '🌐';
                        
                        const value = String(f[key]);
                        const displayValue = value.length > 50 ? value.substring(0, 47) + '...' : value;
                        
                        popupContent += `<div style="margin-bottom: 6px; font-size: 12px;">`;
                        popupContent += `<span style="color: #666; font-weight: 500;">${icon} ${label}:</span> `;
                        popupContent += `<span style="color: #333;">${displayValue}</span>`;
                        popupContent += `</div>`;
                    });
                    
                    popupContent += `</div>`;
                }
                
                // Action button
                popupContent += `<button onclick="window.queryLocation('${location.replace(/'/g, "\\'")}', ${lat}, ${lon})" 
                    style="margin-top: 4px; padding: 10px 16px; background: linear-gradient(135deg, #014751 0%, #026270 100%); 
                    color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; width: 100%; 
                    font-weight: 600; box-shadow: 0 3px 6px rgba(1,71,81,0.3); transition: all 0.2s ease;
                    letter-spacing: 0.3px;">
                    💬 Get Detailed Information
                </button>`;
                
                popupContent += `</div>`;
                
                const marker = L.marker([lat, lon]);
                marker.bindPopup(popupContent, { maxWidth: 380, className: 'custom-popup' });
                marker.addTo(markersLayer);
                bounds.push([lat, lon]);
            });
            // Only auto-fit bounds if this is new data, otherwise preserve zoom/position
            if (bounds.length > 0 && isNewData) {
                map.fitBounds(bounds, { padding: [20, 20] });
            }
        } catch (e) {
            // no-op
        }
    }
    async function refreshMapPydeck(mode) {
        // mode: scatter | heatmap | hexagon
        const mapContainer = document.getElementById("map");
        // Render as iframe so the full HTML (with scripts) executes properly
        try {
            // Save current map state before destroying Leaflet map
            if (map) {
                mapState.center = [map.getCenter().lat, map.getCenter().lng];
                mapState.zoom = map.getZoom();
                map.remove();
                map = null;
                markersLayer = null;
            }
            
            // Pass map state to PyDeck for consistent view
            const params = new URLSearchParams({
                mode: mode,
                lat: mapState.center[0],
                lon: mapState.center[1],
                zoom: mapState.zoom
            });
            
            const src = `/pydeck?${params.toString()}`;
            mapContainer.innerHTML = `<iframe src="${src}" style="width:100%;height:100%;border:0;" allowfullscreen></iframe>`;
        } catch (e) {
            mapContainer.innerHTML = `<div style="padding:12px;color:#b00020;">${String(e)}</div>`;
        }
    }

    function setVizMode(mode) {
        currentVizMode = mode;
        // Update active state
        document.querySelectorAll(".vischoice").forEach((el) => {
            el.classList.remove("selected");
        });
        const activeEl = document.querySelector(`[data-mode="${mode}"]`);
        if (activeEl) {
            activeEl.classList.add("selected");
        }
        // Update map
        if (mode === "leaflet") {
            refreshMapLeaflet();
        } else if (mode.startsWith("pydeck-")) {
            const pydeckMode = mode.replace("pydeck-", "");
            refreshMapPydeck(pydeckMode);
        } else {
            refreshMapLeaflet();
        }
    }

    // Initialize visualization mode selector
    document.querySelectorAll(".vischoice").forEach((option) => {
        option.addEventListener("click", (e) => {
            const mode = option.getAttribute("data-mode");
            if (mode) {
                setVizMode(mode);
            }
        });
    });

    // Set default mode
    setVizMode("pydeck-heatmap");

    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const msg = chatInput.value.trim();
        if (!msg) return;
        chatInput.value = "";
        sendMessage(msg);
        // Auto-refresh map after sending message
        setTimeout(() => {
            if (currentVizMode === "leaflet") {
                refreshMapLeaflet();
            } else if (currentVizMode.startsWith("pydeck-")) {
                const pydeckMode = currentVizMode.replace("pydeck-", "");
                refreshMapPydeck(pydeckMode);
            }
        }, 500);
    });

    chatWindow.addEventListener("scroll", () => {
        updateScrollButtonVisibility();
    });
    scrollBottomBtn.addEventListener("click", () => {
        scrollToBottom(true);
        updateScrollButtonVisibility();
    });
    // Initial state
    updateScrollButtonVisibility();
})();



