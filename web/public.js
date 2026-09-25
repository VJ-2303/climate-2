/**
 * ThermalGuard — Citizen Heat Safety Portal (Madurai)
 * Curated, Actionable Hyperlocal Heat Intelligence and Responsive Split View Engine.
 * Inspired by OpenWeather human-centered ergonomics.
 * 100% Zero-Emoji · High Contrast · Accessible · Pure Vector SVG Icons.
 */

(function () {
  "use strict";

  // ─── Constants & Coordinates ───
  const HARDCODED_LAT = 9.903964;
  const HARDCODED_LON = 78.092508;
  const CENTER = [9.921851, 78.118200];
  const DEFAULT_ZOOM = 13;
  const LOCATE_ZOOM = 16;

  const RISK_COLORS = {
    Critical: "#dc2626",
    High: "#ea580c",
    Medium: "#d97706",
    Low: "#16a34a",
  };

  // Madurai Landmark / Neighborhood Lookup Points
  const MADURAI_LANDMARKS = [
    { name: "Pasumalai / Palanganatham", sub: "Madurai South", lat: 9.904, lon: 78.092, tag: "Pasumalai" },
    { name: "Meenakshi Amman Temple Vicinity", sub: "Central Historic Core", lat: 9.919, lon: 78.119, tag: "Meenakshi Temple" },
    { name: "Periyar / Madurai Junction", sub: "Central Madurai", lat: 9.918, lon: 78.112, tag: "Periyar Station" },
    { name: "Goripalayam / Sellur", sub: "Vaigai North Bank", lat: 9.932, lon: 78.128, tag: "Goripalayam" },
    { name: "Anna Nagar / Sathamangalam", sub: "Madurai East", lat: 9.918, lon: 78.148, tag: "Anna Nagar" },
    { name: "K.K. Nagar / Vandiyur Lake", sub: "Madurai Northeast", lat: 9.928, lon: 78.156, tag: "KK Nagar" },
    { name: "Simmakkal / Vaigai South Bank", sub: "Central North", lat: 9.926, lon: 78.121, tag: "Simmakkal" },
    { name: "Tallakulam / Chokkikulam", sub: "Madurai North", lat: 9.938, lon: 78.136, tag: "Tallakulam" },
    { name: "Thirupparankundram Temple Area", sub: "Madurai Southwest", lat: 9.882, lon: 78.071, tag: "Thirupparankundram" },
    { name: "Villapuram / Avaniyapuram", sub: "Madurai Southeast", lat: 9.892, lon: 78.125, tag: "Avaniyapuram" },
    { name: "Othakadai / Agricultural College", sub: "Madurai Far East", lat: 9.962, lon: 78.175, tag: "Othakadai" },
    { name: "Kochadai / Bethaniyapuram", sub: "Madurai West", lat: 9.931, lon: 78.089, tag: "Kochadai" },
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
  let currentActiveBlockId = "KIB-27897";
  let currentActiveLandmark = MADURAI_LANDMARKS[0];
  let currentBlockData = null;

  let liveAirTemp = 35.8;
  let liveFeelsTemp = 32.0;
  let liveHumidity = 64;
  let liveWindSpeed = 3.2;
  let liveHourlyForecast = [];
  let isWeatherRefreshing = false;
  let currentLang = "EN"; // "EN" or "TA"

  // ─── Initialization ───
  document.addEventListener("DOMContentLoaded", init);

  function init() {
    initMap();
    initBasemaps();
    renderNeighborhoodChips();
    initLiveClock();
    initEventListeners();
    fetchWeather(false);
    loadBlocks();
    // 10-minute automated meteorological background sync
    setInterval(() => fetchWeather(false), 10 * 60 * 1000);
  }

  // ─── Leaflet Map Setup ───
  function initMap() {
    const mapContainer = document.getElementById("ow-map");
    if (!mapContainer) return;

    map = L.map("ow-map", {
      renderer: L.canvas({ padding: 0.5 }),
      zoomControl: false,
      scrollWheelZoom: false, // Prevents map from trapping mouse-wheel page scroll
      minZoom: 11,
      maxZoom: 18,
      maxBounds: [
        [9.85, 78.0],
        [10.0, 78.23],
      ],
      maxBoundsViscosity: 1.0,
    }).setView(CENTER, DEFAULT_ZOOM);

    // Zoom control in bottom right
    L.control.zoom({ position: "bottomright" }).addTo(map);

    // Allow wheel zoom only when user actively clicks on map; release when mouse leaves
    map.on("click", () => {
      map.scrollWheelZoom.enable();
    });
    mapContainer.addEventListener("mouseleave", () => {
      map.scrollWheelZoom.disable();
    });
  }

  // ─── Basemaps ───
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

  // ─── Live Clock ───
  function initLiveClock() {
    updateClock();
    setInterval(updateClock, 15000);
  }

  function updateClock() {
    const clockElem = document.getElementById("live-clock");
    if (!clockElem) return;
    const now = new Date();
    const options = { hour: "numeric", minute: "2-digit", hour12: true, timeZone: "Asia/Kolkata" };
    clockElem.textContent = `${now.toLocaleTimeString("en-US", options)} IST`;
  }

  // ─── Render Neighborhood Quick-Chips ───
  function renderNeighborhoodChips() {
    const container = document.getElementById("neighborhood-chips");
    if (!container) return;

    const labelHtml = `<span class="ow-chips-label" id="label-quick-explore">${currentLang === "TA" ? "விரைவு பகுதிகள்:" : "Quick Areas:"}</span>`;
    const chipsHtml = MADURAI_LANDMARKS.slice(0, 8)
      .map(
        (lm, idx) => `
        <button class="ow-chip ${idx === 0 ? "active" : ""}" data-idx="${idx}" title="${lm.name}">
          ${lm.tag}
        </button>
      `
      )
      .join("");

    container.innerHTML = labelHtml + chipsHtml;

    container.querySelectorAll(".ow-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        container.querySelectorAll(".ow-chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        const idx = parseInt(chip.getAttribute("data-idx"), 10);
        selectLandmark(MADURAI_LANDMARKS[idx]);
      });
    });
  }

  // ─── Select Landmark ───
  function selectLandmark(landmark) {
    currentActiveLandmark = landmark;
    map.flyTo([landmark.lat, landmark.lon], LOCATE_ZOOM, {
      duration: 1.2,
      easeLinearity: 0.25,
    });
    placeLocationMarker(landmark.lat, landmark.lon);

    const block = findBlockAtPoint(landmark.lat, landmark.lon);
    if (block) {
      highlightBlock(block);
      fetchAndShowBlock(block.properties.block_id, landmark);
    } else {
      fetchAndShowBlock("KIB-27897", landmark);
    }
  }

  // ─── Live Meteorological Forecasting (10m Refresh + Manual Sync) ───
  async function fetchWeather(force = false) {
    if (isWeatherRefreshing) return;
    isWeatherRefreshing = true;

    const refreshBtn = document.getElementById("btn-weather-refresh");
    if (refreshBtn) refreshBtn.classList.add("spinning");

    try {
      const url = force ? "/api/forecast/days?force=true" : "/api/forecast/days";
      const fRes = await fetch(url);
      if (fRes.ok) {
        const fData = await fRes.json();
        if (fData.current && fData.current.temperature_celsius != null) {
          liveAirTemp = Number(fData.current.temperature_celsius);
          liveFeelsTemp = Number(fData.current.wbgt_celsius || fData.current.apparent_temperature_celsius);
          if (fData.current.relative_humidity_pct != null) {
            liveHumidity = Math.round(fData.current.relative_humidity_pct);
          }
          if (fData.current.wind_speed_ms != null) {
            liveWindSpeed = Number(fData.current.wind_speed_ms);
          }
          const avgPill = document.getElementById("topbar-avg-temp");
          if (avgPill) {
            avgPill.textContent = `Madurai Heat Safety · Live Air: ${liveAirTemp.toFixed(1)}°C · Feels ${liveFeelsTemp.toFixed(1)}°C`;
          }
        }
        if (Array.isArray(fData.hourly) && fData.hourly.length > 0) {
          liveHourlyForecast = fData.hourly;
        }

        if (currentBlockData && currentActiveLandmark) {
          renderFeedCards(currentBlockData, currentActiveLandmark);
          renderDiurnalChartAndScrubber(currentBlockData);
        }
      }
    } catch (fErr) {
      console.warn("Could not fetch live forecast:", fErr);
    } finally {
      isWeatherRefreshing = false;
      if (refreshBtn) {
        setTimeout(() => refreshBtn.classList.remove("spinning"), 400);
      }
    }
  }

  // ─── Load Dataset & Initial View ───
  async function loadBlocks() {
    try {
      // 1. Fetch GeoJSON sectors
      const res = await fetch("/data/vulnerability_blocks.geojson");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      geojsonData = await res.json();

      featureLookup.clear();
      for (const feat of geojsonData.features) {
        featureLookup.set(feat.properties.block_id, feat);
      }

      renderChoropleth();

      // 3. Select default location (Pasumalai) immediately on page load
      selectLandmark(MADURAI_LANDMARKS[0]);
    } catch (err) {
      console.error("Failed to load blocks:", err);
    }
  }

  // ─── Render Map Choropleth ───
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
            const airStr = `${liveAirTemp.toFixed(1)}°C`;
            return `<strong>Sector ${p.block_id}</strong><br/>${p.risk_class} Risk &bull; Air: ${airStr} &bull; Roof: ${p.surface_temp_celsius}&deg;C`;
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

  // ─── Geometry & Centroid Helpers ───
  function pointInPolygon(lat, lng, polygon) {
    const ring = polygon[0];
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const xi = ring[i][0], yi = ring[i][1];
      const xj = ring[j][0], yj = ring[j][1];
      const intersect = yi > lat !== yj > lat && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi;
      if (intersect) inside = !inside;
    }
    return inside;
  }

  function findBlockAtPoint(lat, lng) {
    if (!geojsonData) return null;
    for (const feat of geojsonData.features) {
      if (feat.geometry.type === "Polygon") {
        if (pointInPolygon(lat, lng, feat.geometry.coordinates)) return feat;
      }
    }
    return null;
  }

  function getPolygonCentroid(geom) {
    if (geom.type !== "Polygon") return CENTER;
    const ring = geom.coordinates[0];
    let xSum = 0, ySum = 0;
    const len = ring.length;
    for (let i = 0; i < len; i++) {
      xSum += ring[i][0];
      ySum += ring[i][1];
    }
    return [ySum / len, xSum / len];
  }

  function resolveNeighborhood(lat, lng) {
    let nearest = MADURAI_LANDMARKS[0];
    let minD = Infinity;
    for (const lm of MADURAI_LANDMARKS) {
      const d = (lm.lat - lat) ** 2 + (lm.lon - lng) ** 2;
      if (d < minD) {
        minD = d;
        nearest = lm;
      }
    }
    return nearest;
  }

  // ─── Map Marker & Highlight ───
  function highlightBlock(feat) {
    if (highlightLayer) {
      map.removeLayer(highlightLayer);
      highlightLayer = null;
    }
    highlightLayer = L.geoJSON(feat, {
      style: {
        color: "#ffffff",
        weight: 3,
        fillColor: "#ea580c",
        fillOpacity: 0.40,
      },
    }).addTo(map);
  }

  function placeLocationMarker(lat, lng) {
    if (locationMarker) {
      map.removeLayer(locationMarker);
      locationMarker = null;
    }
    const icon = L.divIcon({
      className: "pulse-beacon-div-icon",
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
    if (!query) return;
    const qLower = query.toLowerCase().trim();

    // 1. Check landmarks match
    const matchedLandmark = MADURAI_LANDMARKS.find(
      (lm) => lm.name.toLowerCase().includes(qLower) || lm.tag.toLowerCase().includes(qLower)
    );
    if (matchedLandmark) {
      selectLandmark(matchedLandmark);
      return;
    }

    // 2. Check sector ID match (e.g. KIB-27897)
    const feat = featureLookup.get(query.toUpperCase());
    if (feat) {
      highlightBlock(feat);
      const bounds = L.geoJSON(feat).getBounds();
      map.fitBounds(bounds, { maxZoom: 16, padding: [60, 60] });
      const centroid = getPolygonCentroid(feat.geometry);
      const landmark = resolveNeighborhood(centroid[0], centroid[1]);
      fetchAndShowBlock(query.toUpperCase(), landmark);
      return;
    }

    alert(`Location "${query}" not found. Try searching for "Meenakshi Temple", "Anna Nagar", "Goripalayam", or a sector ID.`);
  }

  // ─── Locate Me Handler ───
  function onLocateMe() {
    const btn = document.getElementById("btn-top-locate");
    const mapBtn = document.getElementById("btn-my-location");
    if (btn) { btn.style.opacity = "0.7"; btn.style.pointerEvents = "none"; }
    if (mapBtn) { mapBtn.style.opacity = "0.7"; mapBtn.style.pointerEvents = "none"; }

    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = pos.coords.latitude;
          const lon = pos.coords.longitude;
          if (lat >= 9.85 && lat <= 10.0 && lon >= 78.0 && lon <= 78.23) {
            handleResolvedLocation(lat, lon);
          } else {
            handleResolvedLocation(HARDCODED_LAT, HARDCODED_LON);
          }
          resetLocateButtons(btn, mapBtn);
        },
        () => {
          handleResolvedLocation(HARDCODED_LAT, HARDCODED_LON);
          resetLocateButtons(btn, mapBtn);
        },
        { timeout: 4000 }
      );
    } else {
      handleResolvedLocation(HARDCODED_LAT, HARDCODED_LON);
      resetLocateButtons(btn, mapBtn);
    }
  }

  function handleResolvedLocation(lat, lon) {
    map.flyTo([lat, lon], LOCATE_ZOOM, { duration: 1.4, easeLinearity: 0.25 });
    placeLocationMarker(lat, lon);
    const block = findBlockAtPoint(lat, lon);
    const landmark = resolveNeighborhood(lat, lon);
    const blockId = block ? block.properties.block_id : "KIB-27897";
    if (block) highlightBlock(block);
    fetchAndShowBlock(blockId, landmark);
  }

  function resetLocateButtons(b1, b2) {
    if (b1) { b1.style.opacity = ""; b1.style.pointerEvents = ""; }
    if (b2) { b2.style.opacity = ""; b2.style.pointerEvents = ""; }
  }

  // ─── Fetch Block Details & Render ───
  async function fetchAndShowBlock(blockId, landmark) {
    currentActiveBlockId = blockId;
    currentActiveLandmark = landmark;

    try {
      const res = await fetch(`/api/blocks/${blockId}`);
      if (!res.ok) throw new Error("Block not found");
      const data = await res.json();
      currentBlockData = data;
      renderFeedCards(data, landmark);
      renderDiurnalChartAndScrubber(data);
    } catch (err) {
      console.error("Could not fetch block data:", err);
    }
  }

  // ─── Render Curated Citizen Cards ───
  function renderFeedCards(data, landmark) {
    const rc = data.risk_class || "Medium";
    const blockId = data.block_id || "—";
    const surfVal = data.surface_temp_celsius != null ? Number(data.surface_temp_celsius).toFixed(1) : "50.4";
    const surfTemp = `${surfVal}°C`;

    // 1. Place Information
    const placeName = landmark ? landmark.name : "Madurai Urban Sector";
    const placeSub = landmark ? `${landmark.sub} · Sector ${blockId}` : `Sector ${blockId}`;

    const elemPlaceName = document.getElementById("detail-place-name");
    const elemPlaceSub = document.getElementById("detail-place-sub");
    if (elemPlaceName) elemPlaceName.textContent = placeName;
    if (elemPlaceSub) elemPlaceSub.textContent = placeSub;

    // 2. Weather & Condition Title
    const airVal = data.realtime_weather?.temperature_celsius ?? data.ambient_temp_celsius ?? liveAirTemp;
    const airText = `${Number(airVal).toFixed(1)}°`;
    const feelsVal = data.realtime_weather?.wbgt_celsius ?? data.forecast_trajectory?.[0]?.local_wbgt ?? liveFeelsTemp;
    const feelsText = `${Number(feelsVal).toFixed(1)}°C`;

    const conditionTitlesEn = {
      Critical: "Critical Heat Alert",
      High: "Elevated Heat Stress",
      Medium: "Moderate Thermal Load",
      Low: "Safe & Comfortable",
    };
    const conditionTitlesTa = {
      Critical: "தீவிர வெப்ப அபாய எச்சரிக்கை",
      High: "அதிக வெப்ப அபாயம்",
      Medium: "மிதமான வெப்ப நிலை",
      Low: "பாதுகாப்பான சூழல்",
    };

    const elemAirTemp = document.getElementById("detail-air-temp");
    const elemCondTitle = document.getElementById("detail-weather-condition");
    const elemFeelsTemp = document.getElementById("detail-feels-temp");
    const explainerAirVal = document.getElementById("explainer-air-val");

    if (elemAirTemp) elemAirTemp.textContent = airText;
    if (elemCondTitle) elemCondTitle.textContent = currentLang === "TA" ? conditionTitlesTa[rc] : conditionTitlesEn[rc];
    if (elemFeelsTemp) {
      elemFeelsTemp.textContent = currentLang === "TA" ? `உடல் உணரும் வெப்பம்: ${feelsText} (WBGT)` : `Feels like ${feelsText} (WBGT)`;
    }
    if (explainerAirVal) explainerAirVal.textContent = `${Number(airVal).toFixed(1)}°C`;

    // 3. 2x3 Metric Pills
    const pillAir = document.getElementById("pill-air-temp");
    const pillSurf = document.getElementById("pill-surf-temp");
    const pillHumidity = document.getElementById("pill-humidity");
    const pillWind = document.getElementById("pill-wind");
    const pillDanger = document.getElementById("pill-danger-window");
    const pillShelter = document.getElementById("pill-shelter-dist");

    if (pillAir) pillAir.textContent = `${Number(airVal).toFixed(1)}°C`;
    if (pillSurf) {
      pillSurf.textContent = surfTemp;
      pillSurf.style.color = RISK_COLORS[rc] || "#dc2626";
    }
    if (pillHumidity) {
      const humVal = data.realtime_weather?.relative_humidity_pct != null ? Math.round(data.realtime_weather.relative_humidity_pct) : liveHumidity;
      pillHumidity.textContent = `${humVal}% RH`;
    }
    if (pillWind) {
      const windVal = data.realtime_weather?.wind_speed_ms != null ? Number(data.realtime_weather.wind_speed_ms).toFixed(1) : liveWindSpeed.toFixed(1);
      pillWind.textContent = `${windVal} m/s`;
    }

    const heatHealth = data.heat_health || {};
    const dangerWindow = heatHealth.peak_stress_window ? heatHealth.peak_stress_window.split("(")[0].trim() : "11 AM – 3:30 PM";
    if (pillDanger) pillDanger.textContent = dangerWindow;

    const distG = data.dist_green_m != null ? Math.round(data.dist_green_m) : 150;
    const distW = data.dist_water_m != null ? Math.round(data.dist_water_m) : 280;
    if (pillShelter) pillShelter.textContent = `${distG}m Shaded`;

    // 4. Update Status Pill
    computeAndRenderLiveDangerStatus();

    // 5. Nearest Cool Spots
    const elemParkDist = document.getElementById("spot-park-dist");
    const elemWaterDist = document.getElementById("spot-water-dist");
    const elemParkName = document.getElementById("spot-park-name");
    const elemWaterName = document.getElementById("spot-water-name");

    if (elemParkDist) elemParkDist.textContent = `${distG}m walking`;
    if (elemWaterDist) elemWaterDist.textContent = `${distW}m walking`;

    if (elemParkName) {
      if (currentLang === "TA") {
        elemParkName.textContent = distG < 100 ? "அடர்ந்த மர நிழல் பாதை" : "பொது பூங்கா மற்றும் நிழல் மையம்";
      } else {
        elemParkName.textContent = distG < 100 ? "Dense Tree Canopy & Shade" : "Public Park & Shaded Green Space";
      }
    }
    if (elemWaterName) {
      if (currentLang === "TA") {
        elemWaterName.textContent = distW < 200 ? "வைகை ஆற்றங்கரை / குடிநீர் குழாய்" : "மாநகராட்சி சுத்திகரிக்கப்பட்ட குடிநீர் மையம்";
      } else {
        elemWaterName.textContent = distW < 200 ? "Vaigai Riverfront / Water Tap" : "Municipal Clean Water Refill Tap";
      }
    }

    // 6. Dynamic Microclimate Physical Diagnosis & Advisory (rules.py)
    const explainerDesc = document.getElementById("explainer-desc");
    if (explainerDesc && data.thermal_summary) {
      explainerDesc.textContent = data.thermal_summary;
    }

    if (data.automated_advisory) {
      const actEl = document.getElementById("action-item-hydrate");
      if (actEl) {
        const actionText = currentLang === "TA"
          ? (data.automated_advisory.citizen_action_ta || data.automated_advisory.citizen_action)
          : data.automated_advisory.citizen_action;
        if (actionText) {
          actEl.innerHTML = `<strong>${currentLang === "TA" ? "நேரடி ஆலோசனை:" : "Sector Guidance:"}</strong> ${actionText}`;
        }
      }
    }
  }

  // ─── Render Hourly Diurnal Spline Chart & 9-Tile Scrubber ───
  function renderDiurnalChartAndScrubber(data) {
    const baseAir = data?.realtime_weather?.temperature_celsius ?? liveAirTemp;
    const currentHour = new Date().getHours();
    let hourlyData = [];

    if (liveHourlyForecast && liveHourlyForecast.length >= 6) {
      hourlyData = liveHourlyForecast.slice(0, 9).map((h, idx) => {
        const hStr = h.hour_str ? h.hour_str.toLowerCase() : `${h.hour_num}:00`;
        const isCur = idx === 0 || h.hour_num === currentHour;
        let riskLabel = "Safe";
        if (h.risk_tier === "Critical") riskLabel = "Severe";
        else if (h.risk_tier === "High") riskLabel = "High";
        else if (h.risk_tier === "Medium") riskLabel = "Moderate";
        else riskLabel = "Safe";

        return {
          time: hStr,
          hourNum: h.hour_num,
          temp: Math.round(Number(h.temperature_celsius) * 10) / 10,
          feels: Math.round(Number(h.apparent_temperature_celsius || h.temperature_celsius) * 10) / 10,
          wbgt: Math.round(Number(h.wbgt_celsius || h.temperature_celsius) * 10) / 10,
          isDanger: Boolean(h.is_danger),
          risk: riskLabel,
          risk_tier: h.risk_tier,
          condition: h.condition || "Clear sky",
          weather_code: h.weather_code || 0,
          isCurrent: isCur,
        };
      });
    } else {
      // Fallback 9-point baseline if live forecast is loading
      const hours = [
        { time: "10 a.m.", hourNum: 10, offset: -3.8, isDanger: false, risk: "Safe" },
        { time: "11 a.m.", hourNum: 11, offset: -1.3, isDanger: true, risk: "Moderate" },
        { time: "12 p.m.", hourNum: 12, offset: +0.4, isDanger: true, risk: "High" },
        { time: "1 p.m.",  hourNum: 13, offset: +1.5, isDanger: true, risk: "Severe" },
        { time: "2 p.m.",  hourNum: 14, offset: +1.8, isDanger: true, risk: "Severe" },
        { time: "3 p.m.",  hourNum: 15, offset: +0.7, isDanger: true, risk: "High" },
        { time: "4 p.m.",  hourNum: 16, offset: -1.8, isDanger: false, risk: "Moderate" },
        { time: "5 p.m.",  hourNum: 17, offset: -4.0, isDanger: false, risk: "Safe" },
        { time: "6 p.m.",  hourNum: 18, offset: -6.3, isDanger: false, risk: "Safe" },
      ];
      hourlyData = hours.map((h) => ({
        ...h,
        temp: Math.round((baseAir + h.offset) * 10) / 10,
        isCurrent: currentHour === h.hourNum,
      }));
    }

    // 1. Render Diurnal SVG Chart
    renderSplineSvg(hourlyData);

    // 2. Render 9-Tile Scrubber
    renderHourlyScrubber(hourlyData);
  }

  function renderSplineSvg(dataPoints) {
    const container = document.getElementById("ow-spline-container");
    if (!container) return;

    const width = 600;
    const height = 95;
    const padX = 35;
    const padY = 22;

    const temps = dataPoints.map((d) => d.temp);
    const minT = Math.min(...temps) - 1.5;
    const maxT = Math.max(...temps) + 1.5;

    const coords = dataPoints.map((d, i) => {
      const x = padX + (i / (dataPoints.length - 1)) * (width - 2 * padX);
      const y = height - padY - ((d.temp - minT) / (maxT - minT)) * (height - 2 * padY);
      return { x, y, ...d };
    });

    // Build SVG path with cubic bezier spline
    let pathD = `M ${coords[0].x} ${coords[0].y}`;
    for (let i = 0; i < coords.length - 1; i++) {
      const curr = coords[i];
      const next = coords[i + 1];
      const mx = (curr.x + next.x) / 2;
      pathD += ` C ${mx} ${curr.y}, ${mx} ${next.y}, ${next.x} ${next.y}`;
    }

    // Shaded area under path
    const areaD = `${pathD} L ${coords[coords.length - 1].x} ${height - 6} L ${coords[0].x} ${height - 6} Z`;

    // Coordinates for Danger Band dynamically calculated from isDanger points
    let dangerBandSvg = "";
    const dangerIndices = coords.map((c, i) => c.isDanger ? i : -1).filter((i) => i >= 0);
    if (dangerIndices.length > 0) {
      const minIdx = Math.min(...dangerIndices);
      const maxIdx = Math.max(...dangerIndices);
      const stepX = (width - 2 * padX) / Math.max(1, coords.length - 1);
      const leftX = Math.max(padX, coords[minIdx].x - stepX * 0.4);
      const rightX = Math.min(width - padX, coords[maxIdx].x + stepX * 0.4);
      const bandW = Math.max(16, rightX - leftX);

      dangerBandSvg = `
        <!-- Danger Window Shaded Band -->
        <rect x="${leftX}" y="4" width="${bandW}" height="${height - 10}" fill="url(#dangerBandGradient)" rx="4"/>
        <line x1="${leftX}" y1="4" x2="${leftX}" y2="${height - 6}" stroke="#fca5a5" stroke-width="1.2" stroke-dasharray="3 3"/>
        <line x1="${rightX}" y1="4" x2="${rightX}" y2="${height - 6}" stroke="#fca5a5" stroke-width="1.2" stroke-dasharray="3 3"/>
      `;
    }

    const svg = `
      <svg viewBox="0 0 ${width} ${height}" class="ow-chart-svg" preserveAspectRatio="none" style="overflow: visible;">
        <defs>
          <linearGradient id="curveGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#ea580c" stop-opacity="0.30"/>
            <stop offset="100%" stop-color="#ea580c" stop-opacity="0.0"/>
          </linearGradient>
          <linearGradient id="dangerBandGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#fee2e2" stop-opacity="0.75"/>
            <stop offset="100%" stop-color="#fee2e2" stop-opacity="0.25"/>
          </linearGradient>
        </defs>

        ${dangerBandSvg}

        <!-- Baseline -->
        <line x1="${padX}" y1="${height - 6}" x2="${width - padX}" y2="${height - 6}" stroke="#f3e8d9" stroke-width="1.5"/>

        <!-- Spline Area Fill -->
        <path d="${areaD}" fill="url(#curveGradient)" />

        <!-- Spline Stroke -->
        <path d="${pathD}" fill="none" stroke="#ea580c" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>

        <!-- Nodes and Labels -->
        ${coords
          .map((pt) => `
          <circle cx="${pt.x}" cy="${pt.y}" r="${pt.isCurrent ? 5.5 : 3.5}" 
                  fill="${pt.isCurrent ? '#dc2626' : (pt.isDanger ? '#ea580c' : '#ffffff')}" 
                  stroke="${pt.isCurrent ? '#ffffff' : '#ea580c'}" 
                  stroke-width="${pt.isCurrent ? 2.5 : 1.8}"/>
          <text x="${pt.x}" y="${pt.y - 7}" font-family="var(--font-mono)" font-size="10.5" font-weight="700" 
                fill="${pt.isDanger ? '#991b1b' : '#334155'}" text-anchor="middle">
            ${Math.round(pt.temp)}&deg;
          </text>
        `)
          .join("")}
      </svg>
    `;

    container.innerHTML = svg;
  }

  function renderHourlyScrubber(dataPoints) {
    const scrubber = document.getElementById("ow-hourly-scrubber");
    if (!scrubber) return;

    scrubber.innerHTML = dataPoints
      .map((d) => {
        let weatherIcon = "";
        let riskColor = "#16a34a";

        if (d.risk === "Severe" || d.risk_tier === "Critical") {
          riskColor = "#dc2626";
          weatherIcon = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="4"/>
              <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
            </svg>
          `;
        } else if (d.risk === "High" || d.risk_tier === "High") {
          riskColor = "#ea580c";
          weatherIcon = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ea580c" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="4"/>
              <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2"/>
            </svg>
          `;
        } else if (d.risk === "Moderate" || d.risk_tier === "Medium") {
          riskColor = "#d97706";
          weatherIcon = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>
            </svg>
          `;
        } else {
          riskColor = "#16a34a";
          weatherIcon = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="5"/>
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2"/>
            </svg>
          `;
        }

        const riskLabelsTa = {
          Severe: "தீவிரம்",
          Critical: "தீவிரம்",
          High: "அதிகம்",
          Moderate: "மிதம்",
          Medium: "மிதம்",
          Safe: "பாதுகாப்பு",
          Low: "பாதுகாப்பு",
        };

        const displayRisk = currentLang === "TA" ? (riskLabelsTa[d.risk_tier] || riskLabelsTa[d.risk] || d.risk) : d.risk;

        return `
          <div class="ow-hourly-item ${d.isCurrent ? "active-now" : ""}">
            <span class="ow-hour-time">${d.time}</span>
            <div class="ow-hour-icon">${weatherIcon}</div>
            <span class="ow-hour-risk" style="color: ${riskColor};">${displayRisk}</span>
            <span class="ow-hour-temp">${Math.round(d.temp)}&deg;</span>
          </div>
        `;
      })
      .join("");
  }

  // ─── Compute Live Danger Status (IST Time) ───
  function computeAndRenderLiveDangerStatus() {
    const badge = document.getElementById("danger-live-status");
    if (!badge) return;

    const now = new Date();
    const currentHour = now.getHours() + now.getMinutes() / 60;

    if (currentHour >= 11.0 && currentHour <= 15.5) {
      badge.textContent = currentLang === "TA" ? "தீவிர வெயில் நேரம்" : "In Peak Sun Window";
      badge.style.background = "#fee2e2";
      badge.style.color = "#991b1b";
    } else if (currentHour < 11.0 && currentHour >= 8.0) {
      badge.textContent = currentLang === "TA" ? "வெயில் அதிகரிக்கக்கூடும்" : "Approaching Peak Heat";
      badge.style.background = "#fef9c3";
      badge.style.color = "#854d0e";
    } else {
      badge.textContent = currentLang === "TA" ? "பாதுகாப்பான நேரம்" : "Safe Evening / Morning";
      badge.style.background = "#dcfce7";
      badge.style.color = "#166534";
    }
  }

  // ─── Language Translation Toggle ───
  function toggleLanguage() {
    currentLang = currentLang === "EN" ? "TA" : "EN";
    const btnText = document.getElementById("lang-toggle-text");
    if (btnText) btnText.textContent = currentLang === "EN" ? "தமிழ்" : "English";

    const translations = {
      EN: {
        quickExplore: "Quick Areas:",
        searchPlaceholder: "Search neighborhood or landmark...",
        locateLabel: "Locate Me",
        refreshBtn: "Sync",
        labelPillAir: "Outdoor Air",
        labelPillRoof: "Roof & Ground",
        labelPillHumidity: "Humidity",
        labelPillWind: "Wind Speed",
        labelPillDanger: "Danger Window",
        labelPillShelter: "Cool Shelter",
        explainerTitle: "Why does Roof & Ground heat reach ~50°C?",
        explainerDesc: "Sunlight intensely superheats unshaded tin roofs and asphalt roads. The actual outdoor air you breathe in the shade is ",
        forecastTitle: "Hourly Heat Forecast & Danger Window",
        chartLegendLeft: "Diurnal Heat Stress Curve (°C)",
        chartLegendRight: "Shaded Danger Band: 11:00 AM – 3:30 PM",
        mapTitle: "Madurai 50m Microclimate Heat Vulnerability Map",
        mapSub: "Tap any 50m sector to inspect radiant surface heat, shade deficits, and localized safety metrics.",
        timelineTitle: "Peak Sun Exposure Timeline",
        legendSafe: "Safe (≤45)",
        legendMod: "Moderate (46-70)",
        legendHigh: "High (71-85)",
        legendCrit: "Critical (>85)",
        mapLocate: "My Location",
        healthActions: "Health & Protection Actions",
        hydrate: "<strong>Hydrate actively:</strong> Drink ORS or water every 45–60 minutes, even if you do not feel thirsty.",
        shade: "<strong>Use shaded corridors:</strong> Avoid direct asphalt streets and tin-roof walkways during midday sun (11 AM – 3:30 PM).",
        ventilate: "<strong>Flush interior heat:</strong> Open opposing windows for cross-breeze to remove radiated tin roof heat.",
        vulnerable: "<strong>Protect vulnerable residents:</strong> Keep elders, infants, and pregnant family members in cool, ventilated rooms.",
        coolSpots: "Nearest Cool Spots & Water Points",
      },
      TA: {
        quickExplore: "விரைவு பகுதிகள்:",
        searchPlaceholder: "பகுதி அல்லது இடத்தை தேடுங்கள்...",
        locateLabel: "என் இடம்",
        refreshBtn: "புதுப்பி",
        labelPillAir: "வெளிப்புற நிழல் காற்று",
        labelPillRoof: "தகர கூரை & தரை வெப்பம்",
        labelPillHumidity: "ஈரப்பதம்",
        labelPillWind: "காற்றின் வேகம்",
        labelPillDanger: "உச்சி வெயில் ஆபத்து நேரம்",
        labelPillShelter: "குளிர் நிழல் மையம்",
        explainerTitle: "கூரை மற்றும் தரை ஏன் ~50°C ஐ எட்டுகிறது?",
        explainerDesc: "நேரடி சூரிய கதிர்வீச்சு தகர கூரைகள் மற்றும் தார் சாலைகளை மிகக் கடுமையாக சூடாக்குகிறது. நீங்கள் சுவாசிக்கும் நிழல் காற்று குளிர்ந்தது: ",
        forecastTitle: "மணிநேர வெப்ப முன்னறிவிப்பு மற்றும் ஆபத்து நேரம்",
        chartLegendLeft: "தினசரி வெப்ப அழுத்த வளைவு (°C)",
        chartLegendRight: "தீவிர வெயில் காலம்: காலை 11:00 – மாலை 3:30",
        mapTitle: "மதுரை 50மீ நுண்ணிய வெப்ப வரைபடம்",
        mapSub: "கூரை வெப்பம், நிழல் குறைபாடு மற்றும் பாதுகாப்பு விவரங்களைக் காண எந்த பகுதியையும் தொடவும்.",
        timelineTitle: "சூரிய வெப்ப நேரவரிசை",
        legendSafe: "பாதுகாப்பானது (≤45)",
        legendMod: "மிதமானது (46-70)",
        legendHigh: "அதிகம் (71-85)",
        legendCrit: "தீவிரமானது (>85)",
        mapLocate: "என் இடம்",
        healthActions: "உடல் நலப் பாதுகாப்பு ஆலோசனைகள்",
        hydrate: "<strong>அடிக்கடி தண்ணீர் குடியுங்கள்:</strong> தாகம் இல்லாவிட்டாலும் ஒவ்வொரு 45 நிமிடத்திற்கும் நீர் அல்லது ORS அருந்தவும்.",
        shade: "<strong>நிழலான பாதைகளை பயன்படுத்துங்கள்:</strong> நண்பகல் வெயிலில் (11 மு.ப - 3:30 பி.ப) தார் சாலைகளில் செல்வதை தவிர்க்கவும்.",
        ventilate: "<strong>வீட்டில் காற்றோட்டம் வையுங்கள்:</strong> தகர கூரையின் வெப்பத்தை வெளியேற்ற எதிரெதிர் ஜன்னல்களை திறந்து வைக்கவும்.",
        vulnerable: "<strong>முதியவர்கள் மற்றும் குழந்தைகள்:</strong> குழந்தைகளையும் முதியவர்களையும் காற்றோட்டமான அறைகளில் வைத்திருக்கவும்.",
        coolSpots: "அருகிலுள்ள நிழல் மற்றும் குடிநீர் மையங்கள்",
      },
    };

    const t = translations[currentLang];

    setElemText("label-quick-explore", t.quickExplore);
    const searchInput = document.getElementById("search-input");
    if (searchInput) searchInput.placeholder = t.searchPlaceholder;

    setElemText("btn-locate-label", t.locateLabel);
    setElemText("label-weather-refresh", t.refreshBtn);
    setElemHtml("label-pill-air", `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2"/></svg> ${t.labelPillAir}`);
    setElemHtml("label-pill-roof", `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M8 3v4M12 3v4M16 3v4M4 14a8 8 0 0 0 16 0M3 21h18"/></svg> ${t.labelPillRoof}`);
    setElemHtml("label-pill-humidity", `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/></svg> ${t.labelPillHumidity}`);
    setElemHtml("label-pill-wind", `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2M9.6 4.6A2 2 0 1 1 11 8H2M12.6 19.4A2 2 0 1 0 14 16H2"/></svg> ${t.labelPillWind}`);
    setElemHtml("label-pill-danger", `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg> ${t.labelPillDanger}`);
    setElemHtml("label-pill-shelter", `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 19v3M12 10a5 5 0 0 0-5 5c0 2 2 4 5 4s5-2 5-4a5 5 0 0 0-5-5zM12 2a4 4 0 0 0-4 4c0 1.5 1 3 2 3.5M12 2a4 4 0 0 1 4 4c0 1.5-1 3-2 3.5"/></svg> ${t.labelPillShelter}`);

    setElemText("explainer-title", t.explainerTitle);
    const airVal = document.getElementById("explainer-air-val")?.textContent || "35.8°C";
    const descElem = document.getElementById("explainer-desc");
    if (descElem) descElem.innerHTML = `${t.explainerDesc} <strong id="explainer-air-val">${airVal}</strong>.`;

    setElemText("label-forecast-title", t.forecastTitle);
    setElemText("chart-legend-left", t.chartLegendLeft);
    setElemText("chart-legend-right", t.chartLegendRight);
    setElemText("label-map-title", t.mapTitle);
    setElemText("label-map-sub", t.mapSub);
    setElemText("widget-timeline-title", t.timelineTitle);
    setElemText("legend-label-safe", t.legendSafe);
    setElemText("legend-label-mod", t.legendMod);
    setElemText("legend-label-high", t.legendHigh);
    setElemText("legend-label-crit", t.legendCrit);
    setElemText("label-map-locate", t.mapLocate);
    setElemText("label-health-actions", t.healthActions);
    setElemHtml("action-item-hydrate", t.hydrate);
    setElemHtml("action-item-shade", t.shade);
    setElemHtml("action-item-ventilate", t.ventilate);
    setElemHtml("action-item-vulnerable", t.vulnerable);
    setElemText("label-cool-spots", t.coolSpots);

    if (currentBlockData && currentActiveLandmark) {
      renderFeedCards(currentBlockData, currentActiveLandmark);
      renderDiurnalChartAndScrubber(currentBlockData);
    }
  }

  function setElemText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }
  function setElemHtml(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
  }

  // ─── Event Listeners ───
  function initEventListeners() {
    // Search input
    const searchInput = document.getElementById("search-input");
    const searchBtn = document.getElementById("search-btn");

    if (searchInput) {
      searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          executeSearch(searchInput.value);
        }
      });
    }

    if (searchBtn && searchInput) {
      searchBtn.addEventListener("click", () => {
        executeSearch(searchInput.value);
      });
    }

    // Weather refresh button
    const btnRefresh = document.getElementById("btn-weather-refresh");
    if (btnRefresh) {
      btnRefresh.addEventListener("click", () => {
        fetchWeather(true);
      });
    }

    // Locate Me buttons
    const btnLocateTop = document.getElementById("btn-top-locate");
    if (btnLocateTop) btnLocateTop.addEventListener("click", onLocateMe);

    const btnMapLocate = document.getElementById("btn-my-location");
    if (btnMapLocate) btnMapLocate.addEventListener("click", onLocateMe);

    // Reset view
    const btnReset = document.getElementById("btn-reset-view");
    if (btnReset) {
      btnReset.addEventListener("click", () => {
        map.setView(CENTER, DEFAULT_ZOOM);
      });
    }

    // Basemap toggle
    const btnDefault = document.getElementById("btn-basemap-default");
    const btnSatellite = document.getElementById("btn-basemap-satellite");
    if (btnDefault) btnDefault.addEventListener("click", () => setBasemap("default"));
    if (btnSatellite) btnSatellite.addEventListener("click", () => setBasemap("satellite"));

    // Language toggle
    const btnLang = document.getElementById("btn-lang-toggle");
    if (btnLang) btnLang.addEventListener("click", toggleLanguage);
  }
})();
