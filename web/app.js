const RISK_COLORS = {
  Critical: "#d73027",
  High: "#f46d43",
  Medium: "#ffffbf",
  Low: "#1a9850",
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
const CENTER = [-1.317, 36.789];

// Application State
let map;
let primaryData = null;
let currentLayer = null;
let selectedFeatureLayer = null;
const layerCache = {};

// Initialize application on DOM load
document.addEventListener("DOMContentLoaded", initApp);

function initApp() {
  // 2. Map Initialization
  map = L.map("map", {
    renderer: L.canvas({ padding: 0.5 }),
  }).setView(CENTER, 15);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19,
  }).addTo(map);

  setupEventListeners();
  loadPrimaryData();
  updateLegend("hvi");
}

// 3. Data Loading
async function loadPrimaryData() {
  showLoading(true);
  try {
    const response = await fetch("/data/vulnerability_blocks.geojson");
    if (!response.ok) throw new Error("Network response was not ok");
    primaryData = await response.json();

    updateKPIs(primaryData);
    renderPrimaryLayer();
  } catch (error) {
    console.error("Failed to load primary data:", error);
    alert("Could not load vulnerability data. Please check your connection.");
  } finally {
    showLoading(false);
  }
}

function showLoading(show) {
  const overlay = document.getElementById("loading-overlay");
  if (overlay) {
    overlay.style.display = show ? "flex" : "none";
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

  const updateText = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };

  updateText("kpi-total", total.toLocaleString());
  updateText("kpi-critical", critical.toLocaleString());
  updateText("kpi-high", high.toLocaleString());
}

// 4. HVI Choropleth Styling
function renderPrimaryLayer() {
  if (currentLayer) {
    map.removeLayer(currentLayer);
  }

  currentLayer = L.geoJSON(primaryData, {
    style: getPrimaryStyle,
    onEachFeature: onEachPrimaryFeature,
  }).addTo(map);
}

function getPrimaryStyle(feature) {
  return {
    weight: 0.5,
    color: "#333",
    opacity: 0.7,
    fillOpacity: 0.75,
    fillColor: RISK_COLORS[feature.properties.risk_class] || "#ccc",
  };
}

function onEachPrimaryFeature(feature, layer) {
  layer.bindTooltip(
    `Block: ${feature.properties.block_id} | HVI: ${feature.properties.hvi_score}`,
  );

  layer.on({
    mouseover: (e) => highlightFeature(e.target),
    mouseout: (e) => resetHighlight(e.target),
    click: (e) => selectFeature(e.target, feature.properties),
  });
}

function highlightFeature(layer) {
  if (layer === selectedFeatureLayer) return;

  layer.setStyle({
    weight: 2,
    opacity: 1,
  });

  if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
    layer.bringToFront();
  }
}

function resetHighlight(layer, force = false) {
  if (layer === selectedFeatureLayer && !force) return;

  if (currentLayer) {
    currentLayer.resetStyle(layer);
  }
}

function selectFeature(layer, properties) {
  if (selectedFeatureLayer) {
    resetHighlight(selectedFeatureLayer, true);
  }

  selectedFeatureLayer = layer;

  layer.setStyle({
    weight: 3,
    color: "#000",
  });

  if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
    layer.bringToFront();
  }

  openSidebar(properties);
}

// 5. Layer Switching
async function switchLayer(layerName) {
  showLoading(true);
  closeSidebar();

  try {
    if (layerName === "hvi") {
      renderPrimaryLayer();
      updateLegend("hvi");
    } else {
      const data = await fetchThematicData(layerName);
      renderThematicLayer(layerName, data);
      updateLegend("blue");
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
        weight: 0.5,
        color: "#333",
        opacity: 0.7,
        fillOpacity: 0.55,
        fillColor: getBlueColor(val),
      };
    },
    onEachFeature: (feature, layer) => {
      layer.bindTooltip(
        `Block: ${feature.properties.block_id} | ${propName}: ${feature.properties[propName]}`,
      );

      layer.on({
        mouseover: (e) => highlightFeature(e.target),
        mouseout: (e) => resetHighlight(e.target),
        click: (e) => {
          if (primaryData) {
            const primaryFeature = primaryData.features.find(
              (f) => f.properties.block_id === feature.properties.block_id,
            );
            if (primaryFeature) {
              selectFeature(layer, primaryFeature.properties);
            }
          }
        },
      });
    },
  }).addTo(map);
}

