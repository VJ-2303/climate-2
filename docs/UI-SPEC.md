# UI-SPEC.md — ThermalGuard Citizen Heat Safety Design Contract

**Authoritative Frontend Specification for the Citizen Public Portal (`/public`)**  
**Design Reference:** OpenWeather One Call Dashboard (Human-Designed, Neat, Simple, Pleasant, Non-AI)  
**Target Location:** Madurai, Tamil Nadu  

---

## 1. Executive Summary & Design Vision

This specification defines the visual language, layout structure, typography, color tokens, and component architecture for the **ThermalGuard Citizen Heat Safety Portal**. 

Inspired directly by **OpenWeather's One Call meteorological dashboard**, this design replaces generic, over-engineered "AI template" tropes (neon purple glowing borders, dark cyberpunk glassmorphism, unreadable pastel text) with a **clean, pleasant, human-crafted weather interface** that citizens of Madurai can understand at a glance.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ TOP NAVIGATION BAR: Logo · Madurai Heat Safety · Live Air Pill · [தமிழ்] · [Locate Me]      │
├─────────────────────────────────────────────────────────┬───────────────────────────────────┤
│ CURRENT WEATHER & HEAT STRESS HERO CARD (40%)           │ HOURLY HEAT CURVE & FORECAST (60%)│
│ ┌─────────────────────────────────────────────────────┐ │ ┌───────────────────────────────┐ │
│ │ Sky Banner: Live Air 36°C · Feels 32°C · Clear Sky  │ │ │ Diurnal Heat Line Chart (SVG) │ │
│ └─────────────────────────────────────────────────────┘ │ └───────────────────────────────┘ │
│ ┌───────────────┬───────────────┬───────────────────┐ │ ┌───┬───┬───┬───┬───┬───┬───┬───┐ │
│ │ Outdoor Air   │ Roof Surface  │ Humidity          │ │ │10a│11a│12p│1p │2p │3p │4p │5p │ │
│ │ 35.8°C        │ 50.4°C        │ 68% RH            │ │ │32°│34°│36°│37°│37°│36°│34°│31°│ │
│ ├───────────────┼───────────────┼───────────────────┤ │ └───┴───┴───┴───┴───┴───┴───┴───┘ │
│ │ Wind Speed    │ Danger Window │ Cool Shelter      │ │                                     │
│ │ 3.2 m/s SSE   │ 11AM - 3:30PM │ 180m Park         │ │                                     │
│ └───────────────┴───────────────┴───────────────────┘ │                                     │
├─────────────────────────────────────────────────────────┴───────────────────────────────────┤
│ NEIGHBORHOOD QUICK-CHIPS: [Pasumalai] [Meenakshi Temple] [Periyar] [Goripalayam] [Anna Nagar]│
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ FULL-WIDTH INTERACTIVE HEAT RADAR MAP CARD                                                  │
│ ┌─────────────────────────────────────────────────────────────────────────────────────────┐ │
│ │ Leaflet 50m Microclimate Layer (Carto / Satellite)                                      │ │
│ │                                                                                         │ │
│ │ ┌────────────────────────────────────────┐            ┌───────────────────────────────┐ │ │
│ │ │ FLOATING WIDGET (Bottom-Left):         │            │ FLOATING CONTROLS:            │ │ │
│ │ │ Peak Sun Heat Window Timeline          │            │ • Basemap Switch (Map / Sat)  │ │ │
│ │ │ [Now] [12 PM] [1 PM] [2 PM] [3 PM]     │            │ • "My Location" Crosshair FAB │ │ │
│ │ │ Color Swatches: Safe → Moderate → High │            │ • Reset View                  │ │ │
│ │ └────────────────────────────────────────┘            └───────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ HEALTH & HYDRATION ACTIONS & NEAREST COOL SPOTS                                             │
│ • Hydration Schedule  • Shaded Route Advice  • Cross-Ventilation  • UPHC Centers & Water Taps│
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Visual Style & Color Tokens

### 2.1 Surfaces & Canvas
* **Background Canvas:** Natural atmospheric cloudscape (`background: linear-gradient(rgba(15, 23, 42, 0.75), rgba(15, 23, 42, 0.85)), url('/static/assets/sky_bg.jpg')` with graceful gradient fallback: `linear-gradient(135deg, #1e293b 0%, #0f172a 50%, #1e1b4b 100%)`).
* **Card Containers:** Pure solid white (`#ffffff`), `border-radius: 20px`, `box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.12), 0 8px 10px -6px rgba(0, 0, 0, 0.06)`, `border: 1px solid rgba(255, 255, 255, 0.1)`.
* **Metric Pill Background:** Warm organic sand/cream (`#faf6f0`), `border: 1px solid #f3e8d9`, `border-radius: 12px`.
* **Primary Accent Color:** Warm solar orange (`#f97316` / `#ea580c`) for active buttons, key indicators, and prominent CTAs.

