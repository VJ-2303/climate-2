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
CACHE_TTL_SECONDS = 600  # 10 minutes (real-time automated polling)
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

def _generate_fallback_hourly(daily: list) -> list:
    """Generates 24-hour baseline hourly forecast if offline fallback is active or hourly data is omitted."""
    d0 = daily[0] if daily else {}
    t_max = float(d0.get("temp_max", 34.0))
    t_min = float(d0.get("temp_min", 24.0))
    rh_mean = float(d0.get("humidity_mean", 60.0))

    from datetime import datetime, timezone, timedelta
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist_tz)

    hourly = []
    for h in range(24):
        dt = now + timedelta(hours=h)
        hour_num = dt.hour
        cycle = 0.5 * (1.0 + math.cos((hour_num - 14) * math.pi / 12))
        temp = t_min + (t_max - t_min) * cycle
        rh = max(30.0, min(85.0, rh_mean - (temp - (t_min + t_max) / 2) * 1.5))
        wbgt = calculate_wbgt(temp, rh)
        risk = classify_wbgt_risk(wbgt)
        is_danger = wbgt >= 30.0 or (11 <= hour_num <= 15 and temp >= 33.0)

        hourly.append({
            "time": dt.strftime("%Y-%m-%dT%H:00"),
            "hour_str": dt.strftime("%I %p").lstrip("0"),
            "hour_num": hour_num,
            "temperature_celsius": round(temp, 1),
            "apparent_temperature_celsius": round(temp + (wbgt - temp) * 0.5, 1),
            "relative_humidity_pct": round(rh, 1),
            "wind_speed_ms": 3.2,
            "wbgt_celsius": round(wbgt, 1),
            "risk_tier": risk,
            "weather_code": 0 if (6 <= hour_num <= 18) else 1,
            "condition": "Clear Sky" if (6 <= hour_num <= 18) else "Mainly Clear",
            "is_danger": is_danger
        })
    return hourly

def _load_fallback(filepath: str = FALLBACK_FILE) -> Dict[str, Any]:
    """Loads static baseline forecast from JSON for offline resilience."""
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "current" not in data:
                d0 = data.get("daily", [{}])[0]
                t0 = float(d0.get("temp_max", 29.8))
                wbgt0 = float(d0.get("wbgt_max", calculate_wbgt(t0, 60.0)))
                data["current"] = {
                    "time": d0.get("date", "2026-09-24"),
                    "temperature_celsius": t0,
                    "relative_humidity_pct": float(d0.get("humidity_mean", 62.0)),
                    "apparent_temperature_celsius": t0,
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
            if "hourly" not in data:
                data["hourly"] = _generate_fallback_hourly(data.get("daily", []))
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
        "hourly": _generate_fallback_hourly(fallback_daily),
    }

def build_open_meteo_url(lat: float, lon: float, past_days: int = 7, forecast_days: int = 5, include_hourly: bool = False) -> str:
    """Builds the Open-Meteo request URL (daily metrics + optional rolling hourly forecast + current weather, 3-model blend)."""
    hourly_param = (
        "&hourly=temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,weather_code"
        if include_hourly
        else ""
    )
    return (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&"
        f"models=ecmwf_ifs025,icon_seamless,gfs025&"
        f"daily=temperature_2m_max,temperature_2m_min,relative_humidity_2m_min,relative_humidity_2m_mean,wind_speed_10m_max,shortwave_radiation_sum"
        f"{hourly_param}&"
        f"current=temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m&"
        f"timezone=Asia%2FKolkata&past_days={past_days}&forecast_days={forecast_days}"
    )

BLEND_FIELDS = (
    "temperature_2m_max", "temperature_2m_min",
    "relative_humidity_2m_min", "relative_humidity_2m_mean",
    "wind_speed_10m_max", "shortwave_radiation_sum",
)
HOURLY_BLEND_FIELDS = (
    "temperature_2m", "relative_humidity_2m",
    "apparent_temperature", "wind_speed_10m", "weather_code",
)
MODEL_NAMES = ("ecmwf_ifs025", "icon_seamless", "gfs025")

def _is_multi_model(raw_dict: Dict[str, Any]) -> bool:
    """Multi-model responses carry per-model suffixed fields (e.g. temperature_2m_max_gfs025)."""
    return any(k.endswith("_" + m) for k in raw_dict for m in MODEL_NAMES)

def _blend_model_dict(raw_dict: Dict[str, Any], blend_fields: tuple) -> Dict[str, Any]:
    """Averages per-model suffixed fields into plain field names (element-wise mean).

    Single-model responses (plain field names) pass through unchanged.
    """
    if not _is_multi_model(raw_dict):
        return raw_dict
    times = raw_dict.get("time", [])
    groups: Dict[str, list] = {}
    plain: Dict[str, Any] = {}
    for key, val in raw_dict.items():
        if key == "time":
            continue
        base = key
        for m in MODEL_NAMES:
            if key.endswith("_" + m):
                base = key[: -(len(m) + 1)]
                break
        if base in blend_fields:
            groups.setdefault(base, []).append(val)
        else:
            plain[key] = val
    blended: Dict[str, Any] = {"time": times}
    for field, lists in groups.items():
        blended[field] = []
        for i in range(len(times)):
            vals = [lst[i] for lst in lists if i < len(lst) and lst[i] is not None]
            if not vals:
                blended[field].append(None)
            elif field == "weather_code":
                blended[field].append(int(round(sum(vals) / len(vals))))
            else:
                blended[field].append(round(sum(vals) / len(vals), 2))
    blended.update(plain)
    return blended