function getBlueColor(val) {
  if (val === undefined || val === null) return "#ccc";
  if (val <= 20) return BLUE_SCALE[0];
  if (val <= 40) return BLUE_SCALE[1];
  if (val <= 60) return BLUE_SCALE[2];
  if (val <= 80) return BLUE_SCALE[3];
  return BLUE_SCALE[4];
}

// 6. Sidebar Controller
function openSidebar(props) {
  const sidebar = document.getElementById("sidebar");
  if (sidebar) sidebar.classList.add("sidebar-open");

  const defaultView = document.getElementById("sidebar-default");
  const detailView = document.getElementById("sidebar-detail");
  if (defaultView) defaultView.style.display = "none";
  if (detailView) detailView.style.display = "block";

  const setText = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text !== undefined ? text : "-";
  };

  setText("detail-block-id", props.block_id);

  const badge = document.getElementById("detail-risk-badge");
  if (badge) {
    badge.textContent = props.risk_class || "-";
    badge.className =
      "risk-badge" +
      (props.risk_class ? ` risk-${props.risk_class.toLowerCase()}` : "");
  }

  setText("detail-hvi-score", props.hvi_score);

  const setBar = (idBar, idVal, val) => {
    const bar = document.getElementById(idBar);
    if (bar) bar.style.width = (val || 0) + "%";
    setText(idVal, val);
  };

  setBar("bar-heat", "val-heat", props.ai_heat_exposure);
  setBar("bar-social", "val-social", props.social_sensitivity);
  setBar("bar-cooling", "val-cooling", props.cooling_deficit);

  setText("detail-population", props.estimated_population);
  setText("detail-intervention", props.intervention);

  const driversContainer = document.getElementById("detail-drivers");
  if (driversContainer) {
    driversContainer.innerHTML = "";
    if (props.top_drivers && Array.isArray(props.top_drivers)) {
      props.top_drivers.forEach((driver) => {
        const span = document.createElement("span");
        span.className = "driver-pill";
        span.textContent = DRIVER_LABELS[driver] || driver;
        driversContainer.appendChild(span);
      });
    }
  }

  setText("detail-ndvi", props.ndvi);
  setText("detail-ndwi", props.ndwi);
  setText("detail-ndbi", props.ndbi);
  setText("detail-green", props.distance_to_green);
  setText("detail-water", props.distance_to_water);
  setText("detail-building", props.building_density);
  setText("detail-popdensity", props.population_density);
}

function closeSidebar() {
  const sidebar = document.getElementById("sidebar");
  if (sidebar) sidebar.classList.remove("sidebar-open");

  const defaultView = document.getElementById("sidebar-default");
  const detailView = document.getElementById("sidebar-detail");
  if (defaultView) defaultView.style.display = "block";
  if (detailView) detailView.style.display = "none";

  if (selectedFeatureLayer) {
    resetHighlight(selectedFeatureLayer, true);
    selectedFeatureLayer = null;
  }
}

