/* Minimal client to handle chat and map rendering */
(function () {
    const chatForm = document.getElementById("chatForm");
    const chatInput = document.getElementById("chatInput");
    const chatWindow = document.getElementById("chatWindow");
    const scrollBottomBtn = document.getElementById("scrollBottomBtn");
    const sourceCityLayers = document.getElementById("source-citylayers");
    const sourceOSM = document.getElementById("source-osm");
    const collapseBtn = document.getElementById("collapseBtn");
    const expandBtn = document.getElementById("expandBtn");
    const leftContainer = document.querySelector(".left-container");
    let currentVizMode = "pydeck-heatmap";
    let hasNeo4jData = false;
    let hasOSMData = false;
    let cityLayersEnabled = true;
    let osmEnabled = true;

    // Update data sources display
    function updateDataSources() {
        if (hasNeo4jData) {
            sourceCityLayers.style.display = "flex";
        } else {
            sourceCityLayers.style.display = "none";
        }
        
        if (hasOSMData) {
            sourceOSM.style.display = "flex";
        } else {
            sourceOSM.style.display = "none";
        }
    }

    // Handle collapse/expand
    if (collapseBtn) {
        collapseBtn.addEventListener("click", () => {
            leftContainer.classList.add("collapsed");
            expandBtn.classList.add("show");
        });
    }

    if (expandBtn) {
        expandBtn.addEventListener("click", () => {
            leftContainer.classList.remove("collapsed");
            expandBtn.classList.remove("show");
        });
    }

    // Handle data source button clicks
    function setupDataSourceToggles() {
        if (sourceCityLayers) {
            sourceCityLayers.addEventListener("click", () => {
                cityLayersEnabled = !cityLayersEnabled;
                sourceCityLayers.classList.toggle("active");
                handleDataSourceToggle();
            });
        }

        if (sourceOSM) {
            sourceOSM.addEventListener("click", () => {
                osmEnabled = !osmEnabled;
                sourceOSM.classList.toggle("active");
                handleDataSourceToggle();
            });
        }
    }

    // Handle data source toggle
    function handleDataSourceToggle() {
        // Refresh the current visualization with the new data source settings
        setVizMode(currentVizMode);
        
        // Show a message about what's enabled
        const enabledSources = [];
        if (cityLayersEnabled) enabledSources.push("CityLayers");
        if (osmEnabled) enabledSources.push("OpenStreetMap");
        
        if (enabledSources.length > 0) {
            console.log("Active data sources:", enabledSources.join(", "));
        } else {
            console.log("No data sources selected");
        }
    }

    // Initialize data source toggles
    setupDataSourceToggles();

    // Leaflet Map
    // We maintain Leaflet objects; PyDeck HTML will replace the container content
    let map = null;
    let markersLayer = null;
    function ensureLeaflet() {
        if (map) return;
        map = L.map("map", {
            center: [20, 0],
            zoom: 2,
        });
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "&copy; OpenStreetMap contributors",
        }).addTo(map);
        markersLayer = L.layerGroup().addTo(map);
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
        div.innerHTML = html;
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
                body: JSON.stringify({ message }),
            });
            const data = await res.json();
            // Remove pending
            const pending = chatWindow.querySelector(".assistant.pending");
            if (pending) pending.remove();
            if (data.ok) {
                if (data.answer_html) {
                    appendMessageHTML("assistant", data.answer_html);
                } else {
                    appendMessage("assistant", data.answer);
                }
                
                // Mark that we have Neo4j data
                hasNeo4jData = true;
                updateDataSources();
                
                // If there's a visualization recommendation, handle it
                if (data.visualization_recommendation) {
                    const recommendedType = data.visualization_recommendation.type;
                    const vizMode = `pydeck-${recommendedType}`;
                    
                    // Check if choropleth is recommended and OSM boundaries needed
                    if (recommendedType === "choropleth") {
                        // Ask user for permission to fetch OSM boundaries
                        const userConfirm = confirm("Choropleth visualization works best with area boundaries. Fetch boundaries from OpenStreetMap?");
                        
                        if (userConfirm) {
                            appendMessage("system", "Fetching area boundaries from OpenStreetMap...");
                            
                            // Fetch OSM boundaries
                            fetch("/osm-layer?feature_type=boundary&feature_value=administrative")
                                .then(res => res.json())
                                .then(osmData => {
                                    if (osmData.ok && osmData.count > 0) {
                                        appendMessage("system", `✓ Loaded ${osmData.count} area boundaries`);
                                        hasOSMData = true;
                                        updateDataSources();
                                    }
                                    // Switch to visualization
                                    appendMessage("system", `Visualized in: ${recommendedType.toUpperCase()}`);
                                    setTimeout(() => {
                                        setVizMode(vizMode);
                                    }, 500);
                                })
                                .catch(err => {
                                    appendMessage("system", "⚠ Could not fetch boundaries, using available data");
                                    appendMessage("system", `Visualized in: ${recommendedType.toUpperCase()}`);
                                    setTimeout(() => {
                                        setVizMode(vizMode);
                                    }, 500);
                                });
                        } else {
                            // User declined, just switch visualization
                            appendMessage("system", `Visualized in: ${recommendedType.toUpperCase()}`);
                            setTimeout(() => {
                                setVizMode(vizMode);
                            }, 500);
                        }
                    } else {
                        // For other visualization types, just show simple message
                        appendMessage("system", `Visualized in: ${recommendedType.toUpperCase()}`);
                        setTimeout(() => {
                            setVizMode(vizMode);
                        }, 500);
                    }
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
                map.remove();
                map = null;
                markersLayer = null;
            }
            mapContainer.innerHTML = '<div id="map" class="mappanel"></div>';
            // Update reference to new map div
            const newMapDiv = mapContainer.querySelector("#map");
            if (newMapDiv) {
                newMapDiv.id = "leaflet-map-container";
                map = L.map(newMapDiv, {
                    center: [20, 0],
                    zoom: 2,
                });
                L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
                    attribution: "&copy; OpenStreetMap contributors",
                }).addTo(map);
                markersLayer = L.layerGroup().addTo(map);
            }
        } else {
            ensureLeaflet();
        }
        
        try {
            const res = await fetch("/map-data");
            const data = await res.json();
            if (!data.ok) return;
            const features = data.features || [];
            markersLayer.clearLayers();
            if (features.length === 0) {
                return;
            }
            const bounds = [];
            features.forEach((f) => {
                const lat = f.lat;
                const lon = f.lon;
                const location = f.location || "Unknown Location";
                
                // Build popup content with all available information
                let popupContent = `<div style="font-family: 'Space Grotesk', sans-serif; max-width: 250px;">`;
                popupContent += `<strong style="font-size: 14px; color: #014751;">${location}</strong><br/>`;
                
                // Add coordinates
                popupContent += `<div style="margin-top: 8px; font-size: 12px; color: #666;">`;
                popupContent += `<strong>Coordinates:</strong> ${lat.toFixed(6)}, ${lon.toFixed(6)}<br/>`;
                
                // Add other available fields
                Object.keys(f).forEach(key => {
                    if (key !== 'lat' && key !== 'lon' && key !== 'location' && f[key]) {
                        const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                        popupContent += `<strong>${label}:</strong> ${f[key]}<br/>`;
                    }
                });
                
                popupContent += `</div></div>`;
                
                const marker = L.marker([lat, lon]);
                marker.bindPopup(popupContent);
                marker.addTo(markersLayer);
                bounds.push([lat, lon]);
            });
            if (bounds.length > 0) {
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
            // Reset Leaflet objects to be lazily re-created when needed
            if (map) {
                map.remove();
                map = null;
                markersLayer = null;
            }
            const src = `/pydeck?mode=${encodeURIComponent(mode)}`;
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



