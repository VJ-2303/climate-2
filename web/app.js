/**
 * HeatViz Climate Intelligence Platform — Interactive Application Core
 */

const RISK_COLORS = {
  Critical: "#991b1b",
  High: "#c2410c",
  Medium: "#d97706",
  Low: "#047857",
};

const BLUE_SCALE = ["#eff6ff", "#bfdbfe", "#60a5fa", "#2563eb", "#1e3a8a"];

const LAYER_TITLES = {
  hvi: "Heat Vulnerability Index (HVI)",
  ai_heat_exposure_blocks: "Surface Heat Exposure",
  ndvi_blocks: "Tree Canopy & Greenery (NDVI)",
  ndbi_blocks: "Tin Roofs & Impervious (NDBI)",
  population_density_blocks: "Population Density",
  cooling_deficit_blocks: "Cooling Access Deficit",
};

const CENTER = [-1.317, 36.789];
const DEFAULT_ZOOM = 15;

// Global Application State
let map;
let primaryData = null;
let currentLayer = null;
let selectedFeatureLayer = null;
let currentActiveLayerName = "hvi";
let currentRiskFilter = "All";
let currentThreshold = 0;
const layerCache = {};
const blockIntelligenceCache = {};

document.addEventListener("DOMContentLoaded", initApp);

function initApp() {
  // 1. Initialize Leaflet Map
  map = L.map("map", {
    renderer: L.canvas({ padding: 0.5 }),
    zoomControl: false,
  }).setView(CENTER, DEFAULT_ZOOM);

  // Position zoom controls in bottom-right
  L.control.zoom({ position: "bottomright" }).addTo(map);

  // Clean CartoDB Positron Basemap
  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; CARTO',
    subdomains: "abcd",
    maxZoom: 19,
  }).addTo(map);

  // Map background click closes drawer & dropdowns
  map.on("click", (e) => {
    if (!e.originalEvent._stoppedByFeature) {
      closeSidebar();
      closeLayerDropdown();
    }
  });

  setupEventListeners();
  loadPrimaryData();
  updateLegend("hvi");
}

// 2. Data Loading Engine
async function loadPrimaryData() {
  showLoading(true);
  try {
    const response = await fetch("/data/vulnerability_blocks.geojson");
    if (!response.ok) throw new Error("Failed to fetch primary dataset");
    primaryData = await response.json();
    renderPrimaryLayer();
  } catch (error) {
    console.error("Failed to load primary data:", error);
    alert("Could not load vulnerability dataset. Please verify the server is running.");
  } finally {
    showLoading(false);
  }
}

function showLoading(show) {
  const overlay = document.getElementById("loading-overlay");
  if (overlay) {
    overlay.style.opacity = show ? "1" : "0";
    overlay.style.pointerEvents = show ? "all" : "none";
  }
}

// 3. Primary HVI Layer Rendering
function renderPrimaryLayer() {
  if (currentLayer) {
    map.removeLayer(currentLayer);
  }

  currentLayer = L.geoJSON(primaryData, {
    style: getPrimaryStyle,
    onEachFeature: onEachPrimaryFeature,
  }).addTo(map);

  applyFilters();
}

function getPrimaryStyle(feature) {
  return {
    stroke: false,
    fillOpacity: 0.65,
    fillColor: RISK_COLORS[feature.properties.risk_class] || "#94a3b8",
  };
}

function onEachPrimaryFeature(feature, layer) {
  const props = feature.properties;
  const tempVal = props.surface_temp_celsius !== undefined
    ? props.surface_temp_celsius.toFixed(1)
    : (20.24 + ((props.ai_heat_exposure || 50) / 100) * 18.37).toFixed(1);

  layer.bindTooltip(
    `<strong>${props.block_id}</strong> &bull; <span style="color:#f59e0b;font-weight:700;">${tempVal}°C</span> &bull; HVI: ${props.hvi_score} (${props.risk_class})`,
    { sticky: true, className: "custom-map-tooltip" }
  );

  layer.on({
    mouseover: (e) => highlightFeature(e.target),
    mouseout: (e) => resetHighlight(e.target),
    click: (e) => {
      e.originalEvent._stoppedByFeature = true;
      selectFeature(e.target, feature.properties);
    },
  });
}

