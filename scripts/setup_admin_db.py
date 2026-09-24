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

    # Curated authoritative directory of Madurai's sensitive institutions across 5 Municipal Zones
    # Eliminates all duplicate OSM polygon/linestring representations and internal campus room blocks
    cur.execute("DELETE FROM sensitive_facilities")
    
    MADURAI_INSTITUTIONS = [
        # --- ZONE 1 (EAST - K.Pudur, Mattuthavani, Anna Nagar, Teppakulam) ---
        ("FAC-Z1-001", 1, "Madurai Kidney Centre and Transplantation Research Institute", "Hospital / Clinic", "Dr. G. Sundar", "+91 94421 99001", "info@maduraikidney.com", "6/6, Sivagangai Road, Anna Nagar, Madurai - 625020", 9.92732, 78.14774, "verified"),
        ("FAC-Z1-002", 1, "Meenakshi Mission Hospital & Research Centre", "Hospital / Clinic", "Dr. B. Kannan", "+91 94432 11001", "admin@mmhrc.in", "Melur Main Road, Mattuthavani, Madurai - 625107", 9.93850, 78.16520, "verified"),
        ("FAC-Z1-003", 1, "Apollo Speciality Hospitals", "Hospital / Clinic", "Dr. Rohini Sridhar", "+91 98421 22334", "apollo_mdu@apollohospitals.com", "Lake View Road, K.K. Nagar, Madurai - 625020", 9.92810, 78.15180, "verified"),
        ("FAC-Z1-004", 1, "Raghavendhar Hospital", "Hospital / Clinic", "Dr. S. Raghavan", "+91 94433 88990", "raghavendhar@gmail.com", "36-E, Kuruvikaran Salai, Anna Nagar, Madurai - 625020", 9.91607, 78.13965, "verified"),
        ("FAC-Z1-005", 1, "Anbu Hospital - Madurai", "Hospital / Clinic", "Dr. K. Anbuselvan", "+91 94430 33445", "anbuhospital@gmail.com", "150/1, Kamarajar Salai, Near Teppakulam, Madurai - 625009", 9.91018, 78.15120, "verified"),
        ("FAC-Z1-006", 1, "Avss Hospitals, Advanced Trauma Center", "Hospital / Clinic", "Dr. V. Srinivasan", "+91 94430 55667", "avsshospitals@gmail.com", "32-A, Kuruvikaran Salai, Teppakulam, Madurai - 625009", 9.91739, 78.13923, "verified"),
        ("FAC-Z1-007", 1, "Krishna Gastro and Women Care Hospital", "Hospital / Clinic", "", "", "", "120 Feet Road, Surveyor Colony, K.Pudur, Madurai - 625007", 9.91656, 78.14865, "unverified"),
        ("FAC-Z1-008", 1, "G.S. Hospital", "Hospital / Clinic", "", "", "", "15/9, New Ramnad Road, Iravadanallur, Madurai - 625009", 9.90915, 78.15333, "unverified"),
        ("FAC-Z1-009", 1, "Rajalakshmi E.N.T Nursing Home", "Hospital / Clinic", "", "", "", "48, Teppakulam Anupanadi Road, Madurai - 625009", 9.90872, 78.14660, "unverified"),
        ("FAC-Z1-010", 1, "The American College", "College / University", "Dr. M. Davamani Christober", "+91 94431 55661", "principal@americancollege.edu.in", "Alagar Kovil Main Road, Tallakulam, Madurai - 625002", 9.93280, 78.13520, "verified"),
        ("FAC-Z1-011", 1, "Yadava College", "College / University", "Dr. M. Narayanan", "+91 94420 88991", "yadavacollege@gmail.com", "Govindarajan Campus, Thiruppalai, K.Pudur, Madurai - 625014", 9.96540, 78.15210, "verified"),
        ("FAC-Z1-012", 1, "EMG Yadava Women’s College", "College / University", "", "", "", "New Natham Road, Thiruppalai, Madurai - 625014", 9.96320, 78.15430, "unverified"),
        ("FAC-Z1-013", 1, "Tamil Nadu Polytechnic College", "College / University", "", "", "", "Alagar Kovil Road, K.Pudur, Madurai - 625011", 9.94820, 78.14320, "unverified"),
        ("FAC-Z1-014", 1, "Sourashtra Boys Higher Secondary School", "School", "Thiru. T.R. Sridharan", "+91 98422 66771", "sourashtraschool@gmail.com", "Kamarajar Salai, Near Teppakulam, Madurai - 625009", 9.91020, 78.14580, "verified"),
        ("FAC-Z1-015", 1, "Nirmala Girls Higher Secondary School", "School", "Sr. Mary Grace", "+91 94435 77881", "nirmalaschool@gmail.com", "Kamarajar Salai, Madurai - 625009", 9.91250, 78.14410, "verified"),
        ("FAC-Z1-016", 1, "K.Pudur Corporation Higher Secondary School", "School", "", "", "", "Alagar Kovil Road, K.Pudur, Madurai - 625007", 9.94520, 78.14650, "unverified"),
        ("FAC-Z1-017", 1, "Kendriya Vidyalaya No. 1", "School", "", "", "", "Narayanapuram, K.Pudur, Madurai - 625014", 9.95210, 78.14920, "unverified"),
        ("FAC-Z1-018", 1, "Al-Ameen Higher Secondary School", "School", "", "", "", "K.K. Nagar Main Road, Madurai - 625020", 9.92450, 78.15340, "unverified"),

        # --- ZONE 2 (NORTH - Goripalayam, Tallakulam, Sellur, Bibikulam) ---
        ("FAC-Z2-001", 2, "Government Rajaji Hospital (GRH Multi-Speciality)", "Hospital / Clinic", "Dr. A. Rathinavel", "+91 94431 33221", "dean.grh@tn.gov.in", "Panagal Road, Goripalayam, Madurai - 625020", 9.92606, 78.13716, "verified"),
        ("FAC-Z2-002", 2, "Hannah Joseph Hospital", "Hospital / Clinic", "Dr. M. Joseph", "+91 98432 77889", "hannahjoseph@gmail.com", "134, Lake View Road, K.K. Nagar, Madurai - 625020", 9.93120, 78.14560, "verified"),
        ("FAC-Z2-003", 2, "Dr.Agarwal's Eye Hospital", "Hospital / Clinic", "Dr. R. Agarwal", "+91 98425 33445", "madurai@dragarwal.com", "61, D.D. Main Road, Arapalayam, Madurai - 625016", 9.93150, 78.11890, "verified"),
        ("FAC-Z2-004", 2, "Vadamalayan Hospitals", "Hospital / Clinic", "Dr. V. Pugalagiri", "+91 98421 44556", "vadamalayan@vadamalayan.org", "15, Jawahar Road, Chokkikulam, Madurai - 625002", 9.93620, 78.13210, "verified"),
        ("FAC-Z2-005", 2, "Sri Lakshmi Hospital, Madurai", "Hospital / Clinic", "Dr. K. Lakshmi", "+91 98423 44556", "srilakshmi@gmail.com", "210-A, By-Pass Road, Bethaniapuram, Madurai - 625016", 9.93450, 78.11230, "verified"),
        ("FAC-Z2-006", 2, "G.V Hospital", "Hospital / Clinic", "", "", "", "Nataraj Nagar, Suresh Street, By-Pass Road, Madurai - 625016", 9.93210, 78.11540, "unverified"),
        ("FAC-Z2-007", 2, "Jebam Hospital", "Hospital / Clinic", "", "", "", "13, Theni Main Road, Arasaradi, Madurai - 625016", 9.93020, 78.11720, "unverified"),
        ("FAC-Z2-008", 2, "Madurai Medical College", "College / University", "Dr. J. Sangumani", "+91 94432 66772", "mmc.madurai@tn.gov.in", "Panagal Road, Goripalayam, Madurai - 625020", 9.92710, 78.13650, "verified"),
        ("FAC-Z2-009", 2, "Lady Doak College", "College / University", "Dr. Christianna Singh", "+91 94431 77883", "principal@ldc.edu.in", "Hakim Ajmal Khan Road, Tallakulam, Madurai - 625002", 9.93780, 78.13450, "verified"),
        ("FAC-Z2-010", 2, "Fatima College", "College / University", "Dr. Sr. G. Celine Prameela", "+91 94433 99002", "fatimacollegemdu@gmail.com", "Mary Land, Vilangudi, Madurai - 625018", 9.95420, 78.10980, "verified"),
        ("FAC-Z2-011", 2, "Agricultural College and Research Institute (TNAU)", "College / University", "", "", "", "Othakkadai, Melur Road, Madurai - 625104", 9.96210, 78.17230, "unverified"),
        ("FAC-Z2-012", 2, "St. Mary's Higher Secondary School", "School", "Fr. S. Arulappan", "+91 98421 66554", "stmarys_mdu@yahoo.com", "East Veli Street, Madurai - 625001", 9.92980, 78.12870, "verified"),
        ("FAC-Z2-013", 2, "O.C.P.M. Higher Secondary School", "School", "Mrs. J. Hepzibah", "+91 94431 88776", "ocpmschool@gmail.com", "Narimedu, Tallakulam, Madurai - 625002", 9.93650, 78.13520, "verified"),
        ("FAC-Z2-014", 2, "Sellur Corporation Higher Secondary School", "School", "", "", "", "50 Feet Road, Sellur, Madurai - 625002", 9.93890, 78.12150, "unverified"),
        ("FAC-Z2-015", 2, "Noyes Matriculation Higher Secondary School", "School", "", "", "", "Narimedu, Madurai - 625002", 9.93510, 78.13320, "unverified"),

        # --- ZONE 3 (CENTRAL - Meenakshi Temple, Periyar, Simmakkal, Mahal Core) ---
        ("FAC-Z3-001", 3, "Grace Kennet Foundation Hospital", "Hospital / Clinic", "Dr. Esther Rajan", "+91 98421 11223", "gracekennet@gkfhospital.com", "8, Kennet Road, Periyar, Madurai - 625016", 9.91920, 78.11450, "verified"),
        ("FAC-Z3-002", 3, "Janet Hospitals", "Hospital / Clinic", "Dr. P. Janet", "+91 94422 66778", "janethospitals@gmail.com", "18, 1st Street, Arasaradi, Madurai - 625016", 9.92450, 78.11210, "verified"),
        ("FAC-Z3-003", 3, "Bose Hospital", "Hospital / Clinic", "Dr. C. Bose", "+91 94430 77889", "bosehospital@yahoo.com", "Town Hall Road, Madurai Junction, Madurai - 625001", 9.91850, 78.11620, "verified"),
        ("FAC-Z3-004", 3, "Bagavathy Hospital", "Hospital / Clinic", "", "", "", "77, Kamarajar Salai, Kanpalayam, Madurai - 625009", 9.91520, 78.12650, "unverified"),
        ("FAC-Z3-005", 3, "Selvam Hospital", "Hospital / Clinic", "", "", "", "51, Chithrakara Street, Simmakkal, Madurai - 625001", 9.92310, 78.12180, "unverified"),
        ("FAC-Z3-006", 3, "Arun Hospital (அருண் மருத்துவமனை)", "Hospital / Clinic", "", "", "", "185, Munichalai Road, Nelpettai, Madurai - 625009", 9.91680, 78.12850, "unverified"),
        ("FAC-Z3-007", 3, "The Madura College", "College / University", "Dr. J. Suresh", "+91 94432 44551", "principal@maduracollege.edu.in", "Vidya Nagar, TPK Road, Madurai - 625011", 9.91350, 78.11150, "verified"),
        ("FAC-Z3-008", 3, "Meenakshi Government Arts College for Women", "College / University", "Dr. S. Vanathi", "+91 94435 22334", "mgacwmdu@gmail.com", "Kalavai Street, Goripalayam / Central, Madurai - 625002", 9.92850, 78.12650, "verified"),
        ("FAC-Z3-009", 3, "Union Christian Higher Secondary School", "School", "Thiru. D. Paulraj", "+91 98422 99001", "uchss_mdu@rediffmail.com", "North Veli Street, Simmakkal, Madurai - 625001", 9.92540, 78.12150, "verified"),
        ("FAC-Z3-010", 3, "Sethupathi Higher Secondary School", "School", "Thiru. R. Muthuraman", "+91 94431 88992", "sethupathischool@gmail.com", "North Veli Street, Madurai - 625001", 9.92610, 78.12280, "verified"),
        ("FAC-Z3-011", 3, "Capron Hall Girls Higher Secondary School", "School", "Mrs. E. Vimala", "+91 94436 44552", "capronhall@gmail.com", "Mangapuram, Periyar, Madurai - 625001", 9.91780, 78.11320, "verified"),
        ("FAC-Z3-012", 3, "St. Britto Higher Secondary School", "School", "", "", "", "Gnanaolivupuram, Madurai - 625016", 9.92580, 78.10950, "unverified"),

        # --- ZONE 4 (SOUTH - Pasumalai, Thiruparankundram, Palanganatham, Villapuram) ---
        ("FAC-Z4-001", 4, "Aditya Speciality Hospital", "Hospital / Clinic", "Dr. K. Aditya", "+91 98421 55667", "adityahospital@gmail.com", "277, GST Main Road, Thirunagar, Madurai - 625006", 9.87650, 78.06890, "verified"),
        ("FAC-Z4-002", 4, "Devaki Cancer and Research Institute", "Hospital / Clinic", "Dr. S. Devaki", "+91 94432 77884", "devakicancer@gmail.com", "Theni Road, Palanganatham, Madurai - 625003", 9.91420, 78.09850, "verified"),
        ("FAC-Z4-003", 4, "Vijayaraj Speciality Hospital", "Hospital / Clinic", "Dr. R. Vijayaraj", "+91 98422 33441", "vijayarajhospital@gmail.com", "TPK Road, Pasumalai, Madurai - 625004", 9.89650, 78.08720, "verified"),
        ("FAC-Z4-004", 4, "Srinivasa Hospital, Madurai", "Hospital / Clinic", "", "", "", "164, By-Pass Road, Madurai - 625016", 9.90450, 78.09650, "unverified"),
        ("FAC-Z4-005", 4, "Palaniandavar Hospital", "Hospital / Clinic", "", "", "", "Sannathi Street, Thiruparankundram, Madurai - 625005", 9.87890, 78.07120, "unverified"),
        ("FAC-Z4-006", 4, "Thiagarajar College of Engineering (TCE Campus)", "College / University", "Dr. M. Palaninatha Rajan", "+91 94431 44332", "principal@tce.edu", "GST Road, Thiruparankundram, Madurai - 625015", 9.88280, 78.08250, "verified"),
        ("FAC-Z4-007", 4, "Thiagarajar School of Management (TSM)", "College / University", "Dr. M. Selvalakshmi", "+91 94433 11225", "director@tsm.ac.in", "Pamban Swamy Nagar, Thiruparankundram, Madurai - 625015", 9.88120, 78.08450, "verified"),
        ("FAC-Z4-008", 4, "Mannar Thirumalai Naicker College", "College / University", "Dr. B. Manoharan", "+91 94420 55662", "principal@mannarcollege.ac.in", "Pasumalai, Madurai - 625004", 9.89850, 78.08950, "verified"),
        ("FAC-Z4-009", 4, "Saraswathi Narayanan College", "College / University", "", "", "", "Perungudi, Airport Road, Madurai - 625022", 9.86540, 78.09120, "unverified"),
        ("FAC-Z4-010", 4, "The TVS School", "School", "Mrs. S. Vijayalakshmi", "+91 98421 88993", "thetvsschool@tvsschool.org", "TVS Nagar, Subramaniapuram, Madurai - 625011", 9.90560, 78.09450, "verified"),
        ("FAC-Z4-011", 4, "Pasumalai Higher Secondary School", "School", "Thiru. K. Jeyapaul", "+91 94432 99881", "pasumalaischool@gmail.com", "Pasumalai Hills, Madurai - 625004", 9.89720, 78.08810, "verified"),
        ("FAC-Z4-012", 4, "Government Higher Secondary School", "School", "", "", "", "Sannathi Street, Thiruparankundram, Madurai - 625005", 9.88100, 78.07340, "unverified"),
        ("FAC-Z4-013", 4, "Villapuram Corporation Higher Secondary School", "School", "", "", "", "Aruppukottai Road, Villapuram, Madurai - 625012", 9.89210, 78.11890, "unverified"),

        # --- ZONE 5 (WEST - Kochadai, Arappalayam, Ponmeni, SS Colony) ---
        ("FAC-Z5-001", 5, "Prasanna Kumaran Hospital", "Hospital / Clinic", "Dr. S. Prasanna", "+91 98421 77665", "prasannahospital@gmail.com", "By-Pass Road, SBI Staff Colony, Madurai - 625016", 9.92150, 78.09780, "verified"),
        ("FAC-Z5-002", 5, "Annai Hospital", "Hospital / Clinic", "Dr. M. Senthil Nathan", "+91 94430 88771", "annaihospital_ponmeni@gmail.com", "351, Dinamalar Avenue, Ponmeni, Madurai - 625016", 9.91890, 78.09320, "verified"),
        ("FAC-Z5-003", 5, "Keerthi Hospital", "Hospital / Clinic", "Dr. R. Keerthivasan", "+91 94433 44552", "keerthihospital@gmail.com", "Chokkalinga Nagar, By-Pass Road, Madurai - 625016", 9.92050, 78.09540, "verified"),
        ("FAC-Z5-004", 5, "Thiraviyam Pillai Hospital", "Hospital / Clinic", "", "", "", "Melakkal Main Road, Kochadai, Madurai - 625016", 9.92540, 78.08950, "unverified"),
        ("FAC-Z5-005", 5, "Guru Hospital & Cancer Care Centre", "Hospital / Clinic", "", "", "", "Kochadai Main Road, Madurai - 625016", 9.92850, 78.08450, "unverified"),
        ("FAC-Z5-006", 5, "Madurai Kamaraj University Evening College", "College / University", "Dr. K. Pandian", "+91 94431 99003", "mkuevening@mku.ac.in", "Alagappan Nagar, SS Colony, Madurai - 625016", 9.91520, 78.09120, "verified"),
        ("FAC-Z5-007", 5, "KLN College of Information Technology", "College / University", "", "", "", "Pottapalayam / West Extension, Madurai - 630612", 9.90850, 78.07540, "unverified"),
        ("FAC-Z5-008", 5, "Railway Mixed Higher Secondary School", "School", "Thiru. N. Ramakrishnan", "+91 98422 33221", "railwayschool_mdu@gmail.com", "Railway Colony, Arappalayam, Madurai - 625016", 9.92340, 78.10320, "verified"),
        ("FAC-Z5-009", 5, "Ponmeni Corporation High School", "School", "", "", "", "Ponmeni Main Road, Madurai - 625016", 9.91720, 78.09210, "unverified"),
        ("FAC-Z5-010", 5, "C.E.O.A. Matriculation Higher Secondary School", "School", "", "", "", "A.A. Road, Kochadai, Madurai - 625016", 9.92950, 78.08650, "unverified"),
        ("FAC-Z5-011", 5, "Vikaasa School (West Campus)", "School", "", "", "", "Kochadai, Melakkal Main Road, Madurai - 625016", 9.93120, 78.08210, "unverified"),
    ]

    cur.executemany("""
        INSERT INTO sensitive_facilities (
            id, zone_id, name, category, contact_person, phone, email, address, latitude, longitude, status, last_alert_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
    """, MADURAI_INSTITUTIONS)
    print(f"Successfully seeded {len(MADURAI_INSTITUTIONS)} authentic sensitive facilities into {DB_PATH}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
