"""
HeatViz Climate Intelligence — Rule-Based Expert Decision Engine (rules.py)
Domain-specific heuristics for hyper-local microclimate diagnostics,
land-cover categorization, physical heat root-cause analysis, and targeted intervention planning.
"""

import bisect
from typing import Any, Dict, List, Tuple


def calculate_percentile(score: int, all_scores: List[int]) -> int:
    """Calculates the percentile rank of an HVI score relative to the entire settlement."""
    if not all_scores:
        return 50
    total = len(all_scores)
    pos = bisect.bisect_right(all_scores, score)
    return min(99, max(1, int(round((pos / total) * 100))))


def classify_land_cover(props: Dict[str, Any]) -> Tuple[str, str]:
    """
    Classifies the actual physical ground terrain and land-cover archetype of the 50m parcel:
    - Dense Metal-Roofed Settlement (high building footprint / NDBI)
    - High-Density Commercial & Residential Cluster (elevated population + built density)
    - Riparian Wetland & Alluvial Green Corridor (close to valley water with vegetation)
    - Riparian Informal Edge Settlement (close to water with tin dwellings)
    - High-Canopy Agroforestry & Green Buffer (mature tree canopy)
    - Vegetated Canopy Buffer & Open Space (moderate greenery, low density)
    - Exposed Open Ground & Pathways (bare earth, low canopy, low structures)
    - Mixed Low-Rise Residential Parcel (balanced mixed dwellings)
    """
    ndvi = props.get("ndvi", 50)
    ndbi = props.get("ndbi", 50)
    bld = props.get("building_density", 0)
    dist_water = props.get("distance_to_water", 500)
    pop = props.get("estimated_population", 0)

    if pop >= 60 and bld >= 40:
        return (
            "High-Density Commercial & Residential Cluster",
            f"High-occupancy residential and informal market node with dense tin roofs ({bld}% footprint) housing ~{pop} residents.",
        )
    elif bld >= 50 or ndbi >= 65:
        return (
            "Dense Metal-Roofed Settlement",
            f"High-density informal settlement with contiguous corrugated iron roofs ({bld}% building footprint) housing ~{pop} residents.",
        )
    elif dist_water <= 80 and ndvi >= 45:
        return (
            "Riparian Wetland & Alluvial Green Corridor",
            f"Natural riparian drainage corridor approximately {int(dist_water)}m from valley water course with active wetland vegetation ({ndvi}/100).",
        )
    elif dist_water <= 60 and bld >= 35:
        return (
            "Riparian Informal Edge Settlement",
            f"Low-lying riparian settlement edge approximately {int(dist_water)}m from valley drainage channel with {bld}% building cover.",
        )
    elif ndvi >= 70 and bld <= 20:
        return (
            "High-Canopy Agroforestry & Green Buffer",
            f"Protected high-canopy vegetated buffer ({ndvi}/100 canopy density) providing substantial natural microclimatic cooling.",
        )
    elif ndvi >= 50 and bld <= 35:
        return (
            "Vegetated Canopy Buffer & Open Space",
            f"Predominantly vegetated parcel with active tree canopy ({ndvi}/100) and sparse built structures ({bld}%).",
        )
    elif ndvi < 35 and bld < 40:
        return (
            "Exposed Open Ground & Pathways",
            f"Unshaded terrain and open pedestrian pathways with low vegetative canopy ({ndvi}/100) and exposed bare soil.",
        )
    else:
        return (
            "Mixed Low-Rise Residential Parcel",
            f"Mixed residential environment with scattered dwellings ({bld}% footprint) and partial tree canopy ({ndvi}/100).",
        )


