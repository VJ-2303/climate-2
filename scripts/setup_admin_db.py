#!/usr/bin/env python3
"""
scripts/setup_admin_db.py
Initializes SQLite database `data/admin_facilities.db` with:
1. Official 5 Madurai Municipal Zones & Zonal Officers.
2. ~300 sensitive facilities extracted from `data/raw/madurai_complete.geojson`
   (Schools, Hospitals/Clinics, Colleges/Universities).
"""

import json
import sqlite3
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
GEOJSON_PATH = ROOT / "data" / "raw" / "madurai_complete.geojson"
DB_PATH = ROOT / "data" / "admin_facilities.db"

ZONAL_OFFICERS_INIT = [
    (1, "Zone 1 (East)", "1001", "Dr. K. Murugan", "Zonal Health Officer (ZHO)", "+91 94431 20101", "zho.east@maduraicorporation.gov.in", "Zonal Office 1, Mattuthavani Bus Stand Rd, Madurai - 625007", 1, 38.0),
    (2, "Zone 2 (North)", "2002", "Er. S. Meenakshi", "Zonal Executive Officer", "+91 94432 20202", "zeo.north@maduraicorporation.gov.in", "Zonal Office 2, Race Course Road, Madurai - 625002", 1, 38.0),
    (3, "Zone 3 (Central)", "3003", "Dr. R. Pandian", "Chief Municipal Health Officer", "+91 94433 30303", "cmho.central@maduraicorporation.gov.in", "Aringnar Anna Maligai, Corporation HQ, Madurai - 625001", 1, 38.0),
    (4, "Zone 4 (South)", "4004", "Smt. A. Soundaram", "Zonal Health Inspector", "+91 94434 40404", "zhi.south@maduraicorporation.gov.in", "Zonal Office 4, Palanganatham Main Rd, Madurai - 625003", 1, 38.0),
    (5, "Zone 5 (West)", "5005", "Thiru. M. Senthil", "Zonal Disaster Response Officer", "+91 94435 50505", "zdro.west@maduraicorporation.gov.in", "Zonal Office 5, Bye Pass Road, Ponmeni, Madurai - 625016", 1, 38.0),
]

def extract_coords(c):
    if isinstance(c[0], (int, float)):
        return [c]
    res = []
    for sub in c:
        res.extend(extract_coords(sub))
    return res

def assign_zone(lat: float, lon: float) -> int:
    # Central Zone: inner urban core (Meenakshi Temple, Periyar, Mahal)
    if 9.912 <= lat <= 9.930 and 78.105 <= lon <= 78.132:
        return 3
    # North Zone: North of Vaigai river
    if lat > 9.928:
        return 2
    # South Zone: Southern suburbs (Pasumalai, Thiruparankundram)
    if lat < 9.908:
        return 4
    # East Zone: East of core
    if lon > 78.125:
        return 1
    # West Zone: West of core
    return 5

