"""
ThermalGuard Weather & WBGT Service (SIH26083)
Computes Wet-Bulb Globe Temperature (WBGT) and manages 5-day heatwave forecasting.
"""

import os
import json
import math
import time
import urllib.request
from typing import Dict, Any, Optional

DEFAULT_LAT = 9.921851
DEFAULT_LON = 78.118200
CACHE_TTL_SECONDS = 3600  # 1 hour
FALLBACK_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "fallback_forecast.json")

_CACHE: Dict[str, Any] = {
    "timestamp": 0,
    "data": None
}

def calculate_wbgt(temp_c: float, humidity_pct: float) -> float:
    """
    Calculates simplified outdoor Wet-Bulb Globe Temperature (Liljegren / Australian BOM formula).
    e: water vapor pressure (hPa)
    WBGT = 0.567 * Ta + 0.393 * e + 3.94
    """
    # Clamp humidity to valid physiological range
    rh = max(0.0, min(100.0, float(humidity_pct)))
    t = float(temp_c)
    
    # Vapor pressure in hPa
    e = (rh / 100.0) * 6.105 * math.exp((17.27 * t) / (237.7 + t))
    wbgt = 0.567 * t + 0.393 * e + 3.94
    return round(wbgt, 2)

def estimate_globe_temperature(ta_celsius: float, direct_radiation: float, wind_speed: float) -> float:
    """Estimates black globe temperature (Tg) from the globe energy balance (Liljegren 2002).

    Solves: eps*sigma*(Tg^4 - Ta^4) + h*(Tg - Ta) = (1 - alpha) * Sr / 4
    Standard 150mm matte-black globe: r=0.15m, alpha=0.05, eps=0.95.
    """
    if direct_radiation <= 0:
        return ta_celsius
    ta_k = ta_celsius + 273.15
    h = 5.65 * max(wind_speed, 0.1) ** 0.8  # convective coefficient, W/m2K
    alpha, eps, sigma = 0.05, 0.95, 5.67e-8
    absorbed = (1.0 - alpha) * direct_radiation / 4.0

    def imbalance(tg_k: float) -> float:
        return eps * sigma * (tg_k ** 4 - ta_k ** 4) + h * (tg_k - ta_k) - absorbed

    lo, hi = ta_k, ta_k + 100.0
    for _ in range(60):  # bisection — monotonic in Tg
        mid = (lo + hi) / 2.0
        if imbalance(mid) > 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0 - 273.15

def calculate_full_wbgt(temp_celsius: float, humidity_pct: float, direct_radiation: float, wind_speed: float) -> float:
    """Full ACGIH outdoor WBGT: 0.57*Tg + 0.32*ea + 0.11*Ta (solar-loaded globe temperature)."""
    ea = (humidity_pct / 100.0) * 6.105 * math.exp((17.27 * temp_celsius) / (237.7 + temp_celsius))
    tg = estimate_globe_temperature(temp_celsius, direct_radiation, wind_speed)
    return 0.57 * tg + 0.32 * ea + 0.11 * temp_celsius

def classify_wbgt_risk(wbgt: float) -> str:
    """Classifies physiological heat risk from WBGT calibrated for Indian tropical climate (IMD/NDMA standards)."""
    if wbgt > 38.0:
        return "Critical"
    elif wbgt >= 34.0:
        return "High"
    elif wbgt >= 30.0:
        return "Moderate"
    else:
        return "Low"

def classify_imd_heatwave(temp_max: float, departure: float = 0.0) -> Dict[str, Any]:
    """
    Classifies heatwave conditions according to official India Meteorological Department (IMD) criteria for plains:
    - Heatwave: Tmax >= 40.0°C and departure >= +4.5°C (or absolute Tmax >= 45.0°C)
    - Severe Heatwave: Tmax >= 40.0°C and departure >= +6.5°C (or absolute Tmax >= 47.0°C)
    """
    t = float(temp_max)
    dep = float(departure)
    if t >= 47.0 or (t >= 40.0 and dep >= 6.5):
        return {"is_heatwave": True, "severity": "Severe Heatwave", "color": "#d73027", "code": "RED"}
    elif t >= 45.0 or (t >= 40.0 and dep >= 4.5):
        return {"is_heatwave": True, "severity": "Heatwave", "color": "#f46d43", "code": "ORANGE"}
    elif t >= 38.0 or dep >= 3.0:
        return {"is_heatwave": False, "severity": "Heat Alert Warning", "color": "#eab308", "code": "YELLOW"}
    return {"is_heatwave": False, "severity": "Normal", "color": "#1a9850", "code": "GREEN"}

