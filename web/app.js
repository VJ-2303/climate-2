/**
 * HeatViz Climate Intelligence Platform — Interactive Application Core
 */

const RISK_COLORS = {
  Critical: "#d73027",
  High: "#f46d43",
  Medium: "#eab308", // Visible golden amber for light basemap
  Low: "#16a34a",
};

const BLUE_SCALE = ["#eff3ff", "#bdd7e7", "#6baed6", "#3182bd", "#08519c"];

const DRIVER_LABELS = {
  poor_water_access: "Poor water access",
  poor_green_access: "Poor green space access",
  high_population_exposure: "High population exposure",
  high_building_density: "High building density",
  high_built_surface: "High built-up surface",
  low_vegetation: "Low vegetation",
};

const LAYER_TITLES = {
  hvi: "Heat Vulnerability Index",
  ai_heat_exposure_blocks: "AI Heat Exposure",
  social_sensitivity_blocks: "Social Sensitivity",
  cooling_deficit_blocks: "Cooling Access Deficit",
  ndvi_blocks: "Vegetation (NDVI)",
  ndbi_blocks: "Built-up (NDBI)",
  building_density_blocks: "Building Density",
  population_density_blocks: "Population Density",
};

const CENTER = [-1.317, 36.789];
const DEFAULT_ZOOM = 15;

// Global Application State
let map;
let primaryData = null;
let currentLayer = null;
let selectedFeatureLayer = null;
let currentActiveLayerName = "hvi";
let currentThreshold = 0;
let currentRiskFilter = "All";
const layerCache = {};

document.addEventListener("DOMContentLoaded", initApp);

function initApp() {
  // 1. Initialize Leaflet Map with Canvas Renderer
  map = L.map("map", {
    renderer: L.canvas({ padding: 0.5 }),
    zoomControl: false,
  }).setView(CENTER, DEFAULT_ZOOM);

  // Position zoom controls in bottom-right alongside quick controls
  L.control.zoom({ position: "bottomright" }).addTo(map);

  // High-contrast clean CartoDB Positron Basemap with OSM fallback
  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: "abcd",
    maxZoom: 19,
  }).addTo(map);

  setupEventListeners();
  loadPrimaryData();
  updateLegend("hvi");
}

