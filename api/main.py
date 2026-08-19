from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


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

app = FastAPI(title="HeatViz")
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