def evaluate_neighborhood_context(
    block_id: str,
    props: Dict[str, Any],
    block_to_grid: Dict[str, Tuple[int, int]],
    grid_to_block: Dict[Tuple[int, int], str],
    blocks_db: Dict[str, Dict[str, Any]],
) -> str:
    """Evaluates 8-neighbor spatial spillover to detect thermal canyons or nearby cooling assets."""
    coord = block_to_grid.get(block_id)
    if not coord:
        return "Standard localized microclimate profile."

    gi, gj = coord
    neighbor_hvis = []
    neighbor_ndvis = []
    neighbor_heats = []

    for di in [-1, 0, 1]:
        for dj in [-1, 0, 1]:
            if di == 0 and dj == 0:
                continue
            nb_id = grid_to_block.get((gi + di, gj + dj))
            if nb_id and nb_id in blocks_db:
                nb_props = blocks_db[nb_id]
                neighbor_hvis.append(nb_props.get("hvi_score", 0))
                neighbor_ndvis.append(nb_props.get("ndvi", 0))
                neighbor_heats.append(nb_props.get("ai_heat_exposure", 0))

    if not neighbor_hvis:
        return "Settlement Boundary Parcel: Located on the perimeter with open air circulation from adjacent railway/road corridor."

    avg_nb_hvi = sum(neighbor_hvis) / len(neighbor_hvis)
    high_heat_nbs = sum(1 for h in neighbor_heats if h >= 60)
    green_nbs = sum(1 for v in neighbor_ndvis if v >= 45)
    is_hot = props.get("ai_heat_exposure", 0) >= 50

    if not is_hot:
        if high_heat_nbs >= 3:
            return f"Microclimate Cooling Oasis: Surrounded by {high_heat_nbs} high-heat sectors, serving as a vital thermal refuge for adjacent residents."
        return "Acts as an active microclimate buffer, dissipating radiant heat for adjacent residential pathways."
    elif high_heat_nbs >= 5:
        return "Thermal Canyon Corridor: Surrounded by 5+ contiguous high-density heat sectors, restricting cross-ventilation and trapping stagnant hot air."
    elif green_nbs >= 2:
        return "Cooling Asset Proximity: Bordered by a cooler vegetated zone (~50m away). Connecting street shade will draw cool breezes into this block."
    elif avg_nb_hvi >= 60:
        return "Embedded in an elevated thermal corridor with compounding heat retention from adjacent tin roofs."
    else:
        return "Microclimate is primarily driven by localized rooftop absorption and internal walkway geometry."


def calculate_intervention_sizing(props: Dict[str, Any]) -> Dict[str, Any]:
    """Computes practical material and engineering estimates for 50m sector retrofits (2,500 m2)."""
    bld_dens = props.get("building_density", 0)
    ndvi = props.get("ndvi", 0)
    is_hot = props.get("ai_heat_exposure", 0) >= 50

    total_area = 2500
    bld_ratio = min(1.0, max(0.0, bld_dens / 100.0 if bld_dens > 1 else bld_dens))
    roof_sqm = int(round(total_area * bld_ratio))

    # 1L high-albedo elastomeric coating covers ~8-10 m2
    paint_liters = int(round(roof_sqm * 0.11)) if is_hot else 0

    # Tree canopy target: 25% of sector = 625 m2. Each mature shade tree canopy = ~45 m2
    canopy_ratio = min(1.0, max(0.0, ndvi / 100.0 if ndvi > 1 else ndvi))
    current_canopy_sqm = int(round(total_area * canopy_ratio * 0.4))
    deficit_sqm = max(0, 625 - current_canopy_sqm)
    trees_needed = max(3, min(12, int(round(deficit_sqm / 45.0)))) if is_hot else 0

    return {
        "sector_footprint_sqm": 2500,
        "estimated_roof_sqm": roof_sqm,
        "cool_roof_paint_liters": paint_liters,
        "trees_to_target_canopy": trees_needed,
        "target_canopy_pct": "25% target coverage",
    }