def get_composite_heatwave_alert(temp_max: float, wbgt_max: float, departure: float = 0.0) -> Dict[str, Any]:
    """
    Dual Composite Alert (Harmonized IMD air temperature + NDMA physiological WBGT):
    Higher of air temp departure or humid heat index determines the alert level.
    """
    imd = classify_imd_heatwave(temp_max, departure)
    
    # WBGT levels: >38.0 Critical (Red), 34-38 High (Orange), 30-34 Moderate (Yellow), <30 Normal (Green)
    if wbgt_max > 38.0:
        wbgt_tier, wbgt_code = "Critical", "RED"
    elif wbgt_max >= 34.0:
        wbgt_tier, wbgt_code = "High", "ORANGE"
    elif wbgt_max >= 30.0:
        wbgt_tier, wbgt_code = "Moderate", "YELLOW"
    else:
        wbgt_tier, wbgt_code = "Low", "GREEN"

    level_order = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}
    active_code = max([imd["code"], wbgt_code], key=lambda c: level_order[c])
    
    tier_map = {
        "RED": ("Extreme Heat Emergency (Red Alert)", "#d73027", "Critical"),
        "ORANGE": ("Severe Heat Stress (Orange Alert)", "#f46d43", "High"),
        "YELLOW": ("Moderate Heat Stress (Yellow Alert)", "#eab308", "Moderate"),
        "GREEN": ("Normal Thermal Conditions (Green Alert)", "#1a9850", "Low"),
    }
    label, color, unified_tier = tier_map[active_code]
    return {
        "alert_code": active_code,
        "alert_label": label,
        "alert_color": color,
        "unified_tier": unified_tier,
        "imd_status": imd["severity"],
        "wbgt_tier": wbgt_tier,
        "air_temp_max": temp_max,
        "wbgt_max": wbgt_max,
    }

