from flask import Flask, request, redirect, url_for, render_template_string, make_response
import sqlite3
from datetime import datetime
import random
import math
import os

# ============================================================
# EIA-ASSIST V2
# Student-friendly Environmental Impact Assessment demonstrator
#
# Main improvements:
# 1. No 17-field environmental/impact/mitigation forms.
# 2. User selects actual project activities; impacts are generated
#    from activity profiles.
# 3. Mitigation is activity-specific rather than generic.
# 4. Air-quality demo supports:
#       - manual PM2.5 / PM10 readings
#       - simulated student-demo sensor readings
#       - CPCB breakpoint-based PM sub-index calculation
# 5. Existing database.db is reused and upgraded automatically.
#
# IMPORTANT:
# This is an academic screening/demonstration system. It is NOT a
# statutory/professional EIA and it does not replace certified
# environmental monitoring, laboratory analysis or regulatory appraisal.
# ============================================================

app = Flask(__name__)
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

# ------------------------------------------------------------
# Existing factor set retained for compatibility with old DB.
# ------------------------------------------------------------
FACTORS = [
    "air_quality", "water_quality", "soil_condition", "noise_level",
    "vegetation", "wildlife", "biodiversity", "water_resources",
    "land_resources", "forest_resources", "population_affected",
    "employment_potential", "local_economy", "infrastructure_impact",
    "cultural_sites", "historical_importance", "community_considerations"
]

FACTOR_LABELS = {
    "air_quality": "Air Quality",
    "water_quality": "Water Quality",
    "soil_condition": "Soil Condition",
    "noise_level": "Noise",
    "vegetation": "Vegetation",
    "wildlife": "Wildlife",
    "biodiversity": "Biodiversity",
    "water_resources": "Water Resources",
    "land_resources": "Land Resources",
    "forest_resources": "Forest Resources",
    "population_affected": "Population",
    "employment_potential": "Employment",
    "local_economy": "Local Economy",
    "infrastructure_impact": "Infrastructure",
    "cultural_sites": "Cultural Sites",
    "historical_importance": "Historical Importance",
    "community_considerations": "Community"
}