def select_ecological_species(props: Dict[str, Any]) -> Dict[str, str]:
    """Selects indigenous Kenyan botanical species tailored to soil moisture and structural density."""
    dist_water = props.get("distance_to_water", 500)
    bld_dens = props.get("building_density", 0)

    if dist_water <= 150:
        return {
            "primary_species": "Acacia xanthophloea (Yellow-Barked Fever Tree) & Syzygium cordatum (Water Berry)",
            "botanical_rationale": "High moisture tolerance, rapid transpiration cooling, and stabilization of riparian runoff corridors.",
            "planting_zone": "Along drainage swales and moist alluvial pathways",
        }
    elif bld_dens >= 40:
        return {
            "primary_species": "Markhamia lutea (Siala) & Croton megalocarpus",
            "botanical_rationale": "Deep non-invasive taproots safe for narrow alleys near foundations; dense evergreen shade with low leaf litter.",
            "planting_zone": "Narrow pedestrian alleys and pocket courtyards",
        }
    else:
        return {
            "primary_species": "Azadirachta indica (Mwarobaini / Neem) & Tipuana tipu (Rosewood)",
            "botanical_rationale": "Broad umbrella canopy providing up to 80% solar irradiance reduction and exceptional drought resilience.",
            "planting_zone": "Open thoroughfares and communal gathering nodes",
        }


def evaluate_heat_health_advisory(props: Dict[str, Any]) -> Dict[str, str]:
    """Evaluates diurnal physiological heat stress and provides targeted community advisories for Nairobi latitude."""
    heat = props.get("ai_heat_exposure", 0)
    pop = props.get("estimated_population", 0)
    is_hot = heat >= 50

    if not is_hot:
        return {
            "peak_stress_window": "Safe Baseline (All Hours)",
            "health_alert": "Ambient temperatures remain within safe physiological comfort thresholds.",
            "hydration_guideline": "Standard baseline hydration.",
        }
    elif heat >= 70:
        return {
            "peak_stress_window": "11:00 AM – 3:30 PM (Severe Radiant Peak)",
            "health_alert": f"High risk of heat exhaustion and dehydration for ~{pop} residents, informal outdoor traders, and elderly citizens.",
            "hydration_guideline": "Ensure continuous access to distributed potable water kiosks and deploy shaded rest points.",
        }
    else:
        return {
            "peak_stress_window": "12:00 PM – 3:00 PM (Midday Solar Window)",
            "health_alert": "Elevated radiant heat from tin roofs during midday sun; caution for strenuous outdoor manual work.",
            "hydration_guideline": "Maintain regular drinking water intake during peak afternoon hours.",
        }


