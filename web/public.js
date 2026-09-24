/**
 * ThermalGuard — Citizen Heat Safety Portal (Madurai)
 * Streamlined, User-Friendly Hyperlocal Heat Intelligence and "My Location" Engine.
 */

(function () {
  "use strict";

  // ─── Constants ───
  const HARDCODED_LAT = 9.903964;
  const HARDCODED_LON = 78.092508;
  const CENTER = [9.921851, 78.118200];
  const DEFAULT_ZOOM = 13;
  const LOCATE_ZOOM = 17;

  const RISK_COLORS = {
    Critical: "#dc2626",
    High: "#f97316",
    Medium: "#eab308",
    Low: "#16a34a",
  };

  const RISK_TEXT_COLORS = {
    Critical: "#991b1b",
    High: "#c2410c",
    Medium: "#854d0e",
    Low: "#166534",
  };

  const RISK_BG_COLORS = {
    Critical: "#fee2e2",
    High: "#ffedd5",
    Medium: "#fef9c3",
    Low: "#dcfce7",
  };

  // Madurai Landmark / Neighborhood Lookup Points
  const MADURAI_LANDMARKS = [
    { name: "Pasumalai / Palanganatham", sub: "Madurai South", lat: 9.904, lon: 78.092 },
    { name: "Thirupparankundram Temple Area", sub: "Madurai Southwest", lat: 9.882, lon: 78.071 },
    { name: "Villapuram / Avaniyapuram", sub: "Madurai Southeast", lat: 9.892, lon: 78.125 },
    { name: "Periyar / Madurai Junction", sub: "Central Madurai", lat: 9.918, lon: 78.112 },
    { name: "Meenakshi Amman Temple Vicinity", sub: "Central Historic Core", lat: 9.919, lon: 78.119 },
    { name: "Simmakkal / Vaigai South Bank", sub: "Central North", lat: 9.926, lon: 78.121 },
    { name: "Goripalayam / Sellur", sub: "Vaigai North Bank", lat: 9.932, lon: 78.128 },
    { name: "Anna Nagar / Sathamangalam", sub: "Madurai East", lat: 9.918, lon: 78.148 },
    { name: "K.K. Nagar / Vandiyur Lake", sub: "Madurai Northeast", lat: 9.928, lon: 78.156 },
    { name: "Tallakulam / Chokkikulam", sub: "Madurai North", lat: 9.938, lon: 78.136 },
    { name: "Iyer Bungalow / Anaiyur", sub: "Madurai Far North", lat: 9.965, lon: 78.125 },
    { name: "Othakadai / Agricultural College", sub: "Madurai Far East", lat: 9.962, lon: 78.175 },
    { name: "Kochadai / Bethaniyapuram", sub: "Madurai West", lat: 9.931, lon: 78.089 },
    { name: "Vilangudi / Koodal Nagar", sub: "Madurai Northwest", lat: 9.954, lon: 78.098 },
    { name: "Nagamalai Pudukkottai", sub: "Madurai Far West", lat: 9.942, lon: 78.042 },
  ];

  // ─── Application State ───
  let map;
  let defaultBasemapLayer;
  let satelliteBasemapLayer;
  let satelliteLabelsLayer;
  let currentBasemap = "default";

  let choroplethLayer = null;
  let geojsonData = null;
  let featureLookup = new Map();

  let locationMarker = null;
  let highlightLayer = null;
  let currentFilter = "All";
  let currentThreshold = 0;
  let isDrawerOpen = false;
  let liveAirTemp = null;
  let liveFeelsTemp = null;

  // ─── Initialization ───
  document.addEventListener("DOMContentLoaded", init);

  function init() {
    initMap();
    initBasemaps();
    initEventListeners();
    loadBlocks();
  }

  // ─── Leaflet Map Setup ───
  function initMap() {
    map = L.map("map", {
      renderer: L.canvas({ padding: 0.5 }),
      zoomControl: false,
      minZoom: 11,
      maxZoom: 18,
      maxBounds: [
        [9.85, 78.0],
        [10.0, 78.23],
      ],
      maxBoundsViscosity: 1.0,
    }).setView(CENTER, DEFAULT_ZOOM);

    // Zoom control at bottom right
    L.control.zoom({ position: "bottomright" }).addTo(map);
  }

  // ─── Basemaps (Free, Zero API Key Required) ───
  function initBasemaps() {
    defaultBasemapLayer = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
      crossOrigin: true,
    });

    satelliteBasemapLayer = L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      {
        attribution: "Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics",
        maxZoom: 19,
        crossOrigin: true,
      }
    );

    satelliteLabelsLayer = L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
      {
        attribution: "&copy; Esri",
        maxZoom: 19,
        opacity: 0.85,
        crossOrigin: true,
      }
    );

    defaultBasemapLayer.addTo(map);
  }

  function setBasemap(type) {
    if (type === currentBasemap) return;
    currentBasemap = type;

    const btnDefault = document.getElementById("btn-basemap-default");
    const btnSatellite = document.getElementById("btn-basemap-satellite");

    if (type === "satellite") {
      if (map.hasLayer(defaultBasemapLayer)) map.removeLayer(defaultBasemapLayer);
      satelliteBasemapLayer.addTo(map);
      satelliteLabelsLayer.addTo(map);
      if (btnDefault) btnDefault.classList.remove("active");
      if (btnSatellite) btnSatellite.classList.add("active");
    } else {
      if (map.hasLayer(satelliteBasemapLayer)) map.removeLayer(satelliteBasemapLayer);
      if (map.hasLayer(satelliteLabelsLayer)) map.removeLayer(satelliteLabelsLayer);
      defaultBasemapLayer.addTo(map);
      if (btnSatellite) btnSatellite.classList.remove("active");
      if (btnDefault) btnDefault.classList.add("active");
    }
  }

  // ─── Event Listeners ───
  function initEventListeners() {
    // Basemap toggle
    const btnDefault = document.getElementById("btn-basemap-default");
    const btnSatellite = document.getElementById("btn-basemap-satellite");
    if (btnDefault) btnDefault.addEventListener("click", () => setBasemap("default"));
    if (btnSatellite) btnSatellite.addEventListener("click", () => setBasemap("satellite"));

    // Segmented risk buttons
    const riskButtons = document.querySelectorAll("#risk-segmented-control .segment-btn");
    riskButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        riskButtons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        currentFilter = btn.dataset.risk || "All";
        applyFilters();
      });
    });

    // Threshold Slider
    const thresholdSlider = document.getElementById("threshold-slider");
    const sliderCurrentVal = document.getElementById("slider-current-val");
    const sliderResetBtn = document.getElementById("slider-reset-btn");

    if (thresholdSlider) {
      thresholdSlider.addEventListener("input", (e) => {
        currentThreshold = Number(e.target.value);
        if (sliderCurrentVal) sliderCurrentVal.textContent = `≥ ${currentThreshold}`;
        applyFilters();
      });
    }

    if (sliderResetBtn) {
      sliderResetBtn.addEventListener("click", () => {
        currentThreshold = 0;
        if (thresholdSlider) thresholdSlider.value = "0";
        if (sliderCurrentVal) sliderCurrentVal.textContent = "≥ 0";
        applyFilters();
      });
    }

    // Reset View
    const btnResetView = document.getElementById("btn-reset-view");
    if (btnResetView) {
      btnResetView.addEventListener("click", () => {
        map.setView(CENTER, DEFAULT_ZOOM);
      });
    }

    // "My Location"
    const btnMyLocation = document.getElementById("btn-my-location");
    if (btnMyLocation) {
      btnMyLocation.addEventListener("click", onMyLocation);
    }

    // Drawer close & Esc key
    const sidebarClose = document.getElementById("sidebar-close");
    if (sidebarClose) {
      sidebarClose.addEventListener("click", closeDrawer);
    }

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && isDrawerOpen) {
        closeDrawer();
      }
    });

    // Sector Search
    const searchInput = document.getElementById("search-input");
    const searchClear = document.getElementById("search-clear");

    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        const val = e.target.value.trim().toUpperCase();
        if (searchClear) searchClear.style.display = val ? "block" : "none";
      });

      searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          const val = searchInput.value.trim().toUpperCase();
          if (val) executeSearch(val);
        }
      });
    }

    if (searchClear) {
      searchClear.addEventListener("click", () => {
        if (searchInput) searchInput.value = "";
        searchClear.style.display = "none";
      });
    }
  }

  // ─── Load Vulnerability Blocks ───
  async function loadBlocks() {
    try {
      const res = await fetch("/data/vulnerability_blocks.geojson");
      if (!res.ok) throw new Error("Could not load vulnerability blocks");
      geojsonData = await res.json();

      let tempSum = 0;
      let tempCount = 0;

      for (const feat of geojsonData.features) {
        const p = feat.properties;
        if (p && p.block_id) {
          featureLookup.set(p.block_id, feat);
          if (p.surface_temp_celsius) {
            tempSum += Number(p.surface_temp_celsius);
            tempCount++;
          }
        }
      }

      // Fetch live real-time ambient weather for citizen topbar
      try {
        const fRes = await fetch("/api/forecast/days");
        if (fRes.ok) {
          const fData = await fRes.json();
          if (fData.current && fData.current.temperature_celsius != null) {
            liveAirTemp = Number(fData.current.temperature_celsius).toFixed(1);
            liveFeelsTemp = Number(fData.current.wbgt_celsius || fData.current.apparent_temperature_celsius).toFixed(1);
            const avgPill = document.getElementById("topbar-avg-temp");
            if (avgPill) {
              avgPill.textContent = `Live Air: ${liveAirTemp}°C`;
              avgPill.title = `Madurai Real-time Weather: Air ${liveAirTemp}°C, Feels ${liveFeelsTemp}°C (Humidity: ${fData.current.relative_humidity_pct}%)`;
            }
          }
        }
      } catch (fErr) {
        console.warn("Could not fetch live forecast:", fErr);
      }

      if (tempCount > 0 && !liveAirTemp) {
        const avgTemp = (tempSum / tempCount).toFixed(1);
        const avgPill = document.getElementById("topbar-avg-temp");
        if (avgPill) avgPill.textContent = `Roof Avg: ${avgTemp}°C`;
      }

      renderChoropleth();
    } catch (err) {
      console.error("Failed to load blocks:", err);
    }
  }

  // ─── Render Choropleth ───
  function renderChoropleth() {
    if (!geojsonData) return;

    choroplethLayer = L.geoJSON(geojsonData, {
      style: function (feature) {
        const p = feature.properties;
        return {
          fillColor: RISK_COLORS[p.risk_class] || "#94a3b8",
          fillOpacity: 0.55,
          stroke: false,
        };
      },
      onEachFeature: function (feature, layer) {
        const p = feature.properties;
        layer.bindTooltip(
          () => {
            const airStr = liveAirTemp ? `${liveAirTemp}°C` : "28.0°C";
            return `<strong>Sector ${p.block_id}</strong><br/>${p.risk_class} Risk · HVI ${p.hvi_score}<br/>🌤️ Outdoor Air: ${airStr} &bull; ♨️ Roof Heat: ${p.surface_temp_celsius}°C`;
          },
          { className: "custom-map-tooltip", sticky: true, opacity: 0.95 }
        );

        layer.on("click", function () {
          highlightBlock(feature);
          const centroid = getPolygonCentroid(feature.geometry);
          const landmark = resolveNeighborhood(centroid[0], centroid[1]);
          fetchAndShowBlock(p.block_id, landmark);
        });
      },
    }).addTo(map);
  }

  // ─── Real-time Filter Application ───
  function applyFilters() {
    if (!choroplethLayer) return;

    choroplethLayer.setStyle(function (feature) {
      const p = feature.properties;
      const score = Number(p.hvi_score || 0);
      const matchesThreshold = score >= currentThreshold;
      const matchesRisk = currentFilter === "All" || p.risk_class === currentFilter;

      if (matchesThreshold && matchesRisk) {
        return {
          fillColor: RISK_COLORS[p.risk_class] || "#94a3b8",
          fillOpacity: 0.55,
          stroke: false,
        };
      } else {
        return {
          fillOpacity: 0,
          stroke: false,
        };
      }
    });
  }

  // ─── Geometry & Polygon Ray Casting ───
  function pointInPolygon(lat, lng, polygon) {
    const ring = polygon[0];
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const xi = ring[i][1], yi = ring[i][0];
      const xj = ring[j][1], yj = ring[j][0];
      const intersect =
        yi > lng !== yj > lng && lat < ((xj - xi) * (lng - yi)) / (yj - yi) + xi;
      if (intersect) inside = !inside;
    }
    return inside;
  }

  function findBlockAtPoint(lat, lng) {
    if (!geojsonData) return null;
    for (const feature of geojsonData.features) {
      const geom = feature.geometry;
      if (geom.type === "Polygon") {
        if (pointInPolygon(lat, lng, geom.coordinates)) return feature;
      } else if (geom.type === "MultiPolygon") {
        for (const poly of geom.coordinates) {
          if (pointInPolygon(lat, lng, poly)) return feature;
        }
      }
    }
    return null;
  }

  function getPolygonCentroid(geometry) {
    let coords = [];
    if (geometry.type === "Polygon") {
      coords = geometry.coordinates[0];
    } else if (geometry.type === "MultiPolygon") {
      coords = geometry.coordinates[0][0];
    }
    if (!coords || coords.length === 0) return [CENTER[0], CENTER[1]];

    let sumLat = 0, sumLon = 0;
    for (const pt of coords) {
      sumLon += pt[0];
      sumLat += pt[1];
    }
    return [sumLat / coords.length, sumLon / coords.length];
  }

  // ─── Landmark Resolver ───
  function resolveNeighborhood(lat, lon) {
    let nearest = MADURAI_LANDMARKS[0];
    let minDistance = Infinity;

    for (const lm of MADURAI_LANDMARKS) {
      const dLat = lat - lm.lat;
      const dLon = lon - lm.lon;
      const dist = dLat * dLat + dLon * dLon;
      if (dist < minDistance) {
        minDistance = dist;
        nearest = lm;
      }
    }
    return nearest;
  }

  // ─── Highlight Block ───
  function highlightBlock(feature) {
    if (highlightLayer) {
      map.removeLayer(highlightLayer);
      highlightLayer = null;
    }

    highlightLayer = L.geoJSON(feature, {
      style: {
        fillColor: "transparent",
        fillOpacity: 0,
        color: "#38bdf8",
        weight: 3.5,
        opacity: 1,
      },
    }).addTo(map);
  }

  // ─── Location Beacon Marker ───
  function placeLocationMarker(lat, lng) {
    if (locationMarker) {
      map.removeLayer(locationMarker);
    }

    const icon = L.divIcon({
      className: "",
      html: `
        <div class="pulse-marker-container">
          <div class="pulse-marker-ring"></div>
          <div class="pulse-marker-center"></div>
        </div>
      `,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });

    locationMarker = L.marker([lat, lng], { icon: icon, interactive: false }).addTo(map);
  }

  // ─── Search Execution ───
  function executeSearch(query) {
    const feat = featureLookup.get(query);
    if (!feat) {
      alert(`Sector "${query}" not found. Try searching for KIB-27897 or KIB-0001.`);
      return;
    }

    highlightBlock(feat);
    const bounds = L.geoJSON(feat).getBounds();
    map.fitBounds(bounds, { maxZoom: 16, padding: [60, 60] });

    const centroid = getPolygonCentroid(feat.geometry);
    const landmark = resolveNeighborhood(centroid[0], centroid[1]);

    updateLocationChip(landmark.name, query, feat.properties.risk_class);
    fetchAndShowBlock(query, landmark);
  }

  // ─── "My Location" Handler ───
  function onMyLocation() {
    const btn = document.getElementById("btn-my-location");
    btn.style.pointerEvents = "none";
    btn.style.opacity = "0.75";

    // 1. Fly to location
    map.flyTo([HARDCODED_LAT, HARDCODED_LON], LOCATE_ZOOM, {
      duration: 1.4,
      easeLinearity: 0.25,
    });

    // 2. Beacon & Block Locate
    setTimeout(() => {
      placeLocationMarker(HARDCODED_LAT, HARDCODED_LON);

      const block = findBlockAtPoint(HARDCODED_LAT, HARDCODED_LON);
      if (block) {
        highlightBlock(block);
        const landmark = resolveNeighborhood(HARDCODED_LAT, HARDCODED_LON);
        updateLocationChip(landmark.name, block.properties.block_id, block.properties.risk_class);
        fetchAndShowBlock(block.properties.block_id, landmark);
      } else {
        alert("Location is outside the mapped sector grid.");
      }

      btn.style.pointerEvents = "";
      btn.style.opacity = "";
    }, 1500);
  }

  function updateLocationChip(placeName, blockId, riskClass) {
    const chip = document.getElementById("location-chip");
    const chipText = document.getElementById("location-chip-text");
    if (chip && chipText) {
      chipText.textContent = `${placeName} · ${blockId} (${riskClass} Risk)`;
      chip.style.display = "inline-flex";
    }
  }

  // ─── Drawer Controls ───
  function openDrawer() {
    const sidebar = document.getElementById("sidebar");
    if (sidebar) sidebar.classList.add("open");
    isDrawerOpen = true;
  }

  function closeDrawer() {
    const sidebar = document.getElementById("sidebar");
    if (sidebar) sidebar.classList.remove("open");
    isDrawerOpen = false;

    if (highlightLayer) {
      map.removeLayer(highlightLayer);
      highlightLayer = null;
    }
  }

  function setDrawerLoading(isLoading) {
    const loadingElem = document.getElementById("drawer-loading");
    const detailElem = document.getElementById("sidebar-detail");
    if (loadingElem && detailElem) {
      loadingElem.style.display = isLoading ? "flex" : "none";
      detailElem.style.display = isLoading ? "none" : "flex";
    }
  }

  // ─── Fetch Intelligence & Render ───
  async function fetchAndShowBlock(blockId, landmark) {
    openDrawer();
    setDrawerLoading(true);

    try {
      const res = await fetch(`/api/blocks/${blockId}`);
      if (!res.ok) throw new Error("Block not found");
      const data = await res.json();
      renderDrawer(data, landmark);
    } catch (err) {
      console.error("Could not fetch block data:", err);
      const detailElem = document.getElementById("sidebar-detail");
      if (detailElem) {
        detailElem.innerHTML = `
          <div style="text-align: center; padding: 28px 16px;">
            <p style="color: #ef4444; font-weight: 700;">Could not load heat analysis.</p>
            <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 6px;">Please check connection and retry.</p>
          </div>
        `;
      }
    } finally {
      setDrawerLoading(false);
    }
  }

  // ─── Streamlined Citizen Drawer Renderer ───
  function renderDrawer(data, landmark) {
    const rc = data.risk_class || "Medium";
    const blockId = data.block_id || "—";
    const hvi = data.hvi_score || 0;
    const surfTemp = data.surface_temp_display || `${data.surface_temp_celsius || "--"}°C`;
    const anomalyVal = parseFloat(data.temp_anomaly_celsius || 0);
    const anomaly = `${anomalyVal > 0 ? "+" : ""}${anomalyVal.toFixed(1)}°C`;

    // 1. Place Info
    const placeName = landmark ? landmark.name : "Madurai Urban Sector";
    const placeSub = landmark ? `${landmark.sub} · Sector ${blockId}` : `Sector ${blockId}`;

    const elemPlaceName = document.getElementById("detail-place-name");
    const elemPlaceSub = document.getElementById("detail-place-sub");
    if (elemPlaceName) elemPlaceName.textContent = placeName;
    if (elemPlaceSub) elemPlaceSub.textContent = placeSub;

    // 2. Risk Alert Banner
    const elemRiskBadge = document.getElementById("detail-risk-badge");
    const elemAlertText = document.getElementById("detail-alert-text");
    const elemHvi = document.getElementById("detail-hvi-score");

    const alertLabels = {
      Critical: "⚠️ CRITICAL HEAT ALERT",
      High: "🟠 ELEVATED HEAT RISK",
      Medium: "🟡 MODERATE HEAT LEVEL",
      Low: "🟢 SAFE & COMFORTABLE",
    };

    if (elemRiskBadge) {
      elemRiskBadge.className = `citizen-alert-banner risk-${rc.toLowerCase()}`;
    }
    if (elemAlertText) {
      elemAlertText.textContent = alertLabels[rc] || "HEAT ADVISORY";
    }
    if (elemHvi) {
      elemHvi.textContent = `HVI ${hvi}/100`;
    }

    // 3. Three Glanceable Temp Numbers & Plain-Language Explainer
    const elemAirTemp = document.getElementById("detail-air-temp");
    const elemSurfTemp = document.getElementById("detail-surface-temp");
    const elemFeelsTemp = document.getElementById("detail-feels-temp");
    const explainerAirVal = document.getElementById("explainer-air-val");

    const airVal = data.realtime_weather?.temperature_celsius ?? data.ambient_temp_celsius ?? (liveAirTemp ? Number(liveAirTemp) : null);
    const airText = airVal != null ? `${Number(airVal).toFixed(1)}°C` : "--°C";

    const feelsVal = data.realtime_weather?.wbgt_celsius ?? data.forecast_trajectory?.[0]?.local_wbgt ?? (liveFeelsTemp ? Number(liveFeelsTemp) : null);
    const feelsText = feelsVal != null ? `${Number(feelsVal).toFixed(1)}°C` : "--°C";

    if (elemAirTemp) {
      elemAirTemp.textContent = airText;
    }
    if (elemSurfTemp) {
      elemSurfTemp.textContent = surfTemp;
      elemSurfTemp.style.color = RISK_COLORS[rc] || "#dc2626";
    }
    if (elemFeelsTemp) {
      elemFeelsTemp.textContent = feelsText;
    }
    if (explainerAirVal) {
      explainerAirVal.textContent = airText;
    }

    const elemAnomaly = document.getElementById("detail-temp-anomaly");
    if (elemAnomaly) {
      elemAnomaly.textContent = anomaly;
      elemAnomaly.style.color = anomalyVal > 0 ? "#b91c1c" : "#047857";
    }

    // Safe state vs Risk state toggle
    const safeCard = document.getElementById("safe-state-card");
    const riskContent = document.getElementById("risk-state-content");

    if (rc === "Low") {
      if (safeCard) safeCard.style.display = "block";
      if (riskContent) riskContent.style.display = "none";
      return;
    }

    if (safeCard) safeCard.style.display = "none";
    if (riskContent) riskContent.style.display = "block";

    // 4. Danger Hours
    const heatHealth = data.heat_health || {};
    const dangerWindow = heatHealth.peak_stress_window ? heatHealth.peak_stress_window.split("(")[0].trim() : "11:00 AM – 3:30 PM";
    const elemDangerHours = document.getElementById("detail-danger-hours");
    if (elemDangerHours) elemDangerHours.textContent = dangerWindow;

    // 5. Action Checklist Items
    const elemHydrate = document.getElementById("action-item-hydrate");
    const elemShade = document.getElementById("action-item-shade");
    const elemVentilate = document.getElementById("action-item-ventilate");

    if (elemHydrate) {
      elemHydrate.innerHTML = `<strong>Drink water frequently</strong> — consume ORS or water every 45–60 mins, especially during ${dangerWindow}.`;
    }
    if (elemShade) {
      elemShade.innerHTML = `<strong>Avoid direct sun & exertion</strong> — pause strenuous outdoor work or seek covered shelter.`;
    }
    if (elemVentilate) {
      elemVentilate.innerHTML = `<strong>Ventilate indoor rooms</strong> — unshaded tin roofs trap heat; open opposing windows for cross-draft airflow.`;
    }

    // 6. Quick Microclimate Glance Badges
    const canopyPct = data.canopy_pct != null ? data.canopy_pct : 0;
    const treeBadge = document.getElementById("quick-shade-badge");
    if (treeBadge) {
      treeBadge.textContent = `${canopyPct}% (${canopyPct < 25 ? "Scarce" : canopyPct < 50 ? "Moderate" : "Good"})`;
    }

    const roofBadge = document.getElementById("quick-roof-badge");
    if (roofBadge) {
      const isMetal = data.archetype_title ? data.archetype_title.toLowerCase().includes("metal") : true;
      roofBadge.textContent = isMetal ? "Tin / Sheet Roofs" : "Masonry Built";
    }

    const waterBadge = document.getElementById("quick-water-badge");
    if (waterBadge) {
      const distW = data.dist_water_m != null ? `${data.dist_water_m}m to Water` : "";
      const distG = data.dist_green_m != null ? `${data.dist_green_m}m to Park` : "";
      waterBadge.textContent = distW || distG || "Urban Basin";
    }

    // 7. 5-Day Outlook Strip
    const trajectory = data.forecast_trajectory || [];
    const elemTimeline = document.getElementById("detail-forecast-timeline");
    if (elemTimeline) {
      if (trajectory.length === 0) {
        elemTimeline.innerHTML = '<div style="font-size: 0.75rem; color: var(--text-subtle); grid-column: span 5; text-align: center;">Forecast updating...</div>';
      } else {
        elemTimeline.innerHTML = trajectory
          .map((dayItem, idx) => {
            const tier = dayItem.health_risk_tier || "High";
            const tagCls = `tag-${tier.toLowerCase()}`;
            return `
              <div class="forecast-pill ${idx === 0 ? "active-today" : ""}">
                <span class="forecast-pill-day">${idx === 0 ? "Today" : `Day ${dayItem.day}`}</span>
                <span class="forecast-pill-wbgt">${dayItem.local_wbgt}°</span>
                <span class="forecast-pill-tag ${tagCls}">${tier}</span>
              </div>
            `;
          })
          .join("");
      }
    }

    // 8. Collapsible Technical Data
    // SHAP drivers
    const shapFactors = data.shap_factors || [];
    const elemShapList = document.getElementById("detail-shap-list");
    if (elemShapList) {
      elemShapList.innerHTML = shapFactors
        .slice(0, 3)
        .map((f) => {
          const val = Number(f.shap_value || 0);
          const isWarming = val >= 0;
          const cls = isWarming ? "warming" : "cooling";
          const arrow = isWarming ? "↑" : "↓";
          return `
            <div class="shap-driver-row">
              <span style="color: var(--text-main); font-weight: 500;">${f.name || f.feature}</span>
              <span class="shap-driver-val ${cls}">${arrow} ${f.contribution_celsius}</span>
            </div>
          `;
        })
        .join("");
    }

    // Causes
    const causes = data.why_hot_causes || data.key_causes || [];
    const elemCausesList = document.getElementById("detail-causes-list");
    if (elemCausesList) {
      elemCausesList.innerHTML = causes
        .map((c) => `<li style="margin-bottom: 4px; line-height: 1.4;">${c}</li>`)
        .join("");
    }

    // Planned municipal interventions
    const actions = data.required_controls || data.key_actions || [];
    const elemActionsList = document.getElementById("detail-actions-list");
    if (elemActionsList) {
      elemActionsList.innerHTML = actions
        .map((a) => `<li style="margin-bottom: 6px; line-height: 1.4;">${a}</li>`)
        .join("");
    }
  }
})();
