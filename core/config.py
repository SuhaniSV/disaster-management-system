from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR = ROOT_DIR / "uploads"
DATABASE_DIR = ROOT_DIR / "database"

CITY_NAME = "Global hazard intelligence"
CITY_LAT = 18.5204
CITY_LON = 73.8567
MAP_ZOOM = 11.2

DISCLAIMER = (
    "ResQ-AI is an AI-assisted decision-support prototype. "
    "It does not replace emergency authorities and does not make autonomous "
    "life-critical decisions. Distances are prototype straight-line estimates."
)

RESOURCE_TYPES = {
    "rescue_team": "Rescue Team",
    "medical_rescue": "Medical Rescue Team",
    "ambulance": "Ambulance",
    "fire_response": "Fire Response Team",
}

STATUS_ACTIVE = "Active"
STATUS_ASSIGNED = "Assigned"
STATUS_RESOLVED = "Resolved"

ACCESS_OPEN = "Open"
ACCESS_RESTRICTED = "Restricted"
ACCESS_BLOCKED = "Blocked"