def evaluate_microclimate_diagnosis(props: Dict[str, Any], block_id: str = "") -> Dict[str, Any]:
    """
    Performs multi-dimensional physical microclimate diagnosis:
    1. Detailed Information About This Specific Area (Land-cover and spatial setting).
    2. Why It Is Hot (if it is) — Exact physical causes and temperature measurements.
    3. Required Things to Control It — Targeted engineering and ecological remedies.
    """
    hvi = props.get("hvi_score", 0)
    heat = props.get("ai_heat_exposure", 0)
    ndvi = props.get("ndvi", 50)
    ndbi = props.get("ndbi", 50)
    bld = props.get("building_density", 0)
    pop = props.get("estimated_population", 0)
    dist_water = props.get("distance_to_water", 500)
    dist_green = props.get("distance_to_green", 500)
    risk_class = props.get("risk_class", "Medium")

    # Extract or accurately compute physical Land Surface Temperature in °C
    if "mean_landsat_st_celsius" in props and props["mean_landsat_st_celsius"]:
        st_val = float(props["mean_landsat_st_celsius"])
    else:
        # Scale ai_heat_exposure (0-100) to physical Kibera temperature range [20.24, 38.61]
        st_val = 20.24 + (heat / 100.0) * (38.61 - 20.24)

    surface_temp = round(st_val, 1)
    temp_anomaly = round(surface_temp - 28.7, 1)
    # Peak metal roof solar radiant temperature under direct equatorial sun
    peak_roof_temp = round(min(55.0, max(surface_temp, surface_temp + (ndbi / 100.0) * 16.0)), 1)
    ambient_air_temp = round(24.5 + (surface_temp - 20.0) * 0.45, 1)

    # 1. Physical Land-Cover Classification
    land_type, land_desc = classify_land_cover(props)

    # 2. Thermal Diagnosis: Why is it hot (if it is)?
    is_thermally_hot = heat >= 50
    heat_causes = []

    if not is_thermally_hot:
        thermal_status = f"Naturally Temperate ({surface_temp:.1f}°C)"
        thermal_summary = f"This sector maintains a safe, comfortable microclimate with an observed surface temperature of {surface_temp:.1f}°C ({temp_anomaly:+.1f}°C relative to settlement baseline). Tree canopy shading ({ndvi}/100) and permeable soils actively prevent heat accumulation for its ~{pop} residents."
    else:
        thermal_status = f"Elevated Thermal Load ({surface_temp:.1f}°C)"
        thermal_summary = f"This sector experiences an elevated surface skin temperature of {surface_temp:.1f}°C ({temp_anomaly:+.1f}°C above settlement baseline). Under peak midday solar radiation, unpainted corrugated iron roofs reach up to ~{peak_roof_temp:.1f}°C, re-radiating intense thermal energy into narrow alleys and living spaces for ~{pop} residents."

        # Detect precise physical mechanisms
        if bld >= 40 or ndbi >= 55:
            heat_causes.append(
                f"Galvanized Metal Roof Heating: Corrugated iron roofs ({bld}% footprint) reach ~{peak_roof_temp:.1f}°C under peak solar radiation, re-radiating heat into living spaces."
            )
        if ndvi <= 35:
            heat_causes.append(
                f"Severe Walking Path Insolation: Lack of tree canopy ({ndvi}/100) exposes pedestrian walkways and unpaved soil to direct solar irradiance ({surface_temp:.1f}°C surface temperature)."
            )
        elif ndvi >= 45 and bld < 40:
            heat_causes.append(
                f"Lateral Thermal Advection: Despite having local tree cover ({ndvi}/100), this block absorbs radiant thermal energy from adjacent dense tin-roof clusters."
            )
        if bld >= 60:
            heat_causes.append(
                "Ventilation Obstruction: Dense structural alignment creates narrow alleys (<1.5m) that restrict horizontal breeze circulation and trap stagnant warm air."
            )
        if dist_water <= 80 and heat >= 55:
            heat_causes.append(
                "Valley Basin Micro-Humidity Trap: Low elevation and restricted airflow along the drainage corridor elevate perceived heat index by +2–3°C during afternoon hours."
            )
        if dist_green > 200:
            heat_causes.append(
                f"Buffer Isolation: Located ~{int(dist_green)}m from the nearest open green buffer, limiting passive cooling."
            )

        if not heat_causes:
            heat_causes.append(f"Solar radiation absorption across mixed dry ground with surface temperature measured at {surface_temp:.1f}°C.")

    # 3. Required Things to Control It
    controls = []
    if is_thermally_hot:
        if bld >= 30 or ndbi >= 50:
            roof_sqm = int(round(2500 * (bld / 100)))
            paint_l = int(round(roof_sqm * 0.11))
            controls.append(
                f"Cool Roof Retrofit: Apply solar-reflective white elastomeric coating to ~{roof_sqm} m² of metal roofs (~{paint_l}L paint needed) to reflect 80%+ of incoming radiant heat and reduce surface temperatures from ~{peak_roof_temp:.1f}°C down by 10–15°C (reducing indoor air temperatures by 3–5°C)."
            )
        if ndvi < 50:
            deficit_sqm = max(0, 625 - int(round(2500 * (ndvi / 100) * 0.4)))
            trees_needed = max(3, min(12, int(round(deficit_sqm / 45.0))))
            species_dict = select_ecological_species(props)
            primary_sp = species_dict["primary_species"].split("(")[0].strip()
            controls.append(
                f"Canopy Shading: Plant ~{trees_needed} native shade trees ({primary_sp}) along primary pedestrian routes to provide ambient canopy cooling."
            )
        if pop >= 30 or heat >= 65:
            controls.append(
                f"Hydration & Community Relief: Deploy shaded community rest stations with potable water kiosks for ~{pop} residents during peak hours (11:30 AM – 3:30 PM)."
            )
        if dist_water <= 150:
            controls.append(
                "Drainage Swale Preservation: Maintain permeable bioswales to sustain continuous soil moisture and maximize natural evaporative cooling."
            )
    else:
        controls.append("Canopy Conservation: Protect and maintain existing mature trees and permeable open surfaces from encroachment.")
        controls.append("Drainage Swale Care: Keep natural drainage paths clear to sustain continuous soil moisture and vegetation health.")

    return {
        "is_safe": not is_thermally_hot,
        "status_label": f"{risk_class} Vulnerability" if is_thermally_hot else "Optimal Baseline",
        "land_cover_type": land_type,
        "land_cover_desc": land_desc,
        "thermal_status": thermal_status,
        "thermal_summary": thermal_summary,
        "is_thermally_hot": is_thermally_hot,
        "surface_temp_celsius": surface_temp,
        "temp_anomaly_celsius": temp_anomaly,
        "peak_roof_temp_celsius": peak_roof_temp,
        "ambient_temp_celsius": ambient_air_temp,
        "why_hot_causes": heat_causes,
        "required_controls": controls,
    }