function highlightFeature(layer) {
  if (layer === selectedFeatureLayer) return;
  if (layer.options.fillOpacity === 0) return;

  layer.setStyle({
    stroke: true,
    weight: 2,
    color: "#0f172a",
    opacity: 1,
  });

  if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
    layer.bringToFront();
  }
}

function resetHighlight(layer, force = false) {
  if (layer === selectedFeatureLayer && !force) return;
  if (layer.options.fillOpacity === 0) return;

  if (currentLayer) {
    currentLayer.resetStyle(layer);
  }
}

function selectFeature(layer, properties) {
  if (layer.options.fillOpacity === 0) return;

  if (selectedFeatureLayer) {
    resetHighlight(selectedFeatureLayer, true);
  }

  selectedFeatureLayer = layer;

  layer.setStyle({
    stroke: true,
    weight: 2.5,
    color: "#000000",
    opacity: 1,
  });

  if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
    layer.bringToFront();
  }

  openSidebar(properties);
}

// 4. Layer Switching Manager
async function switchLayer(layerName) {
  currentActiveLayerName = layerName;
  showLoading(true);
  closeLayerDropdown();

  // Update button label
  const title = LAYER_TITLES[layerName] || layerName;
  const labelEl = document.getElementById("active-layer-name");
  if (labelEl) labelEl.textContent = title;

  // Update active state in dropdown
  document.querySelectorAll(".menu-layer-item").forEach((item) => {
    if (item.getAttribute("data-layer") === layerName) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  try {
    if (layerName === "hvi") {
      renderPrimaryLayer();
      updateLegend("hvi");
    } else {
      const data = await fetchThematicData(layerName);
      renderThematicLayer(layerName, data);
      updateLegend("blue", LAYER_TITLES[layerName]);
    }
  } catch (err) {
    console.error("Error switching layer:", err);
  } finally {
    showLoading(false);
  }
}

async function fetchThematicData(layerName) {
  if (layerCache[layerName]) return layerCache[layerName];

  const res = await fetch(`/data/layers/${layerName}.geojson`);
  if (!res.ok) throw new Error(`Failed to load ${layerName}`);

  const data = await res.json();
  layerCache[layerName] = data;
  return data;
}

function renderThematicLayer(layerName, data) {
  if (currentLayer) map.removeLayer(currentLayer);

  const propName = layerName.replace("_blocks", "");

  currentLayer = L.geoJSON(data, {
    style: (feature) => {
      const val = feature.properties[propName];
      return {
        stroke: false,
        fillOpacity: 0.65,
        fillColor: getBlueColor(val),
      };
    },
    onEachFeature: (feature, layer) => {
      layer.bindTooltip(
        `<strong>${feature.properties.block_id}</strong> &bull; ${LAYER_TITLES[layerName] || propName}: ${feature.properties[propName]}`,
        { sticky: true, className: "custom-map-tooltip" }
      );

      layer.on({
        mouseover: (e) => highlightFeature(e.target),
        mouseout: (e) => resetHighlight(e.target),
        click: (e) => {
          e.originalEvent._stoppedByFeature = true;
          if (primaryData) {
            const primaryFeature = primaryData.features.find(
              (f) => f.properties.block_id === feature.properties.block_id
            );
            if (primaryFeature) {
              selectFeature(layer, primaryFeature.properties);
            }
          }
        },
      });
    },
  }).addTo(map);

  applyFilters();
}

function getBlueColor(val) {
  if (val === undefined || val === null) return "#cbd5e1";
  if (val <= 20) return BLUE_SCALE[0];
  if (val <= 40) return BLUE_SCALE[1];
  if (val <= 60) return BLUE_SCALE[2];
  if (val <= 80) return BLUE_SCALE[3];
  return BLUE_SCALE[4];
}

// 5. Clean Sector Profile Drawer Controller
async function openSidebar(props) {
  const drawer = document.getElementById("sidebar");
  const loadingEl = document.getElementById("drawer-loading");
  const detailEl = document.getElementById("sidebar-detail");

  if (drawer) {
    drawer.classList.add("open");
  }

  if (loadingEl) loadingEl.style.display = "flex";
  if (detailEl) detailEl.style.display = "none";

  const blockId = props.block_id;

  try {
    let intelligenceData;
    if (blockIntelligenceCache[blockId]) {
      intelligenceData = blockIntelligenceCache[blockId];
    } else {
      const response = await fetch(`/api/blocks/${blockId}`);
      if (response.ok) {
        intelligenceData = await response.json();
        blockIntelligenceCache[blockId] = intelligenceData;
      } else {
        intelligenceData = generateFallbackIntelligence(props);
      }
    }
    renderBlockIntelligence(intelligenceData);
  } catch (err) {
    console.warn("Could not fetch sector intelligence, using fallback:", err);
    renderBlockIntelligence(generateFallbackIntelligence(props));
  } finally {
    if (loadingEl) loadingEl.style.display = "none";
    if (detailEl) detailEl.style.display = "flex";
  }
}

function renderBlockIntelligence(data) {
  const setText = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text !== undefined && text !== null ? text : "—";
  };

  // 1. Header Card (ID, Risk Badge, KPIs)
  setText("detail-block-id", data.block_id);
  const badge = document.getElementById("detail-risk-badge");
  if (badge) {
    const risk = data.risk_class || "Medium";
    badge.textContent = `${risk.toUpperCase()} RISK`;
    badge.className = `risk-badge risk-${risk.toLowerCase()}`;
  }

  setText("detail-hvi-score", data.hvi_score);
  setText("detail-population", `~${data.population || 0}`);

  // Surface Temperature KPI
  const tempNum = data.surface_temp_celsius !== undefined ? data.surface_temp_celsius : 28.7;
  const tempEl = document.getElementById("detail-surface-temp");
  if (tempEl) {
    tempEl.textContent = `${tempNum.toFixed(1)}°C`;
    tempEl.className = `kpi-val temp-kpi-val ${tempNum >= 31.0 ? "temp-hot" : (tempNum <= 26.0 ? "temp-cool" : "temp-mild")}`;
  }

  // Temperature Anomaly KPI
  const anomNum = data.temp_anomaly_celsius !== undefined ? data.temp_anomaly_celsius : (tempNum - 28.7);
  const anomEl = document.getElementById("detail-temp-anomaly");
  if (anomEl) {
    anomEl.textContent = `${anomNum > 0 ? "+" : ""}${anomNum.toFixed(1)}°C`;
    anomEl.className = `kpi-val temp-kpi-anomaly ${anomNum > 1.5 ? "temp-hot" : (anomNum < -1.5 ? "temp-cool" : "temp-mild")}`;
  }

  // 2. Safe vs Risk State Handling
  const safeCard = document.getElementById("safe-state-card");
  const riskContent = document.getElementById("risk-state-content");

  if (data.is_safe) {
    // Show calm safe card
    if (safeCard) safeCard.style.display = "flex";
    if (riskContent) riskContent.style.display = "none";

    setText("safe-headline", data.headline || `Naturally Temperate (${tempNum.toFixed(1)}°C)`);
    setText("safe-desc", data.summary || `This sector maintains an observed surface temperature of ${tempNum.toFixed(1)}°C, providing natural microclimate cooling.`);
  } else {
    // Show actionable risk card
    if (safeCard) safeCard.style.display = "none";
    if (riskContent) riskContent.style.display = "flex";

    // Typology Title & Narrative Summary
    setText("detail-archetype-title", data.archetype_title || `${data.risk_class} Risk Thermal Sector`);
    setText("detail-summary", data.summary || "No summary available.");

    // Causes List
    const causesList = document.getElementById("detail-causes-list");
    if (causesList) {
      causesList.innerHTML = "";
      const causes = data.key_causes || [];
      if (causes.length > 0) {
        causes.forEach((cause) => {
          const li = document.createElement("li");
          li.textContent = cause;
          causesList.appendChild(li);
        });
      } else {
        const li = document.createElement("li");
        li.textContent = "General urban built environment with elevated radiant heat.";
        causesList.appendChild(li);
      }
    }

    // Actions List
    const actionsList = document.getElementById("detail-actions-list");
    if (actionsList) {
      actionsList.innerHTML = "";
      const actions = data.key_actions || [];
      if (actions.length > 0) {
        actions.forEach((act) => {
          const li = document.createElement("li");
          li.textContent = act;
          actionsList.appendChild(li);
        });
      } else {
        const li = document.createElement("li");
        li.textContent = "Maintain permeable ground and encourage local greening.";
        actionsList.appendChild(li);
      }
    }
  }

  // 3. Technical Factors List (Accordion)
  const factorsContainer = document.getElementById("detail-factors-list");
  if (factorsContainer && data.factors) {
    factorsContainer.innerHTML = "";
    data.factors.forEach((factor) => {
      const card = document.createElement("div");
      card.className = "factor-card-item";
      const score = Math.min(100, Math.max(0, factor.score || 0));
      const statusClass = factor.color || "moderate";
      card.innerHTML = `
        <div class="factor-top-row">
          <div class="factor-title-group">
            <span>${factor.name}</span>
          </div>
          <span class="factor-status-pill ${statusClass}">${factor.status}</span>
        </div>
        <div class="factor-meter-row">
          <div class="factor-track">
            <div class="factor-fill ${statusClass}" style="transform: scaleX(${score / 100});"></div>
          </div>
          <span class="factor-score-num">${score}</span>
        </div>
      `;
      factorsContainer.appendChild(card);
    });
  }
}

function generateFallbackIntelligence(props) {
  const hvi = props.hvi_score || 0;
  const pop = props.estimated_population || 0;
  const risk = props.risk_class || "Medium";
  const is_safe = risk.toLowerCase() === "low" || hvi < 30;
  const heat = props.ai_heat_exposure || 50;

  const st_val = props.surface_temp_celsius !== undefined
    ? Number(props.surface_temp_celsius)
    : (props.mean_landsat_st_celsius !== undefined
      ? Number(props.mean_landsat_st_celsius)
      : (20.24 + (heat / 100.0) * 18.37));
  const surface_temp_c = Math.round(st_val * 10) / 10;
  const temp_anomaly = props.temp_anomaly_celsius !== undefined
    ? Number(props.temp_anomaly_celsius)
    : (Math.round((surface_temp_c - 28.7) * 10) / 10);
  const peak_roof = Math.round(Math.min(55.0, Math.max(surface_temp_c, surface_temp_c + ((props.ndbi || 50) / 100.0) * 16.0)) * 10) / 10;

  return {
    block_id: props.block_id || "KIB-0000",
    risk_class: risk,
    is_safe: is_safe,
    hvi_score: hvi,
    percentile: Math.round(hvi * 0.95),
    population: pop,
    surface_temp_celsius: surface_temp_c,
    surface_temp_display: `${surface_temp_c.toFixed(1)}°C`,
    temp_anomaly_celsius: temp_anomaly,
    temp_anomaly_display: `${temp_anomaly > 0 ? "+" : ""}${temp_anomaly.toFixed(1)}°C`,
    peak_roof_temp_celsius: peak_roof,
    peak_roof_temp_display: `~${peak_roof.toFixed(1)}°C`,
    archetype_title: is_safe ? "Vegetated Microclimate Buffer" : `${risk} Heat Vulnerability Sector`,
    headline: is_safe ? `Naturally Temperate (${surface_temp_c.toFixed(1)}°C)` : `Elevated Thermal Load (${surface_temp_c.toFixed(1)}°C)`,
    summary: is_safe
      ? `This sector maintains healthy tree canopy and an observed surface temperature of ${surface_temp_c.toFixed(1)}°C (${temp_anomaly > 0 ? "+" : ""}${temp_anomaly.toFixed(1)}°C relative to settlement baseline) for its ~${pop} residents.`
      : `This sector experiences elevated surface skin temperature of ${surface_temp_c.toFixed(1)}°C (${temp_anomaly > 0 ? "+" : ""}${temp_anomaly.toFixed(1)}°C above settlement baseline) with peak metal roof temperatures reaching ~${peak_roof.toFixed(1)}°C.`,
    key_causes: [
      `Galvanized metal roof solar absorption reaching up to ~${peak_roof.toFixed(1)}°C`,
      `Pedestrian walkway insolation with surface temperature of ${surface_temp_c.toFixed(1)}°C`,
    ],
    key_actions: [
      "Apply reflective white cool-roof paint to corrugated roofs",
      "Deploy shaded community rest and water kiosks",
    ],
    factors: [
      { name: "Land Surface Temperature", score: heat, status: `${surface_temp_c.toFixed(1)}°C (${temp_anomaly > 0 ? "+" : ""}${temp_anomaly.toFixed(1)}°C)`, color: surface_temp_c >= 31 ? "critical" : (surface_temp_c <= 26 ? "optimal" : "moderate") },
      { name: "Tree Canopy & Greenery", score: props.ndvi || 40, status: "Moderate", color: "moderate" },
      { name: "Tin Roofs & Impervious Mass", score: props.ndbi || 60, status: "Elevated", color: "elevated" },
    ],
  };
}

function closeSidebar() {
  const drawer = document.getElementById("sidebar");
  if (drawer) {
    drawer.classList.remove("open");
  }

  if (selectedFeatureLayer) {
    resetHighlight(selectedFeatureLayer, true);
    selectedFeatureLayer = null;
  }
}

function closeLayerDropdown() {
  const menu = document.getElementById("layer-dropdown-menu");
  if (menu) menu.style.display = "none";
}

// 6. Event Listeners
function setupEventListeners() {
  // Segmented Risk Filter Buttons
  const segmentBtns = document.querySelectorAll(".segment-btn");
  segmentBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      segmentBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const risk = btn.getAttribute("data-risk");
      handleRiskFilter(risk);
    });
  });

  // Vertical Threshold Slider (0–100)
  const thresholdSlider = document.getElementById("threshold-slider");
  const sliderValDisplay = document.getElementById("slider-val-display");
  const sliderResetBtn = document.getElementById("slider-reset-btn");

  if (thresholdSlider) {
    thresholdSlider.addEventListener("input", (e) => {
      currentThreshold = Number(e.target.value);
      if (sliderValDisplay) {
        sliderValDisplay.textContent = `\u2265 ${currentThreshold}`;
      }
      applyFilters();
    });
  }

  if (sliderResetBtn) {
    sliderResetBtn.addEventListener("click", () => {
      currentThreshold = 0;
      if (thresholdSlider) thresholdSlider.value = "0";
      if (sliderValDisplay) sliderValDisplay.textContent = "\u2265 0";
      applyFilters();
    });
  }

  // Layer Dropdown Menu Trigger
  const layerMenuBtn = document.getElementById("layer-menu-btn");
  const layerDropdownMenu = document.getElementById("layer-dropdown-menu");
  if (layerMenuBtn && layerDropdownMenu) {
    layerMenuBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const isVisible = layerDropdownMenu.style.display === "flex";
      layerDropdownMenu.style.display = isVisible ? "none" : "flex";
    });
  }

  // Layer Selection Radio in Dropdown
  const layerRadios = document.querySelectorAll('input[name="layer"]');
  layerRadios.forEach((radio) => {
    radio.addEventListener("change", (e) => switchLayer(e.target.value));
  });

  // Technical Accordion Toggle
  const toggleFactorsBtn = document.getElementById("btn-toggle-factors");
  const factorsList = document.getElementById("detail-factors-list");
  const chevron = document.getElementById("factors-toggle-chevron");
  if (toggleFactorsBtn && factorsList) {
    toggleFactorsBtn.addEventListener("click", () => {
      const isHidden = factorsList.style.display === "none";
      factorsList.style.display = isHidden ? "flex" : "none";
      if (chevron) chevron.textContent = isHidden ? "▴" : "▾";
    });
  }

  // Close Drawer Button
  const closeBtn = document.getElementById("sidebar-close");
  if (closeBtn) closeBtn.addEventListener("click", closeSidebar);

  // Keyboard Escape Key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeSidebar();
      closeLayerDropdown();
    }
  });

  // Search Input
  const searchInput = document.getElementById("search-input");
  const searchClear = document.getElementById("search-clear");
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener("input", (e) => {
      const val = e.target.value;
      if (searchClear) searchClear.style.display = val ? "block" : "none";
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => handleSearch(val), 250);
    });

    if (searchClear) {
      searchClear.addEventListener("click", () => {
        searchInput.value = "";
        searchClear.style.display = "none";
        closeSidebar();
        map.flyTo(CENTER, DEFAULT_ZOOM);
      });
    }
  }

  // Reset Map View Button
  const resetBtn = document.getElementById("btn-reset-view");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      map.flyTo(CENTER, DEFAULT_ZOOM, { duration: 1.0 });
    });
  }

  // Export GeoJSON
  const exportBtn = document.getElementById("export-btn");
  if (exportBtn) {
    exportBtn.addEventListener("click", () => {
      const a = document.createElement("a");
      a.href = "/data/vulnerability_blocks.geojson";
      a.download = "kibera_vulnerability_blocks.geojson";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    });
  }
}