### 2.2 Standard Meteorological Risk Scale (Frozen by Contract)
| Risk Class | Swatch | Background | Text Color | Plain Description |
|---|---|---|---|---|
| **Low / Safe** | `#16a34a` | `#dcfce7` | `#166534` | Safe & Comfortable Conditions |
| **Medium** | `#eab308` | `#fef9c3` | `#854d0e` | Moderate Thermal Load |
| **High** | `#ea580c` | `#ffedd5` | `#9a3412` | Elevated Heat Risk |
| **Critical** | `#dc2626` | `#fee2e2` | `#991b1b` | Severe Heat Danger Alert |

---

## 3. Typography System

* **Primary Typeface:** `'Outfit'`, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif.
* **Numerical & Data Typeface:** `'JetBrains Mono'`, monospace (for coordinates, timestamps, temperatures).

| Role | Font Size | Weight | Line Height | Color |
|---|---|---|---|---|
| **Hero Temperature** | `3.25rem` (52px) | 800 | 1.05 | `#ffffff` (on sky banner) / `#0f172a` |
| **Card Section Titles**| `1.15rem` (18.4px) | 700 | 1.3 | `#0f172a` |
| **Place / Location Title** | `1.10rem` (17.6px) | 800 | 1.25 | `#0f172a` |
| **Metric Pill Value** | `0.92rem` (14.7px) | 700 | 1.2 | `#1e293b` |
| **Metric Pill Label** | `0.70rem` (11.2px) | 600 | 1.2 | `#64748b` |
| **Hourly Forecast Time** | `0.72rem` (11.5px) | 600 | 1.2 | `#475569` |

---

## 4. Component Layout Specifications

### 4.1 Top Navigation Bar
* **Height:** `64px`, `display: flex; align-items: center; justify-content: space-between; padding: 0 24px`.
* **Background:** `rgba(15, 23, 42, 0.85)` with `backdrop-filter: blur(8px)`, `border-bottom: 1px solid rgba(255, 255, 255, 0.1)`.
* **Brand Element:** Sun icon SVG + `ThermalGuard` logo text in crisp white (`#ffffff`).
* **Search Input:** Rounded pill search bar (`border-radius: 24px`, `#ffffff` bg, magnifying glass SVG, placeholder: *"Search neighborhood (e.g. Meenakshi Temple, Anna Nagar)..."*).
* **Language Switcher:** Pill button (`[தமிழ்]` / `[English]`).
* **Locate Action:** Warm orange pill button (`background: #ea580c; color: #ffffff`) with GPS crosshair icon.
* **Officer Link:** Crisp outline button to switch to Municipal Officer Console (`/officer`).

### 4.2 Current Weather & Heat Stress Hero Card (Left Column)
* **Width:** ~38% of desktop container width (stacked on mobile).
* **Upper Atmospheric Sky Header:**
  * Background: Clear tropical sky image or atmospheric azure gradient (`linear-gradient(180deg, #38bdf8 0%, #0284c7 100%)`).
  * `border-radius: 14px`, padding `18px`, color `#ffffff`.
  * Top row: Location chip (`Pasumalai, Madurai South`) + Live Time (`11:03 AM`).
  * Big Temperature: `36°` with condition label (`Clear Sky · High Heat Exposure`) + `Feels like 32°C (WBGT)`.
* **Lower Metric 2x3 Grid:**
  * 6 warm beige pill cards (`#faf6f0`, `border-radius: 12px`, padding `10px`):
    1. **Outdoor Air:** Ambient temperature you breathe (`35.8°C`) with Sun SVG.
    2. **Roof & Ground Heat:** Radiometric satellite skin temperature (`50.4°C`) with Radiant Roof SVG.
    3. **Humidity:** Relative humidity (`68% RH`) with Droplet SVG.
    4. **Wind:** Wind speed (`3.2 m/s SSE`) with Wind SVG.
    5. **Danger Window:** Peak sun hours (`11 AM – 3:30 PM`) with Clock SVG.
    6. **Nearest Cool Shelter:** Proximity to shade (`180m Park`) with Tree SVG.
* **Plain-Language Explainer Note:**
  * Callout box with SVG info icon explaining the difference between baked rooftops/impervious surfaces (~50°C) and outdoor shaded air (~36°C).

### 4.3 Hourly Heat Curve & Forecast Card (Right Column)
* **Width:** ~60% of desktop container width (stacked on mobile).
* **Header:** Bold title `"Hourly Heat Forecast & Danger Window"`.
* **Upper Section: Interactive Diurnal Curve (SVG Chart):**
  * Smooth spline line chart showing heat stress evolution from morning (28°C) to peak sun (37°C) to evening relief (30°C).
  * Shaded danger band under the curve highlighting the peak sun window (`11:00 AM – 3:30 PM`).
