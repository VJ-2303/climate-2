"""
HeatViz Climate Intelligence API
Serves GeoJSON layers and provides a rich, rule-based expert intelligence endpoint
for per-block climate vulnerability inspection in Kibera.
"""

from contextlib import asynccontextmanager
import bisect
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("heatviz.api")

ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT_DIR / "web"
OUTPUT_DIR = ROOT_DIR / "data" / "output"
LAYERS_DIR = OUTPUT_DIR / "layers"

LAYER_NAMES = {
    "ai_heat_exposure_blocks",
    "social_sensitivity_blocks",
    "cooling_deficit_blocks",
    "ndvi_blocks",
    "ndbi_blocks",
    "building_density_blocks",
    "population_density_blocks",
}

# In-memory fast cache for block lookups and settlement statistics
blocks_db: Dict[str, Dict[str, Any]] = {}
all_hvi_scores: List[int] = []
total_blocks_count: int = 0


def load_dataset_into_memory() -> None:
    """Loads vulnerability blocks GeoJSON into memory and precomputes benchmark distributions."""
    global blocks_db, all_hvi_scores, total_blocks_count
    geojson_path = OUTPUT_DIR / "vulnerability_blocks.geojson"
    if not geojson_path.is_file():
        logger.warning(f"Primary GeoJSON not found at {geojson_path}")
        return

    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        features = data.get("features", [])
        blocks_db.clear()
        scores = []

        for feature in features:
            props = feature.get("properties", {})
            block_id = props.get("block_id")
            if block_id:
                blocks_db[block_id] = props
                scores.append(props.get("hvi_score", 0))

        all_hvi_scores = sorted(scores)
        total_blocks_count = len(blocks_db)
        logger.info(f"Loaded {total_blocks_count} blocks into in-memory database successfully.")
    except Exception as e:
        logger.error(f"Failed to load blocks into memory: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dataset_into_memory()
    yield
    blocks_db.clear()
    all_hvi_scores.clear()


app = FastAPI(
    title="HeatViz Climate Intelligence API",
    description="Hyperlocal Urban Heat Vulnerability Platform for Kibera",
    version="2.0.0",
    lifespan=lifespan,
)

# Enable Gzip compression middleware (90% bandwidth reduction on GeoJSON)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Mount static web frontend files
app.mount("/static", StaticFiles(directory=WEB_DIR, check_dir=False), name="static")


def geojson_response(path: Path) -> FileResponse:
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"GeoJSON not found: {path.name}")
    return FileResponse(path, media_type="application/geo+json")


@app.get("/")
def index() -> FileResponse:
    index_path = WEB_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="web/index.html not found")
    return FileResponse(index_path, media_type="text/html")


@app.get("/data/vulnerability_blocks.geojson")
def vulnerability_blocks() -> FileResponse:
    return geojson_response(OUTPUT_DIR / "vulnerability_blocks.geojson")


@app.get("/data/layers/{name}.geojson")
def layer(name: str) -> FileResponse:
    if name not in LAYER_NAMES:
        raise HTTPException(status_code=404, detail=f"Unknown layer: {name}")
    return geojson_response(LAYERS_DIR / f"{name}.geojson")


# ==============================================================================
# Rule-Based Expert Intelligence Engine
# ==============================================================================

# ==============================================================================
# Rule-Based Expert Intelligence Engine
# ==============================================================================

def calculate_percentile(score: int) -> int:
    """Calculates the percentile rank of an HVI score relative to the entire settlement."""
    if not all_hvi_scores or total_blocks_count == 0:
        return 50
    pos = bisect.bisect_right(all_hvi_scores, score)
    return min(99, max(1, int(round((pos / total_blocks_count) * 100))))