// 2. Data Loading Engine
async function loadPrimaryData() {
  showLoading(true);
  try {
    const response = await fetch("/data/vulnerability_blocks.geojson");
    if (!response.ok) throw new Error("Failed to fetch primary vulnerability dataset");
    primaryData = await response.json();

    updateKPIs(primaryData);
    renderPrimaryLayer();
  } catch (error) {
    console.error("Failed to load primary data:", error);
    alert("Could not load vulnerability data. Please verify server status.");
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

function updateKPIs(data) {
  let total = 0,
    critical = 0,
    high = 0;
  data.features.forEach((f) => {
    total++;
    if (f.properties.risk_class === "Critical") critical++;
    if (f.properties.risk_class === "High") high++;
  });

  const setText = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };

  setText("kpi-total", total.toLocaleString());
  setText("kpi-critical", critical.toLocaleString());
  setText("kpi-high", high.toLocaleString());
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
  layer.bindTooltip(
    `<strong>${feature.properties.block_id}</strong> &bull; HVI: ${feature.properties.hvi_score} (${feature.properties.risk_class})`,
    { sticky: true, className: "custom-map-tooltip" }
  );

  layer.on({
    mouseover: (e) => highlightFeature(e.target),
    mouseout: (e) => resetHighlight(e.target),
    click: (e) => selectFeature(e.target, feature.properties),
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

  // Update active pill indicator in layer panel
  const indicator = document.getElementById("active-layer-name");
  if (indicator) {
    indicator.textContent = LAYER_TITLES[layerName] || layerName;
  }

  // Update radio items active class
  document.querySelectorAll(".layer-radio-item").forEach((item) => {
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
        `<strong>${feature.properties.block_id}</strong> &bull; ${propName}: ${feature.properties[propName]}`,
        { sticky: true, className: "custom-map-tooltip" }
      );

      layer.on({
        mouseover: (e) => highlightFeature(e.target),
        mouseout: (e) => resetHighlight(e.target),
        click: (e) => {
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

// 5. Sidebar Inspector Controller
function openSidebar(props) {
  const defaultView = document.getElementById("sidebar-default");
  const detailView = document.getElementById("sidebar-detail");
  if (defaultView) defaultView.style.display = "none";
  if (detailView) detailView.style.display = "flex";

  const setText = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text !== undefined && text !== null ? text : "—";
  };

  setText("detail-block-id", props.block_id);

  // Risk Badge
  const badge = document.getElementById("detail-risk-badge");
  if (badge) {
    badge.textContent = props.risk_class || "—";
    badge.className = "risk-badge " + (props.risk_class ? `risk-${props.risk_class.toLowerCase()}` : "");
  }

  setText("detail-hvi-score", props.hvi_score);
  setText("detail-hvi-raw", props.hvi_raw !== undefined ? props.hvi_raw.toFixed(1) : "—");

  // Metric Pillar Progress Bars
  const setBar = (idBar, idVal, val) => {
    const bar = document.getElementById(idBar);
    const fraction = Math.min(1, Math.max(0, (val || 0) / 100));
    if (bar) bar.style.transform = `scaleX(${fraction})`;
    setText(idVal, val !== undefined && val !== null ? val : 0);
  };

  setBar("bar-heat", "val-heat", props.ai_heat_exposure);
  setBar("bar-social", "val-social", props.social_sensitivity);
  setBar("bar-cooling", "val-cooling", props.cooling_deficit);

  // Population & Intervention
  setText("detail-population", props.estimated_population !== undefined ? props.estimated_population.toLocaleString() : "—");
  setText("detail-intervention", props.intervention || "General monitoring & green space preservation");

  // Top Risk Drivers (Numbered and Styled)
  const driversContainer = document.getElementById("detail-drivers");
  if (driversContainer) {
    driversContainer.innerHTML = "";
    if (props.top_drivers && Array.isArray(props.top_drivers)) {
      props.top_drivers.forEach((driver, idx) => {
        const item = document.createElement("div");
        item.className = "driver-tag-item";
        item.innerHTML = `
          <span class="driver-rank">${idx + 1}</span>
          <span>${DRIVER_LABELS[driver] || driver}</span>
        `;
        driversContainer.appendChild(item);
      });
    }
  }

  // Environmental Telemetry Grid
  setText("detail-popdensity", props.population_density);
  setText("detail-building", props.building_density);
  setText("detail-ndvi", props.ndvi);
  setText("detail-ndwi", props.ndwi);
  setText("detail-ndbi", props.ndbi);
  setText("detail-green", props.distance_to_green);
  setText("detail-water", props.distance_to_water);
}

function closeSidebar() {
  const defaultView = document.getElementById("sidebar-default");
  const detailView = document.getElementById("sidebar-detail");
  if (defaultView) defaultView.style.display = "flex";
  if (detailView) detailView.style.display = "none";

  if (selectedFeatureLayer) {
    resetHighlight(selectedFeatureLayer, true);
    selectedFeatureLayer = null;
  }
}

// 6. Search, Filter & Quick Actions
function setupEventListeners() {
  // Layer Radio Switcher
  const layerRadios = document.querySelectorAll('input[name="layer"]');
  layerRadios.forEach((radio) => {
    radio.addEventListener("change", (e) => switchLayer(e.target.value));
  });

  // Close Sidebar Button
  const closeBtn = document.getElementById("sidebar-close");
  if (closeBtn) closeBtn.addEventListener("click", closeSidebar);

  // Search Input & Clear
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

  // Risk Filter Dropdown
  const riskFilter = document.getElementById("risk-filter");
  if (riskFilter) {
    riskFilter.addEventListener("change", (e) => handleRiskFilter(e.target.value));
  }

  // Vertical Threshold Slider Filter (0–100)
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

  // Reset Map View Button
  const resetBtn = document.getElementById("btn-reset-view");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      map.flyTo(CENTER, DEFAULT_ZOOM, { duration: 1.2 });
    });
  }

  // Export GeoJSON Action
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

    // Retrieve score for threshold comparison
    let score = props[propName];
    if (score === undefined && primaryData) {
      const pf = primaryData.features.find((f) => f.properties.block_id === props.block_id);
      if (pf) score = pf.properties[propName];
    }
    const numScore = score !== undefined && score !== null ? Number(score) : 0;

    // Retrieve risk classification
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
    if (legendTitle) legendTitle.textContent = "Heat Risk Tier";
    if (legendUnit) legendUnit.textContent = "HVI Score (0–100)";

    const items = [
      { label: "Critical Risk (76–100)", color: RISK_COLORS.Critical },
      { label: "High Risk (56–75)", color: RISK_COLORS.High },
      { label: "Medium Risk (31–55)", color: RISK_COLORS.Medium },
      { label: "Low Risk (0–30)", color: RISK_COLORS.Low },
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
    if (legendTitle) legendTitle.textContent = layerTitle || "Relative Intensity";
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
