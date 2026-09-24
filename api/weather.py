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

DEFAULT_LAT = -1.317
DEFAULT_LON = 36.789
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
    """Classifies physiological heat risk from WBGT. Critical: WBGT > 32C (SIH26083 plan spec)."""
    if wbgt > 32.0:
        return "Critical"
    elif wbgt >= 30.0:
        return "High"
    elif wbgt >= 28.0:
        return "Moderate"
    else:
        return "Low"

def _load_fallback(fallback_path: str = FALLBACK_FILE) -> Dict[str, Any]:
    """Loads offline cached fallback forecast."""
    normalized_path = os.path.abspath(fallback_path)
    if os.path.isfile(normalized_path):
        with open(normalized_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Ultimate hardcoded fallback if file missing
    return {
        "location": "Kibera, Nairobi",
        "latitude": DEFAULT_LAT,
        "longitude": DEFAULT_LON,
        "source": "Emergency Fallback Cache",
        "summary": "5-day heat wave forecast (Offline Baseline)",
        "daily": [
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
    }

def build_open_meteo_url(lat: float, lon: float) -> str:
    """Builds the Open-Meteo request URL (daily metrics only)."""
    return (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&"
        f"daily=temperature_2m_max,temperature_2m_min,relative_humidity_2m_mean,wind_speed_10m_max,shortwave_radiation_sum&"
        f"timezone=Africa%2FNairobi&forecast_days=5"
    )

def process_open_meteo(raw_data: Dict[str, Any], lat: float, lon: float) -> Dict[str, Any]:
    """Transforms raw Open-Meteo daily data into the 5-day WBGT forecast structure.

    WBGT is computed from each day's max temperature + mean humidity (daily-max method).
    """
    daily_raw = raw_data.get("daily", {})
    times = daily_raw.get("time", [])
    t_max = daily_raw.get("temperature_2m_max", [])
    t_min = daily_raw.get("temperature_2m_min", [])
    rh_mean = daily_raw.get("relative_humidity_2m_mean", [])
    wind = daily_raw.get("wind_speed_10m_max", [])
    solar = daily_raw.get("shortwave_radiation_sum", [])

    processed_days = []
    for i in range(min(5, len(times))):
        tm = float(t_max[i]) if i < len(t_max) and t_max[i] is not None else 30.0
        tmn = float(t_min[i]) if i < len(t_min) and t_min[i] is not None else 18.0
        rh = float(rh_mean[i]) if i < len(rh_mean) and rh_mean[i] is not None else 60.0
        wbgt = calculate_wbgt(tm, rh)
        tier = classify_wbgt_risk(wbgt)

        processed_days.append({
            "day": i + 1,
            "date": times[i],
            "temp_max": tm,
            "temp_min": tmn,
            "humidity_mean": rh,
            "wind_speed_max": float(wind[i]) if i < len(wind) and wind[i] is not None else 12.0,
            "solar_radiation_sum": float(solar[i]) if i < len(solar) and solar[i] is not None else 20.0,
            "wbgt_max": wbgt,
            "risk_tier": tier,
            "advisory": f"{tier} risk: Projected WBGT of {wbgt:.1f}°C."
        })

    max_overall_wbgt = max(d["wbgt_max"] for d in processed_days) if processed_days else 30.0
    return {
        "location": "Kibera, Nairobi",
        "latitude": lat,
        "longitude": lon,
        "source": "Open-Meteo Live API",
        "summary": f"5-day forecast active. Peak settlement WBGT reaching {max_overall_wbgt:.1f}°C.",
        "daily": processed_days
    }

def fetch_open_meteo_forecast(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON) -> Dict[str, Any]:
    """Fetches real-time 5-day weather forecast (daily metrics) from Open-Meteo API."""
    url = build_open_meteo_url(lat, lon)
    req = urllib.request.Request(url, headers={"User-Agent": "ThermalGuard/1.0"})
    with urllib.request.urlopen(req, timeout=5) as response:
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