function handleSearch(query) {
  if (!currentLayer) return;

  const q = query.toLowerCase().trim();
  if (!q) return;

  const matches = [];
  currentLayer.eachLayer((layer) => {
    const props = layer.feature.properties;
    if (props.block_id && props.block_id.toLowerCase().includes(q)) {
      matches.push(layer);
    }
  });

  if (matches.length === 1) {
    const layer = matches[0];
    map.flyToBounds(layer.getBounds(), { padding: [100, 100], maxZoom: 17, duration: 1.0 });

    let props = layer.feature.properties;
    if (primaryData && !props.hvi_score) {
      const pf = primaryData.features.find((f) => f.properties.block_id === props.block_id);
      if (pf) props = pf.properties;
    }
    selectFeature(layer, props);
  } else if (matches.length > 1 && matches.length < 20) {
    const group = new L.featureGroup(matches);
    map.flyToBounds(group.getBounds(), { padding: [60, 60], duration: 1.0 });
  }
}

function handleRiskFilter(riskClass) {
  currentRiskFilter = riskClass;
  applyFilters();
}

function applyFilters() {
  if (!currentLayer) return;

  const propName = currentActiveLayerName === "hvi" ? "hvi_score" : currentActiveLayerName.replace("_blocks", "");

  currentLayer.eachLayer((layer) => {
    const props = layer.feature.properties;

    let score = props[propName];
    if (score === undefined && primaryData) {
      const pf = primaryData.features.find((f) => f.properties.block_id === props.block_id);
      if (pf) score = pf.properties[propName];
    }
    const numScore = score !== undefined && score !== null ? Number(score) : 0;

    let layerRisk = props.risk_class;
    if (!layerRisk && primaryData) {
      const pf = primaryData.features.find((f) => f.properties.block_id === props.block_id);
      if (pf) layerRisk = pf.properties.risk_class;
    }

    const matchesRisk = currentRiskFilter === "All" || layerRisk === currentRiskFilter;
    const matchesThreshold = numScore >= currentThreshold;

    if (matchesRisk && matchesThreshold) {
      let fillColor;
      if (currentActiveLayerName === "hvi") {
        fillColor = RISK_COLORS[layerRisk] || "#94a3b8";
      } else {
        fillColor = getBlueColor(numScore);
      }
      layer.setStyle({
        stroke: false,
        opacity: 1,
        fillOpacity: 0.65,
        fillColor: fillColor,
      });
    } else {
      layer.setStyle({
        stroke: false,
        opacity: 0,
        fillOpacity: 0,
      });
    }
  });
}

