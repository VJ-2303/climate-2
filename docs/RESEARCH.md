# Heatwave Early Warning & Human Thermal Stress Index
### SIH 2026 · Problem Statement SIH26083 · Ministry of Earth Sciences
**Final consolidated document: a feasible, AI-driven, human-centric early warning framework for India**

---

## 0. At a Glance (Quick Summary)

- **The challenge:** Build a system that reduces the health harm and economic damage caused by extreme heatwaves in India. It is a *decision-support ecosystem*, not just a weather app.
- **The core gap:** India's official heatwave definition (IMD) uses only air temperature and its departure from normal. It ignores **humidity**, even though "the same temperature is survivable in dry air and lethal in humid air."
- **Three other gaps:** forecasts are too coarse for neighbourhood-level decisions (Urban Heat Island effect), vulnerability maps are static, and alerts are generic and hard to act on.
- **Proposed solution, "ThermalGuard":** enrich IMD forecasts with humidity, compute a **Human Thermal Stress Index (HTSI, e.g. WBGT)**, combine it with a **vulnerability score** to give a tiered **Advisory Level**, explain the risk in plain language, and deliver it through a **role-based platform** (Public view + Officer view) with SMS/WhatsApp alerts.
- **Feasibility:** A student team can do this. The earlier **ThermoWatch** project already built a full-stack version (ML risk model, HTSI, role-based UI, regional-language chatbot prototype).
- **Strategy:** Ship a focused MVP (HTSI + map dashboard + manual alert + live demo), and keep XGBoost/SHAP, real-time humidity, satellite LST, dynamic vulnerability and automated alerts as the "advanced" roadmap.

---

## 1. Understanding the Problem Statement

**SIH26083: "Extreme Heatwave Early Warning and Human Thermal Stress Index"** (Ministry of Earth Sciences).

The goal is to **reduce severe human health consequences and socio-economic damage** from extreme heatwaves in India. The problem involves three connected parts:

1. **Technology capability**: forecasting and early warning.
2. **A critical metric**: a *Human Thermal Stress Index*, i.e. how heat actually affects the human body, not just air temperature.
3. **Diverse users and outcomes**: the system must serve many kinds of people and institutions.

The real deliverable is **a decision-support ecosystem designed to save lives and protect livelihoods**. The Ministry of Earth Sciences' involvement signals that the solution must be scientifically robust and operationally relevant at national level.

---

## 2. Who the System Must Serve

Users form a hierarchy, each with different needs:

### 2.1 Vulnerable populations
*Elderly, children, outdoor workers, people in informal settlements.*
- Need **timely, accessible, actionable alerts**. Generic temperature warnings are not enough.
- Messages should be clear and culturally appropriate, **ideally in regional languages** (e.g. ThermoWatch's Kannada localization).
- Messages must translate science into actions, for example: *"Stay hydrated," "Seek shade between 12 PM and 4 PM," "Check on your neighbours."*
- Channels must include **SMS, WhatsApp and voice-based assistants** so people without constant internet or high literacy are reached.

### 2.2 Local authorities
*District Collectors, municipal corporations, emergency services.*
- Need an **integrated command-and-control platform**.
- **Real-time situational awareness** through GIS heat-risk maps at district or sub-district level (similar to IMD's).
- **Actionable workflows:** deploy cooling centres, reserve hospital beds for heatstroke patients, coordinate emergency medical services.
- **A persistent history and auditable log** of all actions taken, useful both for managing the event and for evaluating it afterward.

### 2.3 Institutions: hospitals, schools, industries with outdoor labour
- **Hospitals and clinics:** advance notice to prepare for surges in emergency visits and hospitalizations; ensure staffing, water supply and electricity (as required by plans like Maharashtra's Heat Action Plan).
- **Schools:** a reliable framework to decide when to cancel classes or change schedules.
- **Outdoor workers** (construction, agriculture, where much of the workforce is informal): warnings that let them adjust work hours or access protection, reducing health risk and lost productivity.

---

## 3. What Success Looks Like (Inferred KPIs)

Success is not stated explicitly. It is implied by the severity of the problem and existing research:

| KPI | What it means |
|---|---|
| **Better forecast accuracy and lead time** | Improve on existing systems. IMD gives reasonably skilled forecasts up to **4-5 days**; extended-range models reach up to **32 days** but lose accuracy. Better performance, especially on high-probability events, is a win. |
| **Fewer heat-related deaths and illnesses** | The ultimate measure. Heat Action Plans (HAPs) are proven to work; Ahmedabad's plan was linked to a **significant decrease in all-cause mortality** during heatwaves. A winning solution must explain *how* it contributes to such outcomes. |
| **Reduced economic damage** | Extreme heatwaves cost India **hundreds of billions of potential labour hours** each year. Estimating the labour loss/productivity your early warnings could prevent is a powerful value indicator. |
| **Integration with the disaster-management system** | Must align with **NDMA guidelines** and support **state and district HAPs**. A tool that works in isolation fails the broader "whole-of-government" objective. |

---

## 4. Existing Solutions: India and the World

### 4.1 India

**India Meteorological Department (IMD)** provides the official forecasts.
- Declares a heatwave using **absolute maximum temperature + departure from normal**.
- For **plains**: Tmax **≥ 40°C**, with departure from normal of **4.5°C to 6.4°C**.
- Can predict genesis, duration and intensity with reasonable accuracy **up to 4-5 days** ahead.
- Issues **colour-coded warnings** via daily bulletins and provides **GIS-based visualizations**.

**IITM Extended Range Prediction (ERP)** gives forecasts up to **32 days** ahead, but skill drops sharply beyond about **two weeks**. It is useful for general outlooks, not precise planning.

**NDMA Heat Action Plans (HAPs)** are the policy backbone.
- Guidelines first issued **2016**, revised **2019**.
- Supported development of operational HAPs in **23+ states, 195 districts and 64 cities**.
- Cover **prevention, preparedness, response and recovery**, and assign responsibilities from central ministries down to local authorities.
- Include **vulnerability assessments** to identify at-risk populations, plus mitigation measures such as awareness campaigns and inter-agency coordination.

**ThermoWatch (previous hackathon precedent)**: a student-led, full-stack platform with an **ML-based risk model, an HTSI, role-based web interface (public + officers) and a prototype regional-language chatbot**. It proves a sophisticated solution is achievable in a hackathon timeframe.

### 4.2 Global trends
- **US National Weather Service "HeatRisk":** a color-numeric index of expected heat risk for a **24-hour period**. It moves from binary warnings to a **continuous spectrum of risk**, giving decision-makers more nuanced guidance.
- **AI weather models:** state-of-the-art models such as **GraphCast** and **Pangu-Weather** have outperformed traditional Numerical Weather Prediction (NWP) on many standard metrics. This makes AI integration a promising path to better accuracy and longer lead times.
- **International guidance:** **WMO and WHO** jointly issue guidance on Heat Health Early Warning Systems (HEWS). WMO's **"Early Warnings for All"** initiative reinforces the global urgency of strengthening these systems.

### 4.3 Comparison table

| Feature | India (IMD/NDMA-led) | United States (NWS) | International trend |
|---|---|---|---|
| **Primary forecaster** | India Meteorological Department (IMD) | National Weather Service (NWS) | Merging AI/ML with NWP models |
| **Forecast lead time** | Short-range 4-5 days; extended up to 32 days (skill degrades) | 24-hour risk forecast available | Medium-range (1-15 days) using ML weather prediction |
| **Core metric** | Air temperature & departure from normal | HeatRisk Index (color-numeric) | Human Thermal Stress Index (HTSI) |
| **Vulnerability data** | Integrated in NDMA guidelines and HAPs | Integrated in HeatRisk tool | Dynamic vulnerability mapping |
| **Alert dissemination** | Media broadcasts, mobile alerts, local authority networks | Web service API, media partnerships | Multi-modal (SMS, WhatsApp, voice) |
| **Policy framework** | NDMA Guidelines for HAPs | Not applicable | WMO/WHO joint guidance on HEWS |

**Takeaway:** India has a functional, government-driven system, but there is room for technological enhancement: **reliance on air temperature alone, static vulnerability assessments, and lack of hyper-local granularity.** A new solution should **augment, not replace**, national infrastructure by building on IMD data and aligning with NDMA policy.

---

## 5. Technical Deep Dive

### 5.1 Data layer

| Data | Purpose |
|---|---|
| **IMD daily forecast grids** (Tmax, Tmin, wind speed, pressure) | Primary source for any system in India |
| **Relative humidity** (from reanalysis such as **ERA5** or other open climate datasets) | Fills the critical "missing piece" in IMD's definition; humid heat is far more dangerous than dry heat at the same temperature |
| **Satellite Land Surface Temperature (LST)**, e.g. **MODIS** | Identifies **urban heat islands**, localized areas much hotter than rural surroundings |
| **GIS data:** census demographics, land-use maps (green vs built-up), poverty levels, infrastructure quality | Builds detailed **vulnerability indices** |
| **NWS NDFD XML Web Service** (HeatRisk data) | Model for structured data dissemination (access may be limited to specific regions) |

### 5.2 Modelling approaches
- **Traditional:** IMD relies on ensembles of physics-based **NWP** models.
- **Machine learning:** growing evidence supports ML for improved forecasting. State-of-the-art ML models can skilfully forecast **medium-range (1-15 days)**, often outperforming a single NWP model.
- **Techniques:** classical (**Random Forest, Gradient Boosting**) to deep learning (**CNNs, RNNs**) suited to spatial and temporal climate data.
- **Hybrid AI + NWP** (most promising frontier): AI corrects biases in NWP output or learns relationships NWP misses, giving more accurate and reliable forecasts.
- **What's feasible for a student team:** building a complex standalone ML weather model is likely out of scope. A better approach is to use a **validated HTSI as the core calculation layer**.
  - **WBGT (Wet-Bulb Globe Temperature)** combines temperature and humidity to measure physiological heat stress, directly addressing a major gap in Indian systems.
  - **SHAP (SHapley Additive exPlanations)** can generate plain-language reasons for predictions, turning a black-box output into actionable insight.

### 5.3 System architecture pattern
- **Backend:** Python (xarray, pandas for data; scikit-learn, TensorFlow for ML; Flask or Django for web services), serving a **RESTful API**.
- **Frontend:** Single Page Application in **React** or **Angular**.
- **Maps/GIS:** **Leaflet.js** or **Mapbox GL JS** to render heat-risk maps.
- **Deployment:** **AWS, Google Cloud, or Vercel** (Render also suggested in the MVP plan).
- **Alerting:** a **microservice** that subscribes to forecast updates and, on predefined thresholds, sends alerts via **Twilio** (SMS/WhatsApp). This keeps forecasting/display logic **decoupled** from notification delivery.

**Winning formula:** robust data pipeline + hybrid AI/traditional modelling centred on an HTSI + scalable web architecture + flexible alerting.

---

## 6. Innovation Gaps a Student Team Can Target

### Gap 1: The wrong risk metric (the "humidity blind spot")
IMD's definition relies **only on air temperature and departure from normal**. It ignores relative humidity. High humidity stops sweat from cooling the body, so IMD may **underestimate danger in humid heatwaves**, which are becoming more frequent and intense.
**Opportunity:** adopt a validated **HTSI such as WBGT**, a major methodological advance.

### Gap 2: Lack of hyper-local granularity
IMD's grid forecasts are often too coarse to capture temperature differences within cities from the **Urban Heat Island (UHI) effect**. A concrete-heavy neighbourhood can be much hotter than a nearby park or waterbody.
**Opportunity:** combine **satellite LST** with fine-grained GIS data (land cover, building density, green space) to produce **ward- or block-level risk maps**, so authorities can pinpoint hotspots and deploy mobile cooling units or hydration stations.

### Gap 3: Static vulnerability assessments
Vulnerability in HAPs is usually based on long-term demographic averages. It misses daily and weekly changes (e.g. a construction site with many outdoor workers on a given day).
**Opportunity:** use **near-real-time or dynamic proxies**, such as anonymized mobile phone traffic to estimate pedestrian flows in crowded outdoor areas, or social media sentiment to detect heat distress reports, and adjust the vulnerability score alongside forecast risk to produce a timely **Advisory Level**.

### Gap 4: Weak last-mile dissemination and actionability
Even a perfect forecast fails if it doesn't reach people or isn't understood. Current mobile alerts and media broadcasts are often **generic and impersonal**, and "high-risk" warnings rarely explain *why* or *what to do*.
**Opportunities:**
- **Targeted, multi-modal alerting**, segmented by user type. A construction foreman gets a message about adjusting work hours and checking equipment; a homebound senior gets a reminder to stay indoors and check in with family. Segments could include a school principal, an outdoor worker, a homebound senior.
- **AI-powered explanation engine** that turns model output into plain-language advice. Example: *"Your area will face 'Dangerous' heat stress today due to high humidity. Your body cannot cool itself effectively. Please avoid strenuous activity between 12 PM and 4 PM and drink plenty of water."*

This shifts the system from a passive information provider to an **active tool for behaviour change and life-saving decisions**.

---

## 7. Proposed Solution: "ThermalGuard"

A **human-centric, AI-augmented heat-risk platform** that augments IMD forecasts with a better human thermal stress metric and delivers it through a role-based interface. Three layers:

### 7.1 Data Processing Layer (the "nervous system")
- **Primary input:** IMD gridded forecast data, **Tmax and Tmin**.
- **Enrichment:** relative humidity from open reanalysis products (e.g. **ERA5**), tackling the humidity blind spot.
- **Spatial joins** with baseline data: administrative boundaries (districts, wards), **census population density**, and **land-cover** data as a proxy for UHI.
- **Tools:** Python scripts with **geopandas** and **xarray**.

### 7.2 Core Risk Engine (the innovation)
1. **HTSI calculation:** compute a physiologically relevant index (e.g. a **simplified WBGT equivalent**) combining temperature and humidity into a single risk value.
2. **Lightweight Explainable AI (XAI) model:** rather than a complex weather model from scratch, use a simple, interpretable model (e.g. **XGBoost**) trained on **historical IMD heatwave data** to predict heatwave probability for the next few days. Use **SHAP** to generate plain-language justifications.
3. **Dynamic Vulnerability Scoring:** compute a baseline vulnerability score per administrative unit from **demographic factors** (e.g. % elderly, outdoor workers) and **environmental factors** (e.g. green space coverage). Combine with forecast HTSI to produce a tiered **Advisory Level** (e.g. **Moderate, High, Dangerous**).

### 7.3 Application Layer (role-based web platform)
- **Backend:** Python/Django with a clean RESTful API.
- **Frontend:** React SPA with a central **Leaflet.js / Mapbox GL JS** map visualizing HTSI and Advisory Levels for the chosen region.
- **Two primary views:**
  1. **Public View:** simple, accessible forecast for the user's location, with clear, actionable advice from the XAI module; also a channel for receiving targeted alerts.
  2. **Officer View:** command-and-control dashboard with real-time situational awareness, tools to manage response operations, and an **audit trail** of actions taken during an event.

---

## 8. MVP vs Advanced Version (Development Roadmap)

| Component | **MVP (Hackathon goal)** | **Advanced (post-hackathon)** | Priority & justification |
|---|---|---|---|
| **Data integration** | IMD Tmax/Tmin + static humidity dataset | Real-time humidity; add LST satellite data for UHI detection | **High.** Foundational; core to solving the "humid heat" gap |
| **HTSI calculation** | Basic weighted-average HTSI | Validated index like WBGT; incorporate wind effects | **High.** Directly addresses the most critical flaw in current IMD warnings |
| **Risk engine** | Manual trigger for a sample advisory; no ML model | Train XGBoost for event probability; integrate SHAP for XAI | **Medium.** XAI adds significant value but is complex; start with manual triggers |
| **Vulnerability score** | Static baseline score per district | Dynamic scoring using real-time proxies (e.g. mobility data) | **Medium.** Static is enough for MVP; dynamic is a key future enhancement |
| **Frontend dashboard** | Basic map showing 1-3 day forecast; tabs for time horizons | Role-based views (Public/Officer); interactive map with legend, tooltips, filtering | **High.** Essential to demonstrate usability and impact |
| **Alerting module** | Manual trigger to send a sample SMS via Twilio | Automated, multi-modal (SMS, WhatsApp, voice) based on Advisory Level | **Low.** Manual trigger proves the concept; automation comes later |
| **Deployment** | Hosted on Vercel or Render | Docker containers; AWS/GCP for scalability | **High.** A live, publicly accessible demo is non-negotiable |

**Why this works:** a well-defined MVP lets the team focus on the core innovations, the **HTSI calculation and the role-based interface**, and deliver a polished, functional, high-impact demo instead of chasing every feature.

---

## 9. Key Takeaways

1. **Don't replace IMD; augment it.** Build on IMD data and align with NDMA's HAP framework.
2. **The differentiator is the metric:** HTSI/WBGT (temperature + humidity) instead of air temperature alone.
3. **Add local detail** (ward/block-level via UHI/LST) and, later, **dynamic vulnerability**.
4. **Make warnings understandable and actionable:** plain-language explanations, role-specific messages, regional languages, SMS/WhatsApp/voice.
5. **Serve both the public and the officers** (the officer dashboard needs workflows and an audit log).
6. **Scope smartly:** MVP with HTSI + map dashboard + manual sample alert + live deployment; push XGBoost/SHAP, real-time data and automation to the roadmap.
7. **Show impact** in terms of lives protected and labour hours saved, tied to how HAPs have already cut mortality (e.g. Ahmedabad).

---

## 10. Key References (from the source document)

**Problem statement & precedent**
- SIH 2026 problem statements: github.com/vedantchalke36/sih-2026-problem-statements
- ThermoWatch (SIH26083 precedent): github.com/monishkandanuru/thermowatch-sih26083
- SIH26083 listing: sihbuddy.in/ps/SIH26083
- SIH Navigator: sih-gitam.vercel.app

**Indian sources**
- IMD Heat Wave FAQ: internal.imd.gov.in/section/nhac/dynamic/FAQ_heat_wave.pdf
- Real-time extended range prediction of heat waves over India (Nature, Scientific Reports): nature.com/articles/s41598-019-45430-6
- Maharashtra Heat Wave Action Plan: sdma.maharashtra.gov.in/en/heat-wave-action-plan/
- Pilot evaluation of India's first Heat Action Plan (Ahmedabad): pmc.ncbi.nlm.nih.gov/articles/PMC6236972/
- Impact of heatwaves on all-cause mortality in India: pmc.ncbi.nlm.nih.gov/articles/PMC11790314/
- World Bank, Prioritizing Heat Mitigation Actions in Indian Cities
- PIB releases on urban heat islands and whole-of-government heat approach

**Global & AI/ML sources**
- NWS HeatRisk: wpc.ncep.noaa.gov/heatrisk/
- NDFD XML Web Service: graphical.weather.gov/xml/
- WHO, Heatwaves and health: guidance on warning-system development
- WMO Early Warnings for All: wmo.int/activities/early-warnings-all
- Probabilistic weather forecasting with machine learning (Nature): nature.com/articles/s41586-024-08252-9
- Machine Learning for Heatwave Prediction: A Global Review: preprints.org/manuscript/202605.1485
- Artificial intelligence and numerical weather prediction (ScienceDirect)
- Global HEWS report (PrepareCenter, 2026)

**Impact & economics**
- Extreme heat costing Indian workers billions in lost wages (PreventionWeb)
- Extreme Heat Is a Jobs Crisis: South Asia's Cities Can't Afford to Wait (World Bank blog)
- Heatwave Impacts and Resilience Mechanisms in Urban Informal Settlements (SAGE)

*The original document lists 109 numbered references in total; the above are the most directly relevant ones named in it.*