# ------------------------------------------------------------
# Activity profiles.
# Scores are screening values, not measured environmental data.
# Each activity has:
#   factor: impact score 0-5
#   mitigation: specific control measures
#   effectiveness: expected screening reduction 0-0.80
# ------------------------------------------------------------
ACTIVITIES = {
    "site_clearing": {
        "label": "Site clearing / vegetation removal",
        "description": "Clearing vegetation, removing topsoil or preparing the site.",
        "impacts": {
            "air_quality": 2, "soil_condition": 4, "vegetation": 5,
            "wildlife": 4, "biodiversity": 4, "land_resources": 3,
            "forest_resources": 4, "water_resources": 2,
            "community_considerations": 2
        },
        "mitigation": {
            "air_quality": "Use water misting only where dust is generated, cover loose material and avoid dry sweeping.",
            "soil_condition": "Restrict clearing to the approved footprint, preserve topsoil separately, control erosion and restore disturbed areas.",
            "vegetation": "Mark trees/vegetation to be retained before clearing; avoid unnecessary removal and restore cleared areas with suitable native species.",
            "wildlife": "Inspect the site before clearing, avoid sensitive habitat areas and stop work if protected wildlife is encountered.",
            "biodiversity": "Minimize habitat fragmentation and keep ecological buffers around sensitive features.",
            "land_resources": "Keep earth disturbance within the approved footprint and reuse suitable excavated soil on site.",
            "forest_resources": "Do not remove forest/tree resources without the required permissions; retain trees wherever practicable.",
            "water_resources": "Keep cleared soil away from drains and water bodies and install temporary erosion/runoff controls.",
            "community_considerations": "Provide advance information about disruptive clearing activities and maintain a grievance/contact mechanism."
        },
        "effectiveness": 0.55
    },
    "excavation": {
        "label": "Excavation / earthwork",
        "description": "Excavation, trenching, grading, soil movement and foundation work.",
        "impacts": {
            "air_quality": 4, "soil_condition": 4, "water_quality": 3,
            "noise_level": 3, "water_resources": 3, "land_resources": 4,
            "infrastructure_impact": 2, "community_considerations": 2
        },
        "mitigation": {
            "air_quality": "Dampen exposed soil and haul routes, cover stockpiles, minimize drop heights and maintain equipment.",
            "soil_condition": "Use erosion controls, segregate topsoil, prevent fuel/chemical spills and stabilize exposed soil promptly.",
            "water_quality": "Prevent silt-laden runoff from entering drains or water bodies; use sediment barriers/silt traps where needed.",
            "noise_level": "Maintain excavators and other equipment and schedule high-noise work during permitted hours.",
            "water_resources": "Minimize dewatering and prevent contaminated or sediment-rich water from being discharged untreated.",
            "land_resources": "Reuse suitable excavated material and send excess material only to authorized destinations.",
            "infrastructure_impact": "Identify underground utilities before excavation and protect nearby roads, drains and structures.",
            "community_considerations": "Secure excavations, control access and provide warnings around active work areas."
        },
        "effectiveness": 0.60
    },
    "material_transport": {
        "label": "Material transport / haulage",
        "description": "Movement of soil, aggregate, cement, construction materials and waste vehicles.",
        "impacts": {
            "air_quality": 4, "noise_level": 3, "infrastructure_impact": 3,
            "community_considerations": 3, "land_resources": 1,
            "population_affected": 2
        },
        "mitigation": {
            "air_quality": "Cover dusty loads, control vehicle speed, clean wheels/roads where needed and avoid unnecessary idling.",
            "noise_level": "Maintain vehicles, avoid unnecessary horn use and restrict heavy-vehicle movements to appropriate hours.",
            "infrastructure_impact": "Use approved routes, prevent roadside material dumping and repair project-caused road damage.",
            "community_considerations": "Use safe access routes and communicate expected traffic changes to nearby residents.",
            "population_affected": "Separate pedestrians from construction traffic and provide clear site-entry/exit controls.",
            "land_resources": "Keep temporary storage and vehicle movement within the approved project footprint."
        },
        "effectiveness": 0.60
    },
    "concrete_mixing": {
        "label": "Concrete / batching / mixing",
        "description": "Concrete batching, cement handling, aggregate handling and mixing.",
        "impacts": {
            "air_quality": 4, "water_quality": 3, "soil_condition": 3,
            "noise_level": 4, "water_resources": 3,
            "community_considerations": 2
        },
        "mitigation": {
            "air_quality": "Enclose or cover dusty material handling points, minimize cement dust escape and maintain mixers/vehicles.",
            "water_quality": "Do not discharge cement slurry to drains or soil; collect wash water and manage it through an appropriate system.",
            "soil_condition": "Use designated mixing/washout areas and prevent concrete slurry and chemicals from contacting bare soil.",
            "noise_level": "Use maintained equipment, acoustic controls where appropriate and schedule high-noise operations suitably.",
            "water_resources": "Optimize process water use and reuse suitable wash water where feasible and safe."
        },
        "effectiveness": 0.65
    },
    "demolition": {
        "label": "Demolition / dismantling",
        "description": "Demolition of existing structures and handling of demolition debris.",
        "impacts": {
            "air_quality": 5, "noise_level": 5, "soil_condition": 3,
            "water_quality": 2, "waste": 4, "population_affected": 3,
            "community_considerations": 4, "infrastructure_impact": 3
        },
        "mitigation": {
            "air_quality": "Use controlled wet methods where appropriate, cover debris, use barriers/screens and prevent uncontrolled dust escape.",
            "noise_level": "Use lower-noise methods where practicable, maintain equipment, provide barriers and follow permitted work hours.",
            "soil_condition": "Keep debris in designated areas and prevent hazardous materials or oils from contaminating soil.",
            "water_quality": "Prevent debris and contaminated runoff from entering drains or water bodies.",
            "population_affected": "Restrict access, provide protective barriers and clearly separate the public from demolition operations.",
            "community_considerations": "Notify nearby occupants about major demolition periods and maintain a complaint/contact channel.",
            "infrastructure_impact": "Survey adjacent structures/utilities and use controlled methods to avoid damage."
        },
        "effectiveness": 0.65
    },
    "industrial_processing": {
        "label": "Industrial processing / production",
        "description": "Operation of process equipment, material handling and industrial production.",
        "impacts": {
            "air_quality": 5, "water_quality": 4, "soil_condition": 3,
            "noise_level": 4, "water_resources": 3, "community_considerations": 3,
            "infrastructure_impact": 2
        },
        "mitigation": {
            "air_quality": "Use the appropriate pollution-control system for the process, maintain it, control fugitive emissions and monitor relevant emissions.",
            "water_quality": "Segregate wastewater streams, treat effluent as required and prevent untreated discharge.",
            "soil_condition": "Use secondary containment for oils/chemicals, inspect storage areas and maintain spill-response materials.",
            "noise_level": "Maintain equipment, isolate noisy sources and use acoustic enclosures/barriers where appropriate.",
            "water_resources": "Use water efficiently, control process losses and reuse treated water where feasible.",
            "community_considerations": "Maintain transparent communication and a documented grievance mechanism."
        },
        "effectiveness": 0.70
    },
    "waste_handling": {
        "label": "Waste storage / handling",
        "description": "Collection, temporary storage, segregation and movement of project waste.",
        "impacts": {
            "air_quality": 2, "water_quality": 4, "soil_condition": 4,
            "land_resources": 2, "community_considerations": 3,
            "population_affected": 2
        },
        "mitigation": {
            "air_quality": "Prevent windblown waste, keep dusty waste covered and prohibit uncontrolled burning.",
            "water_quality": "Use covered/contained storage where needed and prevent leachate or contaminated runoff from entering drains.",
            "soil_condition": "Use designated waste storage surfaces and immediately manage spills/leaks.",
            "land_resources": "Minimize storage duration and send waste only through authorized collection/recycling/disposal routes.",
            "community_considerations": "Keep waste areas secure, clean and away from sensitive receptors.",
            "population_affected": "Restrict public access and provide safe waste-handling procedures for workers."
        },
        "effectiveness": 0.65
    },
    "vehicle_operation": {
        "label": "Vehicle / generator operation",
        "description": "Movement and operation of diesel vehicles, generators or other combustion equipment.",
        "impacts": {
            "air_quality": 4, "noise_level": 4, "population_affected": 2,
            "community_considerations": 2
        },
        "mitigation": {
            "air_quality": "Maintain engines, avoid unnecessary idling, use compliant fuel/equipment and inspect visible exhaust emissions.",
            "noise_level": "Maintain silencers/enclosures and position generators away from sensitive receptors where practicable.",
            "population_affected": "Keep exhaust outlets away from occupied areas and control vehicle movement near pedestrians.",
            "community_considerations": "Avoid unnecessary nighttime operation and address repeated nuisance complaints."
        },
        "effectiveness": 0.55
    },
    "water_discharge": {
        "label": "Wastewater / water discharge",
        "description": "Generation, collection, treatment or discharge of wastewater.",
        "impacts": {
            "water_quality": 5, "water_resources": 4, "soil_condition": 3,
            "biodiversity": 2, "community_considerations": 2
        },
        "mitigation": {
            "water_quality": "Collect and treat wastewater before permitted discharge; monitor relevant parameters and prevent bypasses.",
            "water_resources": "Reuse treated water where feasible and minimize freshwater demand.",
            "soil_condition": "Prevent uncontrolled discharge onto soil and maintain leak-proof pipelines/tanks.",
            "biodiversity": "Keep untreated wastewater away from natural water bodies and ecologically sensitive areas.",
            "community_considerations": "Maintain records of discharge monitoring and respond promptly to community concerns."
        },
        "effectiveness": 0.75
    },
    "operation": {
        "label": "Project operation / occupancy",
        "description": "Normal operation, occupancy, services and routine maintenance after construction.",
        "impacts": {
            "air_quality": 2, "water_quality": 2, "water_resources": 3,
            "waste_handling": 3, "noise_level": 2,
            "population_affected": 2, "community_considerations": 2
        },
        "mitigation": {
            "air_quality": "Maintain combustion equipment, manage traffic and prevent open waste burning.",
            "water_quality": "Operate wastewater/sewage treatment systems correctly and prevent untreated discharge.",
            "water_resources": "Use efficient fixtures/processes, repair leaks and reuse treated water where feasible.",
            "noise_level": "Maintain equipment and locate persistent noise sources away from sensitive receptors where practicable.",
            "population_affected": "Maintain safe access, emergency arrangements and clear public information.",
            "community_considerations": "Provide a simple complaint and response mechanism for operational nuisance."
        },
        "effectiveness": 0.55
    }
}

