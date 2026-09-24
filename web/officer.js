// ThermalGuard — Officer Command Center extensions
// Runs after app.js; reuses its global map engine (map, currentLayer, openSidebar, blockIntelligenceCache).

(function () {
  "use strict";

  const TIER_COLORS = { Low: "#1a9850", Medium: "#ffffbf", High: "#f46d43", Critical: "#d73027" };

  let forecastDays = [];
  let forecastAttrMap = null;
  let activeForecastDay = null;
  let smsTargetBlockId = null;

  function scoreColor(score) {
    if (score <= 45) return TIER_COLORS.Low;
    if (score <= 70) return TIER_COLORS.Medium;
    if (score <= 85) return TIER_COLORS.High;
    return TIER_COLORS.Critical;
  }

  // ---------- 5-Day Forecast Dropdown ----------

  function patchForecastColors() {
    // In forecast mode, hover/click/reset must use forecast colors, not HVI colors
    const original = window.getLayerFillColor;
    if (!original) return;
    window.getLayerFillColor = function (layer) {
      if (activeForecastDay && forecastAttrMap && layer && layer.feature) {
        const bid = layer.feature.properties.block_id;
        const score = forecastAttrMap[bid] !== undefined ? forecastAttrMap[bid] : 0;
        return scoreColor(score);
      }
      return original(layer);
    };
  }

  window.getActiveForecastInfo = function (blockId, props) {
    if (activeForecastDay && forecastAttrMap) {
      const score = forecastAttrMap[blockId] !== undefined ? forecastAttrMap[blockId] : 0;
      const dayData = forecastDays.find((d) => d.day === activeForecastDay) || {};
      const baseWbgt = dayData.wbgt_max || 30.0;
      const anomaly = (props && props.temp_anomaly_celsius !== undefined) ? Number(props.temp_anomaly_celsius) : 0.0;
      const localWbgt = (baseWbgt + anomaly * 0.4).toFixed(1);
      const airMax = dayData.temp_max !== undefined ? `${Number(dayData.temp_max).toFixed(1)}°C Air Max &bull; ` : "";
      let tier = "Low";
      if (score > 85) tier = "Critical";
      else if (score > 70) tier = "High";
      else if (score > 45) tier = "Medium";
      return `<strong>${blockId}</strong> &bull; Day ${activeForecastDay} &bull; ${airMax}Local WBGT: <span style="color:#f59e0b;font-weight:700;">${localWbgt}°C</span> &bull; Risk: ${score} (${tier})`;
    }
    return null;
  };

  async function initOfficer() {
    patchForecastColors();
    try {
      const res = await fetch("/api/forecast/days");
      if (!res.ok) return;
      const data = await res.json();
      forecastDays = data.days || [];

      // Update topbar with real-time live ambient temperature
      if (data.current) {
        const curr = data.current;
        if (curr.temperature_celsius !== undefined) {
          window.currentAirTemp = curr.temperature_celsius.toFixed(1);
        }
        const topbarTemp = document.getElementById("topbar-avg-temp");
        if (topbarTemp && curr.temperature_celsius !== undefined) {
          const meanLST = (window.maduraiMeanSurfaceTemp || 49.5).toFixed(1);
          topbarTemp.title = `Live Real-time Ambient Air Temperature: ${curr.temperature_celsius.toFixed(1)}°C (Feels ${curr.apparent_temperature_celsius.toFixed(1)}°C, Humidity ${curr.relative_humidity_pct}%) | Radiometric Landsat LST Mean: ${meanLST}°C`;
          topbarTemp.innerHTML = `Live: <strong>${curr.temperature_celsius.toFixed(1)}°C</strong> <span style="opacity:0.8;font-size:11px;">(Feels ${curr.apparent_temperature_celsius.toFixed(1)}°C)</span> &bull; LST Avg: ${meanLST}°C`;
        }
      }

      const menu = document.getElementById("forecast-menu");
      const btn = document.getElementById("forecast-menu-btn");
      if (!menu || !btn) return;
      menu.innerHTML = "";

      const addHeader = (text) => {
        const h = document.createElement("div");
        h.className = "menu-section-header";
        h.textContent = text;
        menu.appendChild(h);
      };
      const addItem = (label, sub, active, onClick) => {
        const item = document.createElement("div");
        item.className = "menu-layer-item" + (active ? " active" : "");
        item.innerHTML = `<div class="menu-layer-info"><span class="menu-layer-title">${label}</span><span class="menu-layer-desc">${sub}</span></div>`;
        item.addEventListener("click", onClick);
        menu.appendChild(item);
      };

      addHeader("Map View");
      addItem("HVI (Current)", "Static vulnerability index (Landsat LST)", activeForecastDay === null, () => {
        resetForecastView();
        closeForecastMenu();
      });
      addHeader("5-Day Heatwave & WBGT Forecast");
      forecastDays.forEach((d) => {
        const airText = d.temp_max !== undefined ? `${Number(d.temp_max).toFixed(1)}°C Air · ` : "";
        addItem(
          `Day ${d.day} — ${d.date}`,
          `${airText}${Number(d.wbgt_max).toFixed(1)}°C WBGT (${d.risk_tier})`,
          activeForecastDay === d.day,
          () => {
            selectForecastDay(d.day);
            closeForecastMenu();
          }
        );
      });

      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        menu.style.display = menu.style.display === "none" ? "flex" : "none";
      });
      document.addEventListener("click", (e) => {
        if (!menu.contains(e.target) && e.target !== btn) closeForecastMenu();
      });
    } catch (err) {
      console.warn("Officer forecast dropdown init failed:", err);
    }
  }

  function closeForecastMenu() {
    const menu = document.getElementById("forecast-menu");
    if (menu) menu.style.display = "none";
  }

  function setForecastLabel(text) {
    const label = document.getElementById("forecast-menu-label");
    if (label) label.textContent = text;
  }

  async function selectForecastDay(day) {
    try {
      const res = await fetch(`/api/layers/forecast_day_${day}/attributes`);
      if (!res.ok) return;
      forecastAttrMap = await res.json();
      activeForecastDay = day;
      if (typeof currentLayer !== "undefined" && currentLayer) {
        currentLayer.setStyle((feature) => {
          const bid = feature.properties.block_id;
          const score = forecastAttrMap[bid] !== undefined ? forecastAttrMap[bid] : 0;
          return { stroke: false, fillOpacity: 0.65, fillColor: scoreColor(score) };
        });
      }
      const dayData = forecastDays.find((d) => d.day === day) || {};
      const airInfo = dayData.temp_max !== undefined ? ` (${dayData.temp_max}°C Air Max)` : "";
      const nameEl = document.getElementById("active-layer-name");
      if (nameEl) nameEl.textContent = `Day ${day} WBGT Risk Forecast${airInfo}`;
      setForecastLabel(`Day ${day} Forecast`);
    } catch (err) {
      console.warn("Forecast day load failed:", err);
    }
  }

  function resetForecastView() {
    activeForecastDay = null;
    forecastAttrMap = null;
    if (typeof currentLayer !== "undefined" && currentLayer) {
      currentLayer.setStyle((feature) => ({
        stroke: false,
        fillOpacity: 0.6,
        fillColor: (typeof RISK_COLORS !== "undefined" && RISK_COLORS[feature.properties.risk_class]) || "#94a3b8",
      }));
    }
    const label = document.getElementById("active-layer-name");
    if (label) label.textContent = "Heat Vulnerability (HVI)";
    setForecastLabel("Forecast");
  }

  // ---------- Sector Inspector: SHAP Waterfall + 5-Day Sparkline + SMS ----------

  function wrapOpenSidebar() {
    const original = window.openSidebar;
    if (!original) return;
    window.openSidebar = async function (props) {
      await original(props);
      renderOfficerExtras(props.block_id);
    };
  }

  async function renderOfficerExtras(blockId) {
    const detail = document.getElementById("sidebar-detail");
    if (!detail) return;

    let data = (typeof blockIntelligenceCache !== "undefined") ? blockIntelligenceCache[blockId] : null;
    if (!data) {
      try {
        const res = await fetch(`/api/blocks/${blockId}`);
        if (res.ok) data = await res.json();
      } catch (err) {
        console.warn("Officer extras fetch failed:", err);
      }
    }
    if (!data) return;

    // Remove previous officer extras (re-selecting another sector)
    const prev = detail.querySelector("#officer-extras");
    if (prev) prev.remove();

    const wrap = document.createElement("div");
    wrap.id = "officer-extras";
    wrap.style.cssText = "margin-top: 16px; border-top: 1px solid #e2e8f0; padding-top: 12px;";

    // Real-time Station Weather Card
    if (data.realtime_weather) {
      const rw = data.realtime_weather;
      const weatherSec = document.createElement("div");
      weatherSec.style.cssText = "background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; margin-bottom: 12px;";
      weatherSec.innerHTML = `
        <div style="font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">
          🌡️ Real-Time Station Weather (Madurai)
        </div>
        <div style="display: flex; justify-content: space-between; align-items: baseline;">
          <span style="font-size: 16px; font-weight: 800; color: #0f172a;">${Number(rw.temperature_celsius).toFixed(1)}°C Air</span>
          <span style="font-size: 12px; color: #64748b;">Feels ${Number(rw.apparent_temperature_celsius).toFixed(1)}°C</span>
        </div>
        <div style="display: flex; gap: 10px; margin-top: 6px; font-size: 11px; color: #475569;">
          <span>💧 ${Number(rw.relative_humidity_pct).toFixed(0)}% RH</span>
          <span>💨 ${Number(rw.wind_speed_kmh).toFixed(1)} km/h</span>
          <span>🔥 WBGT ${Number(rw.wbgt_celsius).toFixed(1)}°C (${rw.risk_tier})</span>
        </div>
      `;
      wrap.appendChild(weatherSec);
    }

    // SHAP feature attribution waterfall
    const shapFactors = data.shap_factors || [];
    if (shapFactors.length > 0) {
      const maxAbs = Math.max(...shapFactors.map((f) => Math.abs(f.shap_value)), 0.01);
      const sec = document.createElement("div");
      sec.innerHTML = `<div style="font-size: 12px; font-weight: 700; color: #334155; margin-bottom: 6px;">
        AI Heat Drivers (SHAP) — base ${Number(data.shap_base_temp || 49.6).toFixed(1)}°C</div>`;
      shapFactors.forEach((f) => {
        const val = Number(f.shap_value);
        const row = document.createElement("div");
        row.style.cssText = "display: flex; align-items: center; gap: 6px; margin-bottom: 4px;";
        row.innerHTML = `
          <span style="flex: 1; font-size: 11px; color: #475569;">${f.name}</span>
          <div style="width: 90px; height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden;">
            <div style="width: ${Math.round((Math.abs(val) / maxAbs) * 100)}%; height: 100%; background: ${val >= 0 ? "#d73027" : "#1a9850"};"></div>
          </div>
          <span style="width: 52px; text-align: right; font-size: 11px; font-weight: 600; color: ${val >= 0 ? "#d73027" : "#1a9850"};">${f.contribution_celsius}</span>`;
        sec.appendChild(row);
      });
      wrap.appendChild(sec);
    }

    // 5-day health risk trajectory sparkline
    const traj = data.forecast_trajectory || [];
    if (traj.length > 0) {
      const W = 260, H = 60, PAD = 6;
      const pts = traj.map((t, i) => {
        const x = PAD + (i / (traj.length - 1)) * (W - 2 * PAD);
        const y = H - PAD - (t.risk_score / 100) * (H - 2 * PAD);
        return { x, y, t };
      });
      const sec = document.createElement("div");
      sec.style.marginTop = "12px";
      sec.innerHTML = `<div style="font-size: 12px; font-weight: 700; color: #334155; margin-bottom: 6px;">
        5-Day Health Risk Trajectory (local WBGT)</div>`;
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("width", W);
      svg.setAttribute("height", H);
      svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
      const poly = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
      poly.setAttribute("points", pts.map((p) => `${p.x},${p.y}`).join(" "));
      poly.setAttribute("fill", "none");
      poly.setAttribute("stroke", "#334155");
      poly.setAttribute("stroke-width", "2");
      svg.appendChild(poly);
      pts.forEach((p) => {
        const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        c.setAttribute("cx", p.x);
        c.setAttribute("cy", p.y);
        c.setAttribute("r", "4");
        c.setAttribute("fill", TIER_COLORS[p.t.health_risk_tier] || "#94a3b8");
        const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
        const airStr = p.t.temp_max !== undefined ? `${Number(p.t.temp_max).toFixed(1)}°C Air, ` : "";
        title.textContent = `Day ${p.t.day}: ${p.t.health_risk_tier} — ${airStr}WBGT ${p.t.local_wbgt}°C (score ${p.t.risk_score})`;
        c.appendChild(title);
        svg.appendChild(c);
      });
      sec.appendChild(svg);
      const legend = document.createElement("div");
      legend.style.cssText = "display: flex; gap: 8px; margin-top: 4px;";
      legend.innerHTML = traj
        .map((t) => `<span style="font-size: 10px; color: #475569;">D${t.day}${t.temp_max !== undefined ? ` (${Math.round(t.temp_max)}°)` : ""}: ${t.health_risk_tier}</span>`)
        .join("");
      sec.appendChild(legend);
      wrap.appendChild(sec);
    }

    // SMS dispatch trigger
    const btnRow = document.createElement("div");
    btnRow.style.cssText = "margin-top: 12px;";
    const smsBtn = document.createElement("button");
    smsBtn.className = "btn btn-primary";
    smsBtn.style.width = "100%";
    smsBtn.textContent = "📡 Dispatch SMS Alert to This Sector";
    smsBtn.addEventListener("click", () => openSmsModal(data));
    btnRow.appendChild(smsBtn);
    wrap.appendChild(btnRow);

    detail.appendChild(wrap);
  }

  // ---------- SMS Dispatch Modal ----------

  function openSmsModal(data) {
    smsTargetBlockId = data.block_id;
    const modal = document.getElementById("sms-modal");
    if (!modal) return;
    document.getElementById("sms-block-id").textContent =
      `${data.block_id} — ${data.risk_class || "Unknown"} risk, ~${data.population || 0} residents`;
    const advisory = data.automated_advisory;
    const msg = document.getElementById("sms-message");
    msg.value = typeof advisory === "string"
      ? advisory
      : (advisory && advisory.text) ||
        `Heat advisory for sector ${data.block_id}. ${data.summary || "Stay hydrated and limit midday exposure."}`;
    document.getElementById("sms-dispatch-result").textContent = "";
    modal.style.display = "flex";
  }

  function closeSmsModal() {
    const modal = document.getElementById("sms-modal");
    if (modal) modal.style.display = "none";
  }

  async function dispatchSms() {
    const resultEl = document.getElementById("sms-dispatch-result");
    if (!smsTargetBlockId) return;
    resultEl.textContent = "Dispatching…";
    try {
      const res = await fetch("/api/alerts/dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          block_id: smsTargetBlockId,
          recipient_group: document.getElementById("sms-recipient-group").value,
          message: document.getElementById("sms-message").value,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const audit = await res.json();
      resultEl.textContent =
        `✓ ${audit.audit_id} — ${audit.recipients_count} recipients via ${audit.channels.join(", ")}`;
    } catch (err) {
      resultEl.textContent = `Dispatch failed: ${err.message}`;
    }
  }

  function setupOfficerEvents() {
    const closeBtn = document.getElementById("btn-sms-modal-close");
    if (closeBtn) closeBtn.addEventListener("click", closeSmsModal);
    const dispatchBtn = document.getElementById("btn-sms-dispatch");
    if (dispatchBtn) dispatchBtn.addEventListener("click", dispatchSms);
    const modal = document.getElementById("sms-modal");
    if (modal) {
      modal.addEventListener("click", (e) => {
        if (e.target === modal) closeSmsModal();
      });
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    wrapOpenSidebar();
    setupOfficerEvents();
    initOfficer();
  });
})();
