/**
 * ThermalGuard — Citizen Heat Safety Portal (Madurai)
 * Curated, Actionable Hyperlocal Heat Intelligence and Responsive Split View Engine.
 * 100% Zero-Emoji · High Contrast · Accessible · Apple Weather & Windy Ergonomics.
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
  let currentActiveBlockId = null;
  let currentActiveLandmark = null;
  let currentBlockData = null;

  let liveAirTemp = null;
  let liveFeelsTemp = null;
  let currentLang = "EN"; // "EN" or "TA"
  let isViewingMapMobile = false;

  // ─── Initialization ───
  document.addEventListener("DOMContentLoaded", init);

  function init() {
    initMap();
    initBasemaps();
    renderNeighborhoodChips();
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

    // Zoom control in bottom right
    L.control.zoom({ position: "bottomright" }).addTo(map);
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

  // ─── Render Neighborhood Quick-Chips ───
  function renderNeighborhoodChips() {
    const container = document.getElementById("neighborhood-chips");
    if (!container) return;

    container.innerHTML = MADURAI_LANDMARKS.slice(0, 8)
      .map(
        (lm, idx) => `
        <button class="neighborhood-chip ${idx === 0 ? "active" : ""}" data-idx="${idx}" title="${lm.name}">
          ${lm.tag}
        </button>
      `
      )
      .join("");

    container.querySelectorAll(".neighborhood-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        container.querySelectorAll(".neighborhood-chip").forEach((c) => c.classList.remove("active"));
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

  // ─── Load Dataset & Initial View ───
  async function loadBlocks() {
    setFeedLoading(true);
    try {
      // 1. Fetch live Open-Meteo weather
      try {
        const fRes = await fetch("/api/forecast/days");
        if (fRes.ok) {
          const fData = await fRes.json();
          if (fData.current && fData.current.temperature_celsius != null) {
            liveAirTemp = Number(fData.current.temperature_celsius).toFixed(1);
            liveFeelsTemp = Number(fData.current.wbgt_celsius || fData.current.apparent_temperature_celsius).toFixed(1);
            const avgPill = document.getElementById("topbar-avg-temp");
            if (avgPill) {
              avgPill.textContent = `Live Air: ${liveAirTemp}°C · Feels ${liveFeelsTemp}°C`;
            }
          }
        }
      } catch (fErr) {
        console.warn("Could not fetch live forecast:", fErr);
      }

      // 2. Fetch GeoJSON sectors
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
    } finally {
      setFeedLoading(false);
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
            const airStr = liveAirTemp ? `${liveAirTemp}°C` : "35.8°C";
            return `<strong>Sector ${p.block_id}</strong><br/>${p.risk_class} Risk &middot; Air: ${airStr} &bull; Roof: ${p.surface_temp_celsius}&deg;C`;
          },
          { className: "custom-map-tooltip", sticky: true, opacity: 0.95 }
        );

        layer.on("click", function () {
          highlightBlock(feature);
          const centroid = getPolygonCentroid(feature.geometry);
          const landmark = resolveNeighborhood(centroid[0], centroid[1]);
          fetchAndShowBlock(p.block_id, landmark);

          // If on mobile and viewing map, switch back or update
          if (isViewingMapMobile) {
            showMobileNotification(`Selected ${landmark.name}`);
          }
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
        fillColor: "#38bdf8",
        fillOpacity: 0.35,
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
    const btn = document.getElementById("btn-feed-locate");
    const mapBtn = document.getElementById("btn-my-location");
    if (btn) { btn.style.opacity = "0.7"; btn.style.pointerEvents = "none"; }
    if (mapBtn) { mapBtn.style.opacity = "0.7"; mapBtn.style.pointerEvents = "none"; }

    // Check HTML5 Geolocation
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = pos.coords.latitude;
          const lon = pos.coords.longitude;
          // Verify if inside Madurai bounding box
          if (lat >= 9.85 && lat <= 10.0 && lon >= 78.0 && lon <= 78.23) {
            handleResolvedLocation(lat, lon);
          } else {
            // Outside Madurai, fallback to Pasumalai
            handleResolvedLocation(HARDCODED_LAT, HARDCODED_LON);
          }
          resetLocateButtons(btn, mapBtn);
        },
        () => {
          // Geolocation denied or unavailable -> fallback to Pasumalai
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
    setFeedLoading(true);

    try {
      const res = await fetch(`/api/blocks/${blockId}`);
      if (!res.ok) throw new Error("Block not found");
      const data = await res.json();
      currentBlockData = data;
      renderFeedCards(data, landmark);
    } catch (err) {
      console.error("Could not fetch block data:", err);
    } finally {
      setFeedLoading(false);
    }
  }

  function setFeedLoading(isLoading) {
    const loadingElem = document.getElementById("feed-loading");
    const heroCard = document.getElementById("card-hero");
    if (loadingElem) loadingElem.style.display = isLoading ? "flex" : "none";
    if (heroCard) heroCard.style.opacity = isLoading ? "0.4" : "1";
  }

  // ─── Render Curated Citizen Cards ───
  function renderFeedCards(data, landmark) {
    const rc = data.risk_class || "Medium";
    const blockId = data.block_id || "—";
    const surfTemp = data.surface_temp_display || `${data.surface_temp_celsius || "--"}°C`;

    // 1. Place Information
    const placeName = landmark ? landmark.name : "Madurai Urban Sector";
    const placeSub = landmark ? `${landmark.sub} · Sector ${blockId}` : `Sector ${blockId}`;

    const elemPlaceName = document.getElementById("detail-place-name");
    const elemPlaceSub = document.getElementById("detail-place-sub");
    if (elemPlaceName) elemPlaceName.textContent = placeName;
    if (elemPlaceSub) elemPlaceSub.textContent = placeSub;

    // 2. Risk Alert Status Banner
    const elemRiskBadge = document.getElementById("detail-risk-badge");
    const elemAlertIcon = document.getElementById("detail-alert-icon");
    const elemAlertText = document.getElementById("detail-alert-text");
    const elemHeatLevelTag = document.getElementById("detail-heat-level-tag");

    const alertLabelsEn = {
      Critical: "CRITICAL HEAT ALERT",
      High: "ELEVATED HEAT RISK",
      Medium: "MODERATE HEAT LEVEL",
      Low: "SAFE & COMFORTABLE",
    };
    const alertLabelsTa = {
      Critical: "தீவிர வெப்ப அபாய எச்சரிக்கை",
      High: "அதிக வெப்ப அபாயம்",
      Medium: "மிதமான வெப்ப நிலை",
      Low: "பாதுகாப்பான சூழல்",
    };

    const alertIcons = {
      Critical: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
      High: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
      Medium: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
      Low: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
    };

    if (elemRiskBadge) {
      elemRiskBadge.className = `citizen-alert-banner risk-${rc.toLowerCase()}`;
    }
    if (elemAlertIcon) {
      elemAlertIcon.innerHTML = alertIcons[rc] || alertIcons.Medium;
    }
    if (elemAlertText) {
      elemAlertText.textContent = currentLang === "TA" ? alertLabelsTa[rc] : alertLabelsEn[rc];
    }
    if (elemHeatLevelTag) {
      elemHeatLevelTag.textContent = rc.toUpperCase();
    }

    // 3. Three Glanceable Temperatures
    const elemAirTemp = document.getElementById("detail-air-temp");
    const elemSurfTemp = document.getElementById("detail-surface-temp");
    const elemFeelsTemp = document.getElementById("detail-feels-temp");
    const explainerAirVal = document.getElementById("explainer-air-val");

    const airVal = data.realtime_weather?.temperature_celsius ?? data.ambient_temp_celsius ?? (liveAirTemp ? Number(liveAirTemp) : 35.8);
    const airText = `${Number(airVal).toFixed(1)}°C`;

    const feelsVal = data.realtime_weather?.wbgt_celsius ?? data.forecast_trajectory?.[0]?.local_wbgt ?? (liveFeelsTemp ? Number(liveFeelsTemp) : 32.0);
    const feelsText = `${Number(feelsVal).toFixed(1)}°C`;

    if (elemAirTemp) elemAirTemp.textContent = airText;
    if (elemSurfTemp) {
      elemSurfTemp.textContent = surfTemp;
      elemSurfTemp.style.color = RISK_COLORS[rc] || "#dc2626";
    }
    if (elemFeelsTemp) elemFeelsTemp.textContent = feelsText;
    if (explainerAirVal) explainerAirVal.textContent = airText;

    // 4. Peak Sun Danger Hours & Dynamic Live Status
    const heatHealth = data.heat_health || {};
    const dangerWindow = heatHealth.peak_stress_window ? heatHealth.peak_stress_window.split("(")[0].trim() : "11:00 AM – 3:30 PM";
    const elemDangerHours = document.getElementById("detail-danger-hours");
    if (elemDangerHours) elemDangerHours.textContent = dangerWindow;

    // Compute live status based on local time
    computeAndRenderLiveDangerStatus();

    // 5. Nearest Cool Spots & Water Points
    const distG = data.dist_green_m != null ? Math.round(data.dist_green_m) : 150;
    const distW = data.dist_water_m != null ? Math.round(data.dist_water_m) : 280;

    const elemParkDist = document.getElementById("spot-park-dist");
    const elemWaterDist = document.getElementById("spot-water-dist");
    const elemParkName = document.getElementById("spot-park-name");
    const elemWaterName = document.getElementById("spot-water-name");

    if (elemParkDist) elemParkDist.textContent = `${distG}m walking distance`;
    if (elemWaterDist) elemWaterDist.textContent = `${distW}m walking distance`;

    if (elemParkName) {
      elemParkName.textContent = distG < 100 ? "Dense Tree Canopy & Roadside Shade" : "Public Park & Shaded Green Space";
    }
    if (elemWaterName) {
      elemWaterName.textContent = distW < 200 ? "Vaigai Riverfront / Public Water Tap" : "Municipal Clean Water Refill Station";
    }

    // 6. 5-Day Outlook Strip (Apple Weather style)
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
            const wbgtVal = dayItem.local_wbgt != null ? `${dayItem.local_wbgt}°` : "--";

            let weatherIcon = "";
            if (tier === "Critical") {
              weatherIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>`;
            } else if (tier === "High") {
              weatherIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ea580c" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2"/></svg>`;
            } else if (tier === "Medium") {
              weatherIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></svg>`;
            } else {
              weatherIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2"/></svg>`;
            }

            return `
              <div class="forecast-pill ${idx === 0 ? "active-today" : ""}">
                <span class="forecast-pill-day">${idx === 0 ? (currentLang === "TA" ? "இன்று" : "Today") : `D${dayItem.day}`}</span>
                <span class="forecast-pill-icon">${weatherIcon}</span>
                <span class="forecast-pill-wbgt">${wbgtVal}</span>
                <span class="forecast-pill-tag ${tagCls}">${tier}</span>
              </div>
            `;
          })
          .join("");
      }
    }
  }

  // ─── Compute Live Danger Status (IST Time) ───
  function computeAndRenderLiveDangerStatus() {
    const badge = document.getElementById("danger-live-status");
    const hint = document.getElementById("detail-danger-hint");
    if (!badge || !hint) return;

    // Get current hour in IST
    const now = new Date();
    const currentHour = now.getHours() + now.getMinutes() / 60;

    if (currentHour >= 11.0 && currentHour <= 15.5) {
      badge.textContent = currentLang === "TA" ? "தீவிர வெயில் நேரம்" : "In Peak Sun Window";
      badge.style.background = "#fee2e2";
      badge.style.color = "#991b1b";
      hint.textContent = currentLang === "TA" 
        ? "தற்போது தீவிர சூரிய கதிர்வீச்சு உள்ளது. 3:30 மணி வரை வெயிலில் செல்வதை தவிர்க்கவும்."
        : "Direct sun exposure is dangerous now. Stay indoors or under heavy canopy until 3:30 PM.";
    } else if (currentHour < 11.0 && currentHour >= 8.0) {
      badge.textContent = currentLang === "TA" ? "வெயில் அதிகரிக்கக்கூடும்" : "Approaching Peak Heat";
      badge.style.background = "#fef9c3";
      badge.style.color = "#854d0e";
      hint.textContent = currentLang === "TA"
        ? "காலை 11:00 மணிக்குள் அவசியமான வெளிப்புற வேலைகளை முடிக்கவும்."
        : "Complete outdoor errands before 11:00 AM; pre-hydrate with water/ORS.";
    } else {
      badge.textContent = currentLang === "TA" ? "பாதுகாப்பான நேரம்" : "Safe Evening / Morning";
      badge.style.background = "#dcfce7";
      badge.style.color = "#166534";
      hint.textContent = currentLang === "TA"
        ? "சூரிய வெப்பம் குறைந்துள்ளது. இயல்பான பணிகளை தொடரலாம்."
        : "Radiant heat has cooled down. Maintain normal hydration.";
    }
  }

  // ─── Language Translation Toggle ───
  function toggleLanguage() {
    currentLang = currentLang === "EN" ? "TA" : "EN";
    const btnText = document.getElementById("lang-toggle-text");
    if (btnText) btnText.textContent = currentLang === "EN" ? "தமிழ்" : "English";

    // Text translations map
    const translations = {
      EN: {
        activeLoc: "Active Location",
        outdoorAir: "Outdoor Air",
        roofHeat: "Roof & Ground",
        feelsLike: "Feels Like",
        explainerTitle: "Why does Roof & Ground reach ~50°C?",
        explainerDesc: "Sunlight intensely superheats unshaded tin roofs and asphalt roads. The actual outdoor air you breathe in the shade is ",
        dangerHours: "Peak Sun Danger Hours",
        healthActions: "Health & Protection Actions",
        hydrate: "<strong>Drink water frequently</strong> — consume ORS or water every 45–60 minutes even if not thirsty.",
        shade: "<strong>Stay in shaded areas</strong> — avoid direct asphalt or tin-roof walkways during midday sun.",
        ventilate: "<strong>Keep interiors ventilated</strong> — open opposing windows to flush radiant metal-roof heat.",
        vulnerable: "<strong>Vulnerable care</strong> — protect children, elderly family, and pregnant women from unventilated rooms.",
        coolSpots: "Nearest Cool Spots & Water Points",
        forecastTrend: "5-Day Heat Forecast Trend",
      },
      TA: {
        activeLoc: "தேர்ந்தெடுக்கப்பட்ட பகுதி",
        outdoorAir: "வெளிப்புற நிழல் காற்று",
        roofHeat: "தகர கூரை வெப்பம்",
        feelsLike: "உடல் உணரும் வெப்பம்",
        explainerTitle: "கூரை மற்றும் தரை ஏன் ~50°C ஐ எட்டுகிறது?",
        explainerDesc: "நேரடி சூரிய கதிர்வீச்சு தகர கூரைகள் மற்றும் தார் சாலைகளை மிகக் கடுமையாக சூடாக்குகிறது. நீங்கள் சுவாசிக்கும் நிழல் காற்று குளிர்ந்தது: ",
        dangerHours: "உச்சி வெயில் ஆபத்து நேரம்",
        healthActions: "உடல் நலப் பாதுகாப்பு ஆலோசனைகள்",
        hydrate: "<strong>அடிக்கடி தண்ணீர் குடியுங்கள்</strong> — தாகம் இல்லாவிட்டாலும் ஒவ்வொரு 45 நிமிடத்திற்கும் நீர் அல்லது ORS அருந்தவும்.",
        shade: "<strong>நிழலான பாதைகளை பயன்படுத்துங்கள்</strong> — நண்பகல் வெயிலில் தகர கூரை மற்றும் தார் சாலைகளில் செல்வதை தவிர்க்கவும்.",
        ventilate: "<strong>வீட்டில் காற்றோட்டம் வையுங்கள்</strong> — தகர கூரையின் வெப்பத்தை வெளியேற்ற எதிரெதிர் ஜன்னல்களை திறந்து வைக்கவும்.",
        vulnerable: "<strong>முதியவர்கள் மற்றும் குழந்தைகள்</strong> — நண்பகல் 11 முதல் 3:30 வரை குழந்தைகளையும் முதியவர்களையும் வெயிலில் விடாதீர்கள்.",
        coolSpots: "அருகிலுள்ள நிழல் மற்றும் குடிநீர் மையங்கள்",
        forecastTrend: "5-நாள் வெப்ப முன்னறிவிப்பு",
      },
    };

    const t = translations[currentLang];

    setElemText("label-active-loc", t.activeLoc);
    setElemHtml("label-outdoor-air", `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2"/></svg> ${t.outdoorAir}`);
    setElemHtml("label-roof-heat", `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M8 3v4M12 3v4M16 3v4M4 14a8 8 0 0 0 16 0M3 21h18"/></svg> ${t.roofHeat}`);
    setElemHtml("label-feels-like", `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/></svg> ${t.feelsLike}`);
    setElemText("explainer-title", t.explainerTitle);
    
    const airVal = document.getElementById("explainer-air-val")?.textContent || "--°C";
    const descElem = document.getElementById("explainer-desc");
    if (descElem) descElem.innerHTML = `${t.explainerDesc} <strong id="explainer-air-val">${airVal}</strong>.`;

    setElemText("label-danger-hours", t.dangerHours);
    setElemText("label-health-actions", t.healthActions);
    setElemHtml("action-item-hydrate", t.hydrate);
    setElemHtml("action-item-shade", t.shade);
    setElemHtml("action-item-ventilate", t.ventilate);
    setElemHtml("action-item-vulnerable", t.vulnerable);
    setElemText("label-cool-spots", t.coolSpots);
    setElemText("label-forecast-trend", t.forecastTrend);

    if (currentBlockData && currentActiveLandmark) {
      renderFeedCards(currentBlockData, currentActiveLandmark);
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

  // ─── Mobile View Switcher ───
  function toggleMobileView() {
    isViewingMapMobile = !isViewingMapMobile;
    const splitContainer = document.querySelector(".citizen-main-split");
    const toggleText = document.getElementById("mobile-toggle-text");

    if (splitContainer) {
      if (isViewingMapMobile) {
        splitContainer.classList.add("viewing-map");
        if (toggleText) toggleText.textContent = "View Heat Advice";
        setTimeout(() => map.invalidateSize(), 150);
      } else {
        splitContainer.classList.remove("viewing-map");
        if (toggleText) toggleText.textContent = "View Heat Map";
      }
    }
  }

  function showMobileNotification(msg) {
    const bar = document.getElementById("mobile-toggle-text");
    if (bar) {
      const orig = bar.textContent;
      bar.textContent = msg;
      setTimeout(() => { bar.textContent = orig; }, 2000);
    }
  }

  // ─── Event Listeners ───
  function initEventListeners() {
    // Search input
    const searchInput = document.getElementById("search-input");
    const searchClear = document.getElementById("search-clear");

    if (searchInput) {
      searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          executeSearch(searchInput.value);
        }
      });
      searchInput.addEventListener("input", () => {
        if (searchClear) searchClear.style.display = searchInput.value ? "inline-flex" : "none";
      });
    }

    if (searchClear && searchInput) {
      searchClear.addEventListener("click", () => {
        searchInput.value = "";
        searchClear.style.display = "none";
        searchInput.focus();
      });
    }

    // Locate Me buttons
    const btnLocate = document.getElementById("btn-feed-locate");
    if (btnLocate) btnLocate.addEventListener("click", onLocateMe);

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

    // Mobile toggle
    const btnMobileToggle = document.getElementById("btn-mobile-toggle");
    if (btnMobileToggle) btnMobileToggle.addEventListener("click", toggleMobileView);
  }
})();
