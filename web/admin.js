// ThermalGuard — Administrative Command Dashboard Logic (5 Madurai Zones & Sensitive Facilities)
// Manages Zonal PIN auth, facility directory, contact updates, autonomous alerting, and map markers.

(function () {
  "use strict";

  let currentAuth = null; // { role, zone_id, zone_name, officer }
  let currentFacilities = [];
  let facilityMarkersGroup = null;
  let activeCategoryFilter = "All";
  let activeStatusFilter = "All";
  let searchQuery = "";

  const CATEGORY_SVGS = {
    "School": `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>`,
    "Hospital / Clinic": `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 5v14M5 12h14"/></svg>`,
    "College / University": `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c0 2 3 3 6 3s6-1 6-3v-5"/></svg>`,
  };

  const CATEGORY_COLORS = {
    "School": "#0284c7",
    "Hospital / Clinic": "#e11d48",
    "College / University": "#7c3aed",
  };

  // -------------------------------------------------------------------------
  // 1. PIN Authentication
  // -------------------------------------------------------------------------

  function checkSessionAuth() {
    const saved = sessionStorage.getItem("thermalguard_admin_auth");
    if (saved) {
      try {
        currentAuth = JSON.parse(saved);
        onAuthSuccess();
        return;
      } catch (e) {
        sessionStorage.removeItem("thermalguard_admin_auth");
      }
    }
    showAuthModal(true);
  }

  function showAuthModal(show) {
    const modal = document.getElementById("admin-auth-modal");
    if (!modal) return;
    modal.style.display = show ? "flex" : "none";
    if (show) {
      const pinInput = document.getElementById("admin-pin-input");
      if (pinInput) {
        pinInput.value = "";
        pinInput.focus();
      }
      const errEl = document.getElementById("admin-pin-error");
      if (errEl) errEl.style.display = "none";
    }
  }

  async function handlePinLogin(pin) {
    const errEl = document.getElementById("admin-pin-error");
    if (errEl) errEl.style.display = "none";
    const btnLogin = document.getElementById("btn-pin-submit");
    if (btnLogin) btnLogin.textContent = "Verifying...";

    try {
      const res = await fetch("/api/admin/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin: pin.trim() }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Invalid Zonal PIN");
      }

      currentAuth = await res.json();
      sessionStorage.setItem("thermalguard_admin_auth", JSON.stringify(currentAuth));
      showAuthModal(false);
      onAuthSuccess();
    } catch (err) {
      if (errEl) {
        errEl.textContent = err.message;
        errEl.style.display = "block";
      }
    } finally {
      if (btnLogin) btnLogin.textContent = "Unlock Command Center";
    }
  }

  function handleLogout() {
    sessionStorage.removeItem("thermalguard_admin_auth");
    currentAuth = null;
    if (facilityMarkersGroup && typeof map !== "undefined" && map) {
      facilityMarkersGroup.clearLayers();
    }
    window.location.reload();
  }

  // -------------------------------------------------------------------------
  // 2. Auth Success Initialization
  // -------------------------------------------------------------------------

  function onAuthSuccess() {
    if (!currentAuth) return;

    // Update Topbar UI
    const zonePill = document.getElementById("admin-zone-pill");
    const zoneNameEl = document.getElementById("admin-zone-name");
    if (zonePill && zoneNameEl) {
      zonePill.style.display = "inline-flex";
      zoneNameEl.textContent = currentAuth.zone_name;
    }

    // If DDMA Admin, enable Zone Switcher dropdown
    const switcherContainer = document.getElementById("admin-zone-switcher-container");
    if (switcherContainer && currentAuth.role === "ddma_admin") {
      switcherContainer.style.display = "inline-flex";
      initZoneSwitcherMenu();
    }

    // Load Facilities for this Zone (or Zone 1 default if DDMA)
    const targetZone = currentAuth.zone_id > 0 ? currentAuth.zone_id : 1;
    loadZoneFacilities(targetZone);

    // Show Facilities Drawer automatically
    toggleAdminPanel(true);
  }

  async function initZoneSwitcherMenu() {
    const menu = document.getElementById("zone-switcher-menu");
    const btn = document.getElementById("btn-zone-switcher");
    if (!menu || !btn) return;

    try {
      const res = await fetch("/api/admin/zones");
      if (!res.ok) return;
      const data = await res.json();
      const zones = data.zones || [];

      menu.innerHTML = '<div class="menu-section-header">Switch Administrative Zone</div>';
      zones.forEach((z) => {
        const item = document.createElement("div");
        item.className = "menu-layer-item";
        item.innerHTML = `
          <div class="menu-layer-info" style="flex:1;">
            <div style="display:flex; justify-content:space-between;">
              <span class="menu-layer-title">${z.zone_name}</span>
              <span style="font-size:10px; color:#64748b; font-weight:700;">${z.total_facilities} sites</span>
            </div>
            <span class="menu-layer-desc">${z.officer_name} &bull; ${z.verified_contacts} verified</span>
          </div>
        `;
        item.addEventListener("click", () => {
          menu.style.display = "none";
          const zoneNameEl = document.getElementById("admin-zone-name");
          if (zoneNameEl) zoneNameEl.textContent = z.zone_name;
          loadZoneFacilities(z.zone_id);
        });
        menu.appendChild(item);
      });

      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        menu.style.display = menu.style.display === "none" ? "flex" : "none";
      });
    } catch (e) {
      console.warn("Failed to load zones for switcher:", e);
    }
  }

  // -------------------------------------------------------------------------
  // 4. Sensitive Facilities Directory
  // -------------------------------------------------------------------------

  async function loadZoneFacilities(zoneId) {
    const container = document.getElementById("admin-facilities-list");
    if (container) {
      container.innerHTML = '<div style="text-align: center; color: #64748b; padding: 24px;">Loading sensitive facilities...</div>';
    }

    try {
      const res = await fetch(`/api/admin/zones/${zoneId}/facilities`);
      if (!res.ok) throw new Error("Failed to load facilities");
      const data = await res.json();
      currentFacilities = data.facilities || [];

      updateStatsSummary();
      renderFacilitiesList();
      plotFacilityMarkersOnMap();
    } catch (err) {
      if (container) {
        container.innerHTML = `<div style="text-align: center; color: #ef4444; padding: 24px;">Error: ${err.message}</div>`;
      }
    }
  }

  function updateStatsSummary() {
    const totalCount = currentFacilities.length;
    const verifiedCount = currentFacilities.filter((f) => f.status === "verified").length;
    const missingCount = totalCount - verifiedCount;

    const elTotal = document.getElementById("stat-total-facilities");
    const elVerified = document.getElementById("stat-verified-facilities");
    const elMissing = document.getElementById("stat-missing-facilities");
    const elBadge = document.getElementById("admin-verified-count-badge");

    if (elTotal) elTotal.textContent = totalCount;
    if (elVerified) elVerified.textContent = verifiedCount;
    if (elMissing) elMissing.textContent = missingCount;
    if (elBadge) elBadge.textContent = `${verifiedCount}/${totalCount}`;

    // Update One-Click Category Broadcast counts
    const schoolVerified = currentFacilities.filter((f) => f.category === "School" && f.status === "verified").length;
    const hospitalVerified = currentFacilities.filter((f) => f.category === "Hospital / Clinic" && f.status === "verified").length;
    const collegeVerified = currentFacilities.filter((f) => f.category === "College / University" && f.status === "verified").length;

    const countSchool = document.getElementById("bulk-count-schools");
    const countHospital = document.getElementById("bulk-count-hospitals");
    const countCollege = document.getElementById("bulk-count-colleges");

    if (countSchool) countSchool.textContent = `(${schoolVerified} ready)`;
    if (countHospital) countHospital.textContent = `(${hospitalVerified} ready)`;
    if (countCollege) countCollege.textContent = `(${collegeVerified} ready)`;
  }

  function renderFacilitiesList() {
    const container = document.getElementById("admin-facilities-list");
    if (!container) return;

    let filtered = currentFacilities.slice();

    // Category filter
    if (activeCategoryFilter !== "All") {
      filtered = filtered.filter((f) => f.category === activeCategoryFilter);
    }

    // Status filter
    if (activeStatusFilter === "verified") {
      filtered = filtered.filter((f) => f.status === "verified");
    } else if (activeStatusFilter === "unverified") {
      filtered = filtered.filter((f) => f.status === "unverified");
    }

    // Search query
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (f) =>
          f.name.toLowerCase().includes(q) ||
          (f.address && f.address.toLowerCase().includes(q)) ||
          (f.contact_person && f.contact_person.toLowerCase().includes(q)) ||
          (f.phone && f.phone.includes(q))
      );
    }

    if (filtered.length === 0) {
      container.innerHTML = `
        <div class="admin-empty-state">
          <div class="admin-empty-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
          </div>
          <div class="admin-empty-title">No institutions match the filter</div>
          <div class="admin-empty-desc">Try selecting 'All' or clearing the search query.</div>
        </div>
      `;
      return;
    }

    let html = "";
    filtered.forEach((f) => {
      const isVerified = f.status === "verified";
      const svgIcon = CATEGORY_SVGS[f.category] || `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/></svg>`;
      const catColor = CATEGORY_COLORS[f.category] || "#475569";
      const statusBadge = isVerified
        ? '<span class="status-pill status-ready"><span class="status-dot"></span>Ready</span>'
        : '<span class="status-pill status-unregistered"><span class="status-dot"></span>Unregistered</span>';

      const contactDisplay = isVerified
        ? `<div class="facility-contact-row">
             <span class="facility-contact-person">${f.contact_person || "Designated In-Charge"}</span>
             <span class="facility-contact-sep">&bull;</span>
             <span class="facility-contact-phone">${f.phone}</span>
           </div>`
        : "";

      const lastAlertInfo = f.last_alert_time
        ? `<div class="facility-last-alert">Last Alert: ${f.last_alert_time}</div>`
        : "";

      html += `
        <div class="facility-card" data-id="${f.id}">
          <div class="facility-card-header">
            <div class="facility-card-info">
              <div class="facility-card-title-row">
                <span class="facility-category-icon" style="color:${catColor};">${svgIcon}</span>
                <span class="facility-name">${f.name}</span>
              </div>
              <div class="facility-meta" style="color:${catColor};">
                ${f.category} <span class="facility-address">&bull; ${f.address || "Madurai"}</span>
              </div>
              ${contactDisplay}
              ${lastAlertInfo}
            </div>
            <div>${statusBadge}</div>
          </div>

          <div class="facility-card-actions">
            <button class="btn btn-outline btn-edit-contact" data-id="${f.id}">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
              <span>${isVerified ? "Edit Phone" : "Add Phone"}</span>
            </button>
            <button class="btn btn-outline btn-locate-facility" data-lat="${f.latitude}" data-lon="${f.longitude}" data-name="${f.name}">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>
              <span>Focus</span>
            </button>
            <button class="btn btn-primary btn-alert-facility" data-id="${f.id}" data-name="${f.name}" ${!isVerified ? 'disabled title="Add contact phone first"' : ''}>
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              <span>Dispatch Alert</span>
            </button>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;

    // Attach card event listeners
    container.querySelectorAll(".btn-edit-contact").forEach((b) => {
      b.addEventListener("click", () => {
        const facId = b.getAttribute("data-id");
        openFacilityContactModal(facId);
      });
    });

    container.querySelectorAll(".btn-locate-facility").forEach((b) => {
      b.addEventListener("click", () => {
        const lat = parseFloat(b.getAttribute("data-lat"));
        const lon = parseFloat(b.getAttribute("data-lon"));
        const name = b.getAttribute("data-name");
        locateFacilityOnMap(lat, lon, name);
      });
    });

    container.querySelectorAll(".btn-alert-facility").forEach((b) => {
      b.addEventListener("click", () => {
        const facId = b.getAttribute("data-id");
        const facName = b.getAttribute("data-name");
        dispatchSingleFacilityAlert(facId, facName);
      });
    });
  }

  // -------------------------------------------------------------------------
  // 5. Leaflet Map Markers Integration
  // -------------------------------------------------------------------------

  function plotFacilityMarkersOnMap() {
    if (typeof map === "undefined" || !map || typeof L === "undefined") return;

    if (!facilityMarkersGroup) {
      facilityMarkersGroup = L.layerGroup().addTo(map);
    } else {
      facilityMarkersGroup.clearLayers();
    }

    currentFacilities.forEach((f) => {
      const color = CATEGORY_COLORS[f.category] || "#475569";
      const svgIcon = CATEGORY_SVGS[f.category] || `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2"><circle cx="12" cy="12" r="3"/></svg>`;

      const customIcon = L.divIcon({
        className: "custom-facility-pin",
        html: `<div class="facility-map-marker" style="background:${color};" title="${f.name}">${svgIcon}</div>`,
        iconSize: [26, 26],
        iconAnchor: [13, 13],
      });

      const marker = L.marker([f.latitude, f.longitude], { icon: customIcon });

      const isVerified = f.status === "verified";
      const popupHtml = `
        <div class="facility-popup-content">
          <div class="facility-popup-title">${f.name}</div>
          <div class="facility-popup-meta" style="color:${color};">${f.category} &bull; <span style="color:#64748b;font-weight:400;">${f.address || "Madurai"}</span></div>
          ${isVerified ? `<div class="facility-popup-contact"><strong>${f.phone}</strong> &bull; ${f.contact_person || "In-Charge"}</div>` : ""}
          <div style="margin-top:8px;">
            <button class="btn btn-outline" onclick="window.adminOpenContactModal('${f.id}')" style="padding:3px 8px; font-size:11px; width:100%; justify-content:center;">
              ${isVerified ? "Edit Phone" : "Add Phone"}
            </button>
          </div>
        </div>
      `;

      marker.bindPopup(popupHtml);
      facilityMarkersGroup.addLayer(marker);
    });
  }

  function locateFacilityOnMap(lat, lon, name) {
    if (typeof map === "undefined" || !map) return;
    map.flyTo([lat, lon], 17, { duration: 1.2 });
    showToast(`Centered on ${name}`);
  }

  // -------------------------------------------------------------------------
  // 6. Contact & Profile Modals
  // -------------------------------------------------------------------------

  function openFacilityContactModal(facilityId) {
    const fac = currentFacilities.find((f) => f.id === facilityId);
    if (!fac) return;

    const modal = document.getElementById("facility-contact-modal");
    if (!modal) return;

    document.getElementById("contact-facility-name").textContent = fac.name;
    document.getElementById("contact-facility-cat").textContent = `${fac.category} &bull; ${fac.address || "Madurai"}`;
    document.getElementById("input-facility-id").value = fac.id;
    document.getElementById("input-contact-person").value = fac.contact_person || "";
    document.getElementById("input-contact-phone").value = fac.phone || "";
    document.getElementById("input-contact-email").value = fac.email || "";
    document.getElementById("contact-modal-error").style.display = "none";

    modal.style.display = "flex";
  }

  function closeFacilityContactModal() {
    const modal = document.getElementById("facility-contact-modal");
    if (modal) modal.style.display = "none";
  }

  async function saveFacilityContact() {
    const facId = document.getElementById("input-facility-id").value;
    const person = document.getElementById("input-contact-person").value.trim();
    const phone = document.getElementById("input-contact-phone").value.trim();
    const email = document.getElementById("input-contact-email").value.trim();
    const errEl = document.getElementById("contact-modal-error");

    if (errEl) errEl.style.display = "none";

    try {
      const res = await fetch(`/api/admin/facilities/${facId}/contact`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contact_person: person, phone: phone, email: email }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to update contact");
      }

      const updated = await res.json();
      const idx = currentFacilities.findIndex((f) => f.id === facId);
      if (idx !== -1) currentFacilities[idx] = updated;

      updateStatsSummary();
      renderFacilitiesList();
      plotFacilityMarkersOnMap();
      closeFacilityContactModal();
      showToast(`Contact details verified for ${updated.name}`);
    } catch (err) {
      if (errEl) {
        errEl.textContent = err.message;
        errEl.style.display = "block";
      }
    }
  }


  // -------------------------------------------------------------------------
  // 7. Alerting Actions (Single & Bulk)
  // -------------------------------------------------------------------------

  async function dispatchSingleFacilityAlert(facId, facName) {
    if (!confirm(`Broadcast official heat advisory to ${facName}?`)) return;

    try {
      const res = await fetch("/api/admin/alerts/dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ facility_id: facId }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Alert dispatch failed");
      }

      const audit = await res.json();
      showDispatchSuccessModal(audit);
      // Update last alert time locally
      const idx = currentFacilities.findIndex((f) => f.id === facId);
      if (idx !== -1) currentFacilities[idx].last_alert_time = audit.timestamp;
      renderFacilitiesList();
    } catch (err) {
      alert(`Dispatch Error: ${err.message}`);
    }
  }

  async function dispatchBulkCategoryAlert(category) {
    const verifiedCount = currentFacilities.filter(
      (f) => (category === "All" || f.category === category) && f.status === "verified"
    ).length;

    if (verifiedCount === 0) {
      alert(`Cannot broadcast: No verified contacts found for ${category}. Please add phone numbers first.`);
      return;
    }

    const label = category === "All" ? "all verified institutions" : `all ${verifiedCount} verified ${category}s`;
    if (!confirm(`Broadcast emergency heat advisory to ${label} in this zone?`)) return;

    const targetZone = currentAuth.zone_id > 0 ? currentAuth.zone_id : (currentFacilities[0] ? currentFacilities[0].zone_id : 1);

    try {
      const res = await fetch("/api/admin/alerts/dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ zone_id: targetZone, category: category }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Bulk dispatch failed");
      }

      const audit = await res.json();
      showDispatchSuccessModal(audit);
      // Reload zone facilities to refresh last alert times
      loadZoneFacilities(targetZone);
    } catch (err) {
      alert(`Bulk Dispatch Error: ${err.message}`);
    }
  }

  function showDispatchSuccessModal(audit) {
    const modal = document.getElementById("admin-dispatch-result-modal");
    if (!modal) return;

    document.getElementById("res-alert-id").textContent = audit.alert_id;
    document.getElementById("res-alert-recipients").textContent = `${audit.recipients_count} Institutions`;
    document.getElementById("res-alert-channels").textContent = (audit.channels || []).join(", ");
    document.getElementById("res-alert-wbgt").textContent = `${audit.local_wbgt}°C WBGT`;
    document.getElementById("res-alert-msg-en").textContent = audit.message_en;
    document.getElementById("res-alert-msg-ta").textContent = audit.message_ta;

    modal.style.display = "flex";
  }

  // -------------------------------------------------------------------------
  // 8. Toast Helper & Panel Toggle
  // -------------------------------------------------------------------------

  function showToast(msg) {
    let toast = document.getElementById("admin-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "admin-toast";
      toast.style.cssText = "position:fixed; bottom:20px; right:20px; background:#0f172a; color:#fff; padding:10px 18px; border-radius:6px; font-size:12px; font-weight:600; z-index:9999; box-shadow:0 4px 12px rgba(0,0,0,0.15); transition:opacity 0.3s ease;";
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.style.opacity = "1";
    setTimeout(() => { toast.style.opacity = "0"; }, 3500);
  }

  function toggleAdminPanel(forceOpen) {
    const panel = document.getElementById("admin-directory-panel");
    const btn = document.getElementById("btn-admin-panel");
    if (!panel) return;

    const isHidden = panel.style.display === "none" || !panel.style.display;
    const shouldOpen = forceOpen !== undefined ? forceOpen : isHidden;

    panel.style.display = shouldOpen ? "flex" : "none";
    if (btn) {
      if (shouldOpen) btn.classList.add("active");
      else btn.classList.remove("active");
    }
  }

  // -------------------------------------------------------------------------
  // 9. Event Setup & Boot
  // -------------------------------------------------------------------------

  function setupAdminEvents() {
    // PIN submit
    const btnPin = document.getElementById("btn-pin-submit");
    const pinInput = document.getElementById("admin-pin-input");
    if (btnPin && pinInput) {
      btnPin.addEventListener("click", () => handlePinLogin(pinInput.value));
      pinInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") handlePinLogin(pinInput.value);
      });
    }

    // Quick PIN demo chips
    document.querySelectorAll(".pin-demo-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const pin = chip.getAttribute("data-pin");
        if (pinInput) {
          pinInput.value = pin;
          handlePinLogin(pin);
        }
      });
    });

    // Panel Toggle
    const btnPanel = document.getElementById("btn-admin-panel");
    if (btnPanel) btnPanel.addEventListener("click", () => toggleAdminPanel());

    const btnPanelClose = document.getElementById("btn-admin-panel-close");
    if (btnPanelClose) btnPanelClose.addEventListener("click", () => toggleAdminPanel(false));

    // Category filter tabs
    document.querySelectorAll(".cat-filter-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".cat-filter-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        activeCategoryFilter = btn.getAttribute("data-cat");
        renderFacilitiesList();
      });
    });

    // Status filter select
    const statusSelect = document.getElementById("admin-status-filter");
    if (statusSelect) {
      statusSelect.addEventListener("change", (e) => {
        activeStatusFilter = e.target.value;
        renderFacilitiesList();
      });
    }

    // Live search input
    const searchInp = document.getElementById("admin-facility-search");
    if (searchInp) {
      searchInp.addEventListener("input", (e) => {
        searchQuery = e.target.value.trim();
        renderFacilitiesList();
      });
    }

    // Bulk Alert Buttons
    const btnBulkSchools = document.getElementById("btn-bulk-alert-schools");
    if (btnBulkSchools) btnBulkSchools.addEventListener("click", () => dispatchBulkCategoryAlert("School"));

    const btnBulkHospitals = document.getElementById("btn-bulk-alert-hospitals");
    if (btnBulkHospitals) btnBulkHospitals.addEventListener("click", () => dispatchBulkCategoryAlert("Hospital / Clinic"));

    const btnBulkColleges = document.getElementById("btn-bulk-alert-colleges");
    if (btnBulkColleges) btnBulkColleges.addEventListener("click", () => dispatchBulkCategoryAlert("College / University"));

    // Modals close & save
    const btnSaveContact = document.getElementById("btn-save-contact");
    if (btnSaveContact) btnSaveContact.addEventListener("click", saveFacilityContact);

    const btnCloseContact = document.getElementById("btn-close-contact-modal");
    if (btnCloseContact) btnCloseContact.addEventListener("click", closeFacilityContactModal);


    const btnCloseResult = document.getElementById("btn-close-result-modal");
    if (btnCloseResult) {
      btnCloseResult.addEventListener("click", () => {
        const m = document.getElementById("admin-dispatch-result-modal");
        if (m) m.style.display = "none";
      });
    }
  }

  // Expose global helper for popup clicks
  window.adminOpenContactModal = openFacilityContactModal;

  // Boot
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      setupAdminEvents();
      checkSessionAuth();
    });
  } else {
    setupAdminEvents();
    checkSessionAuth();
  }
})();