# Remove helper-only keys not in the factor list.
FACTOR_ORDER = FACTORS

# ------------------------------------------------------------
# CPCB IND-AQI PM breakpoints.
# Used for a PM-based demonstration. It is NOT labelled as the
# full official AQI unless minimum data requirements are met.
# ------------------------------------------------------------
PM10_BREAKPOINTS = [
    (0, 50, 0, 50),
    (51, 100, 51, 100),
    (101, 200, 101, 250),
    (201, 300, 251, 350),
    (301, 400, 351, 430),
    (401, 500, 431, 1000)
]
PM25_BREAKPOINTS = [
    (0, 50, 0, 30),
    (51, 100, 31, 60),
    (101, 200, 61, 90),
    (201, 300, 91, 120),
    (301, 400, 121, 250),
    (401, 500, 251, 1000)
]

AQI_INFO = {
    "Good": "Minimal impact.",
    "Satisfactory": "Minor breathing discomfort to sensitive people.",
    "Moderate": "May cause breathing discomfort to sensitive groups.",
    "Poor": "May cause breathing discomfort on prolonged exposure.",
    "Very Poor": "May cause respiratory illness on prolonged exposure.",
    "Severe": "Respiratory effects may occur even in healthy people."
}

def current_datetime():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def table_columns(conn, table):
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]

def add_column(conn, table, name, definition):
    if name not in table_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

