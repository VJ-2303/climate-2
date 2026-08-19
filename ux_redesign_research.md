# UX Redesign Research: Making HeatViz Accessible for End Users

## 1. Analysis of Current UX & Pain Points
* **Always Visible Sidebars:** The `Data Layers` panel on the left and the `Inspector Sidebar` on the right take up significant screen real estate. For an end-user, the map should be the primary focus, with details summoned only when needed.
* **Information Density:** The current block inspector shows raw gauges, progress bars, and a wall of metrics (12+ data points simultaneously).
* **Technical Jargon:** Terms like `NDVI`, `NDWI`, `NDBI`, `AI Heat Exposure (GAT)`, and `Cooling Access Deficit` are highly technical remote-sensing/ML terms. End users (e.g., city planners, local officials, community workers) need functional language.

## 2. Terminology Simplification
We will map technical terms to easily understandable concepts:
* `NDVI (Vegetation)` ➔ **Greenery & Shade**
* `NDWI (Moisture)` ➔ **Water Presence**
* `NDBI (Built-up)` ➔ **Heat-Trapping Surfaces** (Concrete/Asphalt)
* `AI Heat Exposure` ➔ **Estimated Surface Heat**
* `Cooling Access Deficit` ➔ **Access to Cooling**
* `Social Sensitivity` ➔ **Community Vulnerability**
* `Building Density` ➔ **Crowding**

## 3. Redesign Strategy
### A. The Data Layer Sidebar (Left)
* **Action:** Convert from an always-visible floating deck to a collapsable panel (or a sleek bottom-left toggle). We'll add a minimalist toggle button that slides the panel in and out.
* **Content:** Simplify the layer names. Group them into "Overall Risk" and "Contributing Factors".

### B. The Block Inspector (Right)
* **Action:** Make it an off-canvas sidebar that only slides in when a user clicks on a block. Provide a clear "Close" button (X).
* **Structure:** When opened, it will present a structured "Block Profile":
  1. **Headline Risk:** "Critical Heat Risk" with a clear color indicator.
  2. **Plain English Summary:** E.g., "This area is home to ~48 people. It faces severe heat risk primarily due to lack of greenery and dense heat-trapping surfaces."
  3. **Key Drivers:** 2-3 simple bullet points (e.g., "⚠️ Very low vegetation").
  4. **Actionable Recommendation:** What to do about it.

### C. New Backend Endpoint (`/api/blocks/{block_id}`)
Instead of the frontend trying to parse and translate raw technical scores (`ndvi: 23`) into English, we will offload this to the server. 
* We will create a new FastAPI endpoint that takes a `block_id`.
* It will return a structured JSON containing the human-readable summary, translated metrics, and risk narrative.
* **Why?** It keeps the frontend lightweight, separates data presentation logic from the UI, and allows for future enhancements (like hooking into an LLM for dynamic summaries) without changing frontend code.

## 4. Implementation Steps
1. **Backend:** Create the `/api/blocks/{block_id}` endpoint in `api/main.py`. Cache the block data in a dictionary on startup for fast lookups.
2. **Frontend UI:** 
   - Add toggle buttons for the sidebars.
   - Restyle the right sidebar to be hidden by default (e.g., `transform: translateX(100%)`).
   - Clean up `index.html` to remove the complex telemetry grid and replace it with a clean structure for the API data.
3. **Frontend JS:** Update `app.js` to handle toggle events and make an async `fetch` call to the new API when a block is clicked.
