/**
 * HeatViz Climate Intelligence Platform — Interactive Application Core
 */

const RISK_COLORS = {
  Critical: "#dc2626", // Deep High-Contrast Crimson Red
  High: "#ea580c",     // Deep High-Contrast Amber Orange
  Medium: "#d97706",   // Deep High-Contrast Warm Gold
  Low: "#059669",      // Deep High-Contrast Emerald Green
};

// High-contrast, domain-specific 5-step color ramps (every baseline has a visible tint)
const THEMATIC_PALETTES = {
  ndvi_blocks: ["#cbd5e1", "#86efac", "#22c55e", "#15803d", "#14532d"],
  ai_heat_exposure_blocks: ["#fef08a", "#facc15", "#f97316", "#dc2626", "#7f1d1d"],
  ndbi_blocks: ["#cbd5e1", "#94a3b8", "#64748b", "#334155", "#0f172a"],
  building_density_blocks: ["#fed7aa", "#fb923c", "#ea580c", "#c2410c", "#7c2d12"],
  population_density_blocks: ["#c7d2fe", "#818cf8", "#4f46e5", "#3730a3", "#1e1b4b"],
  cooling_deficit_blocks: ["#bae6fd", "#38bdf8", "#0284c7", "#0369a1", "#0c4a6e"],
  social_sensitivity_blocks: ["#f5d0fe", "#e879f9", "#c026d3", "#86198f", "#4a044e"],
};

const DEFAULT_THEMATIC_PALETTE = ["#cbd5e1", "#93c5fd", "#3b82f6", "#1d4ed8", "#1e3a8a"];

const LAYER_TITLES = {
  hvi: "Heat Vulnerability Index (HVI)",
  ai_heat_exposure_blocks: "Surface Heat Exposure",
  ndvi_blocks: "Tree Canopy & Greenery (NDVI)",
  ndbi_blocks: "Tin Roofs & Impervious (NDBI)",
  building_density_blocks: "Building Footprint Density",
  population_density_blocks: "Population Density",
  cooling_deficit_blocks: "Cooling Access Deficit",
  social_sensitivity_blocks: "Social Vulnerability & Sensitivity",
};

const CENTER = [-1.317, 36.789];
const DEFAULT_ZOOM = 15;

// Global Application State
let map;
let defaultBasemapLayer = null;
let satelliteBasemapLayer = null;
let satelliteLabelsLayer = null;
let currentBasemap = "default";

let primaryData = null;
let primaryFeatureMap = new Map();
let currentLayer = null;
let selectedFeatureLayer = null;
let currentActiveLayerName = "hvi";
let currentRiskFilter = "All";
let currentThreshold = 0;
const layerCache = {};
const blockIntelligenceCache = {};

// Feature 1 — Overview Dashboard state
let overviewOpen = false;

// Feature 2 — Draw Zone Intervention Planner state
let drawControl = null;
let drawnZoneLayer = null;
let zoneHighlightLayer = null;
let isDrawingZone = false;
let kiberaMeanSurfaceTemp = 28.7;

document.addEventListener("DOMContentLoaded", initApp);

function initApp() {
  // 1. Initialize Leaflet Map
  map = L.map("map", {
    renderer: L.canvas({ padding: 0.5 }),
    zoomControl: false,
  }).setView(CENTER, DEFAULT_ZOOM);

  // Position zoom controls in bottom-right
  L.control.zoom({ position: "bottomright" }).addTo(map);

  // Initialize Basemap Surface Layers (Default Carto Light & ESRI High-Res Satellite)
  initBasemaps();

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

function initBasemaps() {
  // Clean CartoDB Positron Basemap (Default Street / Light)
  defaultBasemapLayer = L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; CARTO',
      subdomains: "abcd",
      maxZoom: 19,
    }
  );

  // ESRI World Imagery (High-Resolution Satellite)
  satelliteBasemapLayer = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
      attribution:
        "Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, GIS User Community",
      maxZoom: 19,
    }
  );

  // Optional Satellite Reference & Place Labels Overlay
  satelliteLabelsLayer = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
    {
      attribution: "&copy; Esri",
      maxZoom: 19,
      opacity: 0.85,
    }
  );

  defaultBasemapLayer.addTo(map);
}