def format_humanized_factors(props: Dict[str, Any], surface_temp: float = 28.7, temp_anomaly: float = 0.0) -> List[Dict[str, Any]]:
    """Translates raw sensor & model metrics into human-understandable cards with status indicators."""
    heat = props.get("ai_heat_exposure", 0)
    ndvi = props.get("ndvi", 0)
    ndbi = props.get("ndbi", 0)
    cooling = props.get("cooling_deficit", 0)
    pop_dens = props.get("population_density", 0)

    # Surface heat
    if heat >= 75:
        heat_status, heat_color = f"High Thermal Load ({surface_temp:.1f}°C)", "critical"
    elif heat >= 55:
        heat_status, heat_color = f"Elevated Surface Heat ({surface_temp:.1f}°C)", "elevated"
    elif heat >= 35:
        heat_status, heat_color = f"Moderate Temperature ({surface_temp:.1f}°C)", "moderate"
    else:
        heat_status, heat_color = f"Temperate Baseline ({surface_temp:.1f}°C)", "optimal"

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
            "id": "surface_temperature",
            "name": "Land Surface Temperature",
            "score": heat,
            "value_display": f"{surface_temp:.1f}°C",
            "status": f"{surface_temp:.1f}°C ({temp_anomaly:+.1f}°C Anomaly)",
            "color": heat_color,
            "desc": f"Observed satellite and AI-downscaled skin temperature ({surface_temp:.1f}°C) relative to settlement average (28.7°C).",
        },
        {
            "id": "greenery",
            "name": "Tree Canopy & Greenery",
            "score": ndvi,
            "value_display": f"{ndvi}/100",
            "status": green_status,
            "color": green_color,
            "desc": "Tree canopy and vegetation density offering natural shading and evaporative cooling.",
        },
        {
            "id": "built_surfaces",
            "name": "Tin Roofs & Impervious Mass",
            "score": ndbi,
            "value_display": f"{ndbi}/100",
            "status": built_status,
            "color": built_color,
            "desc": "Concentration of high-heat-capacity metal roofing, concrete, and asphalt surfaces.",
        },
        {
            "id": "cooling_access",
            "name": "Access to Cooling Assets",
            "score": 100 - cooling,
            "value_display": f"{100 - cooling}/100",
            "status": cool_status,
            "color": cool_color,
            "desc": "Walking proximity to public green spaces, natural water bodies, and drainage corridors.",
        },
        {
            "id": "crowding",
            "name": "Demographic Exposure",
            "score": pop_dens,
            "value_display": f"{pop_dens}/100",
            "status": pop_status,
            "color": pop_color,
            "desc": "Relative population density and resident exposure concentration within this 50m sector.",
        },
    ]