* **Lower Section: Hourly Scrubber:**
  * Horizontal row of 9 rounded hourly cards:
    * Time label (`10 a.m`, `11 a.m`, `12 p.m`, `1 p.m`, `2 p.m`, `3 p.m`, `4 p.m`, `5 p.m`, `6 p.m`).
    * Weather condition icon (sun, hazy sun, cloud).
    * Risk tag (`Safe`, `Moderate`, `Severe`).
    * Temperature reading (`32°`, `34°`, `36°`, `37°`, `37°`, `36°`, `34°`, `31°`, `29°`).

### 4.4 Full-Width Interactive Heat Radar Map Card
* **Container:** Large rounded card (`border-radius: 20px`, overflow hidden, height `440px`, margin-top `24px`).
* **Map Engine:** Leaflet map with 50m microclimate heat blocks and 2x buffer boundary constraint.
* **Floating Bottom-Left Widget (Reference match):**
  * Mimicking the reference's *"Minute forecast - precipitation"* widget:
  * White card (`background: #ffffff`, `border-radius: 12px`, padding `12px 16px`, `box-shadow: 0 4px 16px rgba(0,0,0,0.15)`).
  * Left: Peak Sun Window intervals (`11:00 AM`, `12:00 PM`, `1:00 PM`, `2:00 PM`, `3:00 PM`).
  * Right: Legend scale swatches (Safe Green, Moderate Yellow, High Orange, Severe Red).
* **Floating Map Controls:**
  * Basemap toggle (Default Carto / OpenStreetMap vs High-Res Satellite).
  * Floating "My Location" crosshair FAB.
  * Reset View button.

### 4.5 Health & Hydration Protection & Nearest Cool Spots
* **Layout:** Two complementary cards below the map:
  * **Card 1: Health & Hydration Action Checklist:**
    * 4 actionable bullet items with clean vector SVGs (Hydration schedule, Shaded routes, Indoor ventilation, Vulnerable care for children/seniors).
  * **Card 2: Nearest Cool Spots & Water Refill Centers:**
    * Proximity to tree canopy shade / park (`data.dist_green_m`).
    * Proximity to water body / clean drinking water point (`data.dist_water_m`).
    * Nearest Corporation Urban Public Health Center (UPHC) cool shelter.

---

## 5. Bilingual Tamil Safety Integration

When the user taps the **`[தமிழ்]`** button in the top navigation, all safety advisories and labels switch instantly into clean, natural Tamil:
* **Active Location:** *தேர்ந்தெடுக்கப்பட்ட பகுதி*
* **Outdoor Air:** *வெளிப்புற நிழல் காற்று*
* **Roof Heat:** *கூரை வெப்பம்*
* **Feels Like:** *உடல் உணரும் வெப்பம்*
* **Peak Sun Danger Hours:** *உச்சி வெயில் ஆபத்து நேரம் (11:00 மு.ப - 3:30 பி.ப)*
* **Health Actions:** *உடல் நலப் பாதுகாப்பு ஆலோசனைகள்*
* **Nearest Cool Spots:** *அருகிலுள்ள நிழல் மற்றும் குடிநீர் மையங்கள்*
* **Hydration Advice:** *அடிக்கடி தண்ணீர் அல்லது ORS குடியுங்கள்*
* **Shade Advice:** *நண்பகல் வெயிலில் நிழலான பாதைகளை பயன்படுத்துங்கள்*
* **Ventilation Advice:** *வீட்டின் ஜன்னல்களை திறந்து காற்றோட்டமாக வையுங்கள்*

---

## 6. Zero-Emoji Enforcement & Accessibility Standards

* **Emoji Audit:** Exactly **0** unicode emojis allowed across HTML, CSS, JavaScript templates, or SVGs.
* **Vector Iconography:** High-precision, semantic inline SVGs matching standard meteorological icons (thermometer, sun with rays, cloud, droplet, wind, eye, clock, tree, shield, checkmark, crosshair).
* **Accessibility (WCAG AA):**
  * All card text achieves >= 4.5:1 contrast against `#ffffff` and `#faf6f0` backgrounds.
  * All interactive buttons include `:focus-visible` outline rings (`2px solid #0284c7`).
  * All interactive elements have accessible `aria-label` attributes.

---

## 7. Responsive Breakpoints

* **Desktop (`>= 1024px`):** Max-width 1280px container, 2-column upper grid (40% / 60%), full-width map card.
* **Tablet (`768px – 1023px`):** Stacked upper cards, full-width map card, 2-column action cards.
* **Mobile (`< 768px`):** Single-column vertical flow, swipeable hourly forecast scrubber, full-width touch-friendly map card.