def evaluate_microclimate_diagnosis(props: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs multi-dimensional microclimate diagnosis using remote sensing and demographic indices.
    """
    hvi = props.get("hvi_score", 0)
    heat = props.get("ai_heat_exposure", 0)
    ndvi = props.get("ndvi", 50)
    ndbi = props.get("ndbi", 50)
    cooling = props.get("cooling_deficit", 50)
    pop = props.get("estimated_population", 0)
    pop_dens = props.get("population_density", 0)
    bld_dens = props.get("building_density", 0)
    dist_green = props.get("distance_to_green", 0)
    dist_water = props.get("distance_to_water", 0)
    risk_class = props.get("risk_class", "Medium")

    is_safe = (risk_class.lower() == "low") or (hvi < 30)

    # 1. Safe / Resilient Sector Profile
    if is_safe:
        return {
            "is_safe": True,
            "status_label": "Optimal Baseline",
            "archetype_title": "Vegetated Microclimate Buffer",
            "headline": "This sector is within safe thermal and environmental thresholds",
            "diagnosis": f"This 50-meter sector maintains active microclimate buffering. With healthy vegetative canopy (NDVI: {ndvi}/100) and low heat-trapping mass ({ndbi}/100), ambient ground temperatures remain well within safe ranges for its ~{pop} residents.",
            "causes": [],
            "actions": [
                "Preserve and protect existing mature tree canopy and permeable ground surfaces.",
                "Maintain unblocked drainage corridors to support continuous natural soil moisture.",
            ],
            "key_metrics": {
                "canopy_status": "Sufficient / Protective",
                "thermal_status": "Temperate Baseline",
                "roof_status": "Low Thermal Mass",
            },
        }

    # 2. High or Critical Risk Profile
    causes = []
    actions = []

    # Identify primary physical mechanisms
    if ndbi >= 60:
        causes.append("Dense corrugated galvanized iron roofs trapping and re-radiating intense solar heat")
    if ndvi <= 30:
        causes.append("Severe lack of tree canopy and shaded pedestrian corridors (0–10% effective canopy)")
    elif ndvi <= 45:
        causes.append("Insufficient vegetative shade along primary walking alleys")

    if heat >= 65:
        causes.append(f"Elevated radiant surface temperature (Downscaled Heat Index: {heat}/100)")

    if dist_green > 150:
        causes.append(f"Isolated from public green spaces (Nearest open green park: ~{int(dist_green)}m)")
    elif cooling >= 60:
        causes.append("High walking distance to public cooling hubs and vegetated buffers")

    if pop >= 60 or pop_dens >= 60:
        causes.append(f"High demographic exposure with approximately {pop} residents living in this 50m cell")

    if bld_dens >= 60:
        causes.append("Extremely dense building layout creating narrow alleys with restricted natural cross-ventilation")

    if not causes:
        causes.append("Compound thermal accumulation across mixed impervious built surfaces")

    # Construct prioritized multi-tier actions
    if hvi >= 76:
        archetype_title = "Critical Thermal Trap & High-Density Settlement"
        headline = "Acute heat vulnerability requiring immediate and structural mitigation"
        actions.append("Emergency (0–48h): Deploy mobile shaded hydration points and cooling mist stations along central pathways.")
        actions.append("Infrastructure (1–6mo): Apply high-albedo solar-reflective white coatings (cool roofs) to reduce indoor temperatures by 3–5°C.")
        actions.append("Ecological (6–24mo): Plant fast-growing native canopy trees (Acacia xanthophloea, Neem) and establish street-side bioswales.")
    elif hvi >= 56:
        archetype_title = "Dense Built Corridor with Thermal Accumulation"
        headline = "Elevated surface heat with notable shade and cooling access deficits"
        actions.append("Preparedness (Seasonal): Issue community heat-health bulletins and coordinate public water kiosk hours.")
        actions.append("Infrastructure (1–6mo): Retrofit metal roofing with reflective coatings and install fabric walkway awnings.")
        actions.append("Ecological (6–24mo): Establish continuous tree-shaded corridors along pedestrian thoroughfares.")
    else:
        archetype_title = "Moderate Exposure Residential Sector"
        headline = "Moderate thermal exposure with localized midday peak heat"
        actions.append("Urban Forestry: Plant localized shade trees and maintain household pocket greenery.")
        actions.append("Maintenance: Keep public water access points functional and sustain permeable soils.")

    return {
        "is_safe": False,
        "status_label": f"{risk_class} Risk",
        "archetype_title": archetype_title,
        "headline": headline,
        "diagnosis": f"Houses approximately {pop} residents under elevated thermal stress. The microclimate is characterized by high surface heating ({heat}/100) and an acute canopy deficit ({ndvi}/100), placing this sector in the top {max(1, 100 - calculate_percentile(hvi))}% most vulnerable areas in Kibera.",
        "causes": causes,
        "actions": actions,
        "key_metrics": {
            "canopy_status": "Severe Deficit" if ndvi < 30 else "Sparse Cover",
            "thermal_status": "Extreme Load" if heat >= 70 else "Elevated Heat",
            "roof_status": "High Thermal Mass" if ndbi >= 60 else "Moderate Cover",
        },
    }


def format_humanized_factors(props: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Translates raw sensor & model metrics into human-understandable cards with status indicators."""
    heat = props.get("ai_heat_exposure", 0)
    ndvi = props.get("ndvi", 0)
    ndbi = props.get("ndbi", 0)
    cooling = props.get("cooling_deficit", 0)
    pop_dens = props.get("population_density", 0)

    # Surface heat
    if heat >= 75:
        heat_status, heat_color = "High Thermal Load", "critical"
    elif heat >= 55:
        heat_status, heat_color = "Elevated Surface Heat", "elevated"
    elif heat >= 35:
        heat_status, heat_color = "Moderate Temperature", "moderate"
    else:
        heat_status, heat_color = "Temperate Baseline", "optimal"

    # Greenery (Higher NDVI is good)
    if ndvi >= 65:
        green_status, green_color = "Dense Canopy Cover", "optimal"
    elif ndvi >= 45:
        green_status, green_color = "Moderate Vegetation", "moderate"
    elif ndvi >= 25:
        green_status, green_color = "Sparse Canopy", "elevated"
    else:
        green_status, green_color = "Critical Canopy Deficit", "critical"

    # Built surfaces (NDBI)
    if ndbi >= 70:
        built_status, built_color = "High Impervious Density", "critical"
    elif ndbi >= 50:
        built_status, built_color = "Elevated Built Cover", "elevated"
    elif ndbi >= 30:
        built_status, built_color = "Mixed Permeable Ground", "moderate"
    else:
        built_status, built_color = "Predominantly Open Ground", "optimal"

    # Cooling access deficit (Lower deficit is good)
    if cooling >= 65:
        cool_status, cool_color = "Isolated from Buffers", "critical"
    elif cooling >= 45:
        cool_status, cool_color = "Moderate Buffer Distance", "elevated"
    elif cooling >= 25:
        cool_status, cool_color = "Proximity to Water/Green", "moderate"
    else:
        cool_status, cool_color = "Direct Buffer Access", "optimal"

    # Population density
    if pop_dens >= 70:
        pop_status, pop_color = "High Resident Density", "critical"
    elif pop_dens >= 40:
        pop_status, pop_color = "Moderate Resident Density", "elevated"
    else:
        pop_status, pop_color = "Low Density / Open", "moderate"

    return [
        {
            "id": "surface_heat",
            "name": "Surface Heat Exposure",
            "score": heat,
            "status": heat_status,
            "color": heat_color,
            "desc": "Radiant ground-level thermal intensity derived from 50m graph attention downscaling.",
        },
        {
            "id": "greenery",
            "name": "Tree Canopy & Greenery",
            "score": ndvi,
            "status": green_status,
            "color": green_color,
            "desc": "Tree canopy and vegetation density offering natural shading and evaporative cooling.",
        },
        {
            "id": "built_surfaces",
            "name": "Tin Roofs & Impervious Mass",
            "score": ndbi,
            "status": built_status,
            "color": built_color,
            "desc": "Concentration of high-heat-capacity metal roofing, concrete, and asphalt surfaces.",
        },
        {
            "id": "cooling_access",
            "name": "Access to Cooling Assets",
            "score": 100 - cooling,
            "status": cool_status,
            "color": cool_color,
            "desc": "Walking proximity to public green spaces, natural water bodies, and drainage corridors.",
        },
        {
            "id": "crowding",
            "name": "Demographic Exposure",
            "score": pop_dens,
            "status": pop_status,
            "color": pop_color,
            "desc": "Relative population density and resident exposure concentration within this 50m sector.",
        },
    ]


@app.get("/api/blocks/{block_id}")
def get_block_intelligence(block_id: str) -> JSONResponse:
    """
    Returns an advanced, rule-based climate intelligence profile for a 50m sector.
    Includes physical microclimate diagnostics, 3-tier action plans, and safe/risk dual states.
    """
    props = blocks_db.get(block_id)
    if not props:
        if not blocks_db:
            load_dataset_into_memory()
            props = blocks_db.get(block_id)
        if not props:
            raise HTTPException(status_code=404, detail=f"Block {block_id} not found in database.")

    hvi_score = props.get("hvi_score", 0)
    risk_class = props.get("risk_class", "Medium")
    pop = props.get("estimated_population", 0)

    # 1. Percentile Rank
    percentile = calculate_percentile(hvi_score)

    # 2. Comprehensive Diagnosis
    diag = evaluate_microclimate_diagnosis(props)

    # 3. Factor Indicators
    factors = format_humanized_factors(props)

    payload = {
        "block_id": block_id,
        "risk_class": risk_class,
        "is_safe": diag["is_safe"],
        "status_label": diag["status_label"],
        "archetype_title": diag["archetype_title"],
        "hvi_score": hvi_score,
        "percentile": percentile,
        "population": pop,
        "headline": diag["headline"],
        "summary": diag["diagnosis"],
        "key_causes": diag["causes"],
        "key_actions": diag["actions"],
        "key_metrics": diag["key_metrics"],
        "factors": factors,
        "raw_properties": {
            "ai_heat_exposure": props.get("ai_heat_exposure", 0),
            "cooling_deficit": props.get("cooling_deficit", 0),
            "ndvi": props.get("ndvi", 0),
            "ndbi": props.get("ndbi", 0),
            "population_density": props.get("population_density", 0),
            "distance_to_green": props.get("distance_to_green", 0),
            "distance_to_water": props.get("distance_to_water", 0),
        },
    }

    return JSONResponse(content=payload)