def ensure_schema():
    conn = db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            project_type TEXT NOT NULL,
            location TEXT NOT NULL,
            area TEXT NOT NULL,
            phase TEXT NOT NULL,
            estimated_cost TEXT NOT NULL DEFAULT '',
            duration TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    # Keep all old tables so existing data remains usable.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS environmental_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            air_quality TEXT, water_quality TEXT, soil_condition TEXT,
            noise_level TEXT, vegetation TEXT, wildlife TEXT,
            biodiversity TEXT, water_resources TEXT, land_resources TEXT,
            forest_resources TEXT, population_affected TEXT,
            employment_potential TEXT, local_economy TEXT,
            infrastructure_impact TEXT, cultural_sites TEXT,
            historical_importance TEXT, community_considerations TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cols_sql = ", ".join(f"{f} INTEGER" for f in FACTORS)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS baseline_assessment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            {cols_sql},
            created_at TEXT NOT NULL
        )
    """)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS impact_assessment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            {cols_sql},
            created_at TEXT NOT NULL
        )
    """)

    risk_cols = ", ".join(f"{f} REAL" for f in FACTORS)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS risk_assessment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            {risk_cols},
            overall_score REAL,
            overall_level TEXT,
            created_at TEXT NOT NULL
        )
    """)

    text_cols = ", ".join(f"{f} TEXT" for f in FACTORS)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS mitigation_measures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            {text_cols},
            created_at TEXT NOT NULL
        )
    """)

    # New V2 tables.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            activity_key TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(project_id, activity_key)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS air_measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            source TEXT NOT NULL,
            pm25 REAL,
            pm10 REAL,
            no2 REAL,
            so2 REAL,
            co REAL,
            o3 REAL,
            aqi_value INTEGER,
            aqi_category TEXT,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS activity_impacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            activity_key TEXT NOT NULL,
            factor TEXT NOT NULL,
            impact_score INTEGER NOT NULL,
            mitigation TEXT,
            residual_score REAL,
            created_at TEXT NOT NULL
        )
    """)

    # Migrate older risk table names if necessary.
    for table, name, definition in [
        ("risk_assessment", "overall_risk", "REAL"),
        ("risk_assessment", "risk_level", "TEXT")
    ]:
        add_column(conn, table, name, definition)

    conn.commit()
    conn.close()

def get_project(pid):
    conn = db()
    row = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    conn.close()
    return row

def get_selected_activities(pid):
    conn = db()
    rows = conn.execute("""
        SELECT activity_key FROM project_activities
        WHERE project_id=? ORDER BY id
    """, (pid,)).fetchall()
    conn.close()
    return [r["activity_key"] for r in rows]

def latest_air(pid):
    conn = db()
    row = conn.execute("""
        SELECT * FROM air_measurements
        WHERE project_id=? ORDER BY id DESC LIMIT 1
    """, (pid,)).fetchone()
    conn.close()
    return row

def clamp5(v):
    return max(0, min(5, int(round(v))))

# ------------------------------------------------------------
# Screening baseline.
# This is deliberately labelled as a screening baseline.
# Real baseline data can be entered via monitoring tools.
# ------------------------------------------------------------
def baseline_defaults(project):
    # Neutral starting values. Higher values mean more sensitivity/
    # existing environmental concern in this academic model.
    base = {f: 2 for f in FACTORS}

    ptype = (project["project_type"] or "").lower()
    phase = (project["phase"] or "").lower()

    if "industrial" in ptype:
        base.update(air_quality=3, water_quality=3, noise_level=3,
                    water_resources=3, community_considerations=3)
    elif "mining" in ptype:
        base.update(air_quality=3, soil_condition=3, water_quality=3,
                    biodiversity=3, land_resources=3)
    elif "road" in ptype:
        base.update(air_quality=3, noise_level=3,
                    infrastructure_impact=3, population_affected=3)
    elif "residential" in ptype:
        base.update(population_affected=3, infrastructure_impact=3,
                    water_resources=3, community_considerations=3)

    if "operation" in phase:
        base["population_affected"] = max(base["population_affected"], 3)

    return base

def aggregate_impacts(activity_keys):
    scores = {f: 0 for f in FACTORS}
    sources = {f: [] for f in FACTORS}

    for key in activity_keys:
        profile = ACTIVITIES.get(key)
        if not profile:
            continue
        for factor, score in profile["impacts"].items():
            if factor not in scores:
                continue
            # Combine multiple activities without allowing simple
            # addition to exceed the 0-5 screening scale.
            scores[factor] = max(scores[factor], score)
            if score >= 3:
                sources[factor].append(profile["label"])

    return scores, sources

def mitigation_for(factor, activity_keys):
    measures = []
    for key in activity_keys:
        profile = ACTIVITIES.get(key)
        if profile and factor in profile["mitigation"]:
            measures.append(profile["mitigation"][factor])
    # Remove duplicates while preserving order.
    seen = set()
    out = []
    for m in measures:
        if m not in seen:
            out.append(m)
            seen.add(m)
    return out

def calculate_risk(project, activity_keys):
    baseline = baseline_defaults(project)
    impact, sources = aggregate_impacts(activity_keys)

    results = []
    for factor in FACTORS:
        b = baseline[factor]
        i = impact[factor]
        probability = max(1, min(5, round((b + i) / 3)))
        inherent = i * probability
        measures = mitigation_for(factor, activity_keys)
        effectiveness = 0.0
        for key in activity_keys:
            p = ACTIVITIES.get(key)
            if p and factor in p["mitigation"]:
                effectiveness = max(effectiveness, p["effectiveness"])
        residual = round(inherent * (1 - effectiveness), 2) if measures else float(inherent)

        if inherent <= 4:
            level = "Low"
        elif inherent <= 9:
            level = "Moderate"
        elif inherent <= 16:
            level = "High"
        else:
            level = "Very High"

        if residual <= 4:
            residual_level = "Low"
        elif residual <= 9:
            residual_level = "Moderate"
        elif residual <= 16:
            residual_level = "High"
        else:
            residual_level = "Very High"

        results.append({
            "factor": factor,
            "label": FACTOR_LABELS[factor],
            "baseline": b,
            "impact": i,
            "probability": probability,
            "inherent": round(inherent, 2),
            "level": level,
            "residual": residual,
            "residual_level": residual_level,
            "sources": sources[factor],
            "mitigation": measures
        })

    avg_inherent = round(sum(r["inherent"] for r in results) / len(results), 2)
    avg_residual = round(sum(r["residual"] for r in results) / len(results), 2)

    def overall_level(score):
        if score <= 4:
            return "Low"
        if score <= 9:
            return "Moderate"
        if score <= 16:
            return "High"
        return "Very High"

    return {
        "baseline": baseline,
        "impact": impact,
        "results": results,
        "overall_inherent": avg_inherent,
        "overall_residual": avg_residual,
        "inherent_level": overall_level(avg_inherent),
        "residual_level": overall_level(avg_residual)
    }

def save_assessment(pid, calculation):
    conn = db()
    now = current_datetime()

    # Keep the legacy tables populated for compatibility with old report logic.
    cols = ", ".join(FACTORS)
    vals = ", ".join("?" for _ in FACTORS)

    conn.execute("DELETE FROM baseline_assessment WHERE project_id=?", (pid,))
    conn.execute(f"""
        INSERT INTO baseline_assessment(project_id,{cols},created_at)
        VALUES(?,{vals},?)
    """, (pid, *[calculation["baseline"][f] for f in FACTORS], now))

    conn.execute("DELETE FROM impact_assessment WHERE project_id=?", (pid,))
    conn.execute(f"""
        INSERT INTO impact_assessment(project_id,{cols},created_at)
        VALUES(?,{vals},?)
    """, (pid, *[calculation["impact"][f] for f in FACTORS], now))

    conn.execute("DELETE FROM mitigation_measures WHERE project_id=?", (pid,))
    mitigation_values = []
    for f in FACTORS:
        measures = mitigation_for(f, get_selected_activities(pid))
        mitigation_values.append(" ".join(measures) if measures else "No direct activity-specific mitigation required.")

    conn.execute(f"""
        INSERT INTO mitigation_measures(project_id,{cols},created_at)
        VALUES(?,{",".join("?" for _ in FACTORS)},?)
    """, (pid, *mitigation_values, now))

    # Activity-level table.
    conn.execute("DELETE FROM activity_impacts WHERE project_id=?", (pid,))
    for akey in get_selected_activities(pid):
        profile = ACTIVITIES[akey]
        for factor, score in profile["impacts"].items():
            measures = profile["mitigation"].get(factor, "")
            effectiveness = profile["effectiveness"] if measures else 0
            residual = round(score * (1 - effectiveness), 2)
            conn.execute("""
                INSERT INTO activity_impacts
                (project_id,activity_key,factor,impact_score,mitigation,residual_score,created_at)
                VALUES(?,?,?,?,?,?,?)
            """, (pid, akey, factor, score, measures, residual, now))

    conn.execute("DELETE FROM risk_assessment WHERE project_id=?", (pid,))
    risk_values = [r["residual"] for r in calculation["results"]]
    conn.execute(f"""
        INSERT INTO risk_assessment
        (project_id,{",".join(FACTORS)},overall_risk,risk_level,overall_score,overall_level,created_at)
        VALUES(?,{",".join("?" for _ in FACTORS)},?,?,?,?,?)
    """, (
        pid, *risk_values,
        calculation["overall_residual"], calculation["residual_level"],
        calculation["overall_residual"], calculation["residual_level"], now
    ))

    conn.commit()
    conn.close()

def interpolate(value, c_low, c_high, i_low, i_high):
    if c_high == c_low:
        return i_low
    return ((i_high - i_low) / (c_high - c_low)) * (value - c_low) + i_low

def pm_subindex(value, breakpoints):
    value = max(0.0, float(value))
    for i_low, i_high, c_low, c_high in breakpoints:
        if c_low <= value <= c_high:
            return round(interpolate(value, c_low, c_high, i_low, i_high))
    return 500

def aqi_category(aqi):
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Satisfactory"
    if aqi <= 200:
        return "Moderate"
    if aqi <= 300:
        return "Poor"
    if aqi <= 400:
        return "Very Poor"
    return "Severe"

def calculate_pm_demo(pm25, pm10):
    subs = {}
    if pm25 is not None:
        subs["PM2.5"] = pm_subindex(pm25, PM25_BREAKPOINTS)
    if pm10 is not None:
        subs["PM10"] = pm_subindex(pm10, PM10_BREAKPOINTS)
    if not subs:
        return None
    value = max(subs.values())
    return {
        "value": value,
        "category": aqi_category(value),
        "subindices": subs
    }

def simulated_reading():
    # Plausible demo values only; deliberately labelled simulated.
    pm25 = round(random.uniform(12, 95), 1)
    pm10 = round(random.uniform(max(pm25, 30), 180), 1)
    return pm25, pm10

# ------------------------------------------------------------
# HTML helpers
# ------------------------------------------------------------
CSS = """
:root{--green:#176b45;--green2:#0f5132;--bg:#f4f7f5;--card:#fff;--text:#18221d;--muted:#66736c;--line:#dce5df;--blue:#2563eb;--orange:#c26a00;--red:#b42318}
*{box-sizing:border-box}body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--text)}
nav{background:linear-gradient(135deg,#0f5132,#176b45);color:#fff;padding:15px 5%;display:flex;align-items:center;justify-content:space-between;gap:20px}
nav a{color:#fff;text-decoration:none;margin-left:15px;font-size:14px}
.container{max-width:1150px;margin:30px auto;padding:0 18px}
.hero{background:linear-gradient(135deg,#e8f5ed,#fff);border:1px solid var(--line);border-radius:20px;padding:32px;margin-bottom:22px}
h1{font-size:34px;margin:0 0 8px}h2{margin-top:0}h3{margin-bottom:6px}
.muted{color:var(--muted);line-height:1.6}.small{font-size:13px;color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;box-shadow:0 3px 14px rgba(0,0,0,.04)}
.stat{font-size:28px;font-weight:700}.btn{display:inline-block;border:0;border-radius:10px;padding:12px 17px;text-decoration:none;cursor:pointer;font-weight:650;background:var(--green);color:#fff}
.btn.secondary{background:#e8efeb;color:#174d37}.btn.blue{background:var(--blue)}.btn.warn{background:var(--orange)}.btn.danger{background:var(--red)}
form{background:#fff;border:1px solid var(--line);border-radius:16px;padding:22px}
label{display:block;font-weight:650;margin:12px 0 6px}input,select,textarea{width:100%;padding:11px 12px;border:1px solid #cbd6cf;border-radius:9px;font-size:15px;background:#fff}
.row{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:15px}
.activity{border:1px solid var(--line);border-radius:13px;padding:15px;background:#fff;cursor:pointer}
.activity:hover{border-color:#79aa91;background:#f8fcf9}.activity input{width:auto;margin-right:8px}
.activity strong{display:block}.activity p{margin:6px 0 0;color:var(--muted);font-size:13px}
table{width:100%;border-collapse:collapse;background:#fff}th,td{padding:11px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{background:#f0f5f2}
.badge{display:inline-block;padding:5px 9px;border-radius:999px;font-size:12px;font-weight:700;background:#e8efeb}
.low{color:#176b45}.moderate{color:#8a5b00}.high{color:#c26a00}.veryhigh{color:#b42318}
.aqi{font-size:54px;font-weight:800}.aqi.good{color:#176b45}.aqi.satisfactory{color:#547c23}.aqi.moderate{color:#a16207}.aqi.poor{color:#c2410c}.aqi.very-poor{color:#b42318}.aqi.severe{color:#7f1d1d}
.progress{height:9px;background:#e7ece9;border-radius:20px;overflow:hidden}.progress span{display:block;height:100%;background:#176b45}
.notice{padding:13px 15px;border-left:4px solid var(--green);background:#eef7f1;border-radius:8px;margin:12px 0}
.warning{padding:13px 15px;border-left:4px solid #d97706;background:#fff7e8;border-radius:8px;margin:12px 0}
.footer{margin:40px 0;color:var(--muted);font-size:12px}
@media print{nav,.no-print{display:none!important}.container{max-width:none;margin:0}.card,form{box-shadow:none}}
"""

def layout(title, content):
    return render_template_string(f"""
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | EIA-Assist</title><style>{CSS}</style></head>
<body>
<nav><div><strong>🌱 EIA-Assist V2</strong></div>
<div><a href="/">Dashboard</a><a href="/assessment">New Assessment</a></div></nav>
<main class="container">{content}
<div class="footer">Academic EIA demonstration • Not a statutory EIA • Environmental measurements must be verified using appropriate instruments/laboratory or official monitoring data.</div>
</main></body></html>
""")

# ------------------------------------------------------------
# Routes
# ------------------------------------------------------------
@app.route("/")
def home():
    conn = db()
    projects = conn.execute("SELECT * FROM projects ORDER BY id DESC LIMIT 8").fetchall()
    conn.close()
    cards = ""
    for p in projects:
        acts = get_selected_activities(p["id"])
        cards += f"""
        <div class="card">
          <h3>{p["project_name"]}</h3>
          <div class="small">{p["project_type"]} • {p["location"]}</div>
          <p class="muted">{len(acts)} activity/activities selected.</p>
          <a class="btn" href="/project/{p["id"]}">Open assessment</a>
        </div>"""
    if not cards:
        cards = '<div class="card"><h3>No assessments yet</h3><p class="muted">Create your first project to start the demonstration.</p></div>'
    content = f"""
    <section class="hero">
      <h1>Environmental Impact Assessment — simplified & demonstrable</h1>
      <p class="muted">Instead of entering 17 environmental ratings three different times, select what is actually happening at the project site. The system then maps activities → impacts → mitigation → residual risk.</p>
      <a class="btn" href="/assessment">＋ Start New Assessment</a>
    </section>
    <div class="grid">
      <div class="card"><div class="stat">Activity-based</div><p class="muted">Impacts are tied to the work being performed.</p></div>
      <div class="card"><div class="stat">PM₂.₅ / PM₁₀</div><p class="muted">Enter measured readings or use a clearly labelled demo sensor.</p></div>
      <div class="card"><div class="stat">Residual risk</div><p class="muted">Shows risk before and after activity-specific controls.</p></div>
    </div>
    <h2 style="margin-top:30px">Recent projects</h2>
    <div class="grid">{cards}</div>
    """
    return layout("Dashboard", content)

@app.route("/assessment", methods=["GET", "POST"])
def assessment():
    if request.method == "POST":
        data = {
            "project_name": request.form.get("project_name","").strip(),
            "project_type": request.form.get("project_type","").strip(),
            "location": request.form.get("location","").strip(),
            "area": request.form.get("area","").strip(),
            "phase": request.form.get("phase","").strip(),
            "estimated_cost": request.form.get("estimated_cost","").strip(),
            "duration": request.form.get("duration","").strip(),
            "created_at": current_datetime()
        }
        if not all([data["project_name"], data["project_type"], data["location"], data["area"], data["phase"]]):
            return layout("New Assessment", '<div class="warning">Please fill the five required project fields.</div><a class="btn" href="/assessment">Go back</a>')
        conn = db()
        cur = conn.execute("""
            INSERT INTO projects(project_name,project_type,location,area,phase,estimated_cost,duration,created_at)
            VALUES(?,?,?,?,?,?,?,?)
        """, tuple(data.values()))
        pid = cur.lastrowid
        conn.commit(); conn.close()
        return redirect(url_for("activities", project_id=pid))

    content = """
    <div class="hero"><h1>1. Project details</h1><p class="muted">Only the information needed to establish the assessment context. Cost and duration are optional.</p></div>
    <form method="post">
      <div class="row">
        <div><label>Project name *</label><input name="project_name" required placeholder="e.g. Green Valley Apartment Project"></div>
        <div><label>Project type *</label>
          <select name="project_type" required>
            <option value="">Select</option><option>Residential</option><option>Commercial</option><option>Industrial</option>
            <option>Road / Transport</option><option>Mining</option><option>Infrastructure</option><option>Other</option>
          </select>
        </div>
        <div><label>Location *</label><input name="location" required placeholder="City / district / state"></div>
        <div><label>Project area *</label><input name="area" required placeholder="e.g. 2 acres"></div>
        <div><label>Current phase *</label>
          <select name="phase" required><option>Planning</option><option>Construction</option><option>Operation</option><option>Closure / Demolition</option></select>
        </div>
        <div><label>Estimated cost (optional)</label><input name="estimated_cost" placeholder="e.g. ₹10 crore"></div>
        <div><label>Duration (optional)</label><input name="duration" placeholder="e.g. 3 years"></div>
      </div>
      <br><button class="btn" type="submit">Continue to activities →</button>
    </form>
    """
    return layout("New Assessment", content)

@app.route("/activities/<int:project_id>", methods=["GET","POST"])
def activities(project_id):
    project = get_project(project_id)
    if not project:
        return "Project not found", 404

    if request.method == "POST":
        selected = [k for k in request.form.getlist("activities") if k in ACTIVITIES]
        if not selected:
            return layout("Activities", '<div class="warning">Select at least one activity that is actually happening or planned.</div><a class="btn" href="/activities/%s">Go back</a>' % project_id)
        conn = db()
        conn.execute("DELETE FROM project_activities WHERE project_id=?", (project_id,))
        for key in selected:
            conn.execute("INSERT INTO project_activities(project_id,activity_key,created_at) VALUES(?,?,?)", (project_id,key,current_datetime()))
        conn.commit(); conn.close()
        calc = calculate_risk(project, selected)
        save_assessment(project_id, calc)
        return redirect(url_for("monitor", project_id=project_id))

    selected = set(get_selected_activities(project_id))
    items = ""
    for key, p in ACTIVITIES.items():
        checked = "checked" if key in selected else ""
        items += f"""
        <label class="activity">
          <input type="checkbox" name="activities" value="{key}" {checked}>
          <strong>{p["label"]}</strong>
          <p>{p["description"]}</p>
        </label>"""
    content = f"""
    <div class="hero"><h1>2. What is actually being done?</h1>
      <p class="muted"><strong>{project["project_name"]}</strong> — Select only the activities that apply. The system will generate the relevant environmental impacts and mitigation measures automatically.</p>
    </div>
    <form method="post">
      <div class="grid">{items}</div><br>
      <button class="btn" type="submit">Generate environmental assessment →</button>
    </form>
    """
    return layout("Activities", content)

@app.route("/monitor/<int:project_id>", methods=["GET","POST"])
def monitor(project_id):
    project = get_project(project_id)
    if not project:
        return "Project not found", 404

    if request.method == "POST":
        source = request.form.get("source","Manual")
        if source == "Simulated student demo":
            pm25, pm10 = simulated_reading()
            no2 = so2 = co = o3 = None
        else:
            def num(name):
                raw = request.form.get(name,"").strip()
                if raw == "":
                    return None
                try:
                    return float(raw)
                except ValueError:
                    return None
            pm25, pm10 = num("pm25"), num("pm10")
            no2, so2, co, o3 = num("no2"), num("so2"), num("co"), num("o3")

        if pm25 is None and pm10 is None:
            return layout("Air Monitoring", '<div class="warning">Enter PM₂.₅ or PM₁₀, or use the simulated demo reading.</div><a class="btn" href="/monitor/%s">Back</a>' % project_id)

        demo = calculate_pm_demo(pm25, pm10)
        conn = db()
        conn.execute("""
            INSERT INTO air_measurements
            (project_id,source,pm25,pm10,no2,so2,co,o3,aqi_value,aqi_category,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """, (project_id,source,pm25,pm10,no2,so2,co,o3,demo["value"],demo["category"],current_datetime()))
        conn.commit(); conn.close()
        return redirect(url_for("results", project_id=project_id))

    selected = get_selected_activities(project_id)
    last = latest_air(project_id)
    act_names = ", ".join(ACTIVITIES[k]["label"] for k in selected) or "No activities selected"
    previous = ""
    if last:
        previous = f"""
        <div class="card">
          <h3>Latest stored reading</h3>
          <div class="aqi {last["aqi_category"].lower().replace(" ","-")}">{last["aqi_value"]}</div>
          <strong>{last["aqi_category"]}</strong>
          <p class="small">PM₂.₅: {last["pm25"] if last["pm25"] is not None else "—"} µg/m³ • PM₁₀: {last["pm10"] if last["pm10"] is not None else "—"} µg/m³ • Source: {last["source"]}</p>
        </div>"""

    content = f"""
    <div class="hero"><h1>3. Air-quality demonstration</h1>
      <p class="muted">Selected activities: {act_names}</p>
    </div>
    <div class="warning"><strong>Important:</strong> A real air-quality value comes from a suitable monitor or official monitoring data. The demo button creates simulated values for classroom demonstration only. It does not claim that your site has that pollution level.</div>
    <div class="grid">
      <form method="post">
        <input type="hidden" name="source" value="Manual measurement / supplied data">
        <h2>Enter a reading</h2>
        <p class="small">For a student prototype, PM₂.₅ and PM₁₀ are enough to demonstrate pollutant sub-indices. The full CPCB AQI requires sufficient data for at least three pollutants, including PM₂.₅ or PM₁₀.</p>
        <div class="row">
          <div><label>PM₂.₅ (µg/m³)</label><input type="number" step="0.1" min="0" name="pm25" placeholder="e.g. 45"></div>
          <div><label>PM₁₀ (µg/m³)</label><input type="number" step="0.1" min="0" name="pm10" placeholder="e.g. 90"></div>
          <div><label>NO₂ (optional)</label><input type="number" step="0.1" min="0" name="no2"></div>
          <div><label>SO₂ (optional)</label><input type="number" step="0.1" min="0" name="so2"></div>
          <div><label>CO (optional, mg/m³)</label><input type="number" step="0.01" min="0" name="co"></div>
          <div><label>O₃ (optional)</label><input type="number" step="0.1" min="0" name="o3"></div>
        </div><br>
        <button class="btn blue" type="submit">Calculate PM-based index</button>
      </form>
      <form method="post">
        <input type="hidden" name="source" value="Simulated student demo">
        <h2>🎛 Demo sensor</h2>
        <p class="muted">Generates a random PM₂.₅/PM₁₀ reading so you can demonstrate the complete workflow without buying a sensor.</p>
        <button class="btn warn" type="submit">Generate demo reading</button>
      </form>
    </div>
    {previous}
    <br><a class="btn secondary" href="/results/{project_id}">Skip to assessment results →</a>
    """
    return layout("Air Monitoring", content)

@app.route("/results/<int:project_id>")
def results(project_id):
    project = get_project(project_id)
    if not project:
        return "Project not found", 404
    selected = get_selected_activities(project_id)
    calc = calculate_risk(project, selected)
    save_assessment(project_id, calc)
    air = latest_air(project_id)

    high = [r for r in calc["results"] if r["impact"] >= 3]
    rows = ""
    for r in high:
        measures = "<ul>" + "".join(f"<li>{m}</li>" for m in r["mitigation"]) + "</ul>" if r["mitigation"] else "<span class='small'>No activity-specific measure generated.</span>"
        source = ", ".join(r["sources"]) or "—"
        rows += f"""
        <tr><td><strong>{r["label"]}</strong></td><td>{source}</td>
        <td>{r["impact"]}/5</td><td>{r["inherent"]} <span class="badge {r["level"].lower().replace(' ','')}">{r["level"]}</span></td>
        <td>{r["residual"]} <span class="badge {r["residual_level"].lower().replace(' ','')}">{r["residual_level"]}</span></td>
        <td>{measures}</td></tr>"""

    act_cards = "".join(
        f'<div class="card"><strong>{ACTIVITIES[k]["label"]}</strong><p class="small">{ACTIVITIES[k]["description"]}</p></div>'
        for k in selected
    )
    air_card = """
    <div class="card"><h3>Air monitoring</h3><p class="muted">No reading stored yet. You can add a manual or demo reading.</p><a class="btn" href="/monitor/%s">Open air monitor</a></div>
    """ % project_id
    if air:
        air_card = f"""
        <div class="card"><h3>Latest air reading</h3>
          <div class="aqi {air["aqi_category"].lower().replace(" ","-")}">{air["aqi_value"]}</div>
          <strong>{air["aqi_category"]}</strong>
          <p class="small">PM₂.₅: {air["pm25"] if air["pm25"] is not None else "—"} µg/m³ • PM₁₀: {air["pm10"] if air["pm10"] is not None else "—"} µg/m³</p>
          <p class="small">Source: {air["source"]}</p>
          <a class="btn secondary" href="/monitor/{project_id}">Measure again</a>
        </div>"""

    content = f"""
    <div class="hero">
      <h1>Environmental assessment results</h1>
      <p class="muted"><strong>{project["project_name"]}</strong> • {project["project_type"]} • {project["location"]}</p>
      <div class="grid">
        <div><div class="small">Inherent screening risk</div><div class="stat">{calc["overall_inherent"]}</div><span class="badge">{calc["inherent_level"]}</span></div>
        <div><div class="small">Residual screening risk</div><div class="stat">{calc["overall_residual"]}</div><span class="badge">{calc["residual_level"]}</span></div>
      </div>
    </div>
    <div class="grid">{act_cards}{air_card}</div>
    <div class="notice"><strong>Why this is better:</strong> the mitigation table below is generated from the selected activity. For example, excavation produces different controls from demolition or industrial processing.</div>
    <h2>Activity-linked impacts & mitigation</h2>
    <div style="overflow:auto"><table><thead><tr><th>Environmental factor</th><th>Activity causing concern</th><th>Impact</th><th>Before controls</th><th>After controls</th><th>Mitigation</th></tr></thead><tbody>{rows}</tbody></table></div>
    <br>
    <a class="btn" href="/report/{project_id}">Generate final report →</a>
    <a class="btn secondary" href="/activities/{project_id}">Change activities</a>
    """
    return layout("Results", content)

@app.route("/project/<int:project_id>")
def project(project_id):
    p = get_project(project_id)
    if not p: return "Project not found",404
    return redirect(url_for("results", project_id=project_id))

@app.route("/report/<int:project_id>")
def report(project_id):
    project = get_project(project_id)
    if not project: return "Project not found",404
    selected = get_selected_activities(project_id)
    calc = calculate_risk(project, selected)
    air = latest_air(project_id)
    save_assessment(project_id, calc)

    rows = ""
    for r in calc["results"]:
        if r["impact"] <= 0:
            continue
        measures = "<br>".join("• " + m for m in r["mitigation"]) or "No direct activity-specific measure."
        rows += f"""
        <tr><td>{r["label"]}</td><td>{", ".join(r["sources"]) or "—"}</td>
        <td>{r["impact"]}/5</td><td>{r["inherent"]} ({r["level"]})</td>
        <td>{r["residual"]} ({r["residual_level"]})</td><td>{measures}</td></tr>"""

    air_html = "No air reading recorded."
    if air:
        air_html = f"""<strong>PM₂.₅:</strong> {air["pm25"] or "—"} µg/m³ &nbsp;
        <strong>PM₁₀:</strong> {air["pm10"] or "—"} µg/m³ &nbsp;
        <strong>PM-based index:</strong> {air["aqi_value"]} ({air["aqi_category"]})<br>
        <span class="small">Source: {air["source"]}</span>"""

    activities_html = "<ul>" + "".join(f"<li>{ACTIVITIES[k]['label']}</li>" for k in selected) + "</ul>"

    content = f"""
    <div class="hero">
      <h1>Final EIA Screening Report</h1>
      <p><strong>{project["project_name"]}</strong></p>
      <p class="small">Generated: {current_datetime()}</p>
    </div>
    <div class="card">
      <h2>1. Project information</h2>
      <table>
        <tr><th>Project type</th><td>{project["project_type"]}</td></tr>
        <tr><th>Location</th><td>{project["location"]}</td></tr>
        <tr><th>Area</th><td>{project["area"]}</td></tr>
        <tr><th>Phase</th><td>{project["phase"]}</td></tr>
        <tr><th>Estimated cost</th><td>{project["estimated_cost"] or "Not provided"}</td></tr>
        <tr><th>Duration</th><td>{project["duration"] or "Not provided"}</td></tr>
      </table>
    </div>
    <div class="card"><h2>2. Activities assessed</h2>{activities_html}</div>
    <div class="card"><h2>3. Air-quality demonstration</h2>{air_html}
      <p class="small">A PM-only calculation is shown as a demonstration/sub-index style result. It should not be presented as a complete statutory CPCB AQI unless the required pollutant data and averaging period are available.</p>
    </div>
    <div class="card">
      <h2>4. Impact, risk and mitigation</h2>
      <table><thead><tr><th>Factor</th><th>Activity</th><th>Impact</th><th>Inherent risk</th><th>Residual risk</th><th>Activity-specific mitigation</th></tr></thead>
      <tbody>{rows}</tbody></table>
    </div>
    <div class="card">
      <h2>5. Methodology</h2>
      <p class="muted">This student prototype maps selected project activities to screening impact scores. Risk is represented as Impact × Probability, with probability derived from a screening baseline and impact score. Activity-specific controls are then applied using a screening effectiveness factor to show residual risk.</p>
      <p class="warning"><strong>Academic limitation:</strong> Screening values are not field measurements. A real EIA requires site-specific baseline monitoring, impact prediction, legal requirements, expert review and regulatory procedures.</p>
    </div>
    <div class="no-print">
      <button class="btn" onclick="window.print()">🖨 Print / Save as PDF</button>
      <a class="btn secondary" href="/results/{project_id}">Back to results</a>
    </div>
    """
    return layout("Final Report", content)

@app.route("/report/<int:project_id>/download")
def download_report(project_id):
    # Browser-downloadable standalone HTML report.
    html = report(project_id).get_data(as_text=True)
    response = make_response(html)
    response.headers["Content-Disposition"] = 'attachment; filename="EIA_Assist_Report_%s.html"' % project_id
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response

# ------------------------------------------------------------
# Start
# ------------------------------------------------------------
ensure_schema()

if __name__ == "__main__":
    app.run(debug=True)
