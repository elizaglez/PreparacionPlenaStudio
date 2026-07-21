from pathlib import Path

APP_NAME = "Preparación Plena Studio"
APP_VERSION = "0.5.0"
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"
PROJECTS_DIR = ROOT_DIR / "projects"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
METHODOLOGY_FILE = CONFIG_DIR / "metodologia_ppa.json"
RECENT_PROJECTS_FILE = DATA_DIR / "recent_projects.json"