function setBasemap(type) {
  if (type === currentBasemap) return;
  currentBasemap = type;

  if (type === "satellite") {
    if (map.hasLayer(defaultBasemapLayer)) {
      map.removeLayer(defaultBasemapLayer);
    }
    satelliteBasemapLayer.addTo(map);
    satelliteLabelsLayer.addTo(map);
  } else {
    if (map.hasLayer(satelliteBasemapLayer)) {
      map.removeLayer(satelliteBasemapLayer);
    }
    if (map.hasLayer(satelliteLabelsLayer)) {
      map.removeLayer(satelliteLabelsLayer);
    }
    defaultBasemapLayer.addTo(map);
  }

  // Ensure the vector polygon layer stays on top of the basemap
  if (currentLayer) {
    currentLayer.bringToFront();
  }

  // Update button active states in UI toggle bar
  document.querySelectorAll(".basemap-btn").forEach((btn) => {
    if (btn.getAttribute("data-basemap") === type) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });
}

// 2. Data Loading Engine
async function loadPrimaryData() {
  showLoading(true);
  try {
    const response = await fetch("/data/vulnerability_blocks.geojson");
    if (!response.ok) throw new Error("Failed to fetch primary dataset");
    primaryData = await response.json();
    primaryFeatureMap = new Map();
    if (primaryData && primaryData.features) {
      for (let i = 0; i < primaryData.features.length; i++) {
        const feat = primaryData.features[i];
        if (feat.properties && feat.properties.block_id) {
          primaryFeatureMap.set(feat.properties.block_id, feat.properties);
        }
      }
    }
    renderPrimaryLayer();
    initOverviewDashboard();
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

function getThematicColor(layerName, val) {
  if (val === undefined || val === null || isNaN(val)) return "#cbd5e1";
  const palette = THEMATIC_PALETTES[layerName] || DEFAULT_THEMATIC_PALETTE;
  if (val <= 20) return palette[0];
  if (val <= 40) return palette[1];
  if (val <= 60) return palette[2];
  if (val <= 80) return palette[3];
  return palette[4];
}

function getLayerFillColor(layer) {
  if (!layer || !layer.feature) return "#94a3b8";
  const props = layer.feature.properties;
  if (currentActiveLayerName === "hvi") {
    let layerRisk = props.risk_class;
    if (!layerRisk && primaryFeatureMap) {
      const pf = primaryFeatureMap.get(props.block_id);
      if (pf) layerRisk = pf.risk_class;
    }
    return RISK_COLORS[layerRisk] || "#94a3b8";
  } else {
    const propName = currentActiveLayerName.replace("_blocks", "");
    let score = props[propName];
    if (score === undefined && primaryFeatureMap) {
      const pf = primaryFeatureMap.get(props.block_id);
      if (pf) score = pf[propName];
    }
    return getThematicColor(currentActiveLayerName, Number(score));
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
    fillOpacity: 0.60,
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

  const color = getLayerFillColor(layer);
  layer.setStyle({
    stroke: true,
    weight: 2,
    color: "#0f172a",
    opacity: 1,
    fillColor: color,
    fillOpacity: 0.85,
  });

  if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
    layer.bringToFront();
  }
}

function resetHighlight(layer, force = false) {
  if (layer === selectedFeatureLayer && !force) return;
  if (layer.options.fillOpacity === 0) return;

  const color = getLayerFillColor(layer);
  layer.setStyle({
    stroke: false,
    fillColor: color,
    fillOpacity: 0.60,
  });
}

function selectFeature(layer, properties) {
  if (layer.options.fillOpacity === 0) return;

  if (selectedFeatureLayer) {
    resetHighlight(selectedFeatureLayer, true);
  }

  selectedFeatureLayer = layer;

  const color = getLayerFillColor(layer);
  layer.setStyle({
    stroke: true,
    weight: 2.5,
    color: "#0f172a",
    opacity: 1,
    fillColor: color,
    fillOpacity: 0.90,
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
      updateLegend(layerName);
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
        fillOpacity: 0.60,
        fillColor: getThematicColor(layerName, Number(val)),
      };
    },
    onEachFeature: (feature, layer) => {
      const val = feature.properties[propName];
      layer.bindTooltip(
        `<strong>${feature.properties.block_id}</strong> &bull; ${LAYER_TITLES[layerName] || propName}: ${val !== undefined && val !== null ? Number(val).toFixed(1) : "N/A"}`,
        { sticky: true, className: "custom-map-tooltip" }
      );

      layer.on({
        mouseover: (e) => highlightFeature(e.target),
        mouseout: (e) => resetHighlight(e.target),
        click: (e) => {
          e.originalEvent._stoppedByFeature = true;
          let props = feature.properties;
          if (primaryFeatureMap && primaryFeatureMap.has(feature.properties.block_id)) {
            props = primaryFeatureMap.get(feature.properties.block_id);
          }
          selectFeature(layer, props);
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
  // Basemap Toggle Buttons (Default Street / Satellite)
  const basemapBtns = document.querySelectorAll(".basemap-btn");
  basemapBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const type = btn.getAttribute("data-basemap");
      setBasemap(type);
    });
  });

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

  // Feature 1 — Overview Dashboard toggle
  const overviewBtn = document.getElementById("btn-overview");
  const overviewCloseBtn = document.getElementById("btn-overview-close");
  if (overviewBtn) {
    overviewBtn.addEventListener("click", () => toggleOverviewSidebar());
  }
  if (overviewCloseBtn) {
    overviewCloseBtn.addEventListener("click", () => toggleOverviewSidebar(false));
  }

  // Feature 2 — Draw Zone Intervention Planner
  const drawZoneBtn = document.getElementById("btn-draw-zone");
  if (drawZoneBtn) {
    drawZoneBtn.addEventListener("click", () => toggleDrawZoneMode());
  }
  const zoneCloseBtn = document.getElementById("btn-zone-close");
  const zoneClearBtn = document.getElementById("btn-zone-clear");
  if (zoneCloseBtn) zoneCloseBtn.addEventListener("click", clearZone);
  if (zoneClearBtn) zoneClearBtn.addEventListener("click", clearZone);
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
    if (score === undefined && primaryFeatureMap) {
      const pf = primaryFeatureMap.get(props.block_id);
      if (pf) score = pf[propName];
    }
    const numScore = score !== undefined && score !== null ? Number(score) : 0;

    let layerRisk = props.risk_class;
    if (!layerRisk && primaryFeatureMap) {
      const pf = primaryFeatureMap.get(props.block_id);
      if (pf) layerRisk = pf.risk_class;
    }

    const matchesRisk = currentRiskFilter === "All" || layerRisk === currentRiskFilter;
    const matchesThreshold = numScore >= currentThreshold;

    if (matchesRisk && matchesThreshold) {
      let fillColor;
      if (currentActiveLayerName === "hvi") {
        fillColor = RISK_COLORS[layerRisk] || "#94a3b8";
      } else {
        fillColor = getThematicColor(currentActiveLayerName, numScore);
      }
      layer.setStyle({
        stroke: false,
        opacity: 1,
        fillOpacity: 0.60,
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
function updateLegend(layerName) {
  const legendContent = document.getElementById("legend-content");
  const legendTitle = document.getElementById("legend-title");
  const legendUnit = document.getElementById("legend-unit");
  if (!legendContent) return;

  legendContent.innerHTML = "";

  if (layerName === "hvi") {
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
  } else {
    const title = LAYER_TITLES[layerName] || "Thematic Intensity";
    if (legendTitle) legendTitle.textContent = title;
    if (legendUnit) legendUnit.textContent = "Normalized (0–100)";

    const palette = THEMATIC_PALETTES[layerName] || DEFAULT_THEMATIC_PALETTE;
    const items = [
      { label: "80 – 100 (Very High)", color: palette[4] },
      { label: "60 – 80 (High)", color: palette[3] },
      { label: "40 – 60 (Moderate)", color: palette[2] },
      { label: "20 – 40 (Low)", color: palette[1] },
      { label: "0 – 20 (Minimal)", color: palette[0] },
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




// =============================================================================
// Feature 1 — Settlement-Level Summary Dashboard
// =============================================================================

/**
 * Computes all settlement-level statistics from the loaded GeoJSON features.
 * Returns a structured report object.
 */
function computeSettlementStats(features) {
  const counts = { Critical: 0, High: 0, Medium: 0, Low: 0 };
  let totalPop = 0;
  let atRiskPop = 0;
  let hviSum = 0;
  const interventionCounts = {};
  const allBlocks = [];

  features.forEach((feat) => {
    const p = feat.properties;
    if (!p) return;

    const rc = p.risk_class || "Low";
    counts[rc] = (counts[rc] || 0) + 1;

    const pop = p.estimated_population || 0;
    totalPop += pop;
    if (rc === "Critical" || rc === "High") atRiskPop += pop;

    hviSum += (p.hvi_score || 0);

    const intv = p.intervention || "Unknown";
    interventionCounts[intv] = (interventionCounts[intv] || 0) + 1;

    // Priority score = hvi_score × estimated_population (impact × urgency)
    allBlocks.push({
      block_id: p.block_id,
      hvi_score: p.hvi_score || 0,
      risk_class: rc,
      estimated_population: pop,
      intervention: intv,
      priority: (p.hvi_score || 0) * (pop || 1),
    });
  });

  const total = features.length;
  const meanHVI = total > 0 ? Math.round(hviSum / total) : 0;

  // Compute settlement-wide average surface temperature
  const tempFeatures = features.filter((f) => f.properties && f.properties.surface_temp_celsius !== undefined);
  if (tempFeatures.length > 0) {
    const totalTemp = tempFeatures.reduce((acc, f) => acc + Number(f.properties.surface_temp_celsius), 0);
    kiberaMeanSurfaceTemp = totalTemp / tempFeatures.length;
  }

  // Top 5 priority sectors
  const top5 = allBlocks
    .filter((b) => b.risk_class === "Critical" || b.risk_class === "High")
    .sort((a, b) => b.priority - a.priority)
    .slice(0, 5);

  // Sort interventions by count descending
  const sortedInterventions = Object.entries(interventionCounts)
    .sort(([, a], [, b]) => b - a);

  const criticalIntCount = features.filter(
    (f) => f.properties && (f.properties.risk_class === "Critical" || f.properties.risk_class === "High")
  ).reduce((acc, f) => {
    const intv = f.properties.intervention || "Unknown";
    acc[intv] = (acc[intv] || 0) + 1;
    return acc;
  }, {});

  const sortedCriticalIntvs = Object.entries(criticalIntCount).sort(([, a], [, b]) => b - a);
  const dominantIntervention = sortedCriticalIntvs.length > 0 ? sortedCriticalIntvs[0][0] : "--";

  return {
    counts,
    total,
    totalPop: Math.round(totalPop),
    atRiskPop: Math.round(atRiskPop),
    meanHVI,
    kiberaMeanTemp: kiberaMeanSurfaceTemp,
    top5,
    sortedInterventions,
    sortedCriticalIntvs,
    dominantIntervention,
  };
}

/**
 * Populates the Overview sidebar DOM from computed stats.
 */
function renderOverviewDashboard(stats) {
  const {
    counts, total, atRiskPop, meanHVI, kiberaMeanTemp,
    top5, sortedCriticalIntvs, dominantIntervention,
  } = stats;

  // KPI values
  const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  setEl("ov-mean-hvi", meanHVI);
  setEl("ov-mean-temp", `${(kiberaMeanTemp || 28.7).toFixed(1)}°C`);
  setEl("topbar-avg-temp", `Avg: ${(kiberaMeanTemp || 28.7).toFixed(1)}°C`);
  setEl("ov-atrisk-pop", atRiskPop.toLocaleString());
  setEl("ov-critical-count", (counts.Critical || 0).toLocaleString());
  setEl("ov-total-blocks", total.toLocaleString());
  setEl("ov-safe-count", (counts.Low || 0).toLocaleString());

  // Risk distribution segmented bar
  const barEl = document.getElementById("ov-dist-bar");
  const legendEl = document.getElementById("ov-dist-legend");
  if (barEl && legendEl) {
    barEl.innerHTML = "";
    legendEl.innerHTML = "";
    const riskColors = { Critical: "#dc2626", High: "#ea580c", Medium: "#d97706", Low: "#059669" };
    const tiers = ["Critical", "High", "Medium", "Low"];
    tiers.forEach((tier) => {
      const cnt = counts[tier] || 0;
      const pct = total > 0 ? ((cnt / total) * 100).toFixed(1) : 0;
      if (cnt === 0) return;
      // Bar segment
      const seg = document.createElement("div");
      seg.className = "ov-dist-segment";
      seg.style.width = pct + "%";
      seg.style.background = riskColors[tier];
      seg.title = `${tier}: ${cnt} sectors (${pct}%)`;
      barEl.appendChild(seg);
      // Legend item
      const li = document.createElement("div");
      li.className = "ov-legend-item";
      li.innerHTML = `<span class="ov-legend-dot" style="background:${riskColors[tier]}"></span>${tier} ${cnt} (${pct}%)`;
      legendEl.appendChild(li);
    });
  }

  // Dominant intervention badge
  const intBadge = document.getElementById("ov-top-intervention");
  if (intBadge) intBadge.textContent = dominantIntervention;

  // Intervention breakdown mini-bars (top 5 types across Critical+High)
  const intBreakdown = document.getElementById("ov-intervention-breakdown");
  if (intBreakdown) {
    intBreakdown.innerHTML = "";
    const maxCount = sortedCriticalIntvs.length > 0 ? sortedCriticalIntvs[0][1] : 1;
    const topIntvs = sortedCriticalIntvs.slice(0, 5);
    const totalCritHigh = topIntvs.reduce((s, [, c]) => s + c, 0);
    topIntvs.forEach(([name, count]) => {
      const pct = totalCritHigh > 0 ? Math.round((count / totalCritHigh) * 100) : 0;
      const barWidth = maxCount > 0 ? Math.round((count / maxCount) * 100) : 0;
      const row = document.createElement("div");
      row.className = "ov-int-row";
      row.innerHTML = `
        <span class="ov-int-name">${name}</span>
        <span class="ov-int-pct">${pct}%</span>
        <div class="ov-int-bar-wrap"><div class="ov-int-bar-fill" style="width:${barWidth}%"></div></div>
      `;
      intBreakdown.appendChild(row);
    });
  }

  // Top-5 priority sectors list (clickable → opens block detail drawer)
  const priorityList = document.getElementById("ov-priority-list");
  if (priorityList) {
    priorityList.innerHTML = "";
    top5.forEach((block, idx) => {
      const li = document.createElement("li");
      li.className = "ov-priority-item";
      li.innerHTML = `
        <span class="ov-rank">#${idx + 1}</span>
        <div class="ov-block-info">
          <div class="ov-block-id">${block.block_id}</div>
          <div class="ov-block-int">${block.intervention}</div>
        </div>
      `;
      li.addEventListener("click", () => {
        // Navigate to this block on the map and open its Sector Intelligence drawer
        const feature = primaryData && primaryData.features
          ? primaryData.features.find((f) => f.properties && f.properties.block_id === block.block_id)
          : null;
        if (feature) {
          // Fly to block centroid
          const coords = feature.geometry.coordinates;
          let lats = [], lngs = [];
          const extractCoords = (rings) => rings.forEach((ring) => {
            if (Array.isArray(ring[0])) extractCoords(ring);
            else { lngs.push(ring[0]); lats.push(ring[1]); }
          });
          extractCoords(coords);
          const lat = (Math.min(...lats) + Math.max(...lats)) / 2;
          const lng = (Math.min(...lngs) + Math.max(...lngs)) / 2;
          map.flyTo([lat, lng], 17, { duration: 0.8 });
          // Pass the full properties object — openSidebar requires props.block_id
          openSidebar(feature.properties);
        }
      });
      priorityList.appendChild(li);
    });
  }
}

/**
 * Initialises the Overview dashboard by computing stats from loaded data.
 * Called once after primaryData is loaded.
 */
function initOverviewDashboard() {
  if (!primaryData || !primaryData.features) return;
  const stats = computeSettlementStats(primaryData.features);
  renderOverviewDashboard(stats);
}

/**
 * Toggles the Overview left sidebar open/closed.
 * @param {boolean|undefined} forceState — if provided, sets state explicitly.
 */
function toggleOverviewSidebar(forceState) {
  const sidebar = document.getElementById("overview-sidebar");
  const btn = document.getElementById("btn-overview");
  if (!sidebar) return;

  overviewOpen = forceState !== undefined ? forceState : !overviewOpen;
  sidebar.classList.toggle("open", overviewOpen);
  if (btn) btn.classList.toggle("active", overviewOpen);

  // Drive CSS shift of left-side floating panels (threshold slider, basemap toggle)
  document.body.classList.toggle("overview-open", overviewOpen);
}

// =============================================================================
// Feature 2 — Draw Zone Intervention Planner
// =============================================================================

/**
 * Initialises Leaflet.draw control and wires up the draw:created event.
 * Called lazily the first time the Draw Zone button is clicked.
 */
function initDrawZone() {
  if (drawControl) return; // already initialised

  // Create an invisible draw control (we'll trigger it programmatically)
  const drawnItems = new L.FeatureGroup();
  map.addLayer(drawnItems);

  drawControl = new L.Control.Draw({
    position: "topright",
    draw: {
      polygon: {
        allowIntersection: false,
        showArea: false,
        shapeOptions: {
          color: "#f59e0b",
          weight: 2,
          opacity: 0.9,
          fillOpacity: 0.08,
          dashArray: "6 4",
        },
      },
      polyline: false,
      rectangle: false,
      circle: false,
      circlemarker: false,
      marker: false,
    },
    edit: { featureGroup: drawnItems, edit: false, remove: false },
  });

  // Listen for completed drawing
  map.on(L.Draw.Event.CREATED, (e) => {
    // Remove any previous drawn polygon
    if (drawnZoneLayer) {
      map.removeLayer(drawnZoneLayer);
    }
    drawnZoneLayer = e.layer;
    drawnZoneLayer.addTo(map);

    // Exit drawing mode UI
    isDrawingZone = false;
    const drawZoneBtn = document.getElementById("btn-draw-zone");
    if (drawZoneBtn) drawZoneBtn.classList.remove("drawing-active");

    // Analyse and report
    handleZoneDrawn(drawnZoneLayer);
  });

  // If the user cancels drawing (Esc)
  map.on(L.Draw.Event.DRAWSTOP, () => {
    isDrawingZone = false;
    const drawZoneBtn = document.getElementById("btn-draw-zone");
    if (drawZoneBtn) drawZoneBtn.classList.remove("drawing-active");
  });
}

/**
 * Toggles draw zone mode on/off.
 */
function toggleDrawZoneMode() {
  initDrawZone();

  const drawZoneBtn = document.getElementById("btn-draw-zone");

  if (isDrawingZone) {
    // Cancel ongoing draw
    map.fire("draw:drawstop");
    isDrawingZone = false;
    if (drawZoneBtn) drawZoneBtn.classList.remove("drawing-active");
    return;
  }

  // Clear previous zone first
  clearZone(false); // clear highlights without hiding modal (it'll be replaced)

  isDrawingZone = true;
  if (drawZoneBtn) drawZoneBtn.classList.add("drawing-active");

  // Programmatically start drawing a polygon
  const polygonDraw = new L.Draw.Polygon(map, drawControl.options.draw.polygon);
  polygonDraw.enable();
}

/**
 * Called when a polygon zone is completed.
 * Finds all blocks inside, computes report, highlights on map, shows modal.
 */
function handleZoneDrawn(zoneLayer) {
  if (!primaryData || !primaryData.features) return;

  // Build a Turf polygon from the drawn Leaflet layer
  const latlngs = zoneLayer.getLatLngs()[0];
  const coords = latlngs.map((ll) => [ll.lng, ll.lat]);
  // Close the ring
  coords.push(coords[0]);
  const zonePolygon = turf.polygon([coords]);

  // Find all GeoJSON blocks whose centroid is inside the zone
  const blocksInside = [];
  primaryData.features.forEach((feat) => {
    if (!feat.geometry || !feat.properties) return;
    // Use centroid for point-in-polygon test
    const centroid = turf.centroid(feat);
    if (turf.booleanPointInPolygon(centroid, zonePolygon)) {
      blocksInside.push(feat);
    }
  });

  if (blocksInside.length === 0) {
    alert("No sectors found inside the drawn zone. Please draw a larger area.");
    clearZone();
    return;
  }

  // Highlight blocks inside zone on the map
  applyZoneHighlight(blocksInside);

  // Compute zone report
  const report = computeZoneReport(blocksInside);

  // Render modal
  renderZoneModal(report);
}

/**
 * Adds a yellow pulsing highlight Leaflet layer over all blocks in the zone.
 */
function applyZoneHighlight(features) {
  if (zoneHighlightLayer) {
    map.removeLayer(zoneHighlightLayer);
    zoneHighlightLayer = null;
  }

  zoneHighlightLayer = L.geoJSON(
    { type: "FeatureCollection", features },
    {
      style: () => ({
        color: "#f59e0b",
        weight: 2.5,
        opacity: 1,
        fillColor: "#fef3c7",
        fillOpacity: 0.45,
      }),
      onEachFeature: (feat, layer) => {
        // Attach the pulse animation class to each path element
        layer.on("add", () => {
          const el = layer.getElement ? layer.getElement() : null;
          if (el) el.classList.add("zone-highlight-path");
        });
      },
    }
  );

  zoneHighlightLayer.addTo(map);
  zoneHighlightLayer.bringToFront();
  // Ensure main GeoJSON stays below but visible
  if (currentLayer) currentLayer.bringToBack();
}

/**
 * Computes intervention statistics for a set of GeoJSON features (the zone).
 */
function computeZoneReport(features) {
  const counts = { Critical: 0, High: 0, Medium: 0, Low: 0 };
  let atRiskPop = 0;
  let hviSum = 0;
  let zoneTempSum = 0;
  let validTempCount = 0;
  const interventionCounts = {};

  features.forEach((feat) => {
    const p = feat.properties;
    if (!p) return;
    const rc = p.risk_class || "Low";
    counts[rc] = (counts[rc] || 0) + 1;
    const pop = p.estimated_population || 0;
    if (rc === "Critical" || rc === "High") atRiskPop += pop;
    hviSum += p.hvi_score || 0;

    if (p.surface_temp_celsius !== undefined && p.surface_temp_celsius !== null) {
      zoneTempSum += Number(p.surface_temp_celsius);
      validTempCount++;
    }

    const intv = p.intervention || "Unknown";
    interventionCounts[intv] = (interventionCounts[intv] || 0) + 1;
  });

  const total = features.length;
  const meanHVI = total > 0 ? Math.round(hviSum / total) : 0;
  const zoneMeanTemp = validTempCount > 0 ? (zoneTempSum / validTempCount) : kiberaMeanSurfaceTemp;
  const tempDelta = zoneMeanTemp - kiberaMeanSurfaceTemp;

  const sortedIntvs = Object.entries(interventionCounts).sort(([, a], [, b]) => b - a);
  const dominantIntervention = sortedIntvs.length > 0 ? sortedIntvs[0][0] : "--";

  return {
    total,
    counts,
    atRiskPop: Math.round(atRiskPop),
    meanHVI,
    zoneMeanTemp,
    kiberaMeanTemp: kiberaMeanSurfaceTemp,
    tempDelta,
    dominantIntervention,
  };
}

/**
 * Populates and shows the Zone Intervention Report modal.
 */
function renderZoneModal(report) {
  const { total, counts, atRiskPop, meanHVI, zoneMeanTemp, kiberaMeanTemp, tempDelta, dominantIntervention } = report;

  // KPI values
  const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  setEl("zm-block-count", total.toLocaleString());
  setEl("zm-atrisk-pop", atRiskPop.toLocaleString());
  setEl("zm-mean-hvi", meanHVI);

  // Risk tier bars
  const tierBarsEl = document.getElementById("zm-tier-bars");
  if (tierBarsEl) {
    tierBarsEl.innerHTML = "";
    const riskColors = { Critical: "#dc2626", High: "#ea580c", Medium: "#d97706", Low: "#059669" };
    const maxCount = Math.max(...Object.values(counts), 1);
    ["Critical", "High", "Medium", "Low"].forEach((tier) => {
      const cnt = counts[tier] || 0;
      const barW = Math.round((cnt / maxCount) * 100);
      const row = document.createElement("div");
      row.className = "zone-tier-row";
      row.innerHTML = `
        <span class="zone-tier-name">${tier}</span>
        <div class="zone-tier-bar-wrap">
          <div class="zone-tier-bar-fill" style="width:${barW}%;background:${riskColors[tier]}"></div>
        </div>
        <span class="zone-tier-count">${cnt}</span>
      `;
      tierBarsEl.appendChild(row);
    });
  }

  // Dominant intervention
  setEl("zm-dominant-intv", dominantIntervention);

  // Settlement Baseline Temperature Comparison
  setEl("zm-kibera-avg-temp", `${kiberaMeanTemp.toFixed(1)}°C`);
  setEl("zm-zone-avg-temp", `${zoneMeanTemp.toFixed(1)}°C`);
  
  const deltaEl = document.getElementById("zm-temp-delta");
  if (deltaEl) {
    deltaEl.textContent = `${tempDelta > 0 ? "+" : ""}${tempDelta.toFixed(1)}°C`;
    if (tempDelta <= 0) {
      deltaEl.classList.add("temp-cool");
    } else {
      deltaEl.classList.remove("temp-cool");
    }
  }

  // Show modal
  const modal = document.getElementById("zone-modal");
  if (modal) modal.style.display = "flex";
}

/**
 * Clears the drawn zone polygon, highlight layer, and hides the modal.
 * @param {boolean} hideModal - whether to also hide the modal (default: true)
 */
function clearZone(hideModal = true) {
  if (drawnZoneLayer) {
    map.removeLayer(drawnZoneLayer);
    drawnZoneLayer = null;
  }
  if (zoneHighlightLayer) {
    map.removeLayer(zoneHighlightLayer);
    zoneHighlightLayer = null;
  }
  if (hideModal) {
    const modal = document.getElementById("zone-modal");
    if (modal) modal.style.display = "none";
  }
  isDrawingZone = false;
  const drawZoneBtn = document.getElementById("btn-draw-zone");
  if (drawZoneBtn) drawZoneBtn.classList.remove("drawing-active");
  // Restore main layer z-order
  if (currentLayer) currentLayer.bringToFront();
}