// 7. Dynamic Map Legend Controller
function updateLegend(type, layerTitle) {
  const legendContent = document.getElementById("legend-content");
  const legendTitle = document.getElementById("legend-title");
  const legendUnit = document.getElementById("legend-unit");
  if (!legendContent) return;

  legendContent.innerHTML = "";

  if (type === "hvi") {
    if (legendTitle) legendTitle.textContent = "Risk Scale";
    if (legendUnit) legendUnit.textContent = "HVI Score (0–100)";

    const items = [
      { label: "Critical (76–100)", color: RISK_COLORS.Critical },
      { label: "High (56–75)", color: RISK_COLORS.High },
      { label: "Medium (31–55)", color: RISK_COLORS.Medium },
      { label: "Low / Safe (0–30)", color: RISK_COLORS.Low },
    ];

    items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "legend-row";
      row.innerHTML = `
        <span class="legend-swatch" style="background-color: ${item.color};"></span>
        <span>${item.label}</span>
      `;
      legendContent.appendChild(row);
    });
  } else if (type === "blue") {
    if (legendTitle) legendTitle.textContent = layerTitle || "Intensity";
    if (legendUnit) legendUnit.textContent = "Normalized (0–100)";

    const items = [
      { label: "80 – 100 (Very High)", color: BLUE_SCALE[4] },
      { label: "60 – 80 (High)", color: BLUE_SCALE[3] },
      { label: "40 – 60 (Moderate)", color: BLUE_SCALE[2] },
      { label: "20 – 40 (Low)", color: BLUE_SCALE[1] },
      { label: "0 – 20 (Minimal)", color: BLUE_SCALE[0] },
    ];

    items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "legend-row";
      row.innerHTML = `
        <span class="legend-swatch" style="background-color: ${item.color};"></span>
        <span>${item.label}</span>
      `;
      legendContent.appendChild(row);
    });
  }
}