def _load_fallback(fallback_path: str = FALLBACK_FILE) -> Dict[str, Any]:
    """Loads offline cached fallback forecast."""
    normalized_path = os.path.abspath(fallback_path)
    if os.path.isfile(normalized_path):
        with open(normalized_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "current" not in data:
                d0 = data.get("daily", [{}])[0]
                t0 = float(d0.get("temp_max", 29.8))
                rh0 = float(d0.get("humidity_mean", 62.0))
                wbgt0 = calculate_wbgt(t0, rh0)
                data["current"] = {
                    "time": d0.get("date", "2026-09-24T12:00:00Z"),
                    "temperature_celsius": t0,
                    "relative_humidity_pct": rh0,
                    "apparent_temperature_celsius": round(t0 + 2.6, 1),
                    "wind_speed_kmh": float(d0.get("wind_speed_max", 14.2)),
                    "wbgt_celsius": wbgt0,
                    "risk_tier": classify_wbgt_risk(wbgt0),
                }
            if "composite_alert" not in data:
                d0 = data.get("daily", [{}])[0]
                t0 = float(d0.get("temp_max", 29.8))
                wbgt0 = float(d0.get("wbgt_max", calculate_wbgt(t0, 60.0)))
                data["composite_alert"] = get_composite_heatwave_alert(t0, wbgt0)
            if "timeline" not in data:
                data["timeline"] = data.get("daily", [])
            return data
    # Ultimate hardcoded fallback if file missing
    fallback_daily = [
        {
            "day": i + 1,
            "date": f"Day {i + 1}",
            "temp_max": 30.0 + i,
            "temp_min": 18.0,
            "humidity_mean": 60.0,
            "wbgt_max": calculate_wbgt(30.0 + i, 60.0),
            "risk_tier": classify_wbgt_risk(calculate_wbgt(30.0 + i, 60.0)),
            "advisory": "Elevated thermal stress. Maintain hydration."
        }
        for i in range(5)
    ]
    return {
        "location": "Madurai, Tamil Nadu",
        "latitude": DEFAULT_LAT,
        "longitude": DEFAULT_LON,
        "source": "Emergency Fallback Cache",
        "summary": "5-day heat wave forecast (Offline Baseline)",
        "composite_alert": get_composite_heatwave_alert(30.0, calculate_wbgt(30.0, 60.0)),
        "current": {
            "time": "2026-09-24T12:00:00Z",
            "temperature_celsius": 29.5,
            "relative_humidity_pct": 60.0,
            "apparent_temperature_celsius": 32.0,
            "wind_speed_kmh": 12.0,
            "wbgt_celsius": calculate_wbgt(29.5, 60.0),
            "risk_tier": classify_wbgt_risk(calculate_wbgt(29.5, 60.0)),
        },
        "daily": fallback_daily,
        "timeline": fallback_daily,
    }

def build_open_meteo_url(lat: float, lon: float, past_days: int = 7, forecast_days: int = 5) -> str:
    """Builds the Open-Meteo request URL (daily metrics + current real-time weather + past history, 3-model blend)."""
    return (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&"
        f"models=ecmwf_ifs025,icon_seamless,gfs025&"
        f"daily=temperature_2m_max,temperature_2m_min,relative_humidity_2m_min,relative_humidity_2m_mean,wind_speed_10m_max,shortwave_radiation_sum&"
        f"current=temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m&"
        f"timezone=Asia%2FKolkata&past_days={past_days}&forecast_days={forecast_days}"
    )

BLEND_FIELDS = (
    "temperature_2m_max", "temperature_2m_min",
    "relative_humidity_2m_min", "relative_humidity_2m_mean",
    "wind_speed_10m_max", "shortwave_radiation_sum",
)
MODEL_NAMES = ("ecmwf_ifs025", "icon_seamless", "gfs025")

def _is_multi_model(daily_raw: Dict[str, Any]) -> bool:
    """Multi-model responses carry per-model suffixed fields (e.g. temperature_2m_max_gfs025)."""
    return any(k.endswith("_" + m) for k in daily_raw for m in MODEL_NAMES)

def _blend_daily_models(daily_raw: Dict[str, Any]) -> Dict[str, Any]:
    """Averages per-model suffixed fields into plain field names (element-wise mean).

    Single-model responses (plain field names) pass through unchanged.
    """
    if not _is_multi_model(daily_raw):
        return daily_raw
    times = daily_raw.get("time", [])
    groups: Dict[str, list] = {}
    plain: Dict[str, Any] = {}
    for key, val in daily_raw.items():
        if key == "time":
            continue
        base = key
        for m in MODEL_NAMES:
            if key.endswith("_" + m):
                base = key[: -(len(m) + 1)]
                break
        if base in BLEND_FIELDS:
            groups.setdefault(base, []).append(val)
        else:
            plain[key] = val
    blended: Dict[str, Any] = {"time": times}
    for field, lists in groups.items():
        blended[field] = []
        for i in range(len(times)):
            vals = [lst[i] for lst in lists if i < len(lst) and lst[i] is not None]
            blended[field].append(round(sum(vals) / len(vals), 2) if vals else None)
    blended.update(plain)
    return blended

def process_open_meteo(raw_data: Dict[str, Any], lat: float, lon: float) -> Dict[str, Any]:
    """Transforms raw Open-Meteo data into a 12-day timeline (7-day history + 5-day forecast) with WBGT and IMD alerts.

    Multi-model responses are element-wise averaged before WBGT computation.
    Peak daytime WBGT uses concurrent afternoon minimum humidity (relative_humidity_2m_min) at Tmax.
    """
    daily_raw = _blend_daily_models(raw_data.get("daily", {}))
    times = daily_raw.get("time", [])
    t_max = daily_raw.get("temperature_2m_max", [])
    t_min = daily_raw.get("temperature_2m_min", [])
    rh_min = daily_raw.get("relative_humidity_2m_min", [])
    rh_mean = daily_raw.get("relative_humidity_2m_mean", [])
    wind = daily_raw.get("wind_speed_10m_max", [])
    solar = daily_raw.get("shortwave_radiation_sum", [])

    total_days = len(times)
    # The last 5 entries represent the forecast window (Days 1 to 5)
    forecast_start_idx = max(0, total_days - 5)

    all_timeline = []
    processed_days = []

    for i in range(total_days):
        tm = float(t_max[i]) if i < len(t_max) and t_max[i] is not None else 30.0
        tmn = float(t_min[i]) if i < len(t_min) and t_min[i] is not None else 18.0
        # Use daytime minimum humidity (around peak Tmax 2 PM) to calculate realistic daytime WBGT
        if i < len(rh_min) and rh_min[i] is not None:
            rh_peak = float(rh_min[i])
        elif i < len(rh_mean) and rh_mean[i] is not None:
            rh_peak = float(rh_mean[i])
        else:
            rh_peak = 35.0
        
        rh_avg = float(rh_mean[i]) if i < len(rh_mean) and rh_mean[i] is not None else rh_peak
        wbgt = calculate_wbgt(tm, rh_peak)
        tier = classify_wbgt_risk(wbgt)
        alert_info = get_composite_heatwave_alert(tm, wbgt)

        # Historical vs Forecast day labeling
        is_forecast = i >= forecast_start_idx
        if is_forecast:
            day_num = (i - forecast_start_idx) + 1
            day_offset = day_num - 1
            phase = "forecast"
        else:
            day_offset = i - forecast_start_idx
            day_num = day_offset
            phase = "historical"

        entry = {
            "day": day_num,
            "day_offset": day_offset,
            "phase": phase,
            "date": times[i],
            "temp_max": tm,
            "temp_min": tmn,
            "humidity_min": rh_peak,
            "humidity_mean": rh_avg,
            "wind_speed_max": float(wind[i]) if i < len(wind) and wind[i] is not None else 12.0,
            "solar_radiation_sum": float(solar[i]) if i < len(solar) and solar[i] is not None else 20.0,
            "wbgt_max": wbgt,
            "risk_tier": tier,
            "alert": alert_info,
            "advisory": f"{alert_info['unified_tier']} risk: Projected peak WBGT of {wbgt:.1f}°C."
        }
        all_timeline.append(entry)
        if is_forecast:
            processed_days.append(entry)

    # In case fewer than 5 days were returned, ensure processed_days has entries
    if not processed_days and all_timeline:
        processed_days = all_timeline[-5:]

    max_overall_wbgt = max(d["wbgt_max"] for d in processed_days) if processed_days else 30.0
    macro_alert = processed_days[0]["alert"] if processed_days else get_composite_heatwave_alert(30.0, 30.0)
    is_blend = _is_multi_model(raw_data.get("daily", {}))

    # Parse real-time current conditions
    curr_raw = raw_data.get("current", {})
    if curr_raw and "temperature_2m" in curr_raw:
        curr_t = float(curr_raw.get("temperature_2m", 28.0))
        curr_rh = float(curr_raw.get("relative_humidity_2m", 60.0))
        curr_wbgt = calculate_wbgt(curr_t, curr_rh)
        current_weather = {
            "time": curr_raw.get("time", ""),
            "temperature_celsius": curr_t,
            "relative_humidity_pct": curr_rh,
            "apparent_temperature_celsius": float(curr_raw.get("apparent_temperature", curr_t)),
            "wind_speed_kmh": float(curr_raw.get("wind_speed_10m", 0.0)),
            "wbgt_celsius": curr_wbgt,
            "risk_tier": classify_wbgt_risk(curr_wbgt),
        }
    else:
        d0 = processed_days[0] if processed_days else {}
        d0_t = float(d0.get("temp_max", 30.0))
        d0_rh = float(d0.get("humidity_mean", 60.0))
        curr_wbgt = calculate_wbgt(d0_t, d0_rh)
        current_weather = {
            "time": d0.get("date", ""),
            "temperature_celsius": d0_t,
            "relative_humidity_pct": d0_rh,
            "apparent_temperature_celsius": d0_t,
            "wind_speed_kmh": float(d0.get("wind_speed_max", 10.0)),
            "wbgt_celsius": curr_wbgt,
            "risk_tier": classify_wbgt_risk(curr_wbgt),
        }

    return {
        "location": "Madurai, Tamil Nadu",
        "latitude": lat,
        "longitude": lon,
        "source": "Open-Meteo Multi-Model Blend (ECMWF + ICON + GFS)" if is_blend else "Open-Meteo Live API",
        "summary": f"5-day forecast active. Peak settlement WBGT reaching {max_overall_wbgt:.1f}°C.",
        "composite_alert": macro_alert,
        "current": current_weather,
        "daily": processed_days,
        "timeline": all_timeline,
    }

def fetch_open_meteo_forecast(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON) -> Dict[str, Any]:
    """Fetches real-time 5-day weather forecast (daily metrics + current weather) from Open-Meteo API."""
    url = build_open_meteo_url(lat, lon)
    req = urllib.request.Request(url, headers={"User-Agent": "ThermalGuard/1.0"})
    with urllib.request.urlopen(req, timeout=10) as response:
        if response.status == 200:
            raw_data = json.loads(response.read().decode("utf-8"))
            return process_open_meteo(raw_data, lat, lon)
        raise RuntimeError(f"Open-Meteo responded with status {response.status}")

def get_5day_forecast(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON, force_fallback: bool = False, fallback_path: str = FALLBACK_FILE) -> Dict[str, Any]:
    """
    Returns 5-day heatwave forecast with WBGT indices.
    Employs 1-hour in-memory cache and automatic fallback to offline baseline.
    """
    global _CACHE
    now = time.time()

    if force_fallback:
        return _load_fallback(fallback_path)

    # Check valid cache
    if _CACHE["data"] is not None and (now - _CACHE["timestamp"] < CACHE_TTL_SECONDS):
        return _CACHE["data"]

    # Try live fetch
    try:
        data = fetch_open_meteo_forecast(lat, lon)
        _CACHE["timestamp"] = now
        _CACHE["data"] = data
        return data
    except Exception as err:
        # Fallback gracefully
        fallback_data = _load_fallback(fallback_path)
        fallback_data["notice"] = f"Using offline fallback: {str(err)}"
        _CACHE["timestamp"] = now
        _CACHE["data"] = fallback_data
        return fallback_data
