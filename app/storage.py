import json
from app.config import CONFIG_DIR, DATA_DIR, PROJECTS_DIR, SETTINGS_FILE, METHODOLOGY_FILE, RECENT_PROJECTS_FILE

DEFAULT_SETTINGS = {"default_projects_folder": str(PROJECTS_DIR), "theme":"dark", "language":"es"}

DEFAULT_METHODOLOGY = {
    "name":"Metodología PPA",
    "principles":[
        "La Biblia es la autoridad.",
        "La Atalaya es la guía.",
        "La IA actúa solo como editora, nunca como autora doctrinal.",
        "Las preguntas se copian exactamente.",
        "Las respuestas son cortas y conversacionales.",
        "Las comparaciones se usan solo cuando son útiles.",
        "Los textos bíblicos se explican solo cuando es necesario.",
        "Las imágenes se explican únicamente desde el artículo o el audio.",
        "No se permite especulación.",
        "No se permite reinterpretación.",
        "No se permiten añadidos doctrinales."
    ],
    "workflow":{
        "inputs":["PDF","MP3","Citas bíblicas TNM 2019"],
        "first_output":"MASTER completo",
        "after_approval":["Narración","Prompts de imágenes","Prompts de video","Miniatura","Descripción de YouTube","Etiquetas"]
    }
}

def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def ensure_app_data():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists(): save_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    if not METHODOLOGY_FILE.exists(): save_json(METHODOLOGY_FILE, DEFAULT_METHODOLOGY)
    if not RECENT_PROJECTS_FILE.exists(): save_json(RECENT_PROJECTS_FILE, [])

def load_settings():
    ensure_app_data()
    data = load_json(SETTINGS_FILE, {})
    merged = DEFAULT_SETTINGS.copy()
    merged.update(data)
    return merged

def save_settings(data):
    save_json(SETTINGS_FILE, data)

def load_methodology():
    ensure_app_data()
    return load_json(METHODOLOGY_FILE, DEFAULT_METHODOLOGY)

def load_recent_projects():
    ensure_app_data()
    data = load_json(RECENT_PROJECTS_FILE, [])
    return data if isinstance(data, list) else []

def add_recent_project(project):
    items = [x for x in load_recent_projects() if x.get("root") != project.get("root")]
    items.insert(0, project)
    save_json(RECENT_PROJECTS_FILE, items[:20])