def _blend_daily_models(daily_raw: Dict[str, Any]) -> Dict[str, Any]:
    return _blend_model_dict(daily_raw, BLEND_FIELDS)

def _blend_hourly_models(hourly_raw: Dict[str, Any]) -> Dict[str, Any]:
    return _blend_model_dict(hourly_raw, HOURLY_BLEND_FIELDS)

def map_wmo_weather_code(code: int) -> str:
    """Maps WMO weather code to standard descriptive condition string."""
    if code == 0:
        return "Clear Sky"
    elif code in (1, 2):
        return "Mainly Clear"
    elif code == 3:
        return "Overcast"
    elif code in (45, 48):
        return "Hazy"
    elif code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
        return "Rain Showers"
    elif code in (95, 96, 99):
        return "Thunderstorm"
    return "Partly Cloudy"

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

    # ─── Hourly Processing (Rolling Next 24 Hours) ───
    hourly_raw = _blend_hourly_models(raw_data.get("hourly", {}))
    h_times = hourly_raw.get("time", [])
    h_temps = hourly_raw.get("temperature_2m", [])
    h_rh = hourly_raw.get("relative_humidity_2m", [])
    h_app = hourly_raw.get("apparent_temperature", [])
    h_wind = hourly_raw.get("wind_speed_10m", [])
    h_code = hourly_raw.get("weather_code", [])

    processed_hours = []
    if h_times and len(h_times) > 0:
        from datetime import datetime, timezone, timedelta
        ist_tz = timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(ist_tz)
        now_prefix = now_ist.strftime("%Y-%m-%dT%H:00")

        # Find starting index for current hour
        start_idx = 0
        for idx, t_str in enumerate(h_times):
            if t_str >= now_prefix:
                start_idx = idx
                break

        end_idx = min(len(h_times), start_idx + 24)
        for i in range(start_idx, end_idx):
            t_iso = h_times[i]
            try:
                dt = datetime.fromisoformat(t_iso)
                hour_str = dt.strftime("%I %p").lstrip("0")
                hour_num = dt.hour
            except Exception:
                hour_str = f"H+{i - start_idx}"
                hour_num = i % 24

            t_val = float(h_temps[i]) if i < len(h_temps) and h_temps[i] is not None else 32.0
            rh_val = float(h_rh[i]) if i < len(h_rh) and h_rh[i] is not None else 60.0
            app_val = float(h_app[i]) if i < len(h_app) and h_app[i] is not None else t_val
            wind_val = float(h_wind[i]) if i < len(h_wind) and h_wind[i] is not None else 10.0
            code_val = int(h_code[i]) if i < len(h_code) and h_code[i] is not None else 0

            h_wbgt = calculate_wbgt(t_val, rh_val)
            h_tier = classify_wbgt_risk(h_wbgt)
            is_danger = (h_wbgt >= 30.0) or (11 <= hour_num <= 15 and t_val >= 33.0)

            processed_hours.append({
                "time": t_iso,
                "hour_str": hour_str,
                "hour_num": hour_num,
                "temperature_celsius": round(t_val, 1),
                "apparent_temperature_celsius": round(app_val, 1),
                "relative_humidity_pct": round(rh_val, 1),
                "wind_speed_ms": round(wind_val / 3.6, 1) if wind_val > 0 else 0.0,
                "wbgt_celsius": round(h_wbgt, 1),
                "risk_tier": h_tier,
                "weather_code": code_val,
                "condition": map_wmo_weather_code(code_val),
                "is_danger": is_danger,
            })
    else:
        processed_hours = _generate_fallback_hourly(processed_days)

    now_epoch = time.time()
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
        "hourly": processed_hours,
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_epoch)),
    }

def fetch_open_meteo_forecast(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON) -> Dict[str, Any]:
    """Fetches real-time 5-day weather forecast (daily metrics + rolling hourly forecast + current weather) from Open-Meteo API."""
    url = build_open_meteo_url(lat, lon, include_hourly=True)
    req = urllib.request.Request(url, headers={"User-Agent": "ThermalGuard/1.0"})
    with urllib.request.urlopen(req, timeout=10) as response:
        if response.status == 200:
            raw_data = json.loads(response.read().decode("utf-8"))
            return process_open_meteo(raw_data, lat, lon)
        raise RuntimeError(f"Open-Meteo responded with status {response.status}")

def get_5day_forecast(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON, force_fallback: bool = False, force_refresh: bool = False, fallback_path: str = FALLBACK_FILE) -> Dict[str, Any]:
    """
    Returns 5-day heatwave forecast with WBGT indices and rolling hourly forecasts.
    Employs 10-minute in-memory cache and automatic fallback to offline baseline.
    """
    global _CACHE
    now = time.time()

    if force_fallback:
        return _load_fallback(fallback_path)

    # Check valid cache unless forced
    if not force_refresh and _CACHE["data"] is not None and (now - _CACHE["timestamp"] < CACHE_TTL_SECONDS):
        return _CACHE["data"]

    # Try live fetch
    try:
        data = fetch_open_meteo_forecast(lat, lon)
        data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
        _CACHE["timestamp"] = now
        _CACHE["data"] = data
        return data
    except Exception as err:
        fallback_data = _load_fallback(fallback_path)
        fallback_data["notice"] = f"Using offline fallback: {str(err)}"
        fallback_data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
        _CACHE["timestamp"] = now
        _CACHE["data"] = fallback_data
        return fallback_data