// 7. Search, 8. Filter, 9. Export & Event Listeners setup
function setupEventListeners() {
  // Radio buttons for Layer Switching
  const layerRadios = document.querySelectorAll('input[name="layer"]');
  layerRadios.forEach((radio) => {
    radio.addEventListener("change", (e) => switchLayer(e.target.value));
  });

  // Close Sidebar
  const closeBtn = document.getElementById("sidebar-close");
  if (closeBtn) closeBtn.addEventListener("click", closeSidebar);

  // Search
  const searchInput = document.getElementById("search-input");
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener("input", (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => handleSearch(e.target.value), 300);
    });
  }

  // Risk Filter
  const riskFilter = document.getElementById("risk-filter");
  if (riskFilter) {
    riskFilter.addEventListener("change", (e) =>
      handleRiskFilter(e.target.value),
    );
  }

  // Export
  const exportBtn = document.getElementById("export-btn");
  if (exportBtn) {
    exportBtn.addEventListener("click", () => {
      const a = document.createElement("a");
      a.href = "/data/vulnerability_blocks.geojson";
      a.download = "vulnerability_blocks.geojson";
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
    map.fitBounds(layer.getBounds(), { padding: [50, 50] });

    // Find properties from primaryData if needed
    let props = layer.feature.properties;
    if (primaryData && !props.hvi_score) {
      const pf = primaryData.features.find(
        (f) => f.properties.block_id === props.block_id,
      );
      if (pf) props = pf.properties;
    }
    selectFeature(layer, props);
  } else if (matches.length > 1 && matches.length < 10) {
    const group = new L.featureGroup(matches);
    map.fitBounds(group.getBounds(), { padding: [50, 50] });
  }
}

function handleRiskFilter(riskClass) {
  if (!currentLayer) return;

  currentLayer.eachLayer((layer) => {
    let layerRisk = layer.feature.properties.risk_class;

    // Check primary data if the risk_class property isn't in the thematic layer's properties
    if (!layerRisk && primaryData) {
      const pf = primaryData.features.find(
        (f) => f.properties.block_id === layer.feature.properties.block_id,
      );
      if (pf) layerRisk = pf.properties.risk_class;
    }

    if (riskClass === "All" || layerRisk === riskClass) {
      // Restore visibility
      const defaultStyle = currentLayer.options.style(layer.feature);
      layer.setStyle({
        opacity: defaultStyle.opacity || 0.7,
        fillOpacity: defaultStyle.fillOpacity || 0.75,
      });
    } else {
      // Hide
      layer.setStyle({ opacity: 0, fillOpacity: 0 });
    }
  });
}

// 10. Legend
function updateLegend(type) {
  const legendContent = document.getElementById("legend-content");
  if (!legendContent) return;

  legendContent.innerHTML = "";

  if (type === "hvi") {
    const items = [
      { label: "Critical 76-100", color: RISK_COLORS.Critical },
      { label: "High 56-75", color: RISK_COLORS.High },
      { label: "Medium 31-55", color: RISK_COLORS.Medium },
      { label: "Low 0-30", color: RISK_COLORS.Low },
    ];
    items.forEach((item) => {
      const row = document.createElement("div");
      row.style.display = "flex";
      row.style.alignItems = "center";
      row.style.marginBottom = "4px";
      row.innerHTML = `<span style="background-color: ${item.color}; width: 16px; height: 16px; display: inline-block; margin-right: 8px; border: 1px solid #ccc;"></span><span>${item.label}</span>`;
      legendContent.appendChild(row);
    });
  } else if (type === "blue") {
    const items = [
      { label: "0-20", color: BLUE_SCALE[0] },
      { label: "20-40", color: BLUE_SCALE[1] },
      { label: "40-60", color: BLUE_SCALE[2] },
      { label: "60-80", color: BLUE_SCALE[3] },
      { label: "80-100", color: BLUE_SCALE[4] },
    ];
    items.forEach((item) => {
      const row = document.createElement("div");
      row.style.display = "flex";
      row.style.alignItems = "center";
      row.style.marginBottom = "4px";
      row.innerHTML = `<span style="background-color: ${item.color}; width: 16px; height: 16px; display: inline-block; margin-right: 8px; border: 1px solid #ccc;"></span><span>${item.label}</span>`;
      legendContent.appendChild(row);
    });
  }
}