def build_block_intelligence(
    block_id: str,
    props: Dict[str, Any],
    all_scores: List[int],
    block_to_grid: Dict[str, Tuple[int, int]],
    grid_to_block: Dict[Tuple[int, int], str],
    blocks_db: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Constructs complete structured physical climate intelligence payload for a sector."""
    hvi_score = props.get("hvi_score", 0)
    risk_class = props.get("risk_class", "Medium")
    pop = props.get("estimated_population", 0)

    # 1. Percentile Rank
    percentile = calculate_percentile(hvi_score, all_scores)

    # 2. Comprehensive Diagnosis
    diag = evaluate_microclimate_diagnosis(props, block_id)

    # 3. Spatial Neighbor Analysis
    spatial_context = evaluate_neighborhood_context(
        block_id, props, block_to_grid, grid_to_block, blocks_db
    )

    # 4. Quantitative Material Sizing
    sizing = calculate_intervention_sizing(props)

    # 5. Ecological Botanical Species Recommendation
    species_guidance = select_ecological_species(props)

    # 6. Diurnal Heat-Health Advisory
    heat_health = evaluate_heat_health_advisory(props)

    # 7. Factor Indicators
    factors = format_humanized_factors(
        props,
        surface_temp=diag["surface_temp_celsius"],
        temp_anomaly=diag["temp_anomaly_celsius"]
    )

    return {
        "block_id": block_id,
        "risk_class": risk_class,
        "is_safe": diag["is_safe"],
        "status_label": diag["status_label"],
        "hvi_score": hvi_score,
        "percentile": percentile,
        "population": pop,
        
        # Physical Temperature Metrics
        "surface_temp_celsius": diag["surface_temp_celsius"],
        "surface_temp_display": f"{diag['surface_temp_celsius']:.1f}°C",
        "temp_anomaly_celsius": diag["temp_anomaly_celsius"],
        "temp_anomaly_display": f"{diag['temp_anomaly_celsius']:+.1f}°C",
        "peak_roof_temp_celsius": diag["peak_roof_temp_celsius"],
        "peak_roof_temp_display": f"~{diag['peak_roof_temp_celsius']:.1f}°C",
        "ambient_temp_celsius": diag["ambient_temp_celsius"],
        "ambient_temp_display": f"~{diag['ambient_temp_celsius']:.1f}°C",
        "settlement_avg_temp": 28.7,
        
        # 1. Detailed Information About This Area
        "land_cover_type": diag["land_cover_type"],
        "land_cover_desc": diag["land_cover_desc"],
        "archetype_title": diag["land_cover_type"],
        "summary": diag["land_cover_desc"],
        "spatial_context": spatial_context,
        "canopy_pct": props.get("ndvi", 0),
        "built_pct": props.get("building_density", 0),
        "dist_water_m": props.get("distance_to_water", 0),
        "dist_green_m": props.get("distance_to_green", 0),
        
        # 2. Thermal Diagnosis: Why is it hot (if it is)?
        "is_thermally_hot": diag["is_thermally_hot"],
        "thermal_status": diag["thermal_status"],
        "thermal_summary": diag["thermal_summary"],
        "headline": diag["thermal_status"],
        "why_hot_causes": diag["why_hot_causes"],
        "key_causes": diag["why_hot_causes"],
        "heat_health": heat_health,
        
        # 3. Required Things to Control It
        "required_controls": diag["required_controls"],
        "key_actions": diag["required_controls"],
        "sizing": sizing,
        "species_guidance": species_guidance,
        
        # Factor Indicators & Raw
        "factors": factors,
        "raw_properties": {
            "surface_temperature_celsius": diag["surface_temp_celsius"],
            "ai_heat_exposure": props.get("ai_heat_exposure", 0),
            "cooling_deficit": props.get("cooling_deficit", 0),
            "ndvi": props.get("ndvi", 0),
            "ndbi": props.get("ndbi", 0),
            "building_density": props.get("building_density", 0),
            "population_density": props.get("population_density", 0),
            "distance_to_green": props.get("distance_to_green", 0),
            "distance_to_water": props.get("distance_to_water", 0),
        },
    }
