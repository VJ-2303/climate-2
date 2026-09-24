"""
HeatViz Climate Intelligence API
FastAPI backend serving GeoJSON layers and hyperlocal microclimate intelligence for Madurai.
"""

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.rules import build_block_intelligence

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("heatviz.api")

ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT_DIR / "web"
OUTPUT_DIR = ROOT_DIR / "data" / "output"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
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

# In-memory fast cache for block lookups, 2D spatial grid, settlement statistics, layer attributes, and SHAP explainability
blocks_db: Dict[str, Dict[str, Any]] = {}
shap_db: Dict[str, Dict[str, Any]] = {}
block_to_grid: Dict[str, Tuple[int, int]] = {}
grid_to_block: Dict[Tuple[int, int], str] = {}
layer_attributes_cache: Dict[str, Dict[str, float]] = {}
all_hvi_scores: List[int] = []
total_blocks_count: int = 0


def load_dataset_into_memory() -> None:
    """Loads vulnerability blocks GeoJSON into memory, creates 2D spatial grid, and precomputes benchmark distributions."""
    global blocks_db, shap_db, block_to_grid, grid_to_block, all_hvi_scores, total_blocks_count, layer_attributes_cache
    geojson_path = OUTPUT_DIR / "vulnerability_blocks.geojson"
    processed_path = PROCESSED_DIR / "madurai_blocks_50m.geojson"
    shap_path = PROCESSED_DIR / "block_shap_explanations.json"

    if not geojson_path.is_file():
        logger.warning(f"Primary GeoJSON not found at {geojson_path}")
        return

    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        features = data.get("features", [])
        blocks_db.clear()
        block_to_grid.clear()
        grid_to_block.clear()
        layer_attributes_cache.clear()
        scores = []

        for feature in features:
            props = feature.get("properties", {})
            block_id = props.get("block_id")
            if block_id:
                blocks_db[block_id] = props
                scores.append(props.get("hvi_score", 0))

        # Index grid coordinates and physical temperature for spatial 8-neighbor queries
        if processed_path.is_file():
            try:
                with open(processed_path, "r", encoding="utf-8") as pf:
                    pdata = json.load(pf)
                for pfeat in pdata.get("features", []):
                    pprops = pfeat.get("properties", {})
                    pbid = pprops.get("block_id")
                    gi = pprops.get("grid_i")
                    gj = pprops.get("grid_j")
                    if pbid and gi is not None and gj is not None:
                        block_to_grid[pbid] = (gi, gj)
                        grid_to_block[(gi, gj)] = pbid
                    if pbid and pbid in blocks_db:
                        if "mean_landsat_st_celsius" in pprops:
                            blocks_db[pbid]["mean_landsat_st_celsius"] = float(pprops["mean_landsat_st_celsius"])
            except Exception as pe:
                logger.warning(f"Could not load processed grid index: {pe}")

        # Precompute attribute-only maps for ultra-fast sub-layer switching
        for layer_name in LAYER_NAMES:
            layer_file = LAYERS_DIR / f"{layer_name}.geojson"
            if layer_file.is_file():
                try:
                    with open(layer_file, "r", encoding="utf-8") as lf:
                        ldata = json.load(lf)
                    prop_name = layer_name.replace("_blocks", "")
                    attr_map = {}
                    for feat in ldata.get("features", []):
                        fprops = feat.get("properties", {})
                        fbid = fprops.get("block_id")
                        if fbid and prop_name in fprops:
                            attr_map[fbid] = fprops[prop_name]
                    layer_attributes_cache[layer_name] = attr_map
                except Exception as le:
                    logger.warning(f"Could not precompute attributes for {layer_name}: {le}")

        # Load SHAP explainability cache
        shap_db.clear()
        if shap_path.is_file():
            try:
                with open(shap_path, "r", encoding="utf-8") as sf:
                    shap_db.update(json.load(sf))
                logger.info(f"Loaded {len(shap_db)} block SHAP explanations successfully.")
            except Exception as se:
                logger.warning(f"Could not load SHAP explanations: {se}")

        all_hvi_scores = sorted(scores)
        total_blocks_count = len(blocks_db)
        logger.info(f"Loaded {total_blocks_count} blocks and {len(layer_attributes_cache)} layer attribute caches successfully.")
    except Exception as e:
        logger.error(f"Failed to load blocks into memory: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dataset_into_memory()
    yield
    blocks_db.clear()
    shap_db.clear()
    block_to_grid.clear()
    grid_to_block.clear()
    layer_attributes_cache.clear()
    all_hvi_scores.clear()


app = FastAPI(
    title="HeatViz Climate Intelligence API",
    description="Hyperlocal Urban Heat Vulnerability Platform for Madurai",
    version="2.0.0",
    lifespan=lifespan,
)

# Enable Gzip compression middleware (88% bandwidth reduction on GeoJSON)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# HTTP Caching Middleware for static files and GeoJSON responses
@app.middleware("http")
async def add_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.endswith((".geojson", ".js", ".css", ".png", ".svg", ".woff2", ".ttf")):
        response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=3600"
    return response


# Mount static web frontend files
app.mount("/static", StaticFiles(directory=WEB_DIR, check_dir=False), name="static")


def geojson_response(path: Path) -> FileResponse:
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"GeoJSON not found: {path.name}")
    return FileResponse(
        path,
        media_type="application/geo+json",
        headers={"Cache-Control": "public, max-age=86400, stale-while-revalidate=3600"},
    )