# Pre-seeded sample emergency contacts for demo realism
KNOWN_CONTACTS = {
    "Grace Kennet Foundation Hospital": ("Dr. Esther Rajan", "+91 98421 11223"),
    "Avss Hospitals, Advanced Trauma Center": ("Dr. V. Srinivasan", "+91 94430 55667"),
    "Hannah Joseph Hospital": ("Dr. M. Joseph", "+91 98432 77889"),
    "Dr.Agarwal's Eye Hospital": ("Dr. R. Agarwal", "+91 98425 33445"),
    "Janet Hospitals": ("Dr. P. Janet", "+91 94422 66778"),
    "Raghavendhar Hospital": ("Dr. S. Raghavan", "+91 94433 88990"),
    "Sri Lakshmi Hospital, Madurai": ("Dr. K. Lakshmi", "+91 98423 44556"),
    "Madurai Kidney Centre and Transplantation Research Institute": ("Dr. G. Sundar", "+91 94421 99001"),
    "Main Building": ("Prof. N. Thiagarajan", "+91 94431 12345"),
    "madurai clinic": ("Dr. A. Arumugam", "+91 98422 23456"),
}

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Zonal Officers table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS zonal_officers (
            zone_id INTEGER PRIMARY KEY,
            zone_name TEXT NOT NULL,
            pin TEXT NOT NULL,
            officer_name TEXT NOT NULL,
            designation TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            office_address TEXT NOT NULL,
            autonomous_alerts INTEGER DEFAULT 1,
            critical_wbgt_threshold REAL DEFAULT 38.0
        )
    """)

    # Populate Zonal Officers
    cur.execute("DELETE FROM zonal_officers")
    cur.executemany("""
        INSERT INTO zonal_officers (
            zone_id, zone_name, pin, officer_name, designation, phone, email, office_address, autonomous_alerts, critical_wbgt_threshold
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ZONAL_OFFICERS_INIT)

    # 2. Sensitive Facilities table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sensitive_facilities (
            id TEXT PRIMARY KEY,
            zone_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'unverified',
            last_alert_time TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (zone_id) REFERENCES zonal_officers (zone_id)
        )
    """)

    # 3. Institutional Alerts table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS institutional_alerts (
            alert_id TEXT PRIMARY KEY,
            zone_id INTEGER NOT NULL,
            facility_id TEXT,
            facility_name TEXT,
            category TEXT NOT NULL,
            recipients_count INTEGER DEFAULT 1,
            trigger_type TEXT NOT NULL,
            message_en TEXT NOT NULL,
            message_ta TEXT NOT NULL,
            local_wbgt REAL NOT NULL,
            timestamp TEXT NOT NULL,
            status TEXT DEFAULT 'dispatched'
        )
    """)

    # Extract unique facilities from GeoJSON (deduplicating OSM LineString/MultiPolygon duplicates)
    cur.execute("DELETE FROM sensitive_facilities")
    if GEOJSON_PATH.is_file():
        with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        facilities = []
        raw_candidates = []

        for feat in data.get("features", []):
            # Only process MultiPolygon (building area surface), ignore LineString (outline rings)
            # which are exact 1:1 duplicates in OSM export
            if feat.get("geometry", {}).get("type") != "MultiPolygon":
                continue

            p = feat.get("properties", {})
            amenity = p.get("amenity")
            building = p.get("building")

            cat = None
            if amenity in ["hospital", "clinic"] or building in ["hospital", "clinic"]:
                cat = "Hospital / Clinic"
            elif amenity in ["school", "kindergarten"] or building in ["school", "kindergarten"]:
                cat = "School"
            elif amenity in ["college", "university"] or building in ["college", "university"]:
                cat = "College / University"

            if not cat:
                continue

            coords = extract_coords(feat["geometry"]["coordinates"])
            arr = np.array(coords)
            lon = float(arr[:, 0].mean())
            lat = float(arr[:, 1].mean())

            raw_name = (p.get("name") or p.get("operator") or "").strip()
            street = (p.get("addr:street") or p.get("street") or "").strip()
            hno = (p.get("addr:housenumber") or p.get("housenumber") or "").strip()

            # Deduplicate by spatial proximity and campus name
            is_dup = False
            for prev in raw_candidates:
                if prev["cat"] == cat:
                    d_lat = (lat - prev["lat"]) * 111000
                    d_lon = (lon - prev["lon"]) * 109000
                    dist = np.sqrt(d_lat**2 + d_lon**2)
                    # If same named institution within 200m -> duplicate block/record
                    if raw_name and prev["raw_name"] and raw_name.lower() == prev["raw_name"].lower() and dist < 200.0:
                        is_dup = True
                        break
                    # If same category within 15m -> duplicate footprint
                    if dist < 15.0:
                        is_dup = True
                        break

            if is_dup:
                continue

            raw_candidates.append({
                "raw_name": raw_name,
                "street": street,
                "hno": hno,
                "cat": cat,
                "lat": lat,
                "lon": lon,
            })

        zone_counters = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for item in raw_candidates:
            zid = assign_zone(item["lat"], item["lon"])
            zone_counters[zid] += 1

            cat = item["cat"]
            raw_name = item["raw_name"]
            street = item["street"]
            hno = item["hno"]

            if raw_name:
                name = raw_name
            elif hno and street:
                name = f"#{hno}, {street} {cat}"
            elif street:
                name = f"{street} {cat} #{zone_counters[zid]}"
            else:
                name = f"Zone {zid} Municipal {cat} #{zone_counters[zid]}"

            addr = f"#{hno}, {street}" if (hno and street) else (street or f"Zone {zid} Sector, Madurai")
            fac_id = f"FAC-Z{zid}-{zone_counters[zid]:03d}"

            # Check known demo contacts
            contact_person, phone = KNOWN_CONTACTS.get(name, ("", ""))
            status = "verified" if phone else "unverified"

            facilities.append((
                fac_id, zid, name, cat, contact_person, phone, "", addr, item["lat"], item["lon"], status, None
            ))

        cur.executemany("""
            INSERT INTO sensitive_facilities (
                id, zone_id, name, category, contact_person, phone, email, address, latitude, longitude, status, last_alert_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, facilities)
        print(f"Successfully seeded {len(facilities)} unique sensitive facilities into {DB_PATH}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