@app.get("/")
@app.get("/officer")
def officer_view() -> FileResponse:
    officer_path = WEB_DIR / "officer.html"
    if not officer_path.is_file():
        officer_path = WEB_DIR / "index.html"
    if not officer_path.is_file():
        raise HTTPException(status_code=404, detail="Officer dashboard HTML not found")
    return FileResponse(officer_path, media_type="text/html")


@app.get("/public")
def public_view() -> FileResponse:
    """Serves the citizen-facing public heat safety portal."""
    public_path = WEB_DIR / "public.html"
    if not public_path.is_file():
        raise HTTPException(status_code=404, detail="Public portal HTML not found")
    return FileResponse(public_path, media_type="text/html")


@app.post("/api/alerts/dispatch")
async def dispatch_sms_alert(payload: Dict[str, Any]) -> JSONResponse:
    """Simulates targeted SMS emergency advisory dispatch to residents in a specific sector."""
    import uuid
    from datetime import datetime

    block_id = payload.get("block_id", "KIB-0000")
    recipient_group = payload.get("recipient_group", "vulnerable_residents")
    message = payload.get("message", "High heat advisory. Maintain hydration.")

    block_props = blocks_db.get(block_id, {})
    pop = int(block_props.get("estimated_population", 250))
    recipients_count = max(15, pop)

    audit_entry = {
        "status": "dispatched",
        "audit_id": f"DISP-{uuid.uuid4().hex[:8].upper()}",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "block_id": block_id,
        "recipient_group": recipient_group,
        "recipients_count": recipients_count,
        "message": message,
        "channels": ["SMS (TNSDMA Common Alerting Protocol / BSNL)", "WhatsApp Emergency Broadcast", "Ward Health Volunteers / UPHC Outreach", "108 Emergency Ambulance Staging"]
    }
    logger.info(f"Dispatched SMS emergency advisory: {audit_entry['audit_id']} to {recipients_count} recipients in {block_id}")
    return JSONResponse(content=audit_entry)


@app.get("/data/vulnerability_blocks.geojson")
def vulnerability_blocks() -> FileResponse:
    return geojson_response(OUTPUT_DIR / "vulnerability_blocks.geojson")


@app.get("/data/layers/{name}.geojson")
def layer(name: str) -> FileResponse:
    if name not in LAYER_NAMES:
        raise HTTPException(status_code=404, detail=f"Unknown layer: {name}")
    return geojson_response(LAYERS_DIR / f"{name}.geojson")


@app.get("/api/layers/forecast_day_{day}/attributes")
def get_forecast_day_attributes(day: int) -> JSONResponse:
    """Returns day-specific physiological heat risk scores (0..100) across all blocks for map day-scrubber."""
    if day < 1 or day > 5:
        raise HTTPException(status_code=400, detail="Forecast day must be between 1 and 5")

    if not blocks_db:
        load_dataset_into_memory()

    from api.weather import get_5day_forecast
    forecast = get_5day_forecast()
    daily = forecast.get("daily", [])
    day_item = next((d for d in daily if d.get("day") == day), daily[0] if daily else {})
    base_wbgt = float(day_item.get("wbgt_max", 30.0))

    attr_map = {}
    for bid, props in blocks_db.items():
        anomaly = float(props.get("temp_anomaly_celsius", 0.0))
        pop_norm = float(props.get("population_density", 50.0))
        bldg_norm = float(props.get("building_density", 50.0))
        local_wbgt = base_wbgt + (anomaly * 0.4)
        base_score = min(100.0, max(0.0, (local_wbgt - 28.0) * 10.0))
        risk_score = int(round(min(100.0, max(0.0, base_score * 0.75 + (pop_norm * 0.15) + (bldg_norm * 0.10)))))
        attr_map[bid] = risk_score

    return JSONResponse(
        content=attr_map,
        headers={"Cache-Control": "public, max-age=1800"}
    )


@app.get("/api/layers/{name}/attributes")
def layer_attributes(name: str) -> JSONResponse:
    """Returns lightweight key-value dictionary {block_id: score} for ultra-fast in-place layer switching."""
    if name not in LAYER_NAMES:
        raise HTTPException(status_code=404, detail=f"Unknown layer: {name}")
    attr_map = layer_attributes_cache.get(name)
    if not attr_map:
        prop_name = name.replace("_blocks", "")
        layer_file = LAYERS_DIR / f"{name}.geojson"
        if not layer_file.is_file():
            raise HTTPException(status_code=404, detail=f"Layer file not found: {name}")
        with open(layer_file, "r", encoding="utf-8") as f:
            ldata = json.load(f)
        attr_map = {feat["properties"]["block_id"]: feat["properties"].get(prop_name, 0) for feat in ldata.get("features", [])}
        layer_attributes_cache[name] = attr_map

    return JSONResponse(
        content=attr_map,
        headers={"Cache-Control": "public, max-age=86400, stale-while-revalidate=3600"},
    )


@app.get("/api/blocks/{block_id}")
def get_block_intelligence(block_id: str) -> JSONResponse:
    """
    Returns an advanced, rule-based climate intelligence profile for a 50m sector.
    Includes 3 dedicated physical sections:
    1. Area Description & Land-Cover Profile
    2. Thermal Analysis & Exact Why-It-Is-Hot Root Causes
    3. Required Things to Control It (Targeted Interventions & Material Estimates)
    """
    props = blocks_db.get(block_id)
    if not props:
        if not blocks_db:
            load_dataset_into_memory()
            props = blocks_db.get(block_id)
        if not props:
            raise HTTPException(status_code=404, detail=f"Block {block_id} not found in database.")

    shap_info = shap_db.get(block_id, {})
    shap_factors = shap_info.get("factors", [])

    payload = build_block_intelligence(
        block_id=block_id,
        props=props,
        all_scores=all_hvi_scores,
        block_to_grid=block_to_grid,
        grid_to_block=grid_to_block,
        blocks_db=blocks_db,
        shap_factors=shap_factors,
    )

    # Attach explainable AI (SHAP) feature attributions (top 3 per SIH26083 plan 2.3)
    payload["shap_factors"] = shap_factors[:3]
    payload["shap_base_temp"] = shap_info.get("base_value", 49.59)

    return JSONResponse(
        content=payload,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/api/forecast/summary")
def get_forecast_summary() -> JSONResponse:
    """Returns 5-day heatwave forecast, WBGT thermal stress indices, and macro settlement advisory."""
    from api.weather import get_5day_forecast
    data = get_5day_forecast()
    return JSONResponse(content=data, headers={"Cache-Control": "public, max-age=1800"})


@app.get("/api/forecast/days")
def get_forecast_days() -> JSONResponse:
    """Returns lightweight 5-day timeline for map scrubber controls and real-time current weather."""
    from api.weather import get_5day_forecast
    data = get_5day_forecast()
    days = [
        {
            "day": d["day"],
            "date": d["date"],
            "temp_max": d["temp_max"],
            "temp_min": d.get("temp_min"),
            "humidity_mean": d["humidity_mean"],
            "wbgt_max": d["wbgt_max"],
            "risk_tier": d["risk_tier"]
        }
        for d in data.get("daily", [])
    ]
    return JSONResponse(
        content={
            "days": days,
            "current": data.get("current")
        },
        headers={"Cache-Control": "public, max-age=1800"}
    )

